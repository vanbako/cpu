"""Memory instruction semantics for CPU v0.1.

Owner stories:
- E04-S03: `LD48`, `ST48`, `CLC`, and `CSC`.
- E04-S05: capability load/store reporting details.
- E09-S07: common effective-access check order.
- I03-S04: memory operation execution without translation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import Capability, CapabilityPermission, decode_bounds_metadata
from .cells import ADDRESS_SPACE_CELLS, CAPABILITY_OBJECT_CELLS, INTEGER_OBJECT_CELLS, is_aligned
from .instructions import (
    ArchitecturalEffects,
    CapCause,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultCapIndex,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .memory import TaggedMemory
from .mmu import AccessType, Translation, translate
from .state import CoreState, require_general_capability_register_index, require_integer_register_index


MEMORY_MNEMONICS = frozenset({"LD48", "ST48", "CLC", "CSC"})


@dataclass(frozen=True)
class St48Effect:
    address: int
    value: int

    def apply(self, memory: TaggedMemory) -> None:
        memory.st48(self.address, self.value)


@dataclass(frozen=True)
class CscEffect:
    address: int
    capability: Capability

    def apply(self, memory: TaggedMemory) -> None:
        memory.csc(self.address, self.capability)


def memory_instruction(
    mnemonic: str,
    operands: tuple[object, ...],
    *,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(
        mnemonic,
        InstructionSize.BITS_24,
        operands=operands,
        location=location,
    )


def execute_memory(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_memory_checked(core, memory, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_memory_checked(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    mnemonic = instruction.mnemonic
    if mnemonic not in MEMORY_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    if mnemonic == "LD48":
        dd, ca, di = _operands(instruction, 3)
        dd = require_integer_register_index(dd)
        ca = require_general_capability_register_index(ca)
        di = require_integer_register_index(di)
        effective = _effective_address(core, ca, di)
        fault = _check_memory_access(
            core,
            memory,
            instruction,
            ca,
            effective,
            INTEGER_OBJECT_CELLS,
            INTEGER_OBJECT_CELLS,
            (CapabilityPermission.LD,),
        )
        if fault is not None:
            return fault
        physical = _translate_memory_access(
            core,
            memory,
            instruction,
            effective,
            AccessType.LOAD,
        )
        if not isinstance(physical, int):
            return physical
        return instruction.normal_retire(
            ArchitecturalEffects(integer_writes=((dd, memory.ld48(physical)),))
        )

    if mnemonic == "ST48":
        ca, di, ds = _operands(instruction, 3)
        ca = require_general_capability_register_index(ca)
        di = require_integer_register_index(di)
        ds = require_integer_register_index(ds)
        effective = _effective_address(core, ca, di)
        fault = _check_memory_access(
            core,
            memory,
            instruction,
            ca,
            effective,
            INTEGER_OBJECT_CELLS,
            INTEGER_OBJECT_CELLS,
            (CapabilityPermission.ST,),
        )
        if fault is not None:
            return fault
        physical = _translate_memory_access(
            core,
            memory,
            instruction,
            effective,
            AccessType.STORE,
        )
        if not isinstance(physical, int):
            return physical
        return instruction.normal_retire(
            ArchitecturalEffects(
                memory_effects=(St48Effect(physical, core.read_d(ds)),)
            )
        )

    if mnemonic == "CLC":
        cd, ca, di = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        ca = require_general_capability_register_index(ca)
        di = require_integer_register_index(di)
        effective = _effective_address(core, ca, di)
        fault = _check_memory_access(
            core,
            memory,
            instruction,
            ca,
            effective,
            CAPABILITY_OBJECT_CELLS,
            CAPABILITY_OBJECT_CELLS,
            (CapabilityPermission.LD, CapabilityPermission.LC),
        )
        if fault is not None:
            return fault
        physical = _translate_memory_access(
            core,
            memory,
            instruction,
            effective,
            AccessType.LOAD,
        )
        if not isinstance(physical, int):
            return physical
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, memory.clc(physical)),))
        )

    if mnemonic == "CSC":
        ca, di, cs = _operands(instruction, 3)
        ca = require_general_capability_register_index(ca)
        di = require_integer_register_index(di)
        cs = require_general_capability_register_index(cs)
        effective = _effective_address(core, ca, di)
        stored_capability = core.read_c(cs)
        required_permissions = [CapabilityPermission.ST, CapabilityPermission.SC]
        if stored_capability.is_valid and stored_capability.is_local:
            required_permissions.append(CapabilityPermission.SL)
        fault = _check_memory_access(
            core,
            memory,
            instruction,
            ca,
            effective,
            CAPABILITY_OBJECT_CELLS,
            CAPABILITY_OBJECT_CELLS,
            tuple(required_permissions),
            local_store_check=stored_capability.is_valid and stored_capability.is_local,
        )
        if fault is not None:
            return fault
        physical = _translate_memory_access(
            core,
            memory,
            instruction,
            effective,
            AccessType.STORE,
        )
        if not isinstance(physical, int):
            return physical
        return instruction.normal_retire(
            ArchitecturalEffects(memory_effects=(CscEffect(physical, stored_capability),))
        )

    raise AssertionError(f"unhandled memory mnemonic {mnemonic}")


def _check_memory_access(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
    authorizer_index: int,
    effective: int,
    object_cells: int,
    alignment_cells: int,
    required_permissions: tuple[CapabilityPermission, ...],
    *,
    local_store_check: bool = False,
) -> ExecutionResult | None:
    authorizer = core.read_c(authorizer_index)
    fault_cap_idx = _c_index(authorizer_index)

    if authorizer.is_invalid:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            fault_cap_idx,
            0,
        )
    if authorizer.is_sealed:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            fault_cap_idx,
            0,
        )
    if not 0 <= effective <= ADDRESS_SPACE_CELLS - object_cells:
        return _bounds_fault(core, instruction, fault_cap_idx, 0)
    if not is_aligned(effective, alignment_cells):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                _instruction_location(core, instruction),
                tval=effective,
            )
        )

    bounds = decode_bounds_metadata(authorizer.payload.bounds_metadata)
    if not bounds.contains_range(effective, effective + object_cells):
        return _bounds_fault(core, instruction, fault_cap_idx, effective)

    if memory.overlaps_protected_range(effective, object_cells):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
            CapCause.PERMISSION,
            fault_cap_idx,
            effective,
        )

    for permission in required_permissions:
        if authorizer.payload.has_permissions(permission):
            continue
        if permission is CapabilityPermission.SL and local_store_check:
            return _capability_fault(
                core,
                instruction,
                ExceptionCause.CAPABILITY_LOCAL_STORE_FAULT,
                CapCause.LOCAL_STORE,
                fault_cap_idx,
                effective,
            )
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            fault_cap_idx,
            0,
        )

    return None


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _translate_memory_access(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
    effective: int,
    access_type: AccessType,
) -> int | ExecutionResult:
    translated = translate(
        core,
        memory,
        effective,
        access_type,
        _instruction_location(core, instruction),
    )
    if isinstance(translated, Translation):
        return translated.physical_address
    return instruction.fault(translated)


def _operands(instruction: DecodedInstruction, count: int) -> tuple[int, ...]:
    if len(instruction.operands) != count:
        raise ValueError("wrong operand count")
    result = []
    for operand in instruction.operands:
        if type(operand) is not int:
            raise TypeError("memory instruction operands must be register indices")
        result.append(operand)
    return tuple(result)


def _effective_address(core: CoreState, capability_index: int, offset_index: int) -> int:
    return core.read_c(capability_index).payload.cursor + _signed_48(core.read_d(offset_index))


def _signed_48(value: int) -> int:
    value &= (1 << 48) - 1
    sign_bit = 1 << 47
    if value & sign_bit:
        return value - (1 << 48)
    return value


def _c_index(index: int) -> FaultCapIndex:
    return FaultCapIndex(0x10 + index)


def _bounds_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        CapCause.BOUNDS,
        fault_cap_idx,
        tval,
    )


def _capability_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    cause: ExceptionCause,
    capcause: CapCause,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> ExecutionResult:
    return instruction.fault(
        FaultPacket(
            cause,
            _instruction_location(core, instruction),
            tval=tval,
            capcause=capcause,
            fault_cap_idx=fault_cap_idx,
        )
    )

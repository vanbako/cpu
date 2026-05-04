"""`LL48` and `SC48` atomic instruction semantics for CPU v0.1.

Owner stories:
- E08-S01: `LL48`/`SC48` load-linked/store-conditional behavior.
- E08-S02: reservation identity, clear events, and progress constraints.
- E09-S07: effective access checks for atomic memory operations.
- I06-S03: `LL48`/`SC48` reservations.
"""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import CapabilityPermission, decode_bounds_metadata
from .cells import ADDRESS_SPACE_CELLS, INTEGER_OBJECT_CELLS, is_aligned
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
from .mmu import AccessType, MEMORY_TYPE_NORMAL_COHERENT, Translation, translate
from .reservations import ReservationClearEffect, ReservationInstallEffect
from .state import CoreState, require_general_capability_register_index, require_integer_register_index


ATOMIC_MNEMONICS = frozenset({"LL48", "SC48"})


@dataclass(frozen=True)
class Sc48Effect:
    address: int
    value: int
    length_cells: int = INTEGER_OBJECT_CELLS

    def apply(self, memory: TaggedMemory) -> None:
        memory.st48(self.address, self.value)


def atomic_instruction(
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


def execute_atomic(
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
        return _execute_atomic_checked(core, memory, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return _fault_and_clear(
            core,
            instruction,
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            ),
        )


def _execute_atomic_checked(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in ATOMIC_MNEMONICS:
        return _fault_and_clear(
            core,
            instruction,
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            ),
        )

    location = _instruction_location(core, instruction)
    if not instruction.size.is_legal_start(location.address, location.slot):
        return _fault_and_clear(
            core,
            instruction,
            FaultPacket(ExceptionCause.ALIGN_FAULT, location, tval=location.address),
        )

    if instruction.mnemonic == "LL48":
        dd, ca, di = _operands(instruction, 3)
        dd = require_integer_register_index(dd)
        ca = require_general_capability_register_index(ca)
        di = require_integer_register_index(di)
        effective = _effective_address(core, ca, di)
        access = _check_atomic_access(
            core,
            memory,
            instruction,
            ca,
            effective,
            CapabilityPermission.LD,
            AccessType.LOAD,
        )
        if not isinstance(access, Translation):
            return _fault_and_clear(core, instruction, access)
        return instruction.normal_retire(
            ArchitecturalEffects(
                integer_writes=((dd, memory.ld48(access.physical_address)),),
                reservation_effects=(
                    ReservationInstallEffect(
                        access.physical_address,
                        access.memory_type,
                    ),
                ),
            )
        )

    dr, ds, ca, di = _operands(instruction, 4)
    dr = require_integer_register_index(dr)
    ds = require_integer_register_index(ds)
    ca = require_general_capability_register_index(ca)
    di = require_integer_register_index(di)
    store_value = core.read_d(ds)
    effective = _effective_address(core, ca, di)
    access = _check_atomic_access(
        core,
        memory,
        instruction,
        ca,
        effective,
        CapabilityPermission.ST,
        AccessType.STORE,
    )
    if not isinstance(access, Translation):
        return _fault_and_clear(core, instruction, access)

    force_failure = bool(instruction.attributes.get("force_spurious_failure", False))
    success = core.reservation.matches_word(access.physical_address) and not force_failure
    if success:
        return instruction.normal_retire(
            ArchitecturalEffects(
                integer_writes=((dr, 0),),
                memory_effects=(Sc48Effect(access.physical_address, store_value),),
                reservation_effects=(ReservationClearEffect(),),
            )
        )
    return instruction.normal_retire(
        ArchitecturalEffects(
            integer_writes=((dr, 1),),
            reservation_effects=(ReservationClearEffect(),),
        )
    )


def _check_atomic_access(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
    authorizer_index: int,
    effective: int,
    permission: CapabilityPermission,
    access_type: AccessType,
) -> Translation | FaultPacket:
    authorizer = core.read_c(authorizer_index)
    fault_cap_idx = _c_index(authorizer_index)

    if authorizer.is_invalid:
        return _capability_packet(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            fault_cap_idx,
            0,
        )
    if authorizer.is_sealed:
        return _capability_packet(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            fault_cap_idx,
            0,
        )
    if not 0 <= effective <= ADDRESS_SPACE_CELLS - INTEGER_OBJECT_CELLS:
        return _bounds_packet(core, instruction, fault_cap_idx, 0)
    if not is_aligned(effective, INTEGER_OBJECT_CELLS):
        return FaultPacket(
            ExceptionCause.ALIGN_FAULT,
            _instruction_location(core, instruction),
            tval=effective,
        )
    bounds = decode_bounds_metadata(authorizer.payload.bounds_metadata)
    if not bounds.contains_range(effective, effective + INTEGER_OBJECT_CELLS):
        return _bounds_packet(core, instruction, fault_cap_idx, effective)
    if memory.overlaps_protected_range(effective, INTEGER_OBJECT_CELLS):
        return _capability_packet(
            core,
            instruction,
            ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
            CapCause.PERMISSION,
            fault_cap_idx,
            effective,
        )
    if not authorizer.payload.has_permissions(permission):
        return _capability_packet(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            fault_cap_idx,
            0,
        )
    translated = translate(
        core,
        memory,
        effective,
        access_type,
        _instruction_location(core, instruction),
    )
    if not isinstance(translated, Translation):
        return translated
    if translated.memory_type != MEMORY_TYPE_NORMAL_COHERENT:
        return FaultPacket(
            ExceptionCause.ACCESS_FAULT,
            _instruction_location(core, instruction),
            tval=translated.physical_address,
        )
    return translated


def _fault_and_clear(
    core: CoreState,
    instruction: DecodedInstruction,
    packet: FaultPacket,
) -> ExecutionResult:
    core.reservation.clear()
    return instruction.fault(packet)


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _operands(instruction: DecodedInstruction, count: int) -> tuple[int, ...]:
    if len(instruction.operands) != count:
        raise ValueError("wrong operand count")
    result = []
    for operand in instruction.operands:
        if type(operand) is not int:
            raise TypeError("atomic operands must be register indices")
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


def _bounds_packet(
    core: CoreState,
    instruction: DecodedInstruction,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> FaultPacket:
    return _capability_packet(
        core,
        instruction,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        CapCause.BOUNDS,
        fault_cap_idx,
        tval,
    )


def _capability_packet(
    core: CoreState,
    instruction: DecodedInstruction,
    cause: ExceptionCause,
    capcause: CapCause,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> FaultPacket:
    return FaultPacket(
        cause,
        _instruction_location(core, instruction),
        tval=tval,
        capcause=capcause,
        fault_cap_idx=fault_cap_idx,
    )

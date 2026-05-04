"""Direct call and protected return-stack push semantics for CPU v0.1.

Owner stories:
- E04-S04: direct `CALL` control-transfer semantics.
- E05-S04: protected return-stack push transaction.
- E06-S03: sealed local return capability derivation.
- E06-S04: protected return-stack access and fault reporting.
- I05-S01: direct `CALL` and protected return-stack push.
"""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import (
    Capability,
    CapabilityFlag,
    CapabilityPermission,
    OTYPE_ENTRY,
    OTYPE_RETURN,
    OTYPE_UNSEALED,
)
from .cells import ADDRESS_SPACE_CELLS, CAPABILITY_OBJECT_CELLS
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
from .state import (
    CoreState,
    SLOT_0,
    SlottedCapability,
    SPECIAL_NAME_TO_CCSR_INDEX,
    require_general_capability_register_index,
)


CALL_MNEMONICS = frozenset({"CALL", "CALLC"})


@dataclass(frozen=True)
class ReturnStackPushEffect:
    address: int
    capability: Capability

    def apply(self, memory: TaggedMemory) -> None:
        memory.csc(self.address, self.capability)


def call_instruction(
    mnemonic: str,
    operands: tuple[object, ...],
    *,
    size: InstructionSize = InstructionSize.BITS_24,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(
        mnemonic,
        size,
        operands=operands,
        location=location,
    )


def execute_call(
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
        return _execute_call_checked(core, memory, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_call_checked(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in CALL_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    location = _instruction_location(core, instruction)
    if not instruction.size.is_legal_start(location.address, location.slot):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                location,
                tval=location.address,
            )
        )

    pcc_fault = _check_current_pcc(core, instruction)
    if pcc_fault is not None:
        return pcc_fault

    continuation = _call_continuation(location, instruction.size)
    if not _is_cell_address(continuation):
        return _pcc_bounds_fault(core, instruction, 0)
    pcc_capability = location.pcc.without_slot()
    if not pcc_capability.payload.bounds.contains_cursor(continuation):
        return _pcc_bounds_fault(core, instruction, continuation)

    if instruction.mnemonic == "CALL":
        (target_cell,) = _integer_operands(instruction, 1)
        target_fault = _check_direct_target(core, instruction, target_cell)
        if target_fault is not None:
            return target_fault
        next_pcc = SlottedCapability.from_capability(
            pcc_capability.with_cursor(target_cell),
            SLOT_0,
        )
    elif instruction.mnemonic == "CALLC":
        (cs,) = _integer_operands(instruction, 1)
        cs = require_general_capability_register_index(cs)
        entry_capability = core.read_c(cs)
        entry_fault = _check_entry_capability(core, instruction, cs, entry_capability)
        if entry_fault is not None:
            return entry_fault
        next_pcc = SlottedCapability.from_capability(
            entry_capability.with_otype(OTYPE_UNSEALED),
            SLOT_0,
        )
    else:
        raise AssertionError(f"unhandled call mnemonic {instruction.mnemonic}")

    return_capability = _return_capability(pcc_capability, continuation)
    push_target = core.special_capabilities.read("RSC").payload.cursor - CAPABILITY_OBJECT_CELLS
    push_fault = _check_protected_push(core, memory, instruction, push_target, return_capability)
    if push_fault is not None:
        return push_fault

    rsc = core.special_capabilities.read("RSC")
    next_rsc = rsc.with_cursor(push_target)
    return instruction.normal_retire(
        ArchitecturalEffects(
            ccsr_writes=((SPECIAL_NAME_TO_CCSR_INDEX["RSC"], next_rsc),),
            memory_effects=(ReturnStackPushEffect(push_target, return_capability),),
            pcc_update=next_pcc,
        )
    )


def _check_current_pcc(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult | None:
    pcc = core.pcc.without_slot()
    if pcc.is_invalid:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            FaultCapIndex.PCC,
            core.pcc.payload.cursor,
        )
    if pcc.is_sealed:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            FaultCapIndex.PCC,
            0,
        )
    if not pcc.payload.has_permissions(CapabilityPermission.EX):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            FaultCapIndex.PCC,
            0,
        )
    if not pcc.payload.bounds.contains_cursor(pcc.payload.cursor):
        return _pcc_bounds_fault(core, instruction, pcc.payload.cursor)
    return None


def _check_direct_target(
    core: CoreState,
    instruction: DecodedInstruction,
    target_cell: int,
) -> ExecutionResult | None:
    if not _is_cell_address(target_cell):
        return _pcc_bounds_fault(core, instruction, 0)
    if not core.pcc.payload.bounds.contains_cursor(target_cell):
        return _pcc_bounds_fault(core, instruction, target_cell)
    return None


def _check_entry_capability(
    core: CoreState,
    instruction: DecodedInstruction,
    register_index: int,
    entry_capability: Capability,
) -> ExecutionResult | None:
    fault_cap_idx = _c_index(register_index)
    if entry_capability.is_invalid:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            fault_cap_idx,
            0,
        )
    if entry_capability.is_unsealed or entry_capability.payload.otype != OTYPE_ENTRY:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            fault_cap_idx,
            0,
        )
    if not entry_capability.payload.has_permissions(CapabilityPermission.EX):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            fault_cap_idx,
            0,
        )
    if not entry_capability.payload.bounds.contains_cursor(entry_capability.payload.cursor):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_BOUNDS_FAULT,
            CapCause.BOUNDS,
            fault_cap_idx,
            entry_capability.payload.cursor,
        )
    return None


def _check_protected_push(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
    target_slot: int,
    return_capability: Capability,
) -> ExecutionResult | None:
    rsc = core.special_capabilities.read("RSC")
    if rsc.is_invalid:
        return _return_stack_permission_fault(core, instruction, CapCause.TAG, 0)
    if rsc.is_sealed:
        return _return_stack_permission_fault(core, instruction, CapCause.SEAL_TYPE, 0)
    if not _is_cell_address(target_slot):
        return _return_stack_overflow(core, instruction, 0)
    if target_slot % CAPABILITY_OBJECT_CELLS != 0:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                _instruction_location(core, instruction),
                tval=target_slot,
            )
        )
    if target_slot > ADDRESS_SPACE_CELLS - CAPABILITY_OBJECT_CELLS:
        return _return_stack_overflow(core, instruction, target_slot)
    if not rsc.payload.bounds.contains_range(
        target_slot,
        target_slot + CAPABILITY_OBJECT_CELLS,
    ):
        return _return_stack_overflow(core, instruction, target_slot)
    if not memory.overlaps_protected_range(target_slot, CAPABILITY_OBJECT_CELLS):
        return _return_stack_permission_fault(
            core,
            instruction,
            CapCause.PERMISSION,
            target_slot,
        )
    for permission in (CapabilityPermission.ST, CapabilityPermission.SC):
        if not rsc.payload.has_permissions(permission):
            return _return_stack_permission_fault(
                core,
                instruction,
                CapCause.PERMISSION,
                target_slot,
            )
    if not rsc.payload.has_permissions(CapabilityPermission.SL):
        return _return_stack_permission_fault(
            core,
            instruction,
            CapCause.LOCAL_STORE,
            target_slot,
        )
    if return_capability.is_invalid:
        return _return_stack_permission_fault(core, instruction, CapCause.TAG, target_slot)
    if return_capability.payload.otype != OTYPE_RETURN or return_capability.is_global:
        return _return_stack_permission_fault(
            core,
            instruction,
            CapCause.SEAL_TYPE,
            target_slot,
        )
    return None


def _return_capability(pcc: Capability, continuation: int) -> Capability:
    payload = (
        pcc.payload.with_cursor(continuation)
        .with_otype(OTYPE_RETURN)
        .with_flags(pcc.payload.flags & ~int(CapabilityFlag.G))
    )
    return pcc.with_payload(payload)


def _call_continuation(location: InstructionLocation, size: InstructionSize) -> int:
    size = InstructionSize(size)
    if size is InstructionSize.BITS_48:
        return location.address + 2
    return location.address + 1


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _integer_operands(instruction: DecodedInstruction, count: int) -> tuple[int, ...]:
    if len(instruction.operands) != count:
        raise ValueError("wrong operand count")
    result = []
    for operand in instruction.operands:
        if type(operand) is not int:
            raise TypeError("call operands must be integers")
        result.append(operand)
    return tuple(result)


def _is_cell_address(value: int) -> bool:
    return type(value) is int and 0 <= value < ADDRESS_SPACE_CELLS


def _pcc_bounds_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        CapCause.BOUNDS,
        FaultCapIndex.PCC,
        tval,
    )


def _c_index(index: int) -> FaultCapIndex:
    return FaultCapIndex(0x10 + index)


def _return_stack_overflow(
    core: CoreState,
    instruction: DecodedInstruction,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.RETURN_STACK_OVERFLOW,
        CapCause.BOUNDS,
        FaultCapIndex.RSC,
        tval,
    )


def _return_stack_permission_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    capcause: CapCause,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
        capcause,
        FaultCapIndex.RSC,
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

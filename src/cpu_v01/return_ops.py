"""Protected return-stack pop and `RET` semantics for CPU v0.1.

Owner stories:
- E04-S04: `RET` control-transfer semantics.
- E05-S04: protected return-stack pop transaction.
- E06-S03: sealed return-capability validation.
- E06-S04: protected return-stack access and fault reporting.
- I05-S03: `RET` and protected return-stack pop.
"""

from __future__ import annotations

from .capabilities import Capability, CapabilityPermission, OTYPE_RETURN, OTYPE_UNSEALED
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
from .state import CoreState, SLOT_0, SlottedCapability, SPECIAL_NAME_TO_CCSR_INDEX


RET_MNEMONICS = frozenset({"RET"})


def return_instruction(
    mnemonic: str = "RET",
    *,
    size: InstructionSize = InstructionSize.BITS_12,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(
        mnemonic,
        size,
        location=location,
    )


def execute_return(
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
        return _execute_return_checked(core, memory, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_return_checked(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in RET_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )
    if instruction.operands:
        raise ValueError("RET takes no operands")

    location = _instruction_location(core, instruction)
    if not instruction.size.is_legal_start(location.address, location.slot):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                location,
                tval=location.address,
            )
        )

    rsc = core.special_capabilities.read("RSC")
    target_slot = rsc.payload.cursor
    access_fault = _check_protected_pop_access(core, memory, instruction, target_slot)
    if access_fault is not None:
        return access_fault

    return_capability = memory.clc(target_slot)
    validation_fault = _check_return_capability(
        core,
        instruction,
        target_slot,
        return_capability,
    )
    if validation_fault is not None:
        return validation_fault

    next_rsc = rsc.with_cursor(target_slot + CAPABILITY_OBJECT_CELLS)
    next_pcc = SlottedCapability.from_capability(
        return_capability.with_otype(OTYPE_UNSEALED),
        SLOT_0,
    )
    return instruction.normal_retire(
        ArchitecturalEffects(
            ccsr_writes=((SPECIAL_NAME_TO_CCSR_INDEX["RSC"], next_rsc),),
            pcc_update=next_pcc,
        )
    )


def _check_protected_pop_access(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
    target_slot: int,
) -> ExecutionResult | None:
    rsc = core.special_capabilities.read("RSC")
    if rsc.is_invalid:
        return _return_stack_permission_fault(core, instruction, CapCause.TAG, 0)
    if rsc.is_sealed:
        return _return_stack_permission_fault(core, instruction, CapCause.SEAL_TYPE, 0)
    if not _is_cell_address(target_slot):
        return _return_stack_underflow(core, instruction, CapCause.BOUNDS, 0)
    if target_slot % CAPABILITY_OBJECT_CELLS != 0:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                _instruction_location(core, instruction),
                tval=target_slot,
            )
        )
    if target_slot > ADDRESS_SPACE_CELLS - CAPABILITY_OBJECT_CELLS:
        return _return_stack_underflow(core, instruction, CapCause.BOUNDS, target_slot)
    if not rsc.payload.bounds.contains_range(
        target_slot,
        target_slot + CAPABILITY_OBJECT_CELLS,
    ):
        return _return_stack_underflow(core, instruction, CapCause.BOUNDS, target_slot)
    next_cursor = target_slot + CAPABILITY_OBJECT_CELLS
    if not _is_cell_address(next_cursor) or not rsc.payload.bounds.contains_cursor(next_cursor):
        return _return_stack_underflow(core, instruction, CapCause.BOUNDS, target_slot)
    if not memory.overlaps_protected_range(target_slot, CAPABILITY_OBJECT_CELLS):
        return _return_stack_permission_fault(
            core,
            instruction,
            CapCause.PERMISSION,
            target_slot,
        )
    for permission in (CapabilityPermission.LD, CapabilityPermission.LC):
        if not rsc.payload.has_permissions(permission):
            return _return_stack_permission_fault(
                core,
                instruction,
                CapCause.PERMISSION,
                target_slot,
            )
    return None


def _check_return_capability(
    core: CoreState,
    instruction: DecodedInstruction,
    target_slot: int,
    return_capability: Capability,
) -> ExecutionResult | None:
    if return_capability.is_invalid:
        return _return_stack_underflow(core, instruction, CapCause.TAG, target_slot)
    if (
        return_capability.is_unsealed
        or return_capability.payload.otype != OTYPE_RETURN
        or return_capability.is_global
    ):
        return _return_stack_underflow(
            core,
            instruction,
            CapCause.SEAL_TYPE,
            target_slot,
        )
    if not return_capability.payload.has_permissions(CapabilityPermission.EX):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            FaultCapIndex.RSC,
            target_slot,
        )
    if not return_capability.payload.bounds.contains_cursor(return_capability.payload.cursor):
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_BOUNDS_FAULT,
            CapCause.BOUNDS,
            FaultCapIndex.RSC,
            return_capability.payload.cursor,
        )
    return None


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _is_cell_address(value: int) -> bool:
    return type(value) is int and 0 <= value < ADDRESS_SPACE_CELLS


def _return_stack_underflow(
    core: CoreState,
    instruction: DecodedInstruction,
    capcause: CapCause,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.RETURN_STACK_UNDERFLOW,
        capcause,
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

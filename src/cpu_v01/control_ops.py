"""Control and trap-return instruction semantics for CPU v0.1.

Owner stories:
- E04-S04: `IRET`, `EPCCRD`, and `EPCCWR` control-transfer semantics.
- E07-S06: one-level trap state and slot-aware `EPCC` restore.
- I04-S03: trap return and slot-aware `EPCC` helpers.
"""

from __future__ import annotations

from . import csrs
from .capabilities import CapabilityPermission
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
from .state import (
    CoreState,
    SlottedCapability,
    require_general_capability_register_index,
    require_integer_register_index,
)


TRAP_RETURN_MNEMONICS = frozenset({"IRET", "EPCCRD", "EPCCWR"})


def control_instruction(
    mnemonic: str,
    operands: tuple[object, ...] = (),
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


def execute_control(core: CoreState, instruction: DecodedInstruction) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_control_checked(core, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_control_checked(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    mnemonic = instruction.mnemonic
    if mnemonic not in TRAP_RETURN_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    if not _is_kernel(core):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.PRIVILEGE_FAULT,
                _instruction_location(core, instruction),
            )
        )

    if mnemonic == "EPCCRD":
        cd, dd = _operands(instruction, 2)
        cd = require_general_capability_register_index(cd)
        dd = require_integer_register_index(dd)
        epcc = core.epcc
        return instruction.normal_retire(
            ArchitecturalEffects(
                integer_writes=((dd, epcc.slot),),
                capability_writes=((cd, epcc.without_slot()),),
            )
        )

    if mnemonic == "EPCCWR":
        cs, ds = _operands(instruction, 2)
        cs = require_general_capability_register_index(cs)
        ds = require_integer_register_index(ds)
        epcc = SlottedCapability.from_capability(core.read_c(cs), core.read_d(ds) & 1)
        return instruction.normal_retire(ArchitecturalEffects(epcc_update=epcc))

    if mnemonic == "IRET":
        fault = _iret_fault(core, instruction)
        if fault is not None:
            return fault
        return instruction.normal_retire(
            ArchitecturalEffects(
                csr_writes=((csrs.CSR_SR, _iret_sr(core.read_csr(csrs.CSR_SR))),),
                pcc_update=core.epcc,
            )
        )

    raise AssertionError(f"unhandled control mnemonic {mnemonic}")


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
            raise TypeError("control instruction operands must be register indices")
        result.append(operand)
    return tuple(result)


def _is_kernel(core: CoreState) -> bool:
    return bool(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_PRIV_BIT))


def _iret_fault(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult | None:
    epcc = core.epcc
    capability = epcc.without_slot()
    if capability.is_invalid:
        return _epcc_capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            0,
        )
    if capability.is_sealed:
        return _epcc_capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            0,
        )
    if not capability.payload.has_permissions(CapabilityPermission.EX):
        return _epcc_capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            CapCause.PERMISSION,
            0,
        )
    if not capability.payload.bounds.contains_cursor(capability.payload.cursor):
        return _epcc_capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_BOUNDS_FAULT,
            CapCause.BOUNDS,
            capability.payload.cursor,
        )
    return None


def _epcc_capability_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    cause: ExceptionCause,
    capcause: CapCause,
    tval: int,
) -> ExecutionResult:
    return instruction.fault(
        FaultPacket(
            cause,
            _instruction_location(core, instruction),
            tval=tval,
            capcause=capcause,
            fault_cap_idx=FaultCapIndex.EPCC,
        )
    )


def _iret_sr(old_sr: int) -> int:
    value = old_sr
    value = _set_bit(value, csrs.SR_IE_BIT, _bit(old_sr, csrs.SR_PIE_BIT))
    value = _set_bit(value, csrs.SR_PRIV_BIT, _bit(old_sr, csrs.SR_PPRIV_BIT))
    value = _set_bit(value, csrs.SR_EXL_BIT, False)
    return value


def _bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))


def _set_bit(value: int, bit: int, enabled: bool) -> int:
    mask = 1 << bit
    if enabled:
        return value | mask
    return value & ~mask

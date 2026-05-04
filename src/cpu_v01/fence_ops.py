"""Fence and local translation-maintenance instruction semantics for CPU v0.1.

Owner stories:
- E08-S04: `FENCE`, `FENCE.I`, and `SFENCE.VM` forms.
- E09-S03: local TLB invalidation effects.
- I06-S02: TLBs and `SFENCE.VM` forms.
"""

from __future__ import annotations

from . import csrs
from .instructions import (
    ArchitecturalEffects,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .state import CoreState, require_integer_register_index
from .tlb import TlbInvalidateEffect, TlbInvalidateKind


FENCE_MNEMONICS = frozenset(
    {
        "FENCE",
        "FENCE.I",
        "SFENCE.VM",
        "SFENCE.VM.ASID",
        "SFENCE.VM.VA",
        "SFENCE.VM.VA_ASID",
    }
)


def fence_instruction(
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


def execute_fence(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_fence_checked(core, instruction)
    except (IndexError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_fence_checked(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in FENCE_MNEMONICS:
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

    if instruction.mnemonic == "FENCE":
        _operands(instruction, 0)
        return instruction.normal_retire()

    if not _is_kernel_mode(core):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.PRIVILEGE_FAULT,
                location,
            )
        )

    if instruction.mnemonic == "FENCE.I":
        _operands(instruction, 0)
        return instruction.normal_retire()
    if instruction.mnemonic == "SFENCE.VM":
        _operands(instruction, 0)
        return _tlb_retire(instruction, TlbInvalidateEffect(TlbInvalidateKind.ALL))
    if instruction.mnemonic == "SFENCE.VM.ASID":
        (da,) = _operands(instruction, 1)
        asid = core.read_d(da) & csrs.SATP_ASID_MASK
        return _tlb_retire(
            instruction,
            TlbInvalidateEffect(TlbInvalidateKind.ASID, asid=asid),
        )
    if instruction.mnemonic == "SFENCE.VM.VA":
        (dv,) = _operands(instruction, 1)
        return _tlb_retire(
            instruction,
            TlbInvalidateEffect(TlbInvalidateKind.VA, virtual_address=core.read_d(dv)),
        )
    if instruction.mnemonic == "SFENCE.VM.VA_ASID":
        dv, da = _operands(instruction, 2)
        asid = core.read_d(da) & csrs.SATP_ASID_MASK
        return _tlb_retire(
            instruction,
            TlbInvalidateEffect(
                TlbInvalidateKind.VA_ASID,
                virtual_address=core.read_d(dv),
                asid=asid,
            ),
        )
    raise AssertionError(f"unhandled fence mnemonic {instruction.mnemonic}")


def _tlb_retire(
    instruction: DecodedInstruction,
    effect: TlbInvalidateEffect,
) -> ExecutionResult:
    return instruction.normal_retire(ArchitecturalEffects(tlb_effects=(effect,)))


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
            raise TypeError("fence operands must be integer register indices")
        result.append(require_integer_register_index(operand))
    return tuple(result)


def _is_kernel_mode(core: CoreState) -> bool:
    return bool(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_PRIV_BIT))

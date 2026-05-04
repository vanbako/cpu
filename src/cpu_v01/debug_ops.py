"""Non-monitor debug halt and single-step helpers for CPU v0.1.

Owner stories:
- E12-S01: breakpoint debug halt, halt request, and resume behavior.
- E12-S03: single-step arm state and completion event.
- E12-S04: mandatory counter suppression while debug-halted.
- I04-S04: non-monitor debug halt and single-step baseline.
"""

from __future__ import annotations

from . import csrs
from .execution import commit_normal_result
from .instructions import (
    CapCause,
    DebugCause,
    DebugEventPacket,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    ExecutionResultKind,
    FaultCapIndex,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .memory import TaggedMemory
from .state import CoreLifecycle, CoreState


DEBUG_MNEMONICS = frozenset({"BRK"})


def debug_instruction(
    mnemonic: str,
    *,
    size: InstructionSize = InstructionSize.BITS_12,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(mnemonic, size, location=location)


def execute_debug(core: CoreState, instruction: DecodedInstruction) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_debug_checked(core, instruction)
    except (TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def write_debugctl(core: CoreState, value: int) -> None:
    """Apply a software/debug write to the modeled `DEBUGCTL` CSR fields."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    value = csrs.require_uint(value, csrs.CSR_BITS, "DEBUGCTL")
    if value & csrs.DEBUGCTL_RESERVED_MASK:
        raise ValueError("DEBUGCTL reserved bits must be zero")

    current = core.read_csr(csrs.CSR_DEBUGCTL)
    new_value = current
    for bit in (
        csrs.DEBUGCTL_BRKHALT_BIT,
        csrs.DEBUGCTL_MONITOR_BIT,
        csrs.DEBUGCTL_STEP_BIT,
    ):
        new_value = _set_bit(new_value, bit, _bit(value, bit))

    if value & (1 << csrs.DEBUGCTL_HALTREQ_BIT):
        new_value |= 1 << csrs.DEBUGCTL_HALTREQ_BIT

    if not _bit(new_value, csrs.DEBUGCTL_STEP_BIT):
        core.step_active = False

    core.write_csr_raw(csrs.CSR_DEBUGCTL, new_value)
    if value & (1 << csrs.DEBUGCTL_RESUME_BIT):
        resume_debug_halted(core)


def request_halt(core: CoreState) -> None:
    write_debugctl(core, 1 << csrs.DEBUGCTL_HALTREQ_BIT)


def accept_halt_request(core: CoreState) -> ExecutionResult | None:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not _debugctl_bit(core, csrs.DEBUGCTL_HALTREQ_BIT):
        return None
    packet = DebugEventPacket(
        DebugCause.HALTREQ,
        InstructionLocation(core.pcc),
        tval=0,
    )
    return enter_debug_halt(core, packet)


def enter_debug_halt_from_result(
    core: CoreState,
    result: ExecutionResult,
) -> ExecutionResult:
    if not isinstance(result, ExecutionResult):
        raise TypeError("result must be an ExecutionResult")
    if result.kind is not ExecutionResultKind.DEBUG_EVENT:
        raise ValueError("only debug-event results can enter debug halt")
    assert result.debug_packet is not None
    return enter_debug_halt(core, result.debug_packet)


def enter_debug_halt(
    core: CoreState,
    packet: DebugEventPacket,
) -> ExecutionResult:
    """Enter non-monitor `DEBUG_HALTED` for an accepted debug event."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(packet, DebugEventPacket):
        raise TypeError("packet must be a DebugEventPacket")

    core.lifecycle = CoreLifecycle.DEBUG_HALTED
    core.step_active = False
    debugctl = core.read_csr(csrs.CSR_DEBUGCTL)
    debugctl &= ~(1 << csrs.DEBUGCTL_HALTREQ_BIT)
    debugctl |= 1 << csrs.DEBUGCTL_HALTED_BIT
    debugctl = _with_dcause(debugctl, packet.dcause)
    core.write_csr_raw(csrs.CSR_DEBUGCTL, debugctl)
    core.write_csr_raw(csrs.CSR_CAUSE, int(ExceptionCause.DEBUG_HALT))
    core.write_csr_raw(csrs.CSR_TVAL, packet.tval)
    core.write_csr_raw(csrs.CSR_CAPCAUSE, int(CapCause.NONE))
    core.write_csr_raw(csrs.CSR_FAULTCAPIDX, int(FaultCapIndex.NONE))
    return ExecutionResult.debug_event(
        DecodedInstruction("DEBUGHALT", InstructionSize.BITS_12, location=packet.location),
        packet,
    )


def resume_debug_halted(core: CoreState) -> None:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if core.lifecycle is not CoreLifecycle.DEBUG_HALTED:
        raise ValueError("core is not DEBUG_HALTED")
    debugctl = core.read_csr(csrs.CSR_DEBUGCTL)
    debugctl &= ~(1 << csrs.DEBUGCTL_HALTED_BIT)
    debugctl &= ~(1 << csrs.DEBUGCTL_HALTREQ_BIT)
    core.write_csr_raw(csrs.CSR_DEBUGCTL, debugctl)
    core.lifecycle = CoreLifecycle.RUNNING
    core.step_active = _debugctl_bit(core, csrs.DEBUGCTL_STEP_BIT)


def commit_normal_result_with_debug(
    core: CoreState,
    result: ExecutionResult,
    memory: TaggedMemory | None = None,
) -> ExecutionResult | None:
    """Commit a normal result and accept a post-retire step event if armed."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if core.lifecycle is CoreLifecycle.DEBUG_HALTED:
        raise RuntimeError("DEBUG_HALTED cores do not retire ordinary instructions")
    if not isinstance(result, ExecutionResult):
        raise TypeError("result must be an ExecutionResult")
    if result.kind is not ExecutionResultKind.NORMAL_RETIRE:
        if result.is_fault or result.is_debug_event:
            core.step_active = False
        raise ValueError("only normal-retire results can be committed here")
    if result.instruction.location is None:
        raise ValueError("single-step accounting requires an instruction location")

    step_completion = _step_completion_eligible(core)
    tval = result.instruction.location.address
    commit_normal_result(core, result, memory)
    if step_completion:
        return enter_debug_halt(
            core,
            DebugEventPacket(
                DebugCause.SINGLE_STEP,
                InstructionLocation(core.pcc),
                tval=tval,
            ),
        )
    if result.instruction.mnemonic == "IRET":
        _arm_step_if_returned_context(core)
    return None


def tick_cycle(core: CoreState, count: int = 1) -> None:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    count = csrs.require_uint(count, csrs.CSR_BITS, "count")
    if core.lifecycle is CoreLifecycle.DEBUG_HALTED:
        return
    next_cycle = (core.read_csr(csrs.CSR_CYCLE) + count) & csrs.CSR_MASK
    core.write_csr_raw(csrs.CSR_CYCLE, next_cycle)


def dcause(core: CoreState) -> DebugCause:
    value = core.read_csr(csrs.CSR_DEBUGCTL)
    return DebugCause((value & csrs.DEBUGCTL_DCAUSE_MASK) >> csrs.DEBUGCTL_DCAUSE_SHIFT)


def _execute_debug_checked(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in DEBUG_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    if instruction.mnemonic == "BRK":
        location = _instruction_location(core, instruction)
        if _debugctl_bit(core, csrs.DEBUGCTL_BRKHALT_BIT):
            return instruction.debug_event(
                DebugEventPacket(DebugCause.BRK, location, tval=location.address)
            )
        return instruction.fault(
            FaultPacket(
                ExceptionCause.BREAKPOINT,
                location,
                tval=location.address,
            )
        )

    raise AssertionError(f"unhandled debug mnemonic {instruction.mnemonic}")


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _step_completion_eligible(core: CoreState) -> bool:
    return (
        core.step_active
        and core.lifecycle is not CoreLifecycle.DEBUG_HALTED
        and not (core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_EXL_BIT))
    )


def _arm_step_if_returned_context(core: CoreState) -> None:
    if (
        _debugctl_bit(core, csrs.DEBUGCTL_STEP_BIT)
        and core.lifecycle is not CoreLifecycle.DEBUG_HALTED
        and not (core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_EXL_BIT))
    ):
        core.step_active = True


def _debugctl_bit(core: CoreState, bit: int) -> bool:
    return _bit(core.read_csr(csrs.CSR_DEBUGCTL), bit)


def _with_dcause(value: int, dcause: DebugCause) -> int:
    value &= ~csrs.DEBUGCTL_DCAUSE_MASK
    return value | (int(DebugCause(dcause)) << csrs.DEBUGCTL_DCAUSE_SHIFT)


def _bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))


def _set_bit(value: int, bit: int, enabled: bool) -> int:
    mask = 1 << bit
    if enabled:
        return value | mask
    return value & ~mask

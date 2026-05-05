"""Minimal firmware/kernel handler fixtures for CPU v0.1.

Owner stories:
- E07-S05: vectored timer/software/external interrupt delivery.
- E07-S06: software trap frames and slot-aware `IRET` return.
- I09-S01: trap-frame ABI supplement.
- I09-S03: syscall ABI supplement.
- I14-S02: minimal trap, syscall, and timer handler fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from . import abi, control_ops, csrs, execution, program, state, traps
from .instructions import (
    CapCause,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultCapIndex,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)


INTERRUPT_CAUSE_FLAG = 1 << 47
INTERRUPT_SOURCE_MASK = 0x7


class InterruptSource(Enum):
    TIMER = "TIMER"
    SOFTWARE_IPI = "SOFTWARE_IPI"
    EXTERNAL = "EXTERNAL"

    @property
    def bit(self) -> int:
        return {
            InterruptSource.TIMER: 0,
            InterruptSource.SOFTWARE_IPI: 1,
            InterruptSource.EXTERNAL: 2,
        }[self]

    @property
    def cause_code(self) -> int:
        return {
            InterruptSource.TIMER: 0x0001,
            InterruptSource.SOFTWARE_IPI: 0x0002,
            InterruptSource.EXTERNAL: 0x0003,
        }[self]

    @property
    def cause_value(self) -> int:
        return INTERRUPT_CAUSE_FLAG | self.cause_code

    @property
    def vector_index(self) -> int:
        return {
            InterruptSource.TIMER: 1,
            InterruptSource.SOFTWARE_IPI: 2,
            InterruptSource.EXTERNAL: 3,
        }[self]


INTERRUPT_PRIORITY = (
    InterruptSource.EXTERNAL,
    InterruptSource.SOFTWARE_IPI,
    InterruptSource.TIMER,
)


class InterruptEntryKind(Enum):
    ENTERED = "ENTERED"
    NOT_DELIVERABLE = "NOT_DELIVERABLE"
    FATAL_DELIVERY_FAILURE = "FATAL_DELIVERY_FAILURE"


@dataclass(frozen=True)
class InterruptEntryResult:
    kind: InterruptEntryKind
    source: InterruptSource | None
    cause_value: int = 0
    vector_pcc: state.SlottedCapability | None = None
    failure: traps.TrapEntryFailure | None = None

    @property
    def entered(self) -> bool:
        return self.kind is InterruptEntryKind.ENTERED

    @property
    def fatal(self) -> bool:
        return self.kind is InterruptEntryKind.FATAL_DELIVERY_FAILURE


@dataclass(frozen=True)
class SoftwareTrapFrame:
    epcc: state.SlottedCapability
    sr: int
    cause: int
    tval: int
    capcause: CapCause
    fault_cap_idx: FaultCapIndex

    def __post_init__(self) -> None:
        if not isinstance(self.epcc, state.SlottedCapability):
            raise TypeError("epcc must be a SlottedCapability")
        object.__setattr__(self, "sr", csrs.require_uint(self.sr, csrs.CSR_BITS, "sr"))
        object.__setattr__(
            self,
            "cause",
            csrs.require_uint(self.cause, csrs.CSR_BITS, "cause"),
        )
        object.__setattr__(
            self,
            "tval",
            csrs.require_uint(self.tval, csrs.CSR_BITS, "tval"),
        )
        object.__setattr__(self, "capcause", CapCause(self.capcause))
        object.__setattr__(self, "fault_cap_idx", FaultCapIndex(self.fault_cap_idx))


@dataclass(frozen=True)
class SyscallFixtureReport:
    trap_entry: traps.TrapEntryResult
    saved_frame: SoftwareTrapFrame
    service_number: int
    integer_arguments: tuple[int, ...]
    capability_argument_tags: tuple[bool, ...]
    return_d0: int
    return_d1: int
    final_pcc: state.SlottedCapability
    final_sr: int
    iret_result: ExecutionResult


@dataclass(frozen=True)
class TimerFixtureReport:
    interrupt_entry: InterruptEntryResult
    saved_frame: SoftwareTrapFrame
    old_timecmp: int
    new_timecmp: int
    final_pcc: state.SlottedCapability
    final_sr: int
    iret_result: ExecutionResult


def save_trap_frame(core: state.CoreState) -> SoftwareTrapFrame:
    """Capture the minimum software trap frame from the hardware saved level."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    return SoftwareTrapFrame(
        epcc=core.epcc,
        sr=core.read_csr(csrs.CSR_SR),
        cause=core.read_csr(csrs.CSR_CAUSE),
        tval=core.read_csr(csrs.CSR_TVAL),
        capcause=core.read_csr(csrs.CSR_CAPCAUSE),
        fault_cap_idx=core.read_csr(csrs.CSR_FAULTCAPIDX),
    )


def restore_frame_for_iret(core: state.CoreState, frame: SoftwareTrapFrame) -> None:
    """Restore the one hardware saved level before executing `IRET`."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(frame, SoftwareTrapFrame):
        raise TypeError("frame must be a SoftwareTrapFrame")
    core.install_epcc(frame.epcc)
    core.write_csr_raw(csrs.CSR_CAUSE, frame.cause)
    core.write_csr_raw(csrs.CSR_TVAL, frame.tval)
    core.write_csr_raw(csrs.CSR_CAPCAUSE, int(frame.capcause))
    core.write_csr_raw(csrs.CSR_FAULTCAPIDX, int(frame.fault_cap_idx))
    core.write_csr_raw(csrs.CSR_SR, frame.sr)


def execute_iret(core: state.CoreState) -> ExecutionResult:
    """Execute and commit the architectural `IRET` instruction."""
    result = control_ops.execute_control(core, control_ops.control_instruction("IRET"))
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


def enter_syscall_from_current_pcc(
    core: state.CoreState,
    *,
    size: InstructionSize = InstructionSize.BITS_12,
) -> traps.TrapEntryResult:
    """Raise a precise `SYS` trap at the current `PCC`."""
    instruction = DecodedInstruction(
        abi.SYSCALL_CANONICAL_MNEMONIC,
        size,
        location=InstructionLocation(core.pcc),
    )
    result = instruction.fault(
        FaultPacket(ExceptionCause.SYSCALL_TRAP, instruction.location)
    )
    return traps.enter_trap_from_result(core, result)


def run_syscall_handler_fixture(
    core: state.CoreState,
    *,
    syscall_size: InstructionSize = InstructionSize.BITS_12,
) -> SyscallFixtureReport:
    """Run the minimal syscall handler and return through `IRET`."""
    trap_entry = enter_syscall_from_current_pcc(core, size=syscall_size)
    if not trap_entry.entered:
        raise RuntimeError("SYS trap did not enter TVC")
    frame = save_trap_frame(core)
    service = core.read_d(abi.SYSCALL_SERVICE_REGISTER)
    integer_arguments = tuple(core.read_d(index) for index in abi.SYSCALL_INTEGER_ARGUMENT_REGS)
    capability_argument_tags = tuple(
        core.read_c(index).is_valid for index in abi.SYSCALL_CAPABILITY_ARGUMENT_REGS
    )
    core.write_d(0, service)
    core.write_d(1, sum(integer_arguments) & csrs.CSR_MASK)

    return_frame = replace(
        frame,
        epcc=program.sequential_pcc(frame.epcc, syscall_size),
    )
    restore_frame_for_iret(core, return_frame)
    iret_result = execute_iret(core)
    return SyscallFixtureReport(
        trap_entry=trap_entry,
        saved_frame=frame,
        service_number=service,
        integer_arguments=integer_arguments,
        capability_argument_tags=capability_argument_tags,
        return_d0=core.read_d(0),
        return_d1=core.read_d(1),
        final_pcc=core.pcc,
        final_sr=core.read_csr(csrs.CSR_SR),
        iret_result=iret_result,
    )


def effective_pending_mask(
    core: state.CoreState,
    *,
    external_pending: bool = False,
) -> int:
    """Return the mandatory low interrupt pending bits, including timer level."""
    pending = core.read_csr(csrs.CSR_IPENDING) & INTERRUPT_SOURCE_MASK
    if core.read_csr(csrs.CSR_TIMER) >= core.read_csr(csrs.CSR_TIMECMP):
        pending |= 1 << InterruptSource.TIMER.bit
    if external_pending:
        pending |= 1 << InterruptSource.EXTERNAL.bit
    return pending


def selected_interrupt_source(
    core: state.CoreState,
    *,
    external_pending: bool = False,
) -> InterruptSource | None:
    if not _interrupt_delivery_enabled(core):
        return None
    deliverable = (
        effective_pending_mask(core, external_pending=external_pending)
        & core.read_csr(csrs.CSR_IENABLE)
        & INTERRUPT_SOURCE_MASK
    )
    for source in INTERRUPT_PRIORITY:
        if deliverable & (1 << source.bit):
            return source
    return None


def enter_pending_interrupt(
    core: state.CoreState,
    *,
    external_pending: bool = False,
) -> InterruptEntryResult:
    """Deliver the highest-priority pending mandatory interrupt, if any."""
    source = selected_interrupt_source(core, external_pending=external_pending)
    if source is None:
        return InterruptEntryResult(InterruptEntryKind.NOT_DELIVERABLE, None)

    tvc = core.special_capabilities.read("TVC")
    vector_cell = tvc.payload.cursor + source.vector_index * _vector_stride(core)
    failure = _interrupt_vector_failure(core, vector_cell)
    if failure is not None:
        return InterruptEntryResult(
            InterruptEntryKind.FATAL_DELIVERY_FAILURE,
            source,
            source.cause_value,
            failure=failure,
        )

    vector_pcc = state.SlottedCapability.from_capability(
        tvc.with_cursor(vector_cell),
        state.SLOT_0,
    )
    old_sr = core.read_csr(csrs.CSR_SR)
    core.reservation.clear()
    core.install_epcc(core.pcc)
    core.write_csr_raw(csrs.CSR_CAUSE, source.cause_value)
    core.write_csr_raw(csrs.CSR_TVAL, 0)
    core.write_csr_raw(csrs.CSR_CAPCAUSE, int(CapCause.NONE))
    core.write_csr_raw(csrs.CSR_FAULTCAPIDX, int(FaultCapIndex.NONE))
    core.write_csr_raw(csrs.CSR_SR, _entry_sr(old_sr))
    core.install_pcc(vector_pcc)
    return InterruptEntryResult(
        InterruptEntryKind.ENTERED,
        source,
        source.cause_value,
        vector_pcc,
    )


def run_timer_handler_fixture(
    core: state.CoreState,
    *,
    next_timecmp: int,
) -> TimerFixtureReport:
    """Deliver a timer interrupt, program the next deadline, and return with `IRET`."""
    old_timecmp = core.read_csr(csrs.CSR_TIMECMP)
    entry = enter_pending_interrupt(core)
    if not entry.entered or entry.source is not InterruptSource.TIMER:
        raise RuntimeError("timer interrupt was not delivered")
    frame = save_trap_frame(core)
    core.write_csr_raw(csrs.CSR_TIMECMP, next_timecmp)
    restore_frame_for_iret(core, frame)
    iret_result = execute_iret(core)
    return TimerFixtureReport(
        interrupt_entry=entry,
        saved_frame=frame,
        old_timecmp=old_timecmp,
        new_timecmp=core.read_csr(csrs.CSR_TIMECMP),
        final_pcc=core.pcc,
        final_sr=core.read_csr(csrs.CSR_SR),
        iret_result=iret_result,
    )


def _interrupt_delivery_enabled(core: state.CoreState) -> bool:
    sr = core.read_csr(csrs.CSR_SR)
    return bool(sr & (1 << csrs.SR_IE_BIT)) and not bool(sr & (1 << csrs.SR_EXL_BIT))


def _vector_stride(core: state.CoreState) -> int:
    vshift = core.read_csr(csrs.CSR_TVEC) & 0xF
    return 4 << vshift


def _interrupt_vector_failure(
    core: state.CoreState,
    vector_cell: int,
) -> traps.TrapEntryFailure | None:
    tvc = core.special_capabilities.read("TVC")
    base_failure = traps._tvc_delivery_failure(tvc)
    if base_failure is not None:
        return base_failure
    if not 0 <= vector_cell < (1 << 48):
        return traps.TrapEntryFailure(CapCause.BOUNDS, tval=0)
    if not tvc.payload.bounds.contains_cursor(vector_cell):
        return traps.TrapEntryFailure(CapCause.BOUNDS, tval=vector_cell)
    return None


def _entry_sr(old_sr: int) -> int:
    value = old_sr
    value = _set_bit(value, csrs.SR_PIE_BIT, _bit(old_sr, csrs.SR_IE_BIT))
    value = _set_bit(value, csrs.SR_IE_BIT, False)
    value = _set_bit(value, csrs.SR_PPRIV_BIT, _bit(old_sr, csrs.SR_PRIV_BIT))
    value = _set_bit(value, csrs.SR_PRIV_BIT, True)
    value = _set_bit(value, csrs.SR_EXL_BIT, True)
    return value


def _bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))


def _set_bit(value: int, bit: int, enabled: bool) -> int:
    mask = 1 << bit
    if enabled:
        return value | mask
    return value & ~mask

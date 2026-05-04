"""Direct synchronous trap-entry helpers for CPU v0.1.

Owner stories:
- E07-S02: exception cause and capability-reporting values.
- E07-S04: direct exception trap entry through TVC.
- I04-S02: fault packets and direct trap entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import csrs
from .capabilities import Capability, CapabilityPermission
from .instructions import (
    CapCause,
    ExceptionCause,
    ExecutionResult,
    ExecutionResultKind,
    FaultCapIndex,
    FaultPacket,
)
from .state import CoreState, SLOT_0, SlottedCapability


CAPABILITY_REPORTING_CAUSES = frozenset(
    {
        ExceptionCause.CAPABILITY_TAG_FAULT,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        ExceptionCause.CAPABILITY_PERMISSION_FAULT,
        ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
        ExceptionCause.CAPABILITY_LOCAL_STORE_FAULT,
        ExceptionCause.RETURN_STACK_UNDERFLOW,
        ExceptionCause.RETURN_STACK_OVERFLOW,
        ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
    }
)


class TrapEntryKind(Enum):
    """Outcome classes for attempting to deliver a synchronous trap."""

    ENTERED = "ENTERED"
    FATAL_DELIVERY_FAILURE = "FATAL_DELIVERY_FAILURE"


@dataclass(frozen=True)
class TrapEntryFailure:
    """Diagnostic packet for an undeliverable trap due to invalid `TVC`."""

    capcause: CapCause
    fault_cap_idx: FaultCapIndex = FaultCapIndex.TVC
    tval: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "capcause", CapCause(self.capcause))
        object.__setattr__(self, "fault_cap_idx", FaultCapIndex(self.fault_cap_idx))
        object.__setattr__(self, "tval", self.tval)


@dataclass(frozen=True)
class TrapEntryResult:
    """Result of direct synchronous trap entry."""

    kind: TrapEntryKind
    original_packet: FaultPacket
    failure: TrapEntryFailure | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", TrapEntryKind(self.kind))
        if not isinstance(self.original_packet, FaultPacket):
            raise TypeError("original_packet must be a FaultPacket")
        if self.kind is TrapEntryKind.ENTERED and self.failure is not None:
            raise ValueError("successful trap entry cannot carry a failure packet")
        if self.kind is TrapEntryKind.FATAL_DELIVERY_FAILURE and not isinstance(
            self.failure,
            TrapEntryFailure,
        ):
            raise TypeError("fatal trap delivery requires a TrapEntryFailure")

    @property
    def entered(self) -> bool:
        return self.kind is TrapEntryKind.ENTERED

    @property
    def fatal(self) -> bool:
        return self.kind is TrapEntryKind.FATAL_DELIVERY_FAILURE


def enter_trap_from_result(core: CoreState, result: ExecutionResult) -> TrapEntryResult:
    """Deliver a fault `ExecutionResult` through direct trap entry."""
    if not isinstance(result, ExecutionResult):
        raise TypeError("result must be an ExecutionResult")
    if result.kind is not ExecutionResultKind.FAULT:
        raise ValueError("only fault results can enter the synchronous trap path")
    assert result.fault_packet is not None
    return enter_trap(core, result.fault_packet)


def enter_trap(core: CoreState, packet: FaultPacket) -> TrapEntryResult:
    """Attempt direct synchronous trap entry for a precise fault packet."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(packet, FaultPacket):
        raise TypeError("packet must be a FaultPacket")

    tvc = core.special_capabilities.read("TVC")
    failure = _tvc_delivery_failure(tvc)
    if failure is not None:
        return TrapEntryResult(
            TrapEntryKind.FATAL_DELIVERY_FAILURE,
            packet,
            failure=failure,
        )

    old_sr = core.read_csr(csrs.CSR_SR)
    core.install_epcc(packet.faulting_location.pcc)
    core.write_csr_raw(csrs.CSR_CAUSE, int(ExceptionCause(packet.cause)))
    core.write_csr_raw(csrs.CSR_TVAL, packet.tval)
    capcause, fault_cap_idx = _capability_reporting(packet)
    core.write_csr_raw(csrs.CSR_CAPCAUSE, int(capcause))
    core.write_csr_raw(csrs.CSR_FAULTCAPIDX, int(fault_cap_idx))
    core.write_csr_raw(csrs.CSR_SR, _trap_entry_sr(old_sr))
    core.install_pcc(SlottedCapability.from_capability(tvc, SLOT_0))
    return TrapEntryResult(TrapEntryKind.ENTERED, packet)


def _capability_reporting(packet: FaultPacket) -> tuple[CapCause, FaultCapIndex]:
    if packet.cause in CAPABILITY_REPORTING_CAUSES:
        return packet.capcause, packet.fault_cap_idx
    return CapCause.NONE, FaultCapIndex.NONE


def _tvc_delivery_failure(tvc: Capability) -> TrapEntryFailure | None:
    if not isinstance(tvc, Capability):
        raise TypeError("TVC must be a Capability")
    if tvc.is_invalid:
        return TrapEntryFailure(CapCause.TAG, tval=tvc.payload.cursor)
    if tvc.is_sealed:
        return TrapEntryFailure(CapCause.SEAL_TYPE, tval=tvc.payload.cursor)
    if not tvc.payload.has_permissions(CapabilityPermission.EX):
        return TrapEntryFailure(CapCause.PERMISSION, tval=tvc.payload.cursor)
    if not tvc.payload.bounds.contains_cursor(tvc.payload.cursor):
        return TrapEntryFailure(CapCause.BOUNDS, tval=tvc.payload.cursor)
    return None


def _trap_entry_sr(old_sr: int) -> int:
    old_ie = _bit(old_sr, csrs.SR_IE_BIT)
    old_priv = _bit(old_sr, csrs.SR_PRIV_BIT)
    value = old_sr
    value = _set_bit(value, csrs.SR_PIE_BIT, old_ie)
    value = _set_bit(value, csrs.SR_IE_BIT, False)
    value = _set_bit(value, csrs.SR_PPRIV_BIT, old_priv)
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

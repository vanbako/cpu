"""CPU-side endpoint event and interrupt-routing fixtures for CPU v0.1.

Owner stories:
- E07-S05: vectored timer/software/external interrupt delivery.
- E11-S03: secondary-core startup.
- I14-S03: firmware-controlled secondary-core startup demo.
- I18-S04: scheduler-compatible timer interrupt handling.
- I19-S01: CPU external endpoint and fabric attachment boundary.
- I19-S02: endpoint event, IPI, and interrupt routing fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import MutableMapping, Sequence

from . import csrs, firmware, kernel, platform, state, startup
from .instructions import ExecutionResult


EVENT_CODE_FABRIC_NOTIFY = 0x1902
TIMER_ROUTE_NOW = 0x1902_0000
TIMER_ACK_DELTA = 0x40
ALL_INTERRUPT_SOURCES = (
    kernel.InterruptSource.TIMER,
    kernel.InterruptSource.SOFTWARE_IPI,
    kernel.InterruptSource.EXTERNAL,
)


class EndpointIngress(Enum):
    """Topology-neutral CPU-side event ingress identifiers."""

    LEFT_PEER = "LEFT_PEER"
    RIGHT_PEER = "RIGHT_PEER"
    FABRIC0 = "FABRIC0"
    FABRIC1 = "FABRIC1"


class EndpointEventKind(Enum):
    FABRIC_EXTERNAL = "FABRIC_EXTERNAL"


@dataclass(frozen=True)
class EndpointEvent:
    target_coreid: int
    ingress: EndpointIngress
    event_code: int
    kind: EndpointEventKind = EndpointEventKind.FABRIC_EXTERNAL

    def __post_init__(self) -> None:
        if type(self.target_coreid) is not int:
            raise TypeError("target_coreid must be an int")
        object.__setattr__(self, "ingress", EndpointIngress(self.ingress))
        object.__setattr__(
            self,
            "event_code",
            csrs.require_uint(self.event_code, csrs.CSR_BITS, "event_code"),
        )
        object.__setattr__(self, "kind", EndpointEventKind(self.kind))


@dataclass(frozen=True)
class InterruptDeliveryObservation:
    core_id: int
    source: kernel.InterruptSource
    pending_before_delivery: int
    entry: kernel.InterruptEntryResult
    saved_frame: kernel.SoftwareTrapFrame
    pending_after_ack: int
    external_pending_after_ack: bool
    iret_result: ExecutionResult

    @property
    def vector_cursor(self) -> int:
        assert self.entry.vector_pcc is not None
        return self.entry.vector_pcc.payload.cursor


@dataclass(frozen=True)
class EndpointRoutingReport:
    cores: tuple[state.CoreState, ...]
    start_result: startup.StartupResult
    started_coreid: int
    observations: tuple[InterruptDeliveryObservation, ...]
    priority_orders: tuple[tuple[int, tuple[kernel.InterruptSource, ...]], ...]
    final_selected_sources: tuple[tuple[int, kernel.InterruptSource | None], ...]

    def observations_for_core(
        self,
        core_id: int,
    ) -> tuple[InterruptDeliveryObservation, ...]:
        return tuple(
            observation
            for observation in self.observations
            if observation.core_id == core_id
        )


@dataclass
class EndpointEventController:
    """Route CPU-visible endpoint events without modeling a shared bus."""

    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE
    external_events: MutableMapping[int, list[EndpointEvent]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(self.profile, platform.TestPlatformProfile):
            raise TypeError("profile must be a TestPlatformProfile")
        for core_id in range(self.profile.core_count):
            self.external_events.setdefault(core_id, [])

    def route_external_event(
        self,
        target_coreid: int,
        *,
        ingress: EndpointIngress,
        event_code: int = EVENT_CODE_FABRIC_NOTIFY,
    ) -> EndpointEvent:
        self._require_coreid(target_coreid)
        event = EndpointEvent(
            target_coreid=target_coreid,
            ingress=ingress,
            event_code=event_code,
        )
        self.external_events[target_coreid].append(event)
        return event

    def route_software_ipi(
        self,
        cores: Sequence[state.CoreState],
        *,
        sender_coreid: int,
        target_coreid: int,
    ) -> None:
        self._require_coreid(sender_coreid)
        target = self._target_core(cores, target_coreid)
        bit = 1 << kernel.InterruptSource.SOFTWARE_IPI.bit
        target.write_csr_raw(csrs.CSR_IPENDING, target.read_csr(csrs.CSR_IPENDING) | bit)

    def arm_timer(self, core: state.CoreState, *, now: int = TIMER_ROUTE_NOW) -> None:
        if not isinstance(core, state.CoreState):
            raise TypeError("core must be a CoreState")
        core.write_csr_raw(csrs.CSR_TIMER, now)
        core.write_csr_raw(csrs.CSR_TIMECMP, now)

    def acknowledge(self, core: state.CoreState, source: kernel.InterruptSource) -> None:
        if not isinstance(core, state.CoreState):
            raise TypeError("core must be a CoreState")
        source = kernel.InterruptSource(source)
        if source is kernel.InterruptSource.EXTERNAL:
            self._acknowledge_external(core.core_id)
        elif source is kernel.InterruptSource.SOFTWARE_IPI:
            self._clear_pending_bit(core, source)
        elif source is kernel.InterruptSource.TIMER:
            core.write_csr_raw(
                csrs.CSR_TIMECMP,
                core.read_csr(csrs.CSR_TIMER) + TIMER_ACK_DELTA,
            )

    def pending_mask(self, core: state.CoreState) -> int:
        if not isinstance(core, state.CoreState):
            raise TypeError("core must be a CoreState")
        return kernel.effective_pending_mask(
            core,
            external_pending=self.external_pending(core.core_id),
        )

    def selected_interrupt_source(
        self,
        core: state.CoreState,
    ) -> kernel.InterruptSource | None:
        if not isinstance(core, state.CoreState):
            raise TypeError("core must be a CoreState")
        return kernel.selected_interrupt_source(
            core,
            external_pending=self.external_pending(core.core_id),
        )

    def enter_pending_interrupt(
        self,
        core: state.CoreState,
    ) -> kernel.InterruptEntryResult:
        if not isinstance(core, state.CoreState):
            raise TypeError("core must be a CoreState")
        return kernel.enter_pending_interrupt(
            core,
            external_pending=self.external_pending(core.core_id),
        )

    def external_pending(self, core_id: int) -> bool:
        self._require_coreid(core_id)
        return bool(self.external_events[core_id])

    def _acknowledge_external(self, core_id: int) -> None:
        self._require_coreid(core_id)
        if self.external_events[core_id]:
            self.external_events[core_id].pop(0)

    def _clear_pending_bit(
        self,
        core: state.CoreState,
        source: kernel.InterruptSource,
    ) -> None:
        bit = 1 << source.bit
        core.write_csr_raw(csrs.CSR_IPENDING, core.read_csr(csrs.CSR_IPENDING) & ~bit)

    def _target_core(
        self,
        cores: Sequence[state.CoreState],
        target_coreid: int,
    ) -> state.CoreState:
        self._require_coreid(target_coreid)
        if len(cores) <= target_coreid:
            raise ValueError("cores does not contain the target core")
        target = cores[target_coreid]
        if not isinstance(target, state.CoreState):
            raise TypeError("cores must contain CoreState instances")
        if target.core_id != target_coreid:
            raise ValueError("target core index does not match COREID")
        return target

    def _require_coreid(self, core_id: int) -> None:
        if type(core_id) is not int:
            raise TypeError("core_id must be an int")
        if not 0 <= core_id < self.profile.core_count:
            raise ValueError("core_id is outside the platform profile")


def run_endpoint_interrupt_routing_fixture() -> EndpointRoutingReport:
    """Run external event, IPI, and timer routing across boot and secondary cores."""
    boot_report = firmware.run_secondary_core_boot_demo()
    cores = list(boot_report.cores)
    controller = EndpointEventController()
    boot_coreid = 0
    target_coreids = (boot_coreid, boot_report.started_coreid)
    observations: list[InterruptDeliveryObservation] = []
    priority_orders: list[tuple[int, tuple[kernel.InterruptSource, ...]]] = []
    final_selected_sources: list[tuple[int, kernel.InterruptSource | None]] = []

    for target_coreid in target_coreids:
        target = cores[target_coreid]
        _enable_interrupt_delivery(target, ALL_INTERRUPT_SOURCES)
        controller.arm_timer(target, now=TIMER_ROUTE_NOW + target_coreid)
        controller.route_software_ipi(
            cores,
            sender_coreid=_ipi_sender_for(target_coreid, boot_report.started_coreid),
            target_coreid=target_coreid,
        )
        controller.route_external_event(
            target_coreid,
            ingress=_external_ingress_for(target_coreid),
        )

        order: list[kernel.InterruptSource] = []
        while True:
            selected = controller.selected_interrupt_source(target)
            if selected is None:
                break
            order.append(selected)
            observations.append(_deliver_ack_and_return(controller, target, selected))
        priority_orders.append((target_coreid, tuple(order)))
        final_selected_sources.append(
            (target_coreid, controller.selected_interrupt_source(target))
        )

    return EndpointRoutingReport(
        cores=tuple(cores),
        start_result=boot_report.start_result,
        started_coreid=boot_report.started_coreid,
        observations=tuple(observations),
        priority_orders=tuple(priority_orders),
        final_selected_sources=tuple(final_selected_sources),
    )


def _deliver_ack_and_return(
    controller: EndpointEventController,
    core: state.CoreState,
    expected_source: kernel.InterruptSource,
) -> InterruptDeliveryObservation:
    pending_before = controller.pending_mask(core)
    entry = controller.enter_pending_interrupt(core)
    if not entry.entered or entry.source is not expected_source:
        raise RuntimeError("interrupt routing fixture delivered an unexpected source")
    frame = kernel.save_trap_frame(core)
    controller.acknowledge(core, expected_source)
    pending_after_ack = controller.pending_mask(core)
    external_pending_after_ack = controller.external_pending(core.core_id)
    kernel.restore_frame_for_iret(core, frame)
    iret_result = kernel.execute_iret(core)
    return InterruptDeliveryObservation(
        core_id=core.core_id,
        source=expected_source,
        pending_before_delivery=pending_before,
        entry=entry,
        saved_frame=frame,
        pending_after_ack=pending_after_ack,
        external_pending_after_ack=external_pending_after_ack,
        iret_result=iret_result,
    )


def _enable_interrupt_delivery(
    core: state.CoreState,
    sources: tuple[kernel.InterruptSource, ...],
) -> None:
    mask = 0
    for source in sources:
        mask |= 1 << kernel.InterruptSource(source).bit
    core.write_csr_raw(csrs.CSR_IENABLE, mask)
    sr = core.read_csr(csrs.CSR_SR)
    sr |= 1 << csrs.SR_IE_BIT
    sr &= ~(1 << csrs.SR_EXL_BIT)
    core.write_csr_raw(csrs.CSR_SR, sr)


def _ipi_sender_for(target_coreid: int, started_coreid: int) -> int:
    if target_coreid == 0:
        return started_coreid
    return 0


def _external_ingress_for(target_coreid: int) -> EndpointIngress:
    if target_coreid == 0:
        return EndpointIngress.FABRIC0
    return EndpointIngress.FABRIC1

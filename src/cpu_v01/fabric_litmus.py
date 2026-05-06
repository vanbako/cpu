"""Point-to-point fabric integration litmus fixtures for CPU v0.1.

Owner stories:
- E08-S03: TSO-like store-buffer visibility.
- E10-S03: coherent payload/tag visibility.
- I06-S03: LL/SC reservation contention behavior.
- I06-S04: executable memory-ordering litmus support.
- I19-S02: endpoint event routing fixtures.
- I19-S03: noncoherent external-agent transfer fixtures.
- I19-S04: point-to-point fabric integration litmus suite.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import (
    atomic_ops,
    capabilities as caps,
    csrs,
    endpoint_events,
    execution,
    external_transfers,
    firmware,
    kernel,
    litmus,
    platform,
    reservations,
    startup,
    state,
)
from .cells import CACHE_LINE_CELLS, CELL_BITS
from .memory import TaggedMemory


FABRIC_CORE_COUNT = 4
FABRIC_BOOT_ARG_BASE = 0x1904
FABRIC_STACK_BASE = platform.RAM_BASE + 0x8000
FABRIC_STACK_STRIDE = 0x800
FABRIC_STACK_CELLS = 0x100
SHARED_BASE = 0x0019_4000
SHARED_STRIDE = 0x10
LOCK_ADDRESS = 0x0019_5000
TAG_SLOT_ADDRESS = 0x0019_6000


@dataclass(frozen=True)
class FabricLink:
    source_coreid: int
    target_coreid: int
    ingress: endpoint_events.EndpointIngress


@dataclass(frozen=True)
class FabricEventObservation:
    target_coreid: int
    ingress: endpoint_events.EndpointIngress
    selected_source: kernel.InterruptSource | None
    vector_cursor: int
    saved_cause: int
    returned_with_iret: bool
    external_pending_after_ack: bool


@dataclass(frozen=True)
class SharedMemoryObservation:
    visible_before_fences: tuple[int, ...]
    post_fence_reads: tuple[tuple[int, ...], ...]
    final_values: tuple[int, ...]


@dataclass(frozen=True)
class LlScContentionObservation:
    loaded_values: tuple[int, ...]
    reservation_valid_after_ll: tuple[bool, ...]
    sc_results: tuple[int, ...]
    final_lock_value: int
    reservation_valid_after_sc: tuple[bool, ...]


@dataclass(frozen=True)
class TagVisibilityObservation:
    capability_visible_to_peer: bool
    tag_after_integer_store: bool
    first_word_after_integer_store: int


@dataclass(frozen=True)
class FabricIntegrationReport:
    cores: tuple[state.CoreState, ...]
    startup_results: tuple[startup.StartupResult, ...]
    links: tuple[FabricLink, ...]
    event_observations: tuple[FabricEventObservation, ...]
    shared_memory: SharedMemoryObservation
    llsc_contention: LlScContentionObservation
    tag_visibility: TagVisibilityObservation
    external_transfer: external_transfers.ExternalAgentTransferReport

    @property
    def started_coreids(self) -> tuple[int, ...]:
        return tuple(result.target_coreid for result in self.startup_results)

    @property
    def all_interrupts_returned(self) -> bool:
        return all(observation.returned_with_iret for observation in self.event_observations)


def run_point_to_point_fabric_litmus_suite() -> FabricIntegrationReport:
    """Run deterministic four-core CPU-side fabric integration litmus cases."""
    cores, startup_results = _start_all_cores()
    links = _logical_links()
    event_observations = _deliver_fabric_events(cores, links)
    shared_memory = _run_shared_memory_litmus()
    llsc_contention = _run_llsc_contention_litmus(cores)
    tag_visibility = _run_tag_visibility_litmus()
    external_transfer = external_transfers.run_external_agent_transfer_fixture()
    return FabricIntegrationReport(
        cores=cores,
        startup_results=startup_results,
        links=links,
        event_observations=event_observations,
        shared_memory=shared_memory,
        llsc_contention=llsc_contention,
        tag_visibility=tag_visibility,
        external_transfer=external_transfer,
    )


def _start_all_cores() -> tuple[
    tuple[state.CoreState, ...],
    tuple[startup.StartupResult, ...],
]:
    memory = TaggedMemory()
    cores = list(platform.cold_reset_cores())
    firmware.initialize_boot_core_for_kernel_handoff(cores[0], memory)
    controller = startup.SecondaryStartupController()
    results: list[startup.StartupResult] = []
    for core_id in range(1, FABRIC_CORE_COUNT):
        controller.publish_start(
            core_id,
            core_id,
            entry_pcc=_entry_pcc(core_id),
            dsc=_stack_capability(core_id, 0),
            rsc=_stack_capability(core_id, 1),
            ksc=_stack_capability(core_id, 2),
            krc=cores[0].special_capabilities.read("KRC"),
            tvc=cores[0].special_capabilities.read("TVC"),
            arg0=FABRIC_BOOT_ARG_BASE + core_id,
        )
        results.append(controller.send_start_signal(cores, core_id))
    return tuple(cores), tuple(results)


def _logical_links() -> tuple[FabricLink, ...]:
    return (
        FabricLink(1, 0, endpoint_events.EndpointIngress.FABRIC0),
        FabricLink(0, 1, endpoint_events.EndpointIngress.LEFT_PEER),
        FabricLink(3, 2, endpoint_events.EndpointIngress.RIGHT_PEER),
        FabricLink(2, 3, endpoint_events.EndpointIngress.FABRIC1),
    )


def _deliver_fabric_events(
    cores: tuple[state.CoreState, ...],
    links: tuple[FabricLink, ...],
) -> tuple[FabricEventObservation, ...]:
    controller = endpoint_events.EndpointEventController()
    observations: list[FabricEventObservation] = []
    for link in links:
        target = cores[link.target_coreid]
        _enable_external_interrupt(target)
        controller.route_external_event(
            link.target_coreid,
            ingress=link.ingress,
        )
        selected = controller.selected_interrupt_source(target)
        entry = controller.enter_pending_interrupt(target)
        if not entry.entered:
            raise RuntimeError("fabric event was not delivered")
        frame = kernel.save_trap_frame(target)
        controller.acknowledge(target, kernel.InterruptSource.EXTERNAL)
        pending_after_ack = controller.external_pending(link.target_coreid)
        kernel.restore_frame_for_iret(target, frame)
        iret = kernel.execute_iret(target)
        assert entry.vector_pcc is not None
        observations.append(
            FabricEventObservation(
                target_coreid=link.target_coreid,
                ingress=link.ingress,
                selected_source=selected,
                vector_cursor=entry.vector_pcc.payload.cursor,
                saved_cause=frame.cause,
                returned_with_iret=iret.is_normal_retire,
                external_pending_after_ack=pending_after_ack,
            )
        )
    return tuple(observations)


def _run_shared_memory_litmus() -> SharedMemoryObservation:
    model = litmus.TsoMemoryModel(core_count=FABRIC_CORE_COUNT)
    addresses = _shared_addresses()
    values = tuple(0x1904_0000 + core_id for core_id in range(FABRIC_CORE_COUNT))
    for core_id, address in enumerate(addresses):
        model.st48(core_id, address, values[core_id])
    visible_before = tuple(model.visible_value(address) for address in addresses)
    for core_id in range(FABRIC_CORE_COUNT):
        model.fence(core_id)
    reads = tuple(
        tuple(model.ld48(core_id, address) for address in addresses)
        for core_id in range(FABRIC_CORE_COUNT)
    )
    final_values = tuple(model.visible_value(address) for address in addresses)
    return SharedMemoryObservation(
        visible_before_fences=visible_before,
        post_fence_reads=reads,
        final_values=final_values,
    )


def _run_llsc_contention_litmus(
    cores: tuple[state.CoreState, ...],
) -> LlScContentionObservation:
    memory = TaggedMemory()
    memory.st48(LOCK_ADDRESS, 0)
    for core_id, core in enumerate(cores):
        core.write_c(1, _data_authority(LOCK_ADDRESS, LOCK_ADDRESS + 2))
        core.write_d(2, 0)
        core.write_d(3, core_id + 1)
        _execute_atomic(core, memory, "LL48", (0, 1, 2))
    loaded_values = tuple(core.read_d(0) for core in cores)
    reservations_after_ll = tuple(core.reservation.valid for core in cores)

    _execute_atomic(cores[0], memory, "SC48", (4, 3, 1, 2))
    reservations.clear_conflicting_reservations(cores[1:], LOCK_ADDRESS, 2)
    for core in cores[1:]:
        _execute_atomic(core, memory, "SC48", (4, 3, 1, 2))

    return LlScContentionObservation(
        loaded_values=loaded_values,
        reservation_valid_after_ll=reservations_after_ll,
        sc_results=tuple(core.read_d(4) for core in cores),
        final_lock_value=memory.ld48(LOCK_ADDRESS),
        reservation_valid_after_sc=tuple(core.reservation.valid for core in cores),
    )


def _run_tag_visibility_litmus() -> TagVisibilityObservation:
    model = litmus.CacheDmaModel(core_count=FABRIC_CORE_COUNT)
    tagged = _data_capability(0x0019_7000)
    model.csc(0, TAG_SLOT_ADDRESS, tagged)
    peer_capability = model.clc(1, TAG_SLOT_ADDRESS)
    model.st48(2, TAG_SLOT_ADDRESS, 0x55AA)
    observed_after_store = model.clc(3, TAG_SLOT_ADDRESS)
    return TagVisibilityObservation(
        capability_visible_to_peer=peer_capability.tag,
        tag_after_integer_store=observed_after_store.tag,
        first_word_after_integer_store=model.ld48(3, TAG_SLOT_ADDRESS),
    )


def _execute_atomic(
    core: state.CoreState,
    memory: TaggedMemory,
    mnemonic: str,
    operands: tuple[int, ...],
) -> None:
    result = atomic_ops.execute_atomic(
        core,
        memory,
        atomic_ops.atomic_instruction(mnemonic, operands),
    )
    if not result.is_normal_retire:
        raise RuntimeError(f"{mnemonic} did not retire normally")
    execution.commit_normal_result(core, result, memory)


def _enable_external_interrupt(core: state.CoreState) -> None:
    core.write_csr_raw(csrs.CSR_IENABLE, 1 << kernel.InterruptSource.EXTERNAL.bit)
    sr = core.read_csr(csrs.CSR_SR)
    sr |= 1 << csrs.SR_IE_BIT
    sr &= ~(1 << csrs.SR_EXL_BIT)
    core.write_csr_raw(csrs.CSR_SR, sr)


def _entry_pcc(core_id: int) -> state.SlottedCapability:
    rom = platform.TEST_PLATFORM_PROFILE.reset_rom_region
    return state.SlottedCapability.from_capability(
        _global_capability(
            cursor=firmware.SECONDARY_ENTRY_CELL + (core_id * 4),
            base=rom.base,
            top=rom.end,
            permissions=caps.CapabilityPermission.EX,
        ),
        state.SLOT_0,
    )


def _stack_capability(core_id: int, stack_index: int) -> caps.Capability:
    base = FABRIC_STACK_BASE + (core_id * FABRIC_STACK_STRIDE)
    base += stack_index * FABRIC_STACK_CELLS
    return _local_capability(
        cursor=base + FABRIC_STACK_CELLS - 4,
        base=base,
        top=base + FABRIC_STACK_CELLS,
        permissions=(
            caps.CapabilityPermission.LD
            | caps.CapabilityPermission.ST
            | caps.CapabilityPermission.LC
            | caps.CapabilityPermission.SC
            | caps.CapabilityPermission.SL
        ),
    )


def _data_authority(base: int, top: int) -> caps.Capability:
    del top
    return _global_capability(
        cursor=base,
        base=0,
        top=1 << 48,
        permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.ST,
    )


def _data_capability(cursor: int) -> caps.Capability:
    return _global_capability(
        cursor=cursor,
        base=0,
        top=1 << 48,
        permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.ST,
    )


def _global_capability(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
) -> caps.Capability:
    return _capability(
        cursor=cursor,
        base=base,
        top=top,
        permissions=permissions,
        flags=caps.CapabilityFlag.G,
    )


def _local_capability(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
) -> caps.Capability:
    return _capability(
        cursor=cursor,
        base=base,
        top=top,
        permissions=permissions,
        flags=caps.CapabilityFlag.NONE,
    )


def _capability(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
    flags: caps.CapabilityFlag,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(permissions),
        flags=int(flags),
    ).with_bounds(base, top)
    return caps.Capability.valid(payload)


def _shared_addresses() -> tuple[int, ...]:
    return tuple(
        SHARED_BASE + (core_id * SHARED_STRIDE)
        for core_id in range(FABRIC_CORE_COUNT)
    )

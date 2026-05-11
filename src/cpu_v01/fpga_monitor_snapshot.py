"""Debug snapshot and replay handoff for FPGA monitor sessions.

Owner stories:
- I32-S04: add debug snapshot and replay handoff for monitor sessions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    capabilities as caps,
    csrs,
    debug_abi,
    firmware,
    fpga_debug_status,
    fpga_monitor_firmware,
    fpga_monitor_profile,
    fpga_program_loader,
    fpga_replay_mapper,
    platform,
    state,
)
from .memory import TaggedMemory


JsonValue = Any

FPGA_MONITOR_SNAPSHOT_STORY = "I32-S04"
FPGA_MONITOR_SNAPSHOT_DOC = Path("docs/implementation/fpga-monitor-debug-snapshot.md")
FPGA_MONITOR_SNAPSHOT_TOOL = "python tools\\fpga_monitor_snapshot.py --check"
FPGA_MONITOR_SNAPSHOT_STATUS = "debug_snapshot_replay_handoff"
DEBUG_ABI_GATE = "python -m unittest tests.conformance.test_i09_s04_debug_abi"
SNAPSHOT_PROGRAM_ID = "call_return.direct_call_ret_fpga"
SNAPSHOT_MEMORY_CELLS = 4


@dataclass(frozen=True)
class MonitorSnapshotRegisterSample:
    name: str
    register_class: str
    index: int
    value: int
    tag_visible: bool
    tag: bool | None
    slot_visible: bool
    slot: int | None
    writable_by_snapshot: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "register_class": self.register_class,
            "index": self.index,
            "value": self.value,
            "tag_visible": self.tag_visible,
            "tag": self.tag,
            "slot_visible": self.slot_visible,
            "slot": self.slot,
            "writable_by_snapshot": self.writable_by_snapshot,
        }


@dataclass(frozen=True)
class MonitorSnapshotMemoryWindow:
    target_memory: str
    base_cell: int
    cell_count: int
    cells: tuple[int, ...]
    tag_bits_before: tuple[int, ...]
    tag_bits_after: tuple[int, ...]
    tag_bits_exposed_to_host: bool
    writable_by_snapshot: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "target_memory": self.target_memory,
            "base_cell": self.base_cell,
            "cell_count": self.cell_count,
            "cells": list(self.cells),
            "tag_bits_before": list(self.tag_bits_before),
            "tag_bits_after": list(self.tag_bits_after),
            "tag_bits_exposed_to_host": self.tag_bits_exposed_to_host,
            "writable_by_snapshot": self.writable_by_snapshot,
        }


@dataclass(frozen=True)
class MonitorSnapshotReplayHandoff:
    status_packet_hex: str
    pass_fail_state: str
    replay_case_id: str
    replay_command: str
    compare_command: str
    diagnostics: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status_packet_hex": self.status_packet_hex,
            "pass_fail_state": self.pass_fail_state,
            "replay_case_id": self.replay_case_id,
            "replay_command": self.replay_command,
            "compare_command": self.compare_command,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class MonitorSnapshotTagPolicy:
    register_tags_reported: bool
    ccsr_tags_reported: bool
    host_tag_write_enabled: bool
    memory_tags_unchanged: bool
    write_memory_commands_issued: int

    @property
    def passed(self) -> bool:
        return (
            self.register_tags_reported
            and self.ccsr_tags_reported
            and not self.host_tag_write_enabled
            and self.memory_tags_unchanged
            and self.write_memory_commands_issued == 0
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "register_tags_reported": self.register_tags_reported,
            "ccsr_tags_reported": self.ccsr_tags_reported,
            "host_tag_write_enabled": self.host_tag_write_enabled,
            "memory_tags_unchanged": self.memory_tags_unchanged,
            "write_memory_commands_issued": self.write_memory_commands_issued,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class MonitorDebugSnapshot:
    story: str
    status: str
    lifecycle: str
    monitor_state: str
    pc_cell: int
    pc_slot: int
    integer_registers: tuple[MonitorSnapshotRegisterSample, ...]
    capability_registers: tuple[MonitorSnapshotRegisterSample, ...]
    ccsr_registers: tuple[MonitorSnapshotRegisterSample, ...]
    csr_registers: tuple[MonitorSnapshotRegisterSample, ...]
    memory_window: MonitorSnapshotMemoryWindow
    status_packet: fpga_debug_status.DebugStatusPacket
    replay_handoff: MonitorSnapshotReplayHandoff
    tag_policy: MonitorSnapshotTagPolicy

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "lifecycle": self.lifecycle,
            "monitor_state": self.monitor_state,
            "pc_cell": self.pc_cell,
            "pc_slot": self.pc_slot,
            "integer_registers": [sample.as_dict() for sample in self.integer_registers],
            "capability_registers": [sample.as_dict() for sample in self.capability_registers],
            "ccsr_registers": [sample.as_dict() for sample in self.ccsr_registers],
            "csr_registers": [sample.as_dict() for sample in self.csr_registers],
            "memory_window": self.memory_window.as_dict(),
            "status_packet": self.status_packet.as_dict(),
            "replay_handoff": self.replay_handoff.as_dict(),
            "tag_policy": self.tag_policy.as_dict(),
        }


@dataclass(frozen=True)
class MonitorSnapshotProfile:
    story: str
    status: str
    monitor_firmware_gate: str
    debug_abi_gate: str
    replay_mapper_gate: str
    captured_registers: tuple[str, ...]
    memory_window_cells: int
    snapshot_rules: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "monitor_firmware_gate": self.monitor_firmware_gate,
            "debug_abi_gate": self.debug_abi_gate,
            "replay_mapper_gate": self.replay_mapper_gate,
            "captured_registers": list(self.captured_registers),
            "memory_window_cells": self.memory_window_cells,
            "snapshot_rules": list(self.snapshot_rules),
            "handoffs": list(self.handoffs),
        }


def fpga_monitor_snapshot_profile() -> MonitorSnapshotProfile:
    return MonitorSnapshotProfile(
        story=FPGA_MONITOR_SNAPSHOT_STORY,
        status=FPGA_MONITOR_SNAPSHOT_STATUS,
        monitor_firmware_gate=fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL,
        debug_abi_gate=DEBUG_ABI_GATE,
        replay_mapper_gate=fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        captured_registers=("D0", "D1", "D2", "D3", "C0", "C1", "PCC", "EPCC", "TVC", "RSC", "SR", "CAUSE", "TVAL", "DEBUGCTL"),
        memory_window_cells=SNAPSHOT_MEMORY_CELLS,
        snapshot_rules=(
            "direct architectural register capture requires DEBUG_HALTED lifecycle",
            "PCC and EPCC include hidden slot state",
            "capability and CCSR samples report existing tag bits but never synthesize tags",
            "memory windows are read-only data_ram payload cells and do not expose writable tag sidecars",
            "the captured status packet maps immediately to an I25-S04 replay command",
        ),
        handoffs=(
            "I32-S05 can attach this snapshot shape to each interactive corpus case",
            "I32-S06 can archive packet hex, replay command, and memory/register samples with board evidence",
            "future monitor transports must preserve the no-tag-forgery tag policy in this profile",
        ),
    )


def capture_monitor_debug_snapshot() -> MonitorDebugSnapshot:
    monitor_state, status_result, read_result = _prepare_monitor_capture()
    core = _prepared_debug_halted_core(status_result.report.debug_packet)
    memory_window = _memory_window(monitor_state)
    replay_handoff = _replay_handoff(status_result.report.debug_packet)
    integer_samples = tuple(_integer_sample(core, name) for name in ("D0", "D1", "D2", "D3"))
    capability_samples = tuple(_capability_sample(core, name) for name in ("C0", "C1"))
    ccsr_samples = tuple(_ccsr_sample(core, name) for name in ("PCC", "EPCC", "TVC", "RSC"))
    csr_samples = tuple(_csr_sample(core, name) for name in ("SR", "CAUSE", "TVAL", "DEBUGCTL"))
    tag_policy = MonitorSnapshotTagPolicy(
        register_tags_reported=any(sample.tag_visible and sample.tag for sample in capability_samples),
        ccsr_tags_reported=any(sample.tag_visible and sample.tag for sample in ccsr_samples),
        host_tag_write_enabled=memory_window.tag_bits_exposed_to_host or memory_window.writable_by_snapshot,
        memory_tags_unchanged=memory_window.tag_bits_before == memory_window.tag_bits_after,
        write_memory_commands_issued=sum(
            1
            for result in (read_result, status_result)
            if result.request.command_name == fpga_monitor_profile.COMMAND_WRITE_MEMORY
        ),
    )
    return MonitorDebugSnapshot(
        story=FPGA_MONITOR_SNAPSHOT_STORY,
        status=FPGA_MONITOR_SNAPSHOT_STATUS,
        lifecycle=core.lifecycle.value,
        monitor_state=monitor_state.monitor_state,
        pc_cell=core.pcc.payload.cursor,
        pc_slot=core.pcc.slot,
        integer_registers=integer_samples,
        capability_registers=capability_samples,
        ccsr_registers=ccsr_samples,
        csr_registers=csr_samples,
        memory_window=memory_window,
        status_packet=status_result.report.debug_packet,
        replay_handoff=replay_handoff,
        tag_policy=tag_policy,
    )


def fpga_monitor_snapshot_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_monitor_snapshot_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_monitor_debug_snapshot_json(*, indent: int = 2) -> str:
    return json.dumps(capture_monitor_debug_snapshot().as_dict(), indent=indent, sort_keys=True)


def render_fpga_monitor_snapshot(profile: MonitorSnapshotProfile | None = None) -> str:
    if profile is None:
        profile = fpga_monitor_snapshot_profile()
    lines = [
        "# FPGA Monitor Debug Snapshot",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Monitor firmware gate: `{profile.monitor_firmware_gate}`",
        f"Debug ABI gate: `{profile.debug_abi_gate}`",
        f"Replay mapper gate: `{profile.replay_mapper_gate}`",
        "",
        "## Captured Registers",
        "",
        ", ".join(f"`{name}`" for name in profile.captured_registers),
        "",
        "## Snapshot Rules",
        "",
    ]
    lines.extend(f"- {rule}." for rule in profile.snapshot_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_monitor_snapshot(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_snapshot_profile()
    snapshot = capture_monitor_debug_snapshot()
    issues: list[str] = []

    if profile.story != FPGA_MONITOR_SNAPSHOT_STORY:
        issues.append(f"monitor snapshot story must be {FPGA_MONITOR_SNAPSHOT_STORY}")
    if profile.status != FPGA_MONITOR_SNAPSHOT_STATUS:
        issues.append("monitor snapshot status must remain fixture-defined")
    if profile.monitor_firmware_gate != fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL:
        issues.append("monitor snapshot must depend on I32-S02 monitor firmware")
    if profile.debug_abi_gate != DEBUG_ABI_GATE:
        issues.append("monitor snapshot must depend on I09-S04 debug ABI")
    if profile.replay_mapper_gate != fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL:
        issues.append("monitor snapshot must depend on I25-S04 replay mapper")

    issues.extend(fpga_monitor_firmware.validate_fpga_monitor_firmware(root))
    issues.extend(debug_abi.validate_debug_abi_profile())
    issues.extend(fpga_replay_mapper.validate_fpga_replay_mapper(root))

    if snapshot.lifecycle != state.CoreLifecycle.DEBUG_HALTED.value:
        issues.append("snapshot core must be DEBUG_HALTED")
    if not debug_abi.direct_register_access_allowed(state.CoreLifecycle.DEBUG_HALTED):
        issues.append("debug ABI must allow direct access while debug halted")
    if debug_abi.direct_register_access_allowed(state.CoreLifecycle.RUNNING):
        issues.append("debug ABI must reject direct access while running")
    if snapshot.pc_slot not in state.VALID_SLOTS:
        issues.append("snapshot PC slot must be visible and valid")

    integer_names = {sample.name for sample in snapshot.integer_registers}
    for name in ("D0", "D1", "D2", "D3"):
        if name not in integer_names:
            issues.append(f"snapshot missing integer register {name}")
    capability_names = {sample.name for sample in snapshot.capability_registers}
    for name in ("C0", "C1"):
        if name not in capability_names:
            issues.append(f"snapshot missing capability register {name}")
    ccsr = {sample.name: sample for sample in snapshot.ccsr_registers}
    for name in ("PCC", "EPCC", "TVC", "RSC"):
        if name not in ccsr:
            issues.append(f"snapshot missing CCSR {name}")
    for name in ("PCC", "EPCC"):
        if name in ccsr and not ccsr[name].slot_visible:
            issues.append(f"snapshot must expose {name} slot")
    if "TVC" in ccsr and ccsr["TVC"].slot is not None:
        issues.append("non-slotted CCSR TVC must not report a hidden slot")

    csr_names = {sample.name for sample in snapshot.csr_registers}
    for name in ("SR", "CAUSE", "TVAL", "DEBUGCTL"):
        if name not in csr_names:
            issues.append(f"snapshot missing CSR {name}")

    if snapshot.memory_window.target_memory != fpga_program_loader.TARGET_MEMORY:
        issues.append("snapshot memory window must target data_ram")
    if snapshot.memory_window.cell_count != SNAPSHOT_MEMORY_CELLS:
        issues.append("snapshot memory window must have the configured cell count")
    if snapshot.memory_window.writable_by_snapshot:
        issues.append("snapshot memory window must be read-only")
    if snapshot.memory_window.tag_bits_exposed_to_host:
        issues.append("snapshot must not expose tag bits as host-writable data")
    if not snapshot.tag_policy.passed:
        issues.append("snapshot tag policy must prevent tag forgery")

    packet_issues = fpga_debug_status.validate_debug_status_packet(snapshot.status_packet)
    if packet_issues:
        issues.append("snapshot status packet invalid: " + "; ".join(packet_issues))
    if len(snapshot.replay_handoff.status_packet_hex) != fpga_debug_status.STATUS_PACKET_SIZE_BYTES * 2:
        issues.append("snapshot replay handoff must preserve 32-byte packet hex")
    if "verilator_diff_harness.py --case-id" not in snapshot.replay_handoff.replay_command:
        issues.append("snapshot replay handoff must name a Verilator replay command")
    if snapshot.replay_handoff.replay_case_id != "core.shell.reset_idle":
        issues.append("halted BAD_COMMAND snapshot should map to reset/idle replay first")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(snapshot.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"monitor snapshot objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_MONITOR_SNAPSHOT_DOC)
    for token in (
        "Story: I32-S04",
        FPGA_MONITOR_SNAPSHOT_TOOL,
        fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL,
        DEBUG_ABI_GATE,
        fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        "DEBUG_HALTED",
        "PCC",
        "EPCC",
        "CCSR",
        "memory window",
        "status packet",
        "replay_command",
        "signature",
        "tag forgery",
        "tag_bits_exposed_to_host",
        "I32-S05",
        "I32-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MONITOR_SNAPSHOT_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _prepare_monitor_capture() -> tuple[
    fpga_monitor_firmware.MonitorFirmwareState,
    fpga_monitor_firmware.MonitorFirmwareCommandResult,
    fpga_monitor_firmware.MonitorFirmwareCommandResult,
]:
    monitor_state = fpga_monitor_firmware.fpga_monitor_firmware_state()
    for command in (
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HELLO),
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_HALT,
            reason="snapshot",
        ),
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_LOAD_IMAGE,
            program_id=SNAPSHOT_PROGRAM_ID,
            cell_count=fpga_program_loader.MAX_CHUNK_CELLS,
        ),
    ):
        fpga_monitor_firmware.execute_monitor_command(monitor_state, command)
    read_result = fpga_monitor_firmware.execute_monitor_command(
        monitor_state,
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_READ_MEMORY,
            target_memory=fpga_program_loader.TARGET_MEMORY,
            base_cell=platform.RAM_BASE,
            cell_count=SNAPSHOT_MEMORY_CELLS,
        ),
    )
    status_result = fpga_monitor_firmware.execute_monitor_command(
        monitor_state,
        fpga_monitor_firmware.MonitorFirmwareCommandRequest("NOPE"),
    )
    return monitor_state, status_result, read_result


def _prepared_debug_halted_core(
    packet: fpga_debug_status.DebugStatusPacket,
) -> state.CoreState:
    memory = TaggedMemory()
    core = platform.cold_reset_cores()[0]
    firmware.initialize_boot_core_for_kernel_handoff(core, memory)
    core.lifecycle = state.CoreLifecycle.DEBUG_HALTED
    core.write_d(0, packet.sequence)
    core.write_d(1, packet.fault_code)
    core.write_d(2, packet.pc_cell)
    core.write_d(3, packet.retire_count)
    core.write_c(0, core.special_capabilities.read("KRC"))
    core.write_c(1, caps.Capability.invalid())
    core.write_csr_raw(csrs.CSR_CAUSE, packet.fault_code)
    core.write_csr_raw(csrs.CSR_TVAL, packet.pc_cell)
    core.write_csr_raw(csrs.CSR_DEBUGCTL, 0)
    return core


def _memory_window(
    monitor_state: fpga_monitor_firmware.MonitorFirmwareState,
) -> MonitorSnapshotMemoryWindow:
    target = fpga_program_loader.fpga_program_loader_profile()
    offset = platform.RAM_BASE - target.target_base_cell
    before = tuple(monitor_state.loader_state.tag_ram[offset : offset + SNAPSHOT_MEMORY_CELLS])
    cells = tuple(monitor_state.loader_state.data_ram[offset : offset + SNAPSHOT_MEMORY_CELLS])
    after = tuple(monitor_state.loader_state.tag_ram[offset : offset + SNAPSHOT_MEMORY_CELLS])
    return MonitorSnapshotMemoryWindow(
        target_memory=fpga_program_loader.TARGET_MEMORY,
        base_cell=platform.RAM_BASE,
        cell_count=SNAPSHOT_MEMORY_CELLS,
        cells=cells,
        tag_bits_before=before,
        tag_bits_after=after,
        tag_bits_exposed_to_host=False,
        writable_by_snapshot=False,
    )


def _replay_handoff(
    packet: fpga_debug_status.DebugStatusPacket,
) -> MonitorSnapshotReplayHandoff:
    packet_hex = fpga_debug_status.encode_debug_status_packet(packet).hex()
    mapping = fpga_replay_mapper.map_debug_status_packet(packet, packet_hex=packet_hex)
    candidate = mapping.candidates[0]
    return MonitorSnapshotReplayHandoff(
        status_packet_hex=packet_hex,
        pass_fail_state=mapping.pass_fail_state,
        replay_case_id=candidate.case_id,
        replay_command=candidate.replay_command,
        compare_command=candidate.compare_command,
        diagnostics=mapping.diagnostics,
    )


def _integer_sample(core: state.CoreState, name: str) -> MonitorSnapshotRegisterSample:
    view = debug_abi.debug_register_view(name)
    return MonitorSnapshotRegisterSample(
        name=view.name,
        register_class=view.register_class.value,
        index=view.index,
        value=core.read_d(view.index),
        tag_visible=view.tag_visible,
        tag=None,
        slot_visible=view.slot_visible,
        slot=None,
        writable_by_snapshot=False,
    )


def _capability_sample(core: state.CoreState, name: str) -> MonitorSnapshotRegisterSample:
    view = debug_abi.debug_register_view(name)
    capability = core.read_c(view.index)
    return _capability_register_sample(view, capability, None)


def _ccsr_sample(core: state.CoreState, name: str) -> MonitorSnapshotRegisterSample:
    view = debug_abi.debug_register_view(name)
    if name in state.SLOTTED_SPECIAL_CAPABILITY_NAMES:
        slotted = core.special_capabilities.read_slotted(name)
        return _capability_register_sample(view, slotted.without_slot(), slotted.slot)
    return _capability_register_sample(view, core.read_ccsr(view.index), None)


def _capability_register_sample(
    view: debug_abi.DebugRegisterView,
    capability: caps.Capability,
    slot: int | None,
) -> MonitorSnapshotRegisterSample:
    value = capability.payload.cursor if capability.is_valid else 0
    return MonitorSnapshotRegisterSample(
        name=view.name,
        register_class=view.register_class.value,
        index=view.index,
        value=value,
        tag_visible=view.tag_visible,
        tag=capability.is_valid if view.tag_visible else None,
        slot_visible=view.slot_visible,
        slot=slot if view.slot_visible else None,
        writable_by_snapshot=False,
    )


def _csr_sample(core: state.CoreState, name: str) -> MonitorSnapshotRegisterSample:
    view = debug_abi.debug_register_view(name)
    return MonitorSnapshotRegisterSample(
        name=view.name,
        register_class=view.register_class.value,
        index=view.index,
        value=core.read_csr(view.index),
        tag_visible=view.tag_visible,
        tag=None,
        slot_visible=view.slot_visible,
        slot=None,
        writable_by_snapshot=False,
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

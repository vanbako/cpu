"""Optional GAO/ILA probe bundle profile for FPGA bring-up.

Owner stories:
- I25-S03: define first-failure probe bundles for FPGA debug.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_constraints, fpga_debug_status


JsonValue = Any

FPGA_PROBE_BUNDLES_STORY = "I25-S03"
FPGA_PROBE_BUNDLES_DOC = Path("docs/implementation/fpga-probe-bundles.md")
FPGA_PROBE_BUNDLES_TOOL = "python tools\\fpga_probe_bundles.py --check"


@dataclass(frozen=True)
class FpgaProbeSignal:
    name: str
    width: int
    bundle: str
    source: str
    rtl_token: str
    role: str
    required_for_failure_capture: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "width": self.width,
            "bundle": self.bundle,
            "source": self.source,
            "rtl_token": self.rtl_token,
            "role": self.role,
            "required_for_failure_capture": self.required_for_failure_capture,
        }


@dataclass(frozen=True)
class FpgaProbeTrigger:
    name: str
    source: str
    condition: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source": self.source,
            "condition": self.condition,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FpgaProbeBundleProfile:
    story: str
    top_module: str
    packet_gate: str
    constraints_gate: str
    supported_tools: tuple[str, ...]
    release_policy: str
    signals: tuple[FpgaProbeSignal, ...]
    triggers: tuple[FpgaProbeTrigger, ...]
    capture_rules: tuple[str, ...]
    non_interference_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "packet_gate": self.packet_gate,
            "constraints_gate": self.constraints_gate,
            "supported_tools": list(self.supported_tools),
            "release_policy": self.release_policy,
            "signals": [signal.as_dict() for signal in self.signals],
            "triggers": [trigger.as_dict() for trigger in self.triggers],
            "capture_rules": list(self.capture_rules),
            "non_interference_rules": list(self.non_interference_rules),
        }


def fpga_probe_bundle_profile() -> FpgaProbeBundleProfile:
    return FpgaProbeBundleProfile(
        story=FPGA_PROBE_BUNDLES_STORY,
        top_module="cpu_v01_fpga_top",
        packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        constraints_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        supported_tools=("Gowin GAO", "generic ILA"),
        release_policy=(
            "Probe definitions are optional debug project metadata; the release "
            "top module keeps the same ports and does not instantiate analyzer IP."
        ),
        signals=(
            FpgaProbeSignal(
                "probe_board_clk",
                1,
                "clock_reset",
                "board_clk_i",
                "board_clk_i",
                "sample clock reference",
                True,
            ),
            FpgaProbeSignal(
                "probe_board_reset_n",
                1,
                "clock_reset",
                "board_reset_n_i",
                "board_reset_n_i",
                "async board reset input",
                True,
            ),
            FpgaProbeSignal(
                "probe_core_rst_n",
                1,
                "clock_reset",
                "core_rst_n",
                "core_rst_n",
                "synchronized core reset",
                True,
            ),
            FpgaProbeSignal(
                "probe_reset_observed",
                1,
                "clock_reset",
                "status_reset_observed_o",
                "status_reset_observed_o",
                "reset-release observation",
                True,
            ),
            FpgaProbeSignal(
                "probe_pcc_cursor_low",
                32,
                "status_packet",
                "debug_pcc_cursor_low_o",
                "debug_pcc_cursor_low_o",
                "current low PC/PCC cursor bits",
                True,
            ),
            FpgaProbeSignal(
                "probe_pc_slot",
                1,
                "status_packet",
                "retire_packet.slot",
                "retire_packet.slot",
                "retired instruction slot",
                True,
            ),
            FpgaProbeSignal(
                "probe_retire_valid",
                1,
                "status_packet",
                "retire_valid",
                "retire_valid",
                "sample marks an architectural retire",
                True,
            ),
            FpgaProbeSignal(
                "probe_retire_count",
                32,
                "status_packet",
                "status_retire_count_o",
                "status_retire_count_o",
                "retire progress counter",
                True,
            ),
            FpgaProbeSignal(
                "probe_fault_valid",
                1,
                "status_packet",
                "status_fault_valid_o",
                "status_fault_valid_o",
                "sticky fault observation",
                True,
            ),
            FpgaProbeSignal(
                "probe_fault_code",
                16,
                "status_packet",
                "status_fault_code_o",
                "status_fault_code_o",
                "sticky first fault cause",
                True,
            ),
            FpgaProbeSignal(
                "probe_trap_cause",
                16,
                "status_packet",
                "retire_packet.fault.cause",
                "retire_packet.fault.cause",
                "trap cause at sampled retire point",
                True,
            ),
            FpgaProbeSignal(
                "probe_pass_led",
                1,
                "status_packet",
                "pass_led_o",
                "pass_led_o",
                "first-test pass state",
                True,
            ),
            FpgaProbeSignal(
                "probe_fail_led",
                1,
                "status_packet",
                "fail_led_o",
                "fail_led_o",
                "first-test fail state",
                True,
            ),
            FpgaProbeSignal(
                "probe_heartbeat",
                1,
                "status_packet",
                "heartbeat_led_o",
                "heartbeat_led_o",
                "retire-derived heartbeat",
                True,
            ),
            FpgaProbeSignal(
                "probe_uart_tx",
                1,
                "status_packet",
                "uart_tx_o",
                "uart_tx_o",
                "UART status stream activity",
                False,
            ),
            FpgaProbeSignal(
                "probe_uart_packet_started",
                1,
                "status_packet",
                "uart_status_packet_started",
                "uart_status_packet_started",
                "packet capture alignment marker",
                False,
            ),
            FpgaProbeSignal(
                "probe_uart_sequence",
                32,
                "status_packet",
                "uart_status_sequence_q",
                "uart_status_sequence_q",
                "UART packet sequence counter",
                False,
            ),
            FpgaProbeSignal(
                "probe_imem_req_valid",
                1,
                "memory_handshake",
                "imem_req_valid",
                "imem_req_valid",
                "instruction request valid",
                True,
            ),
            FpgaProbeSignal(
                "probe_imem_req_ready",
                1,
                "memory_handshake",
                "imem_req_ready",
                "imem_req_ready",
                "instruction request accepted",
                True,
            ),
            FpgaProbeSignal(
                "probe_imem_rsp_valid",
                1,
                "memory_handshake",
                "imem_rsp_valid",
                "imem_rsp_valid",
                "instruction response valid",
                True,
            ),
            FpgaProbeSignal(
                "probe_dmem_req_valid",
                1,
                "memory_handshake",
                "dmem_req_valid",
                "dmem_req_valid",
                "data request valid",
                True,
            ),
            FpgaProbeSignal(
                "probe_dmem_req_ready",
                1,
                "memory_handshake",
                "dmem_req_ready",
                "dmem_req_ready",
                "data request accepted",
                True,
            ),
            FpgaProbeSignal(
                "probe_dmem_req_write",
                1,
                "memory_handshake",
                "dmem_req_write",
                "dmem_req_write",
                "data request write/read direction",
                False,
            ),
            FpgaProbeSignal(
                "probe_dmem_rsp_valid",
                1,
                "memory_handshake",
                "dmem_rsp_valid",
                "dmem_rsp_valid",
                "data response valid",
                True,
            ),
            FpgaProbeSignal(
                "probe_tagmem_req_valid",
                1,
                "memory_handshake",
                "tagmem_req_valid",
                "tagmem_req_valid",
                "tag memory request valid",
                True,
            ),
            FpgaProbeSignal(
                "probe_tagmem_req_ready",
                1,
                "memory_handshake",
                "tagmem_req_ready",
                "tagmem_req_ready",
                "tag memory request accepted",
                True,
            ),
            FpgaProbeSignal(
                "probe_tagmem_req_write",
                1,
                "memory_handshake",
                "tagmem_req_write",
                "tagmem_req_write",
                "tag memory write/read direction",
                False,
            ),
            FpgaProbeSignal(
                "probe_tagmem_rsp_valid",
                1,
                "memory_handshake",
                "tagmem_rsp_valid",
                "tagmem_rsp_valid",
                "tag memory response valid",
                True,
            ),
        ),
        triggers=(
            FpgaProbeTrigger(
                "reset_release",
                "probe_reset_observed",
                "rising edge",
                "confirm reset synchronizer and first fetch startup",
            ),
            FpgaProbeTrigger(
                "first_pass",
                "probe_pass_led",
                "rising edge",
                "capture the first successful smoke completion window",
            ),
            FpgaProbeTrigger(
                "first_fault",
                "probe_fault_valid or probe_fail_led",
                "rising edge",
                "capture PC, slot, fault code, and handshakes around the first fault",
            ),
            FpgaProbeTrigger(
                "memory_stall",
                "request valid without ready or response progress",
                "high for 16 cycles",
                "distinguish memory adapter stalls from core decode or trap faults",
            ),
            FpgaProbeTrigger(
                "uart_packet_start",
                "probe_uart_packet_started",
                "rising edge",
                "align GAO/ILA samples with the UART status packet sequence",
            ),
        ),
        capture_rules=(
            "use board_clk_i as the sample clock for first-test probes",
            "capture at least 128 samples before and after first_fault when the tool supports pretrigger depth",
            "archive the probe setup file and decoded signal list with I25-S05 evidence",
            "keep pass/fail/heartbeat, PC/slot, retire count, fault code, and memory handshakes in the same capture group",
        ),
        non_interference_rules=(
            "release builds keep the same cpu_v01_fpga_top ports",
            "probe definitions do not change retire_ready or memory ready/valid behavior",
            "GAO or ILA IP is enabled only in a debug Gowin project variant",
            "captured samples are debug evidence and are not architectural state",
        ),
    )


def fpga_probe_bundle_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_probe_bundle_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_probe_bundle_command_plan() -> tuple[str, ...]:
    return (
        FPGA_PROBE_BUNDLES_TOOL,
        "python tools\\fpga_debug_status_packet.py --check",
        "python tools\\fpga_constraints_overlay.py --check",
    )


def render_fpga_probe_bundle_profile(
    profile: FpgaProbeBundleProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_probe_bundle_profile()
    lines = [
        "# FPGA Probe Bundles",
        "",
        f"Story: {profile.story}",
        "",
        f"Top module: `{profile.top_module}`",
        f"Packet gate: `{profile.packet_gate}`",
        f"Constraints gate: `{profile.constraints_gate}`",
        f"Release policy: {profile.release_policy}",
        "",
        "## Signals",
        "",
        "| Bundle | Signal | Width | Source | Role |",
        "| --- | --- | --- | --- | --- |",
    ]
    for signal in profile.signals:
        lines.append(
            f"| `{signal.bundle}` | `{signal.name}` | {signal.width} | "
            f"`{signal.source}` | {signal.role} |"
        )
    lines.extend(["", "## Triggers", "", "| Trigger | Source | Condition | Purpose |", "| --- | --- | --- | --- |"])
    for trigger in profile.triggers:
        lines.append(
            f"| `{trigger.name}` | `{trigger.source}` | {trigger.condition} | {trigger.purpose} |"
        )
    lines.extend(["", "## Non-Interference", ""])
    lines.extend(f"- {rule}." for rule in profile.non_interference_rules)
    lines.append("")
    return "\n".join(lines)


def render_probe_list(profile: FpgaProbeBundleProfile | None = None) -> str:
    if profile is None:
        profile = fpga_probe_bundle_profile()
    lines = ["bundle,name,width,source,required_for_failure_capture"]
    for signal in profile.signals:
        lines.append(
            f"{signal.bundle},{signal.name},{signal.width},{signal.source},"
            f"{str(signal.required_for_failure_capture).lower()}"
        )
    return "\n".join(lines)


def validate_fpga_probe_bundles(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_probe_bundle_profile()
    issues: list[str] = []

    if profile.story != FPGA_PROBE_BUNDLES_STORY:
        issues.append(f"probe bundle story must be {FPGA_PROBE_BUNDLES_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("probe bundle top module must be cpu_v01_fpga_top")
    if profile.packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("probe bundle packet gate must be I25-S01")
    if profile.constraints_gate != fpga_constraints.FPGA_CONSTRAINTS_TOOL:
        issues.append("probe bundle constraints gate must be I24-S02")
    if "Gowin GAO" not in profile.supported_tools or "generic ILA" not in profile.supported_tools:
        issues.append("probe bundle must support GAO and generic ILA flows")
    if "does not instantiate analyzer IP" not in profile.release_policy:
        issues.append("probe bundle release policy must avoid analyzer IP in release builds")

    issues.extend(fpga_debug_status.validate_fpga_debug_status(root))
    issues.extend(fpga_constraints.validate_fpga_constraints_overlay(root))

    signals = {signal.name: signal for signal in profile.signals}
    required_signals = (
        "probe_board_clk",
        "probe_board_reset_n",
        "probe_core_rst_n",
        "probe_pcc_cursor_low",
        "probe_pc_slot",
        "probe_retire_count",
        "probe_fault_code",
        "probe_pass_led",
        "probe_fail_led",
        "probe_heartbeat",
        "probe_imem_req_valid",
        "probe_imem_req_ready",
        "probe_dmem_req_valid",
        "probe_dmem_req_ready",
        "probe_tagmem_req_valid",
        "probe_tagmem_req_ready",
    )
    for name in required_signals:
        signal = signals.get(name)
        if signal is None:
            issues.append(f"missing required probe signal {name}")
        elif not signal.required_for_failure_capture:
            issues.append(f"required probe signal {name} must be marked for failure capture")

    bundles = {signal.bundle for signal in profile.signals}
    for bundle in ("clock_reset", "status_packet", "memory_handshake"):
        if bundle not in bundles:
            issues.append(f"missing probe bundle {bundle}")

    triggers = {trigger.name for trigger in profile.triggers}
    for trigger in ("reset_release", "first_pass", "first_fault", "memory_stall"):
        if trigger not in triggers:
            issues.append(f"missing probe trigger {trigger}")

    if not any("retire_ready" in rule for rule in profile.non_interference_rules):
        issues.append("probe bundle must preserve retire_ready behavior")
    if not any("same cpu_v01_fpga_top ports" in rule for rule in profile.non_interference_rules):
        issues.append("probe bundle must preserve release top-level ports")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    for signal in profile.signals:
        if signal.rtl_token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing probe source {signal.rtl_token}")

    doc = _read_if_exists(root / FPGA_PROBE_BUNDLES_DOC)
    for token in (
        "Story: I25-S03",
        FPGA_PROBE_BUNDLES_TOOL,
        "GAO",
        "ILA",
        "clock_reset",
        "status_packet",
        "memory_handshake",
        "probe_pcc_cursor_low",
        "probe_pc_slot",
        "probe_retire_count",
        "probe_fault_code",
        "probe_pass_led",
        "probe_fail_led",
        "probe_heartbeat",
        "probe_imem_req_valid",
        "probe_dmem_req_valid",
        "probe_tagmem_req_valid",
        "first_fault",
        "retire_ready",
        "release build",
    ):
        if token not in doc:
            issues.append(f"{FPGA_PROBE_BUNDLES_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

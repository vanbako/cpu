"""FPGA DDR controller wrapper and calibration visibility profile.

Owner stories:
- I29-S02: integrate the DDR controller wrapper and calibration visibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_external_memory, fpga_reset_cdc


JsonValue = Any

FPGA_DDR_WRAPPER_STORY = "I29-S02"
FPGA_DDR_WRAPPER_DOC = Path("docs/implementation/fpga-ddr-wrapper.md")
FPGA_DDR_WRAPPER_TOOL = "python tools\\fpga_ddr_wrapper.py --check"
FPGA_DDR_GATE_RTL = Path("rtl/cpu_v01_fpga_ddr_calibration_gate.sv")
FPGA_DDR_GATE_TB = Path("rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv")
FPGA_DDR_WRAPPER_STATUS = "rtl_calibration_gate_board_ip_blocked"


@dataclass(frozen=True)
class DdrVisibilitySignal:
    name: str
    width: str
    source: str
    visible_use: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("DDR visibility signal name must not be empty")
        if not self.width:
            raise ValueError("DDR visibility signal width must not be empty")
        if not self.source:
            raise ValueError("DDR visibility signal source must not be empty")
        if not self.visible_use:
            raise ValueError("DDR visibility signal visible_use must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "width": self.width,
            "source": self.source,
            "visible_use": self.visible_use,
        }


@dataclass(frozen=True)
class DdrGateRule:
    name: str
    condition: str
    behavior: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("DDR gate rule name must not be empty")
        if not self.condition:
            raise ValueError("DDR gate rule condition must not be empty")
        if not self.behavior:
            raise ValueError("DDR gate rule behavior must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "condition": self.condition,
            "behavior": self.behavior,
        }


@dataclass(frozen=True)
class FpgaDdrWrapperProfile:
    story: str
    status: str
    boundary_gate: str
    reset_cdc_gate: str
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    visibility_signals: tuple[DdrVisibilitySignal, ...]
    gate_rules: tuple[DdrGateRule, ...]
    integration_blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def visibility_by_name(self, name: str) -> DdrVisibilitySignal:
        normalized = name.lower()
        for signal in self.visibility_signals:
            if signal.name.lower() == normalized:
                return signal
        raise KeyError(name)

    def rule_by_name(self, name: str) -> DdrGateRule:
        normalized = name.lower()
        for rule in self.gate_rules:
            if rule.name.lower() == normalized:
                return rule
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "boundary_gate": self.boundary_gate,
            "reset_cdc_gate": self.reset_cdc_gate,
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "visibility_signals": [signal.as_dict() for signal in self.visibility_signals],
            "gate_rules": [rule.as_dict() for rule in self.gate_rules],
            "integration_blockers": list(self.integration_blockers),
            "handoffs": list(self.handoffs),
        }


def fpga_ddr_wrapper_profile() -> FpgaDdrWrapperProfile:
    return FpgaDdrWrapperProfile(
        story=FPGA_DDR_WRAPPER_STORY,
        status=FPGA_DDR_WRAPPER_STATUS,
        boundary_gate=fpga_external_memory.FPGA_EXTERNAL_MEMORY_TOOL,
        reset_cdc_gate=fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
        rtl_sources=(
            "rtl/cpu_v01_pkg.sv",
            FPGA_DDR_GATE_RTL.as_posix(),
            FPGA_DDR_GATE_TB.as_posix(),
        ),
        verilator_commands=(
            "verilator --lint-only --timing --top-module cpu_v01_fpga_ddr_calibration_gate_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_ddr_calibration_gate.sv "
            "rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv",
        ),
        visibility_signals=_visibility_signals(),
        gate_rules=_gate_rules(),
        integration_blockers=(
            "vendor DDR controller IP, physical pins, byte lanes, and training parameters are not committed",
            "ddr_ui_clk and ddr_ui_reset still need I28-S02 reset/CDC treatment before top-level use",
            "cpu_v01_fpga_top still needs an external-memory decoder path before DDR data traffic is live",
            "UART/status packet placement for DDR calibration fields is reserved but not assigned",
            "Gowin reports and board evidence must exist before this is claimed as board-calibrated DDR",
        ),
        handoffs=(
            "I29-S03 uses status_controller_ready_o and fail_visible_o for memory-test firmware progress",
            "I29-S04 decides coherent/cacheable and capability-tag policy before off-BRAM capability traffic",
            "I29-S05 archives calibration, timeout, memory-test, UART/status, timing, and bitstream evidence",
        ),
    )


def fpga_ddr_wrapper_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_ddr_wrapper_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_ddr_wrapper_verilator_commands() -> tuple[str, ...]:
    return fpga_ddr_wrapper_profile().verilator_commands


def render_fpga_ddr_wrapper(profile: FpgaDdrWrapperProfile | None = None) -> str:
    if profile is None:
        profile = fpga_ddr_wrapper_profile()
    lines = [
        "# FPGA DDR Wrapper",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        "",
        "## Visibility Signals",
        "",
        "| Signal | Width | Source | Use |",
        "| --- | --- | --- | --- |",
    ]
    for signal in profile.visibility_signals:
        lines.append(
            f"| `{signal.name}` | `{signal.width}` | {signal.source} | {signal.visible_use} |"
        )
    lines.extend(["", "## Gate Rules", ""])
    lines.extend(f"- `{rule.name}`: {rule.behavior}." for rule in profile.gate_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_ddr_wrapper(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_ddr_wrapper_profile()
    issues: list[str] = []

    if profile.story != FPGA_DDR_WRAPPER_STORY:
        issues.append(f"DDR wrapper story must be {FPGA_DDR_WRAPPER_STORY}")
    if profile.status != FPGA_DDR_WRAPPER_STATUS:
        issues.append(f"DDR wrapper status must be {FPGA_DDR_WRAPPER_STATUS}")
    if profile.boundary_gate != fpga_external_memory.FPGA_EXTERNAL_MEMORY_TOOL:
        issues.append("DDR wrapper must depend on the I29-S01 external-memory boundary")
    if profile.reset_cdc_gate != fpga_reset_cdc.FPGA_RESET_CDC_TOOL:
        issues.append("DDR wrapper must depend on the I28-S02 reset/CDC audit")

    issues.extend(fpga_external_memory.validate_fpga_external_memory(root))
    issues.extend(fpga_reset_cdc.validate_fpga_reset_cdc(root))

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing DDR wrapper RTL source {source}")

    visibility_names = {signal.name for signal in profile.visibility_signals}
    for required in (
        "status_calibration_done_o",
        "status_calibration_error_o",
        "status_init_in_progress_o",
        "status_controller_ready_o",
        "status_access_gate_closed_o",
        "status_timeout_o",
        "status_error_code_o",
        "fail_visible_o",
    ):
        if required not in visibility_names:
            issues.append(f"missing DDR visibility signal {required}")

    rule_names = {rule.name for rule in profile.gate_rules}
    for required in (
        "gate_until_controller_ready",
        "pass_ready_requests",
        "controller_error_fault",
        "calibration_timeout_visible_fail",
        "reset_request_clears_sticky_status",
    ):
        if required not in rule_names:
            issues.append(f"missing DDR gate rule {required}")

    if not any("cpu_v01_fpga_top still needs" in blocker for blocker in profile.integration_blockers):
        issues.append("DDR wrapper must preserve the top-level decoder integration blocker")
    if not any("I29-S05" in handoff for handoff in profile.handoffs):
        issues.append("DDR wrapper must hand off board evidence to I29-S05")

    issues.extend(_validate_files(root, profile))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"DDR wrapper profile is not JSON serializable: {exc}")

    return tuple(issues)


def _visibility_signals() -> tuple[DdrVisibilitySignal, ...]:
    return (
        DdrVisibilitySignal(
            "status_calibration_done_o",
            "1",
            "DDR controller calibration_done_i",
            "UART/status or probe bit showing DDR training completed.",
        ),
        DdrVisibilitySignal(
            "status_calibration_error_o",
            "1",
            "DDR controller calibration_error_i",
            "Visible failure bit when calibration fails.",
        ),
        DdrVisibilitySignal(
            "status_init_in_progress_o",
            "1",
            "DDR controller init_in_progress_i",
            "Visible progress bit while DDR training is active.",
        ),
        DdrVisibilitySignal(
            "status_controller_ready_o",
            "1",
            "derived calibration gate",
            "CPU access may pass to the controller only when this is set.",
        ),
        DdrVisibilitySignal(
            "status_access_gate_closed_o",
            "1",
            "derived calibration gate",
            "Visible reason that CPU external-memory traffic is blocked.",
        ),
        DdrVisibilitySignal(
            "status_timeout_o",
            "1",
            "calibration timeout counter",
            "Visible failure bit when calibration does not complete in time.",
        ),
        DdrVisibilitySignal(
            "status_error_code_o",
            "16",
            "sticky wrapper error latch",
            "Normalized calibration, timeout, or controller response error code.",
        ),
        DdrVisibilitySignal(
            "fail_visible_o",
            "1",
            "calibration gate",
            "LED, UART/status packet, or probe failure input for board triage.",
        ),
    )


def _gate_rules() -> tuple[DdrGateRule, ...]:
    return (
        DdrGateRule(
            "gate_until_controller_ready",
            "controller_ready is false",
            "CPU requests are not forwarded and instead receive a precise ACCESS_FAULT",
        ),
        DdrGateRule(
            "pass_ready_requests",
            "controller_ready is true and no request is outstanding",
            "one CPU request is forwarded to the DDR controller adapter",
        ),
        DdrGateRule(
            "controller_error_fault",
            "the DDR controller adapter returns ctrl_rsp_error_i",
            "the response becomes a precise ACCESS_FAULT and fail_visible_o is asserted",
        ),
        DdrGateRule(
            "calibration_timeout_visible_fail",
            "init_in_progress_i stays high beyond CALIBRATION_TIMEOUT_CYCLES",
            "status_timeout_o, status_error_code_o, and fail_visible_o assert",
        ),
        DdrGateRule(
            "reset_request_clears_sticky_status",
            "firmware or debug asserts reset_request_i",
            "controller_reset_o asserts and sticky timeout/controller-error state clears",
        ),
    )


def _validate_files(root: Path, profile: FpgaDdrWrapperProfile) -> tuple[str, ...]:
    issues: list[str] = []
    rtl = _read_if_exists(root / FPGA_DDR_GATE_RTL)
    tb = _read_if_exists(root / FPGA_DDR_GATE_TB)
    doc = _read_if_exists(root / FPGA_DDR_WRAPPER_DOC)

    for token in (
        "module cpu_v01_fpga_ddr_calibration_gate",
        "parameter int CALIBRATION_TIMEOUT_CYCLES = 25_000_000",
        "calibration_done_i",
        "calibration_error_i",
        "init_in_progress_i",
        "controller_ready",
        "assign ctrl_req_valid_o = cpu_req_valid_i && controller_ready && !outstanding_q",
        "assign status_access_gate_closed_o = !controller_ready",
        "assign fail_visible_o = calibration_error_i || timeout_q || controller_error_seen_q",
        "EXC_ACCESS_FAULT",
        "controller_reset_o",
        "status_timeout_o",
        "status_error_code_o",
    ):
        if token not in rtl:
            issues.append(f"{FPGA_DDR_GATE_RTL.as_posix()} missing {token}")

    for token in (
        "module cpu_v01_fpga_ddr_calibration_gate_tb",
        ".CALIBRATION_TIMEOUT_CYCLES(4)",
        "FPGA DDR calibration gate forwarded request before controller_ready",
        "FPGA DDR calibration gate did not expose controller_ready",
        "FPGA DDR calibration gate did not convert controller error to CPU fault",
        "FPGA DDR calibration gate did not fail visibly on calibration timeout",
        "FPGA DDR calibration gate did not forward reset_request",
    ):
        if token not in tb:
            issues.append(f"{FPGA_DDR_GATE_TB.as_posix()} missing {token}")

    for token in (
        "Story: I29-S02",
        FPGA_DDR_WRAPPER_TOOL,
        fpga_external_memory.FPGA_EXTERNAL_MEMORY_TOOL,
        fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
        "rtl/cpu_v01_fpga_ddr_calibration_gate.sv",
        "rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv",
        "calibration_done",
        "calibration_error",
        "controller_ready",
        "access_gate_closed",
        "fail_visible_o",
        "ACCESS_FAULT",
        "UART/status",
        "board-specific DDR IP",
        "cpu_v01_fpga_top still needs an external-memory decoder",
        "I29-S03",
        "I29-S04",
        "I29-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_DDR_WRAPPER_DOC.as_posix()} missing {token}")

    if not profile.verilator_commands or "cpu_v01_fpga_ddr_calibration_gate_tb" not in profile.verilator_commands[0]:
        issues.append("DDR wrapper profile must name the calibration gate Verilator command")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

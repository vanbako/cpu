"""FPGA 720p scanout simulation and evidence gate.

Owner stories:
- I35-S05: gate 720p scanout simulation, lint, timing, and resource evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_gowin_reports, fpga_video_mmio, fpga_video_output, fpga_video_timing


JsonValue = Any

FPGA_VIDEO_SCANOUT_GATE_STORY = "I35-S05"
FPGA_VIDEO_SCANOUT_GATE_DOC = Path("docs/implementation/fpga-video-scanout-gate.md")
FPGA_VIDEO_SCANOUT_GATE_TOOL = "python tools\\fpga_video_scanout_gate.py --check"
FPGA_VIDEO_SCANOUT_GATE_TESTBENCH = Path("rtl/cpu_v01_fpga_video_scanout_gate_tb.sv")
FPGA_VIDEO_SCANOUT_GATE_TEST = Path(
    "tests/conformance/test_i35_s05_fpga_video_scanout_gate.py"
)
FPGA_VIDEO_SCANOUT_GATE_VERILATOR_COMMAND = (
    "verilator --lint-only --timing --top-module cpu_v01_fpga_video_scanout_gate_tb "
    "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
    "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
    "rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_video_timing.sv "
    "rtl/cpu_v01_fpga_video_output_boundary.sv rtl/cpu_v01_fpga_top.sv "
    "rtl/cpu_v01_fpga_video_scanout_gate_tb.sv"
)

VIDEO_PIXEL_CLOCK_EXPECTED_MHZ = 74.25
VIDEO_PIXEL_CLOCK_TOLERANCE_MHZ = 0.05
VIDEO_CDC_WARNING_TOKENS = (
    "cdc",
    "clock domain",
    "asynchronous path",
    "unsynchronized",
    "metastability",
)


@dataclass(frozen=True)
class VideoScanoutGateCheck:
    name: str
    requirement: str
    evidence: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "requirement": self.requirement,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class VideoScanoutGateProfile:
    story: str
    timing_gate: str
    output_gate: str
    mmio_gate: str
    report_gate: str
    validator: str
    testbench: str
    active_width: int
    active_height: int
    h_total: int
    v_total: int
    pixel_clock_hz: int
    vblank_start_cycles: int
    frame_cycles: int
    verilator_commands: tuple[str, ...]
    evidence_checks: tuple[VideoScanoutGateCheck, ...]
    report_fields: tuple[str, ...]
    cdc_warning_tokens: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "timing_gate": self.timing_gate,
            "output_gate": self.output_gate,
            "mmio_gate": self.mmio_gate,
            "report_gate": self.report_gate,
            "validator": self.validator,
            "testbench": self.testbench,
            "active_width": self.active_width,
            "active_height": self.active_height,
            "h_total": self.h_total,
            "v_total": self.v_total,
            "pixel_clock_hz": self.pixel_clock_hz,
            "vblank_start_cycles": self.vblank_start_cycles,
            "frame_cycles": self.frame_cycles,
            "verilator_commands": list(self.verilator_commands),
            "evidence_checks": [check.as_dict() for check in self.evidence_checks],
            "report_fields": list(self.report_fields),
            "cdc_warning_tokens": list(self.cdc_warning_tokens),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class VideoScanoutGateSummary:
    active_pixels: int
    hsync_pixels: int
    vsync_pixels: int
    vblank_pixels: int
    vblank_start_cycle: int
    frame_cycles: int
    frames_completed: int
    final_h_count: int
    final_v_count: int
    irq_asserted_on_vblank: bool
    irq_cleared_after_ack: bool
    pattern_select: int
    background_rgb: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "active_pixels": self.active_pixels,
            "hsync_pixels": self.hsync_pixels,
            "vsync_pixels": self.vsync_pixels,
            "vblank_pixels": self.vblank_pixels,
            "vblank_start_cycle": self.vblank_start_cycle,
            "frame_cycles": self.frame_cycles,
            "frames_completed": self.frames_completed,
            "final_h_count": self.final_h_count,
            "final_v_count": self.final_v_count,
            "irq_asserted_on_vblank": self.irq_asserted_on_vblank,
            "irq_cleared_after_ack": self.irq_cleared_after_ack,
            "pattern_select": self.pattern_select,
            "background_rgb": self.background_rgb,
        }


@dataclass(frozen=True)
class VideoScanoutReportAudit:
    status: str
    message: str
    gowin_status: str
    video_clock_frequency_mhz: float | None
    unconstrained_paths: int
    utilization_metrics: tuple[str, ...]
    cdc_warning_lines: tuple[str, ...]
    missing_fields: tuple[str, ...]
    policy_violations: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == fpga_gowin_reports.GOWIN_REPORTS_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "gowin_status": self.gowin_status,
            "video_clock_frequency_mhz": self.video_clock_frequency_mhz,
            "unconstrained_paths": self.unconstrained_paths,
            "utilization_metrics": list(self.utilization_metrics),
            "cdc_warning_lines": list(self.cdc_warning_lines),
            "missing_fields": list(self.missing_fields),
            "policy_violations": list(self.policy_violations),
            "actions": list(self.actions),
        }


def fpga_video_scanout_gate_profile() -> VideoScanoutGateProfile:
    timing = fpga_video_timing.fpga_video_timing_profile()
    return VideoScanoutGateProfile(
        story=FPGA_VIDEO_SCANOUT_GATE_STORY,
        timing_gate=fpga_video_timing.FPGA_VIDEO_TIMING_TOOL,
        output_gate=fpga_video_output.FPGA_VIDEO_OUTPUT_TOOL,
        mmio_gate=fpga_video_mmio.FPGA_VIDEO_MMIO_TOOL,
        report_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        validator=FPGA_VIDEO_SCANOUT_GATE_TOOL,
        testbench=FPGA_VIDEO_SCANOUT_GATE_TESTBENCH.as_posix(),
        active_width=timing.active_width,
        active_height=timing.active_height,
        h_total=timing.h_total,
        v_total=timing.v_total,
        pixel_clock_hz=timing.pixel_clock_hz,
        vblank_start_cycles=timing.active_height * timing.h_total,
        frame_cycles=timing.h_total * timing.v_total,
        verilator_commands=(FPGA_VIDEO_SCANOUT_GATE_VERILATOR_COMMAND,),
        evidence_checks=(
            VideoScanoutGateCheck(
                "exact_720p_frame_timing",
                "1280x720 active pixels with 1650x750 total timing and exact sync/vblank counts",
                "fpga_video_timing.summarize_one_frame and cpu_v01_fpga_video_timing_tb",
            ),
            VideoScanoutGateCheck(
                "combined_scanout_mmio_irq",
                "MMIO-programmed scanout reaches vblank, raises video_vblank IRQ, and reads frame count",
                FPGA_VIDEO_SCANOUT_GATE_TESTBENCH.as_posix(),
            ),
            VideoScanoutGateCheck(
                "verilator_lint_inventory",
                "combined lint command includes timing, output-boundary, video-MMIO, and gate testbench sources",
                FPGA_VIDEO_SCANOUT_GATE_VERILATOR_COMMAND,
            ),
            VideoScanoutGateCheck(
                "gowin_report_fields",
                "report audit extracts video pixel clock, utilization, unconstrained paths, and warning lines",
                "audit_video_scanout_reports",
            ),
            VideoScanoutGateCheck(
                "cdc_warning_policy",
                "CDC or async warning lines in generated reports are classified as gate failures",
                "unexpected_video_cdc_warning",
            ),
        ),
        report_fields=(
            "video_pixel_clk clock summary",
            "worst slack",
            "utilization",
            "unconstrained paths",
            "warnings",
            "bitstream identity",
        ),
        cdc_warning_tokens=VIDEO_CDC_WARNING_TOKENS,
        handoffs=(
            "I35-S06 consumes this gate before claiming board-visible scanout evidence",
            "I36-S04 consumes vblank behavior for atomic plane descriptor updates",
            "I28-S03 remains the underlying Gowin report parser for timing and resource evidence",
        ),
    )


def simulate_video_scanout_gate_summary() -> VideoScanoutGateSummary:
    profile = fpga_video_scanout_gate_profile()
    frame_summary = fpga_video_timing.summarize_one_frame()
    mmio = fpga_video_mmio.initial_video_mmio_state()
    mmio = mmio.write(
        0x00,
        fpga_video_mmio.VIDEO_CONTROL_SCANOUT_ENABLE
        | fpga_video_mmio.VIDEO_CONTROL_OUTPUT_ENABLE,
    )
    mmio = mmio.write(0x08, fpga_video_timing.PATTERN_CHECKERBOARD)
    mmio = mmio.write(0x09, 0x123456)
    mmio = mmio.write(0x03, fpga_video_mmio.VIDEO_IRQ_VBLANK)

    mmio = mmio.tick(
        vblank=False,
        frame_count=0,
        line_count=profile.active_height - 1,
        pixel_count=profile.h_total - 1,
    )
    mmio = mmio.tick(
        vblank=True,
        frame_count=0,
        line_count=profile.active_height,
        pixel_count=0,
    )
    irq_asserted_on_vblank = mmio.irq_asserted
    mmio = mmio.tick(vblank=False, frame_count=1, line_count=0, pixel_count=0)
    after_ack = mmio.write(0x04, fpga_video_mmio.VIDEO_IRQ_VBLANK)

    return VideoScanoutGateSummary(
        active_pixels=frame_summary.active_pixels,
        hsync_pixels=frame_summary.hsync_pixels,
        vsync_pixels=frame_summary.vsync_pixels,
        vblank_pixels=frame_summary.vblank_pixels,
        vblank_start_cycle=profile.vblank_start_cycles,
        frame_cycles=profile.frame_cycles,
        frames_completed=1,
        final_h_count=0,
        final_v_count=0,
        irq_asserted_on_vblank=irq_asserted_on_vblank,
        irq_cleared_after_ack=not after_ack.irq_asserted,
        pattern_select=after_ack.test_pattern,
        background_rgb=after_ack.bg_color,
    )


def audit_video_scanout_reports(
    build_root: Path,
    *,
    profile_id: str = fpga_gowin_reports.FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
) -> VideoScanoutReportAudit:
    base = fpga_gowin_reports.audit_gowin_reports(build_root, profile_id=profile_id)
    parsed = base.parse
    video_clock = _find_video_clock(parsed.clock_summary)
    utilization_metrics = tuple(metric.name for metric in parsed.utilization)
    cdc_warning_lines = _cdc_warning_lines(parsed.warning_lines)

    missing_fields: list[str] = []
    policy_violations = list(base.policy_violations)

    if base.status == fpga_gowin_reports.GOWIN_REPORTS_BLOCKED:
        return VideoScanoutReportAudit(
            status=fpga_gowin_reports.GOWIN_REPORTS_BLOCKED,
            message="FPGA video scanout gate is blocked until the Gowin report bundle exists.",
            gowin_status=base.status,
            video_clock_frequency_mhz=None if video_clock is None else video_clock.frequency_mhz,
            unconstrained_paths=parsed.unconstrained_paths,
            utilization_metrics=utilization_metrics,
            cdc_warning_lines=cdc_warning_lines,
            missing_fields=tuple(base.missing_reports),
            policy_violations=tuple(policy_violations),
            actions=(
                "run the I35-S05 Verilator lint command",
                "run Gowin and audit the report bundle",
            ),
        )

    if video_clock is None:
        missing_fields.append("video_pixel_clk_clock_summary")
    elif video_clock.frequency_mhz is None:
        policy_violations.append("missing_video_pixel_clk_frequency")
    elif abs(video_clock.frequency_mhz - VIDEO_PIXEL_CLOCK_EXPECTED_MHZ) > VIDEO_PIXEL_CLOCK_TOLERANCE_MHZ:
        policy_violations.append("video_pixel_clk_frequency_mismatch")

    if not utilization_metrics:
        missing_fields.append("utilization")
    if parsed.unconstrained_paths != 0:
        policy_violations.append("unconstrained_paths_present")
    if cdc_warning_lines:
        policy_violations.append("unexpected_video_cdc_warning")

    policy_violations = sorted(set(policy_violations))
    status = (
        fpga_gowin_reports.GOWIN_REPORTS_FAILED
        if missing_fields or policy_violations or base.status != fpga_gowin_reports.GOWIN_REPORTS_PASSED
        else fpga_gowin_reports.GOWIN_REPORTS_PASSED
    )
    return VideoScanoutReportAudit(
        status=status,
        message=(
            "FPGA video scanout report gate passed."
            if status == fpga_gowin_reports.GOWIN_REPORTS_PASSED
            else "FPGA video scanout report gate found policy violations."
        ),
        gowin_status=base.status,
        video_clock_frequency_mhz=None if video_clock is None else video_clock.frequency_mhz,
        unconstrained_paths=parsed.unconstrained_paths,
        utilization_metrics=utilization_metrics,
        cdc_warning_lines=cdc_warning_lines,
        missing_fields=tuple(missing_fields),
        policy_violations=tuple(policy_violations),
        actions=(
            "fix scanout timing, constraints, CDC warnings, or report generation",
            "rerun Verilator lint and Gowin report audit",
        )
        if status != fpga_gowin_reports.GOWIN_REPORTS_PASSED
        else ("archive report fields for I35-S06 board scanout evidence",),
    )


def fpga_video_scanout_gate_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_video_scanout_gate_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_video_scanout_gate() -> str:
    profile = fpga_video_scanout_gate_profile()
    lines = [
        "# FPGA Video Scanout Gate",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"Mode: `{profile.active_width}x{profile.active_height}`",
        f"Frame cycles: `{profile.frame_cycles}`",
        f"Vblank start: `{profile.vblank_start_cycles}`",
        "",
        "## Evidence Checks",
        "",
        "| Check | Requirement |",
        "| --- | --- |",
    ]
    for check in profile.evidence_checks:
        lines.append(f"| `{check.name}` | {check.requirement} |")
    return "\n".join(lines)


def validate_fpga_video_scanout_gate(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_scanout_gate_profile()
    issues: list[str] = []

    timing_issues = fpga_video_timing.validate_fpga_video_timing(root)
    issues.extend(f"I35-S02 prerequisite: {issue}" for issue in timing_issues)
    output_issues = fpga_video_output.validate_fpga_video_output(root)
    issues.extend(f"I35-S03 prerequisite: {issue}" for issue in output_issues)
    mmio_issues = fpga_video_mmio.validate_fpga_video_mmio(root)
    issues.extend(f"I35-S04 prerequisite: {issue}" for issue in mmio_issues)
    report_issues = fpga_gowin_reports.validate_fpga_gowin_reports(root)
    issues.extend(f"I28-S03 prerequisite: {issue}" for issue in report_issues)

    if profile.story != FPGA_VIDEO_SCANOUT_GATE_STORY:
        issues.append(f"video scanout gate story must be {FPGA_VIDEO_SCANOUT_GATE_STORY}")
    if (profile.active_width, profile.active_height) != (1280, 720):
        issues.append("video scanout gate must remain 1280x720")
    if (profile.h_total, profile.v_total) != (1650, 750):
        issues.append("video scanout gate totals must remain 1650x750")
    if profile.pixel_clock_hz != 74_250_000:
        issues.append("video scanout gate pixel clock must remain 74.25 MHz")
    if profile.vblank_start_cycles != 1_188_000:
        issues.append("video scanout vblank start must be 720*1650 cycles")
    if profile.frame_cycles != 1_237_500:
        issues.append("video scanout frame length must be 750*1650 cycles")
    if "video_pixel_clk clock summary" not in profile.report_fields:
        issues.append("video scanout gate must require video pixel clock report evidence")
    if "cdc" not in profile.cdc_warning_tokens:
        issues.append("video scanout gate must classify CDC warnings")

    summary = simulate_video_scanout_gate_summary()
    if summary.active_pixels != 921_600:
        issues.append("video scanout summary active-pixel count mismatch")
    if summary.hsync_pixels != 30_000:
        issues.append("video scanout summary hsync count mismatch")
    if summary.vsync_pixels != 8_250:
        issues.append("video scanout summary vsync count mismatch")
    if summary.vblank_pixels != 49_500:
        issues.append("video scanout summary vblank count mismatch")
    if summary.vblank_start_cycle != profile.vblank_start_cycles:
        issues.append("video scanout summary vblank start mismatch")
    if summary.frames_completed != 1 or summary.final_h_count != 0 or summary.final_v_count != 0:
        issues.append("video scanout summary must wrap exactly one frame")
    if not summary.irq_asserted_on_vblank:
        issues.append("video scanout summary did not assert vblank IRQ")
    if not summary.irq_cleared_after_ack:
        issues.append("video scanout summary did not clear vblank IRQ")

    if not (root / FPGA_VIDEO_SCANOUT_GATE_TESTBENCH).exists():
        issues.append(f"missing RTL testbench {FPGA_VIDEO_SCANOUT_GATE_TESTBENCH.as_posix()}")
    tb = _read_if_exists(root / FPGA_VIDEO_SCANOUT_GATE_TESTBENCH)
    for token in (
        "module cpu_v01_fpga_video_scanout_gate_tb",
        "VBLANK_START_CYCLES = 720 * 1650",
        "FULL_FRAME_CYCLES = 750 * 1650",
        "cpu_v01_fpga_video_output_boundary video_output",
        "cpu_v01_fpga_video_mmio video_mmio",
        "FPGA video scanout gate did not reach vblank",
        "FPGA video scanout gate did not raise vblank IRQ",
        "FPGA video scanout gate frame count readback mismatch",
        "FPGA video scanout gate unexpected underflow count",
    ):
        if token not in tb:
            issues.append(f"{FPGA_VIDEO_SCANOUT_GATE_TESTBENCH.as_posix()} missing {token}")

    doc = _read_if_exists(root / FPGA_VIDEO_SCANOUT_GATE_DOC)
    for token in (
        "Story: I35-S05",
        FPGA_VIDEO_SCANOUT_GATE_TOOL,
        "python tools\\fpga_video_timing.py --check",
        "python tools\\fpga_video_output.py --check",
        "python tools\\fpga_video_mmio.py --check",
        "python tools\\fpga_gowin_reports.py --check",
        "cpu_v01_fpga_video_scanout_gate_tb",
        "1280x720",
        "74.25 MHz",
        "vblank IRQ",
        "video_pixel_clk",
        "utilization",
        "unconstrained paths",
        "unexpected_video_cdc_warning",
        "I35-S06",
        "I36-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_SCANOUT_GATE_DOC.as_posix()} missing {token}")

    default_reports = audit_video_scanout_reports(
        root / fpga_gowin_reports.fpga_gowin_report_parser_profile().build_root
    )
    if default_reports.status != fpga_gowin_reports.GOWIN_REPORTS_BLOCKED:
        issues.append("default video scanout report audit must be blocked without reports")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(summary.as_dict(), sort_keys=True)
        json.dumps(default_reports.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video scanout gate objects are not JSON serializable: {exc}")

    return tuple(issues)


def _find_video_clock(
    clocks: tuple[fpga_gowin_reports.ClockSummary, ...],
) -> fpga_gowin_reports.ClockSummary | None:
    for clock in clocks:
        name = clock.name.lower()
        source = clock.source.lower()
        if name == fpga_video_output.VIDEO_PIXEL_CLOCK_NAME.lower() or "video_pixel" in source:
            return clock
    return None


def _cdc_warning_lines(lines: tuple[str, ...]) -> tuple[str, ...]:
    matches: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(token in lower for token in VIDEO_CDC_WARNING_TOKENS):
            matches.append(line)
    return tuple(matches)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

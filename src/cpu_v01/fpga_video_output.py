"""FPGA video output clock/reset/CDC and board-boundary profile.

Owner stories:
- I35-S03: add scanout clock, reset, CDC, and board-output boundary handling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_clock_profiles, fpga_reset_cdc, fpga_video_timing


JsonValue = Any

FPGA_VIDEO_OUTPUT_STORY = "I35-S03"
FPGA_VIDEO_OUTPUT_DOC = Path("docs/implementation/fpga-video-output-boundary.md")
FPGA_VIDEO_OUTPUT_TOOL = "python tools\\fpga_video_output.py --check"
FPGA_VIDEO_OUTPUT_PROFILE_NAME = "cpu_v01_fpga_video_output_boundary"
VIDEO_PIXEL_CLOCK_HZ = 74_250_000
VIDEO_PIXEL_CLOCK_NAME = "video_pixel_clk"
VIDEO_RESET_SYNC_STAGES = 2


@dataclass(frozen=True)
class VideoOutputSignal:
    name: str
    width_bits: int
    role: str
    board_handoff: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "width_bits": self.width_bits,
            "role": self.role,
            "board_handoff": self.board_handoff,
        }


@dataclass(frozen=True)
class VideoCdcRule:
    name: str
    source_domain: str
    destination_domain: str
    handling: str
    status: str
    evidence_tokens: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source_domain": self.source_domain,
            "destination_domain": self.destination_domain,
            "handling": self.handling,
            "status": self.status,
            "evidence_tokens": list(self.evidence_tokens),
        }


@dataclass(frozen=True)
class VideoOutputProfile:
    story: str
    timing_gate: str
    clock_profile_gate: str
    reset_cdc_gate: str
    output_module: str
    testbench_module: str
    pixel_clock_name: str
    pixel_clock_hz: int
    pixel_clock_source: str
    generated_clock_sdc: str
    reset_sync_stages: int
    output_signals: tuple[VideoOutputSignal, ...]
    cdc_rules: tuple[VideoCdcRule, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    board_handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def signal_by_name(self, name: str) -> VideoOutputSignal:
        for signal in self.output_signals:
            if signal.name == name:
                return signal
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "timing_gate": self.timing_gate,
            "clock_profile_gate": self.clock_profile_gate,
            "reset_cdc_gate": self.reset_cdc_gate,
            "output_module": self.output_module,
            "testbench_module": self.testbench_module,
            "pixel_clock_name": self.pixel_clock_name,
            "pixel_clock_hz": self.pixel_clock_hz,
            "pixel_clock_source": self.pixel_clock_source,
            "generated_clock_sdc": self.generated_clock_sdc,
            "reset_sync_stages": self.reset_sync_stages,
            "output_signals": [signal.as_dict() for signal in self.output_signals],
            "cdc_rules": [rule.as_dict() for rule in self.cdc_rules],
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "board_handoffs": list(self.board_handoffs),
            "non_goals": list(self.non_goals),
        }


def fpga_video_output_profile() -> VideoOutputProfile:
    return VideoOutputProfile(
        story=FPGA_VIDEO_OUTPUT_STORY,
        timing_gate=fpga_video_timing.FPGA_VIDEO_TIMING_TOOL,
        clock_profile_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        reset_cdc_gate=fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
        output_module="cpu_v01_fpga_video_output_boundary",
        testbench_module="cpu_v01_fpga_video_output_boundary_tb",
        pixel_clock_name=VIDEO_PIXEL_CLOCK_NAME,
        pixel_clock_hz=VIDEO_PIXEL_CLOCK_HZ,
        pixel_clock_source="board_clk_i through future video PLL wrapper",
        generated_clock_sdc=(
            "create_generated_clock -name video_pixel_clk -source [get_ports {board_clk_i}] "
            "-multiply_by 297 -divide_by 100 [get_pins {u_video_pll/clkout}]"
        ),
        reset_sync_stages=VIDEO_RESET_SYNC_STAGES,
        output_signals=_output_signals(),
        cdc_rules=_cdc_rules(),
        rtl_sources=(
            "rtl/cpu_v01_fpga_video_timing.sv",
            "rtl/cpu_v01_fpga_video_output_boundary.sv",
            "rtl/cpu_v01_fpga_video_output_boundary_tb.sv",
        ),
        verilator_commands=fpga_video_output_verilator_commands(),
        board_handoffs=(
            "I35-S06 captures board output adapter wiring and visible/probe evidence",
            "I24-S02 or a later board constraints story maps RGB, hsync, vsync, de, and pixel clock pins",
            "I28-S03 must fail timing reports with unconstrained video_pixel_clk paths",
        ),
        non_goals=(
            "instantiate_vendor_pll_ip",
            "claim_board_pinout",
            "claim_hdmi_tmds_encoding",
            "cross_multi_bit_mmio_config_without_I35_S04_latch",
            "framebuffer_fetch",
        ),
    )


def fpga_video_output_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_video_output_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_video_output_verilator_commands() -> tuple[str, ...]:
    sources = " ".join(
        (
            "rtl/cpu_v01_pkg.sv",
            "rtl/cpu_v01_fpga_video_timing.sv",
            "rtl/cpu_v01_fpga_video_output_boundary.sv",
            "rtl/cpu_v01_fpga_video_output_boundary_tb.sv",
        )
    )
    return (
        f"verilator --lint-only --timing --top-module cpu_v01_fpga_video_output_boundary_tb {sources}",
    )


def render_fpga_video_output() -> str:
    profile = fpga_video_output_profile()
    lines = [
        "# FPGA Video Output Boundary",
        "",
        f"Story: `{profile.story}`",
        f"Module: `{profile.output_module}`",
        f"Pixel clock: `{profile.pixel_clock_name}` `{profile.pixel_clock_hz}`",
        "",
        "## Outputs",
        "",
        "| Signal | Width | Role |",
        "| --- | ---: | --- |",
    ]
    for signal in profile.output_signals:
        lines.append(f"| `{signal.name}` | {signal.width_bits} | {signal.role} |")
    return "\n".join(lines)


def validate_fpga_video_output(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_output_profile()
    issues: list[str] = []

    timing_issues = fpga_video_timing.validate_fpga_video_timing(root)
    issues.extend(f"I35-S02 prerequisite: {issue}" for issue in timing_issues)
    clock_issues = fpga_clock_profiles.validate_fpga_clock_profiles(root)
    issues.extend(f"I28-S01 prerequisite: {issue}" for issue in clock_issues)
    reset_issues = fpga_reset_cdc.validate_fpga_reset_cdc(root)
    issues.extend(f"I28-S02 prerequisite: {issue}" for issue in reset_issues)

    if profile.story != FPGA_VIDEO_OUTPUT_STORY:
        issues.append(f"video output story must be {FPGA_VIDEO_OUTPUT_STORY}")
    if profile.pixel_clock_hz != VIDEO_PIXEL_CLOCK_HZ:
        issues.append("video output pixel clock must be 74.25 MHz")
    if "-multiply_by 297 -divide_by 100" not in profile.generated_clock_sdc:
        issues.append("video output generated-clock SDC must derive 74.25 MHz from 25 MHz")
    if profile.reset_sync_stages < 2:
        issues.append("video output reset synchronizer must use at least two stages")
    for signal_name in (
        "video_rgb_o",
        "video_hsync_o",
        "video_vsync_o",
        "video_de_o",
        "video_pixel_clk_o",
        "video_output_enable_o",
    ):
        try:
            profile.signal_by_name(signal_name)
        except KeyError:
            issues.append(f"missing video board output signal {signal_name}")
    for rule_name in (
        "pixel_reset_release",
        "scanout_enable_sync",
        "output_enable_sync",
        "registered_board_outputs",
        "stable_pattern_config_boundary",
    ):
        if rule_name not in {rule.name for rule in profile.cdc_rules}:
            issues.append(f"missing video CDC rule {rule_name}")
    if "cross_multi_bit_mmio_config_without_I35_S04_latch" not in profile.non_goals:
        issues.append("video output profile must defer unsafe multi-bit MMIO CDC to I35-S04")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / "rtl" / "cpu_v01_fpga_video_output_boundary.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_video_output_boundary_tb.sv")
    for token in (
        "module cpu_v01_fpga_video_output_boundary",
        "parameter int RESET_SYNC_STAGES = 2",
        "pixel_reset_sync_q",
        "scanout_enable_sync_q",
        "output_enable_sync_q",
        "cpu_v01_fpga_video_timing u_timing",
        "assign video_pixel_clk_o = pixel_clk_i",
        "assign video_output_enable_o = output_enable_sync_q[1]",
        "video_rgb_o <= timing_de ? timing_rgb : 24'h000000",
        "video_hsync_o <= timing_hsync",
    ):
        if token not in rtl:
            issues.append(f"rtl/cpu_v01_fpga_video_output_boundary.sv missing {token}")
    for token in (
        "module cpu_v01_fpga_video_output_boundary_tb",
        "cpu_v01_fpga_video_output_boundary dut",
        "VIDEO output reset did not hold outputs blank",
        "VIDEO output enable did not blank RGB",
        "VIDEO output did not forward hsync",
        "VIDEO output did not expose pixel clock",
    ):
        if token not in tb:
            issues.append(f"rtl/cpu_v01_fpga_video_output_boundary_tb.sv missing {token}")

    doc = _read_if_exists(root / FPGA_VIDEO_OUTPUT_DOC)
    for token in (
        "Story: I35-S03",
        FPGA_VIDEO_OUTPUT_TOOL,
        "74.25 MHz",
        "create_generated_clock -name video_pixel_clk",
        "cpu_v01_fpga_video_output_boundary",
        "pixel_reset_sync_q",
        "scanout_enable_sync_q",
        "video_rgb_o",
        "video_hsync_o",
        "video_vsync_o",
        "video_de_o",
        "I35-S04",
        "I35-S06",
        "I28-S03",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_OUTPUT_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video output profile is not JSON serializable: {exc}")

    return tuple(issues)


def _output_signals() -> tuple[VideoOutputSignal, ...]:
    return (
        VideoOutputSignal("video_rgb_o", 24, "registered RGB output", "board adapter or resistor-DAC/HDMI path"),
        VideoOutputSignal("video_hsync_o", 1, "registered horizontal sync", "board adapter sync pin"),
        VideoOutputSignal("video_vsync_o", 1, "registered vertical sync", "board adapter sync pin"),
        VideoOutputSignal("video_de_o", 1, "registered active-video data enable", "display adapter data-enable pin"),
        VideoOutputSignal("video_pixel_clk_o", 1, "forwarded pixel clock", "display adapter pixel clock pin"),
        VideoOutputSignal("video_output_enable_o", 1, "synchronized output-enable status", "debug/status probe or output buffer enable"),
    )


def _cdc_rules() -> tuple[VideoCdcRule, ...]:
    return (
        VideoCdcRule(
            "pixel_reset_release",
            "board reset or PLL lock",
            VIDEO_PIXEL_CLOCK_NAME,
            "asynchronous assert and two-stage synchronized release in the pixel clock domain",
            "implemented_in_boundary_rtl",
            ("pixel_reset_sync_q", "RESET_SYNC_STAGES"),
        ),
        VideoCdcRule(
            "scanout_enable_sync",
            "SoC/MMIO control domain",
            VIDEO_PIXEL_CLOCK_NAME,
            "two-flop synchronization of the single-bit scanout enable",
            "implemented_in_boundary_rtl",
            ("scanout_enable_sync_q",),
        ),
        VideoCdcRule(
            "output_enable_sync",
            "board/debug control domain",
            VIDEO_PIXEL_CLOCK_NAME,
            "two-flop synchronization of the single-bit output blanking control",
            "implemented_in_boundary_rtl",
            ("output_enable_sync_q",),
        ),
        VideoCdcRule(
            "registered_board_outputs",
            VIDEO_PIXEL_CLOCK_NAME,
            "board output pins or adapter signals",
            "RGB, sync, data-enable, and status outputs register in the pixel clock domain",
            "implemented_in_boundary_rtl",
            ("video_rgb_o", "video_hsync_o", "video_vsync_o", "video_de_o"),
        ),
        VideoCdcRule(
            "stable_pattern_config_boundary",
            "SoC/MMIO control domain",
            VIDEO_PIXEL_CLOCK_NAME,
            "multi-bit pattern and background fields must be held stable while disabled until I35-S04 adds MMIO latch/update sequencing",
            "documented_handoff_to_I35_S04",
            ("pattern_select_i", "bg_color_i"),
        ),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

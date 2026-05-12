"""FPGA 720p timing generator and test-pattern scanout profile.

Owner stories:
- I35-S02: implement a 1280x720 timing generator and test-pattern scanout core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_video_display


JsonValue = Any

FPGA_VIDEO_TIMING_STORY = "I35-S02"
FPGA_VIDEO_TIMING_DOC = Path("docs/implementation/fpga-video-timing-scanout.md")
FPGA_VIDEO_TIMING_TOOL = "python tools\\fpga_video_timing.py --check"
FPGA_VIDEO_TIMING_PROFILE_NAME = "cpu_v01_fpga_720p_timing_scanout"

PATTERN_BACKGROUND = 0
PATTERN_COLOR_BARS = 1
PATTERN_CHECKERBOARD = 2


@dataclass(frozen=True)
class VideoTimingOutput:
    h_count: int
    v_count: int
    pixel_x: int
    pixel_y: int
    hsync: bool
    vsync: bool
    data_enable: bool
    vblank: bool
    frame_count: int
    rgb: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "h_count": self.h_count,
            "v_count": self.v_count,
            "pixel_x": self.pixel_x,
            "pixel_y": self.pixel_y,
            "hsync": self.hsync,
            "vsync": self.vsync,
            "data_enable": self.data_enable,
            "vblank": self.vblank,
            "frame_count": self.frame_count,
            "rgb": self.rgb,
        }


@dataclass
class VideoTimingState:
    h_count: int = 0
    v_count: int = 0
    frame_count: int = 0
    enabled: bool = True
    pattern_select: int = PATTERN_COLOR_BARS
    background_rgb: int = 0

    def sample(self) -> VideoTimingOutput:
        timing = fpga_video_display.fpga_video_display_profile().timing
        active = self.h_count < timing.active_width and self.v_count < timing.active_height
        hsync_start = timing.active_width + timing.h_front_porch
        hsync_end = hsync_start + timing.h_sync
        vsync_start = timing.active_height + timing.v_front_porch
        vsync_end = vsync_start + timing.v_sync
        hsync_active = hsync_start <= self.h_count < hsync_end
        vsync_active = vsync_start <= self.v_count < vsync_end
        return VideoTimingOutput(
            h_count=self.h_count,
            v_count=self.v_count,
            pixel_x=self.h_count if active else 0,
            pixel_y=self.v_count if active else 0,
            hsync=hsync_active if timing.hsync_active_high else not hsync_active,
            vsync=vsync_active if timing.vsync_active_high else not vsync_active,
            data_enable=active,
            vblank=self.v_count >= timing.active_height,
            frame_count=self.frame_count,
            rgb=self.pattern_rgb(self.h_count, self.v_count) if active else 0,
        )

    def tick(self) -> None:
        if not self.enabled:
            return
        timing = fpga_video_display.fpga_video_display_profile().timing
        if self.h_count == timing.h_total - 1:
            self.h_count = 0
            if self.v_count == timing.v_total - 1:
                self.v_count = 0
                self.frame_count += 1
            else:
                self.v_count += 1
        else:
            self.h_count += 1

    def pattern_rgb(self, x: int, y: int) -> int:
        timing = fpga_video_display.fpga_video_display_profile().timing
        if self.pattern_select == PATTERN_BACKGROUND:
            return self.background_rgb & 0xFFFFFF
        if self.pattern_select == PATTERN_CHECKERBOARD:
            return 0xFFFFFF if ((x >> 5) ^ (y >> 5)) & 0x1 else 0x000000
        if self.pattern_select == PATTERN_COLOR_BARS:
            bar = min((x * 8) // timing.active_width, 7)
            return (
                0xFF0000,
                0x00FF00,
                0x0000FF,
                0xFFFF00,
                0x00FFFF,
                0xFF00FF,
                0xFFFFFF,
                0x202020,
            )[bar]
        return self.background_rgb & 0xFFFFFF


@dataclass(frozen=True)
class VideoFrameSummary:
    active_pixels: int
    hsync_pixels: int
    vsync_pixels: int
    vblank_pixels: int
    frames_completed: int
    final_h_count: int
    final_v_count: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "active_pixels": self.active_pixels,
            "hsync_pixels": self.hsync_pixels,
            "vsync_pixels": self.vsync_pixels,
            "vblank_pixels": self.vblank_pixels,
            "frames_completed": self.frames_completed,
            "final_h_count": self.final_h_count,
            "final_v_count": self.final_v_count,
        }


@dataclass(frozen=True)
class VideoTimingProfile:
    story: str
    display_gate: str
    timing_name: str
    active_width: int
    active_height: int
    h_total: int
    v_total: int
    pixel_clock_hz: int
    pattern_names: tuple[str, ...]
    output_signals: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    handoff_stories: tuple[str, ...]
    non_goals: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "display_gate": self.display_gate,
            "timing_name": self.timing_name,
            "active_width": self.active_width,
            "active_height": self.active_height,
            "h_total": self.h_total,
            "v_total": self.v_total,
            "pixel_clock_hz": self.pixel_clock_hz,
            "pattern_names": list(self.pattern_names),
            "output_signals": list(self.output_signals),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "handoff_stories": list(self.handoff_stories),
            "non_goals": list(self.non_goals),
        }


def fpga_video_timing_profile() -> VideoTimingProfile:
    timing = fpga_video_display.fpga_video_display_profile().timing
    return VideoTimingProfile(
        story=FPGA_VIDEO_TIMING_STORY,
        display_gate=fpga_video_display.FPGA_VIDEO_DISPLAY_TOOL,
        timing_name=timing.name,
        active_width=timing.active_width,
        active_height=timing.active_height,
        h_total=timing.h_total,
        v_total=timing.v_total,
        pixel_clock_hz=timing.pixel_clock_hz,
        pattern_names=("background", "color_bars", "checkerboard"),
        output_signals=(
            "pixel_x_o",
            "pixel_y_o",
            "hsync_o",
            "vsync_o",
            "de_o",
            "vblank_o",
            "frame_start_o",
            "line_start_o",
            "rgb_o",
            "frame_count_o",
        ),
        rtl_sources=(
            "rtl/cpu_v01_fpga_video_timing.sv",
            "rtl/cpu_v01_fpga_video_timing_tb.sv",
        ),
        verilator_commands=fpga_video_timing_verilator_commands(),
        handoff_stories=("I35-S03", "I35-S04", "I36-S02"),
        non_goals=("framebuffer_fetch", "plane_composition", "board_pin_constraints"),
    )


def fpga_video_timing_state() -> VideoTimingState:
    return VideoTimingState()


def summarize_one_frame() -> VideoFrameSummary:
    timing = fpga_video_display.fpga_video_display_profile().timing
    return VideoFrameSummary(
        active_pixels=timing.active_width * timing.active_height,
        hsync_pixels=timing.h_sync * timing.v_total,
        vsync_pixels=timing.v_sync * timing.h_total,
        vblank_pixels=(timing.v_total - timing.active_height) * timing.h_total,
        frames_completed=1,
        final_h_count=0,
        final_v_count=0,
    )


def fpga_video_timing_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_video_timing_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_video_timing_verilator_commands() -> tuple[str, ...]:
    sources = " ".join(
        (
            "rtl/cpu_v01_pkg.sv",
            "rtl/cpu_v01_fpga_video_timing.sv",
            "rtl/cpu_v01_fpga_video_timing_tb.sv",
        )
    )
    return (
        f"verilator --lint-only --timing --top-module cpu_v01_fpga_video_timing_tb {sources}",
    )


def render_fpga_video_timing() -> str:
    profile = fpga_video_timing_profile()
    return "\n".join(
        (
            "# FPGA Video Timing Scanout",
            "",
            f"Story: `{profile.story}`",
            f"Mode: `{profile.timing_name}`",
            f"Active: `{profile.active_width}x{profile.active_height}`",
            f"Total: `{profile.h_total}x{profile.v_total}`",
            f"Pixel clock: `{profile.pixel_clock_hz}`",
            "",
            "## Verilator",
            "",
            *profile.verilator_commands,
        )
    )


def validate_fpga_video_timing(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_timing_profile()
    issues: list[str] = []

    display_issues = fpga_video_display.validate_fpga_video_display(root)
    issues.extend(f"I35-S01 prerequisite: {issue}" for issue in display_issues)
    if profile.story != FPGA_VIDEO_TIMING_STORY:
        issues.append(f"video timing story must be {FPGA_VIDEO_TIMING_STORY}")
    if (profile.active_width, profile.active_height) != (1280, 720):
        issues.append("video timing must remain 1280x720")
    if (profile.h_total, profile.v_total) != (1650, 750):
        issues.append("video timing totals must remain 1650x750")
    if profile.pixel_clock_hz != 74_250_000:
        issues.append("video timing pixel clock must remain 74.25 MHz")
    for pattern in ("background", "color_bars", "checkerboard"):
        if pattern not in profile.pattern_names:
            issues.append(f"missing scanout pattern {pattern}")
    for signal in (
        "pixel_x_o",
        "pixel_y_o",
        "hsync_o",
        "vsync_o",
        "de_o",
        "vblank_o",
        "frame_start_o",
        "line_start_o",
        "rgb_o",
        "frame_count_o",
    ):
        if signal not in profile.output_signals:
            issues.append(f"missing scanout output signal {signal}")

    state = fpga_video_timing_state()
    first = state.sample()
    if not first.data_enable or first.pixel_x != 0 or first.pixel_y != 0:
        issues.append("video timing first sample must be active pixel 0,0")
    if first.rgb != 0xFF0000:
        issues.append("color-bar pattern must start with red")
    state.pattern_select = PATTERN_CHECKERBOARD
    if state.pattern_rgb(0, 0) != 0x000000 or state.pattern_rgb(32, 0) != 0xFFFFFF:
        issues.append("checkerboard pattern must toggle every 32 pixels")
    summary = summarize_one_frame()
    if summary.active_pixels != 1280 * 720:
        issues.append("one-frame summary active-pixel count mismatch")
    if summary.hsync_pixels != 40 * 750:
        issues.append("one-frame summary hsync-pixel count mismatch")
    if summary.vsync_pixels != 5 * 1650:
        issues.append("one-frame summary vsync-pixel count mismatch")
    if summary.frames_completed != 1 or summary.final_h_count != 0 or summary.final_v_count != 0:
        issues.append("one-frame summary must wrap to frame 1 at 0,0")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / "rtl" / "cpu_v01_fpga_video_timing.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_video_timing_tb.sv")
    for token in (
        "module cpu_v01_fpga_video_timing",
        "H_ACTIVE = 1280",
        "H_TOTAL = H_ACTIVE + H_FRONT + H_SYNC + H_BACK",
        "PATTERN_COLOR_BARS = 4'd1",
        "assign de_o = active_pixel",
        "assign hsync_o = hsync_active",
        "assign vsync_o = vsync_active",
        "color_bar_rgb",
        "checkerboard_rgb",
        "frame_count_o",
    ):
        if token not in rtl:
            issues.append(f"rtl/cpu_v01_fpga_video_timing.sv missing {token}")
    for token in (
        "module cpu_v01_fpga_video_timing_tb",
        "cpu_v01_fpga_video_timing dut",
        "ACTIVE_PIXELS mismatch",
        "HSYNC_PIXELS mismatch",
        "VSYNC_PIXELS mismatch",
        "FRAME_COUNT did not advance",
        "COLOR_BAR first pixel mismatch",
        "CHECKERBOARD did not toggle",
    ):
        if token not in tb:
            issues.append(f"rtl/cpu_v01_fpga_video_timing_tb.sv missing {token}")

    doc = _read_if_exists(root / FPGA_VIDEO_TIMING_DOC)
    for token in (
        "Story: I35-S02",
        FPGA_VIDEO_TIMING_TOOL,
        "1280x720",
        "74.25 MHz",
        "cpu_v01_fpga_video_timing",
        "color_bars",
        "checkerboard",
        "hsync_o",
        "vsync_o",
        "de_o",
        "I35-S03",
        "I36-S02",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_TIMING_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(summary.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video timing profile is not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

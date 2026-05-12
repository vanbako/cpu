"""FPGA 720p display profile and CPU/compositor interface.

Owner stories:
- I35-S01: define the 720p display subsystem profile and CPU/compositor interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_soc_platform, platform


JsonValue = Any

FPGA_VIDEO_DISPLAY_STORY = "I35-S01"
FPGA_VIDEO_DISPLAY_DOC = Path("docs/implementation/fpga-video-display-profile.md")
FPGA_VIDEO_DISPLAY_TOOL = "python tools\\fpga_video_display.py --check"
FPGA_VIDEO_DISPLAY_PROFILE_NAME = "cpu_v01_fpga_720p_display_profile"
FPGA_VIDEO_MMIO_BASE = platform.DEVICE_BASE + 0x500
FPGA_VIDEO_MMIO_CELLS = 0x100
FPGA_VIDEO_IRQ_LINE = "video_vblank"
FPGA_VIDEO_IRQ_BIT = 4


@dataclass(frozen=True)
class VideoTiming:
    name: str
    active_width: int
    active_height: int
    h_front_porch: int
    h_sync: int
    h_back_porch: int
    v_front_porch: int
    v_sync: int
    v_back_porch: int
    pixel_clock_hz: int
    hsync_active_high: bool
    vsync_active_high: bool

    @property
    def h_total(self) -> int:
        return self.active_width + self.h_front_porch + self.h_sync + self.h_back_porch

    @property
    def v_total(self) -> int:
        return self.active_height + self.v_front_porch + self.v_sync + self.v_back_porch

    @property
    def pixels_per_frame(self) -> int:
        return self.h_total * self.v_total

    @property
    def frame_rate_millihz(self) -> int:
        return (self.pixel_clock_hz * 1000) // self.pixels_per_frame

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "active_width": self.active_width,
            "active_height": self.active_height,
            "h_front_porch": self.h_front_porch,
            "h_sync": self.h_sync,
            "h_back_porch": self.h_back_porch,
            "h_total": self.h_total,
            "v_front_porch": self.v_front_porch,
            "v_sync": self.v_sync,
            "v_back_porch": self.v_back_porch,
            "v_total": self.v_total,
            "pixel_clock_hz": self.pixel_clock_hz,
            "frame_rate_millihz": self.frame_rate_millihz,
            "hsync_active_high": self.hsync_active_high,
            "vsync_active_high": self.vsync_active_high,
        }


@dataclass(frozen=True)
class VideoRegister:
    name: str
    offset_cell: int
    width_bits: int
    access: str
    reset_value: int
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("register name must not be empty")
        if type(self.offset_cell) is not int or self.offset_cell < 0:
            raise ValueError("register offset_cell must be a nonnegative int")
        if type(self.width_bits) is not int or self.width_bits <= 0 or self.width_bits > 48:
            raise ValueError("register width_bits must be in 1..48")
        if self.access not in {"ro", "wo", "rw", "w1c"}:
            raise ValueError("register access must be ro, wo, rw, or w1c")
        if type(self.reset_value) is not int or self.reset_value < 0:
            raise ValueError("register reset_value must be a nonnegative int")
        if not self.purpose:
            raise ValueError("register purpose must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "offset_cell": self.offset_cell,
            "width_bits": self.width_bits,
            "access": self.access,
            "reset_value": self.reset_value,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class VideoMmioProfile:
    name: str
    base_cell: int
    size_cells: int
    owner_story: str
    interrupt_line: str
    interrupt_bit: int
    registers: tuple[VideoRegister, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("MMIO profile name must not be empty")
        if type(self.base_cell) is not int or self.base_cell < 0:
            raise ValueError("MMIO base_cell must be a nonnegative int")
        if type(self.size_cells) is not int or self.size_cells <= 0:
            raise ValueError("MMIO size_cells must be positive")
        if not self.owner_story:
            raise ValueError("MMIO owner_story must not be empty")
        if not self.interrupt_line:
            raise ValueError("MMIO interrupt_line must not be empty")
        if type(self.interrupt_bit) is not int or self.interrupt_bit < 0:
            raise ValueError("MMIO interrupt_bit must be a nonnegative int")
        object.__setattr__(self, "registers", tuple(self.registers))
        if not self.registers:
            raise ValueError("MMIO profile must expose registers")
        for register in self.registers:
            if not isinstance(register, VideoRegister):
                raise TypeError("registers must contain VideoRegister values")
            if register.offset_cell >= self.size_cells:
                raise ValueError(f"register {register.name} is outside video MMIO window")

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    def register_by_name(self, name: str) -> VideoRegister:
        normalized = name.upper()
        for register in self.registers:
            if register.name.upper() == normalized:
                return register
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "owner_story": self.owner_story,
            "interrupt_line": self.interrupt_line,
            "interrupt_bit": self.interrupt_bit,
            "registers": [register.as_dict() for register in self.registers],
        }


@dataclass(frozen=True)
class VideoReadMasterSignal:
    name: str
    direction: str
    width_bits: int
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("read-master signal name must not be empty")
        if self.direction not in {"display_to_memory", "memory_to_display"}:
            raise ValueError("read-master direction must name display_to_memory or memory_to_display")
        if type(self.width_bits) is not int or self.width_bits <= 0:
            raise ValueError("read-master width_bits must be positive")
        if not self.purpose:
            raise ValueError("read-master purpose must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "width_bits": self.width_bits,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class VideoDisplayProfile:
    name: str
    story: str
    board: str
    fpga_top_module: str
    timing: VideoTiming
    mmio: VideoMmioProfile
    cpu_control_interface: str
    framebuffer_read_master: str
    pixel_formats: tuple[str, ...]
    read_master_signals: tuple[VideoReadMasterSignal, ...]
    memory_ownership_rules: tuple[str, ...]
    prerequisite_tools: tuple[str, ...]
    handoff_stories: tuple[str, ...]
    excluded_interfaces: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "story": self.story,
            "board": self.board,
            "fpga_top_module": self.fpga_top_module,
            "timing": self.timing.as_dict(),
            "mmio": self.mmio.as_dict(),
            "cpu_control_interface": self.cpu_control_interface,
            "framebuffer_read_master": self.framebuffer_read_master,
            "pixel_formats": list(self.pixel_formats),
            "read_master_signals": [signal.as_dict() for signal in self.read_master_signals],
            "memory_ownership_rules": list(self.memory_ownership_rules),
            "prerequisite_tools": list(self.prerequisite_tools),
            "handoff_stories": list(self.handoff_stories),
            "excluded_interfaces": list(self.excluded_interfaces),
        }


def fpga_video_display_profile() -> VideoDisplayProfile:
    return VideoDisplayProfile(
        name=FPGA_VIDEO_DISPLAY_PROFILE_NAME,
        story=FPGA_VIDEO_DISPLAY_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        fpga_top_module=fpga_first_test.FPGA_TOP_MODULE,
        timing=_timing_720p60(),
        mmio=_video_mmio_profile(),
        cpu_control_interface="local_mmio_device_ordered_48bit_cells",
        framebuffer_read_master="display_payload_read_master_without_capability_tags",
        pixel_formats=("test_pattern", "rgb565", "xrgb8888"),
        read_master_signals=_read_master_signals(),
        memory_ownership_rules=(
            "CPU programs video registers through the existing data/MMIO decoder",
            "CPU or loader fills framebuffer payload memory through existing memory paths",
            "Display logic reads framebuffer payloads through a read-only scanout master",
            "Display logic never accepts, creates, or stores capability tags",
            "Descriptor and framebuffer update visibility is synchronized at vblank",
        ),
        prerequisite_tools=(
            "python tools\\fpga_soc_platform.py --check",
            "python tools\\fpga_soc_top_decoder.py --check",
            "python tools\\fpga_clock_profiles.py --check",
        ),
        handoff_stories=("I35-S02", "I35-S04", "I36-S01", "I36-S08"),
        excluded_interfaces=(
            "PCIe_like_fabric",
            "cache_coherent_gpu_interconnect",
            "shader_command_queue",
            "3d_acceleration",
            "display_master_tag_sidecar",
        ),
    )


def fpga_video_display_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_video_display_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_video_display_profile() -> str:
    profile = fpga_video_display_profile()
    timing = profile.timing
    mmio = profile.mmio
    lines = [
        "# FPGA Video Display Profile",
        "",
        f"Story: `{profile.story}`",
        f"Profile: `{profile.name}`",
        f"Board: `{profile.board}`",
        f"Top: `{profile.fpga_top_module}`",
        f"Mode: `{timing.name}` `{timing.active_width}x{timing.active_height}` "
        f"`{timing.pixel_clock_hz} Hz`",
        f"MMIO: `0x{mmio.base_cell:08X}`..`0x{mmio.end_cell:08X}`",
        f"IRQ: `{mmio.interrupt_line}` bit `{mmio.interrupt_bit}`",
        "",
        "## Registers",
        "",
        "| Register | Offset | Access | Width |",
        "| --- | ---: | --- | ---: |",
    ]
    for register in mmio.registers:
        lines.append(
            f"| `{register.name}` | `0x{register.offset_cell:02X}` | "
            f"`{register.access}` | {register.width_bits} |"
        )
    return "\n".join(lines)


def validate_fpga_video_display(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_display_profile()
    issues: list[str] = []

    if profile.story != FPGA_VIDEO_DISPLAY_STORY:
        issues.append(f"video display story must be {FPGA_VIDEO_DISPLAY_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("video display board must match I23-S01")
    if profile.fpga_top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("video display top module must match the FPGA wrapper")

    timing = profile.timing
    if (timing.active_width, timing.active_height) != (1280, 720):
        issues.append("video timing must target 1280x720 active pixels")
    if (timing.h_total, timing.v_total) != (1650, 750):
        issues.append("720p timing totals must be 1650x750")
    if timing.pixel_clock_hz != 74_250_000:
        issues.append("720p timing pixel clock must be 74.25 MHz")
    if timing.frame_rate_millihz != 60_000:
        issues.append("720p timing must derive exactly 60.000 Hz")

    soc_profile = fpga_soc_platform.fpga_soc_platform_profile()
    soc_issues = fpga_soc_platform.validate_fpga_soc_platform(root)
    issues.extend(f"I27-S01 prerequisite: {issue}" for issue in soc_issues)
    device = platform.TEST_PLATFORM_PROFILE.region_by_name("platform_devices")
    mmio = profile.mmio
    if mmio.base_cell != FPGA_VIDEO_MMIO_BASE or mmio.size_cells != FPGA_VIDEO_MMIO_CELLS:
        issues.append("video MMIO window must use the reserved I35-S01 range")
    if not device.contains(mmio.base_cell) or mmio.end_cell > device.end:
        issues.append("video MMIO window must fit inside platform_devices")
    for peripheral in soc_profile.peripherals:
        if mmio.base_cell < peripheral.end_cell and peripheral.base_cell < mmio.end_cell:
            issues.append(f"video MMIO overlaps existing SoC peripheral {peripheral.name}")
    if mmio.interrupt_line != FPGA_VIDEO_IRQ_LINE:
        issues.append("video interrupt line must be video_vblank")
    if mmio.interrupt_bit != FPGA_VIDEO_IRQ_BIT or mmio.interrupt_bit >= 16:
        issues.append("video interrupt bit must be bit 4 within the 16-bit interrupt controller")

    register_names = [register.name for register in mmio.registers]
    if len(register_names) != len(set(register_names)):
        issues.append("video register names are not unique")
    for register_name in (
        "VIDEO_CONTROL",
        "VIDEO_MODE",
        "VIDEO_STATUS",
        "VIDEO_IRQ_ENABLE",
        "VIDEO_IRQ_ACK",
        "VIDEO_FRAME_COUNT",
        "VIDEO_LINE_COUNT",
        "VIDEO_PIXEL_COUNT",
        "VIDEO_TEST_PATTERN",
        "VIDEO_BG_COLOR",
        "VIDEO_UNDERFLOW_COUNT",
        "VIDEO_FB_MASTER_STATUS",
    ):
        if register_name not in register_names:
            issues.append(f"video MMIO missing register {register_name}")

    if profile.cpu_control_interface != "local_mmio_device_ordered_48bit_cells":
        issues.append("video CPU interface must be local MMIO")
    if "PCIe_like_fabric" not in profile.excluded_interfaces:
        issues.append("video profile must explicitly exclude PCIe-like fabric")
    if "display_master_tag_sidecar" not in profile.excluded_interfaces:
        issues.append("video profile must explicitly exclude display tag sidecars")
    for pixel_format in ("test_pattern", "rgb565", "xrgb8888"):
        if pixel_format not in profile.pixel_formats:
            issues.append(f"video profile missing pixel format {pixel_format}")

    signal_names = [signal.name for signal in profile.read_master_signals]
    for signal_name in (
        "video_rd_req_valid",
        "video_rd_req_ready",
        "video_rd_req_addr",
        "video_rd_req_len_cells",
        "video_rd_rsp_valid",
        "video_rd_rsp_ready",
        "video_rd_rsp_data",
        "video_rd_rsp_error",
    ):
        if signal_name not in signal_names:
            issues.append(f"video read-master boundary missing {signal_name}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video display profile is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_VIDEO_DISPLAY_DOC)
    for token in (
        "Story: I35-S01",
        FPGA_VIDEO_DISPLAY_TOOL,
        "1280x720",
        "74.25 MHz",
        "0x00F00500",
        "VIDEO_CONTROL",
        "VIDEO_IRQ_ACK",
        "VIDEO_FB_MASTER_STATUS",
        "video_vblank",
        "local MMIO",
        "framebuffer read master",
        "PCIe-like",
        "I35-S04",
        "I36-S01",
        "I36-S08",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_DISPLAY_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _timing_720p60() -> VideoTiming:
    return VideoTiming(
        name="cea_720p60",
        active_width=1280,
        active_height=720,
        h_front_porch=110,
        h_sync=40,
        h_back_porch=220,
        v_front_porch=5,
        v_sync=5,
        v_back_porch=20,
        pixel_clock_hz=74_250_000,
        hsync_active_high=True,
        vsync_active_high=True,
    )


def _video_mmio_profile() -> VideoMmioProfile:
    return VideoMmioProfile(
        name="video_display",
        base_cell=FPGA_VIDEO_MMIO_BASE,
        size_cells=FPGA_VIDEO_MMIO_CELLS,
        owner_story=FPGA_VIDEO_DISPLAY_STORY,
        interrupt_line=FPGA_VIDEO_IRQ_LINE,
        interrupt_bit=FPGA_VIDEO_IRQ_BIT,
        registers=(
            VideoRegister("VIDEO_CONTROL", 0x00, 16, "rw", 0, "Enable scanout and select reset/test-pattern behavior."),
            VideoRegister("VIDEO_MODE", 0x01, 16, "rw", 0, "Selected timing mode; zero is cea_720p60."),
            VideoRegister("VIDEO_STATUS", 0x02, 16, "ro", 0, "Enabled, in-vblank, underflow, and mode-valid status bits."),
            VideoRegister("VIDEO_IRQ_ENABLE", 0x03, 16, "rw", 0, "Enable vblank and error interrupt sources."),
            VideoRegister("VIDEO_IRQ_ACK", 0x04, 16, "w1c", 0, "Acknowledge sticky vblank and error interrupt sources."),
            VideoRegister("VIDEO_FRAME_COUNT", 0x05, 48, "ro", 0, "Number of completed frames."),
            VideoRegister("VIDEO_LINE_COUNT", 0x06, 16, "ro", 0, "Current scanout line counter in the pixel domain snapshot."),
            VideoRegister("VIDEO_PIXEL_COUNT", 0x07, 16, "ro", 0, "Current scanout pixel counter in the pixel domain snapshot."),
            VideoRegister("VIDEO_TEST_PATTERN", 0x08, 16, "rw", 1, "Test-pattern selector used before framebuffer fetch is implemented."),
            VideoRegister("VIDEO_BG_COLOR", 0x09, 24, "rw", 0, "Background RGB color used by test pattern and later compositor clear."),
            VideoRegister("VIDEO_UNDERFLOW_COUNT", 0x0A, 48, "ro", 0, "Sticky count of scanout read or line-buffer underflows."),
            VideoRegister("VIDEO_FB_MASTER_STATUS", 0x0B, 16, "ro", 0, "Read-master idle, busy, blocked, and error status bits."),
        ),
    )


def _read_master_signals() -> tuple[VideoReadMasterSignal, ...]:
    return (
        VideoReadMasterSignal("video_rd_req_valid", "display_to_memory", 1, "Scanout read request is valid."),
        VideoReadMasterSignal("video_rd_req_ready", "memory_to_display", 1, "Memory arbiter can accept a scanout read request."),
        VideoReadMasterSignal("video_rd_req_addr", "display_to_memory", 48, "Cell address for the next scanout payload read."),
        VideoReadMasterSignal("video_rd_req_len_cells", "display_to_memory", 8, "Bounded burst length in cells."),
        VideoReadMasterSignal("video_rd_rsp_valid", "memory_to_display", 1, "Read response data is valid."),
        VideoReadMasterSignal("video_rd_rsp_ready", "display_to_memory", 1, "Scanout pipeline can accept read response data."),
        VideoReadMasterSignal("video_rd_rsp_data", "memory_to_display", 48, "Payload data returned from BRAM or external memory."),
        VideoReadMasterSignal("video_rd_rsp_error", "memory_to_display", 1, "Memory boundary reported an error for the scanout read."),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

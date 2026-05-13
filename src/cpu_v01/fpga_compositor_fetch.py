"""FPGA compositor single-plane fetch and line-buffer profile.

Owner stories:
- I36-S02: implement single-plane framebuffer fetch and line buffering.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import fpga_compositor_framebuffer, fpga_ddr_wrapper, fpga_video_timing


JsonValue = Any

FPGA_COMPOSITOR_FETCH_STORY = "I36-S02"
FPGA_COMPOSITOR_FETCH_DOC = Path("docs/implementation/fpga-compositor-fetch.md")
FPGA_COMPOSITOR_FETCH_TOOL = "python tools\\fpga_compositor_fetch.py --check"
FPGA_COMPOSITOR_FETCH_RTL = Path("rtl/cpu_v01_fpga_single_plane_fetch.sv")
FPGA_COMPOSITOR_FETCH_TB = Path("rtl/cpu_v01_fpga_single_plane_fetch_tb.sv")
PIXEL_FORMAT_RGB565 = "rgb565"
PIXEL_FORMAT_XRGB8888 = "xrgb8888"
FORMAT_SELECT_RGB565 = 0
FORMAT_SELECT_XRGB8888 = 1
BG_COLOR = 0x000000


@dataclass(frozen=True)
class FetchReadRequest:
    addr_cell: int
    len_cells: int
    x: int
    y: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "addr_cell": self.addr_cell,
            "len_cells": self.len_cells,
            "x": self.x,
            "y": self.y,
        }


@dataclass(frozen=True)
class PlaneDescriptor:
    enabled: bool
    base_cell: int
    stride_cells: int
    width: int
    height: int
    pixel_format: str
    background_rgb: int = BG_COLOR

    def __post_init__(self) -> None:
        if self.base_cell < 0:
            raise ValueError("plane base_cell must be nonnegative")
        if self.stride_cells <= 0:
            raise ValueError("plane stride_cells must be positive")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("plane width and height must be positive")
        if self.pixel_format not in {PIXEL_FORMAT_RGB565, PIXEL_FORMAT_XRGB8888}:
            raise ValueError(f"unsupported I36-S02 pixel format {self.pixel_format}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "base_cell": self.base_cell,
            "stride_cells": self.stride_cells,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "background_rgb": self.background_rgb,
        }


@dataclass(frozen=True)
class LineFetchResult:
    descriptor: PlaneDescriptor
    y: int
    requests: tuple[FetchReadRequest, ...]
    rgb_pixels: tuple[int, ...]
    underflow: bool
    error_cells: tuple[int, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "descriptor": self.descriptor.as_dict(),
            "y": self.y,
            "requests": [request.as_dict() for request in self.requests],
            "rgb_pixels": list(self.rgb_pixels),
            "underflow": self.underflow,
            "error_cells": list(self.error_cells),
        }


@dataclass(frozen=True)
class CompositorFetchProfile:
    story: str
    framebuffer_gate: str
    timing_gate: str
    ddr_wrapper_gate: str
    validator: str
    fetch_module: str
    testbench_module: str
    supported_formats: tuple[str, ...]
    format_selects: dict[str, int]
    line_buffer_pixels: int
    line_buffered_lines: int
    request_policy: str
    read_master_signals: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "framebuffer_gate": self.framebuffer_gate,
            "timing_gate": self.timing_gate,
            "ddr_wrapper_gate": self.ddr_wrapper_gate,
            "validator": self.validator,
            "fetch_module": self.fetch_module,
            "testbench_module": self.testbench_module,
            "supported_formats": list(self.supported_formats),
            "format_selects": dict(self.format_selects),
            "line_buffer_pixels": self.line_buffer_pixels,
            "line_buffered_lines": self.line_buffered_lines,
            "request_policy": self.request_policy,
            "read_master_signals": list(self.read_master_signals),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "handoffs": list(self.handoffs),
            "non_goals": list(self.non_goals),
        }


def fpga_compositor_fetch_profile() -> CompositorFetchProfile:
    framebuffer = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()
    return CompositorFetchProfile(
        story=FPGA_COMPOSITOR_FETCH_STORY,
        framebuffer_gate=fpga_compositor_framebuffer.FPGA_COMPOSITOR_FRAMEBUFFER_TOOL,
        timing_gate=fpga_video_timing.FPGA_VIDEO_TIMING_TOOL,
        ddr_wrapper_gate=fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        validator=FPGA_COMPOSITOR_FETCH_TOOL,
        fetch_module="cpu_v01_fpga_single_plane_fetch",
        testbench_module="cpu_v01_fpga_single_plane_fetch_tb",
        supported_formats=(PIXEL_FORMAT_RGB565, PIXEL_FORMAT_XRGB8888),
        format_selects={
            PIXEL_FORMAT_RGB565: FORMAT_SELECT_RGB565,
            PIXEL_FORMAT_XRGB8888: FORMAT_SELECT_XRGB8888,
        },
        line_buffer_pixels=framebuffer.line_buffer.active_width,
        line_buffered_lines=framebuffer.line_buffer.buffered_lines,
        request_policy=(
            "one payload cell per visible fixture pixel in the first BRAM/adapter fixture; "
            "stride_cells selects each source line and I36-S08 owns shared CPU/compositor arbitration"
        ),
        read_master_signals=(
            "video_rd_req_valid_o",
            "video_rd_req_ready_i",
            "video_rd_req_addr_o",
            "video_rd_req_len_cells_o",
            "video_rd_rsp_valid_i",
            "video_rd_rsp_ready_o",
            "video_rd_rsp_data_i",
            "video_rd_rsp_error_i",
        ),
        rtl_sources=(FPGA_COMPOSITOR_FETCH_RTL.as_posix(), FPGA_COMPOSITOR_FETCH_TB.as_posix()),
        verilator_commands=fpga_compositor_fetch_verilator_commands(),
        handoffs=(
            "I36-S03 layers multi-plane composition on top of the single-plane RGB output",
            "I36-S06 archives timing, bandwidth, resource, and underflow evidence",
            "I36-S08 arbitrates CPU data/MMIO traffic against compositor scanout reads",
        ),
        non_goals=(
            "multi_plane_z_order",
            "vblank_atomic_descriptor_latch",
            "shared_cpu_compositor_memory_arbiter",
            "capability_tag_scanout_payloads",
        ),
    )


def fpga_compositor_fetch_verilator_commands() -> tuple[str, ...]:
    return (
        "verilator --lint-only --timing --top-module cpu_v01_fpga_single_plane_fetch_tb "
        "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_single_plane_fetch.sv "
        "rtl/cpu_v01_fpga_single_plane_fetch_tb.sv",
    )


def default_plane_descriptor(pixel_format: str = PIXEL_FORMAT_RGB565) -> PlaneDescriptor:
    framebuffer = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()
    fmt = framebuffer.format_by_name(pixel_format)
    return PlaneDescriptor(
        enabled=True,
        base_cell=framebuffer.framebuffer_window.base_cell,
        stride_cells=fmt.stride_cells(8),
        width=8,
        height=4,
        pixel_format=pixel_format,
        background_rgb=0x102030,
    )


def fetch_line(
    descriptor: PlaneDescriptor,
    y: int,
    memory: Mapping[int, int],
) -> LineFetchResult:
    requests: list[FetchReadRequest] = []
    pixels: list[int] = []
    error_cells: list[int] = []

    if not descriptor.enabled or y < 0 or y >= descriptor.height:
        return LineFetchResult(
            descriptor=descriptor,
            y=y,
            requests=(),
            rgb_pixels=tuple(descriptor.background_rgb for _ in range(descriptor.width)),
            underflow=False,
            error_cells=(),
        )

    for x in range(descriptor.width):
        addr = descriptor.base_cell + y * descriptor.stride_cells + x
        requests.append(FetchReadRequest(addr_cell=addr, len_cells=1, x=x, y=y))
        if addr not in memory:
            pixels.append(descriptor.background_rgb)
            error_cells.append(addr)
            continue
        cell = memory[addr] & ((1 << 48) - 1)
        if descriptor.pixel_format == PIXEL_FORMAT_RGB565:
            pixels.append(rgb565_to_rgb888(cell & 0xFFFF))
        elif descriptor.pixel_format == PIXEL_FORMAT_XRGB8888:
            pixels.append(xrgb8888_to_rgb888(cell & 0xFFFFFFFF))
        else:
            pixels.append(descriptor.background_rgb)
            error_cells.append(addr)

    return LineFetchResult(
        descriptor=descriptor,
        y=y,
        requests=tuple(requests),
        rgb_pixels=tuple(pixels),
        underflow=bool(error_cells),
        error_cells=tuple(error_cells),
    )


def rgb565_to_rgb888(value: int) -> int:
    red = (value >> 11) & 0x1F
    green = (value >> 5) & 0x3F
    blue = value & 0x1F
    red8 = (red << 3) | (red >> 2)
    green8 = (green << 2) | (green >> 4)
    blue8 = (blue << 3) | (blue >> 2)
    return (red8 << 16) | (green8 << 8) | blue8


def xrgb8888_to_rgb888(value: int) -> int:
    return value & 0x00FF_FFFF


def demo_fetch_line() -> LineFetchResult:
    descriptor = default_plane_descriptor(PIXEL_FORMAT_RGB565)
    base = descriptor.base_cell
    memory = {
        base + 0: 0xF800,
        base + 1: 0x07E0,
        base + 2: 0x001F,
        base + 3: 0xFFFF,
        base + 4: 0x0000,
        base + 5: 0xFFE0,
        base + 6: 0x07FF,
        base + 7: 0xF81F,
    }
    return fetch_line(descriptor, 0, memory)


def demo_underflow_line() -> LineFetchResult:
    descriptor = default_plane_descriptor(PIXEL_FORMAT_XRGB8888)
    base = descriptor.base_cell
    memory = {base + 0: 0x00123456, base + 2: 0x00ABCDEF}
    return fetch_line(descriptor, 0, memory)


def fpga_compositor_fetch_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_compositor_fetch_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_compositor_fetch() -> str:
    profile = fpga_compositor_fetch_profile()
    lines = [
        "# FPGA Compositor Fetch",
        "",
        f"Story: `{profile.story}`",
        f"Module: `{profile.fetch_module}`",
        f"Line buffer pixels: `{profile.line_buffer_pixels}`",
        "",
        "## Read Master Signals",
        "",
    ]
    lines.extend(f"- `{signal}`" for signal in profile.read_master_signals)
    return "\n".join(lines)


def validate_fpga_compositor_fetch(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_fetch_profile()
    issues: list[str] = []

    issues.extend(
        f"I36-S01 prerequisite: {issue}"
        for issue in fpga_compositor_framebuffer.validate_fpga_compositor_framebuffer(root)
    )
    issues.extend(
        f"I35-S02 prerequisite: {issue}"
        for issue in fpga_video_timing.validate_fpga_video_timing(root)
    )
    issues.extend(
        f"I29-S02 prerequisite: {issue}"
        for issue in fpga_ddr_wrapper.validate_fpga_ddr_wrapper(root)
    )

    if profile.story != FPGA_COMPOSITOR_FETCH_STORY:
        issues.append(f"compositor fetch story must be {FPGA_COMPOSITOR_FETCH_STORY}")
    if profile.framebuffer_gate != fpga_compositor_framebuffer.FPGA_COMPOSITOR_FRAMEBUFFER_TOOL:
        issues.append("compositor fetch must depend on I36-S01")
    if profile.timing_gate != fpga_video_timing.FPGA_VIDEO_TIMING_TOOL:
        issues.append("compositor fetch must depend on I35-S02")
    if profile.ddr_wrapper_gate != fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL:
        issues.append("compositor fetch must depend on I29-S02")
    for fmt in (PIXEL_FORMAT_RGB565, PIXEL_FORMAT_XRGB8888):
        if fmt not in profile.supported_formats:
            issues.append(f"compositor fetch missing format {fmt}")
    if profile.line_buffer_pixels != 1280 or profile.line_buffered_lines != 2:
        issues.append("compositor fetch must retain 1280-pixel, two-line buffer policy")
    for signal in (
        "video_rd_req_valid_o",
        "video_rd_req_ready_i",
        "video_rd_req_addr_o",
        "video_rd_req_len_cells_o",
        "video_rd_rsp_valid_i",
        "video_rd_rsp_ready_o",
        "video_rd_rsp_data_i",
        "video_rd_rsp_error_i",
    ):
        if signal not in profile.read_master_signals:
            issues.append(f"missing read-master signal {signal}")

    demo = demo_fetch_line()
    if demo.underflow:
        issues.append("complete RGB565 demo line must not underflow")
    if demo.rgb_pixels[:4] != (0xFF0000, 0x00FF00, 0x0000FF, 0xFFFFFF):
        issues.append("RGB565 demo conversion mismatch")
    if demo.requests[3].addr_cell != demo.descriptor.base_cell + 3:
        issues.append("fetch demo request addresses must be stride-relative")
    underflow = demo_underflow_line()
    if not underflow.underflow:
        issues.append("incomplete XRGB8888 demo line must report underflow")
    if underflow.rgb_pixels[0] != 0x123456 or underflow.rgb_pixels[2] != 0xABCDEF:
        issues.append("XRGB8888 demo conversion mismatch")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / FPGA_COMPOSITOR_FETCH_RTL)
    tb = _read_if_exists(root / FPGA_COMPOSITOR_FETCH_TB)
    for token in (
        "module cpu_v01_fpga_single_plane_fetch",
        "FORMAT_RGB565 = 2'd0",
        "FORMAT_XRGB8888 = 2'd1",
        "line_rgb_q",
        "line_valid_q",
        "assign video_rd_req_valid_o = fetch_active_q",
        "assign video_rd_req_len_cells_o = 8'd1",
        "rgb565_to_rgb888",
        "xrgb8888_to_rgb888",
        "underflow_pulse_o",
        "video_rd_req_addr_o",
        "plane_stride_cells_i",
    ):
        if token not in rtl:
            issues.append(f"{FPGA_COMPOSITOR_FETCH_RTL.as_posix()} missing {token}")
    for token in (
        "module cpu_v01_fpga_single_plane_fetch_tb",
        "cpu_v01_fpga_single_plane_fetch dut",
        "single-plane fetch RGB565 red mismatch",
        "single-plane fetch XRGB8888 conversion mismatch",
        "single-plane fetch did not report deterministic underflow",
        "single-plane fetch request address mismatch",
    ):
        if token not in tb:
            issues.append(f"{FPGA_COMPOSITOR_FETCH_TB.as_posix()} missing {token}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_FETCH_DOC)
    for token in (
        "Story: I36-S02",
        FPGA_COMPOSITOR_FETCH_TOOL,
        "python tools\\fpga_compositor_framebuffer.py --check",
        "python tools\\fpga_video_timing.py --check",
        "python tools\\fpga_ddr_wrapper.py --check",
        "cpu_v01_fpga_single_plane_fetch",
        "video_rd_req_valid_o",
        "video_rd_rsp_valid_i",
        "rgb565",
        "xrgb8888",
        "line_rgb_q",
        "VIDEO_UNDERFLOW_COUNT",
        "I36-S03",
        "I36-S08",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_FETCH_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(demo.as_dict(), sort_keys=True)
        json.dumps(underflow.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor fetch objects are not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

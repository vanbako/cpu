"""FPGA compositor framebuffer memory and pixel-format policy.

Owner stories:
- I36-S01: define framebuffer memory, bandwidth, and pixel-format policy for planes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_external_memory, fpga_video_display


JsonValue = Any

FPGA_COMPOSITOR_FRAMEBUFFER_STORY = "I36-S01"
FPGA_COMPOSITOR_FRAMEBUFFER_DOC = Path("docs/implementation/fpga-compositor-framebuffer-policy.md")
FPGA_COMPOSITOR_FRAMEBUFFER_TOOL = "python tools\\fpga_compositor_framebuffer.py --check"
FPGA_COMPOSITOR_FRAMEBUFFER_PROFILE_NAME = "cpu_v01_fpga_compositor_framebuffer_policy"
FRAMEBUFFER_HEAP_BASE = fpga_external_memory.FPGA_EXTERNAL_MEMORY_BASE + 0x0010_0000
FRAMEBUFFER_HEAP_CELLS = 0x0040_0000
FRAMEBUFFER_HEAP_END = FRAMEBUFFER_HEAP_BASE + FRAMEBUFFER_HEAP_CELLS
FRAMEBUFFER_ALIGN_CELLS = 16
STRIDE_ALIGN_CELLS = 16
PAYLOAD_BYTES_PER_CELL = 6
LINE_BUFFER_CELLS = 2048


@dataclass(frozen=True)
class PixelFormat:
    name: str
    bytes_per_pixel: int
    alpha_policy: str
    endian: str
    first_story: str
    notes: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("pixel format name must not be empty")
        if type(self.bytes_per_pixel) is not int or self.bytes_per_pixel <= 0:
            raise ValueError("pixel format bytes_per_pixel must be positive")
        if not self.alpha_policy:
            raise ValueError("pixel format alpha_policy must not be empty")
        if self.endian not in {"little_byte_order_within_payload_cells"}:
            raise ValueError("pixel format endian policy is not supported")
        if not self.first_story:
            raise ValueError("pixel format first_story must not be empty")
        if not self.notes:
            raise ValueError("pixel format notes must not be empty")

    def frame_bytes(self, width: int, height: int) -> int:
        return width * height * self.bytes_per_pixel

    def frame_cells(self, width: int, height: int) -> int:
        return _ceil_div(self.frame_bytes(width, height), PAYLOAD_BYTES_PER_CELL)

    def stride_cells(self, width: int) -> int:
        return _align_up(_ceil_div(width * self.bytes_per_pixel, PAYLOAD_BYTES_PER_CELL), STRIDE_ALIGN_CELLS)

    def as_dict(self) -> dict[str, JsonValue]:
        timing = fpga_video_display.fpga_video_display_profile().timing
        return {
            "name": self.name,
            "bytes_per_pixel": self.bytes_per_pixel,
            "alpha_policy": self.alpha_policy,
            "endian": self.endian,
            "first_story": self.first_story,
            "notes": self.notes,
            "frame_bytes_720p": self.frame_bytes(timing.active_width, timing.active_height),
            "frame_cells_720p": self.frame_cells(timing.active_width, timing.active_height),
            "stride_cells_720p": self.stride_cells(timing.active_width),
        }


@dataclass(frozen=True)
class FramebufferWindow:
    name: str
    base_cell: int
    size_cells: int
    memory_type: str
    cacheability: str
    tag_policy: str
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("framebuffer window name must not be empty")
        if type(self.base_cell) is not int or self.base_cell < 0:
            raise ValueError("framebuffer base_cell must be a nonnegative int")
        if type(self.size_cells) is not int or self.size_cells <= 0:
            raise ValueError("framebuffer size_cells must be positive")
        if not self.memory_type:
            raise ValueError("framebuffer memory_type must not be empty")
        if not self.cacheability:
            raise ValueError("framebuffer cacheability must not be empty")
        if not self.tag_policy:
            raise ValueError("framebuffer tag_policy must not be empty")
        if not self.purpose:
            raise ValueError("framebuffer purpose must not be empty")

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "memory_type": self.memory_type,
            "cacheability": self.cacheability,
            "tag_policy": self.tag_policy,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class LineBufferPolicy:
    active_width: int
    max_bytes_per_pixel: int
    buffered_lines: int
    allocated_cells: int
    underflow_counter: str

    @property
    def required_cells(self) -> int:
        return _ceil_div(
            self.active_width * self.max_bytes_per_pixel * self.buffered_lines,
            PAYLOAD_BYTES_PER_CELL,
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "active_width": self.active_width,
            "max_bytes_per_pixel": self.max_bytes_per_pixel,
            "buffered_lines": self.buffered_lines,
            "required_cells": self.required_cells,
            "allocated_cells": self.allocated_cells,
            "underflow_counter": self.underflow_counter,
        }


@dataclass(frozen=True)
class FramebufferPolicyProfile:
    name: str
    story: str
    display_profile: str
    framebuffer_window: FramebufferWindow
    pixel_formats: tuple[PixelFormat, ...]
    payload_bytes_per_cell: int
    framebuffer_align_cells: int
    stride_align_cells: int
    line_buffer: LineBufferPolicy
    bram_fixture_policy: str
    memory_ownership_rules: tuple[str, ...]
    handoff_stories: tuple[str, ...]
    non_goals: tuple[str, ...]

    def format_by_name(self, name: str) -> PixelFormat:
        normalized = name.lower()
        for pixel_format in self.pixel_formats:
            if pixel_format.name.lower() == normalized:
                return pixel_format
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "story": self.story,
            "display_profile": self.display_profile,
            "framebuffer_window": self.framebuffer_window.as_dict(),
            "pixel_formats": [pixel_format.as_dict() for pixel_format in self.pixel_formats],
            "payload_bytes_per_cell": self.payload_bytes_per_cell,
            "framebuffer_align_cells": self.framebuffer_align_cells,
            "stride_align_cells": self.stride_align_cells,
            "line_buffer": self.line_buffer.as_dict(),
            "bram_fixture_policy": self.bram_fixture_policy,
            "memory_ownership_rules": list(self.memory_ownership_rules),
            "handoff_stories": list(self.handoff_stories),
            "non_goals": list(self.non_goals),
        }


def fpga_compositor_framebuffer_profile() -> FramebufferPolicyProfile:
    timing = fpga_video_display.fpga_video_display_profile().timing
    return FramebufferPolicyProfile(
        name=FPGA_COMPOSITOR_FRAMEBUFFER_PROFILE_NAME,
        story=FPGA_COMPOSITOR_FRAMEBUFFER_STORY,
        display_profile=fpga_video_display.FPGA_VIDEO_DISPLAY_PROFILE_NAME,
        framebuffer_window=FramebufferWindow(
            name="external_ddr_framebuffer_heap",
            base_cell=FRAMEBUFFER_HEAP_BASE,
            size_cells=FRAMEBUFFER_HEAP_CELLS,
            memory_type="normal_uncacheable",
            cacheability="uncacheable_until_future_coherent_graphics_policy",
            tag_policy="payload_only_no_capability_tags",
            purpose="720p framebuffer payloads and plane surfaces for the compositor.",
        ),
        pixel_formats=(
            PixelFormat(
                "rgb565",
                2,
                "opaque",
                "little_byte_order_within_payload_cells",
                "I36-S02",
                "Compact first framebuffer format for bandwidth-constrained board demos.",
            ),
            PixelFormat(
                "xrgb8888",
                4,
                "x_byte_ignored_opaque",
                "little_byte_order_within_payload_cells",
                "I36-S02",
                "Debug-friendly 32-bit format for single-plane and overlay demos.",
            ),
            PixelFormat(
                "indexed8",
                1,
                "palette_entry_policy_deferred",
                "little_byte_order_within_payload_cells",
                "I36-S03",
                "Optional indexed plane format; palette registers are deferred to composition.",
            ),
        ),
        payload_bytes_per_cell=PAYLOAD_BYTES_PER_CELL,
        framebuffer_align_cells=FRAMEBUFFER_ALIGN_CELLS,
        stride_align_cells=STRIDE_ALIGN_CELLS,
        line_buffer=LineBufferPolicy(
            active_width=timing.active_width,
            max_bytes_per_pixel=4,
            buffered_lines=2,
            allocated_cells=LINE_BUFFER_CELLS,
            underflow_counter="VIDEO_UNDERFLOW_COUNT",
        ),
        bram_fixture_policy=(
            "BRAM fixtures may cover reduced-size planes and line-buffer tests; "
            "full 1280x720 framebuffers require the external-memory window."
        ),
        memory_ownership_rules=(
            "CPU and loader writes populate framebuffer payloads through existing memory paths",
            "Compositor reads framebuffer payloads through the I35-S01 read-only scanout master",
            "Framebuffer payload memory is not capability-tag-bearing storage",
            "CLC and CSC targeting framebuffer surfaces are rejected by the existing external-memory tag policy",
            "CPU/compositor arbitration is closed by I36-S08 before shared-memory board demos are claimed",
        ),
        handoff_stories=("I36-S02", "I36-S03", "I36-S04", "I36-S08"),
        non_goals=(
            "cache_coherent_graphics",
            "capability_tag_sidecar_for_framebuffers",
            "shader_or_command_processor",
            "PCIe_like_graphics_endpoint",
        ),
    )


def fpga_compositor_framebuffer_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_compositor_framebuffer_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_compositor_framebuffer_profile() -> str:
    profile = fpga_compositor_framebuffer_profile()
    window = profile.framebuffer_window
    lines = [
        "# FPGA Compositor Framebuffer Policy",
        "",
        f"Story: `{profile.story}`",
        f"Profile: `{profile.name}`",
        f"Display profile: `{profile.display_profile}`",
        f"Framebuffer heap: `0x{window.base_cell:08X}`..`0x{window.end_cell:08X}`",
        "",
        "## Pixel Formats",
        "",
        "| Format | Bytes/px | 720p cells | Stride cells |",
        "| --- | ---: | ---: | ---: |",
    ]
    timing = fpga_video_display.fpga_video_display_profile().timing
    for pixel_format in profile.pixel_formats:
        lines.append(
            f"| `{pixel_format.name}` | {pixel_format.bytes_per_pixel} | "
            f"{pixel_format.frame_cells(timing.active_width, timing.active_height)} | "
            f"{pixel_format.stride_cells(timing.active_width)} |"
        )
    return "\n".join(lines)


def validate_fpga_compositor_framebuffer(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_framebuffer_profile()
    issues: list[str] = []

    if profile.story != FPGA_COMPOSITOR_FRAMEBUFFER_STORY:
        issues.append(f"compositor framebuffer story must be {FPGA_COMPOSITOR_FRAMEBUFFER_STORY}")
    display_issues = fpga_video_display.validate_fpga_video_display(root)
    issues.extend(f"I35-S01 prerequisite: {issue}" for issue in display_issues)
    external_issues = fpga_external_memory.validate_fpga_external_memory(root)
    issues.extend(f"I29-S01 prerequisite: {issue}" for issue in external_issues)

    window = profile.framebuffer_window
    external = fpga_external_memory.fpga_external_memory_profile().window_by_name("external_ddr_payload")
    if window.base_cell < external.base_cell or window.end_cell > external.end_cell:
        issues.append("framebuffer heap must fit inside external_ddr_payload")
    if window.base_cell % profile.framebuffer_align_cells != 0:
        issues.append("framebuffer heap base must satisfy framebuffer alignment")
    if window.memory_type != "normal_uncacheable":
        issues.append("framebuffer heap must remain normal uncacheable for first policy")
    if window.tag_policy != "payload_only_no_capability_tags":
        issues.append("framebuffer heap must reject capability-tag storage")

    timing = fpga_video_display.fpga_video_display_profile().timing
    for required in ("rgb565", "xrgb8888", "indexed8"):
        try:
            profile.format_by_name(required)
        except KeyError:
            issues.append(f"missing pixel format {required}")
    xrgb = profile.format_by_name("xrgb8888")
    rgb565 = profile.format_by_name("rgb565")
    if xrgb.frame_bytes(timing.active_width, timing.active_height) != 3_686_400:
        issues.append("xrgb8888 720p frame must be 3,686,400 bytes")
    if rgb565.frame_bytes(timing.active_width, timing.active_height) != 1_843_200:
        issues.append("rgb565 720p frame must be 1,843,200 bytes")
    if xrgb.stride_cells(timing.active_width) % profile.stride_align_cells != 0:
        issues.append("xrgb8888 stride must satisfy stride alignment")
    if window.size_cells < xrgb.frame_cells(timing.active_width, timing.active_height) * 2:
        issues.append("framebuffer heap must fit at least two xrgb8888 720p frames")

    if profile.line_buffer.allocated_cells < profile.line_buffer.required_cells:
        issues.append("line buffer allocation must cover two xrgb8888 lines")
    if profile.line_buffer.underflow_counter != "VIDEO_UNDERFLOW_COUNT":
        issues.append("line buffer must report underflow through VIDEO_UNDERFLOW_COUNT")
    if "I36-S08" not in profile.handoff_stories:
        issues.append("framebuffer policy must hand memory arbitration to I36-S08")
    for non_goal in (
        "cache_coherent_graphics",
        "capability_tag_sidecar_for_framebuffers",
        "PCIe_like_graphics_endpoint",
    ):
        if non_goal not in profile.non_goals:
            issues.append(f"framebuffer policy missing non-goal {non_goal}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"framebuffer profile is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_FRAMEBUFFER_DOC)
    for token in (
        "Story: I36-S01",
        FPGA_COMPOSITOR_FRAMEBUFFER_TOOL,
        "0x01100000",
        "external_ddr_framebuffer_heap",
        "rgb565",
        "xrgb8888",
        "indexed8",
        "VIDEO_UNDERFLOW_COUNT",
        "normal uncacheable",
        "payload-only",
        "capability tags",
        "I36-S02",
        "I36-S08",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_FRAMEBUFFER_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _align_up(value: int, alignment: int) -> int:
    return _ceil_div(value, alignment) * alignment


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

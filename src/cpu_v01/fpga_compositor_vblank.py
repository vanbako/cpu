"""FPGA compositor vblank-atomic descriptor update profile.

Owner stories:
- I36-S04: add atomic plane descriptor updates at vblank.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import fpga_compositor_pipeline, fpga_video_mmio


JsonValue = Any

FPGA_COMPOSITOR_VBLANK_STORY = "I36-S04"
FPGA_COMPOSITOR_VBLANK_DOC = Path("docs/implementation/fpga-compositor-vblank-descriptors.md")
FPGA_COMPOSITOR_VBLANK_TOOL = "python tools\\fpga_compositor_vblank.py --check"
FPGA_COMPOSITOR_VBLANK_RTL = Path("rtl/cpu_v01_fpga_compositor_descriptor_latch.sv")
FPGA_COMPOSITOR_VBLANK_TB = Path("rtl/cpu_v01_fpga_compositor_descriptor_latch_tb.sv")

FIELD_CONTROL = 0
FIELD_BASE = 1
FIELD_STRIDE = 2
FIELD_POSITION = 3
FIELD_SIZE = 4
FIELD_FORMAT_Z_ALPHA = 5
FIELD_COLOR_KEY = 6


@dataclass(frozen=True)
class PlaneDescriptor:
    enable: bool
    base_cell: int
    stride_cells: int
    x: int
    y: int
    width: int
    height: int
    pixel_format: int
    z: int
    alpha: int
    color_key_enable: bool
    color_key_rgb: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "enable": self.enable,
            "base_cell": self.base_cell,
            "stride_cells": self.stride_cells,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "z": self.z,
            "alpha": self.alpha,
            "color_key_enable": self.color_key_enable,
            "color_key_rgb": self.color_key_rgb,
        }


@dataclass(frozen=True)
class DescriptorLatchState:
    shadow: tuple[PlaneDescriptor, PlaneDescriptor]
    active: tuple[PlaneDescriptor, PlaneDescriptor]
    pending: bool = False
    applied_count: int = 0
    vblank: bool = False

    def write_field(self, plane: int, field: int, value: int) -> "DescriptorLatchState":
        if plane not in (0, 1):
            raise ValueError("plane must be 0 or 1")
        current = self.shadow[plane]
        updated = _write_descriptor_field(current, field, value)
        shadow = list(self.shadow)
        shadow[plane] = updated
        return replace(self, shadow=(shadow[0], shadow[1]), pending=True)

    def tick(self, *, vblank: bool) -> "DescriptorLatchState":
        rising = vblank and not self.vblank
        if rising and self.pending:
            return replace(
                self,
                active=self.shadow,
                pending=False,
                applied_count=(self.applied_count + 1) & 0xFFFF,
                vblank=vblank,
            )
        return replace(self, vblank=vblank)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "shadow": [descriptor.as_dict() for descriptor in self.shadow],
            "active": [descriptor.as_dict() for descriptor in self.active],
            "pending": self.pending,
            "applied_count": self.applied_count,
            "vblank": self.vblank,
        }


@dataclass(frozen=True)
class CompositorVblankProfile:
    story: str
    pipeline_gate: str
    video_mmio_gate: str
    validator: str
    latch_module: str
    testbench_module: str
    plane_count: int
    descriptor_fields: tuple[str, ...]
    status_bits: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "pipeline_gate": self.pipeline_gate,
            "video_mmio_gate": self.video_mmio_gate,
            "validator": self.validator,
            "latch_module": self.latch_module,
            "testbench_module": self.testbench_module,
            "plane_count": self.plane_count,
            "descriptor_fields": list(self.descriptor_fields),
            "status_bits": list(self.status_bits),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "handoffs": list(self.handoffs),
            "non_goals": list(self.non_goals),
        }


def fpga_compositor_vblank_profile() -> CompositorVblankProfile:
    return CompositorVblankProfile(
        story=FPGA_COMPOSITOR_VBLANK_STORY,
        pipeline_gate=fpga_compositor_pipeline.FPGA_COMPOSITOR_PIPELINE_TOOL,
        video_mmio_gate=fpga_video_mmio.FPGA_VIDEO_MMIO_TOOL,
        validator=FPGA_COMPOSITOR_VBLANK_TOOL,
        latch_module="cpu_v01_fpga_compositor_descriptor_latch",
        testbench_module="cpu_v01_fpga_compositor_descriptor_latch_tb",
        plane_count=2,
        descriptor_fields=(
            "control",
            "base_cell",
            "stride_cells",
            "position_xy",
            "size_wh",
            "format_z_alpha",
            "color_key_rgb",
        ),
        status_bits=("descriptor_pending", "descriptor_applied_pulse", "applied_count"),
        rtl_sources=(FPGA_COMPOSITOR_VBLANK_RTL.as_posix(), FPGA_COMPOSITOR_VBLANK_TB.as_posix()),
        verilator_commands=fpga_compositor_vblank_verilator_commands(),
        handoffs=(
            "I36-S05 firmware and monitor demos program the shadow descriptor fields",
            "I36-S06 archives descriptor pending/applied and underflow evidence",
            "I36-S08 arbitrates memory once CPU writes and scanout reads overlap",
        ),
        non_goals=(
            "full_video_mmio_register_map_for_planes",
            "firmware_demo",
            "memory_arbitration",
            "more_than_two_planes",
        ),
    )


def fpga_compositor_vblank_verilator_commands() -> tuple[str, ...]:
    return (
        "verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_descriptor_latch_tb "
        "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_descriptor_latch.sv "
        "rtl/cpu_v01_fpga_compositor_descriptor_latch_tb.sv",
    )


def initial_descriptor() -> PlaneDescriptor:
    return PlaneDescriptor(
        enable=False,
        base_cell=0,
        stride_cells=0,
        x=0,
        y=0,
        width=0,
        height=0,
        pixel_format=0,
        z=0,
        alpha=255,
        color_key_enable=False,
        color_key_rgb=0,
    )


def initial_latch_state() -> DescriptorLatchState:
    desc = initial_descriptor()
    return DescriptorLatchState(shadow=(desc, desc), active=(desc, desc))


def demo_vblank_update() -> tuple[DescriptorLatchState, DescriptorLatchState, DescriptorLatchState]:
    state = initial_latch_state()
    state = state.write_field(0, FIELD_BASE, 0x0110_0000)
    state = state.write_field(0, FIELD_STRIDE, 16)
    state = state.write_field(0, FIELD_POSITION, 0x000A_0014)
    state = state.write_field(0, FIELD_SIZE, 0x0080_0040)
    state = state.write_field(0, FIELD_FORMAT_Z_ALPHA, 0x00FF_0100)
    state = state.write_field(0, FIELD_COLOR_KEY, 0x00FF00)
    state = state.write_field(0, FIELD_CONTROL, 0x3)
    before_vblank = state
    mid_frame = state.tick(vblank=False)
    after_vblank = mid_frame.tick(vblank=True)
    return before_vblank, mid_frame, after_vblank


def fpga_compositor_vblank_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_compositor_vblank_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_compositor_vblank() -> str:
    profile = fpga_compositor_vblank_profile()
    lines = [
        "# FPGA Compositor Vblank Descriptors",
        "",
        f"Story: `{profile.story}`",
        f"Module: `{profile.latch_module}`",
        "",
        "## Descriptor Fields",
        "",
    ]
    lines.extend(f"- `{field}`" for field in profile.descriptor_fields)
    return "\n".join(lines)


def validate_fpga_compositor_vblank(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_vblank_profile()
    issues: list[str] = []

    issues.extend(
        f"I36-S03 prerequisite: {issue}"
        for issue in fpga_compositor_pipeline.validate_fpga_compositor_pipeline(root)
    )
    issues.extend(
        f"I35-S04 prerequisite: {issue}"
        for issue in fpga_video_mmio.validate_fpga_video_mmio(root)
    )

    if profile.story != FPGA_COMPOSITOR_VBLANK_STORY:
        issues.append(f"compositor vblank story must be {FPGA_COMPOSITOR_VBLANK_STORY}")
    if profile.pipeline_gate != fpga_compositor_pipeline.FPGA_COMPOSITOR_PIPELINE_TOOL:
        issues.append("compositor vblank latch must depend on I36-S03")
    if profile.video_mmio_gate != fpga_video_mmio.FPGA_VIDEO_MMIO_TOOL:
        issues.append("compositor vblank latch must depend on I35-S04")
    if profile.plane_count != 2:
        issues.append("compositor vblank latch must cover two planes")
    for field in ("base_cell", "stride_cells", "position_xy", "size_wh", "format_z_alpha"):
        if field not in profile.descriptor_fields:
            issues.append(f"missing descriptor field {field}")
    for bit in ("descriptor_pending", "descriptor_applied_pulse", "applied_count"):
        if bit not in profile.status_bits:
            issues.append(f"missing status bit {bit}")

    before, mid, after = demo_vblank_update()
    if not before.pending or not mid.pending:
        issues.append("shadow descriptor writes must set pending before vblank")
    if before.active[0].enable or mid.active[0].enable:
        issues.append("active descriptor must not change before vblank")
    if after.pending or after.applied_count != 1:
        issues.append("vblank update must clear pending and increment applied_count")
    if not after.active[0].enable or after.active[0].base_cell != 0x0110_0000:
        issues.append("vblank update must copy shadow descriptor into active descriptor")
    if after.active[0].x != 0x0014 or after.active[0].y != 0x000A:
        issues.append("position descriptor field decode mismatch")
    if after.active[0].width != 0x0040 or after.active[0].height != 0x0080:
        issues.append("size descriptor field decode mismatch")
    if after.active[0].color_key_rgb != 0x00FF00 or not after.active[0].color_key_enable:
        issues.append("color key descriptor field decode mismatch")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / FPGA_COMPOSITOR_VBLANK_RTL)
    tb = _read_if_exists(root / FPGA_COMPOSITOR_VBLANK_TB)
    for token in (
        "module cpu_v01_fpga_compositor_descriptor_latch",
        "shadow_plane0_base_q",
        "active_plane0_base_q",
        "descriptor_pending_o",
        "descriptor_applied_pulse_o",
        "applied_count_o",
        "vblank_q",
        "if (vblank_i && !vblank_q && descriptor_pending_o)",
    ):
        if token not in rtl:
            issues.append(f"{FPGA_COMPOSITOR_VBLANK_RTL.as_posix()} missing {token}")
    for token in (
        "module cpu_v01_fpga_compositor_descriptor_latch_tb",
        "cpu_v01_fpga_compositor_descriptor_latch dut",
        "descriptor latch active base changed before vblank",
        "descriptor latch did not apply on vblank",
        "descriptor latch did not expose pending status",
    ):
        if token not in tb:
            issues.append(f"{FPGA_COMPOSITOR_VBLANK_TB.as_posix()} missing {token}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_VBLANK_DOC)
    for token in (
        "Story: I36-S04",
        FPGA_COMPOSITOR_VBLANK_TOOL,
        "python tools\\fpga_compositor_pipeline.py --check",
        "python tools\\fpga_video_mmio.py --check",
        "cpu_v01_fpga_compositor_descriptor_latch",
        "shadow descriptor",
        "active descriptor",
        "vblank",
        "descriptor_pending",
        "descriptor_applied_pulse",
        "applied_count",
        "I36-S05",
        "I36-S08",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_VBLANK_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps([state.as_dict() for state in demo_vblank_update()], sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor vblank objects are not JSON serializable: {exc}")

    return tuple(issues)


def _write_descriptor_field(descriptor: PlaneDescriptor, field: int, value: int) -> PlaneDescriptor:
    value &= (1 << 48) - 1
    if field == FIELD_CONTROL:
        return replace(
            descriptor,
            enable=bool(value & 0x1),
            color_key_enable=bool(value & 0x2),
        )
    if field == FIELD_BASE:
        return replace(descriptor, base_cell=value)
    if field == FIELD_STRIDE:
        return replace(descriptor, stride_cells=value & 0xFFFF)
    if field == FIELD_POSITION:
        return replace(descriptor, x=value & 0xFFFF, y=(value >> 16) & 0xFFFF)
    if field == FIELD_SIZE:
        return replace(descriptor, width=value & 0xFFFF, height=(value >> 16) & 0xFFFF)
    if field == FIELD_FORMAT_Z_ALPHA:
        return replace(
            descriptor,
            pixel_format=value & 0xF,
            z=(value >> 8) & 0xF,
            alpha=(value >> 16) & 0xFF,
        )
    if field == FIELD_COLOR_KEY:
        return replace(descriptor, color_key_rgb=value & 0xFFFFFF)
    raise ValueError(f"unknown descriptor field {field}")


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

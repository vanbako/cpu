"""FPGA multi-plane compositor pipeline profile.

Owner stories:
- I36-S03: implement the multi-plane compositor pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_compositor_fetch


JsonValue = Any

FPGA_COMPOSITOR_PIPELINE_STORY = "I36-S03"
FPGA_COMPOSITOR_PIPELINE_DOC = Path("docs/implementation/fpga-compositor-pipeline.md")
FPGA_COMPOSITOR_PIPELINE_TOOL = "python tools\\fpga_compositor_pipeline.py --check"
FPGA_COMPOSITOR_PIPELINE_RTL = Path("rtl/cpu_v01_fpga_compositor_pipeline.sv")
FPGA_COMPOSITOR_PIPELINE_TB = Path("rtl/cpu_v01_fpga_compositor_pipeline_tb.sv")
ALPHA_OPAQUE = 255
ALPHA_HALF = 128


@dataclass(frozen=True)
class PlaneState:
    name: str
    enabled: bool
    x: int
    y: int
    width: int
    height: int
    z: int
    alpha: int
    color_key_enabled: bool
    color_key_rgb: int
    rgb: int
    valid: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("plane name must not be empty")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("plane width and height must be positive")
        if not 0 <= self.alpha <= 255:
            raise ValueError("plane alpha must fit 8 bits")
        if not 0 <= self.rgb <= 0xFFFFFF:
            raise ValueError("plane rgb must fit 24 bits")
        if not 0 <= self.color_key_rgb <= 0xFFFFFF:
            raise ValueError("plane color key must fit 24 bits")

    def contains(self, pixel_x: int, pixel_y: int) -> bool:
        return (
            self.enabled
            and self.valid
            and self.x <= pixel_x < self.x + self.width
            and self.y <= pixel_y < self.y + self.height
        )

    def transparent_at(self, pixel_x: int, pixel_y: int) -> bool:
        if not self.contains(pixel_x, pixel_y):
            return True
        return self.color_key_enabled and self.rgb == self.color_key_rgb

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "z": self.z,
            "alpha": self.alpha,
            "color_key_enabled": self.color_key_enabled,
            "color_key_rgb": self.color_key_rgb,
            "rgb": self.rgb,
            "valid": self.valid,
        }


@dataclass(frozen=True)
class CompositionResult:
    pixel_x: int
    pixel_y: int
    background_rgb: int
    rgb: int
    selected_plane: str
    sampled_planes: tuple[str, ...]
    clipped_planes: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "pixel_x": self.pixel_x,
            "pixel_y": self.pixel_y,
            "background_rgb": self.background_rgb,
            "rgb": self.rgb,
            "selected_plane": self.selected_plane,
            "sampled_planes": list(self.sampled_planes),
            "clipped_planes": list(self.clipped_planes),
        }


@dataclass(frozen=True)
class CompositorPipelineProfile:
    story: str
    fetch_gate: str
    validator: str
    compositor_module: str
    testbench_module: str
    max_planes: int
    composition_rules: tuple[str, ...]
    output_signals: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "fetch_gate": self.fetch_gate,
            "validator": self.validator,
            "compositor_module": self.compositor_module,
            "testbench_module": self.testbench_module,
            "max_planes": self.max_planes,
            "composition_rules": list(self.composition_rules),
            "output_signals": list(self.output_signals),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "handoffs": list(self.handoffs),
            "non_goals": list(self.non_goals),
        }


def fpga_compositor_pipeline_profile() -> CompositorPipelineProfile:
    return CompositorPipelineProfile(
        story=FPGA_COMPOSITOR_PIPELINE_STORY,
        fetch_gate=fpga_compositor_fetch.FPGA_COMPOSITOR_FETCH_TOOL,
        validator=FPGA_COMPOSITOR_PIPELINE_TOOL,
        compositor_module="cpu_v01_fpga_compositor_pipeline",
        testbench_module="cpu_v01_fpga_compositor_pipeline_tb",
        max_planes=2,
        composition_rules=(
            "disabled planes are ignored",
            "pixels outside plane x/y/width/height are clipped and not sampled",
            "higher z wins when both planes cover a pixel",
            "color-keyed pixels are transparent",
            "alpha 255 is opaque; alpha 0 is transparent; intermediate alpha blends over the current background",
        ),
        output_signals=(
            "rgb_o",
            "de_o",
            "selected_plane_o",
            "plane0_sample_o",
            "plane1_sample_o",
        ),
        rtl_sources=(FPGA_COMPOSITOR_PIPELINE_RTL.as_posix(), FPGA_COMPOSITOR_PIPELINE_TB.as_posix()),
        verilator_commands=fpga_compositor_pipeline_verilator_commands(),
        handoffs=(
            "I36-S04 latches plane descriptors atomically at vblank",
            "I36-S05 adds firmware and monitor demos for programming planes",
            "I36-S08 arbitrates shared CPU/compositor memory traffic",
        ),
        non_goals=(
            "descriptor_shadow_latch",
            "firmware_plane_programming",
            "memory_fetch_arbitration",
            "more_than_two_planes",
        ),
    )


def fpga_compositor_pipeline_verilator_commands() -> tuple[str, ...]:
    return (
        "verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_pipeline_tb "
        "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_pipeline.sv "
        "rtl/cpu_v01_fpga_compositor_pipeline_tb.sv",
    )


def compose_pixel(
    *,
    pixel_x: int,
    pixel_y: int,
    background_rgb: int,
    planes: tuple[PlaneState, ...],
) -> CompositionResult:
    ordered = sorted(planes, key=lambda plane: plane.z)
    rgb = background_rgb & 0xFFFFFF
    selected = "background"
    sampled: list[str] = []
    clipped: list[str] = []
    for plane in ordered:
        if plane.contains(pixel_x, pixel_y):
            sampled.append(plane.name)
        else:
            clipped.append(plane.name)
            continue
        if plane.transparent_at(pixel_x, pixel_y):
            continue
        rgb = alpha_blend(plane.rgb, rgb, plane.alpha)
        selected = plane.name
    return CompositionResult(
        pixel_x=pixel_x,
        pixel_y=pixel_y,
        background_rgb=background_rgb & 0xFFFFFF,
        rgb=rgb,
        selected_plane=selected,
        sampled_planes=tuple(sampled),
        clipped_planes=tuple(clipped),
    )


def alpha_blend(src_rgb: int, dst_rgb: int, alpha: int) -> int:
    if alpha <= 0:
        return dst_rgb & 0xFFFFFF
    if alpha >= ALPHA_OPAQUE:
        return src_rgb & 0xFFFFFF
    sr, sg, sb = _split_rgb(src_rgb)
    dr, dg, db = _split_rgb(dst_rgb)
    red = _blend_channel(sr, dr, alpha)
    green = _blend_channel(sg, dg, alpha)
    blue = _blend_channel(sb, db, alpha)
    return (red << 16) | (green << 8) | blue


def demo_composition() -> tuple[CompositionResult, ...]:
    background = 0x102030
    plane0 = PlaneState(
        name="plane0",
        enabled=True,
        x=0,
        y=0,
        width=4,
        height=4,
        z=0,
        alpha=ALPHA_OPAQUE,
        color_key_enabled=False,
        color_key_rgb=0,
        rgb=0xFF0000,
    )
    plane1 = PlaneState(
        name="plane1",
        enabled=True,
        x=2,
        y=0,
        width=4,
        height=4,
        z=1,
        alpha=ALPHA_HALF,
        color_key_enabled=False,
        color_key_rgb=0x00FF00,
        rgb=0x0000FF,
    )
    key_plane = PlaneState(
        name="plane1",
        enabled=True,
        x=2,
        y=0,
        width=4,
        height=4,
        z=1,
        alpha=ALPHA_OPAQUE,
        color_key_enabled=True,
        color_key_rgb=0x00FF00,
        rgb=0x00FF00,
    )
    return (
        compose_pixel(pixel_x=1, pixel_y=1, background_rgb=background, planes=(plane0, plane1)),
        compose_pixel(pixel_x=2, pixel_y=1, background_rgb=background, planes=(plane0, plane1)),
        compose_pixel(pixel_x=2, pixel_y=1, background_rgb=background, planes=(plane0, key_plane)),
        compose_pixel(pixel_x=7, pixel_y=7, background_rgb=background, planes=(plane0, plane1)),
    )


def fpga_compositor_pipeline_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_compositor_pipeline_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_compositor_pipeline() -> str:
    profile = fpga_compositor_pipeline_profile()
    lines = [
        "# FPGA Compositor Pipeline",
        "",
        f"Story: `{profile.story}`",
        f"Module: `{profile.compositor_module}`",
        f"Planes: `{profile.max_planes}`",
        "",
        "## Rules",
        "",
    ]
    lines.extend(f"- {rule}." for rule in profile.composition_rules)
    return "\n".join(lines)


def validate_fpga_compositor_pipeline(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_pipeline_profile()
    issues: list[str] = []

    issues.extend(
        f"I36-S02 prerequisite: {issue}"
        for issue in fpga_compositor_fetch.validate_fpga_compositor_fetch(root)
    )

    if profile.story != FPGA_COMPOSITOR_PIPELINE_STORY:
        issues.append(f"compositor pipeline story must be {FPGA_COMPOSITOR_PIPELINE_STORY}")
    if profile.fetch_gate != fpga_compositor_fetch.FPGA_COMPOSITOR_FETCH_TOOL:
        issues.append("compositor pipeline must depend on I36-S02")
    if profile.max_planes < 2:
        issues.append("compositor pipeline must support at least two planes")
    for rule in ("higher z wins", "color-keyed pixels", "alpha 255"):
        if not any(rule in item for item in profile.composition_rules):
            issues.append(f"missing composition rule {rule}")
    if "I36-S04 latches plane descriptors atomically at vblank" not in profile.handoffs:
        issues.append("compositor pipeline must hand descriptor latch to I36-S04")

    demo = demo_composition()
    if demo[0].rgb != 0xFF0000 or demo[0].selected_plane != "plane0":
        issues.append("single covered pixel must select plane0")
    if demo[1].rgb != alpha_blend(0x0000FF, 0xFF0000, ALPHA_HALF):
        issues.append("overlap pixel must alpha-blend higher-z plane over plane0")
    if demo[2].rgb != 0xFF0000 or demo[2].selected_plane != "plane0":
        issues.append("color-keyed higher-z pixel must reveal plane0")
    if demo[3].rgb != 0x102030 or demo[3].sampled_planes:
        issues.append("outside pixel must remain background without sampling planes")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / FPGA_COMPOSITOR_PIPELINE_RTL)
    tb = _read_if_exists(root / FPGA_COMPOSITOR_PIPELINE_TB)
    for token in (
        "module cpu_v01_fpga_compositor_pipeline",
        "plane0_sample_o",
        "plane1_sample_o",
        "selected_plane_o",
        "alpha_blend",
        "plane0_key_hit",
        "plane1_key_hit",
        "plane1_over_plane0",
        "rgb_o <= composed_rgb",
    ):
        if token not in rtl:
            issues.append(f"{FPGA_COMPOSITOR_PIPELINE_RTL.as_posix()} missing {token}")
    for token in (
        "module cpu_v01_fpga_compositor_pipeline_tb",
        "cpu_v01_fpga_compositor_pipeline dut",
        "compositor pipeline did not select plane0",
        "compositor pipeline did not alpha blend plane1",
        "compositor pipeline did not honor color key",
        "compositor pipeline sampled clipped planes",
    ):
        if token not in tb:
            issues.append(f"{FPGA_COMPOSITOR_PIPELINE_TB.as_posix()} missing {token}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_PIPELINE_DOC)
    for token in (
        "Story: I36-S03",
        FPGA_COMPOSITOR_PIPELINE_TOOL,
        "python tools\\fpga_compositor_fetch.py --check",
        "cpu_v01_fpga_compositor_pipeline",
        "plane0_sample_o",
        "plane1_sample_o",
        "selected_plane_o",
        "global alpha",
        "color-key",
        "z-order",
        "clipping",
        "I36-S04",
        "I36-S08",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_PIPELINE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps([result.as_dict() for result in demo], sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor pipeline objects are not JSON serializable: {exc}")

    return tuple(issues)


def _split_rgb(rgb: int) -> tuple[int, int, int]:
    return ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)


def _blend_channel(src: int, dst: int, alpha: int) -> int:
    return ((src * alpha) + (dst * (255 - alpha)) + 127) // 255


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

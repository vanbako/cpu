"""FPGA compositor firmware and monitor demo fixtures.

Owner stories:
- I36-S05: add firmware and monitor demos for framebuffer composition.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_compositor_framebuffer,
    fpga_compositor_pipeline,
    fpga_compositor_vblank,
    fpga_monitor_session,
    fpga_program_loader,
)


JsonValue = Any

FPGA_COMPOSITOR_DEMO_STORY = "I36-S05"
FPGA_COMPOSITOR_DEMO_DOC = Path("docs/implementation/fpga-compositor-firmware-monitor-demos.md")
FPGA_COMPOSITOR_DEMO_TOOL = "python tools\\fpga_compositor_demo.py --check"
FPGA_COMPOSITOR_DEMO_STATUS = "firmware_monitor_demo_fixture"

DEMO_WIDTH = 4
DEMO_HEIGHT = 4
DEMO_STRIDE_CELLS = 16
DEMO_BACKGROUND_RGB = 0x102030
FORMAT_XRGB8888_SELECT = 1

ONE_PLANE_BASE = fpga_compositor_framebuffer.FRAMEBUFFER_HEAP_BASE
OVERLAY_BASE = ONE_PLANE_BASE + 0x1000
SWAP_BASE = ONE_PLANE_BASE + 0x2000
BAD_BASE = fpga_compositor_framebuffer.FRAMEBUFFER_HEAP_END + 0x1000

RGB_RED = 0xFF0000
RGB_BLUE = 0x0000FF
RGB_GREEN = 0x00FF00
RGB_MAGENTA_KEY = 0xFF00FF


@dataclass(frozen=True)
class FramebufferSurface:
    name: str
    base_cell: int
    width: int
    height: int
    stride_cells: int
    pixel_format: str
    fill_rgb: int
    fill_pattern: str

    @property
    def end_cell(self) -> int:
        return self.base_cell + (self.stride_cells * self.height)

    @property
    def payload_digest(self) -> str:
        payload = "|".join(
            (
                self.name,
                f"{self.base_cell:012x}",
                str(self.width),
                str(self.height),
                str(self.stride_cells),
                self.pixel_format,
                f"{self.fill_rgb:06x}",
                self.fill_pattern,
            )
        )
        return hashlib.sha256(payload.encode("ascii")).hexdigest()

    def sample_rgb(self, x: int, y: int) -> int | None:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.fill_rgb
        return None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "width": self.width,
            "height": self.height,
            "stride_cells": self.stride_cells,
            "pixel_format": self.pixel_format,
            "fill_rgb": self.fill_rgb,
            "fill_pattern": self.fill_pattern,
            "payload_digest": self.payload_digest,
        }


@dataclass(frozen=True)
class DescriptorFieldWrite:
    plane: int
    field_name: str
    field_id: int
    value: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "plane": self.plane,
            "field_name": self.field_name,
            "field_id": self.field_id,
            "value": self.value,
        }


@dataclass(frozen=True)
class PlaneDescriptorProgram:
    plane: int
    base_cell: int
    stride_cells: int
    x: int
    y: int
    width: int
    height: int
    z: int
    alpha: int
    enable: bool = True
    pixel_format: int = FORMAT_XRGB8888_SELECT
    color_key_enable: bool = False
    color_key_rgb: int = RGB_MAGENTA_KEY

    def field_writes(self) -> tuple[DescriptorFieldWrite, ...]:
        control = (1 if self.enable else 0) | (2 if self.color_key_enable else 0)
        return (
            DescriptorFieldWrite(self.plane, "base_cell", fpga_compositor_vblank.FIELD_BASE, self.base_cell),
            DescriptorFieldWrite(
                self.plane,
                "stride_cells",
                fpga_compositor_vblank.FIELD_STRIDE,
                self.stride_cells,
            ),
            DescriptorFieldWrite(
                self.plane,
                "position_xy",
                fpga_compositor_vblank.FIELD_POSITION,
                ((self.y & 0xFFFF) << 16) | (self.x & 0xFFFF),
            ),
            DescriptorFieldWrite(
                self.plane,
                "size_wh",
                fpga_compositor_vblank.FIELD_SIZE,
                ((self.height & 0xFFFF) << 16) | (self.width & 0xFFFF),
            ),
            DescriptorFieldWrite(
                self.plane,
                "format_z_alpha",
                fpga_compositor_vblank.FIELD_FORMAT_Z_ALPHA,
                ((self.alpha & 0xFF) << 16) | ((self.z & 0xF) << 8) | (self.pixel_format & 0xF),
            ),
            DescriptorFieldWrite(
                self.plane,
                "color_key_rgb",
                fpga_compositor_vblank.FIELD_COLOR_KEY,
                self.color_key_rgb & 0xFFFFFF,
            ),
            DescriptorFieldWrite(self.plane, "control", fpga_compositor_vblank.FIELD_CONTROL, control),
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "plane": self.plane,
            "base_cell": self.base_cell,
            "stride_cells": self.stride_cells,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "z": self.z,
            "alpha": self.alpha,
            "enable": self.enable,
            "pixel_format": self.pixel_format,
            "color_key_enable": self.color_key_enable,
            "color_key_rgb": self.color_key_rgb,
        }


@dataclass(frozen=True)
class DemoSignature:
    led: str
    uart: str
    probe: str
    status_code: int

    @property
    def digest(self) -> str:
        payload = "|".join((self.led, self.uart, self.probe, f"{self.status_code:08x}"))
        return hashlib.sha256(payload.encode("ascii")).hexdigest()

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "led": self.led,
            "uart": self.uart,
            "probe": self.probe,
            "status_code": self.status_code,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class CompositorDemoPhase:
    phase_id: str
    descriptor_programs: tuple[PlaneDescriptorProgram, ...]
    sample_x: int
    sample_y: int
    expected_rgb: int
    expected_selected_plane: str
    expected_underflow: bool
    signature: DemoSignature

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "phase_id": self.phase_id,
            "descriptor_programs": [program.as_dict() for program in self.descriptor_programs],
            "sample_x": self.sample_x,
            "sample_y": self.sample_y,
            "expected_rgb": self.expected_rgb,
            "expected_selected_plane": self.expected_selected_plane,
            "expected_underflow": self.expected_underflow,
            "signature": self.signature.as_dict(),
        }


@dataclass(frozen=True)
class CompositorDemoCase:
    case_id: str
    actor: str
    program_id: str
    manifest_image_sha256: str
    ram_image_sha256: str
    monitor_case_id: str | None
    description: str
    framebuffers: tuple[FramebufferSurface, ...]
    command_script: tuple[str, ...]
    phases: tuple[CompositorDemoPhase, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "actor": self.actor,
            "program_id": self.program_id,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "monitor_case_id": self.monitor_case_id,
            "description": self.description,
            "framebuffers": [surface.as_dict() for surface in self.framebuffers],
            "command_script": list(self.command_script),
            "phases": [phase.as_dict() for phase in self.phases],
        }


@dataclass(frozen=True)
class CompositorDemoProfile:
    story: str
    status: str
    vblank_gate: str
    loader_gate: str
    monitor_session_gate: str
    framebuffer_gate: str
    validator: str
    command_vocabulary: tuple[str, ...]
    cases: tuple[CompositorDemoCase, ...]
    handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def case_by_id(self, case_id: str) -> CompositorDemoCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "vblank_gate": self.vblank_gate,
            "loader_gate": self.loader_gate,
            "monitor_session_gate": self.monitor_session_gate,
            "framebuffer_gate": self.framebuffer_gate,
            "validator": self.validator,
            "command_vocabulary": list(self.command_vocabulary),
            "cases": [case.as_dict() for case in self.cases],
            "handoffs": list(self.handoffs),
            "non_goals": list(self.non_goals),
        }


@dataclass(frozen=True)
class CompositorDemoObservation:
    case_id: str
    actor: str
    phase_id: str
    program_id: str
    applied_count: int
    pending_before_vblank: bool
    pending_after_vblank: bool
    sample_x: int
    sample_y: int
    rgb: int
    selected_plane: str
    sampled_planes: tuple[str, ...]
    underflow: bool
    field_writes: tuple[DescriptorFieldWrite, ...]
    signature: DemoSignature

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "actor": self.actor,
            "phase_id": self.phase_id,
            "program_id": self.program_id,
            "applied_count": self.applied_count,
            "pending_before_vblank": self.pending_before_vblank,
            "pending_after_vblank": self.pending_after_vblank,
            "sample_x": self.sample_x,
            "sample_y": self.sample_y,
            "rgb": self.rgb,
            "selected_plane": self.selected_plane,
            "sampled_planes": list(self.sampled_planes),
            "underflow": self.underflow,
            "field_writes": [write.as_dict() for write in self.field_writes],
            "signature": self.signature.as_dict(),
        }


@dataclass(frozen=True)
class CompositorDemoRun:
    story: str
    status: str
    observations: tuple[CompositorDemoObservation, ...]
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def observation_by_phase(self, case_id: str, phase_id: str) -> CompositorDemoObservation:
        for observation in self.observations:
            if observation.case_id == case_id and observation.phase_id == phase_id:
                return observation
        raise KeyError(f"{case_id}:{phase_id}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "passed": self.passed,
            "observations": [observation.as_dict() for observation in self.observations],
            "issues": list(self.issues),
        }


def fpga_compositor_demo_profile() -> CompositorDemoProfile:
    return CompositorDemoProfile(
        story=FPGA_COMPOSITOR_DEMO_STORY,
        status=FPGA_COMPOSITOR_DEMO_STATUS,
        vblank_gate=fpga_compositor_vblank.FPGA_COMPOSITOR_VBLANK_TOOL,
        loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        monitor_session_gate=fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        framebuffer_gate=fpga_compositor_framebuffer.FPGA_COMPOSITOR_FRAMEBUFFER_TOOL,
        validator=FPGA_COMPOSITOR_DEMO_TOOL,
        command_vocabulary=(
            "LOAD_IMAGE",
            "COMPOSITOR_FILL",
            "PROGRAM_PLANE",
            "WAIT_VBLANK",
            "SWAP_DESCRIPTOR",
            "READ_STATUS",
        ),
        cases=_demo_cases(),
        handoffs=(
            "I36-S06 archives timing, bandwidth, resource, and underflow evidence for these demos",
            "I36-S07 captures first board compositor demo evidence or blocker disposition",
            "I36-S08 closes shared CPU/compositor memory arbitration before board claims",
        ),
        non_goals=(
            "physical_board_capture",
            "cycle_accurate_firmware_binary",
            "shared_memory_arbiter",
            "new_monitor_transport_command_set",
        ),
    )


def run_compositor_demo(case_ids: tuple[str, ...] | None = None) -> CompositorDemoRun:
    profile = fpga_compositor_demo_profile()
    selected_ids = tuple(case.case_id for case in profile.cases) if case_ids is None else case_ids
    observations: list[CompositorDemoObservation] = []
    issues: list[str] = []
    if len(selected_ids) != len(set(selected_ids)):
        issues.append("demo run selected duplicate cases")

    for case_id in selected_ids:
        try:
            case = profile.case_by_id(case_id)
        except KeyError:
            issues.append(f"unknown demo case {case_id}")
            continue
        case_observations, case_issues = _run_demo_case(case)
        observations.extend(case_observations)
        issues.extend(f"{case.case_id}: {issue}" for issue in case_issues)

    signature_digests = [observation.signature.digest for observation in observations]
    if len(signature_digests) != len(set(signature_digests)):
        issues.append("demo observations must preserve distinct visible/status signatures")

    return CompositorDemoRun(
        story=FPGA_COMPOSITOR_DEMO_STORY,
        status=FPGA_COMPOSITOR_DEMO_STATUS,
        observations=tuple(observations),
        issues=tuple(issues),
    )


def fpga_compositor_demo_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_compositor_demo_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_compositor_demo_run_json(*, indent: int = 2) -> str:
    return json.dumps(run_compositor_demo().as_dict(), indent=indent, sort_keys=True)


def render_fpga_compositor_demo(profile: CompositorDemoProfile | None = None) -> str:
    if profile is None:
        profile = fpga_compositor_demo_profile()
    lines = [
        "# FPGA Compositor Firmware And Monitor Demos",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Vblank gate: `{profile.vblank_gate}`",
        f"Loader gate: `{profile.loader_gate}`",
        f"Monitor session gate: `{profile.monitor_session_gate}`",
        "",
        "## Demo Cases",
        "",
        "| Case | Actor | Program | Phases |",
        "| --- | --- | --- | ---: |",
    ]
    for case in profile.cases:
        lines.append(
            f"| `{case.case_id}` | `{case.actor}` | `{case.program_id}` | {len(case.phases)} |"
        )
    lines.extend(["", "## Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.command_vocabulary)
    return "\n".join(lines)


def validate_fpga_compositor_demo(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_demo_profile()
    issues: list[str] = []

    issues.extend(
        f"I36-S04 prerequisite: {issue}"
        for issue in fpga_compositor_vblank.validate_fpga_compositor_vblank(root)
    )
    issues.extend(
        f"I26-S04 prerequisite: {issue}"
        for issue in fpga_program_loader.validate_fpga_program_loader(root)
    )
    issues.extend(
        f"I32-S03 prerequisite: {issue}"
        for issue in fpga_monitor_session.validate_fpga_monitor_session(root)
    )

    if profile.story != FPGA_COMPOSITOR_DEMO_STORY:
        issues.append(f"compositor demo story must be {FPGA_COMPOSITOR_DEMO_STORY}")
    if profile.status != FPGA_COMPOSITOR_DEMO_STATUS:
        issues.append("compositor demo status must remain fixture-defined")
    if profile.vblank_gate != fpga_compositor_vblank.FPGA_COMPOSITOR_VBLANK_TOOL:
        issues.append("compositor demo must depend on I36-S04")
    if profile.loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("compositor demo must depend on I26-S04")
    if profile.monitor_session_gate != fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL:
        issues.append("compositor demo must depend on I32-S03")
    for command in ("COMPOSITOR_FILL", "PROGRAM_PLANE", "WAIT_VBLANK", "SWAP_DESCRIPTOR"):
        if command not in profile.command_vocabulary:
            issues.append(f"compositor demo command vocabulary missing {command}")

    case_ids = [case.case_id for case in profile.cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("compositor demo case IDs must be unique")
    for required in ("one_plane_fill", "overlay_swap", "error_path_underflow"):
        if required not in case_ids:
            issues.append(f"missing compositor demo case {required}")
    actors = {case.actor for case in profile.cases}
    if actors != {"firmware", "monitor"}:
        issues.append("compositor demos must include firmware and monitor actors")

    monitor_cases = {
        selection.case_id for selection in fpga_monitor_session.fpga_monitor_session_profile().selected_cases
    }
    loader_profile = fpga_program_loader.fpga_program_loader_profile()
    window = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile().framebuffer_window
    for case in profile.cases:
        try:
            loader_profile.plan_by_program_id(case.program_id)
        except KeyError:
            issues.append(f"{case.case_id}: program_id is not loader-visible")
        if len(case.manifest_image_sha256) != 64:
            issues.append(f"{case.case_id}: manifest hash must be SHA-256")
        if len(case.ram_image_sha256) != 64:
            issues.append(f"{case.case_id}: RAM hash must be SHA-256")
        if case.actor == "monitor" and case.monitor_case_id not in monitor_cases:
            issues.append(f"{case.case_id}: monitor actor must name an I32-S03 case")
        for surface in case.framebuffers:
            if surface.base_cell < window.base_cell or surface.end_cell > window.end_cell:
                issues.append(f"{case.case_id}:{surface.name}: surface outside framebuffer heap")
            if surface.base_cell % fpga_compositor_framebuffer.FRAMEBUFFER_ALIGN_CELLS != 0:
                issues.append(f"{case.case_id}:{surface.name}: surface base is not framebuffer-aligned")
            if surface.stride_cells % fpga_compositor_framebuffer.STRIDE_ALIGN_CELLS != 0:
                issues.append(f"{case.case_id}:{surface.name}: surface stride is not aligned")

    run = run_compositor_demo()
    if not run.passed:
        issues.extend(run.issues)
    try:
        one = run.observation_by_phase("one_plane_fill", "one_plane")
        overlay = run.observation_by_phase("overlay_swap", "overlay")
        swap = run.observation_by_phase("overlay_swap", "swap")
        error = run.observation_by_phase("error_path_underflow", "bad_base")
    except KeyError as exc:
        issues.append(f"missing compositor demo observation {exc}")
    else:
        if one.rgb != RGB_RED or one.selected_plane != "plane0" or one.underflow:
            issues.append("one-plane demo must select a red plane0 pixel without underflow")
        expected_overlay = fpga_compositor_pipeline.alpha_blend(RGB_BLUE, RGB_RED, 128)
        if overlay.rgb != expected_overlay or overlay.selected_plane != "plane1" or overlay.underflow:
            issues.append("overlay demo must alpha-blend plane1 over plane0 without underflow")
        if swap.rgb != RGB_GREEN or swap.selected_plane != "plane1" or swap.applied_count != 2:
            issues.append("swap demo must apply the second descriptor at the second vblank")
        if error.rgb != DEMO_BACKGROUND_RGB or error.selected_plane != "background" or not error.underflow:
            issues.append("error-path demo must report underflow and leave background visible")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor demo objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_DEMO_DOC)
    for token in (
        "Story: I36-S05",
        FPGA_COMPOSITOR_DEMO_TOOL,
        fpga_compositor_vblank.FPGA_COMPOSITOR_VBLANK_TOOL,
        fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        "one_plane_fill",
        "overlay_swap",
        "error_path_underflow",
        "COMPOSITOR_FILL",
        "PROGRAM_PLANE",
        "WAIT_VBLANK",
        "SWAP_DESCRIPTOR",
        "descriptor_pending",
        "applied_count",
        "expected LED",
        "expected UART",
        "expected probe",
        "UNDERFLOW_ERROR",
        "I36-S06",
        "I36-S07",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_DEMO_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _demo_cases() -> tuple[CompositorDemoCase, ...]:
    red = FramebufferSurface(
        "red_base",
        ONE_PLANE_BASE,
        DEMO_WIDTH,
        DEMO_HEIGHT,
        DEMO_STRIDE_CELLS,
        "xrgb8888",
        RGB_RED,
        "solid_red",
    )
    blue = FramebufferSurface(
        "blue_overlay",
        OVERLAY_BASE,
        DEMO_WIDTH,
        DEMO_HEIGHT,
        DEMO_STRIDE_CELLS,
        "xrgb8888",
        RGB_BLUE,
        "solid_blue",
    )
    green = FramebufferSurface(
        "green_swap",
        SWAP_BASE,
        DEMO_WIDTH,
        DEMO_HEIGHT,
        DEMO_STRIDE_CELLS,
        "xrgb8888",
        RGB_GREEN,
        "solid_green",
    )
    one_loader = _loader_hashes("relocation.branch_call_data_fpga")
    overlay_loader = _loader_hashes("call_return.direct_call_ret_fpga")
    error_loader = _loader_hashes("syscall_trap.sys_pause_iret_fpga")
    return (
        CompositorDemoCase(
            case_id="one_plane_fill",
            actor="firmware",
            program_id="relocation.branch_call_data_fpga",
            manifest_image_sha256=one_loader[0],
            ram_image_sha256=one_loader[1],
            monitor_case_id=None,
            description="Firmware fills one framebuffer, programs plane0, and waits for vblank.",
            framebuffers=(red,),
            command_script=(
                "LOAD_IMAGE relocation.branch_call_data_fpga",
                "COMPOSITOR_FILL red_base solid_red",
                "PROGRAM_PLANE plane0 red_base",
                "WAIT_VBLANK",
                "READ_STATUS",
            ),
            phases=(
                CompositorDemoPhase(
                    phase_id="one_plane",
                    descriptor_programs=(
                        PlaneDescriptorProgram(
                            plane=0,
                            base_cell=red.base_cell,
                            stride_cells=red.stride_cells,
                            x=0,
                            y=0,
                            width=red.width,
                            height=red.height,
                            z=0,
                            alpha=255,
                        ),
                    ),
                    sample_x=1,
                    sample_y=1,
                    expected_rgb=RGB_RED,
                    expected_selected_plane="plane0",
                    expected_underflow=False,
                    signature=DemoSignature(
                        "I36S05_LED_ONE_PLANE_PASS",
                        "I36-S05 ONE_PLANE rgb=FF0000 applied=1",
                        "plane0_active selected=plane0 underflow=0",
                        0x3605_0001,
                    ),
                ),
            ),
        ),
        CompositorDemoCase(
            case_id="overlay_swap",
            actor="monitor",
            program_id="call_return.direct_call_ret_fpga",
            manifest_image_sha256=overlay_loader[0],
            ram_image_sha256=overlay_loader[1],
            monitor_case_id="scalar_control.call_return",
            description="Monitor fixture fills two planes, observes overlay, swaps plane1, and waits for vblank.",
            framebuffers=(red, blue, green),
            command_script=(
                "HELLO",
                "HALT",
                "LOAD_IMAGE call_return.direct_call_ret_fpga",
                "COMPOSITOR_FILL red_base solid_red",
                "COMPOSITOR_FILL blue_overlay solid_blue",
                "PROGRAM_PLANE plane0 red_base",
                "PROGRAM_PLANE plane1 blue_overlay",
                "WAIT_VBLANK",
                "COMPOSITOR_FILL green_swap solid_green",
                "SWAP_DESCRIPTOR plane1 green_swap",
                "WAIT_VBLANK",
                "READ_STATUS",
                "RESUME",
            ),
            phases=(
                CompositorDemoPhase(
                    phase_id="overlay",
                    descriptor_programs=(
                        PlaneDescriptorProgram(
                            plane=0,
                            base_cell=red.base_cell,
                            stride_cells=red.stride_cells,
                            x=0,
                            y=0,
                            width=red.width,
                            height=red.height,
                            z=0,
                            alpha=255,
                        ),
                        PlaneDescriptorProgram(
                            plane=1,
                            base_cell=blue.base_cell,
                            stride_cells=blue.stride_cells,
                            x=2,
                            y=0,
                            width=blue.width,
                            height=blue.height,
                            z=1,
                            alpha=128,
                        ),
                    ),
                    sample_x=2,
                    sample_y=1,
                    expected_rgb=fpga_compositor_pipeline.alpha_blend(RGB_BLUE, RGB_RED, 128),
                    expected_selected_plane="plane1",
                    expected_underflow=False,
                    signature=DemoSignature(
                        "I36S05_LED_OVERLAY_PASS",
                        "I36-S05 OVERLAY rgb=7F0080 applied=1",
                        "plane1_over_plane0 alpha=128 underflow=0",
                        0x3605_0002,
                    ),
                ),
                CompositorDemoPhase(
                    phase_id="swap",
                    descriptor_programs=(
                        PlaneDescriptorProgram(
                            plane=1,
                            base_cell=green.base_cell,
                            stride_cells=green.stride_cells,
                            x=2,
                            y=0,
                            width=green.width,
                            height=green.height,
                            z=1,
                            alpha=255,
                        ),
                    ),
                    sample_x=2,
                    sample_y=1,
                    expected_rgb=RGB_GREEN,
                    expected_selected_plane="plane1",
                    expected_underflow=False,
                    signature=DemoSignature(
                        "I36S05_LED_SWAP_PASS",
                        "I36-S05 SWAP rgb=00FF00 applied=2",
                        "plane1_swap selected=plane1 underflow=0",
                        0x3605_0003,
                    ),
                ),
            ),
        ),
        CompositorDemoCase(
            case_id="error_path_underflow",
            actor="firmware",
            program_id="syscall_trap.sys_pause_iret_fpga",
            manifest_image_sha256=error_loader[0],
            ram_image_sha256=error_loader[1],
            monitor_case_id=None,
            description="Firmware programs an out-of-window plane base and observes deterministic underflow status.",
            framebuffers=(),
            command_script=(
                "LOAD_IMAGE syscall_trap.sys_pause_iret_fpga",
                "PROGRAM_PLANE plane0 bad_base",
                "WAIT_VBLANK",
                "READ_STATUS UNDERFLOW_ERROR",
            ),
            phases=(
                CompositorDemoPhase(
                    phase_id="bad_base",
                    descriptor_programs=(
                        PlaneDescriptorProgram(
                            plane=0,
                            base_cell=BAD_BASE,
                            stride_cells=DEMO_STRIDE_CELLS,
                            x=0,
                            y=0,
                            width=DEMO_WIDTH,
                            height=DEMO_HEIGHT,
                            z=0,
                            alpha=255,
                        ),
                    ),
                    sample_x=0,
                    sample_y=0,
                    expected_rgb=DEMO_BACKGROUND_RGB,
                    expected_selected_plane="background",
                    expected_underflow=True,
                    signature=DemoSignature(
                        "I36S05_LED_UNDERFLOW_ERROR",
                        "I36-S05 UNDERFLOW_ERROR bad_base",
                        "plane0_underflow selected=background underflow=1",
                        0x3605_00E1,
                    ),
                ),
            ),
        ),
    )


def _run_demo_case(case: CompositorDemoCase) -> tuple[list[CompositorDemoObservation], list[str]]:
    state = fpga_compositor_vblank.initial_latch_state()
    observations: list[CompositorDemoObservation] = []
    issues: list[str] = []
    surfaces = {surface.base_cell: surface for surface in case.framebuffers}

    for phase in case.phases:
        writes: list[DescriptorFieldWrite] = []
        for program in phase.descriptor_programs:
            for write in program.field_writes():
                state = state.write_field(write.plane, write.field_id, write.value)
                writes.append(write)
        pending_before = state.pending
        state = state.tick(vblank=False)
        state = state.tick(vblank=True)
        composition, underflow = _compose_active_sample(
            state,
            surfaces,
            sample_x=phase.sample_x,
            sample_y=phase.sample_y,
        )
        observation = CompositorDemoObservation(
            case_id=case.case_id,
            actor=case.actor,
            phase_id=phase.phase_id,
            program_id=case.program_id,
            applied_count=state.applied_count,
            pending_before_vblank=pending_before,
            pending_after_vblank=state.pending,
            sample_x=phase.sample_x,
            sample_y=phase.sample_y,
            rgb=composition.rgb,
            selected_plane=composition.selected_plane,
            sampled_planes=composition.sampled_planes,
            underflow=underflow,
            field_writes=tuple(writes),
            signature=phase.signature,
        )
        observations.append(observation)
        issues.extend(_phase_issues(phase, observation))
        state = state.tick(vblank=False)

    return observations, issues


def _compose_active_sample(
    state: fpga_compositor_vblank.DescriptorLatchState,
    surfaces: dict[int, FramebufferSurface],
    *,
    sample_x: int,
    sample_y: int,
) -> tuple[fpga_compositor_pipeline.CompositionResult, bool]:
    planes: list[fpga_compositor_pipeline.PlaneState] = []
    underflow = False
    for index, descriptor in enumerate(state.active):
        plane_underflow = False
        rgb = 0
        if _descriptor_covers(descriptor, sample_x, sample_y):
            local_x = sample_x - descriptor.x
            local_y = sample_y - descriptor.y
            surface = surfaces.get(descriptor.base_cell)
            sampled = None if surface is None else surface.sample_rgb(local_x, local_y)
            if sampled is None:
                plane_underflow = True
                underflow = True
            else:
                rgb = sampled
        planes.append(
            fpga_compositor_pipeline.PlaneState(
                name=f"plane{index}",
                enabled=descriptor.enable,
                x=descriptor.x,
                y=descriptor.y,
                width=max(1, descriptor.width),
                height=max(1, descriptor.height),
                z=descriptor.z,
                alpha=descriptor.alpha,
                color_key_enabled=descriptor.color_key_enable,
                color_key_rgb=descriptor.color_key_rgb,
                rgb=rgb,
                valid=not plane_underflow,
            )
        )
    return (
        fpga_compositor_pipeline.compose_pixel(
            pixel_x=sample_x,
            pixel_y=sample_y,
            background_rgb=DEMO_BACKGROUND_RGB,
            planes=tuple(planes),
        ),
        underflow,
    )


def _phase_issues(
    phase: CompositorDemoPhase,
    observation: CompositorDemoObservation,
) -> list[str]:
    issues: list[str] = []
    if not observation.pending_before_vblank:
        issues.append(f"{phase.phase_id}: descriptor writes did not set descriptor_pending")
    if observation.pending_after_vblank:
        issues.append(f"{phase.phase_id}: descriptor_pending did not clear after WAIT_VBLANK")
    if observation.rgb != phase.expected_rgb:
        issues.append(f"{phase.phase_id}: rgb 0x{observation.rgb:06X} did not match expected")
    if observation.selected_plane != phase.expected_selected_plane:
        issues.append(f"{phase.phase_id}: selected plane mismatch")
    if observation.underflow != phase.expected_underflow:
        issues.append(f"{phase.phase_id}: underflow status mismatch")
    if not observation.signature.digest:
        issues.append(f"{phase.phase_id}: signature digest missing")
    return issues


def _descriptor_covers(
    descriptor: fpga_compositor_vblank.PlaneDescriptor,
    sample_x: int,
    sample_y: int,
) -> bool:
    return (
        descriptor.enable
        and descriptor.x <= sample_x < descriptor.x + descriptor.width
        and descriptor.y <= sample_y < descriptor.y + descriptor.height
    )


def _loader_hashes(program_id: str) -> tuple[str, str]:
    request = fpga_program_loader.program_load_request_for_program(program_id)
    return request.manifest_image_sha256, request.ram_image_sha256


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

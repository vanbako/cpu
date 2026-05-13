"""FPGA compositor timing, bandwidth, resource, and underflow evidence archive.

Owner stories:
- I36-S06: archive compositor timing, bandwidth, resource, and underflow evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_compositor_demo,
    fpga_compositor_framebuffer,
    fpga_external_memory_evidence,
    fpga_gowin_reports,
    fpga_video_timing,
)


JsonValue = Any

FPGA_COMPOSITOR_EVIDENCE_STORY = "I36-S06"
FPGA_COMPOSITOR_EVIDENCE_DOC = Path("docs/implementation/fpga-compositor-evidence-archive.md")
FPGA_COMPOSITOR_EVIDENCE_TOOL = "python tools\\fpga_compositor_evidence.py --check"
FPGA_COMPOSITOR_EVIDENCE_PATH = Path(
    "docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt"
)
FPGA_COMPOSITOR_EVIDENCE_RESULT = "compositor_evidence_archived"
COMPOSITOR_DEMO_PASS = "compositor_demo_pass"

ARCHIVE_ARCHIVED = "archived"
ARCHIVE_BLOCKED = "blocked"
ARCHIVE_INVALID = "invalid"
ARCHIVE_NEEDS_FOLLOWUP = "needs_followup"

BYTES_PER_XRGB8888_PIXEL = 4
TWO_PLANE_XRGB8888 = "two_plane_xrgb8888"


@dataclass(frozen=True)
class CompositorEvidenceField:
    name: str
    required: bool
    description: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class CompositorBandwidthAssumption:
    scenario: str
    pixel_clock_hz: int
    planes: int
    bytes_per_pixel: int
    required_bytes_per_second: int
    required_cells_per_second: int
    notes: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "scenario": self.scenario,
            "pixel_clock_hz": self.pixel_clock_hz,
            "planes": self.planes,
            "bytes_per_pixel": self.bytes_per_pixel,
            "required_bytes_per_second": self.required_bytes_per_second,
            "required_cells_per_second": self.required_cells_per_second,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CompositorLineBufferEvidence:
    active_width: int
    max_bytes_per_pixel: int
    buffered_lines: int
    required_cells: int
    allocated_cells: int
    underflow_counter: str

    @property
    def margin_cells(self) -> int:
        return self.allocated_cells - self.required_cells

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "active_width": self.active_width,
            "max_bytes_per_pixel": self.max_bytes_per_pixel,
            "buffered_lines": self.buffered_lines,
            "required_cells": self.required_cells,
            "allocated_cells": self.allocated_cells,
            "margin_cells": self.margin_cells,
            "underflow_counter": self.underflow_counter,
        }


@dataclass(frozen=True)
class CompositorEvidenceProfile:
    story: str
    evidence_path: Path
    required_result: str
    compositor_demo_gate: str
    gowin_report_gate: str
    external_memory_evidence_gate: str
    video_timing_gate: str
    active_mode: str
    pixel_clock_hz: int
    bandwidth_assumption: CompositorBandwidthAssumption
    line_buffer: CompositorLineBufferEvidence
    required_fields: tuple[CompositorEvidenceField, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> CompositorEvidenceField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "evidence_path": self.evidence_path.as_posix(),
            "required_result": self.required_result,
            "compositor_demo_gate": self.compositor_demo_gate,
            "gowin_report_gate": self.gowin_report_gate,
            "external_memory_evidence_gate": self.external_memory_evidence_gate,
            "video_timing_gate": self.video_timing_gate,
            "active_mode": self.active_mode,
            "pixel_clock_hz": self.pixel_clock_hz,
            "bandwidth_assumption": self.bandwidth_assumption.as_dict(),
            "line_buffer": self.line_buffer.as_dict(),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class CompositorEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class CompositorEvidenceAudit:
    status: str
    message: str
    evidence_path: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    metric_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == ARCHIVE_ARCHIVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "metric_issues": list(self.metric_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_compositor_evidence_profile() -> CompositorEvidenceProfile:
    timing = fpga_video_timing.fpga_video_timing_profile()
    line_buffer = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile().line_buffer
    required_bandwidth = timing.pixel_clock_hz * 2 * BYTES_PER_XRGB8888_PIXEL
    required_cells = _ceil_div(required_bandwidth, fpga_compositor_framebuffer.PAYLOAD_BYTES_PER_CELL)
    return CompositorEvidenceProfile(
        story=FPGA_COMPOSITOR_EVIDENCE_STORY,
        evidence_path=FPGA_COMPOSITOR_EVIDENCE_PATH,
        required_result=FPGA_COMPOSITOR_EVIDENCE_RESULT,
        compositor_demo_gate=fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
        gowin_report_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        external_memory_evidence_gate=fpga_external_memory_evidence.FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL,
        video_timing_gate=fpga_video_timing.FPGA_VIDEO_TIMING_TOOL,
        active_mode=f"{timing.active_width}x{timing.active_height}@{timing.pixel_clock_hz}",
        pixel_clock_hz=timing.pixel_clock_hz,
        bandwidth_assumption=CompositorBandwidthAssumption(
            scenario=TWO_PLANE_XRGB8888,
            pixel_clock_hz=timing.pixel_clock_hz,
            planes=2,
            bytes_per_pixel=BYTES_PER_XRGB8888_PIXEL,
            required_bytes_per_second=required_bandwidth,
            required_cells_per_second=required_cells,
            notes="Worst first-pass payload assumption: two opaque XRGB8888 planes read at active pixel rate.",
        ),
        line_buffer=CompositorLineBufferEvidence(
            active_width=line_buffer.active_width,
            max_bytes_per_pixel=line_buffer.max_bytes_per_pixel,
            buffered_lines=line_buffer.buffered_lines,
            required_cells=line_buffer.required_cells,
            allocated_cells=line_buffer.allocated_cells,
            underflow_counter=line_buffer.underflow_counter,
        ),
        required_fields=(
            CompositorEvidenceField("story", True, "Must be I36-S06."),
            CompositorEvidenceField("archived_at", True, "Local archive date/time."),
            CompositorEvidenceField("repository_commit", True, "Repository commit used for the evidence bundle."),
            CompositorEvidenceField("active_mode", True, "Must be the 1280x720 compositor mode string."),
            CompositorEvidenceField("pixel_clock_hz", True, "Must match the I35-S02 74.25 MHz pixel clock."),
            CompositorEvidenceField("bandwidth_scenario", True, "Must name the two-plane XRGB8888 assumption."),
            CompositorEvidenceField("required_bandwidth_bytes_per_second", True, "Required scanout payload bandwidth."),
            CompositorEvidenceField("available_bandwidth_bytes_per_second", True, "Available DDR or reduced-mode payload bandwidth."),
            CompositorEvidenceField("line_buffer_required_cells", True, "Cells needed for the configured buffered lines."),
            CompositorEvidenceField("line_buffer_allocated_cells", True, "Configured line-buffer cell depth."),
            CompositorEvidenceField("utilization_lut", True, "LUT utilization from Gowin reports."),
            CompositorEvidenceField("utilization_register", True, "Register utilization from Gowin reports."),
            CompositorEvidenceField("utilization_bram", True, "BRAM/B-SRAM utilization from Gowin reports."),
            CompositorEvidenceField("timing_slack_ns", True, "Worst timing slack from Gowin reports."),
            CompositorEvidenceField("timing_report_bundle", True, "Path to the parsed timing/utilization bundle."),
            CompositorEvidenceField("gowin_report_audit", True, "I28-S03 parser audit output or path."),
            CompositorEvidenceField("external_memory_evidence", True, "I29-S05 external-memory evidence archive path."),
            CompositorEvidenceField("ddr_calibration_dependency", True, "DDR calibration status dependency."),
            CompositorEvidenceField("underflow_counter_one_plane", True, "Counter value after one-plane demo."),
            CompositorEvidenceField("underflow_counter_overlay", True, "Counter value after overlay and swap demos."),
            CompositorEvidenceField("underflow_counter_error", True, "Counter value after error-path demo."),
            CompositorEvidenceField("compositor_demo_result", True, "Must be compositor_demo_pass."),
            CompositorEvidenceField("archive_result", True, "Must be compositor_evidence_archived."),
            CompositorEvidenceField("reduced_mode_fallback", True, "none, or a concrete reduced-mode fallback."),
            CompositorEvidenceField("residual_blockers", True, "none, or named blockers."),
            CompositorEvidenceField("filed_issues", True, "none, or issue IDs for residual blockers."),
            CompositorEvidenceField("retest_commands", True, "Commands to rerun validators and evidence checks."),
        ),
        link_fields=(
            "timing_report_bundle",
            "gowin_report_audit",
            "external_memory_evidence",
        ),
        retest_commands=(
            fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            fpga_external_memory_evidence.FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL,
            FPGA_COMPOSITOR_EVIDENCE_TOOL,
        ),
        blockers=(
            "Gowin timing and utilization reports must be parsed by I28-S03 before archive pass",
            "I29-S05 external-memory evidence must show DDR calibration and memory-test disposition",
            "underflow counters must be zero for one-plane and overlay demos and nonzero for the error-path demo",
            "available bandwidth must satisfy the two-plane XRGB8888 assumption or name a reduced-mode fallback",
            "residual blockers must be none, or filed with issue IDs and retest commands",
        ),
    )


def compositor_evidence_template(
    profile: CompositorEvidenceProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_compositor_evidence_profile()
    retest_commands = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"active_mode={profile.active_mode}",
            f"pixel_clock_hz={profile.pixel_clock_hz}",
            f"bandwidth_scenario={profile.bandwidth_assumption.scenario}",
            f"required_bandwidth_bytes_per_second={profile.bandwidth_assumption.required_bytes_per_second}",
            f"available_bandwidth_bytes_per_second={profile.bandwidth_assumption.required_bytes_per_second}",
            f"line_buffer_required_cells={profile.line_buffer.required_cells}",
            f"line_buffer_allocated_cells={profile.line_buffer.allocated_cells}",
            "utilization_lut=",
            "utilization_register=",
            "utilization_bram=",
            "timing_slack_ns=",
            "timing_report_bundle=build/fpga/tang_mega_138k/compositor/impl",
            "gowin_report_audit=docs/implementation/evidence/i36_s06_gowin_report_audit.json",
            "external_memory_evidence=docs/implementation/evidence/i29_s05_external_memory_board_evidence.txt",
            "ddr_calibration_dependency=I29-S05 controller_ready and ddr_calibration_evidence must be archived",
            "underflow_counter_one_plane=0",
            "underflow_counter_overlay=0",
            "underflow_counter_error=1",
            f"compositor_demo_result={COMPOSITOR_DEMO_PASS}",
            f"archive_result={profile.required_result}",
            "reduced_mode_fallback=none",
            "residual_blockers=none",
            "filed_issues=none",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_compositor_evidence(text: str) -> CompositorEvidenceRecord:
    fields: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} is not key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {line_number} has an empty key")
        fields[key] = value.strip()
    return CompositorEvidenceRecord(fields)


def audit_compositor_evidence(
    record: CompositorEvidenceRecord,
    *,
    evidence_path: str = "<inline>",
    profile: CompositorEvidenceProfile | None = None,
) -> CompositorEvidenceAudit:
    if profile is None:
        profile = fpga_compositor_evidence_profile()

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I36-S06")
    if record.value("active_mode") and record.value("active_mode") != profile.active_mode:
        missing_fields.append("active_mode_must_match_compositor_profile")

    link_issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence")
    if record.value("gowin_report_audit") and not _mentions_story_or_tool(
        record.value("gowin_report_audit"),
        "i36_s06",
        "i28_s03",
        "gowin_report",
        "fpga_gowin_reports",
    ):
        link_issues.append("gowin_report_audit must reference I28-S03 parser evidence")
    if record.value("external_memory_evidence") and not _mentions_story_or_tool(
        record.value("external_memory_evidence"),
        "i29_s05",
        "external_memory",
        "fpga_external_memory_evidence",
    ):
        link_issues.append("external_memory_evidence must reference I29-S05 evidence")

    metric_issues: list[str] = []
    pixel_clock = _parse_int(record.value("pixel_clock_hz"))
    if pixel_clock is not None and pixel_clock != profile.pixel_clock_hz:
        metric_issues.append("pixel_clock_hz must match the 74.25 MHz video timing profile")
    required_bandwidth = _parse_int(record.value("required_bandwidth_bytes_per_second"))
    available_bandwidth = _parse_int(record.value("available_bandwidth_bytes_per_second"))
    if required_bandwidth is not None and required_bandwidth != (
        profile.bandwidth_assumption.required_bytes_per_second
    ):
        metric_issues.append("required_bandwidth_bytes_per_second must match the two-plane XRGB8888 assumption")
    if available_bandwidth is not None and required_bandwidth is not None and available_bandwidth < required_bandwidth:
        if _is_empty_disposition(record.value("reduced_mode_fallback")):
            metric_issues.append("available bandwidth below requirement must name a reduced-mode fallback")

    if record.value("bandwidth_scenario") and record.value("bandwidth_scenario") != (
        profile.bandwidth_assumption.scenario
    ):
        metric_issues.append("bandwidth_scenario must be two_plane_xrgb8888")
    if _parse_int(record.value("line_buffer_required_cells")) not in (None, profile.line_buffer.required_cells):
        metric_issues.append("line_buffer_required_cells must match the framebuffer policy")
    allocated = _parse_int(record.value("line_buffer_allocated_cells"))
    if allocated is not None and allocated < profile.line_buffer.required_cells:
        metric_issues.append("line_buffer_allocated_cells must cover the required line-buffer depth")
    for field in ("utilization_lut", "utilization_register", "utilization_bram"):
        value = _parse_int(record.value(field))
        if value is not None and value < 0:
            metric_issues.append(f"{field} must be nonnegative")
    timing_slack = _parse_float(record.value("timing_slack_ns"))
    if timing_slack is not None and timing_slack < 0.0:
        metric_issues.append("timing_slack_ns must be nonnegative for an archive pass")
    if "controller_ready" not in record.value("ddr_calibration_dependency"):
        metric_issues.append("ddr_calibration_dependency must mention controller_ready")

    one_underflow = _parse_int(record.value("underflow_counter_one_plane"))
    overlay_underflow = _parse_int(record.value("underflow_counter_overlay"))
    error_underflow = _parse_int(record.value("underflow_counter_error"))
    if one_underflow not in (None, 0):
        metric_issues.append("underflow_counter_one_plane must be zero")
    if overlay_underflow not in (None, 0):
        metric_issues.append("underflow_counter_overlay must be zero")
    if error_underflow is not None and error_underflow <= 0:
        metric_issues.append("underflow_counter_error must be nonzero")

    blocker_issues: list[str] = []
    if record.value("compositor_demo_result") != COMPOSITOR_DEMO_PASS:
        blocker_issues.append("compositor_demo_result must be compositor_demo_pass")
    if record.value("archive_result") != profile.required_result:
        blocker_issues.append("archive_result must be compositor_evidence_archived")
    retest_commands = record.value("retest_commands")
    for command in profile.retest_commands:
        if retest_commands and command not in retest_commands:
            blocker_issues.append(f"retest_commands must include {command}")
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    if residual_blockers and not _is_empty_disposition(residual_blockers):
        if _is_empty_disposition(filed_issues):
            blocker_issues.append("residual blockers must have filed_issues")
        if _is_empty_disposition(retest_commands):
            blocker_issues.append("residual blockers must have retest_commands")

    if missing_fields:
        return CompositorEvidenceAudit(
            status=ARCHIVE_INVALID,
            message="Compositor evidence archive is incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            metric_issues=tuple(metric_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required archive fields", "rerun the I36-S06 audit"),
        )
    if link_issues:
        return CompositorEvidenceAudit(
            status=ARCHIVE_INVALID,
            message="Compositor evidence archive links are incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=tuple(link_issues),
            metric_issues=tuple(metric_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete evidence links", "rerun the I36-S06 audit"),
        )
    if metric_issues or blocker_issues:
        return CompositorEvidenceAudit(
            status=ARCHIVE_NEEDS_FOLLOWUP,
            message="Compositor evidence exists but metrics or blocker disposition need follow-up.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=(),
            metric_issues=tuple(metric_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix timing, bandwidth, line-buffer, or underflow metrics", "file or close residual blockers"),
        )
    return CompositorEvidenceAudit(
        status=ARCHIVE_ARCHIVED,
        message="Compositor timing, bandwidth, resource, and underflow evidence archive is complete.",
        evidence_path=evidence_path,
        missing_fields=(),
        link_issues=(),
        metric_issues=(),
        blocker_issues=(),
        actions=("archive can be handed to I36-S07 board compositor demo evidence",),
    )


def load_compositor_evidence_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> CompositorEvidenceAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_evidence_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return CompositorEvidenceAudit(
            status=ARCHIVE_BLOCKED,
            message="No compositor evidence archive has been captured yet.",
            evidence_path=relative_path.as_posix(),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            metric_issues=(),
            blocker_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link Gowin timing/utilization reports and I29-S05 external-memory evidence",
                "record underflow counters and reduced-mode fallback disposition",
            ),
        )
    try:
        record = parse_compositor_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return CompositorEvidenceAudit(
            status=ARCHIVE_INVALID,
            message="Compositor evidence archive could not be parsed.",
            evidence_path=relative_path.as_posix(),
            missing_fields=(str(exc),),
            link_issues=(),
            metric_issues=(),
            blocker_issues=(),
            actions=("fix the key=value archive record", "rerun the I36-S06 audit"),
        )
    return audit_compositor_evidence(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_compositor_evidence_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_compositor_evidence_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def compositor_evidence_audit_json(*, indent: int = 2) -> str:
    return json.dumps(
        load_compositor_evidence_audit().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_compositor_evidence(
    profile: CompositorEvidenceProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_compositor_evidence_profile()
    lines = [
        "# FPGA Compositor Evidence Archive",
        "",
        f"Story: {profile.story}",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Required result: `{profile.required_result}`",
        f"Active mode: `{profile.active_mode}`",
        f"Pixel clock: `{profile.pixel_clock_hz}`",
        f"Required bandwidth: `{profile.bandwidth_assumption.required_bytes_per_second}` bytes/s",
        f"Line buffer: `{profile.line_buffer.required_cells}` required / `{profile.line_buffer.allocated_cells}` allocated cells",
        "",
        "## Gates",
        "",
        f"- `{profile.compositor_demo_gate}`",
        f"- `{profile.gowin_report_gate}`",
        f"- `{profile.external_memory_evidence_gate}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_compositor_evidence(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_evidence_profile()
    issues: list[str] = []

    if profile.story != FPGA_COMPOSITOR_EVIDENCE_STORY:
        issues.append(f"compositor evidence story must be {FPGA_COMPOSITOR_EVIDENCE_STORY}")
    if profile.required_result != FPGA_COMPOSITOR_EVIDENCE_RESULT:
        issues.append("compositor evidence required result must be compositor_evidence_archived")
    if profile.compositor_demo_gate != fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL:
        issues.append("compositor evidence must depend on I36-S05 demos")
    if profile.gowin_report_gate != fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL:
        issues.append("compositor evidence must depend on I28-S03 Gowin reports")
    if profile.external_memory_evidence_gate != fpga_external_memory_evidence.FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL:
        issues.append("compositor evidence must depend on I29-S05 external-memory evidence")
    if profile.video_timing_gate != fpga_video_timing.FPGA_VIDEO_TIMING_TOOL:
        issues.append("compositor evidence must record the video timing gate")

    issues.extend(fpga_compositor_demo.validate_fpga_compositor_demo(root))
    issues.extend(fpga_gowin_reports.validate_fpga_gowin_reports(root))
    issues.extend(fpga_external_memory_evidence.validate_fpga_external_memory_evidence(root))

    if profile.pixel_clock_hz != 74_250_000:
        issues.append("compositor evidence pixel clock must be 74.25 MHz")
    if profile.bandwidth_assumption.required_bytes_per_second != 594_000_000:
        issues.append("two-plane XRGB8888 bandwidth must be 594,000,000 bytes/s")
    if profile.bandwidth_assumption.required_cells_per_second != 99_000_000:
        issues.append("two-plane XRGB8888 bandwidth must be 99,000,000 48-bit cells/s")
    if profile.line_buffer.allocated_cells < profile.line_buffer.required_cells:
        issues.append("line-buffer allocation must cover required cells")
    if profile.line_buffer.underflow_counter != "VIDEO_UNDERFLOW_COUNT":
        issues.append("compositor evidence must record VIDEO_UNDERFLOW_COUNT")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "active_mode",
        "pixel_clock_hz",
        "bandwidth_scenario",
        "required_bandwidth_bytes_per_second",
        "available_bandwidth_bytes_per_second",
        "line_buffer_required_cells",
        "line_buffer_allocated_cells",
        "utilization_lut",
        "utilization_register",
        "utilization_bram",
        "timing_slack_ns",
        "timing_report_bundle",
        "gowin_report_audit",
        "external_memory_evidence",
        "ddr_calibration_dependency",
        "underflow_counter_one_plane",
        "underflow_counter_overlay",
        "underflow_counter_error",
        "compositor_demo_result",
        "archive_result",
        "reduced_mode_fallback",
        "residual_blockers",
        "filed_issues",
        "retest_commands",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing compositor evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    for link in profile.link_fields:
        if link not in fields:
            issues.append(f"compositor evidence link field {link} must also be required")

    run = fpga_compositor_demo.run_compositor_demo()
    if not run.passed:
        issues.append("I36-S05 compositor demos must pass before evidence archive")
    underflow_by_phase = {
        f"{observation.case_id}:{observation.phase_id}": observation.underflow
        for observation in run.observations
    }
    if underflow_by_phase.get("one_plane_fill:one_plane") is not False:
        issues.append("one-plane demo must have no underflow before archive")
    if underflow_by_phase.get("overlay_swap:overlay") is not False:
        issues.append("overlay demo must have no underflow before archive")
    if underflow_by_phase.get("error_path_underflow:bad_base") is not True:
        issues.append("error-path demo must have deterministic underflow before archive")

    good_record = parse_compositor_evidence(
        compositor_evidence_template()
        .replace("archived_at=", "archived_at=2026-05-13T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("utilization_lut=", "utilization_lut=1234")
        .replace("utilization_register=", "utilization_register=5678")
        .replace("utilization_bram=", "utilization_bram=12")
        .replace("timing_slack_ns=", "timing_slack_ns=1.25")
    )
    if not audit_compositor_evidence(good_record).passed:
        issues.append("complete compositor evidence archive must audit as archived")

    followup_record = parse_compositor_evidence(
        compositor_evidence_template()
        .replace("archived_at=", "archived_at=2026-05-13T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("utilization_lut=", "utilization_lut=1234")
        .replace("utilization_register=", "utilization_register=5678")
        .replace("utilization_bram=", "utilization_bram=12")
        .replace("timing_slack_ns=", "timing_slack_ns=1.25")
        .replace(
            "available_bandwidth_bytes_per_second=594000000",
            "available_bandwidth_bytes_per_second=148500000",
        )
    )
    if audit_compositor_evidence(followup_record).status != ARCHIVE_NEEDS_FOLLOWUP:
        issues.append("insufficient bandwidth without fallback must require follow-up")

    default_audit = load_compositor_evidence_audit(root)
    if default_audit.status != ARCHIVE_BLOCKED:
        issues.append("default compositor evidence audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_EVIDENCE_DOC)
    for token in (
        "Story: I36-S06",
        FPGA_COMPOSITOR_EVIDENCE_TOOL,
        FPGA_COMPOSITOR_EVIDENCE_PATH.as_posix(),
        fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        fpga_external_memory_evidence.FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL,
        "74.25 MHz",
        "594,000,000 bytes/s",
        "99,000,000 48-bit cells/s",
        "line-buffer depth",
        "utilization_lut",
        "timing_slack_ns",
        "VIDEO_UNDERFLOW_COUNT",
        "DDR calibration",
        "reduced_mode_fallback",
        "blocked",
        "I36-S07",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_EVIDENCE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(load_compositor_evidence_audit(root).as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor evidence objects are not JSON serializable: {exc}")

    return tuple(issues)


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _parse_int(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _mentions_story_or_tool(value: str, *tokens: str) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in tokens)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

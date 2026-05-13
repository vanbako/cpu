"""FPGA first board compositor demo evidence archive.

Owner stories:
- I36-S07: capture first board compositor demo evidence or blocker disposition.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_compositor_demo,
    fpga_compositor_evidence,
    fpga_first_test,
    fpga_video_board_scanout,
)


JsonValue = Any

FPGA_COMPOSITOR_BOARD_STORY = "I36-S07"
FPGA_COMPOSITOR_BOARD_DOC = Path("docs/implementation/fpga-compositor-board-demo.md")
FPGA_COMPOSITOR_BOARD_TOOL = "python tools\\fpga_compositor_board.py --check"
FPGA_COMPOSITOR_BOARD_EVIDENCE = Path(
    "docs/implementation/evidence/i36_s07_compositor_board_demo.txt"
)
FPGA_COMPOSITOR_BOARD_STATUS = "blocked_until_board_demo_pass_or_classified_blocker"

ARCHIVED = "archived"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_FOLLOWUP = "needs_followup"

BOARD_RESULT_PASS = "compositor_board_pass"
BOARD_RESULT_FAILURE = "failure_observed"
ARCHIVE_RESULT_PASS = "compositor_board_pass_archived"
ARCHIVE_RESULT_BLOCKER = "compositor_board_blocker_archived"
CLASS_NONE = "none"
CLASSIFIED_BLOCKER_CLASSES = (
    "scanout_precondition",
    "compositor_timing",
    "framebuffer_image",
    "firmware_command",
    "vblank_descriptor",
    "underflow_status",
    "visible_output",
    "probe_capture",
    "memory_bandwidth",
    "board_integration",
)


@dataclass(frozen=True)
class CompositorBoardField:
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
class CompositorBoardResultRule:
    archive_result: str
    pass_fail_result: str
    evidence_requirement: str
    blocker_requirement: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_result": self.archive_result,
            "pass_fail_result": self.pass_fail_result,
            "evidence_requirement": self.evidence_requirement,
            "blocker_requirement": self.blocker_requirement,
        }


@dataclass(frozen=True)
class CompositorBoardProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    compositor_evidence_gate: str
    video_board_scanout_gate: str
    compositor_demo_gate: str
    archive_results: tuple[str, ...]
    blocker_classes: tuple[str, ...]
    required_fields: tuple[CompositorBoardField, ...]
    result_rules: tuple[CompositorBoardResultRule, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> CompositorBoardField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "board": self.board,
            "compositor_evidence_gate": self.compositor_evidence_gate,
            "video_board_scanout_gate": self.video_board_scanout_gate,
            "compositor_demo_gate": self.compositor_demo_gate,
            "archive_results": list(self.archive_results),
            "blocker_classes": list(self.blocker_classes),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "result_rules": [rule.as_dict() for rule in self.result_rules],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class CompositorBoardRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class CompositorBoardAudit:
    status: str
    message: str
    evidence_path: str
    compositor_evidence_status: str
    video_board_scanout_status: str
    archive_result: str
    pass_fail_result: str
    blocker_class: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    result_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == ARCHIVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "compositor_evidence_status": self.compositor_evidence_status,
            "video_board_scanout_status": self.video_board_scanout_status,
            "archive_result": self.archive_result,
            "pass_fail_result": self.pass_fail_result,
            "blocker_class": self.blocker_class,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "result_issues": list(self.result_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_compositor_board_profile() -> CompositorBoardProfile:
    return CompositorBoardProfile(
        story=FPGA_COMPOSITOR_BOARD_STORY,
        status=FPGA_COMPOSITOR_BOARD_STATUS,
        evidence_path=FPGA_COMPOSITOR_BOARD_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        compositor_evidence_gate=fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_TOOL,
        video_board_scanout_gate=fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_TOOL,
        compositor_demo_gate=fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
        archive_results=(ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER),
        blocker_classes=CLASSIFIED_BLOCKER_CLASSES,
        required_fields=(
            CompositorBoardField("story", True, "Must be I36-S07."),
            CompositorBoardField("archived_at", True, "Local archive timestamp."),
            CompositorBoardField("repository_commit", True, "Repository commit used for the board demo."),
            CompositorBoardField("board", True, "Physical board name."),
            CompositorBoardField("video_board_scanout", True, "I35-S06 board scanout archive path."),
            CompositorBoardField("video_board_scanout_status", True, "I35-S06 audit status."),
            CompositorBoardField("compositor_evidence", True, "I36-S06 compositor evidence archive path."),
            CompositorBoardField("compositor_evidence_status", True, "I36-S06 audit status."),
            CompositorBoardField("compositor_demo_gate", True, "I36-S05 demo command or artifact."),
            CompositorBoardField("compositor_demo_status", True, "I36-S05 demo status."),
            CompositorBoardField("bitstream_path", True, "Programmed compositor .fs bitstream path."),
            CompositorBoardField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            CompositorBoardField("framebuffer_image_manifest", True, "Manifest for framebuffer images used by the demo."),
            CompositorBoardField("framebuffer_image_hashes", True, "Hashes for one-plane, overlay, swap, and error-path images."),
            CompositorBoardField("firmware_command_log", True, "Firmware or monitor command transcript."),
            CompositorBoardField("visible_capture", True, "Photo/video of compositor output, or none when probe evidence carries result."),
            CompositorBoardField("probe_capture", True, "ILA/logic/UART probe output, or none when visible capture carries result."),
            CompositorBoardField("vblank_log", True, "Vblank wait and descriptor applied log."),
            CompositorBoardField("underflow_log", True, "Underflow counter/status log for all demo phases."),
            CompositorBoardField("status_log", True, "Decoded status/UART/pass-fail log."),
            CompositorBoardField("replay_or_simulation_commands", True, "Replay or Verilator commands for nearest reproducible case."),
            CompositorBoardField("pass_fail_result", True, "compositor_board_pass or failure_observed."),
            CompositorBoardField("archive_result", True, "compositor_board_pass_archived or compositor_board_blocker_archived."),
            CompositorBoardField("blocker_class", True, "none for pass, otherwise a classified blocker class."),
            CompositorBoardField("blocker_evidence", True, "none for pass, otherwise evidence supporting blocker classification."),
            CompositorBoardField("residual_blockers", True, "none, or named blockers."),
            CompositorBoardField("filed_issues", True, "none, or issue IDs/links for blockers."),
            CompositorBoardField("retest_criteria", True, "Concrete criteria and commands for rerunning board compositor evidence."),
        ),
        result_rules=(
            CompositorBoardResultRule(
                ARCHIVE_RESULT_PASS,
                BOARD_RESULT_PASS,
                "visible_capture or probe_capture must be concrete, with vblank, underflow, status, and framebuffer evidence",
                "blocker_class=none, blocker_evidence=none, residual_blockers=none, and filed_issues=none",
            ),
            CompositorBoardResultRule(
                ARCHIVE_RESULT_BLOCKER,
                BOARD_RESULT_FAILURE,
                "blocker_evidence, blocker_class, status logs, replay/simulation commands, and retest criteria must be concrete",
                "residual_blockers and filed_issues must name the remaining problem",
            ),
        ),
        link_fields=(
            "video_board_scanout",
            "compositor_evidence",
            "compositor_demo_gate",
            "bitstream_path",
            "framebuffer_image_manifest",
            "framebuffer_image_hashes",
            "firmware_command_log",
            "vblank_log",
            "underflow_log",
            "status_log",
            "replay_or_simulation_commands",
        ),
        retest_commands=(
            fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_TOOL,
            fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_TOOL,
            fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
            "python tools\\fpga_compositor_board.py --audit docs\\implementation\\evidence\\i36_s07_compositor_board_demo.txt",
        ),
        blockers=(
            "I36-S06 compositor evidence must be archived before claiming a board compositor pass",
            "I35-S06 video scanout must be archived before compositor board evidence can close",
            "bitstream identity, framebuffer images, firmware commands, visible/probe output, vblank, underflow, and status logs must be linked",
            "a pass archive must include one-plane, overlay, swap, and error-path observations with no residual blockers",
            "a blocker archive must classify the failure, link filed issues, and preserve replay or simulation commands plus retest criteria",
        ),
    )


def compositor_board_template(
    profile: CompositorBoardProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_compositor_board_profile()
    retest_criteria = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"video_board_scanout={fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE.as_posix()}",
            f"video_board_scanout_status={ARCHIVED}",
            f"compositor_evidence={fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_PATH.as_posix()}",
            f"compositor_evidence_status={ARCHIVED}",
            f"compositor_demo_gate={fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL}",
            "compositor_demo_status=passed",
            "bitstream_path=build/fpga/tang_mega_138k/compositor/impl/pnr/compositor_demo.fs",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "framebuffer_image_manifest=docs/implementation/evidence/i36_s07_framebuffer_manifest.json",
            "framebuffer_image_hashes=one_plane=sha256:1111111111111111111111111111111111111111111111111111111111111111,overlay=sha256:2222222222222222222222222222222222222222222222222222222222222222,swap=sha256:3333333333333333333333333333333333333333333333333333333333333333,error=sha256:4444444444444444444444444444444444444444444444444444444444444444",
            "firmware_command_log=docs/implementation/evidence/i36_s07_firmware_commands.log",
            "visible_capture=docs/implementation/evidence/i36_s07_compositor_capture.jpg",
            "probe_capture=none",
            "vblank_log=docs/implementation/evidence/i36_s07_vblank.log",
            "underflow_log=docs/implementation/evidence/i36_s07_underflow.log",
            "status_log=docs/implementation/evidence/i36_s07_status.log",
            "replay_or_simulation_commands=python tools\\fpga_compositor_demo.py --run ; python tools\\fpga_compositor_board.py --audit docs\\implementation\\evidence\\i36_s07_compositor_board_demo.txt",
            f"pass_fail_result={BOARD_RESULT_PASS}",
            f"archive_result={ARCHIVE_RESULT_PASS}",
            f"blocker_class={CLASS_NONE}",
            "blocker_evidence=none",
            "residual_blockers=none",
            "filed_issues=none",
            f"retest_criteria={retest_criteria}",
            "",
        )
    )


def parse_compositor_board(text: str) -> CompositorBoardRecord:
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
    return CompositorBoardRecord(fields)


def audit_compositor_board(
    record: CompositorBoardRecord,
    *,
    compositor_evidence_audit: fpga_compositor_evidence.CompositorEvidenceAudit | None = None,
    video_board_scanout_audit: fpga_video_board_scanout.VideoBoardScanoutAudit | None = None,
    evidence_path: str = "<inline>",
    profile: CompositorBoardProfile | None = None,
) -> CompositorBoardAudit:
    if profile is None:
        profile = fpga_compositor_board_profile()

    compositor_status = (
        compositor_evidence_audit.status
        if compositor_evidence_audit is not None
        else record.value("compositor_evidence_status")
    )
    scanout_status = (
        video_board_scanout_audit.status
        if video_board_scanout_audit is not None
        else record.value("video_board_scanout_status")
    )

    if compositor_evidence_audit is not None and compositor_evidence_audit.status == BLOCKED:
        return _audit(
            BLOCKED,
            "Compositor board demo archive is blocked until I36-S06 evidence is archived.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            actions=("complete I36-S06 compositor evidence archive first",),
        )
    if video_board_scanout_audit is not None and video_board_scanout_audit.status == BLOCKED:
        return _audit(
            BLOCKED,
            "Compositor board demo archive is blocked until I35-S06 scanout evidence is archived.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            actions=("complete I35-S06 video board scanout archive first",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I36-S07")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    link_issues = _link_issues(record, profile)
    result_issues = _result_issues(record, profile, compositor_status, scanout_status)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            INVALID,
            "Compositor board demo archive evidence is incomplete or malformed.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I36-S07 fields", "rerun the board compositor audit"),
        )
    if link_issues:
        return _audit(
            INVALID,
            "Compositor board demo archive links are incomplete or malformed.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete compositor board evidence links",),
        )
    if result_issues:
        return _audit(
            INVALID,
            "Compositor board demo archive result fields are inconsistent.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix pass/blocker result, prerequisite status, or classification consistency",),
        )
    if blocker_issues:
        return _audit(
            NEEDS_FOLLOWUP,
            "Compositor board demo archive needs blocker disposition or retest criteria.",
            evidence_path,
            compositor_status,
            scanout_status,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("file or close blockers", "record concrete compositor retest criteria"),
        )
    return _audit(
        ARCHIVED,
        "First board compositor demo pass or classified blocker is archived.",
        evidence_path,
        compositor_status,
        scanout_status,
        record,
        actions=("archive can be handed to later compositor arbitration and board-retest work",),
    )


def load_compositor_board_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    compositor_evidence_path: Path | None = None,
    video_board_scanout_path: Path | None = None,
) -> CompositorBoardAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_board_profile()
    relative_path = evidence_path or profile.evidence_path
    compositor_audit = fpga_compositor_evidence.load_compositor_evidence_audit(
        root,
        compositor_evidence_path,
    )
    scanout_audit = fpga_video_board_scanout.load_video_board_scanout_audit(
        root,
        video_board_scanout_path,
    )
    path = root / relative_path
    if not path.exists():
        return _audit(
            BLOCKED,
            "No compositor board demo archive has been captured yet.",
            relative_path.as_posix(),
            compositor_audit.status,
            scanout_audit.status,
            CompositorBoardRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link bitstream, framebuffer image, firmware command, visible/probe, vblank, underflow, status, replay, blocker, and retest evidence",
            ),
        )
    try:
        record = parse_compositor_board(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            INVALID,
            "Compositor board demo evidence could not be parsed.",
            relative_path.as_posix(),
            compositor_audit.status,
            scanout_audit.status,
            CompositorBoardRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value archive record", "rerun the I36-S07 audit"),
        )
    return audit_compositor_board(
        record,
        compositor_evidence_audit=compositor_audit,
        video_board_scanout_audit=scanout_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_compositor_board_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_compositor_board_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_compositor_board(
    profile: CompositorBoardProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_compositor_board_profile()
    lines = [
        "# FPGA Compositor Board Demo",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        "",
        "## Gates",
        "",
        f"- `{profile.compositor_evidence_gate}`",
        f"- `{profile.video_board_scanout_gate}`",
        f"- `{profile.compositor_demo_gate}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |")
    lines.extend(["", "## Result Rules", ""])
    for rule in profile.result_rules:
        lines.append(f"- `{rule.archive_result}`: {rule.pass_fail_result}; {rule.evidence_requirement}.")
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_compositor_board(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_board_profile()
    issues: list[str] = []

    if profile.story != FPGA_COMPOSITOR_BOARD_STORY:
        issues.append(f"compositor board story must be {FPGA_COMPOSITOR_BOARD_STORY}")
    if profile.status != FPGA_COMPOSITOR_BOARD_STATUS:
        issues.append("compositor board status must stay blocked until pass or classified blocker evidence exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("compositor board target must match the FPGA first-test board")
    if profile.compositor_evidence_gate != fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_TOOL:
        issues.append("compositor board evidence must depend on I36-S06")
    if profile.video_board_scanout_gate != fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_TOOL:
        issues.append("compositor board evidence must depend on I35-S06")
    if profile.compositor_demo_gate != fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL:
        issues.append("compositor board evidence must depend on I36-S05")

    issues.extend(fpga_compositor_evidence.validate_fpga_compositor_evidence(root))
    issues.extend(fpga_video_board_scanout.validate_fpga_video_board_scanout(root))
    issues.extend(fpga_compositor_demo.validate_fpga_compositor_demo(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "board",
        "video_board_scanout",
        "video_board_scanout_status",
        "compositor_evidence",
        "compositor_evidence_status",
        "compositor_demo_gate",
        "compositor_demo_status",
        "bitstream_path",
        "bitstream_sha256",
        "framebuffer_image_manifest",
        "framebuffer_image_hashes",
        "firmware_command_log",
        "visible_capture",
        "probe_capture",
        "vblank_log",
        "underflow_log",
        "status_log",
        "replay_or_simulation_commands",
        "pass_fail_result",
        "archive_result",
        "blocker_class",
        "blocker_evidence",
        "residual_blockers",
        "filed_issues",
        "retest_criteria",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing compositor board field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for archive_result in (ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER):
        if archive_result not in profile.archive_results:
            issues.append(f"missing compositor board archive result {archive_result}")
    for blocker_class in CLASSIFIED_BLOCKER_CLASSES:
        if blocker_class not in profile.blocker_classes:
            issues.append(f"missing compositor board blocker class {blocker_class}")

    pass_record = parse_compositor_board(
        compositor_board_template()
        .replace("archived_at=", "archived_at=2026-05-13T10:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_compositor_board(
        pass_record,
        compositor_evidence_audit=_compositor_evidence(ARCHIVED),
        video_board_scanout_audit=_video_board_scanout(ARCHIVED),
    ).passed:
        issues.append("complete compositor board pass record must audit as archived")

    blocker_record = parse_compositor_board(_blocker_archive_text())
    if not audit_compositor_board(
        blocker_record,
        compositor_evidence_audit=_compositor_evidence(ARCHIVED),
        video_board_scanout_audit=_video_board_scanout(ARCHIVED),
    ).passed:
        issues.append("complete compositor board blocker record must audit as archived")

    missing_issue = parse_compositor_board(
        _blocker_archive_text().replace("filed_issues=CPU-360", "filed_issues=none")
    )
    if audit_compositor_board(missing_issue).status != NEEDS_FOLLOWUP:
        issues.append("compositor board blocker archive without filed issues must require follow-up")

    default_audit = load_compositor_board_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default compositor board audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_BOARD_DOC)
    for token in (
        "Story: I36-S07",
        FPGA_COMPOSITOR_BOARD_TOOL,
        FPGA_COMPOSITOR_BOARD_EVIDENCE.as_posix(),
        fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_TOOL,
        fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_TOOL,
        fpga_compositor_demo.FPGA_COMPOSITOR_DEMO_TOOL,
        "bitstream_sha256",
        "framebuffer_image_manifest",
        "framebuffer_image_hashes",
        "firmware_command_log",
        "visible_capture",
        "probe_capture",
        "vblank_log",
        "underflow_log",
        "status_log",
        "replay_or_simulation_commands",
        ARCHIVE_RESULT_PASS,
        ARCHIVE_RESULT_BLOCKER,
        "blocker_class",
        "memory_bandwidth",
        "residual_blockers",
        "filed_issues",
        "retest_criteria",
        "I36-S08",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_BOARD_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor board objects are not JSON serializable: {exc}")

    return tuple(issues)


def _link_issues(record: CompositorBoardRecord, profile: CompositorBoardProfile) -> list[str]:
    issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            issues.append(f"{field} must link concrete evidence")
    if record.value("video_board_scanout") and "i35_s06" not in record.value("video_board_scanout").lower():
        issues.append("video_board_scanout must reference I35-S06 evidence")
    if record.value("compositor_evidence") and "i36_s06" not in record.value("compositor_evidence").lower():
        issues.append("compositor_evidence must reference I36-S06 evidence")
    demo_gate = record.value("compositor_demo_gate").lower()
    if demo_gate and "fpga_compositor_demo.py" not in demo_gate and "i36_s05" not in demo_gate:
        issues.append("compositor_demo_gate must reference I36-S05")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        issues.append("bitstream_path must name a .fs file")
    if record.value("bitstream_sha256") and not _is_sha256_hex(record.value("bitstream_sha256")):
        issues.append("bitstream_sha256 must be a 64-character hex digest")
    hashes = record.value("framebuffer_image_hashes")
    for token in ("one_plane", "overlay", "swap", "error"):
        if hashes and token not in hashes:
            issues.append(f"framebuffer_image_hashes must include {token}")
    for field in ("framebuffer_image_manifest", "firmware_command_log", "vblank_log", "underflow_log", "status_log"):
        if record.value(field) and "i36_s07" not in record.value(field).lower():
            issues.append(f"{field} must reference I36-S07 evidence")
    replay = record.value("replay_or_simulation_commands").lower()
    if replay and "fpga_compositor_demo.py --run" not in replay:
        issues.append("replay_or_simulation_commands must include the compositor demo replay")
    return issues


def _result_issues(
    record: CompositorBoardRecord,
    profile: CompositorBoardProfile,
    compositor_status: str,
    scanout_status: str,
) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    pass_fail_result = record.value("pass_fail_result")
    if compositor_status and compositor_status != ARCHIVED:
        issues.append("compositor_evidence_status must be archived")
    if scanout_status and scanout_status != ARCHIVED:
        issues.append("video_board_scanout_status must be archived")
    if record.value("compositor_demo_status") and record.value("compositor_demo_status") != "passed":
        issues.append("compositor_demo_status must be passed")
    if archive_result not in profile.archive_results:
        issues.append("archive_result must be compositor_board_pass_archived or compositor_board_blocker_archived")
    if pass_fail_result not in {BOARD_RESULT_PASS, BOARD_RESULT_FAILURE}:
        issues.append("pass_fail_result must be compositor_board_pass or failure_observed")

    if archive_result == ARCHIVE_RESULT_PASS:
        if pass_fail_result != BOARD_RESULT_PASS:
            issues.append("compositor_board_pass_archived requires pass_fail_result=compositor_board_pass")
        if record.value("blocker_class") != CLASS_NONE:
            issues.append("compositor_board_pass_archived requires blocker_class=none")
        if not _is_empty_disposition(record.value("blocker_evidence")):
            issues.append("compositor_board_pass_archived requires blocker_evidence=none")
        if _is_empty_disposition(record.value("visible_capture")) and _is_empty_disposition(record.value("probe_capture")):
            issues.append("compositor_board_pass_archived requires visible_capture or probe_capture")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if pass_fail_result != BOARD_RESULT_FAILURE:
            issues.append("compositor_board_blocker_archived requires pass_fail_result=failure_observed")
        if record.value("blocker_class") not in CLASSIFIED_BLOCKER_CLASSES:
            issues.append("compositor_board_blocker_archived requires a classified blocker_class")
        if _is_empty_disposition(record.value("blocker_evidence")):
            issues.append("compositor_board_blocker_archived requires blocker_evidence")
    return issues


def _blocker_issues(record: CompositorBoardRecord) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_criteria = record.value("retest_criteria")
    if _is_empty_disposition(retest_criteria):
        issues.append("retest_criteria must be concrete")
    if archive_result == ARCHIVE_RESULT_PASS:
        if not _is_empty_disposition(residual_blockers):
            issues.append("compositor_board_pass_archived requires residual_blockers=none")
        if not _is_empty_disposition(filed_issues):
            issues.append("compositor_board_pass_archived requires filed_issues=none")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if _is_empty_disposition(residual_blockers):
            issues.append("compositor_board_blocker_archived requires residual_blockers")
        if _is_empty_disposition(filed_issues):
            issues.append("compositor_board_blocker_archived requires filed_issues")
    return issues


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    compositor_status: str,
    scanout_status: str,
    record: CompositorBoardRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    result_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> CompositorBoardAudit:
    return CompositorBoardAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        compositor_evidence_status=compositor_status,
        video_board_scanout_status=scanout_status,
        archive_result=record.value("archive_result"),
        pass_fail_result=record.value("pass_fail_result"),
        blocker_class=record.value("blocker_class"),
        missing_fields=missing_fields,
        link_issues=link_issues,
        result_issues=result_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _blocker_archive_text() -> str:
    return (
        compositor_board_template()
        .replace("archived_at=", "archived_at=2026-05-13T10:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("visible_capture=docs/implementation/evidence/i36_s07_compositor_capture.jpg", "visible_capture=none")
        .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i36_s07_probe_capture.vcd")
        .replace("pass_fail_result=compositor_board_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=compositor_board_pass_archived", "archive_result=compositor_board_blocker_archived")
        .replace("blocker_class=none", "blocker_class=memory_bandwidth")
        .replace("blocker_evidence=none", "blocker_evidence=docs/implementation/evidence/i36_s07_bandwidth_blocker.txt")
        .replace("residual_blockers=none", "residual_blockers=compositor_ddr_bandwidth_shortfall")
        .replace("filed_issues=none", "filed_issues=CPU-360")
    )


def _compositor_evidence(status: str) -> fpga_compositor_evidence.CompositorEvidenceAudit:
    return fpga_compositor_evidence.CompositorEvidenceAudit(
        status=status,
        message=status,
        evidence_path=fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_PATH.as_posix(),
        missing_fields=(),
        link_issues=(),
        metric_issues=(),
        blocker_issues=(),
        actions=(),
    )


def _video_board_scanout(status: str) -> fpga_video_board_scanout.VideoBoardScanoutAudit:
    return fpga_video_board_scanout.VideoBoardScanoutAudit(
        status=status,
        message=status,
        evidence_path=fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE.as_posix(),
        scanout_gate_status="passed",
        first_pass_archive_status=ARCHIVED,
        archive_result=fpga_video_board_scanout.ARCHIVE_RESULT_PASS,
        pass_fail_result=fpga_video_board_scanout.BOARD_RESULT_PASS,
        blocker_class=CLASS_NONE,
        missing_fields=(),
        link_issues=(),
        result_issues=(),
        blocker_issues=(),
        actions=(),
    )


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {
        "",
        "none",
        "n/a",
        "na",
        "-",
        "blocked",
        "missing",
        "not_applicable",
        "not_required",
    }


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""FPGA first board video scanout evidence archive.

Owner stories:
- I35-S06: capture first board scanout evidence or a classified blocker.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_pass_archive, fpga_first_test, fpga_video_scanout_gate


JsonValue = Any

FPGA_VIDEO_BOARD_SCANOUT_STORY = "I35-S06"
FPGA_VIDEO_BOARD_SCANOUT_DOC = Path("docs/implementation/fpga-video-board-scanout.md")
FPGA_VIDEO_BOARD_SCANOUT_TOOL = "python tools\\fpga_video_board_scanout.py --check"
FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE = Path(
    "docs/implementation/evidence/i35_s06_video_board_scanout.txt"
)
VIDEO_BOARD_SCANOUT_STATUS = "blocked_until_board_scanout_pass_or_classified_blocker"

ARCHIVED = "archived"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_FOLLOWUP = "needs_followup"

BOARD_RESULT_PASS = "scanout_pass"
BOARD_RESULT_FAILURE = "failure_observed"
ARCHIVE_RESULT_PASS = "board_scanout_pass_archived"
ARCHIVE_RESULT_BLOCKER = "board_scanout_blocker_archived"
CLASS_NONE = "none"
CLASSIFIED_BLOCKER_CLASSES = (
    "display_adapter",
    "pixel_clock",
    "timing",
    "scanout_mmio",
    "vblank_irq",
    "bitstream",
    "board_integration",
)


@dataclass(frozen=True)
class VideoBoardScanoutField:
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
class VideoBoardScanoutResultRule:
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
class VideoBoardScanoutProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    scanout_gate: str
    first_pass_archive_gate: str
    archive_results: tuple[str, ...]
    blocker_classes: tuple[str, ...]
    required_fields: tuple[VideoBoardScanoutField, ...]
    result_rules: tuple[VideoBoardScanoutResultRule, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> VideoBoardScanoutField:
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
            "scanout_gate": self.scanout_gate,
            "first_pass_archive_gate": self.first_pass_archive_gate,
            "archive_results": list(self.archive_results),
            "blocker_classes": list(self.blocker_classes),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "result_rules": [rule.as_dict() for rule in self.result_rules],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class VideoBoardScanoutRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class VideoBoardScanoutAudit:
    status: str
    message: str
    evidence_path: str
    scanout_gate_status: str
    first_pass_archive_status: str
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
            "scanout_gate_status": self.scanout_gate_status,
            "first_pass_archive_status": self.first_pass_archive_status,
            "archive_result": self.archive_result,
            "pass_fail_result": self.pass_fail_result,
            "blocker_class": self.blocker_class,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "result_issues": list(self.result_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_video_board_scanout_profile() -> VideoBoardScanoutProfile:
    return VideoBoardScanoutProfile(
        story=FPGA_VIDEO_BOARD_SCANOUT_STORY,
        status=VIDEO_BOARD_SCANOUT_STATUS,
        evidence_path=FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        scanout_gate=fpga_video_scanout_gate.FPGA_VIDEO_SCANOUT_GATE_TOOL,
        first_pass_archive_gate=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        archive_results=(ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER),
        blocker_classes=CLASSIFIED_BLOCKER_CLASSES,
        required_fields=(
            VideoBoardScanoutField("story", True, "Must be I35-S06."),
            VideoBoardScanoutField("archived_at", True, "Local archive timestamp."),
            VideoBoardScanoutField("repository_commit", True, "Repository commit used for the board run."),
            VideoBoardScanoutField("board", True, "Physical board name."),
            VideoBoardScanoutField("first_pass_archive", True, "I31-S05 first CPU pass or blocker archive path."),
            VideoBoardScanoutField("first_pass_archive_status", True, "I31-S05 audit status."),
            VideoBoardScanoutField("scanout_gate", True, "I35-S05 scanout gate command or artifact."),
            VideoBoardScanoutField("scanout_gate_status", True, "I35-S05 gate status."),
            VideoBoardScanoutField("gowin_report_bundle", True, "Gowin report bundle used for the displayed bitstream."),
            VideoBoardScanoutField("bitstream_path", True, "Programmed .fs bitstream path."),
            VideoBoardScanoutField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            VideoBoardScanoutField("display_adapter_wiring", True, "Display/output adapter wiring note or photo."),
            VideoBoardScanoutField("pixel_clock_evidence", True, "Pixel-clock measurement, report, or probe capture."),
            VideoBoardScanoutField("timing_evidence", True, "720p timing report, scope capture, or probe decode."),
            VideoBoardScanoutField("visible_test_pattern_capture", True, "Photo/video of test pattern, or none when probe evidence carries the result."),
            VideoBoardScanoutField("probe_capture", True, "Probe/ILA/logic capture, or none when visible capture carries the result."),
            VideoBoardScanoutField("video_mmio_register_log", True, "Firmware/monitor log of video register programming."),
            VideoBoardScanoutField("vblank_status_observation", True, "Vblank IRQ/status observation or blocker-specific not-reached evidence."),
            VideoBoardScanoutField("decoded_status_packet", True, "Decoded UART/status packet or transcript."),
            VideoBoardScanoutField("pass_fail_result", True, "scanout_pass or failure_observed."),
            VideoBoardScanoutField("archive_result", True, "board_scanout_pass_archived or board_scanout_blocker_archived."),
            VideoBoardScanoutField("blocker_class", True, "none for pass, otherwise a classified blocker class."),
            VideoBoardScanoutField("blocker_evidence", True, "none for pass, otherwise evidence supporting blocker classification."),
            VideoBoardScanoutField("residual_blockers", True, "none, or named blockers."),
            VideoBoardScanoutField("filed_issues", True, "none, or issue IDs/links for blockers."),
            VideoBoardScanoutField("retest_steps", True, "Concrete commands or steps for rerunning scanout evidence."),
        ),
        result_rules=(
            VideoBoardScanoutResultRule(
                ARCHIVE_RESULT_PASS,
                BOARD_RESULT_PASS,
                "visible_test_pattern_capture or probe_capture must be concrete, with vblank/status observations",
                "blocker_class=none, blocker_evidence=none, residual_blockers=none, and filed_issues=none",
            ),
            VideoBoardScanoutResultRule(
                ARCHIVE_RESULT_BLOCKER,
                BOARD_RESULT_FAILURE,
                "blocker_evidence, blocker_class, vblank/status disposition, and retest steps must be concrete",
                "residual_blockers and filed_issues must name the remaining problem",
            ),
        ),
        link_fields=(
            "first_pass_archive",
            "scanout_gate",
            "gowin_report_bundle",
            "bitstream_path",
            "display_adapter_wiring",
            "pixel_clock_evidence",
            "timing_evidence",
            "video_mmio_register_log",
            "vblank_status_observation",
            "decoded_status_packet",
        ),
        retest_commands=(
            fpga_video_scanout_gate.FPGA_VIDEO_SCANOUT_GATE_TOOL,
            fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
            "python tools\\fpga_video_board_scanout.py --audit docs\\implementation\\evidence\\i35_s06_video_board_scanout.txt",
        ),
        blockers=(
            "I35-S05 scanout simulation/report gate must pass before board scanout evidence can close",
            "I31-S05 first-pass archive status must be archived before the board scanout archive can close",
            "bitstream identity, display/output wiring, pixel-clock/timing evidence, and vblank/status observations must be linked",
            "a pass archive must have a visible test pattern or probe capture and no residual blockers",
            "a blocker archive must classify the failure and link filed issues plus retest steps",
        ),
    )


def video_board_scanout_template(
    profile: VideoBoardScanoutProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_video_board_scanout_profile()
    retest_steps = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"first_pass_archive={fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix()}",
            f"first_pass_archive_status={ARCHIVED}",
            f"scanout_gate={fpga_video_scanout_gate.FPGA_VIDEO_SCANOUT_GATE_TOOL}",
            "scanout_gate_status=passed",
            "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
            "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first_video.fs",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "display_adapter_wiring=docs/implementation/evidence/i35_s06_display_adapter_wiring.txt",
            "pixel_clock_evidence=docs/implementation/evidence/i35_s06_pixel_clock_scope.png",
            "timing_evidence=docs/implementation/evidence/i35_s06_720p_timing_decode.txt",
            "visible_test_pattern_capture=docs/implementation/evidence/i35_s06_test_pattern.jpg",
            "probe_capture=none",
            "video_mmio_register_log=docs/implementation/evidence/i35_s06_video_mmio.log",
            "vblank_status_observation=docs/implementation/evidence/i35_s06_vblank_status.txt",
            "decoded_status_packet=docs/implementation/evidence/i35_s06_status_packet.json",
            f"pass_fail_result={BOARD_RESULT_PASS}",
            f"archive_result={ARCHIVE_RESULT_PASS}",
            f"blocker_class={CLASS_NONE}",
            "blocker_evidence=none",
            "residual_blockers=none",
            "filed_issues=none",
            f"retest_steps={retest_steps}",
            "",
        )
    )


def parse_video_board_scanout(text: str) -> VideoBoardScanoutRecord:
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
    return VideoBoardScanoutRecord(fields)


def audit_video_board_scanout(
    record: VideoBoardScanoutRecord,
    *,
    first_pass_archive_audit: fpga_first_pass_archive.FirstPassArchiveAudit | None = None,
    evidence_path: str = "<inline>",
    profile: VideoBoardScanoutProfile | None = None,
) -> VideoBoardScanoutAudit:
    if profile is None:
        profile = fpga_video_board_scanout_profile()

    first_pass_status = (
        first_pass_archive_audit.status
        if first_pass_archive_audit is not None
        else record.value("first_pass_archive_status")
    )
    scanout_gate_status = record.value("scanout_gate_status")

    if first_pass_archive_audit is not None and first_pass_archive_audit.status == BLOCKED:
        return _audit(
            BLOCKED,
            "Video board scanout archive is blocked until I31-S05 evidence is archived.",
            evidence_path,
            scanout_gate_status,
            first_pass_status,
            record,
            actions=("complete I31-S05 first-pass archive evidence first",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I35-S06")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    link_issues = _link_issues(record, profile)
    result_issues = _result_issues(record, profile, first_pass_status)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            INVALID,
            "Video board scanout archive evidence is incomplete or malformed.",
            evidence_path,
            scanout_gate_status,
            first_pass_status,
            record,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I35-S06 fields", "rerun the archive audit"),
        )
    if link_issues:
        return _audit(
            INVALID,
            "Video board scanout archive links are incomplete or malformed.",
            evidence_path,
            scanout_gate_status,
            first_pass_status,
            record,
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete scanout evidence links",),
        )
    if result_issues:
        return _audit(
            INVALID,
            "Video board scanout archive result fields are inconsistent.",
            evidence_path,
            scanout_gate_status,
            first_pass_status,
            record,
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix pass/blocker result, gate status, or classification consistency",),
        )
    if blocker_issues:
        return _audit(
            NEEDS_FOLLOWUP,
            "Video board scanout archive needs blocker disposition or retest steps.",
            evidence_path,
            scanout_gate_status,
            first_pass_status,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("file or close blockers", "record concrete scanout retest steps"),
        )
    return _audit(
        ARCHIVED,
        "First board scanout pass or classified blocker is archived.",
        evidence_path,
        scanout_gate_status,
        first_pass_status,
        record,
        actions=("hand scanout archive to compositor and board-evidence planning",),
    )


def load_video_board_scanout_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    first_pass_archive_path: Path | None = None,
) -> VideoBoardScanoutAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_board_scanout_profile()
    relative_path = evidence_path or profile.evidence_path
    first_pass_audit = fpga_first_pass_archive.load_first_pass_archive_audit(
        root,
        first_pass_archive_path,
    )
    path = root / relative_path
    if not path.exists():
        return _audit(
            BLOCKED,
            "No video board scanout archive has been captured yet.",
            relative_path.as_posix(),
            "",
            first_pass_audit.status,
            VideoBoardScanoutRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link bitstream identity, display wiring, pixel-clock/timing, visible/probe, vblank/status, blockers, and retest evidence",
            ),
        )
    try:
        record = parse_video_board_scanout(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            INVALID,
            "Video board scanout evidence could not be parsed.",
            relative_path.as_posix(),
            "",
            first_pass_audit.status,
            VideoBoardScanoutRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value archive record", "rerun the I35-S06 audit"),
        )
    return audit_video_board_scanout(
        record,
        first_pass_archive_audit=first_pass_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_video_board_scanout_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_video_board_scanout_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_video_board_scanout(
    profile: VideoBoardScanoutProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_video_board_scanout_profile()
    lines = [
        "# FPGA Video Board Scanout",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        "",
        "## Gates",
        "",
        f"- `{profile.scanout_gate}`",
        f"- `{profile.first_pass_archive_gate}`",
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


def validate_fpga_video_board_scanout(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_board_scanout_profile()
    issues: list[str] = []

    if profile.story != FPGA_VIDEO_BOARD_SCANOUT_STORY:
        issues.append(f"video board scanout story must be {FPGA_VIDEO_BOARD_SCANOUT_STORY}")
    if profile.status != VIDEO_BOARD_SCANOUT_STATUS:
        issues.append("video board scanout status must stay blocked until pass or classified blocker evidence exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("video board scanout board must match the FPGA first-test target")
    if profile.scanout_gate != fpga_video_scanout_gate.FPGA_VIDEO_SCANOUT_GATE_TOOL:
        issues.append("video board scanout must depend on I35-S05")
    if profile.first_pass_archive_gate != fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL:
        issues.append("video board scanout must depend on I31-S05")

    issues.extend(fpga_video_scanout_gate.validate_fpga_video_scanout_gate(root))
    issues.extend(fpga_first_pass_archive.validate_fpga_first_pass_archive(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "board",
        "first_pass_archive",
        "first_pass_archive_status",
        "scanout_gate",
        "scanout_gate_status",
        "gowin_report_bundle",
        "bitstream_path",
        "bitstream_sha256",
        "display_adapter_wiring",
        "pixel_clock_evidence",
        "timing_evidence",
        "visible_test_pattern_capture",
        "probe_capture",
        "video_mmio_register_log",
        "vblank_status_observation",
        "decoded_status_packet",
        "pass_fail_result",
        "archive_result",
        "blocker_class",
        "blocker_evidence",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing video board scanout field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for archive_result in (ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER):
        if archive_result not in profile.archive_results:
            issues.append(f"missing video board scanout archive result {archive_result}")
    for blocker_class in CLASSIFIED_BLOCKER_CLASSES:
        if blocker_class not in profile.blocker_classes:
            issues.append(f"missing video board scanout blocker class {blocker_class}")

    pass_record = parse_video_board_scanout(
        video_board_scanout_template()
        .replace("archived_at=", "archived_at=2026-05-13T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_video_board_scanout(
        pass_record,
        first_pass_archive_audit=_first_pass_archive(ARCHIVED),
    ).passed:
        issues.append("complete video board scanout pass record must audit as archived")

    blocker_record = parse_video_board_scanout(_blocker_archive_text())
    if not audit_video_board_scanout(
        blocker_record,
        first_pass_archive_audit=_first_pass_archive(ARCHIVED),
    ).passed:
        issues.append("complete video board scanout blocker record must audit as archived")

    missing_issue = parse_video_board_scanout(
        _blocker_archive_text().replace("filed_issues=CPU-350", "filed_issues=none")
    )
    if audit_video_board_scanout(missing_issue).status != NEEDS_FOLLOWUP:
        issues.append("video board scanout blocker archive without filed issues must require follow-up")

    default_audit = load_video_board_scanout_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default video board scanout audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_VIDEO_BOARD_SCANOUT_DOC)
    for token in (
        "Story: I35-S06",
        FPGA_VIDEO_BOARD_SCANOUT_TOOL,
        FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE.as_posix(),
        fpga_video_scanout_gate.FPGA_VIDEO_SCANOUT_GATE_TOOL,
        fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        "bitstream_sha256",
        "display_adapter_wiring",
        "pixel_clock_evidence",
        "timing_evidence",
        "visible_test_pattern_capture",
        "probe_capture",
        "video_mmio_register_log",
        "vblank_status_observation",
        "decoded_status_packet",
        ARCHIVE_RESULT_PASS,
        ARCHIVE_RESULT_BLOCKER,
        "blocker_class",
        "display_adapter",
        "pixel_clock",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
        "I36-S07",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_BOARD_SCANOUT_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video board scanout objects are not JSON serializable: {exc}")

    return tuple(issues)


def _link_issues(
    record: VideoBoardScanoutRecord,
    profile: VideoBoardScanoutProfile,
) -> list[str]:
    issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            issues.append(f"{field} must link concrete evidence")

    if record.value("first_pass_archive") and "i31_s05" not in record.value("first_pass_archive").lower():
        issues.append("first_pass_archive must reference I31-S05 evidence")
    scanout_gate = record.value("scanout_gate").lower()
    if scanout_gate and "fpga_video_scanout_gate.py" not in scanout_gate and "i35_s05" not in scanout_gate:
        issues.append("scanout_gate must reference I35-S05")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        issues.append("bitstream_path must name a .fs file")
    if record.value("bitstream_sha256") and not _is_sha256_hex(record.value("bitstream_sha256")):
        issues.append("bitstream_sha256 must be a 64-character hex digest")
    if record.value("gowin_report_bundle") and "tang_mega_138k" not in record.value("gowin_report_bundle"):
        issues.append("gowin_report_bundle must reference the Tang Mega 138K build root")
    if record.value("display_adapter_wiring") and "i35_s06" not in record.value("display_adapter_wiring").lower():
        issues.append("display_adapter_wiring must reference I35-S06 evidence")
    if record.value("pixel_clock_evidence") and "i35_s06" not in record.value("pixel_clock_evidence").lower():
        issues.append("pixel_clock_evidence must reference I35-S06 evidence")
    if record.value("timing_evidence") and "i35_s06" not in record.value("timing_evidence").lower():
        issues.append("timing_evidence must reference I35-S06 evidence")
    if record.value("video_mmio_register_log") and "i35_s06" not in record.value("video_mmio_register_log").lower():
        issues.append("video_mmio_register_log must reference I35-S06 evidence")
    if record.value("vblank_status_observation") and "i35_s06" not in record.value("vblank_status_observation").lower():
        issues.append("vblank_status_observation must reference I35-S06 evidence")
    return issues


def _result_issues(
    record: VideoBoardScanoutRecord,
    profile: VideoBoardScanoutProfile,
    first_pass_status: str,
) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    pass_fail_result = record.value("pass_fail_result")

    if first_pass_status and first_pass_status != ARCHIVED:
        issues.append("first_pass_archive_status must be archived")
    if record.value("scanout_gate_status") and record.value("scanout_gate_status") != "passed":
        issues.append("scanout_gate_status must be passed")
    if archive_result not in profile.archive_results:
        issues.append("archive_result must be board_scanout_pass_archived or board_scanout_blocker_archived")
    if pass_fail_result not in {BOARD_RESULT_PASS, BOARD_RESULT_FAILURE}:
        issues.append("pass_fail_result must be scanout_pass or failure_observed")

    if archive_result == ARCHIVE_RESULT_PASS:
        if pass_fail_result != BOARD_RESULT_PASS:
            issues.append("board_scanout_pass_archived requires pass_fail_result=scanout_pass")
        if record.value("blocker_class") != CLASS_NONE:
            issues.append("board_scanout_pass_archived requires blocker_class=none")
        if not _is_empty_disposition(record.value("blocker_evidence")):
            issues.append("board_scanout_pass_archived requires blocker_evidence=none")
        if (
            _is_empty_disposition(record.value("visible_test_pattern_capture"))
            and _is_empty_disposition(record.value("probe_capture"))
        ):
            issues.append("board_scanout_pass_archived requires visible_test_pattern_capture or probe_capture")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if pass_fail_result != BOARD_RESULT_FAILURE:
            issues.append("board_scanout_blocker_archived requires pass_fail_result=failure_observed")
        if record.value("blocker_class") not in CLASSIFIED_BLOCKER_CLASSES:
            issues.append("board_scanout_blocker_archived requires a classified blocker_class")
        if _is_empty_disposition(record.value("blocker_evidence")):
            issues.append("board_scanout_blocker_archived requires blocker_evidence")
    return issues


def _blocker_issues(record: VideoBoardScanoutRecord) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_steps = record.value("retest_steps")

    if _is_empty_disposition(retest_steps):
        issues.append("retest_steps must be concrete")
    if archive_result == ARCHIVE_RESULT_PASS:
        if not _is_empty_disposition(residual_blockers):
            issues.append("board_scanout_pass_archived requires residual_blockers=none")
        if not _is_empty_disposition(filed_issues):
            issues.append("board_scanout_pass_archived requires filed_issues=none")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if _is_empty_disposition(residual_blockers):
            issues.append("board_scanout_blocker_archived requires residual_blockers")
        if _is_empty_disposition(filed_issues):
            issues.append("board_scanout_blocker_archived requires filed_issues")
    return issues


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    scanout_gate_status: str,
    first_pass_archive_status: str,
    record: VideoBoardScanoutRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    result_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> VideoBoardScanoutAudit:
    return VideoBoardScanoutAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        scanout_gate_status=scanout_gate_status,
        first_pass_archive_status=first_pass_archive_status,
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
        video_board_scanout_template()
        .replace("archived_at=", "archived_at=2026-05-13T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("visible_test_pattern_capture=docs/implementation/evidence/i35_s06_test_pattern.jpg", "visible_test_pattern_capture=none")
        .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i35_s06_pixel_clock_probe.vcd")
        .replace("pass_fail_result=scanout_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=board_scanout_pass_archived", "archive_result=board_scanout_blocker_archived")
        .replace("blocker_class=none", "blocker_class=pixel_clock")
        .replace("blocker_evidence=none", "blocker_evidence=docs/implementation/evidence/i35_s06_pixel_clock_blocker.txt")
        .replace("residual_blockers=none", "residual_blockers=video_pixel_clk_unstable")
        .replace("filed_issues=none", "filed_issues=CPU-350")
    )


def _first_pass_archive(status: str) -> fpga_first_pass_archive.FirstPassArchiveAudit:
    return fpga_first_pass_archive.FirstPassArchiveAudit(
        status=status,
        message=status,
        evidence_path=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix(),
        first_board_archive_status=ARCHIVED,
        programming_status="observed",
        replay_status="not_required",
        archive_result=fpga_first_pass_archive.ARCHIVE_RESULT_PASS,
        pass_fail_result="first_pass",
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

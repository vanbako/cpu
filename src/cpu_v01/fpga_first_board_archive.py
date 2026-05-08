"""Tang Mega 138K first-board evidence archive gate.

Owner stories:
- I24-S05: archive first-board evidence and close or file blockers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_programming


JsonValue = Any

FPGA_ARCHIVE_STORY = "I24-S05"
FPGA_ARCHIVE_DOC = Path("docs/implementation/fpga-first-board-evidence.md")
FPGA_ARCHIVE_TOOL = "python tools\\fpga_first_board_archive.py --check"
FPGA_ARCHIVE_EVIDENCE = Path(
    "docs/implementation/evidence/i24_s05_first_board_archive.txt"
)
ARCHIVE_ARCHIVED = "archived"
ARCHIVE_BLOCKED = "blocked"
ARCHIVE_INVALID = "invalid"
ARCHIVE_NEEDS_FOLLOWUP = "needs_followup"


@dataclass(frozen=True)
class ArchiveEvidenceField:
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
class FpgaFirstBoardArchiveProfile:
    story: str
    board: str
    programming_gate: str
    archive_path: Path
    required_result: str
    required_fields: tuple[ArchiveEvidenceField, ...]
    link_fields: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "programming_gate": self.programming_gate,
            "archive_path": self.archive_path.as_posix(),
            "required_result": self.required_result,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "link_fields": list(self.link_fields),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstBoardArchiveRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstBoardArchiveAudit:
    status: str
    message: str
    archive_path: str
    programming_status: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == ARCHIVE_ARCHIVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "archive_path": self.archive_path,
            "programming_status": self.programming_status,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_first_board_archive_profile() -> FpgaFirstBoardArchiveProfile:
    return FpgaFirstBoardArchiveProfile(
        story=FPGA_ARCHIVE_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        programming_gate=fpga_programming.FPGA_PROGRAMMING_TOOL,
        archive_path=FPGA_ARCHIVE_EVIDENCE,
        required_result="first_pass",
        required_fields=(
            ArchiveEvidenceField("story", True, "Must be I24-S05."),
            ArchiveEvidenceField("board", True, "Physical board name."),
            ArchiveEvidenceField("archived_at", True, "Local archive date/time."),
            ArchiveEvidenceField("identity_evidence", True, "I24-S01 scan or marking evidence."),
            ArchiveEvidenceField("constraints_evidence", True, "I24-S02 pin overlay evidence."),
            ArchiveEvidenceField("gowin_report_bundle", True, "I24-S03 report-bundle root."),
            ArchiveEvidenceField("bitstream_path", True, "Audited .fs bitstream path."),
            ArchiveEvidenceField("programming_evidence", True, "I24-S04 evidence record path."),
            ArchiveEvidenceField("programming_log", True, "Captured programming log path."),
            ArchiveEvidenceField("reset_observation", True, "Reset assertion/release capture."),
            ArchiveEvidenceField("led_evidence", True, "Photo, video, or probe capture path."),
            ArchiveEvidenceField("board_result", True, "Must be first_pass for archive pass."),
            ArchiveEvidenceField("residual_blockers", True, "none, or named blockers."),
            ArchiveEvidenceField("filed_issues", True, "none, or issue IDs for residual blockers."),
            ArchiveEvidenceField("retest_steps", True, "none, or concrete retest steps."),
        ),
        link_fields=(
            "identity_evidence",
            "constraints_evidence",
            "gowin_report_bundle",
            "bitstream_path",
            "programming_evidence",
            "programming_log",
            "reset_observation",
            "led_evidence",
        ),
        blockers=(
            "I24-S04 programming audit must pass before the archive can pass",
            "the archive must link scan, constraints, reports, bitstream, programming, reset, and LED/probe evidence",
            "residual blockers must be closed as none or filed with issue IDs and retest steps",
            "do not claim first-board completion from an incomplete or failed archive record",
        ),
    )


def first_board_archive_template(
    profile: FpgaFirstBoardArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_board_archive_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            f"board={profile.board}",
            "archived_at=",
            "identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
            "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
            "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
            "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
            f"programming_evidence={fpga_programming.FPGA_PROGRAMMING_EVIDENCE.as_posix()}",
            "programming_log=docs/implementation/evidence/i24_s04_programming.log",
            "reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt",
            "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
            "board_result=first_pass",
            "residual_blockers=none",
            "filed_issues=none",
            "retest_steps=none",
            "",
        )
    )


def parse_first_board_archive(text: str) -> FirstBoardArchiveRecord:
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
    return FirstBoardArchiveRecord(fields)


def audit_first_board_archive(
    record: FirstBoardArchiveRecord,
    *,
    programming_audit: fpga_programming.ProgrammingAudit,
    archive_path: str = "<inline>",
    profile: FpgaFirstBoardArchiveProfile | None = None,
) -> FirstBoardArchiveAudit:
    if profile is None:
        profile = fpga_first_board_archive_profile()
    if not programming_audit.passed:
        return FirstBoardArchiveAudit(
            status=ARCHIVE_BLOCKED,
            message="First-board archive is blocked until I24-S04 programming evidence passes.",
            archive_path=archive_path,
            programming_status=programming_audit.status,
            missing_fields=(),
            link_issues=(),
            blocker_issues=(),
            actions=("complete I24-S04 programming evidence", "do not archive as first pass"),
        )

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I24-S05")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    link_issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        link_issues.append("bitstream_path must name a .fs file")
    if record.value("programming_evidence") and "i24_s04" not in record.value("programming_evidence"):
        link_issues.append("programming_evidence must link the I24-S04 record")

    blocker_issues: list[str] = []
    if record.value("board_result") != profile.required_result:
        blocker_issues.append("board_result must be first_pass")
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_steps = record.value("retest_steps")
    if residual_blockers and not _is_empty_disposition(residual_blockers):
        if _is_empty_disposition(filed_issues):
            blocker_issues.append("residual blockers must have filed_issues")
        if _is_empty_disposition(retest_steps):
            blocker_issues.append("residual blockers must have retest_steps")

    if missing_fields:
        return FirstBoardArchiveAudit(
            status=ARCHIVE_INVALID,
            message="First-board archive evidence is incomplete or malformed.",
            archive_path=archive_path,
            programming_status=programming_audit.status,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required archive fields", "rerun the archive audit"),
        )
    if link_issues:
        return FirstBoardArchiveAudit(
            status=ARCHIVE_INVALID,
            message="First-board archive links are incomplete or malformed.",
            archive_path=archive_path,
            programming_status=programming_audit.status,
            missing_fields=(),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholder links with concrete evidence paths", "rerun the archive audit"),
        )
    if blocker_issues:
        return FirstBoardArchiveAudit(
            status=ARCHIVE_NEEDS_FOLLOWUP,
            message="First-board archive exists but blocker disposition is not complete.",
            archive_path=archive_path,
            programming_status=programming_audit.status,
            missing_fields=(),
            link_issues=(),
            blocker_issues=tuple(blocker_issues),
            actions=("file or close residual blockers", "record retest steps before closure"),
        )
    return FirstBoardArchiveAudit(
        status=ARCHIVE_ARCHIVED,
        message="First-board evidence archive is complete.",
        archive_path=archive_path,
        programming_status=programming_audit.status,
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=("first-board archive can be referenced by downstream FPGA stories",),
    )


def load_first_board_archive_audit(
    root: Path | None = None,
    archive_path: Path | None = None,
    programming_evidence_path: Path | None = None,
    build_root: Path | None = None,
) -> FirstBoardArchiveAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_board_archive_profile()
    relative_path = archive_path or profile.archive_path
    programming_audit = fpga_programming.load_programming_audit(
        root,
        programming_evidence_path,
        build_root,
    )
    path = root / relative_path
    if not path.exists():
        return FirstBoardArchiveAudit(
            status=ARCHIVE_BLOCKED,
            message="No first-board archive evidence note has been captured yet.",
            archive_path=relative_path.as_posix(),
            programming_status=programming_audit.status,
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            blocker_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link scan, reports, bitstream, programming, reset, and LED/probe evidence",
                "close or file every residual blocker",
            ),
        )
    try:
        record = parse_first_board_archive(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return FirstBoardArchiveAudit(
            status=ARCHIVE_INVALID,
            message="First-board archive evidence could not be parsed.",
            archive_path=relative_path.as_posix(),
            programming_status=programming_audit.status,
            missing_fields=(str(exc),),
            link_issues=(),
            blocker_issues=(),
            actions=("fix the key=value archive record", "rerun the archive audit"),
        )
    return audit_first_board_archive(
        record,
        programming_audit=programming_audit,
        archive_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_first_board_archive_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_board_archive_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_board_archive(
    profile: FpgaFirstBoardArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_board_archive_profile()
    lines = [
        "# FPGA First Board Evidence",
        "",
        f"Story: {profile.story}",
        "",
        f"Board: `{profile.board}`",
        f"Programming gate: `{profile.programming_gate}`",
        f"Archive path: `{profile.archive_path.as_posix()}`",
        f"Required board result: `{profile.required_result}`",
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
    lines.extend(["", "## Evidence Links", ""])
    lines.extend(f"- `{field}`." for field in profile.link_fields)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_board_archive(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_board_archive_profile()
    issues: list[str] = []

    if profile.story != FPGA_ARCHIVE_STORY:
        issues.append(f"archive story must be {FPGA_ARCHIVE_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("archive board must match first-test profile")
    if profile.programming_gate != fpga_programming.FPGA_PROGRAMMING_TOOL:
        issues.append("archive programming gate must be the I24-S04 programming gate")
    if profile.required_result != "first_pass":
        issues.append("archive required board result must be first_pass")

    issues.extend(fpga_programming.validate_fpga_programming(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "board",
        "archived_at",
        "identity_evidence",
        "constraints_evidence",
        "gowin_report_bundle",
        "bitstream_path",
        "programming_evidence",
        "programming_log",
        "reset_observation",
        "led_evidence",
        "board_result",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing archive evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    for link in profile.link_fields:
        if link not in fields:
            issues.append(f"archive link field {link} must also be required")

    passed_programming = fpga_programming.ProgrammingAudit(
        status="passed",
        message="passed",
        evidence_path=fpga_programming.FPGA_PROGRAMMING_EVIDENCE.as_posix(),
        build_status="passed",
        missing_fields=(),
        observation_issues=(),
        actions=(),
    )
    good_record = parse_first_board_archive(
        "\n".join(
            (
                "story=I24-S05",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "archived_at=2026-05-08T00:00:00",
                "identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
                "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
                "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
                "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                "programming_evidence=docs/implementation/evidence/i24_s04_sram_programming.txt",
                "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                "reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt",
                "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                "board_result=first_pass",
                "residual_blockers=none",
                "filed_issues=none",
                "retest_steps=none",
            )
        )
    )
    if not audit_first_board_archive(good_record, programming_audit=passed_programming).passed:
        issues.append("complete first-board archive evidence must audit as archived")

    default_audit = load_first_board_archive_audit(root)
    if default_audit.status != ARCHIVE_BLOCKED:
        issues.append("default first-board archive audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_ARCHIVE_DOC)
    for token in (
        "Story: I24-S05",
        FPGA_ARCHIVE_TOOL,
        profile.archive_path.as_posix(),
        fpga_programming.FPGA_PROGRAMMING_TOOL,
        fpga_programming.FPGA_PROGRAMMING_EVIDENCE.as_posix(),
        "identity_evidence",
        "constraints_evidence",
        "gowin_report_bundle",
        "bitstream_path",
        "programming_log",
        "reset_observation",
        "led_evidence",
        "board_result=first_pass",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_ARCHIVE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

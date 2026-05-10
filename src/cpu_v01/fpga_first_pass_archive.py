"""First physical integrated CPU pass or blocker archive gate.

Owner stories:
- I31-S05: archive first physical single-core CPU pass or blocker disposition.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_first_board_archive,
    fpga_first_pass_programming,
    fpga_first_pass_replay,
    fpga_first_test,
)


JsonValue = Any

FPGA_FIRST_PASS_ARCHIVE_STORY = "I31-S05"
FPGA_FIRST_PASS_ARCHIVE_DOC = Path("docs/implementation/fpga-first-pass-archive.md")
FPGA_FIRST_PASS_ARCHIVE_TOOL = "python tools\\fpga_first_pass_archive.py --check"
FPGA_FIRST_PASS_ARCHIVE_EVIDENCE = Path(
    "docs/implementation/evidence/i31_s05_first_cpu_pass_archive.txt"
)
FIRST_PASS_ARCHIVE_STATUS = "blocked_until_pass_or_classified_blocker"

ARCHIVED = "archived"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_FOLLOWUP = "needs_followup"

ARCHIVE_RESULT_PASS = "first_pass_archived"
ARCHIVE_RESULT_BLOCKER = "blocker_disposition_archived"
REPLAY_NOT_REQUIRED = "not_required"


@dataclass(frozen=True)
class FirstPassArchiveField:
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
class FirstPassArchiveResultRule:
    archive_result: str
    programming_result: str
    replay_requirement: str
    blocker_requirement: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "archive_result": self.archive_result,
            "programming_result": self.programming_result,
            "replay_requirement": self.replay_requirement,
            "blocker_requirement": self.blocker_requirement,
        }


@dataclass(frozen=True)
class FirstPassArchiveProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    first_board_archive_gate: str
    programming_gate: str
    replay_gate: str
    archive_results: tuple[str, ...]
    required_fields: tuple[FirstPassArchiveField, ...]
    result_rules: tuple[FirstPassArchiveResultRule, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> FirstPassArchiveField:
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
            "first_board_archive_gate": self.first_board_archive_gate,
            "programming_gate": self.programming_gate,
            "replay_gate": self.replay_gate,
            "archive_results": list(self.archive_results),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "result_rules": [rule.as_dict() for rule in self.result_rules],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstPassArchiveRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstPassArchiveAudit:
    status: str
    message: str
    evidence_path: str
    first_board_archive_status: str
    programming_status: str
    replay_status: str
    archive_result: str
    pass_fail_result: str
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
            "first_board_archive_status": self.first_board_archive_status,
            "programming_status": self.programming_status,
            "replay_status": self.replay_status,
            "archive_result": self.archive_result,
            "pass_fail_result": self.pass_fail_result,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "result_issues": list(self.result_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_first_pass_archive_profile() -> FirstPassArchiveProfile:
    return FirstPassArchiveProfile(
        story=FPGA_FIRST_PASS_ARCHIVE_STORY,
        status=FIRST_PASS_ARCHIVE_STATUS,
        evidence_path=FPGA_FIRST_PASS_ARCHIVE_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        first_board_archive_gate=fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
        programming_gate=fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
        replay_gate=fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_TOOL,
        archive_results=(ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER),
        required_fields=(
            FirstPassArchiveField("story", True, "Must be I31-S05."),
            FirstPassArchiveField("archived_at", True, "Local archive timestamp."),
            FirstPassArchiveField("repository_commit", True, "Repository commit used for the board run."),
            FirstPassArchiveField("board", True, "Physical board name."),
            FirstPassArchiveField("first_board_archive", True, "I24-S05 first-board archive path."),
            FirstPassArchiveField("first_board_archive_status", True, "I24-S05 audit status."),
            FirstPassArchiveField("identity_evidence", True, "Board scan or marking evidence."),
            FirstPassArchiveField("constraints_evidence", True, "CST/pin overlay evidence."),
            FirstPassArchiveField("gowin_report_bundle", True, "Gowin report bundle root."),
            FirstPassArchiveField("bitstream_path", True, "Programmed .fs bitstream path."),
            FirstPassArchiveField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            FirstPassArchiveField("programming_evidence", True, "I31-S03 programming observation path."),
            FirstPassArchiveField("programming_status", True, "I31-S03 audit status."),
            FirstPassArchiveField("programming_board_result", True, "first_pass or failure_observed."),
            FirstPassArchiveField("programming_log", True, "Programming tool log path."),
            FirstPassArchiveField("reset_observation", True, "Reset assertion/release evidence."),
            FirstPassArchiveField("led_evidence", True, "Heartbeat/pass/fail LED evidence."),
            FirstPassArchiveField("uart_log", True, "UART/status capture log path."),
            FirstPassArchiveField("decoded_status_packet", True, "Decoded status packet or transcript."),
            FirstPassArchiveField("probe_capture", True, "Probe capture path, or none."),
            FirstPassArchiveField("replay_classification", True, "I31-S04 replay record, or not_required_first_pass."),
            FirstPassArchiveField("replay_status", True, "classified or not_required."),
            FirstPassArchiveField("replay_case_id", True, "Selected replay case, or none."),
            FirstPassArchiveField("first_mismatch", True, "First mismatch/assertion, or none for first pass."),
            FirstPassArchiveField("debug_evidence", True, "I25-S05 debug evidence path, or none for first pass."),
            FirstPassArchiveField("pass_fail_result", True, "first_pass or failure_observed."),
            FirstPassArchiveField("archive_result", True, "first_pass_archived or blocker_disposition_archived."),
            FirstPassArchiveField("residual_blockers", True, "none, or named blockers."),
            FirstPassArchiveField("filed_issues", True, "none, or issue IDs/links for blockers."),
            FirstPassArchiveField("retest_steps", True, "Concrete commands or steps for rerunning the board evidence."),
        ),
        result_rules=(
            FirstPassArchiveResultRule(
                ARCHIVE_RESULT_PASS,
                "I31-S03 observed with board_result=first_pass",
                "replay_status=not_required and replay_classification=not_required_first_pass",
                "residual_blockers=none and filed_issues=none",
            ),
            FirstPassArchiveResultRule(
                ARCHIVE_RESULT_BLOCKER,
                "I31-S03 observed with board_result=failure_observed",
                "I31-S04 replay_status=classified, replay_case_id, and first_mismatch are required",
                "residual_blockers, filed_issues, and retest_steps must be concrete",
            ),
        ),
        link_fields=(
            "first_board_archive",
            "identity_evidence",
            "constraints_evidence",
            "gowin_report_bundle",
            "bitstream_path",
            "programming_evidence",
            "programming_log",
            "reset_observation",
            "led_evidence",
            "uart_log",
            "decoded_status_packet",
        ),
        retest_commands=(
            fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
            fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
            fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_TOOL,
        ),
        blockers=(
            "I24-S05 first-board archive links scan, reports, bitstream, programming, reset, and LED evidence",
            "I31-S03 programming evidence must be observed before final archive closure",
            "first-pass archives must have no residual blockers",
            "failure archives must link classified I31-S04 replay evidence with first_mismatch and filed issues",
            "all archives must carry concrete retest steps for reproducing the board result",
        ),
    )


def first_pass_archive_template(profile: FirstPassArchiveProfile | None = None) -> str:
    if profile is None:
        profile = fpga_first_pass_archive_profile()
    retest_steps = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"first_board_archive={fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix()}",
            f"first_board_archive_status={fpga_first_board_archive.ARCHIVE_ARCHIVED}",
            "identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
            "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
            "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
            "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            f"programming_evidence={fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix()}",
            f"programming_status={fpga_first_pass_programming.OBSERVED}",
            f"programming_board_result={fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS}",
            "programming_log=docs/implementation/evidence/i31_s03_programming.log",
            "reset_observation=docs/implementation/evidence/i31_s03_reset_release.txt",
            "led_evidence=docs/implementation/evidence/i31_s03_leds.mp4",
            "uart_log=docs/implementation/evidence/i31_s03_uart.log",
            "decoded_status_packet=docs/implementation/evidence/i31_s03_status_packet.json",
            "probe_capture=none",
            "replay_classification=not_required_first_pass",
            f"replay_status={REPLAY_NOT_REQUIRED}",
            "replay_case_id=none",
            "first_mismatch=none",
            "debug_evidence=none",
            f"pass_fail_result={fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS}",
            f"archive_result={ARCHIVE_RESULT_PASS}",
            "residual_blockers=none",
            "filed_issues=none",
            f"retest_steps={retest_steps}",
            "",
        )
    )


def parse_first_pass_archive(text: str) -> FirstPassArchiveRecord:
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
    return FirstPassArchiveRecord(fields)


def audit_first_pass_archive(
    record: FirstPassArchiveRecord,
    *,
    first_board_archive_audit: fpga_first_board_archive.FirstBoardArchiveAudit | None = None,
    programming_audit: fpga_first_pass_programming.FirstPassProgrammingAudit | None = None,
    replay_audit: fpga_first_pass_replay.FirstPassReplayAudit | None = None,
    evidence_path: str = "<inline>",
    profile: FirstPassArchiveProfile | None = None,
) -> FirstPassArchiveAudit:
    if profile is None:
        profile = fpga_first_pass_archive_profile()

    first_board_status = (
        first_board_archive_audit.status
        if first_board_archive_audit is not None
        else record.value("first_board_archive_status")
    )
    programming_status = programming_audit.status if programming_audit is not None else record.value("programming_status")
    replay_status = replay_audit.status if replay_audit is not None else record.value("replay_status")

    if first_board_archive_audit is not None and first_board_archive_audit.status == fpga_first_board_archive.ARCHIVE_BLOCKED:
        return _audit(
            BLOCKED,
            "First CPU pass archive is blocked until I24-S05 evidence exists.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            actions=("complete or file I24-S05 first-board evidence first",),
        )
    if programming_audit is not None and not programming_audit.passed:
        return _audit(
            BLOCKED,
            "First CPU pass archive is blocked until I31-S03 programming evidence is observed.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            actions=("complete I31-S03 programming observations first",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I31-S05")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    link_issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence")
    if record.value("first_board_archive") and "i24_s05" not in record.value("first_board_archive").lower():
        link_issues.append("first_board_archive must reference I24-S05 evidence")
    if record.value("identity_evidence") and "i24_s01" not in record.value("identity_evidence").lower():
        link_issues.append("identity_evidence must reference board identity evidence")
    if record.value("constraints_evidence") and "i24_s02" not in record.value("constraints_evidence").lower():
        link_issues.append("constraints_evidence must reference constraints overlay evidence")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        link_issues.append("bitstream_path must name a .fs file")
    if record.value("bitstream_sha256") and not _is_sha256_hex(record.value("bitstream_sha256")):
        link_issues.append("bitstream_sha256 must be a 64-character hex digest")
    if record.value("programming_evidence") and "i31_s03" not in record.value("programming_evidence").lower():
        link_issues.append("programming_evidence must reference I31-S03 evidence")
    replay_classification = record.value("replay_classification")
    if (
        replay_classification
        and replay_classification != "not_required_first_pass"
        and "i31_s04" not in replay_classification.lower()
    ):
        link_issues.append("replay_classification must reference I31-S04 evidence or be not_required_first_pass")
    if (
        record.value("debug_evidence")
        and not _is_empty_disposition(record.value("debug_evidence"))
        and "i25_s05" not in record.value("debug_evidence").lower()
    ):
        link_issues.append("debug_evidence must reference I25-S05 evidence or be none")

    result_issues: list[str] = []
    archive_result = record.value("archive_result")
    pass_fail_result = record.value("pass_fail_result")
    programming_board_result = record.value("programming_board_result")
    if archive_result not in profile.archive_results:
        result_issues.append("archive_result must be first_pass_archived or blocker_disposition_archived")
    if pass_fail_result not in {
        fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS,
        fpga_first_pass_programming.BOARD_RESULT_FAILURE,
    }:
        result_issues.append("pass_fail_result must be first_pass or failure_observed")
    if programming_status and programming_status != fpga_first_pass_programming.OBSERVED:
        result_issues.append("programming_status must be observed")
    if programming_audit is not None and programming_board_result != programming_audit.board_result:
        result_issues.append("programming_board_result must match I31-S03 audit")
    if programming_board_result and programming_board_result != pass_fail_result:
        result_issues.append("programming_board_result must match pass_fail_result")

    blocker_issues: list[str] = []
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_steps = record.value("retest_steps")
    if _is_empty_disposition(retest_steps):
        blocker_issues.append("retest_steps must be concrete")

    if archive_result == ARCHIVE_RESULT_PASS:
        if pass_fail_result != fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS:
            result_issues.append("first_pass_archived requires pass_fail_result=first_pass")
        if record.value("first_board_archive_status") != fpga_first_board_archive.ARCHIVE_ARCHIVED:
            result_issues.append("first_pass_archived requires first_board_archive_status=archived")
        if record.value("replay_status") != REPLAY_NOT_REQUIRED:
            result_issues.append("first_pass_archived requires replay_status=not_required")
        if record.value("replay_classification") != "not_required_first_pass":
            result_issues.append("first_pass_archived requires replay_classification=not_required_first_pass")
        if not _is_empty_disposition(residual_blockers):
            blocker_issues.append("first_pass_archived requires residual_blockers=none")
        if not _is_empty_disposition(filed_issues):
            blocker_issues.append("first_pass_archived requires filed_issues=none")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if pass_fail_result != fpga_first_pass_programming.BOARD_RESULT_FAILURE:
            result_issues.append("blocker_disposition_archived requires pass_fail_result=failure_observed")
        if record.value("first_board_archive_status") not in {
            fpga_first_board_archive.ARCHIVE_NEEDS_FOLLOWUP,
            fpga_first_board_archive.ARCHIVE_ARCHIVED,
        }:
            result_issues.append("blocker disposition requires I24-S05 status needs_followup or archived")
        if record.value("replay_status") != fpga_first_pass_replay.CLASSIFIED:
            result_issues.append("blocker disposition requires replay_status=classified")
        if replay_audit is not None and not replay_audit.passed:
            result_issues.append("blocker disposition requires a passing I31-S04 replay audit")
        if _is_empty_disposition(replay_classification):
            link_issues.append("blocker disposition requires replay_classification")
        if _is_empty_disposition(record.value("replay_case_id")):
            result_issues.append("blocker disposition requires replay_case_id")
        if _is_empty_disposition(record.value("first_mismatch")):
            result_issues.append("blocker disposition requires first_mismatch")
        if _is_empty_disposition(residual_blockers):
            blocker_issues.append("blocker disposition requires residual_blockers")
        if _is_empty_disposition(filed_issues):
            blocker_issues.append("blocker disposition requires filed_issues")

    if missing_fields:
        return _audit(
            INVALID,
            "First CPU pass archive evidence is incomplete or malformed.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I31-S05 fields", "rerun the archive audit"),
        )
    if link_issues:
        return _audit(
            INVALID,
            "First CPU pass archive links are incomplete or malformed.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete evidence links", "rerun the archive audit"),
        )
    if result_issues:
        return _audit(
            INVALID,
            "First CPU pass archive result fields are inconsistent.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix pass/fail, replay, and archive result consistency",),
        )
    if blocker_issues:
        return _audit(
            NEEDS_FOLLOWUP,
            "First CPU pass archive needs blocker disposition or retest steps.",
            evidence_path,
            first_board_status,
            programming_status,
            replay_status,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("close or file blockers", "record concrete retest steps"),
        )
    return _audit(
        ARCHIVED,
        "First physical single-core CPU pass or blocker disposition is archived.",
        evidence_path,
        first_board_status,
        programming_status,
        replay_status,
        record,
        actions=("hand archive to I31-S06 retest matrix and release-candidate evidence",),
    )


def load_first_pass_archive_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    first_board_archive_path: Path | None = None,
    programming_evidence_path: Path | None = None,
    replay_evidence_path: Path | None = None,
) -> FirstPassArchiveAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_archive_profile()
    relative_path = evidence_path or profile.evidence_path
    first_board_audit = fpga_first_board_archive.load_first_board_archive_audit(
        root,
        first_board_archive_path,
    )
    programming_audit = fpga_first_pass_programming.load_first_pass_programming_audit(
        root,
        programming_evidence_path,
    )
    replay_audit = fpga_first_pass_replay.load_first_pass_replay_audit(
        root,
        replay_evidence_path,
    )
    path = root / relative_path
    if not path.exists():
        return _audit(
            BLOCKED,
            "No first CPU pass archive has been captured yet.",
            relative_path.as_posix(),
            first_board_audit.status,
            programming_audit.status,
            replay_audit.status,
            FirstPassArchiveRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link scan, reports, bitstream, programming, reset, LED/UART/probe, replay, blockers, and retest steps",
            ),
        )
    try:
        record = parse_first_pass_archive(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            INVALID,
            "First CPU pass archive evidence could not be parsed.",
            relative_path.as_posix(),
            first_board_audit.status,
            programming_audit.status,
            replay_audit.status,
            FirstPassArchiveRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value archive record", "rerun the I31-S05 audit"),
        )
    return audit_first_pass_archive(
        record,
        first_board_archive_audit=first_board_audit,
        programming_audit=programming_audit,
        replay_audit=replay_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_first_pass_archive_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_archive_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_archive(
    profile: FirstPassArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_archive_profile()
    lines = [
        "# FPGA First-Pass Archive",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        "",
        "## Gates",
        "",
        f"- `{profile.first_board_archive_gate}`",
        f"- `{profile.programming_gate}`",
        f"- `{profile.replay_gate}`",
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
        lines.append(f"- `{rule.archive_result}`: {rule.programming_result}; {rule.replay_requirement}.")
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_pass_archive(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_archive_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_ARCHIVE_STORY:
        issues.append(f"first-pass archive story must be {FPGA_FIRST_PASS_ARCHIVE_STORY}")
    if profile.status != FIRST_PASS_ARCHIVE_STATUS:
        issues.append("first-pass archive status must stay blocked until pass or classified blocker evidence exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("first-pass archive board must match the FPGA first-test target")
    if profile.first_board_archive_gate != fpga_first_board_archive.FPGA_ARCHIVE_TOOL:
        issues.append("first-pass archive must depend on I24-S05")
    if profile.programming_gate != fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL:
        issues.append("first-pass archive must depend on I31-S03")
    if profile.replay_gate != fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_TOOL:
        issues.append("first-pass archive must depend on I31-S04")

    issues.extend(fpga_first_board_archive.validate_fpga_first_board_archive(root))
    issues.extend(fpga_first_pass_programming.validate_fpga_first_pass_programming(root))
    issues.extend(fpga_first_pass_replay.validate_fpga_first_pass_replay(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "board",
        "first_board_archive",
        "first_board_archive_status",
        "identity_evidence",
        "constraints_evidence",
        "gowin_report_bundle",
        "bitstream_path",
        "bitstream_sha256",
        "programming_evidence",
        "programming_status",
        "programming_board_result",
        "programming_log",
        "reset_observation",
        "led_evidence",
        "uart_log",
        "decoded_status_packet",
        "probe_capture",
        "replay_classification",
        "replay_status",
        "replay_case_id",
        "first_mismatch",
        "debug_evidence",
        "pass_fail_result",
        "archive_result",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing first-pass archive field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for archive_result in (ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER):
        if archive_result not in profile.archive_results:
            issues.append(f"missing first-pass archive result {archive_result}")

    pass_record = parse_first_pass_archive(
        first_pass_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T15:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_first_pass_archive(
        pass_record,
        first_board_archive_audit=_first_board_archive(fpga_first_board_archive.ARCHIVE_ARCHIVED),
        programming_audit=_programming(fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS),
    ).passed:
        issues.append("complete first-pass archive record must audit as archived")

    blocker_record = parse_first_pass_archive(_blocker_archive_text())
    if not audit_first_pass_archive(
        blocker_record,
        first_board_archive_audit=_first_board_archive(fpga_first_board_archive.ARCHIVE_NEEDS_FOLLOWUP),
        programming_audit=_programming(fpga_first_pass_programming.BOARD_RESULT_FAILURE),
        replay_audit=_replay(fpga_first_pass_replay.CLASSIFIED),
    ).passed:
        issues.append("complete blocker disposition archive must audit as archived")

    missing_issue = parse_first_pass_archive(
        _blocker_archive_text().replace("filed_issues=CPU-123", "filed_issues=none")
    )
    if audit_first_pass_archive(missing_issue).status != NEEDS_FOLLOWUP:
        issues.append("blocker archive without filed issues must require follow-up")

    default_audit = load_first_pass_archive_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default first-pass archive audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_ARCHIVE_DOC)
    for token in (
        "Story: I31-S05",
        FPGA_FIRST_PASS_ARCHIVE_TOOL,
        FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix(),
        fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
        fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
        fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_TOOL,
        "identity_evidence",
        "constraints_evidence",
        "gowin_report_bundle",
        "bitstream_sha256",
        "programming_log",
        "reset_observation",
        "led_evidence",
        "uart_log",
        "decoded_status_packet",
        "probe_capture",
        "replay_classification",
        "first_mismatch",
        "first_pass_archived",
        "blocker_disposition_archived",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
        "I31-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_ARCHIVE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass archive objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    first_board_archive_status: str,
    programming_status: str,
    replay_status: str,
    record: FirstPassArchiveRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    result_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> FirstPassArchiveAudit:
    return FirstPassArchiveAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        first_board_archive_status=first_board_archive_status,
        programming_status=programming_status,
        replay_status=replay_status,
        archive_result=record.value("archive_result"),
        pass_fail_result=record.value("pass_fail_result"),
        missing_fields=missing_fields,
        link_issues=link_issues,
        result_issues=result_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _blocker_archive_text() -> str:
    return (
        first_pass_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T15:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("first_board_archive_status=archived", "first_board_archive_status=needs_followup")
        .replace("programming_board_result=first_pass", "programming_board_result=failure_observed")
        .replace("replay_classification=not_required_first_pass", f"replay_classification={fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_EVIDENCE.as_posix()}")
        .replace("replay_status=not_required", "replay_status=classified")
        .replace("replay_case_id=none", "replay_case_id=core.control_trap.sys_iret")
        .replace("first_mismatch=none", "first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch")
        .replace("debug_evidence=none", "debug_evidence=docs/implementation/evidence/i25_s05_debug_evidence.txt")
        .replace("pass_fail_result=first_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=first_pass_archived", "archive_result=blocker_disposition_archived")
        .replace("residual_blockers=none", "residual_blockers=trap_replay_mismatch")
        .replace("filed_issues=none", "filed_issues=CPU-123")
    )


def _first_board_archive(status: str) -> fpga_first_board_archive.FirstBoardArchiveAudit:
    return fpga_first_board_archive.FirstBoardArchiveAudit(
        status=status,
        message=status,
        archive_path=fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix(),
        programming_status="passed",
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=(),
    )


def _programming(board_result: str) -> fpga_first_pass_programming.FirstPassProgrammingAudit:
    return fpga_first_pass_programming.FirstPassProgrammingAudit(
        status=fpga_first_pass_programming.OBSERVED,
        message="observed",
        evidence_path=fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix(),
        gowin_status="passed",
        board_result=board_result,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=(),
    )


def _replay(status: str) -> fpga_first_pass_replay.FirstPassReplayAudit:
    return fpga_first_pass_replay.FirstPassReplayAudit(
        status=status,
        message=status,
        evidence_path=fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_EVIDENCE.as_posix(),
        programming_status=fpga_first_pass_programming.OBSERVED,
        debug_evidence_status="accepted",
        failure_class="trap",
        replay_case_id="core.control_trap.sys_iret",
        missing_fields=(),
        link_issues=(),
        capture_issues=(),
        packet_issues=(),
        replay_issues=(),
        classification_issues=(),
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
        "not_required_first_pass",
    }


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""Tang Retro Console 60K pass or blocker archive gate.

Owner stories:
- I34-S06: archive Retro Console 60K pass or blocker evidence and handoff policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_interactive_corpus,
    fpga_retro_console_constraints,
    fpga_retro_console_gowin,
    fpga_retro_console_identity,
    fpga_retro_console_programming,
    fpga_retro_console_replay,
)


JsonValue = Any

FPGA_RETRO_CONSOLE_ARCHIVE_STORY = "I34-S06"
FPGA_RETRO_CONSOLE_ARCHIVE_DOC = Path(
    "docs/implementation/fpga-retro-console-archive.md"
)
FPGA_RETRO_CONSOLE_ARCHIVE_TOOL = "python tools\\fpga_retro_console_archive.py --check"
FPGA_RETRO_CONSOLE_ARCHIVE_EVIDENCE = Path(
    "docs/implementation/evidence/i34_s06_retro_console_archive.txt"
)
RETRO_CONSOLE_ARCHIVE_STATUS = "blocked_until_retro_console_pass_or_blocker"

ARCHIVED = "archived"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_FOLLOWUP = "needs_followup"

ARCHIVE_RESULT_PASS = "retro_console_pass_archived"
ARCHIVE_RESULT_BLOCKER = "retro_console_blocker_archived"
REPLAY_NOT_REQUIRED = "not_required"
REPLAY_NOT_REQUIRED_PASS = "not_required_retro_console_smoke_pass"
HANDOFF_138K_ACTIVE = "retro_console_deferred_while_138k_i31_i32_active"
HANDOFF_60K_READY = "retro_console_ready_with_138k_i31_i32_active"
PRIMARY_138K_ACTIVE = "i31_i32_continue_on_tang_mega_138k"


@dataclass(frozen=True)
class RetroConsoleArchiveField:
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
class RetroConsoleArchiveResultRule:
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
class RetroConsoleArchiveProfile:
    story: str
    status: str
    board: str
    evidence_path: Path
    identity_gate: str
    constraints_gate: str
    gowin_gate: str
    programming_gate: str
    replay_gate: str
    interactive_corpus_gate: str
    archive_results: tuple[str, ...]
    handoff_policies: tuple[str, ...]
    required_fields: tuple[RetroConsoleArchiveField, ...]
    result_rules: tuple[RetroConsoleArchiveResultRule, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> RetroConsoleArchiveField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "evidence_path": self.evidence_path.as_posix(),
            "identity_gate": self.identity_gate,
            "constraints_gate": self.constraints_gate,
            "gowin_gate": self.gowin_gate,
            "programming_gate": self.programming_gate,
            "replay_gate": self.replay_gate,
            "interactive_corpus_gate": self.interactive_corpus_gate,
            "archive_results": list(self.archive_results),
            "handoff_policies": list(self.handoff_policies),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "result_rules": [rule.as_dict() for rule in self.result_rules],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class RetroConsoleArchiveRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RetroConsoleArchiveAudit:
    status: str
    message: str
    evidence_path: str
    programming_status: str
    replay_status: str
    archive_result: str
    pass_fail_result: str
    handoff_policy: str
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
            "programming_status": self.programming_status,
            "replay_status": self.replay_status,
            "archive_result": self.archive_result,
            "pass_fail_result": self.pass_fail_result,
            "handoff_policy": self.handoff_policy,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "result_issues": list(self.result_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_retro_console_archive_profile() -> RetroConsoleArchiveProfile:
    return RetroConsoleArchiveProfile(
        story=FPGA_RETRO_CONSOLE_ARCHIVE_STORY,
        status=RETRO_CONSOLE_ARCHIVE_STATUS,
        board=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD,
        evidence_path=FPGA_RETRO_CONSOLE_ARCHIVE_EVIDENCE,
        identity_gate=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        constraints_gate=(
            fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL
        ),
        gowin_gate=fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        programming_gate=(
            fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL
        ),
        replay_gate=fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_TOOL,
        interactive_corpus_gate=fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL,
        archive_results=(ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER),
        handoff_policies=(HANDOFF_138K_ACTIVE, HANDOFF_60K_READY),
        required_fields=(
            RetroConsoleArchiveField("story", True, "Must be I34-S06."),
            RetroConsoleArchiveField("archived_at", True, "Local archive timestamp."),
            RetroConsoleArchiveField("repository_commit", True, "Repository commit used for the board run."),
            RetroConsoleArchiveField("board", True, "Physical board name."),
            RetroConsoleArchiveField("identity_evidence", True, "I34-S01 board scan or marking evidence."),
            RetroConsoleArchiveField("identity_status", True, "I34-S01 audit status."),
            RetroConsoleArchiveField("constraints_evidence", True, "I34-S02 CST/pin evidence."),
            RetroConsoleArchiveField("constraints_status", True, "I34-S02 audit status."),
            RetroConsoleArchiveField("gowin_evidence", True, "I34-S03 Gowin build evidence path."),
            RetroConsoleArchiveField("gowin_status", True, "I34-S03 audit status."),
            RetroConsoleArchiveField("gowin_report_bundle", True, "Retro Console Gowin report bundle root."),
            RetroConsoleArchiveField("bitstream_path", True, "Programmed Retro Console .fs bitstream path."),
            RetroConsoleArchiveField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            RetroConsoleArchiveField("programming_evidence", True, "I34-S04 SRAM programming observation path."),
            RetroConsoleArchiveField("programming_status", True, "I34-S04 audit status."),
            RetroConsoleArchiveField("programming_board_result", True, "retro_console_smoke_pass or failure_observed."),
            RetroConsoleArchiveField("programming_log", True, "Programming tool log path."),
            RetroConsoleArchiveField("reset_observation", True, "Reset assertion/release evidence."),
            RetroConsoleArchiveField("led_evidence", True, "Heartbeat/pass/fail LED evidence."),
            RetroConsoleArchiveField("uart_log", True, "UART/status capture log path."),
            RetroConsoleArchiveField("decoded_status_packet", True, "Decoded status packet or transcript."),
            RetroConsoleArchiveField("probe_capture", True, "Probe capture path, or none."),
            RetroConsoleArchiveField("replay_classification", True, "I34-S05 replay record, or not_required_retro_console_smoke_pass."),
            RetroConsoleArchiveField("replay_status", True, "classified or not_required."),
            RetroConsoleArchiveField("replay_case_id", True, "Selected replay case, or none."),
            RetroConsoleArchiveField("first_mismatch", True, "First mismatch/assertion, or none for smoke pass."),
            RetroConsoleArchiveField("failure_class", True, "I34-S05 failure class, or none for smoke pass."),
            RetroConsoleArchiveField("interactive_corpus", True, "I32-S05 corpus command, version, or path."),
            RetroConsoleArchiveField("interactive_corpus_status", True, "I32-S05 corpus status."),
            RetroConsoleArchiveField("pass_fail_result", True, "retro_console_smoke_pass or failure_observed."),
            RetroConsoleArchiveField("archive_result", True, "retro_console_pass_archived or retro_console_blocker_archived."),
            RetroConsoleArchiveField("retro_console_handoff_policy", True, "60K handoff policy with 138K path status."),
            RetroConsoleArchiveField("primary_138k_claim", True, "Must be no."),
            RetroConsoleArchiveField("primary_138k_path_status", True, "Must keep I31/I32 active on Tang Mega 138K."),
            RetroConsoleArchiveField("residual_blockers", True, "none, or named blockers."),
            RetroConsoleArchiveField("filed_issues", True, "none, or issue IDs/links for blockers."),
            RetroConsoleArchiveField("retest_steps", True, "Concrete commands or steps for rerunning board evidence."),
        ),
        result_rules=(
            RetroConsoleArchiveResultRule(
                ARCHIVE_RESULT_PASS,
                "I34-S04 observed with board_result=retro_console_smoke_pass",
                "replay_status=not_required and replay_classification=not_required_retro_console_smoke_pass",
                "residual_blockers=none and filed_issues=none",
            ),
            RetroConsoleArchiveResultRule(
                ARCHIVE_RESULT_BLOCKER,
                "I34-S04 observed with board_result=failure_observed",
                "I34-S05 replay_status=classified, replay_case_id, failure_class, and first_mismatch are required",
                "residual_blockers, filed_issues, and retest_steps must be concrete",
            ),
        ),
        link_fields=(
            "identity_evidence",
            "constraints_evidence",
            "gowin_evidence",
            "gowin_report_bundle",
            "bitstream_path",
            "programming_evidence",
            "programming_log",
            "reset_observation",
            "led_evidence",
            "uart_log",
            "decoded_status_packet",
            "interactive_corpus",
        ),
        retest_commands=(
            fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
            fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
            fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
            fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL,
            fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_TOOL,
            fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL,
        ),
        blockers=(
            "I34-S01, I34-S02, I34-S03, and I34-S04 evidence must be linked before archive closure",
            "Retro Console smoke-pass archives must carry no residual blockers",
            "Retro Console failure archives must link classified I34-S05 replay evidence",
            "I32-S05 interactive corpus readiness must remain linked for future monitor use",
            "the archive must explicitly keep the Tang Mega Dock with 138K SOM I31/I32 path active",
        ),
    )


def retro_console_archive_template(
    profile: RetroConsoleArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_archive_profile()
    retest_steps = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"identity_evidence={fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix()}",
            "identity_status=alternate_target_verified",
            f"constraints_evidence={fpga_retro_console_constraints.RETRO_CONSOLE_CONSTRAINT_EVIDENCE.as_posix()}",
            f"constraints_status={fpga_retro_console_constraints.CONSTRAINT_CONFIRMED_STATUS}",
            f"gowin_evidence={fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE.as_posix()}",
            f"gowin_status={fpga_retro_console_gowin.GOWIN_PASS}",
            "gowin_report_bundle=build/fpga/tang_60k_retro_console/first_test/impl",
            "bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            f"programming_evidence={fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE.as_posix()}",
            f"programming_status={fpga_retro_console_programming.OBSERVED}",
            f"programming_board_result={fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS}",
            "programming_log=docs/implementation/evidence/i34_s04_programming.log",
            "reset_observation=docs/implementation/evidence/i34_s04_reset_release.txt",
            "led_evidence=docs/implementation/evidence/i34_s04_leds.mp4",
            "uart_log=docs/implementation/evidence/i34_s04_uart.log",
            "decoded_status_packet=docs/implementation/evidence/i34_s04_status_packet.json",
            "probe_capture=none",
            f"replay_classification={REPLAY_NOT_REQUIRED_PASS}",
            f"replay_status={REPLAY_NOT_REQUIRED}",
            "replay_case_id=none",
            "first_mismatch=none",
            "failure_class=none",
            f"interactive_corpus={fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL}",
            f"interactive_corpus_status={fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_STATUS}",
            f"pass_fail_result={fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS}",
            f"archive_result={ARCHIVE_RESULT_PASS}",
            f"retro_console_handoff_policy={HANDOFF_60K_READY}",
            "primary_138k_claim=no",
            f"primary_138k_path_status={PRIMARY_138K_ACTIVE}",
            "residual_blockers=none",
            "filed_issues=none",
            f"retest_steps={retest_steps}",
            "",
        )
    )


def parse_retro_console_archive(text: str) -> RetroConsoleArchiveRecord:
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
    return RetroConsoleArchiveRecord(fields)


def audit_retro_console_archive(
    record: RetroConsoleArchiveRecord,
    *,
    programming_audit: fpga_retro_console_programming.RetroConsoleProgrammingAudit | None = None,
    replay_audit: fpga_retro_console_replay.RetroConsoleReplayAudit | None = None,
    evidence_path: str = "<inline>",
    profile: RetroConsoleArchiveProfile | None = None,
) -> RetroConsoleArchiveAudit:
    if profile is None:
        profile = fpga_retro_console_archive_profile()

    programming_status = (
        programming_audit.status if programming_audit is not None else record.value("programming_status")
    )
    replay_status = replay_audit.status if replay_audit is not None else record.value("replay_status")

    if programming_audit is not None and not programming_audit.passed:
        return _audit(
            BLOCKED,
            "Retro Console archive is blocked until I34-S04 programming evidence is observed.",
            evidence_path,
            programming_status,
            replay_status,
            record,
            actions=("complete I34-S04 programming observations first",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I34-S06")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_retro_console_60k")

    link_issues = _link_issues(record, profile)
    result_issues = _result_issues(record, profile, programming_audit, replay_audit)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            INVALID,
            "Retro Console archive evidence is incomplete or malformed.",
            evidence_path,
            programming_status,
            replay_status,
            record,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I34-S06 fields", "rerun the archive audit"),
        )
    if link_issues:
        return _audit(
            INVALID,
            "Retro Console archive links are incomplete or malformed.",
            evidence_path,
            programming_status,
            replay_status,
            record,
            link_issues=tuple(link_issues),
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete Retro Console evidence links",),
        )
    if result_issues:
        return _audit(
            INVALID,
            "Retro Console archive result fields are inconsistent.",
            evidence_path,
            programming_status,
            replay_status,
            record,
            result_issues=tuple(result_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix pass/failure, replay, archive result, or handoff policy consistency",),
        )
    if blocker_issues:
        return _audit(
            NEEDS_FOLLOWUP,
            "Retro Console archive needs blocker disposition or retest steps.",
            evidence_path,
            programming_status,
            replay_status,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("close or file blockers", "record concrete retest steps"),
        )
    return _audit(
        ARCHIVED,
        "Retro Console 60K pass or blocker disposition is archived.",
        evidence_path,
        programming_status,
        replay_status,
        record,
        actions=("hand archive to release traceability while keeping I31/I32 on the 138K path active",),
    )


def load_retro_console_archive_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    programming_evidence_path: Path | None = None,
    replay_evidence_path: Path | None = None,
) -> RetroConsoleArchiveAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_archive_profile()
    relative_path = evidence_path or profile.evidence_path
    programming_audit = fpga_retro_console_programming.load_retro_console_programming_audit(
        root,
        programming_evidence_path,
    )
    replay_audit = fpga_retro_console_replay.load_retro_console_replay_audit(
        root,
        replay_evidence_path,
    )
    path = root / relative_path
    if not path.exists():
        return _audit(
            BLOCKED,
            "No Retro Console pass/blocker archive has been captured yet.",
            relative_path.as_posix(),
            programming_audit.status,
            replay_audit.status,
            RetroConsoleArchiveRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link scan, constraints, reports, bitstream, programming, LED/UART/probe, replay, blockers, and 138K handoff policy",
            ),
        )
    try:
        record = parse_retro_console_archive(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            INVALID,
            "Retro Console archive evidence could not be parsed.",
            relative_path.as_posix(),
            programming_audit.status,
            replay_audit.status,
            RetroConsoleArchiveRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value archive record", "rerun the I34-S06 audit"),
        )
    return audit_retro_console_archive(
        record,
        programming_audit=programming_audit,
        replay_audit=replay_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_retro_console_archive_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_retro_console_archive_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_retro_console_archive(
    profile: RetroConsoleArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_archive_profile()
    lines = [
        "# FPGA Retro Console Archive",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Board: `{profile.board}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        "",
        "## Gates",
        "",
        f"- `{profile.identity_gate}`",
        f"- `{profile.constraints_gate}`",
        f"- `{profile.gowin_gate}`",
        f"- `{profile.programming_gate}`",
        f"- `{profile.replay_gate}`",
        f"- `{profile.interactive_corpus_gate}`",
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


def validate_fpga_retro_console_archive(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_archive_profile()
    issues: list[str] = []

    if profile.story != FPGA_RETRO_CONSOLE_ARCHIVE_STORY:
        issues.append(f"Retro Console archive story must be {FPGA_RETRO_CONSOLE_ARCHIVE_STORY}")
    if profile.status != RETRO_CONSOLE_ARCHIVE_STATUS:
        issues.append("Retro Console archive status must stay blocked until pass or classified blocker evidence exists")
    if profile.board != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD:
        issues.append("Retro Console archive board must match I34-S01")
    if profile.identity_gate != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL:
        issues.append("Retro Console archive must depend on I34-S01")
    if profile.constraints_gate != fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL:
        issues.append("Retro Console archive must depend on I34-S02")
    if profile.gowin_gate != fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL:
        issues.append("Retro Console archive must depend on I34-S03")
    if profile.programming_gate != fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL:
        issues.append("Retro Console archive must depend on I34-S04")
    if profile.replay_gate != fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_TOOL:
        issues.append("Retro Console archive must depend on I34-S05")
    if profile.interactive_corpus_gate != fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL:
        issues.append("Retro Console archive must depend on I32-S05")

    for check_issues in (
        fpga_retro_console_identity.validate_fpga_retro_console_identity(root),
        fpga_retro_console_constraints.validate_fpga_retro_console_constraints(root),
        fpga_retro_console_gowin.validate_fpga_retro_console_gowin(root),
        fpga_retro_console_programming.validate_fpga_retro_console_programming(root),
        fpga_retro_console_replay.validate_fpga_retro_console_replay(root),
        fpga_interactive_corpus.validate_fpga_interactive_corpus(root),
    ):
        issues.extend(check_issues)

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "board",
        "identity_evidence",
        "identity_status",
        "constraints_evidence",
        "constraints_status",
        "gowin_evidence",
        "gowin_status",
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
        "failure_class",
        "interactive_corpus",
        "interactive_corpus_status",
        "pass_fail_result",
        "archive_result",
        "retro_console_handoff_policy",
        "primary_138k_claim",
        "primary_138k_path_status",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing Retro Console archive field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for archive_result in (ARCHIVE_RESULT_PASS, ARCHIVE_RESULT_BLOCKER):
        if archive_result not in profile.archive_results:
            issues.append(f"missing Retro Console archive result {archive_result}")
    for handoff in (HANDOFF_138K_ACTIVE, HANDOFF_60K_READY):
        if handoff not in profile.handoff_policies:
            issues.append(f"missing Retro Console handoff policy {handoff}")

    pass_record = parse_retro_console_archive(
        retro_console_archive_template()
        .replace("archived_at=", "archived_at=2026-05-12T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_retro_console_archive(
        pass_record,
        programming_audit=_programming(fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS),
    ).passed:
        issues.append("complete Retro Console pass archive record must audit as archived")

    blocker_record = parse_retro_console_archive(_blocker_archive_text())
    if not audit_retro_console_archive(
        blocker_record,
        programming_audit=_programming(fpga_retro_console_programming.BOARD_RESULT_FAILURE),
        replay_audit=_replay(fpga_retro_console_replay.CLASSIFIED),
    ).passed:
        issues.append("complete Retro Console blocker archive must audit as archived")

    missing_issue = parse_retro_console_archive(
        _blocker_archive_text().replace("filed_issues=CPU-234", "filed_issues=none")
    )
    if audit_retro_console_archive(missing_issue).status != NEEDS_FOLLOWUP:
        issues.append("Retro Console blocker archive without filed issues must require follow-up")

    default_audit = load_retro_console_archive_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default Retro Console archive audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_RETRO_CONSOLE_ARCHIVE_DOC)
    for token in (
        "Story: I34-S06",
        FPGA_RETRO_CONSOLE_ARCHIVE_TOOL,
        FPGA_RETRO_CONSOLE_ARCHIVE_EVIDENCE.as_posix(),
        fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
        fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL,
        fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_TOOL,
        fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL,
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
        "failure_class",
        "retro_console_pass_archived",
        "retro_console_blocker_archived",
        "primary_138k_claim=no",
        HANDOFF_138K_ACTIVE,
        PRIMARY_138K_ACTIVE,
        "I31/I32",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RETRO_CONSOLE_ARCHIVE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"Retro Console archive objects are not JSON serializable: {exc}")

    return tuple(issues)


def _link_issues(
    record: RetroConsoleArchiveRecord,
    profile: RetroConsoleArchiveProfile,
) -> list[str]:
    issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            issues.append(f"{field} must link concrete evidence")

    expected_values = {
        "board": profile.board,
        "identity_status": "alternate_target_verified",
        "constraints_status": fpga_retro_console_constraints.CONSTRAINT_CONFIRMED_STATUS,
        "gowin_status": fpga_retro_console_gowin.GOWIN_PASS,
        "programming_status": fpga_retro_console_programming.OBSERVED,
        "interactive_corpus_status": fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_STATUS,
        "primary_138k_claim": "no",
        "primary_138k_path_status": PRIMARY_138K_ACTIVE,
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            issues.append(f"{field} must be {expected}")

    story_tokens = {
        "identity_evidence": "i34_s01",
        "constraints_evidence": "i34_s02",
        "gowin_evidence": "i34_s03",
        "programming_evidence": "i34_s04",
    }
    for field, token in story_tokens.items():
        value = record.value(field)
        if value and token not in value.lower():
            story = token.upper().replace("_", "-")
            issues.append(f"{field} must reference {story} evidence")

    for field in ("gowin_report_bundle", "bitstream_path"):
        value = record.value(field)
        if value and "tang_60k_retro_console" not in value:
            issues.append(f"{field} must reference the Retro Console 60K build root")
        if value and "tang_mega_138k" in value:
            issues.append(f"{field} must not reference the Tang Mega 138K build root")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        issues.append("bitstream_path must name a .fs file")
    if record.value("bitstream_sha256") and not _is_sha256_hex(record.value("bitstream_sha256")):
        issues.append("bitstream_sha256 must be a 64-character hex digest")

    replay_classification = record.value("replay_classification")
    if (
        replay_classification
        and replay_classification != REPLAY_NOT_REQUIRED_PASS
        and "i34_s05" not in replay_classification.lower()
    ):
        issues.append("replay_classification must reference I34-S05 evidence or be not_required_retro_console_smoke_pass")
    interactive = record.value("interactive_corpus")
    if interactive and not _mentions_story_or_tool(interactive, "i32_s05", "fpga_interactive_corpus", "fpga-interactive-program-corpus"):
        issues.append("interactive_corpus must name the I32-S05 corpus command or artifact")
    handoff = record.value("retro_console_handoff_policy")
    if handoff and handoff not in profile.handoff_policies:
        issues.append("retro_console_handoff_policy must name an approved Retro Console handoff policy")
    return issues


def _result_issues(
    record: RetroConsoleArchiveRecord,
    profile: RetroConsoleArchiveProfile,
    programming_audit: fpga_retro_console_programming.RetroConsoleProgrammingAudit | None,
    replay_audit: fpga_retro_console_replay.RetroConsoleReplayAudit | None,
) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    pass_fail_result = record.value("pass_fail_result")
    programming_board_result = record.value("programming_board_result")

    if archive_result not in profile.archive_results:
        issues.append("archive_result must be retro_console_pass_archived or retro_console_blocker_archived")
    if pass_fail_result not in {
        fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS,
        fpga_retro_console_programming.BOARD_RESULT_FAILURE,
    }:
        issues.append("pass_fail_result must be retro_console_smoke_pass or failure_observed")
    if programming_audit is not None and programming_board_result != programming_audit.board_result:
        issues.append("programming_board_result must match I34-S04 audit")
    if programming_board_result and programming_board_result != pass_fail_result:
        issues.append("programming_board_result must match pass_fail_result")

    if archive_result == ARCHIVE_RESULT_PASS:
        if pass_fail_result != fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS:
            issues.append("retro_console_pass_archived requires pass_fail_result=retro_console_smoke_pass")
        if record.value("replay_status") != REPLAY_NOT_REQUIRED:
            issues.append("retro_console_pass_archived requires replay_status=not_required")
        if record.value("replay_classification") != REPLAY_NOT_REQUIRED_PASS:
            issues.append("retro_console_pass_archived requires replay_classification=not_required_retro_console_smoke_pass")
        if not _is_empty_disposition(record.value("replay_case_id")):
            issues.append("retro_console_pass_archived requires replay_case_id=none")
        if not _is_empty_disposition(record.value("first_mismatch")):
            issues.append("retro_console_pass_archived requires first_mismatch=none")
        if not _is_empty_disposition(record.value("failure_class")):
            issues.append("retro_console_pass_archived requires failure_class=none")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if pass_fail_result != fpga_retro_console_programming.BOARD_RESULT_FAILURE:
            issues.append("retro_console_blocker_archived requires pass_fail_result=failure_observed")
        if record.value("replay_status") != fpga_retro_console_replay.CLASSIFIED:
            issues.append("retro_console_blocker_archived requires replay_status=classified")
        if replay_audit is not None and not replay_audit.passed:
            issues.append("retro_console_blocker_archived requires a passing I34-S05 replay audit")
        if _is_empty_disposition(record.value("replay_classification")):
            issues.append("retro_console_blocker_archived requires replay_classification")
        if _is_empty_disposition(record.value("replay_case_id")):
            issues.append("retro_console_blocker_archived requires replay_case_id")
        if _is_empty_disposition(record.value("first_mismatch")):
            issues.append("retro_console_blocker_archived requires first_mismatch")
        if _is_empty_disposition(record.value("failure_class")):
            issues.append("retro_console_blocker_archived requires failure_class")
    return issues


def _blocker_issues(record: RetroConsoleArchiveRecord) -> list[str]:
    issues: list[str] = []
    archive_result = record.value("archive_result")
    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_steps = record.value("retest_steps")

    if _is_empty_disposition(retest_steps):
        issues.append("retest_steps must be concrete")
    if archive_result == ARCHIVE_RESULT_PASS:
        if not _is_empty_disposition(residual_blockers):
            issues.append("retro_console_pass_archived requires residual_blockers=none")
        if not _is_empty_disposition(filed_issues):
            issues.append("retro_console_pass_archived requires filed_issues=none")
    elif archive_result == ARCHIVE_RESULT_BLOCKER:
        if _is_empty_disposition(residual_blockers):
            issues.append("retro_console_blocker_archived requires residual_blockers")
        if _is_empty_disposition(filed_issues):
            issues.append("retro_console_blocker_archived requires filed_issues")
    return issues


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    programming_status: str,
    replay_status: str,
    record: RetroConsoleArchiveRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    result_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> RetroConsoleArchiveAudit:
    return RetroConsoleArchiveAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        programming_status=programming_status,
        replay_status=replay_status,
        archive_result=record.value("archive_result"),
        pass_fail_result=record.value("pass_fail_result"),
        handoff_policy=record.value("retro_console_handoff_policy"),
        missing_fields=missing_fields,
        link_issues=link_issues,
        result_issues=result_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _blocker_archive_text() -> str:
    return (
        retro_console_archive_template()
        .replace("archived_at=", "archived_at=2026-05-12T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("programming_board_result=retro_console_smoke_pass", "programming_board_result=failure_observed")
        .replace(f"replay_classification={REPLAY_NOT_REQUIRED_PASS}", f"replay_classification={fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_EVIDENCE.as_posix()}")
        .replace("replay_status=not_required", "replay_status=classified")
        .replace("replay_case_id=none", "replay_case_id=core.control_trap.sys_iret")
        .replace("first_mismatch=none", "first_mismatch=core.control_trap.sys_iret packet 5: pc_cell mismatch")
        .replace("failure_class=none", "failure_class=trap")
        .replace("pass_fail_result=retro_console_smoke_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=retro_console_pass_archived", "archive_result=retro_console_blocker_archived")
        .replace(f"retro_console_handoff_policy={HANDOFF_60K_READY}", f"retro_console_handoff_policy={HANDOFF_138K_ACTIVE}")
        .replace("residual_blockers=none", "residual_blockers=trap_replay_mismatch")
        .replace("filed_issues=none", "filed_issues=CPU-234")
    )


def _programming(
    board_result: str,
) -> fpga_retro_console_programming.RetroConsoleProgrammingAudit:
    return fpga_retro_console_programming.RetroConsoleProgrammingAudit(
        status=fpga_retro_console_programming.OBSERVED,
        message="observed",
        evidence_path=fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE.as_posix(),
        gowin_status=fpga_retro_console_gowin.GOWIN_PASS,
        board_result=board_result,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=(),
    )


def _replay(status: str) -> fpga_retro_console_replay.RetroConsoleReplayAudit:
    return fpga_retro_console_replay.RetroConsoleReplayAudit(
        status=status,
        message=status,
        evidence_path=fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_EVIDENCE.as_posix(),
        programming_status=fpga_retro_console_programming.OBSERVED,
        debug_evidence_status="accepted",
        board_result=fpga_retro_console_programming.BOARD_RESULT_FAILURE,
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
        REPLAY_NOT_REQUIRED_PASS,
    }


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _mentions_story_or_tool(value: str, *tokens: str) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in tokens)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

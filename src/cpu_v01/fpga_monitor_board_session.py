"""Physical interactive FPGA monitor board-session evidence gate.

Owner stories:
- I32-S06: capture an interactive multi-program board session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_debug_status,
    fpga_first_pass_archive,
    fpga_first_test,
    fpga_interactive_corpus,
    fpga_monitor_session,
    fpga_monitor_snapshot,
)


JsonValue = Any

FPGA_MONITOR_BOARD_SESSION_STORY = "I32-S06"
FPGA_MONITOR_BOARD_SESSION_DOC = Path(
    "docs/implementation/fpga-monitor-board-session.md"
)
FPGA_MONITOR_BOARD_SESSION_TOOL = "python tools\\fpga_monitor_board_session.py --check"
FPGA_MONITOR_BOARD_SESSION_EVIDENCE = Path(
    "docs/implementation/evidence/i32_s06_monitor_board_session.txt"
)
FPGA_MONITOR_BOARD_SESSION_STATUS = "blocked_until_physical_monitor_session"

SESSION_ACCEPTED = "accepted"
SESSION_BLOCKED = "blocked"
SESSION_INVALID = "invalid"
SESSION_NEEDS_FOLLOWUP = "needs_followup"

RESULT_MULTI_PROGRAM_PASS = "multi_program_session_passed"
RESULT_CLASSIFIED_BLOCKER = "classified_board_session_blocker"


@dataclass(frozen=True)
class MonitorBoardSessionField:
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
class MonitorBoardSessionProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    first_pass_archive_gate: str
    monitor_session_gate: str
    interactive_corpus_gate: str
    snapshot_gate: str
    required_program_count: int
    accepted_results: tuple[str, ...]
    required_fields: tuple[MonitorBoardSessionField, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "board": self.board,
            "first_pass_archive_gate": self.first_pass_archive_gate,
            "monitor_session_gate": self.monitor_session_gate,
            "interactive_corpus_gate": self.interactive_corpus_gate,
            "snapshot_gate": self.snapshot_gate,
            "required_program_count": self.required_program_count,
            "accepted_results": list(self.accepted_results),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class MonitorBoardSessionRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class MonitorBoardSessionAudit:
    status: str
    message: str
    evidence_path: str
    board: str
    first_pass_archive_status: str
    loaded_case_ids: tuple[str, ...]
    pass_fail_result: str
    missing_fields: tuple[str, ...]
    case_issues: tuple[str, ...]
    link_issues: tuple[str, ...]
    packet_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == SESSION_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "board": self.board,
            "first_pass_archive_status": self.first_pass_archive_status,
            "loaded_case_ids": list(self.loaded_case_ids),
            "pass_fail_result": self.pass_fail_result,
            "missing_fields": list(self.missing_fields),
            "case_issues": list(self.case_issues),
            "link_issues": list(self.link_issues),
            "packet_issues": list(self.packet_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_monitor_board_session_profile() -> MonitorBoardSessionProfile:
    return MonitorBoardSessionProfile(
        story=FPGA_MONITOR_BOARD_SESSION_STORY,
        status=FPGA_MONITOR_BOARD_SESSION_STATUS,
        evidence_path=FPGA_MONITOR_BOARD_SESSION_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        first_pass_archive_gate=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        monitor_session_gate=fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        interactive_corpus_gate=fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL,
        snapshot_gate=fpga_monitor_snapshot.FPGA_MONITOR_SNAPSHOT_TOOL,
        required_program_count=2,
        accepted_results=(RESULT_MULTI_PROGRAM_PASS, RESULT_CLASSIFIED_BLOCKER),
        required_fields=(
            MonitorBoardSessionField("story", True, "Must be I32-S06."),
            MonitorBoardSessionField("captured_at", True, "Local board-session timestamp."),
            MonitorBoardSessionField("repository_commit", True, "Repository commit used for the board run."),
            MonitorBoardSessionField("board", True, "Physical board name."),
            MonitorBoardSessionField("first_pass_archive", True, "I31-S05 pass/blocker archive path."),
            MonitorBoardSessionField("first_pass_archive_status", True, "I31-S05 audit status."),
            MonitorBoardSessionField("monitor_transport", True, "UART/JTAG transport and COM or probe endpoint."),
            MonitorBoardSessionField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            MonitorBoardSessionField("interactive_corpus", True, "I32-S05 corpus version, path, or command output."),
            MonitorBoardSessionField("loaded_case_ids", True, "Comma-separated I32-S05 case IDs loaded in order."),
            MonitorBoardSessionField("program_run_count", True, "Number of loaded and started program runs."),
            MonitorBoardSessionField("loader_connect_log", True, "Monitor connect/HELLO transcript path."),
            MonitorBoardSessionField("command_transcript", True, "Full monitor command transcript path."),
            MonitorBoardSessionField("status_packet_hex", True, "Final or failure I25-S01 32-byte packet hex."),
            MonitorBoardSessionField("uart_capture", True, "UART/status capture path."),
            MonitorBoardSessionField("snapshot_evidence", True, "I32-S04 debug snapshot path."),
            MonitorBoardSessionField("replay_command", True, "Nearest replay or snapshot reproduction command."),
            MonitorBoardSessionField("pass_fail_result", True, "multi_program_session_passed or classified_board_session_blocker."),
            MonitorBoardSessionField("residual_blockers", True, "none, or named blockers for classified sessions."),
            MonitorBoardSessionField("evidence_archive", True, "Directory or bundle containing raw board captures."),
            MonitorBoardSessionField("retest_steps", True, "Concrete commands or steps to reproduce the session."),
        ),
        blockers=(
            "I31-S05 must archive a first-pass result or a classified blocker before this board-session evidence can close",
            "physical monitor transport evidence must include connect, load, run, status, and snapshot captures",
            "at least two I32-S05 cases must be loaded and started in one bounded session",
            "classified blockers require residual blockers and a replay command",
        ),
        handoffs=(
            "I33-S01 consumes accepted board-session evidence for the release-candidate checklist",
            "I33-S02 consumes the evidence archive and retest steps for full regression capture",
            "I32 follow-up work can reuse residual blockers and replay commands for board-debug sessions",
        ),
    )


def board_session_template(profile: MonitorBoardSessionProfile | None = None) -> str:
    if profile is None:
        profile = fpga_monitor_board_session_profile()
    packet_hex = fpga_debug_status.encode_debug_status_packet(
        fpga_debug_status.example_debug_status_packet()
    ).hex()
    return "\n".join(
        (
            f"story={profile.story}",
            "captured_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"first_pass_archive={fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix()}",
            "first_pass_archive_status=archived",
            "monitor_transport=UART COMx 8N1 or JTAG monitor transport",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "interactive_corpus=python tools\\fpga_interactive_corpus.py --check",
            "loaded_case_ids=scalar_control.call_return,trap_syscall.sys_pause_iret",
            "program_run_count=2",
            "loader_connect_log=docs/implementation/evidence/i32_s06_loader_connect.log",
            "command_transcript=docs/implementation/evidence/i32_s06_monitor_commands.log",
            f"status_packet_hex={packet_hex}",
            "uart_capture=docs/implementation/evidence/i32_s06_uart.log",
            "snapshot_evidence=docs/implementation/evidence/i32_s06_snapshot.json",
            "replay_command=python tools\\fpga_monitor_snapshot.py --snapshot-json",
            f"pass_fail_result={RESULT_MULTI_PROGRAM_PASS}",
            "residual_blockers=none",
            "evidence_archive=docs/implementation/evidence/i32_s06_board_session",
            "retest_steps=python tools\\fpga_monitor_profile.py --check ; python tools\\fpga_interactive_corpus.py --check",
            "",
        )
    )


def parse_board_session_record(text: str) -> MonitorBoardSessionRecord:
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
    return MonitorBoardSessionRecord(fields)


def audit_board_session_record(
    record: MonitorBoardSessionRecord,
    *,
    evidence_path: str = "<inline>",
    profile: MonitorBoardSessionProfile | None = None,
) -> MonitorBoardSessionAudit:
    if profile is None:
        profile = fpga_monitor_board_session_profile()

    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I32-S06")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_first_test_target")

    case_ids = _split_case_ids(record.value("loaded_case_ids"))
    case_issues = _case_issues(case_ids, record, profile)
    link_issues = _link_issues(record)
    packet_issues = _packet_issues(record.value("status_packet_hex"))
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            SESSION_INVALID,
            "Interactive board-session evidence is incomplete or malformed.",
            evidence_path,
            record,
            case_ids,
            missing_fields=tuple(missing_fields),
            case_issues=tuple(case_issues),
            link_issues=tuple(link_issues),
            packet_issues=tuple(packet_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I32-S06 evidence fields", "rerun the board-session audit"),
        )
    if case_issues or link_issues or packet_issues:
        return _audit(
            SESSION_INVALID,
            "Interactive board-session evidence is internally inconsistent.",
            evidence_path,
            record,
            case_ids,
            case_issues=tuple(case_issues),
            link_issues=tuple(link_issues),
            packet_issues=tuple(packet_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix case IDs, evidence links, hashes, or status-packet data",),
        )
    if blocker_issues:
        return _audit(
            SESSION_NEEDS_FOLLOWUP,
            "Interactive board-session evidence needs blocker disposition.",
            evidence_path,
            record,
            case_ids,
            blocker_issues=tuple(blocker_issues),
            actions=("close or file residual blockers", "record concrete replay and retest steps"),
        )
    return _audit(
        SESSION_ACCEPTED,
        "Interactive multi-program board session or classified blocker is accepted.",
        evidence_path,
        record,
        case_ids,
        actions=("hand accepted session evidence to I33-S01 release-candidate checklist",),
    )


def load_board_session_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> MonitorBoardSessionAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_board_session_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            SESSION_BLOCKED,
            "No physical interactive board-session evidence has been captured yet.",
            relative_path.as_posix(),
            MonitorBoardSessionRecord({}),
            (),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the board-session template after the FPGA run",
                "capture connect, load, run, status, UART, snapshot, replay, blockers, archive, and retest evidence",
            ),
        )
    try:
        record = parse_board_session_record(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            SESSION_INVALID,
            "Interactive board-session evidence could not be parsed.",
            relative_path.as_posix(),
            MonitorBoardSessionRecord({}),
            (),
            missing_fields=(str(exc),),
            actions=("fix the key=value board-session record", "rerun the I32-S06 audit"),
        )
    return audit_board_session_record(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_monitor_board_session_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_monitor_board_session_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_monitor_board_session(
    profile: MonitorBoardSessionProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_monitor_board_session_profile()
    lines = [
        "# FPGA Monitor Board Session",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        "",
        "## Gates",
        "",
        f"- `{profile.first_pass_archive_gate}`",
        f"- `{profile.monitor_session_gate}`",
        f"- `{profile.interactive_corpus_gate}`",
        f"- `{profile.snapshot_gate}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_monitor_board_session(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_board_session_profile()
    issues: list[str] = []

    if profile.story != FPGA_MONITOR_BOARD_SESSION_STORY:
        issues.append(f"monitor board-session story must be {FPGA_MONITOR_BOARD_SESSION_STORY}")
    if profile.status != FPGA_MONITOR_BOARD_SESSION_STATUS:
        issues.append("monitor board-session status must stay blocked until physical evidence exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("monitor board-session board must match the first-test target")
    if profile.first_pass_archive_gate != fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL:
        issues.append("monitor board-session must depend on I31-S05")
    if profile.monitor_session_gate != fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL:
        issues.append("monitor board-session must depend on I32-S03")
    if profile.interactive_corpus_gate != fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL:
        issues.append("monitor board-session must depend on I32-S05")
    if profile.snapshot_gate != fpga_monitor_snapshot.FPGA_MONITOR_SNAPSHOT_TOOL:
        issues.append("monitor board-session must depend on I32-S04")

    issues.extend(fpga_first_pass_archive.validate_fpga_first_pass_archive(root))
    issues.extend(fpga_monitor_session.validate_fpga_monitor_session(root))
    issues.extend(fpga_interactive_corpus.validate_fpga_interactive_corpus(root))
    issues.extend(fpga_monitor_snapshot.validate_fpga_monitor_snapshot(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "captured_at",
        "repository_commit",
        "board",
        "first_pass_archive",
        "first_pass_archive_status",
        "monitor_transport",
        "bitstream_sha256",
        "interactive_corpus",
        "loaded_case_ids",
        "program_run_count",
        "loader_connect_log",
        "command_transcript",
        "status_packet_hex",
        "uart_capture",
        "snapshot_evidence",
        "replay_command",
        "pass_fail_result",
        "residual_blockers",
        "evidence_archive",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing monitor board-session field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    template = board_session_template(profile)
    for token in (
        "story=I32-S06",
        f"board={fpga_first_test.TARGET_BOARD_NAME}",
        "first_pass_archive_status=archived",
        "loaded_case_ids=scalar_control.call_return,trap_syscall.sys_pause_iret",
        "program_run_count=2",
        "status_packet_hex=",
        f"pass_fail_result={RESULT_MULTI_PROGRAM_PASS}",
        "residual_blockers=none",
    ):
        if token not in template:
            issues.append(f"board-session template missing {token}")

    accepted = audit_board_session_record(
        parse_board_session_record(
            template
            .replace("captured_at=", "captured_at=2026-05-11T15:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
        )
    )
    if not accepted.accepted:
        issues.append("complete monitor board-session pass record must audit as accepted")

    blocker = audit_board_session_record(parse_board_session_record(_classified_blocker_text()))
    if not blocker.accepted:
        issues.append("complete classified monitor board-session blocker must audit as accepted")

    followup = audit_board_session_record(
        parse_board_session_record(
            _classified_blocker_text().replace(
                "residual_blockers=trap_syscall_uart_timeout",
                "residual_blockers=none",
            )
        )
    )
    if followup.status != SESSION_NEEDS_FOLLOWUP:
        issues.append("classified board-session blocker without residual blockers must need follow-up")

    default_audit = load_board_session_audit(root)
    if default_audit.status != SESSION_BLOCKED:
        issues.append("default monitor board-session audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_MONITOR_BOARD_SESSION_DOC)
    for token in (
        "Story: I32-S06",
        FPGA_MONITOR_BOARD_SESSION_TOOL,
        FPGA_MONITOR_BOARD_SESSION_EVIDENCE.as_posix(),
        fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        fpga_interactive_corpus.FPGA_INTERACTIVE_CORPUS_TOOL,
        fpga_monitor_snapshot.FPGA_MONITOR_SNAPSHOT_TOOL,
        "loaded_case_ids",
        "program_run_count",
        "status_packet_hex",
        "uart_capture",
        "snapshot_evidence",
        "replay_command",
        RESULT_MULTI_PROGRAM_PASS,
        RESULT_CLASSIFIED_BLOCKER,
        "residual_blockers",
        "evidence_archive",
        "I33-S01",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MONITOR_BOARD_SESSION_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"monitor board-session objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: MonitorBoardSessionRecord,
    loaded_case_ids: tuple[str, ...],
    *,
    missing_fields: tuple[str, ...] = (),
    case_issues: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    packet_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> MonitorBoardSessionAudit:
    return MonitorBoardSessionAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        board=record.value("board"),
        first_pass_archive_status=record.value("first_pass_archive_status"),
        loaded_case_ids=loaded_case_ids,
        pass_fail_result=record.value("pass_fail_result"),
        missing_fields=missing_fields,
        case_issues=case_issues,
        link_issues=link_issues,
        packet_issues=packet_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _case_issues(
    case_ids: tuple[str, ...],
    record: MonitorBoardSessionRecord,
    profile: MonitorBoardSessionProfile,
) -> list[str]:
    issues: list[str] = []
    corpus = fpga_interactive_corpus.fpga_interactive_corpus_profile()
    if len(case_ids) < profile.required_program_count:
        issues.append("loaded_case_ids must contain at least two cases")
    if len(case_ids) != len(set(case_ids)):
        issues.append("loaded_case_ids must be unique")
    categories: set[str] = set()
    for case_id in case_ids:
        try:
            categories.add(corpus.case_by_id(case_id).category)
        except KeyError:
            issues.append(f"unknown I32-S05 case {case_id}")
    if len(categories) < 2:
        issues.append("loaded_case_ids must cover at least two interactive categories")
    if record.value("program_run_count"):
        try:
            program_run_count = int(record.value("program_run_count"))
        except ValueError:
            issues.append("program_run_count must be numeric")
        else:
            if program_run_count != len(case_ids):
                issues.append("program_run_count must match loaded_case_ids")
            if program_run_count < profile.required_program_count:
                issues.append("program_run_count must be at least two")
    return issues


def _link_issues(record: MonitorBoardSessionRecord) -> list[str]:
    issues: list[str] = []
    if record.value("first_pass_archive") and "i31_s05" not in record.value("first_pass_archive").lower():
        issues.append("first_pass_archive must reference I31-S05 evidence")
    if record.value("first_pass_archive_status") not in {"archived", "needs_followup"}:
        issues.append("first_pass_archive_status must be archived or needs_followup")
    if record.value("bitstream_sha256") and not _is_sha256_hex(record.value("bitstream_sha256")):
        issues.append("bitstream_sha256 must be a 64-character hex digest")
    if record.value("interactive_corpus") and "fpga_interactive_corpus.py" not in record.value("interactive_corpus"):
        issues.append("interactive_corpus must name the I32-S05 corpus command or artifact")
    for field in (
        "loader_connect_log",
        "command_transcript",
        "uart_capture",
        "snapshot_evidence",
        "evidence_archive",
        "retest_steps",
    ):
        if _empty(record.value(field)):
            issues.append(f"{field} must be concrete")
    if record.value("snapshot_evidence") and "i32_s06" not in record.value("snapshot_evidence").lower():
        issues.append("snapshot_evidence must be archived with I32-S06 board-session captures")
    if record.value("replay_command") and not (
        "fpga_monitor_snapshot.py" in record.value("replay_command")
        or "verilator_diff_harness.py --case-id" in record.value("replay_command")
    ):
        issues.append("replay_command must name the snapshot tool or Verilator replay case")
    return issues


def _packet_issues(packet_hex: str) -> list[str]:
    if not packet_hex:
        return []
    try:
        payload = bytes.fromhex(packet_hex)
    except ValueError:
        return ["status_packet_hex must be hex"]
    try:
        fpga_debug_status.decode_debug_status_packet(payload)
    except ValueError as exc:
        return [f"status_packet_hex does not decode as I25-S01 packet: {exc}"]
    return []


def _blocker_issues(record: MonitorBoardSessionRecord) -> list[str]:
    result = record.value("pass_fail_result")
    blockers = record.value("residual_blockers")
    issues: list[str] = []
    if result not in {RESULT_MULTI_PROGRAM_PASS, RESULT_CLASSIFIED_BLOCKER}:
        issues.append("pass_fail_result must be an accepted I32-S06 result")
    if result == RESULT_MULTI_PROGRAM_PASS:
        if not _empty(blockers):
            issues.append("multi_program_session_passed requires residual_blockers=none")
        if record.value("first_pass_archive_status") != "archived":
            issues.append("multi_program_session_passed requires first_pass_archive_status=archived")
    if result == RESULT_CLASSIFIED_BLOCKER:
        if _empty(blockers):
            issues.append("classified_board_session_blocker requires residual_blockers")
        if "verilator_diff_harness.py --case-id" not in record.value("replay_command"):
            issues.append("classified_board_session_blocker requires a Verilator replay command")
    return issues


def _split_case_ids(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.replace(";", ",").split(",") if part.strip())


def _classified_blocker_text() -> str:
    packet = fpga_debug_status.DebugStatusPacket(
        flags=fpga_debug_status.debug_status_flag_mask(
            "reset_observed",
            "fault_valid",
            "fail_led",
            "heartbeat",
        ),
        slot=0,
        pass_fail_state=3,
        pc_cell=0x1008,
        retire_count=4,
        fault_code=2,
        trap_cause=2,
        build_id=0x2501C0DE,
        sequence=7,
    )
    return (
        board_session_template()
        .replace("captured_at=", "captured_at=2026-05-11T15:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("first_pass_archive_status=archived", "first_pass_archive_status=needs_followup")
        .replace("status_packet_hex=" + fpga_debug_status.encode_debug_status_packet(fpga_debug_status.example_debug_status_packet()).hex(), "status_packet_hex=" + fpga_debug_status.encode_debug_status_packet(packet).hex())
        .replace(f"pass_fail_result={RESULT_MULTI_PROGRAM_PASS}", f"pass_fail_result={RESULT_CLASSIFIED_BLOCKER}")
        .replace("residual_blockers=none", "residual_blockers=trap_syscall_uart_timeout")
        .replace(
            "replay_command=python tools\\fpga_monitor_snapshot.py --snapshot-json",
            "replay_command=python tools\\verilator_diff_harness.py --case-id traps.sys_iret_return",
        )
    )


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

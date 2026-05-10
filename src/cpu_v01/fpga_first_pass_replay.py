"""First-pass FPGA failure replay classification gate.

Owner stories:
- I31-S04: replay and classify first-pass board failure captures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_debug_evidence,
    fpga_debug_status,
    fpga_first_pass_programming,
    fpga_replay_mapper,
    instructions,
)


JsonValue = Any

FPGA_FIRST_PASS_REPLAY_STORY = "I31-S04"
FPGA_FIRST_PASS_REPLAY_DOC = Path("docs/implementation/fpga-first-pass-replay.md")
FPGA_FIRST_PASS_REPLAY_TOOL = "python tools\\fpga_first_pass_replay.py --check"
FPGA_FIRST_PASS_REPLAY_EVIDENCE = Path(
    "docs/implementation/evidence/i31_s04_failure_replay_classification.txt"
)
FIRST_PASS_REPLAY_PROFILE_STATUS = "blocked_until_failure_capture"

CLASSIFIED = "classified"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_CAPTURE = "needs_capture"
NEEDS_TRIAGE = "needs_triage"

FAILURE_CLASSES = (
    "clock_reset",
    "memory",
    "firmware",
    "trap",
    "translation",
    "loader",
    "board_integration",
)
CAPTURE_SOURCES = ("uart", "gao_ila", "both")


@dataclass(frozen=True)
class FirstPassReplayField:
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
class FailureClassificationRule:
    failure_class: str
    status_signature: str
    replay_requirement: str
    disposition: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "failure_class": self.failure_class,
            "status_signature": self.status_signature,
            "replay_requirement": self.replay_requirement,
            "disposition": self.disposition,
        }


@dataclass(frozen=True)
class FirstPassReplayProfile:
    story: str
    status: str
    evidence_path: Path
    programming_gate: str
    replay_mapper_gate: str
    debug_evidence_gate: str
    failure_classes: tuple[str, ...]
    capture_sources: tuple[str, ...]
    required_fields: tuple[FirstPassReplayField, ...]
    classification_rules: tuple[FailureClassificationRule, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> FirstPassReplayField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "programming_gate": self.programming_gate,
            "replay_mapper_gate": self.replay_mapper_gate,
            "debug_evidence_gate": self.debug_evidence_gate,
            "failure_classes": list(self.failure_classes),
            "capture_sources": list(self.capture_sources),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "classification_rules": [rule.as_dict() for rule in self.classification_rules],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstPassReplayRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstPassReplayAudit:
    status: str
    message: str
    evidence_path: str
    programming_status: str
    debug_evidence_status: str
    failure_class: str
    replay_case_id: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    capture_issues: tuple[str, ...]
    packet_issues: tuple[str, ...]
    replay_issues: tuple[str, ...]
    classification_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == CLASSIFIED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "programming_status": self.programming_status,
            "debug_evidence_status": self.debug_evidence_status,
            "failure_class": self.failure_class,
            "replay_case_id": self.replay_case_id,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "capture_issues": list(self.capture_issues),
            "packet_issues": list(self.packet_issues),
            "replay_issues": list(self.replay_issues),
            "classification_issues": list(self.classification_issues),
            "actions": list(self.actions),
        }


def fpga_first_pass_replay_profile() -> FirstPassReplayProfile:
    return FirstPassReplayProfile(
        story=FPGA_FIRST_PASS_REPLAY_STORY,
        status=FIRST_PASS_REPLAY_PROFILE_STATUS,
        evidence_path=FPGA_FIRST_PASS_REPLAY_EVIDENCE,
        programming_gate=fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
        replay_mapper_gate=fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        debug_evidence_gate=fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        failure_classes=FAILURE_CLASSES,
        capture_sources=CAPTURE_SOURCES,
        required_fields=(
            FirstPassReplayField("story", True, "Must be I31-S04."),
            FirstPassReplayField("classified_at", True, "Local classification timestamp."),
            FirstPassReplayField("repository_commit", True, "Repository commit used for replay triage."),
            FirstPassReplayField("first_pass_programming", True, "I31-S03 programming evidence path."),
            FirstPassReplayField("programming_board_result", True, "Must be failure_observed."),
            FirstPassReplayField("capture_source", True, "uart, gao_ila, or both."),
            FirstPassReplayField("uart_status_packet_hex", True, "Captured 32-byte I25-S01 status packet hex."),
            FirstPassReplayField("uart_log", True, "UART capture log path, or none for probe-only captures."),
            FirstPassReplayField("decoded_status_packet", True, "Decoded packet record path or transcript."),
            FirstPassReplayField("probe_capture", True, "GAO/ILA/probe capture path, or none."),
            FirstPassReplayField("replay_mapping", True, "I25-S04 mapping output path or transcript."),
            FirstPassReplayField("replay_case_id", True, "Selected Verilator replay case ID."),
            FirstPassReplayField("replay_command", True, "Selected Verilator replay command."),
            FirstPassReplayField("observed_trace", True, "Observed retire trace path, or none."),
            FirstPassReplayField("first_mismatch", True, "First mismatch or assertion diagnostic."),
            FirstPassReplayField("failure_class", True, "One of the I31-S04 failure classes."),
            FirstPassReplayField("classification_rationale", True, "Why the packet and replay imply the class."),
            FirstPassReplayField("debug_evidence", True, "I25-S05 debug evidence record path."),
            FirstPassReplayField("debug_evidence_status", True, "I25-S05 audit status, normally accepted."),
            FirstPassReplayField("followup_issue", True, "Filed issue/blocker ID for the classified failure."),
            FirstPassReplayField("retest_commands", True, "Commands to rerun programming, mapping, evidence, and replay."),
        ),
        classification_rules=(
            FailureClassificationRule(
                "clock_reset",
                "reset asserted, idle, or no retire progress",
                "map to core.shell.reset_idle or preserve a reset/probe assertion",
                "file clock/reset, PLL, pin, or reset-synchronizer blocker",
            ),
            FailureClassificationRule(
                "memory",
                "access, align, capability, tag, bounds, permission, or local-store fault",
                "map to cap/mem or fetch/decode replay cases and preserve first mismatch",
                "file memory adapter, tag sidecar, or data path blocker",
            ),
            FailureClassificationRule(
                "firmware",
                "failed packet without a memory, trap, or translation cause",
                "map to the nearest scalar/control replay and compare firmware expectation",
                "file ROM/image/pass-condition blocker",
            ),
            FailureClassificationRule(
                "trap",
                "syscall, return-stack, divide, debug, or control-trap cause",
                "map to control/trap or scalar fault replay cases",
                "file trap-frame, return-stack, or exception-path blocker",
            ),
            FailureClassificationRule(
                "translation",
                "page-fault cause or MMU/TLB replay selection",
                "map to core.mmu_tlb.translation_sfence and preserve first mismatch",
                "file translation, SATP/ASID, or TLB blocker",
            ),
            FailureClassificationRule(
                "loader",
                "captured status implicates image load, entry handoff, or loader data",
                "preserve replay plus loader/image evidence",
                "file loader, image identity, or handoff blocker",
            ),
            FailureClassificationRule(
                "board_integration",
                "capture implicates board pins, LEDs, UART/probe wiring, or constraints",
                "preserve replay/probe evidence even when core replay is clean",
                "file board integration blocker with exact recapture steps",
            ),
        ),
        retest_commands=(
            fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
            fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
            fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
            "python tools\\verilator_diff_harness.py --case-id <case_id>",
        ),
        blockers=(
            "I31-S03 must report failure_observed before I31-S04 can close",
            "the captured status packet must select a concrete I25-S04 replay case",
            "first_mismatch or assertion output must be preserved for the selected replay",
            "I25-S05 debug evidence must be accepted before failure classification closes",
            "classified failures must have a filed issue or blocker and concrete retest commands",
        ),
    )


def example_failure_status_packet() -> fpga_debug_status.DebugStatusPacket:
    return fpga_debug_status.DebugStatusPacket(
        flags=fpga_debug_status.debug_status_flag_mask(
            "reset_observed",
            "retire_valid",
            "fault_valid",
            "fail_led",
            "heartbeat",
        ),
        slot=0,
        pass_fail_state=3,
        pc_cell=0x1008,
        retire_count=4,
        fault_code=int(instructions.ExceptionCause.SYSCALL_TRAP),
        trap_cause=int(instructions.ExceptionCause.SYSCALL_TRAP),
        build_id=0x2501C0DE,
        sequence=4,
    )


def first_pass_replay_template(profile: FirstPassReplayProfile | None = None) -> str:
    if profile is None:
        profile = fpga_first_pass_replay_profile()
    packet = example_failure_status_packet()
    packet_hex = fpga_debug_status.encode_debug_status_packet(packet).hex()
    mapping = fpga_replay_mapper.map_debug_status_packet(packet, packet_hex=packet_hex)
    selected = mapping.candidates[0]
    retest_commands = " ; ".join(profile.retest_commands).replace(
        "<case_id>",
        selected.case_id,
    )
    observed_trace = fpga_replay_mapper.OBSERVED_TRACE_TEMPLATE.format(
        sequence=packet.sequence,
    )
    return "\n".join(
        (
            f"story={profile.story}",
            "classified_at=",
            "repository_commit=",
            f"first_pass_programming={fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix()}",
            f"programming_board_result={fpga_first_pass_programming.BOARD_RESULT_FAILURE}",
            "capture_source=uart",
            f"uart_status_packet_hex={packet_hex}",
            "uart_log=docs/implementation/evidence/i31_s04_uart_failure.log",
            "decoded_status_packet=docs/implementation/evidence/i31_s04_status_packet.json",
            "probe_capture=none",
            "replay_mapping=docs/implementation/evidence/i31_s04_replay_mapping.json",
            f"replay_case_id={selected.case_id}",
            f"replay_command={selected.replay_command}",
            f"observed_trace={observed_trace}",
            f"first_mismatch={selected.case_id} packet {packet.sequence}: pc_cell mismatch",
            "failure_class=trap",
            "classification_rationale=syscall trap captured in first-pass status packet",
            f"debug_evidence={fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_PATH.as_posix()}",
            f"debug_evidence_status={fpga_debug_evidence.DEBUG_EVIDENCE_ACCEPTED}",
            "followup_issue=CPU-123",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_first_pass_replay(text: str) -> FirstPassReplayRecord:
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
    return FirstPassReplayRecord(fields)


def audit_first_pass_replay(
    record: FirstPassReplayRecord,
    *,
    programming_audit: fpga_first_pass_programming.FirstPassProgrammingAudit | None = None,
    debug_evidence_audit: fpga_debug_evidence.DebugEvidenceAudit | None = None,
    evidence_path: str = "<inline>",
    profile: FirstPassReplayProfile | None = None,
) -> FirstPassReplayAudit:
    if profile is None:
        profile = fpga_first_pass_replay_profile()

    programming_status = programming_audit.status if programming_audit is not None else "not_checked"
    debug_status = debug_evidence_audit.status if debug_evidence_audit is not None else record.value("debug_evidence_status")

    if programming_audit is not None and not programming_audit.passed:
        return FirstPassReplayAudit(
            status=BLOCKED,
            message="First-pass replay is blocked until I31-S03 programming evidence is observed.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=record.value("failure_class"),
            replay_case_id=record.value("replay_case_id"),
            missing_fields=(),
            link_issues=(),
            capture_issues=(),
            packet_issues=(),
            replay_issues=(),
            classification_issues=(),
            actions=("complete I31-S03 programming evidence first",),
        )
    if (
        programming_audit is not None
        and programming_audit.board_result != fpga_first_pass_programming.BOARD_RESULT_FAILURE
    ):
        return FirstPassReplayAudit(
            status=BLOCKED,
            message="No first-pass board failure capture is available to replay.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=record.value("failure_class"),
            replay_case_id=record.value("replay_case_id"),
            missing_fields=(),
            link_issues=(),
            capture_issues=(),
            packet_issues=(),
            replay_issues=(),
            classification_issues=(),
            actions=("archive the first_pass result through I31-S05 instead",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I31-S04")

    link_issues: list[str] = []
    if record.value("first_pass_programming") and "i31_s03" not in record.value("first_pass_programming").lower():
        link_issues.append("first_pass_programming must reference I31-S03 evidence")
    if record.value("debug_evidence") and not _mentions_story_or_tool(
        record.value("debug_evidence"),
        "i25_s05",
        "fpga_debug_evidence",
        "debug_evidence",
    ):
        link_issues.append("debug_evidence must reference I25-S05 debug evidence")

    capture_issues: list[str] = []
    if record.value("programming_board_result") != fpga_first_pass_programming.BOARD_RESULT_FAILURE:
        capture_issues.append("programming_board_result must be failure_observed")
    capture_source = record.value("capture_source")
    if capture_source and capture_source not in profile.capture_sources:
        capture_issues.append("capture_source must be uart, gao_ila, or both")
    if capture_source in {"uart", "both"} and _is_empty_disposition(record.value("uart_log")):
        capture_issues.append("UART captures require uart_log")
    if capture_source in {"gao_ila", "both"} and _is_empty_disposition(record.value("probe_capture")):
        capture_issues.append("GAO/ILA captures require probe_capture")

    packet, packet_issues = _decode_packet(record.value("uart_status_packet_hex"))
    mapping: fpga_replay_mapper.ReplayMapping | None = None
    candidate_ids: tuple[str, ...] = ()
    if packet is not None:
        packet_hex = "".join(record.value("uart_status_packet_hex").split())
        mapping = fpga_replay_mapper.map_debug_status_packet(packet, packet_hex=packet_hex)
        candidate_ids = tuple(candidate.case_id for candidate in mapping.candidates)

    replay_issues: list[str] = []
    replay_case_id = record.value("replay_case_id")
    if _is_empty_disposition(record.value("replay_mapping")):
        replay_issues.append("replay_mapping must link I25-S04 mapping output")
    if _is_empty_disposition(replay_case_id):
        replay_issues.append("replay_case_id must select a replay case")
    elif candidate_ids and replay_case_id not in candidate_ids:
        replay_issues.append("replay_case_id must be selected from the I25-S04 ranked candidates")
    replay_command = record.value("replay_command")
    if replay_case_id and f"verilator_diff_harness.py --case-id {replay_case_id}" not in replay_command:
        replay_issues.append("replay_command must run the selected Verilator differential case")
    if _is_empty_disposition(record.value("first_mismatch")):
        replay_issues.append("first_mismatch must preserve first mismatch or assertion diagnostics")
    retest_commands = record.value("retest_commands")
    for command in (profile.programming_gate, profile.replay_mapper_gate, profile.debug_evidence_gate):
        if retest_commands and command not in retest_commands:
            replay_issues.append(f"retest_commands must include {command}")
    if replay_case_id and retest_commands and f"--case-id {replay_case_id}" not in retest_commands:
        replay_issues.append("retest_commands must include the selected replay case")

    classification_issues: list[str] = []
    failure_class = record.value("failure_class")
    if failure_class not in profile.failure_classes:
        classification_issues.append("failure_class must be clock_reset, memory, firmware, trap, translation, loader, or board_integration")
    elif packet is not None and mapping is not None and not _class_matches_packet(
        failure_class,
        packet,
        mapping,
        replay_case_id,
        record.value("classification_rationale"),
    ):
        classification_issues.append("failure_class must match the decoded packet, replay mapping, or recorded rationale")
    if _is_empty_disposition(record.value("classification_rationale")):
        classification_issues.append("classification_rationale must explain the selected failure class")
    if record.value("debug_evidence_status") != fpga_debug_evidence.DEBUG_EVIDENCE_ACCEPTED:
        classification_issues.append("debug_evidence_status must be accepted")
    if debug_evidence_audit is not None and not debug_evidence_audit.passed:
        if debug_evidence_audit.status == fpga_debug_evidence.DEBUG_EVIDENCE_NEEDS_CAPTURE:
            capture_issues.append("I25-S05 debug evidence still needs capture")
        elif debug_evidence_audit.status == fpga_debug_evidence.DEBUG_EVIDENCE_INVALID:
            link_issues.append("I25-S05 debug evidence is invalid")
        else:
            classification_issues.append("I25-S05 debug evidence has not accepted the failure triage")
    if _is_empty_disposition(record.value("followup_issue")):
        classification_issues.append("classified failures require a followup_issue")

    if missing_fields:
        return FirstPassReplayAudit(
            status=INVALID,
            message="First-pass failure replay evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=failure_class,
            replay_case_id=replay_case_id,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            capture_issues=tuple(capture_issues),
            packet_issues=tuple(packet_issues),
            replay_issues=tuple(replay_issues),
            classification_issues=tuple(classification_issues),
            actions=("complete all required I31-S04 fields", "rerun the failure replay audit"),
        )
    if link_issues or packet_issues:
        return FirstPassReplayAudit(
            status=INVALID,
            message="First-pass failure replay links or status packet are invalid.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=failure_class,
            replay_case_id=replay_case_id,
            missing_fields=(),
            link_issues=tuple(link_issues),
            capture_issues=tuple(capture_issues),
            packet_issues=tuple(packet_issues),
            replay_issues=tuple(replay_issues),
            classification_issues=tuple(classification_issues),
            actions=("fix evidence links, I25-S05 status, or the captured packet",),
        )
    if capture_issues:
        return FirstPassReplayAudit(
            status=NEEDS_CAPTURE,
            message="First-pass failure replay needs more complete board capture evidence.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=failure_class,
            replay_case_id=replay_case_id,
            missing_fields=(),
            link_issues=(),
            capture_issues=tuple(capture_issues),
            packet_issues=(),
            replay_issues=tuple(replay_issues),
            classification_issues=tuple(classification_issues),
            actions=("capture UART or GAO/ILA status evidence", "rerun I31-S03 and I25-S05"),
        )
    if replay_issues or classification_issues:
        return FirstPassReplayAudit(
            status=NEEDS_TRIAGE,
            message="First-pass failure replay exists but classification or replay disposition is incomplete.",
            evidence_path=evidence_path,
            programming_status=programming_status,
            debug_evidence_status=debug_status,
            failure_class=failure_class,
            replay_case_id=replay_case_id,
            missing_fields=(),
            link_issues=(),
            capture_issues=(),
            packet_issues=(),
            replay_issues=tuple(replay_issues),
            classification_issues=tuple(classification_issues),
            actions=("select the replay case", "preserve first_mismatch", "record the failure class and issue"),
        )
    return FirstPassReplayAudit(
        status=CLASSIFIED,
        message="First-pass board failure capture has replay mapping and classification.",
        evidence_path=evidence_path,
        programming_status=programming_status,
        debug_evidence_status=debug_status,
        failure_class=failure_class,
        replay_case_id=replay_case_id,
        missing_fields=(),
        link_issues=(),
        capture_issues=(),
        packet_issues=(),
        replay_issues=(),
        classification_issues=(),
        actions=("hand the classified failure or closure disposition to I31-S05",),
    )


def load_first_pass_replay_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    programming_evidence_path: Path | None = None,
    debug_evidence_path: Path | None = None,
) -> FirstPassReplayAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_replay_profile()
    relative_path = evidence_path or profile.evidence_path
    programming_audit = fpga_first_pass_programming.load_first_pass_programming_audit(
        root,
        programming_evidence_path,
    )
    debug_evidence_audit = fpga_debug_evidence.load_debug_evidence_audit(
        root,
        debug_evidence_path,
    )
    path = root / relative_path
    if not path.exists():
        return FirstPassReplayAudit(
            status=BLOCKED,
            message="No first-pass failure replay classification has been captured yet.",
            evidence_path=relative_path.as_posix(),
            programming_status=programming_audit.status,
            debug_evidence_status=debug_evidence_audit.status,
            failure_class="",
            replay_case_id="",
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            capture_issues=(),
            packet_issues=(),
            replay_issues=(),
            classification_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the I31-S04 template",
                "capture a failure packet from I31-S03",
                "run I25-S04 replay mapping and I25-S05 debug evidence audit",
            ),
        )
    try:
        record = parse_first_pass_replay(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return FirstPassReplayAudit(
            status=INVALID,
            message="First-pass failure replay evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            programming_status=programming_audit.status,
            debug_evidence_status=debug_evidence_audit.status,
            failure_class="",
            replay_case_id="",
            missing_fields=(str(exc),),
            link_issues=(),
            capture_issues=(),
            packet_issues=(),
            replay_issues=(),
            classification_issues=(),
            actions=("fix the key=value replay classification record", "rerun the I31-S04 audit"),
        )
    return audit_first_pass_replay(
        record,
        programming_audit=programming_audit,
        debug_evidence_audit=debug_evidence_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_first_pass_replay_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_replay_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_replay(
    profile: FirstPassReplayProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_replay_profile()
    lines = [
        "# FPGA First-Pass Failure Replay",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        "",
        "## Gates",
        "",
        f"- `{profile.programming_gate}`",
        f"- `{profile.replay_mapper_gate}`",
        f"- `{profile.debug_evidence_gate}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |")
    lines.extend(["", "## Failure Classes", ""])
    for rule in profile.classification_rules:
        lines.append(f"- `{rule.failure_class}`: {rule.status_signature}; {rule.replay_requirement}.")
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_pass_replay(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_replay_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_REPLAY_STORY:
        issues.append(f"first-pass replay story must be {FPGA_FIRST_PASS_REPLAY_STORY}")
    if profile.status != FIRST_PASS_REPLAY_PROFILE_STATUS:
        issues.append("first-pass replay profile must remain blocked until failure capture exists")
    if profile.programming_gate != fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL:
        issues.append("first-pass replay must depend on I31-S03 programming")
    if profile.replay_mapper_gate != fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL:
        issues.append("first-pass replay must depend on I25-S04 replay mapper")
    if profile.debug_evidence_gate != fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL:
        issues.append("first-pass replay must depend on I25-S05 debug evidence")

    issues.extend(fpga_first_pass_programming.validate_fpga_first_pass_programming(root))
    issues.extend(fpga_replay_mapper.validate_fpga_replay_mapper(root))
    issues.extend(fpga_debug_evidence.validate_fpga_debug_evidence(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "classified_at",
        "repository_commit",
        "first_pass_programming",
        "programming_board_result",
        "capture_source",
        "uart_status_packet_hex",
        "uart_log",
        "decoded_status_packet",
        "probe_capture",
        "replay_mapping",
        "replay_case_id",
        "replay_command",
        "observed_trace",
        "first_mismatch",
        "failure_class",
        "classification_rationale",
        "debug_evidence",
        "debug_evidence_status",
        "followup_issue",
        "retest_commands",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing first-pass replay field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for failure_class in FAILURE_CLASSES:
        if failure_class not in profile.failure_classes:
            issues.append(f"missing first-pass replay failure class {failure_class}")
    for source in CAPTURE_SOURCES:
        if source not in profile.capture_sources:
            issues.append(f"missing first-pass replay capture source {source}")

    programming_failure = _programming_audit(fpga_first_pass_programming.BOARD_RESULT_FAILURE)
    debug_accepted = _debug_evidence_audit(fpga_debug_evidence.DEBUG_EVIDENCE_ACCEPTED)
    complete_record = parse_first_pass_replay(
        first_pass_replay_template()
        .replace("classified_at=", "classified_at=2026-05-10T13:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    complete_audit = audit_first_pass_replay(
        complete_record,
        programming_audit=programming_failure,
        debug_evidence_audit=debug_accepted,
    )
    if not complete_audit.passed:
        issues.append("complete first-pass failure replay evidence must audit as classified")

    missing_mismatch = parse_first_pass_replay(
        first_pass_replay_template()
        .replace("classified_at=", "classified_at=2026-05-10T13:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch", "first_mismatch=none")
    )
    if audit_first_pass_replay(missing_mismatch, programming_audit=programming_failure).status != NEEDS_TRIAGE:
        issues.append("missing first_mismatch must require replay triage")

    pass_record = parse_first_pass_replay(
        first_pass_replay_template()
        .replace("classified_at=", "classified_at=2026-05-10T13:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("programming_board_result=failure_observed", "programming_board_result=first_pass")
    )
    if audit_first_pass_replay(pass_record, programming_audit=programming_failure).status != NEEDS_CAPTURE:
        issues.append("first_pass programming result must not close I31-S04 replay classification")

    default_audit = load_first_pass_replay_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default first-pass replay audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_REPLAY_DOC)
    for token in (
        "Story: I31-S04",
        FPGA_FIRST_PASS_REPLAY_TOOL,
        FPGA_FIRST_PASS_REPLAY_EVIDENCE.as_posix(),
        fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_TOOL,
        fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        "uart_status_packet_hex",
        "replay_case_id",
        "replay_command",
        "observed_trace",
        "first_mismatch",
        "clock_reset",
        "memory",
        "firmware",
        "trap",
        "translation",
        "loader",
        "board_integration",
        "debug_evidence_status",
        "followup_issue",
        "I31-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_REPLAY_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass replay objects are not JSON serializable: {exc}")

    return tuple(issues)


def _decode_packet(value: str) -> tuple[fpga_debug_status.DebugStatusPacket | None, list[str]]:
    if not value:
        return None, []
    compact = "".join(value.split())
    if len(compact) != 64:
        return None, ["uart_status_packet_hex must encode exactly 32 bytes"]
    try:
        payload = bytes.fromhex(compact)
    except ValueError:
        return None, ["uart_status_packet_hex must be hexadecimal"]
    try:
        return fpga_debug_status.decode_debug_status_packet(payload), []
    except ValueError as exc:
        return None, [f"uart_status_packet_hex did not decode as I25-S01 packet: {exc}"]


def _class_matches_packet(
    failure_class: str,
    packet: fpga_debug_status.DebugStatusPacket,
    mapping: fpga_replay_mapper.ReplayMapping,
    replay_case_id: str,
    rationale: str,
) -> bool:
    flag_names = set(mapping.flag_names)
    cause = _dominant_cause(packet)
    rationale_lower = rationale.lower()

    if failure_class == "clock_reset":
        return (
            replay_case_id == "core.shell.reset_idle"
            or "reset_asserted" in flag_names
            or ("core_idle" in flag_names and packet.retire_count == 0)
        )
    if failure_class == "memory":
        return cause in {
            instructions.ExceptionCause.ALIGN_FAULT,
            instructions.ExceptionCause.ACCESS_FAULT,
            instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
            instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
            instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            instructions.ExceptionCause.CAPABILITY_LOCAL_STORE_FAULT,
        } or "cap_mem" in replay_case_id or "memory" in rationale_lower
    if failure_class == "firmware":
        return cause in {
            instructions.ExceptionCause.ILLEGAL_INSTRUCTION,
            instructions.ExceptionCause.BREAKPOINT,
            instructions.ExceptionCause.RESERVED_CSR_FAULT,
            instructions.ExceptionCause.ILLEGAL_CSR_READ,
            instructions.ExceptionCause.ILLEGAL_CSR_WRITE,
        } or "firmware" in rationale_lower or "rom" in rationale_lower
    if failure_class == "trap":
        return cause in {
            instructions.ExceptionCause.SYSCALL_TRAP,
            instructions.ExceptionCause.RETURN_STACK_UNDERFLOW,
            instructions.ExceptionCause.RETURN_STACK_OVERFLOW,
            instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
            instructions.ExceptionCause.DIVIDE_BY_ZERO,
            instructions.ExceptionCause.DEBUG_HALT,
        } or "control_trap" in replay_case_id or "trap" in rationale_lower
    if failure_class == "translation":
        return cause == instructions.ExceptionCause.PAGE_FAULT or "mmu_tlb" in replay_case_id
    if failure_class == "loader":
        return any(token in rationale_lower for token in ("loader", "image", "handoff", "entry"))
    if failure_class == "board_integration":
        return any(
            token in rationale_lower
            for token in ("board", "pin", "led", "uart", "probe", "constraint", "package")
        )
    return False


def _dominant_cause(
    packet: fpga_debug_status.DebugStatusPacket,
) -> instructions.ExceptionCause | None:
    raw = packet.trap_cause or packet.fault_code
    if raw == 0:
        return None
    try:
        return instructions.ExceptionCause(raw)
    except ValueError:
        return None


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
    }


def _mentions_story_or_tool(value: str, *tokens: str) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in tokens)


def _programming_audit(board_result: str) -> fpga_first_pass_programming.FirstPassProgrammingAudit:
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


def _debug_evidence_audit(status: str) -> fpga_debug_evidence.DebugEvidenceAudit:
    return fpga_debug_evidence.DebugEvidenceAudit(
        status=status,
        message=status,
        evidence_path=fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_PATH.as_posix(),
        archive_status="archived",
        missing_fields=(),
        capture_issues=(),
        classification_issues=(),
        replay_issues=(),
        actions=(),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""FPGA debug-evidence gate for first-board bring-up.

Owner stories:
- I25-S05: require UART or ILA evidence for diagnosable FPGA failures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_first_board_archive,
    fpga_first_test,
    fpga_probe_bundles,
    fpga_replay_mapper,
    fpga_uart_status,
)


JsonValue = Any

FPGA_DEBUG_EVIDENCE_STORY = "I25-S05"
FPGA_DEBUG_EVIDENCE_DOC = Path("docs/implementation/fpga-debug-evidence-gate.md")
FPGA_DEBUG_EVIDENCE_TOOL = "python tools\\fpga_debug_evidence.py --check"
FPGA_DEBUG_EVIDENCE_PATH = Path("docs/implementation/evidence/i25_s05_debug_evidence.txt")
DEBUG_EVIDENCE_ACCEPTED = "accepted"
DEBUG_EVIDENCE_BLOCKED = "blocked"
DEBUG_EVIDENCE_INVALID = "invalid"
DEBUG_EVIDENCE_NEEDS_CAPTURE = "needs_capture"
DEBUG_EVIDENCE_NEEDS_TRIAGE = "needs_triage"


@dataclass(frozen=True)
class DebugEvidenceField:
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
class DebugEvidenceTriageRule:
    symptom_class: str
    required_capture: str
    replay_requirement: str
    distinguishes: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "symptom_class": self.symptom_class,
            "required_capture": self.required_capture,
            "replay_requirement": self.replay_requirement,
            "distinguishes": self.distinguishes,
        }


@dataclass(frozen=True)
class FpgaDebugEvidenceProfile:
    story: str
    board: str
    evidence_path: Path
    archive_gate: str
    uart_gate: str
    probe_gate: str
    replay_gate: str
    required_fields: tuple[DebugEvidenceField, ...]
    triage_rules: tuple[DebugEvidenceTriageRule, ...]
    nontrivial_failure_classes: tuple[str, ...]
    capture_sources: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "evidence_path": self.evidence_path.as_posix(),
            "archive_gate": self.archive_gate,
            "uart_gate": self.uart_gate,
            "probe_gate": self.probe_gate,
            "replay_gate": self.replay_gate,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "triage_rules": [rule.as_dict() for rule in self.triage_rules],
            "nontrivial_failure_classes": list(self.nontrivial_failure_classes),
            "capture_sources": list(self.capture_sources),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class DebugEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class DebugEvidenceAudit:
    status: str
    message: str
    evidence_path: str
    archive_status: str
    missing_fields: tuple[str, ...]
    capture_issues: tuple[str, ...]
    classification_issues: tuple[str, ...]
    replay_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == DEBUG_EVIDENCE_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "archive_status": self.archive_status,
            "missing_fields": list(self.missing_fields),
            "capture_issues": list(self.capture_issues),
            "classification_issues": list(self.classification_issues),
            "replay_issues": list(self.replay_issues),
            "actions": list(self.actions),
        }


def fpga_debug_evidence_profile() -> FpgaDebugEvidenceProfile:
    return FpgaDebugEvidenceProfile(
        story=FPGA_DEBUG_EVIDENCE_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        evidence_path=FPGA_DEBUG_EVIDENCE_PATH,
        archive_gate=fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
        uart_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        probe_gate=fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        replay_gate=fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        required_fields=(
            DebugEvidenceField("story", True, "Must be I25-S05."),
            DebugEvidenceField("board", True, "Physical board name."),
            DebugEvidenceField("captured_at", True, "Local date/time of debug capture."),
            DebugEvidenceField("first_board_archive", True, "I24-S05 archive or failure archive record."),
            DebugEvidenceField("board_result", True, "first_pass or observed failure result."),
            DebugEvidenceField("symptom_class", True, "clock_reset, firmware, memory, trap, translation, external, pass, or unknown."),
            DebugEvidenceField("evidence_source", True, "uart, gao_ila, both, led_only, or none."),
            DebugEvidenceField("uart_packet_hex", True, "Captured I25-S01 packet hex, or none when unavailable."),
            DebugEvidenceField("uart_log", True, "UART capture log path, or none."),
            DebugEvidenceField("probe_capture", True, "GAO/ILA capture path, or none."),
            DebugEvidenceField("probe_setup", True, "GAO/ILA setup or signal-list path, or none."),
            DebugEvidenceField("replay_mapping", True, "I25-S04 mapping output path, or none for pass/clock-only cases."),
            DebugEvidenceField("replay_command", True, "Selected Verilator replay command, or none."),
            DebugEvidenceField("first_mismatch", True, "Harness first-mismatch line, assertion output, or none."),
            DebugEvidenceField("clock_reset_diagnosis", True, "clock/reset diagnosis or not_applicable."),
            DebugEvidenceField("firmware_diagnosis", True, "firmware diagnosis or not_applicable."),
            DebugEvidenceField("memory_diagnosis", True, "memory diagnosis or not_applicable."),
            DebugEvidenceField("trap_diagnosis", True, "trap diagnosis or not_applicable."),
            DebugEvidenceField("translation_diagnosis", True, "translation diagnosis or not_applicable."),
            DebugEvidenceField("followup_issue", True, "none or filed issue/link."),
            DebugEvidenceField("retest_steps", True, "none or concrete retest steps."),
        ),
        triage_rules=(
            DebugEvidenceTriageRule(
                "clock_reset",
                "reset observation plus LED/probe clock evidence; UART may be unavailable",
                "replay optional until clock/reset is alive",
                "separates pin, reset synchronizer, and clocking failures from CPU execution",
            ),
            DebugEvidenceTriageRule(
                "firmware",
                "UART packet or GAO/ILA status capture",
                "I25-S04 replay mapping and selected Verilator command",
                "separates ROM/image/pass-condition failures from memory and trap failures",
            ),
            DebugEvidenceTriageRule(
                "memory",
                "UART packet plus GAO/ILA memory_handshake capture when available",
                "I25-S04 replay mapping to cap/mem or fetch/decode cases",
                "separates memory adapter stalls from core execution faults",
            ),
            DebugEvidenceTriageRule(
                "trap",
                "UART packet or GAO/ILA status_packet capture with fault/trap fields",
                "I25-S04 replay mapping to control/trap cases",
                "separates trap-frame or return-stack failures from translation faults",
            ),
            DebugEvidenceTriageRule(
                "translation",
                "UART packet or GAO/ILA status_packet capture with page-fault evidence",
                "I25-S04 replay mapping to MMU/TLB cases",
                "separates address-translation failures from memory adapter failures",
            ),
        ),
        nontrivial_failure_classes=("firmware", "memory", "trap", "translation", "unknown"),
        capture_sources=("uart", "gao_ila", "both", "led_only", "none"),
        blockers=(
            "I24-S05 first-board archive must exist before debug evidence can close",
            "nontrivial failures require UART or GAO/ILA evidence, not only LED state",
            "firmware, memory, trap, and translation failures require replay mapping",
            "clock/reset failures must record why UART or ILA evidence is unavailable or insufficient",
        ),
    )


def debug_evidence_template(profile: FpgaDebugEvidenceProfile | None = None) -> str:
    if profile is None:
        profile = fpga_debug_evidence_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            f"board={profile.board}",
            "captured_at=",
            f"first_board_archive={fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix()}",
            "board_result=",
            "symptom_class=",
            "evidence_source=",
            "uart_packet_hex=none",
            "uart_log=none",
            "probe_capture=none",
            "probe_setup=none",
            "replay_mapping=none",
            "replay_command=none",
            "first_mismatch=none",
            "clock_reset_diagnosis=not_applicable",
            "firmware_diagnosis=not_applicable",
            "memory_diagnosis=not_applicable",
            "trap_diagnosis=not_applicable",
            "translation_diagnosis=not_applicable",
            "followup_issue=none",
            "retest_steps=none",
            "",
        )
    )


def parse_debug_evidence(text: str) -> DebugEvidenceRecord:
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
    return DebugEvidenceRecord(fields)


def audit_debug_evidence(
    record: DebugEvidenceRecord,
    *,
    archive_audit: fpga_first_board_archive.FirstBoardArchiveAudit,
    evidence_path: str = "<inline>",
    profile: FpgaDebugEvidenceProfile | None = None,
) -> DebugEvidenceAudit:
    if profile is None:
        profile = fpga_debug_evidence_profile()

    if archive_audit.status == fpga_first_board_archive.ARCHIVE_BLOCKED:
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_BLOCKED,
            message="Debug evidence is blocked until an I24-S05 first-board archive exists.",
            evidence_path=evidence_path,
            archive_status=archive_audit.status,
            missing_fields=(),
            capture_issues=(),
            classification_issues=(),
            replay_issues=(),
            actions=("complete or file the first-board archive", "do not close debug evidence yet"),
        )

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I25-S05")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    board_result = record.value("board_result").lower()
    symptom_class = record.value("symptom_class").lower()
    evidence_source = record.value("evidence_source").lower()

    classification_issues: list[str] = []
    if symptom_class not in {
        "clock_reset",
        "firmware",
        "memory",
        "trap",
        "translation",
        "external",
        "pass",
        "unknown",
    }:
        classification_issues.append("symptom_class must classify clock_reset, firmware, memory, trap, translation, external, pass, or unknown")
    if evidence_source and evidence_source not in profile.capture_sources:
        classification_issues.append("evidence_source must be uart, gao_ila, both, led_only, or none")
    if board_result == "first_pass" and symptom_class not in {"pass", "external"}:
        classification_issues.append("first_pass board_result must use pass or external symptom_class")
    if board_result != "first_pass" and symptom_class == "pass":
        classification_issues.append("non-pass board_result must not use pass symptom_class")

    capture_issues: list[str] = []
    has_uart = evidence_source in {"uart", "both"} and not _is_empty_disposition(record.value("uart_packet_hex"))
    has_probe = evidence_source in {"gao_ila", "both"} and not _is_empty_disposition(record.value("probe_capture"))
    nontrivial_failure = board_result not in {"", "first_pass"} and symptom_class in profile.nontrivial_failure_classes
    if nontrivial_failure and not (has_uart or has_probe):
        capture_issues.append("nontrivial failures require UART packet hex or GAO/ILA capture evidence")
    if symptom_class == "clock_reset":
        if _is_empty_disposition(record.value("clock_reset_diagnosis")):
            capture_issues.append("clock_reset failures require clock_reset_diagnosis")
        if evidence_source == "none" and _is_empty_disposition(record.value("probe_capture")):
            capture_issues.append("clock_reset failures require reset/clock observation or probe evidence")

    if has_uart and len(record.value("uart_packet_hex").replace(" ", "")) != 64:
        capture_issues.append("uart_packet_hex must be exactly 32 bytes encoded as 64 hex characters")
    if has_probe and _is_empty_disposition(record.value("probe_setup")):
        capture_issues.append("GAO/ILA capture evidence must include probe_setup")

    diagnosis_fields = {
        "clock_reset": "clock_reset_diagnosis",
        "firmware": "firmware_diagnosis",
        "memory": "memory_diagnosis",
        "trap": "trap_diagnosis",
        "translation": "translation_diagnosis",
    }
    diagnosis_field = diagnosis_fields.get(symptom_class)
    if diagnosis_field and _is_empty_disposition(record.value(diagnosis_field)):
        classification_issues.append(f"{symptom_class} failures require {diagnosis_field}")

    replay_issues: list[str] = []
    replay_required = nontrivial_failure or symptom_class in {"firmware", "memory", "trap", "translation"}
    if replay_required:
        if _is_empty_disposition(record.value("replay_mapping")):
            replay_issues.append("nontrivial failures require replay_mapping")
        if "verilator_diff_harness.py --case-id" not in record.value("replay_command"):
            replay_issues.append("replay_command must use the Verilator differential harness case selector")
        if _is_empty_disposition(record.value("first_mismatch")):
            replay_issues.append("nontrivial failures must preserve first_mismatch or assertion diagnostics")

    if record.value("followup_issue").lower() != "none" and _is_empty_disposition(record.value("retest_steps")):
        classification_issues.append("filed followup issues require concrete retest_steps")

    if missing_fields:
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_INVALID,
            message="Debug evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            archive_status=archive_audit.status,
            missing_fields=tuple(missing_fields),
            capture_issues=tuple(capture_issues),
            classification_issues=tuple(classification_issues),
            replay_issues=tuple(replay_issues),
            actions=("complete all required debug evidence fields", "rerun the debug evidence audit"),
        )
    if capture_issues:
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_NEEDS_CAPTURE,
            message="Debug evidence needs UART or GAO/ILA capture before closure.",
            evidence_path=evidence_path,
            archive_status=archive_audit.status,
            missing_fields=(),
            capture_issues=tuple(capture_issues),
            classification_issues=tuple(classification_issues),
            replay_issues=tuple(replay_issues),
            actions=("capture UART status packets or GAO/ILA probes", "rerun I25-S04 replay mapping for failures"),
        )
    if classification_issues or replay_issues:
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_NEEDS_TRIAGE,
            message="Debug evidence exists but triage or replay disposition is incomplete.",
            evidence_path=evidence_path,
            archive_status=archive_audit.status,
            missing_fields=(),
            capture_issues=(),
            classification_issues=tuple(classification_issues),
            replay_issues=tuple(replay_issues),
            actions=("classify the failure domain", "record replay mapping and first-mismatch diagnostics"),
        )
    return DebugEvidenceAudit(
        status=DEBUG_EVIDENCE_ACCEPTED,
        message="Debug evidence gate is complete.",
        evidence_path=evidence_path,
        archive_status=archive_audit.status,
        missing_fields=(),
        capture_issues=(),
        classification_issues=(),
        replay_issues=(),
        actions=("debug evidence can be referenced by downstream FPGA stories",),
    )


def load_debug_evidence_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    archive_path: Path | None = None,
) -> DebugEvidenceAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_debug_evidence_profile()
    relative_path = evidence_path or profile.evidence_path
    archive_audit = fpga_first_board_archive.load_first_board_archive_audit(
        root,
        archive_path,
    )
    path = root / relative_path
    if not path.exists():
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_BLOCKED,
            message="No debug evidence record has been captured yet.",
            evidence_path=relative_path.as_posix(),
            archive_status=archive_audit.status,
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            capture_issues=(),
            classification_issues=(),
            replay_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the debug evidence template",
                "capture UART or GAO/ILA evidence for nontrivial failures",
                "map failure packets with I25-S04 before closure",
            ),
        )
    try:
        record = parse_debug_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return DebugEvidenceAudit(
            status=DEBUG_EVIDENCE_INVALID,
            message="Debug evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            archive_status=archive_audit.status,
            missing_fields=(str(exc),),
            capture_issues=(),
            classification_issues=(),
            replay_issues=(),
            actions=("fix the key=value debug evidence record", "rerun the debug evidence audit"),
        )
    return audit_debug_evidence(
        record,
        archive_audit=archive_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_debug_evidence_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_debug_evidence_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_debug_evidence_profile(
    profile: FpgaDebugEvidenceProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_debug_evidence_profile()
    lines = [
        "# FPGA Debug Evidence Gate",
        "",
        f"Story: {profile.story}",
        "",
        f"Board: `{profile.board}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Archive gate: `{profile.archive_gate}`",
        f"UART gate: `{profile.uart_gate}`",
        f"Probe gate: `{profile.probe_gate}`",
        f"Replay gate: `{profile.replay_gate}`",
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
    lines.extend(["", "## Triage Rules", ""])
    lines.extend(
        f"- `{rule.symptom_class}`: {rule.required_capture}; {rule.replay_requirement}."
        for rule in profile.triage_rules
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_debug_evidence(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_debug_evidence_profile()
    issues: list[str] = []

    if profile.story != FPGA_DEBUG_EVIDENCE_STORY:
        issues.append(f"debug evidence story must be {FPGA_DEBUG_EVIDENCE_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("debug evidence board must match first-test profile")
    if profile.archive_gate != fpga_first_board_archive.FPGA_ARCHIVE_TOOL:
        issues.append("debug evidence archive gate must be I24-S05")
    if profile.uart_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("debug evidence UART gate must be I25-S02")
    if profile.probe_gate != fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL:
        issues.append("debug evidence probe gate must be I25-S03")
    if profile.replay_gate != fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL:
        issues.append("debug evidence replay gate must be I25-S04")

    issues.extend(fpga_first_board_archive.validate_fpga_first_board_archive(root))
    issues.extend(fpga_uart_status.validate_fpga_uart_status(root))
    issues.extend(fpga_probe_bundles.validate_fpga_probe_bundles(root))
    issues.extend(fpga_replay_mapper.validate_fpga_replay_mapper(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "board",
        "captured_at",
        "first_board_archive",
        "board_result",
        "symptom_class",
        "evidence_source",
        "uart_packet_hex",
        "uart_log",
        "probe_capture",
        "probe_setup",
        "replay_mapping",
        "replay_command",
        "first_mismatch",
        "clock_reset_diagnosis",
        "firmware_diagnosis",
        "memory_diagnosis",
        "trap_diagnosis",
        "translation_diagnosis",
        "followup_issue",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing debug evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    rules = {rule.symptom_class: rule for rule in profile.triage_rules}
    for required in ("clock_reset", "firmware", "memory", "trap", "translation"):
        if required not in rules:
            issues.append(f"missing debug evidence triage rule {required}")
    if "unknown" not in profile.nontrivial_failure_classes:
        issues.append("unknown failures must require debug capture")
    for source in ("uart", "gao_ila", "both", "led_only", "none"):
        if source not in profile.capture_sources:
            issues.append(f"missing debug evidence capture source {source}")

    accepted_archive = fpga_first_board_archive.FirstBoardArchiveAudit(
        status=fpga_first_board_archive.ARCHIVE_ARCHIVED,
        message="archived",
        archive_path=fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix(),
        programming_status="passed",
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=(),
    )
    good_failure = parse_debug_evidence(
        "\n".join(
            (
                "story=I25-S05",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "captured_at=2026-05-09T00:00:00",
                f"first_board_archive={fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix()}",
                "board_result=fail_led_asserted",
                "symptom_class=trap",
                "evidence_source=uart",
                "uart_packet_hex=01c5012000100100021000000000000008000000080000dec001250700000000",
                "uart_log=docs/implementation/evidence/i25_s05_uart.log",
                "probe_capture=none",
                "probe_setup=none",
                "replay_mapping=docs/implementation/evidence/i25_s05_replay.json",
                "replay_command=python tools\\verilator_diff_harness.py --case-id core.control_trap.sys_iret",
                "first_mismatch=core.control_trap.sys_iret packet 7: pc_cell mismatch",
                "clock_reset_diagnosis=not_applicable",
                "firmware_diagnosis=not_applicable",
                "memory_diagnosis=not_applicable",
                "trap_diagnosis=syscall trap replay selected",
                "translation_diagnosis=not_applicable",
                "followup_issue=CPU-123",
                "retest_steps=rerun first-test bitstream after trap fix",
            )
        )
    )
    if not audit_debug_evidence(good_failure, archive_audit=accepted_archive).passed:
        issues.append("complete nontrivial debug evidence must audit as accepted")

    weak_failure = parse_debug_evidence(
        debug_evidence_template().replace("board_result=", "board_result=fail_led_asserted")
        .replace("captured_at=", "captured_at=2026-05-09T00:00:00")
        .replace("symptom_class=", "symptom_class=memory")
        .replace("evidence_source=", "evidence_source=led_only")
    )
    if audit_debug_evidence(weak_failure, archive_audit=accepted_archive).status != DEBUG_EVIDENCE_NEEDS_CAPTURE:
        issues.append("nontrivial LED-only failure evidence must require capture")

    default_audit = load_debug_evidence_audit(root)
    if default_audit.status != DEBUG_EVIDENCE_BLOCKED:
        issues.append("default debug evidence audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_DEBUG_EVIDENCE_DOC)
    for token in (
        "Story: I25-S05",
        FPGA_DEBUG_EVIDENCE_TOOL,
        profile.evidence_path.as_posix(),
        fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
        fpga_uart_status.FPGA_UART_STATUS_TOOL,
        fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        "UART or GAO/ILA",
        "clock_reset",
        "firmware",
        "memory",
        "trap",
        "translation",
        "first_mismatch",
        "replay_command",
        "needs_capture",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_DEBUG_EVIDENCE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing", "not_applicable"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""First FPGA external-memory board evidence archive gate.

Owner stories:
- I29-S05: capture first external-memory FPGA evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_ddr_wrapper,
    fpga_external_memory,
    fpga_external_memory_policy,
    fpga_external_memory_tests,
    fpga_first_test,
    fpga_reproducible_build,
)


JsonValue = Any

FPGA_EXTERNAL_MEMORY_EVIDENCE_STORY = "I29-S05"
FPGA_EXTERNAL_MEMORY_EVIDENCE_DOC = Path("docs/implementation/fpga-external-memory-evidence.md")
FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL = "python tools\\fpga_external_memory_evidence.py --check"
FPGA_EXTERNAL_MEMORY_EVIDENCE_PATH = Path(
    "docs/implementation/evidence/i29_s05_external_memory_board_evidence.txt"
)
EXTERNAL_MEMORY_RESULT_PASS = "external_memory_pass"
EVIDENCE_ARCHIVED = "archived"
EVIDENCE_BLOCKED = "blocked"
EVIDENCE_INVALID = "invalid"
EVIDENCE_NEEDS_FOLLOWUP = "needs_followup"


@dataclass(frozen=True)
class ExternalMemoryEvidenceField:
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
class ExternalMemoryEvidenceProfile:
    story: str
    board: str
    evidence_path: Path
    required_result: str
    ddr_wrapper_gate: str
    memory_test_gate: str
    policy_gate: str
    reproducible_build_gate: str
    required_fields: tuple[ExternalMemoryEvidenceField, ...]
    link_fields: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> ExternalMemoryEvidenceField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "evidence_path": self.evidence_path.as_posix(),
            "required_result": self.required_result,
            "ddr_wrapper_gate": self.ddr_wrapper_gate,
            "memory_test_gate": self.memory_test_gate,
            "policy_gate": self.policy_gate,
            "reproducible_build_gate": self.reproducible_build_gate,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "link_fields": list(self.link_fields),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ExternalMemoryEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class ExternalMemoryEvidenceAudit:
    status: str
    message: str
    evidence_path: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == EVIDENCE_ARCHIVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_external_memory_evidence_profile() -> ExternalMemoryEvidenceProfile:
    return ExternalMemoryEvidenceProfile(
        story=FPGA_EXTERNAL_MEMORY_EVIDENCE_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        evidence_path=FPGA_EXTERNAL_MEMORY_EVIDENCE_PATH,
        required_result=EXTERNAL_MEMORY_RESULT_PASS,
        ddr_wrapper_gate=fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        memory_test_gate=fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TESTS_TOOL,
        policy_gate=fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_TOOL,
        reproducible_build_gate=fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        required_fields=(
            ExternalMemoryEvidenceField("story", True, "Must be I29-S05."),
            ExternalMemoryEvidenceField("board", True, "Physical board name."),
            ExternalMemoryEvidenceField("captured_at", True, "Local capture date/time."),
            ExternalMemoryEvidenceField("board_identity_evidence", True, "I24-S01 device/package evidence."),
            ExternalMemoryEvidenceField("ddr_calibration_evidence", True, "DDR calibration done/error capture."),
            ExternalMemoryEvidenceField("memory_test_program", True, "I29-S03 program ID."),
            ExternalMemoryEvidenceField("memory_test_result", True, "Must be external_memory_pass."),
            ExternalMemoryEvidenceField("memory_test_log", True, "Walking/address/burst/alignment/fault log."),
            ExternalMemoryEvidenceField("timing_report_bundle", True, "Gowin timing and utilization report root."),
            ExternalMemoryEvidenceField("debug_status_capture", True, "Decoded debug/status packet evidence."),
            ExternalMemoryEvidenceField("uart_status_capture", True, "UART status stream or transcript."),
            ExternalMemoryEvidenceField("probe_capture", True, "LED, GAO/ILA, or probe evidence."),
            ExternalMemoryEvidenceField("bitstream_sha256", True, "SHA-256 of programmed bitstream."),
            ExternalMemoryEvidenceField("policy_status", True, "I29-S04 policy status."),
            ExternalMemoryEvidenceField("residual_blockers", True, "none, or named blockers."),
            ExternalMemoryEvidenceField("filed_issues", True, "none, or issue IDs for residual blockers."),
            ExternalMemoryEvidenceField("retest_steps", True, "none, or concrete retest steps."),
        ),
        link_fields=(
            "board_identity_evidence",
            "ddr_calibration_evidence",
            "memory_test_log",
            "timing_report_bundle",
            "debug_status_capture",
            "uart_status_capture",
            "probe_capture",
        ),
        blockers=(
            "board-specific DDR controller IP and verified pin constraints must exist before a pass archive",
            "Gowin timing reports and bitstream identity must be linked",
            "memory-test evidence must include walking_pattern, address_line, burst, alignment, and fault_injection observations",
            "UART/status or probe evidence must preserve the first failure sample when the result is not a pass",
            "residual blockers must be closed as none or filed with retest steps",
        ),
    )


def external_memory_evidence_template(
    profile: ExternalMemoryEvidenceProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_external_memory_evidence_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            f"board={profile.board}",
            "captured_at=",
            "board_identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
            "ddr_calibration_evidence=docs/implementation/evidence/i29_s05_ddr_calibration.txt",
            f"memory_test_program={fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID}",
            f"memory_test_result={profile.required_result}",
            "memory_test_log=docs/implementation/evidence/i29_s05_memory_test.log",
            "timing_report_bundle=build/fpga/tang_mega_138k/external_memory/impl",
            "debug_status_capture=docs/implementation/evidence/i29_s05_debug_status.json",
            "uart_status_capture=docs/implementation/evidence/i29_s05_uart_status.log",
            "probe_capture=docs/implementation/evidence/i29_s05_probe_capture.txt",
            "bitstream_sha256=",
            f"policy_status={fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_STATUS}",
            "residual_blockers=none",
            "filed_issues=none",
            "retest_steps=none",
            "",
        )
    )


def parse_external_memory_evidence(text: str) -> ExternalMemoryEvidenceRecord:
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
    return ExternalMemoryEvidenceRecord(fields)


def audit_external_memory_evidence(
    record: ExternalMemoryEvidenceRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ExternalMemoryEvidenceProfile | None = None,
) -> ExternalMemoryEvidenceAudit:
    if profile is None:
        profile = fpga_external_memory_evidence_profile()

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I29-S05")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    link_issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence")

    bitstream_sha256 = record.value("bitstream_sha256")
    if bitstream_sha256 and not _is_sha256(bitstream_sha256):
        link_issues.append("bitstream_sha256 must be a 64-hex-character SHA-256")

    blocker_issues: list[str] = []
    if record.value("memory_test_program") and record.value("memory_test_program") != (
        fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID
    ):
        blocker_issues.append("memory_test_program must be the I29-S03 external-memory test program")
    if record.value("memory_test_result") != profile.required_result:
        blocker_issues.append("memory_test_result must be external_memory_pass")
    if record.value("policy_status") and record.value("policy_status") != (
        fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_STATUS
    ):
        blocker_issues.append("policy_status must match the I29-S04 conservative policy")

    residual_blockers = record.value("residual_blockers")
    filed_issues = record.value("filed_issues")
    retest_steps = record.value("retest_steps")
    if residual_blockers and not _is_empty_disposition(residual_blockers):
        if _is_empty_disposition(filed_issues):
            blocker_issues.append("residual blockers must have filed_issues")
        if _is_empty_disposition(retest_steps):
            blocker_issues.append("residual blockers must have retest_steps")

    if missing_fields:
        return ExternalMemoryEvidenceAudit(
            status=EVIDENCE_INVALID,
            message="External-memory board evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required evidence fields", "rerun the I29-S05 audit"),
        )
    if link_issues:
        return ExternalMemoryEvidenceAudit(
            status=EVIDENCE_INVALID,
            message="External-memory board evidence links are incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete evidence paths and hashes", "rerun the I29-S05 audit"),
        )
    if blocker_issues:
        return ExternalMemoryEvidenceAudit(
            status=EVIDENCE_NEEDS_FOLLOWUP,
            message="External-memory evidence exists but blocker disposition is not complete.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=(),
            blocker_issues=tuple(blocker_issues),
            actions=("file or close residual blockers", "record retest steps before closure"),
        )
    return ExternalMemoryEvidenceAudit(
        status=EVIDENCE_ARCHIVED,
        message="External-memory FPGA evidence archive is complete.",
        evidence_path=evidence_path,
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=("external-memory evidence can be referenced by later DDR/cache/tag work",),
    )


def load_external_memory_evidence_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> ExternalMemoryEvidenceAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_external_memory_evidence_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return ExternalMemoryEvidenceAudit(
            status=EVIDENCE_BLOCKED,
            message="No external-memory board evidence note has been captured yet.",
            evidence_path=relative_path.as_posix(),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            blocker_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the evidence template",
                "link DDR calibration, memory-test, timing, UART/status, probe, and bitstream evidence",
                "close or file residual blockers with retest steps",
            ),
        )
    try:
        record = parse_external_memory_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return ExternalMemoryEvidenceAudit(
            status=EVIDENCE_INVALID,
            message="External-memory board evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            missing_fields=(str(exc),),
            link_issues=(),
            blocker_issues=(),
            actions=("fix the key=value evidence record", "rerun the I29-S05 audit"),
        )
    return audit_external_memory_evidence(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_external_memory_evidence_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_external_memory_evidence_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def external_memory_evidence_audit_json(*, indent: int = 2) -> str:
    return json.dumps(
        load_external_memory_evidence_audit().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_external_memory_evidence(
    profile: ExternalMemoryEvidenceProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_external_memory_evidence_profile()
    lines = [
        "# FPGA External Memory Evidence",
        "",
        f"Story: {profile.story}",
        f"Board: `{profile.board}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Required result: `{profile.required_result}`",
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


def validate_fpga_external_memory_evidence(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_external_memory_evidence_profile()
    issues: list[str] = []

    if profile.story != FPGA_EXTERNAL_MEMORY_EVIDENCE_STORY:
        issues.append(f"external-memory evidence story must be {FPGA_EXTERNAL_MEMORY_EVIDENCE_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("external-memory evidence board must match first-test target")
    if profile.required_result != EXTERNAL_MEMORY_RESULT_PASS:
        issues.append("external-memory evidence required result must be external_memory_pass")

    issues.extend(fpga_ddr_wrapper.validate_fpga_ddr_wrapper(root))
    issues.extend(fpga_external_memory.validate_fpga_external_memory(root))
    issues.extend(fpga_external_memory_tests.validate_fpga_external_memory_tests(root))
    issues.extend(fpga_external_memory_policy.validate_fpga_external_memory_policy(root))
    issues.extend(fpga_reproducible_build.validate_fpga_reproducible_build(root))

    for required_gate in (
        fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TESTS_TOOL,
        fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
    ):
        if required_gate not in {
            profile.ddr_wrapper_gate,
            profile.memory_test_gate,
            profile.policy_gate,
            profile.reproducible_build_gate,
        }:
            issues.append(f"missing external-memory evidence gate {required_gate}")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "board",
        "captured_at",
        "board_identity_evidence",
        "ddr_calibration_evidence",
        "memory_test_program",
        "memory_test_result",
        "memory_test_log",
        "timing_report_bundle",
        "debug_status_capture",
        "uart_status_capture",
        "probe_capture",
        "bitstream_sha256",
        "policy_status",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing external-memory evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    for link in profile.link_fields:
        if link not in fields:
            issues.append(f"external-memory evidence link field {link} must also be required")

    good_record = parse_external_memory_evidence(
        "\n".join(
            (
                "story=I29-S05",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "captured_at=2026-05-09T00:00:00",
                "board_identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
                "ddr_calibration_evidence=docs/implementation/evidence/i29_s05_ddr_calibration.txt",
                f"memory_test_program={fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID}",
                "memory_test_result=external_memory_pass",
                "memory_test_log=docs/implementation/evidence/i29_s05_memory_test.log",
                "timing_report_bundle=build/fpga/tang_mega_138k/external_memory/impl",
                "debug_status_capture=docs/implementation/evidence/i29_s05_debug_status.json",
                "uart_status_capture=docs/implementation/evidence/i29_s05_uart_status.log",
                "probe_capture=docs/implementation/evidence/i29_s05_probe_capture.txt",
                "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                f"policy_status={fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_STATUS}",
                "residual_blockers=none",
                "filed_issues=none",
                "retest_steps=none",
            )
        )
    )
    if not audit_external_memory_evidence(good_record).passed:
        issues.append("complete external-memory evidence must audit as archived")

    followup_record = parse_external_memory_evidence(
        external_memory_evidence_template().replace(
            "captured_at=",
            "captured_at=2026-05-09T00:00:00",
        ).replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        ).replace(
            "residual_blockers=none",
            "residual_blockers=timing_margin_not_closed",
        )
    )
    followup_audit = audit_external_memory_evidence(followup_record)
    if followup_audit.status != EVIDENCE_NEEDS_FOLLOWUP:
        issues.append("residual blockers without filed issues must require follow-up")

    default_audit = load_external_memory_evidence_audit(root)
    if default_audit.status != EVIDENCE_BLOCKED:
        issues.append("default external-memory evidence audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_EXTERNAL_MEMORY_EVIDENCE_DOC)
    for token in (
        "Story: I29-S05",
        FPGA_EXTERNAL_MEMORY_EVIDENCE_TOOL,
        FPGA_EXTERNAL_MEMORY_EVIDENCE_PATH.as_posix(),
        "python tools\\fpga_ddr_wrapper.py --check",
        "python tools\\fpga_external_memory_tests.py --check",
        "python tools\\fpga_external_memory_policy.py --check",
        "python tools\\fpga_reproducible_build.py --check",
        "DDR calibration",
        "memory-test pass/fail",
        "timing reports",
        "debug/status",
        "UART/status",
        "probe",
        "bitstream_sha256",
        "external_memory_pass",
        "residual_blockers",
        "filed_issues",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_EXTERNAL_MEMORY_EVIDENCE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(load_external_memory_evidence_audit(root).as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"external-memory evidence objects are not JSON serializable: {exc}")

    return tuple(issues)


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""Tang Mega 138K SRAM programming and first-observation evidence gate.

Owner stories:
- I24-S04: program SRAM and capture pass/fail/heartbeat board evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_gowin_build


JsonValue = Any

FPGA_PROGRAMMING_STORY = "I24-S04"
FPGA_PROGRAMMING_DOC = Path("docs/implementation/fpga-board-programming.md")
FPGA_PROGRAMMING_TOOL = "python tools\\fpga_board_programming.py --check"
FPGA_PROGRAMMING_EVIDENCE = Path(
    "docs/implementation/evidence/i24_s04_sram_programming.txt"
)
PROGRAMMING_PASSED = "passed"
PROGRAMMING_BLOCKED = "blocked"
PROGRAMMING_FAILED = "failed"
PROGRAMMING_INVALID = "invalid"


@dataclass(frozen=True)
class ProgrammingEvidenceField:
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
class FpgaProgrammingProfile:
    story: str
    board: str
    build_gate: str
    evidence_path: Path
    required_mode: str
    minimum_observation_seconds: int
    required_fields: tuple[ProgrammingEvidenceField, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "build_gate": self.build_gate,
            "evidence_path": self.evidence_path.as_posix(),
            "required_mode": self.required_mode,
            "minimum_observation_seconds": self.minimum_observation_seconds,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ProgrammingEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class ProgrammingAudit:
    status: str
    message: str
    evidence_path: str
    build_status: str
    missing_fields: tuple[str, ...]
    observation_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == PROGRAMMING_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "build_status": self.build_status,
            "missing_fields": list(self.missing_fields),
            "observation_issues": list(self.observation_issues),
            "actions": list(self.actions),
        }


def fpga_programming_profile() -> FpgaProgrammingProfile:
    return FpgaProgrammingProfile(
        story=FPGA_PROGRAMMING_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        build_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        evidence_path=FPGA_PROGRAMMING_EVIDENCE,
        required_mode="SRAM",
        minimum_observation_seconds=10,
        required_fields=(
            ProgrammingEvidenceField("story", True, "Must be I24-S04."),
            ProgrammingEvidenceField("board", True, "Physical board name."),
            ProgrammingEvidenceField("gowin_build_root", True, "Audited I24-S03 build root."),
            ProgrammingEvidenceField("bitstream_path", True, "Audited .fs bitstream path."),
            ProgrammingEvidenceField("programming_tool", True, "Gowin Programmer or approved equivalent."),
            ProgrammingEvidenceField("programming_mode", True, "Must be SRAM for first board programming."),
            ProgrammingEvidenceField("programming_result", True, "Must be success."),
            ProgrammingEvidenceField("programmed_at", True, "Local date/time of programming."),
            ProgrammingEvidenceField("programming_log", True, "Path to captured programming log."),
            ProgrammingEvidenceField("reset_released", True, "yes when board_reset_n_i was released."),
            ProgrammingEvidenceField("observation_duration_s", True, "Observation duration after reset release."),
            ProgrammingEvidenceField("heartbeat_observed", True, "yes when heartbeat_led_o toggled."),
            ProgrammingEvidenceField("pass_led_observed", True, "yes when pass_led_o asserted."),
            ProgrammingEvidenceField("fail_led_observed", True, "no when fail_led_o stayed deasserted."),
            ProgrammingEvidenceField("led_evidence", True, "Photo, video, or probe capture path."),
            ProgrammingEvidenceField("status_retire_count", True, "Observed retire count, at least 8."),
            ProgrammingEvidenceField("status_fault_code", True, "Observed fault code, expected 0."),
        ),
        blockers=(
            "I24-S03 Gowin report audit must pass before programming",
            "first programming mode must be SRAM, not flash",
            "reset release, heartbeat, pass LED, fail LED, retire count, and fault code must be recorded",
            "do not count a physical pass without programming log and LED/probe evidence",
        ),
    )


def programming_evidence_template(profile: FpgaProgrammingProfile | None = None) -> str:
    if profile is None:
        profile = fpga_programming_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            f"board={profile.board}",
            f"gowin_build_root={fpga_gowin_build.fpga_gowin_build_profile().build_root.as_posix()}",
            "bitstream_path=",
            "programming_tool=Gowin Programmer",
            "programming_mode=SRAM",
            "programming_result=",
            "programmed_at=",
            "programming_log=",
            "reset_released=",
            "observation_duration_s=10",
            "heartbeat_observed=",
            "pass_led_observed=",
            "fail_led_observed=",
            "led_evidence=",
            "status_retire_count=",
            "status_fault_code=",
            "",
        )
    )


def parse_programming_evidence(text: str) -> ProgrammingEvidenceRecord:
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
    return ProgrammingEvidenceRecord(fields)


def audit_programming_evidence(
    record: ProgrammingEvidenceRecord,
    *,
    build_audit: fpga_gowin_build.GowinReportAudit,
    evidence_path: str = "<inline>",
    profile: FpgaProgrammingProfile | None = None,
) -> ProgrammingAudit:
    if profile is None:
        profile = fpga_programming_profile()
    if not build_audit.passed:
        return ProgrammingAudit(
            status=PROGRAMMING_BLOCKED,
            message="Board programming is blocked until the I24-S03 Gowin report audit passes.",
            evidence_path=evidence_path,
            build_status=build_audit.status,
            missing_fields=(),
            observation_issues=(),
            actions=("complete I24-S03 report audit", "do not program SRAM yet"),
        )

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I24-S04")
    if record.value("board") and record.value("board") != profile.board:
        missing_fields.append("board_must_match_target")

    issues: list[str] = []
    if record.value("programming_mode") and record.value("programming_mode").upper() != profile.required_mode:
        issues.append("programming_mode must be SRAM")
    if record.value("programming_result").lower() != "success":
        issues.append("programming_result must be success")
    if record.value("reset_released").lower() != "yes":
        issues.append("reset_released must be yes")
    if record.value("heartbeat_observed").lower() != "yes":
        issues.append("heartbeat_observed must be yes")
    if record.value("pass_led_observed").lower() != "yes":
        issues.append("pass_led_observed must be yes")
    if record.value("fail_led_observed").lower() != "no":
        issues.append("fail_led_observed must be no")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        issues.append("bitstream_path must name a .fs file")

    _check_minimum_int(record, "observation_duration_s", profile.minimum_observation_seconds, issues)
    _check_minimum_int(record, "status_retire_count", 8, issues)
    _check_exact_int(record, "status_fault_code", 0, issues)

    if missing_fields:
        return ProgrammingAudit(
            status=PROGRAMMING_INVALID,
            message="Programming evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            build_status=build_audit.status,
            missing_fields=tuple(missing_fields),
            observation_issues=tuple(issues),
            actions=("capture all required programming evidence fields", "rerun the programming audit"),
        )
    if issues:
        return ProgrammingAudit(
            status=PROGRAMMING_FAILED,
            message="Programming evidence captured a failed or inconclusive board run.",
            evidence_path=evidence_path,
            build_status=build_audit.status,
            missing_fields=(),
            observation_issues=tuple(issues),
            actions=("triage clock/reset, bitstream, or firmware result", "do not archive as first pass"),
        )
    return ProgrammingAudit(
        status=PROGRAMMING_PASSED,
        message="SRAM programming and first pass/fail/heartbeat observation passed.",
        evidence_path=evidence_path,
        build_status=build_audit.status,
        missing_fields=(),
        observation_issues=(),
        actions=("archive this evidence in I24-S05",),
    )


def load_programming_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    build_root: Path | None = None,
) -> ProgrammingAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_programming_profile()
    relative_path = evidence_path or profile.evidence_path
    build_profile = fpga_gowin_build.fpga_gowin_build_profile()
    audit_root = root / (build_root or build_profile.build_root)
    build_audit = fpga_gowin_build.audit_gowin_report_bundle(audit_root)
    path = root / relative_path
    if not path.exists():
        return ProgrammingAudit(
            status=PROGRAMMING_BLOCKED,
            message="No SRAM programming evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            build_status=build_audit.status,
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            observation_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the evidence template",
                "program SRAM only after I24-S03 passes",
                "capture reset, LED/probe, retire, and fault observations",
            ),
        )
    try:
        record = parse_programming_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return ProgrammingAudit(
            status=PROGRAMMING_INVALID,
            message="Programming evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            build_status=build_audit.status,
            missing_fields=(str(exc),),
            observation_issues=(),
            actions=("fix the key=value evidence record", "rerun the programming audit"),
        )
    return audit_programming_evidence(
        record,
        build_audit=build_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_programming_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_programming_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_programming_profile(
    profile: FpgaProgrammingProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_programming_profile()
    lines = [
        "# FPGA Board Programming",
        "",
        f"Story: {profile.story}",
        "",
        f"Board: `{profile.board}`",
        f"Build gate: `{profile.build_gate}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Required programming mode: `{profile.required_mode}`",
        f"Minimum observation: {profile.minimum_observation_seconds} seconds",
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


def validate_fpga_programming(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_programming_profile()
    issues: list[str] = []

    if profile.story != FPGA_PROGRAMMING_STORY:
        issues.append(f"programming story must be {FPGA_PROGRAMMING_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("programming board must match first-test profile")
    if profile.required_mode != "SRAM":
        issues.append("first board programming mode must be SRAM")
    if profile.minimum_observation_seconds < 10:
        issues.append("minimum observation must be at least 10 seconds")
    if profile.build_gate != fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL:
        issues.append("programming build gate must be the I24-S03 Gowin build gate")

    issues.extend(fpga_gowin_build.validate_fpga_gowin_build(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "board",
        "gowin_build_root",
        "bitstream_path",
        "programming_tool",
        "programming_mode",
        "programming_result",
        "programmed_at",
        "programming_log",
        "reset_released",
        "observation_duration_s",
        "heartbeat_observed",
        "pass_led_observed",
        "fail_led_observed",
        "led_evidence",
        "status_retire_count",
        "status_fault_code",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing programming evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    passed_build = fpga_gowin_build.GowinReportAudit(
        status="passed",
        message="passed",
        build_root="build/fpga/tang_mega_138k/first_test",
        identity_status="confirmed",
        constraints_status="confirmed",
        missing_reports=(),
        token_issues=(),
        failure_markers=(),
        bitstreams=("build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",),
        actions=(),
    )
    good_record = parse_programming_evidence(
        "\n".join(
            (
                "story=I24-S04",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "gowin_build_root=build/fpga/tang_mega_138k/first_test",
                "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                "programming_tool=Gowin Programmer",
                "programming_mode=SRAM",
                "programming_result=success",
                "programmed_at=2026-05-08T00:00:00",
                "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                "reset_released=yes",
                "observation_duration_s=10",
                "heartbeat_observed=yes",
                "pass_led_observed=yes",
                "fail_led_observed=no",
                "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                "status_retire_count=8",
                "status_fault_code=0",
            )
        )
    )
    if not audit_programming_evidence(good_record, build_audit=passed_build).passed:
        issues.append("complete programming evidence must audit as passed")

    default_audit = load_programming_audit(root)
    if default_audit.status != PROGRAMMING_BLOCKED:
        issues.append("default programming audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_PROGRAMMING_DOC)
    for token in (
        "Story: I24-S04",
        FPGA_PROGRAMMING_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        profile.evidence_path.as_posix(),
        "python tools\\fpga_gowin_build.py --audit-reports",
        "Gowin Programmer",
        "SRAM",
        "board_reset_n_i",
        "heartbeat_led_o",
        "pass_led_o",
        "fail_led_o",
        "status_retire_count",
        "status_fault_code",
        "programming_log",
        "led_evidence",
        "I24-S05",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_PROGRAMMING_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _check_minimum_int(
    record: ProgrammingEvidenceRecord,
    key: str,
    minimum: int,
    issues: list[str],
) -> None:
    value = record.value(key)
    if not value:
        return
    try:
        parsed = int(value)
    except ValueError:
        issues.append(f"{key} must be numeric")
        return
    if parsed < minimum:
        issues.append(f"{key} must be at least {minimum}")


def _check_exact_int(
    record: ProgrammingEvidenceRecord,
    key: str,
    expected: int,
    issues: list[str],
) -> None:
    value = record.value(key)
    if not value:
        return
    try:
        parsed = int(value)
    except ValueError:
        issues.append(f"{key} must be numeric")
        return
    if parsed != expected:
        issues.append(f"{key} must be {expected}")


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

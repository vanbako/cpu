"""Release-candidate full regression and artifact-capture gate.

Owner stories:
- I33-S02: run the full regression and artifact capture gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_reproducible_build, release_candidate_checklist


JsonValue = Any

RELEASE_REGRESSION_STORY = "I33-S02"
RELEASE_REGRESSION_DOC = Path("docs/implementation/release-regression-capture.md")
RELEASE_REGRESSION_TOOL = "python tools\\release_regression_capture.py --check"
RELEASE_REGRESSION_EVIDENCE = Path(
    "docs/implementation/evidence/i33_s02_release_regression_capture.txt"
)
RELEASE_REGRESSION_STATUS = "blocked_until_full_regression_capture"

REGRESSION_ACCEPTED = "accepted"
REGRESSION_BLOCKED = "blocked"
REGRESSION_INVALID = "invalid"
REGRESSION_NEEDS_FOLLOWUP = "needs_followup"

RESULT_CAPTURED = "full_regression_artifacts_captured"
RESULT_BLOCKER = "regression_blocker_captured"

VERILATOR_SLOW_GATE = "python tools\\verilator_diff_harness.py --suite slow"
VERILATOR_ALL_GATE = "python tools\\verilator_diff_harness.py --suite all"
FPGA_VALIDATOR_GATES = (
    "python tools\\fpga_board_identity.py --check",
    "python tools\\fpga_constraints_overlay.py --check",
    "python tools\\fpga_gowin_reports.py --check",
    "python tools\\fpga_reproducible_build.py --check",
    "python tools\\fpga_monitor_board_session.py --check",
)


@dataclass(frozen=True)
class RegressionCaptureCommand:
    name: str
    category: str
    command: str
    required: bool
    expected_status_field: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "category": self.category,
            "command": self.command,
            "required": self.required,
            "expected_status_field": self.expected_status_field,
        }


@dataclass(frozen=True)
class RegressionCaptureField:
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
class ReleaseRegressionCaptureProfile:
    story: str
    status: str
    evidence_path: Path
    release_checklist_gate: str
    reproducible_build_gate: str
    accepted_results: tuple[str, ...]
    commands: tuple[RegressionCaptureCommand, ...]
    required_fields: tuple[RegressionCaptureField, ...]
    artifact_requirements: tuple[str, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "release_checklist_gate": self.release_checklist_gate,
            "reproducible_build_gate": self.reproducible_build_gate,
            "accepted_results": list(self.accepted_results),
            "commands": [command.as_dict() for command in self.commands],
            "required_fields": [field.as_dict() for field in self.required_fields],
            "artifact_requirements": list(self.artifact_requirements),
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class RegressionCaptureRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RegressionCaptureAudit:
    status: str
    message: str
    evidence_path: str
    regression_result: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == REGRESSION_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "regression_result": self.regression_result,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def release_regression_capture_profile() -> ReleaseRegressionCaptureProfile:
    return ReleaseRegressionCaptureProfile(
        story=RELEASE_REGRESSION_STORY,
        status=RELEASE_REGRESSION_STATUS,
        evidence_path=RELEASE_REGRESSION_EVIDENCE,
        release_checklist_gate=release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_TOOL,
        reproducible_build_gate=fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        accepted_results=(RESULT_CAPTURED, RESULT_BLOCKER),
        commands=(
            RegressionCaptureCommand(
                "release_checklist_audit",
                "release_checklist",
                (
                    "python tools\\release_candidate_checklist.py --audit-evidence "
                    "docs\\implementation\\evidence\\i33_s01_release_candidate_checklist.txt"
                ),
                True,
                "release_checklist_status",
            ),
            RegressionCaptureCommand(
                "local_checks",
                "local_checks",
                release_candidate_checklist.LOCAL_CHECKS_GATE,
                True,
                "local_checks_status",
            ),
            RegressionCaptureCommand(
                "spec_reference",
                "traceability",
                release_candidate_checklist.SPEC_REFERENCE_GATE,
                True,
                "spec_reference_status",
            ),
            RegressionCaptureCommand(
                "story_coverage",
                "traceability",
                release_candidate_checklist.STORY_COVERAGE_GATE,
                True,
                "story_coverage_status",
            ),
            RegressionCaptureCommand(
                "verilator_fast",
                "verilator",
                release_candidate_checklist.VERILATOR_FAST_GATE,
                True,
                "fast_verilator_status",
            ),
            RegressionCaptureCommand(
                "verilator_slow",
                "verilator",
                VERILATOR_SLOW_GATE,
                True,
                "slow_verilator_status",
            ),
            RegressionCaptureCommand(
                "verilator_all",
                "verilator",
                VERILATOR_ALL_GATE,
                True,
                "full_verilator_status",
            ),
            *(
                RegressionCaptureCommand(
                    f"fpga_validator_{index}",
                    "fpga_validators",
                    command,
                    True,
                    "fpga_validator_status",
                )
                for index, command in enumerate(FPGA_VALIDATOR_GATES, start=1)
            ),
        ),
        required_fields=(
            RegressionCaptureField("story", True, "Must be I33-S02."),
            RegressionCaptureField("captured_at", True, "Local capture timestamp."),
            RegressionCaptureField("repository_commit", True, "Commit under regression."),
            RegressionCaptureField("release_candidate_id", True, "RC identifier from I33-S01."),
            RegressionCaptureField("release_checklist", True, "I33-S01 checklist evidence path."),
            RegressionCaptureField("release_checklist_status", True, "I33-S01 audit status."),
            RegressionCaptureField("local_checks_log", True, "Full local_checks transcript path."),
            RegressionCaptureField("local_checks_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("spec_reference_log", True, "Spec-reference drift transcript path."),
            RegressionCaptureField("spec_reference_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("story_coverage_log", True, "Story-coverage drift transcript path."),
            RegressionCaptureField("story_coverage_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("fast_verilator_log", True, "Fast Verilator suite transcript path."),
            RegressionCaptureField("fast_verilator_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("slow_verilator_log", True, "Slow Verilator suite transcript path."),
            RegressionCaptureField("slow_verilator_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("full_verilator_log", True, "All-suite Verilator transcript path."),
            RegressionCaptureField("full_verilator_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("fpga_validator_logs", True, "Archive or list of FPGA validator transcripts."),
            RegressionCaptureField("fpga_validator_status", True, "passed, failed, or blocked."),
            RegressionCaptureField("reproducible_build_manifest", True, "I28-S05 manifest path."),
            RegressionCaptureField("reproducible_build_status", True, "captured, failed, or blocked."),
            RegressionCaptureField("command_log_archive", True, "Directory containing all raw command logs."),
            RegressionCaptureField("unexplained_failures", True, "none, or named unexplained failures."),
            RegressionCaptureField("regression_result", True, f"{RESULT_CAPTURED} or {RESULT_BLOCKER}."),
            RegressionCaptureField("residual_blockers", True, "none, or named blockers with follow-up."),
            RegressionCaptureField("signed_off_by", True, "Person or process recording the capture."),
            RegressionCaptureField("signed_off_at", True, "Local sign-off timestamp."),
        ),
        artifact_requirements=(
            "release_checklist",
            "local_checks_log",
            "spec_reference_log",
            "story_coverage_log",
            "fast_verilator_log",
            "slow_verilator_log",
            "full_verilator_log",
            "fpga_validator_logs",
            "reproducible_build_manifest",
            "command_log_archive",
        ),
        blockers=(
            "I33-S01 checklist must audit as accepted before a clean regression capture can close",
            "captured regression artifacts require local checks and all Verilator suites to pass",
            "FPGA validators and reproducible-build metadata must be archived with command logs",
            "regression blockers are allowed only when every failure is explained and residual blockers are named",
        ),
        handoffs=(
            "I33-S03 consumes command logs and statuses for traceability audit",
            "I33-S04 consumes residual blockers and unexplained failure disposition",
            "I33-S05 consumes the command_log_archive and reproducible_build_manifest paths",
        ),
    )


def release_regression_capture_template(
    profile: ReleaseRegressionCaptureProfile | None = None,
) -> str:
    if profile is None:
        profile = release_regression_capture_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            "captured_at=",
            "repository_commit=",
            "release_candidate_id=single-core-v0.1-rc1",
            f"release_checklist={release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_EVIDENCE.as_posix()}",
            "release_checklist_status=accepted",
            "local_checks_log=docs/implementation/evidence/i33_s02_local_checks.log",
            "local_checks_status=passed",
            "spec_reference_log=docs/implementation/evidence/i33_s02_spec_reference.log",
            "spec_reference_status=passed",
            "story_coverage_log=docs/implementation/evidence/i33_s02_story_coverage.log",
            "story_coverage_status=passed",
            "fast_verilator_log=docs/implementation/evidence/i33_s02_verilator_fast.log",
            "fast_verilator_status=passed",
            "slow_verilator_log=docs/implementation/evidence/i33_s02_verilator_slow.log",
            "slow_verilator_status=passed",
            "full_verilator_log=docs/implementation/evidence/i33_s02_verilator_all.log",
            "full_verilator_status=passed",
            "fpga_validator_logs=docs/implementation/evidence/i33_s02_fpga_validators",
            "fpga_validator_status=passed",
            f"reproducible_build_manifest={fpga_reproducible_build.FPGA_REPRO_BUILD_MANIFEST.as_posix()}",
            "reproducible_build_status=captured",
            "command_log_archive=docs/implementation/evidence/i33_s02_command_logs",
            "unexplained_failures=none",
            f"regression_result={RESULT_CAPTURED}",
            "residual_blockers=none",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_regression_capture(text: str) -> RegressionCaptureRecord:
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
    return RegressionCaptureRecord(fields)


def audit_release_regression_capture(
    record: RegressionCaptureRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ReleaseRegressionCaptureProfile | None = None,
) -> RegressionCaptureAudit:
    if profile is None:
        profile = release_regression_capture_profile()
    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S02")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record, profile)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            REGRESSION_INVALID,
            "Release regression capture evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I33-S02 fields", "rerun the regression capture audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            REGRESSION_INVALID,
            "Release regression capture statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix command statuses and artifact paths before capture closure",),
        )
    if blocker_issues:
        return _audit(
            REGRESSION_NEEDS_FOLLOWUP,
            "Release regression capture needs blocker disposition.",
            evidence_path,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("explain failures, file blockers, or rerun failed gates",),
        )
    return _audit(
        REGRESSION_ACCEPTED,
        "Release regression capture is accepted for traceability audit.",
        evidence_path,
        record,
        actions=("hand command logs and artifact archive to I33-S03",),
    )


def load_release_regression_capture_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> RegressionCaptureAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_regression_capture_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            REGRESSION_BLOCKED,
            "No release regression capture evidence has been captured yet.",
            relative_path.as_posix(),
            RegressionCaptureRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the regression capture template",
                "archive local checks, Verilator suites, FPGA validators, reproducible build metadata, command logs, and blockers",
            ),
        )
    try:
        record = parse_release_regression_capture(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            REGRESSION_INVALID,
            "Release regression capture evidence could not be parsed.",
            relative_path.as_posix(),
            RegressionCaptureRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value regression capture record", "rerun the I33-S02 audit"),
        )
    return audit_release_regression_capture(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_regression_capture_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_regression_capture_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_release_regression_capture(
    profile: ReleaseRegressionCaptureProfile | None = None,
) -> str:
    if profile is None:
        profile = release_regression_capture_profile()
    lines = [
        "# Release Regression Capture",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        "",
        "## Commands",
        "",
        "| Name | Category | Command | Status field |",
        "| --- | --- | --- | --- |",
    ]
    for command in profile.commands:
        lines.append(
            f"| `{command.name}` | `{command.category}` | `{command.command}` | `{command.expected_status_field}` |"
        )
    lines.extend(["", "## Artifact Requirements", ""])
    lines.extend(f"- `{artifact}`" for artifact in profile.artifact_requirements)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_release_regression_capture(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_regression_capture_profile()
    issues: list[str] = []

    if profile.story != RELEASE_REGRESSION_STORY:
        issues.append(f"release regression story must be {RELEASE_REGRESSION_STORY}")
    if profile.status != RELEASE_REGRESSION_STATUS:
        issues.append("release regression status must stay blocked until captured evidence exists")
    if profile.release_checklist_gate != release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_TOOL:
        issues.append("release regression must depend on I33-S01 checklist")
    if profile.reproducible_build_gate != fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL:
        issues.append("release regression must depend on I28-S05 reproducible build")

    issues.extend(release_candidate_checklist.validate_release_candidate_checklist(root))
    issues.extend(fpga_reproducible_build.validate_fpga_reproducible_build(root))

    command_names = {command.name for command in profile.commands}
    for required in (
        "local_checks",
        "spec_reference",
        "story_coverage",
        "verilator_fast",
        "verilator_slow",
        "verilator_all",
    ):
        if required not in command_names:
            issues.append(f"release regression missing command {required}")
    if len([command for command in profile.commands if command.category == "fpga_validators"]) < 4:
        issues.append("release regression must name FPGA validator commands")
    if RESULT_CAPTURED not in profile.accepted_results or RESULT_BLOCKER not in profile.accepted_results:
        issues.append("release regression must support captured and blocker results")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "captured_at",
        "repository_commit",
        "release_candidate_id",
        "release_checklist",
        "release_checklist_status",
        "local_checks_log",
        "local_checks_status",
        "spec_reference_log",
        "spec_reference_status",
        "story_coverage_log",
        "story_coverage_status",
        "fast_verilator_log",
        "fast_verilator_status",
        "slow_verilator_log",
        "slow_verilator_status",
        "full_verilator_log",
        "full_verilator_status",
        "fpga_validator_logs",
        "fpga_validator_status",
        "reproducible_build_manifest",
        "reproducible_build_status",
        "command_log_archive",
        "unexplained_failures",
        "regression_result",
        "residual_blockers",
        "signed_off_by",
        "signed_off_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing release regression field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    complete = parse_release_regression_capture(
        release_regression_capture_template()
        .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
    )
    if not audit_release_regression_capture(complete).accepted:
        issues.append("complete release regression capture record must audit as accepted")

    blocker = parse_release_regression_capture(
        release_regression_capture_template()
        .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("full_verilator_status=passed", "full_verilator_status=failed")
        .replace(f"regression_result={RESULT_CAPTURED}", f"regression_result={RESULT_BLOCKER}")
        .replace("residual_blockers=none", "residual_blockers=verilator_full_timeout")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
    )
    if not audit_release_regression_capture(blocker).accepted:
        issues.append("explained release regression blocker record must audit as accepted")

    followup = parse_release_regression_capture(
        release_regression_capture_template()
        .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(f"regression_result={RESULT_CAPTURED}", f"regression_result={RESULT_BLOCKER}")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
    )
    if audit_release_regression_capture(followup).status != REGRESSION_NEEDS_FOLLOWUP:
        issues.append("blocker regression capture without residual blockers must need follow-up")

    default_audit = load_release_regression_capture_audit(root)
    if default_audit.status != REGRESSION_BLOCKED:
        issues.append("default release regression audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_REGRESSION_DOC)
    for token in (
        "Story: I33-S02",
        RELEASE_REGRESSION_TOOL,
        RELEASE_REGRESSION_EVIDENCE.as_posix(),
        release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_TOOL,
        release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_EVIDENCE.as_posix(),
        release_candidate_checklist.LOCAL_CHECKS_GATE,
        release_candidate_checklist.SPEC_REFERENCE_GATE,
        release_candidate_checklist.STORY_COVERAGE_GATE,
        release_candidate_checklist.VERILATOR_FAST_GATE,
        VERILATOR_SLOW_GATE,
        VERILATOR_ALL_GATE,
        "release_checklist",
        "spec_reference_log",
        "story_coverage_log",
        "fpga_validator_logs",
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        "reproducible_build_manifest",
        "command_log_archive",
        "unexplained_failures",
        RESULT_CAPTURED,
        RESULT_BLOCKER,
        "I33-S03",
        "I33-S04",
        "I33-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_REGRESSION_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release regression objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: RegressionCaptureRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> RegressionCaptureAudit:
    return RegressionCaptureAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        regression_result=record.value("regression_result"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _status_issues(record: RegressionCaptureRecord) -> list[str]:
    result = record.value("regression_result")
    issues: list[str] = []
    if record.value("release_checklist_status") and record.value("release_checklist_status") != "accepted":
        issues.append("release_checklist_status must be accepted")
    if result not in {RESULT_CAPTURED, RESULT_BLOCKER, ""}:
        issues.append(f"regression_result must be {RESULT_CAPTURED} or {RESULT_BLOCKER}")

    expected = {
        "local_checks_status": "passed",
        "spec_reference_status": "passed",
        "story_coverage_status": "passed",
        "fast_verilator_status": "passed",
        "slow_verilator_status": "passed",
        "full_verilator_status": "passed",
        "fpga_validator_status": "passed",
        "reproducible_build_status": "captured",
    }
    if result == RESULT_CAPTURED or not result:
        for field, value in expected.items():
            if record.value(field) and record.value(field) != value:
                issues.append(f"{field} must be {value}")
    elif result == RESULT_BLOCKER:
        for field in expected:
            if record.value(field) and record.value(field) not in {"passed", "captured", "failed", "blocked"}:
                issues.append(f"{field} must be passed, captured, failed, or blocked")
    return issues


def _artifact_issues(
    record: RegressionCaptureRecord,
    profile: ReleaseRegressionCaptureProfile,
) -> list[str]:
    issues: list[str] = []
    for field in profile.artifact_requirements:
        if _empty(record.value(field)):
            issues.append(f"{field} must name a concrete artifact path")
    checklist = record.value("release_checklist")
    if checklist and "i33_s01" not in checklist.lower():
        issues.append("release_checklist must reference I33-S01 evidence")
    manifest = record.value("reproducible_build_manifest")
    if manifest and "i28_s05" not in manifest.lower():
        issues.append("reproducible_build_manifest must reference I28-S05 evidence")
    if manifest and not manifest.lower().endswith(".json"):
        issues.append("reproducible_build_manifest must be a JSON manifest")
    return issues


def _blocker_issues(record: RegressionCaptureRecord) -> list[str]:
    result = record.value("regression_result")
    unexplained = record.value("unexplained_failures").strip().lower()
    blockers = record.value("residual_blockers").strip().lower()
    issues: list[str] = []
    if unexplained and unexplained != "none":
        issues.append("unexplained_failures must be none")
    if result == RESULT_CAPTURED and blockers != "none":
        issues.append(f"{RESULT_CAPTURED} requires residual_blockers=none")
    if result == RESULT_BLOCKER and blockers == "none":
        issues.append(f"{RESULT_BLOCKER} requires named residual_blockers")
    return issues


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

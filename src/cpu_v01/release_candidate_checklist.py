"""Single-core v0.1 release-candidate checklist gate.

Owner stories:
- I33-S01: define the single-core v0.1 release-candidate checklist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_first_pass_archive,
    fpga_first_test,
    fpga_monitor_board_session,
    fpga_reproducible_build,
)


JsonValue = Any

RELEASE_CANDIDATE_CHECKLIST_STORY = "I33-S01"
RELEASE_CANDIDATE_CHECKLIST_DOC = Path(
    "docs/implementation/release-candidate-checklist.md"
)
RELEASE_CANDIDATE_CHECKLIST_TOOL = "python tools\\release_candidate_checklist.py --check"
RELEASE_CANDIDATE_CHECKLIST_EVIDENCE = Path(
    "docs/implementation/evidence/i33_s01_release_candidate_checklist.txt"
)
RELEASE_CANDIDATE_CHECKLIST_STATUS = "blocked_until_release_candidate_evidence"

LOCAL_CHECKS_GATE = "python tools\\local_checks.py"
SPEC_REFERENCE_GATE = "python tools\\spec_reference_check.py"
STORY_COVERAGE_GATE = "python tools\\story_coverage.py --check-drift"
VERILATOR_FAST_GATE = "python tools\\verilator_diff_harness.py --suite fast"
VERILATOR_FULL_GATE = "python tools\\verilator_diff_harness.py --suite all"
KNOWN_LIMITATIONS_PATH = Path("docs/implementation/single-core-v0.1-known-limitations.md")
RELEASE_BUNDLE_PATH = Path("docs/implementation/evidence/i33_s05_release_candidate_bundle.txt")

RC_ACCEPTED = "accepted"
RC_BLOCKED = "blocked"
RC_INVALID = "invalid"
RC_NEEDS_FOLLOWUP = "needs_followup"

RC_DECISION_READY = "ready_for_rc_tag"
RC_DECISION_BLOCKED = "blocked"


@dataclass(frozen=True)
class ReleaseChecklistItem:
    item_id: str
    category: str
    required: bool
    gate: str
    evidence: str
    acceptance: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "required": self.required,
            "gate": self.gate,
            "evidence": self.evidence,
            "acceptance": self.acceptance,
        }


@dataclass(frozen=True)
class ReleaseChecklistField:
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
class ReleaseCandidateChecklistProfile:
    story: str
    status: str
    evidence_path: Path
    target_board: str
    required_categories: tuple[str, ...]
    checklist_items: tuple[ReleaseChecklistItem, ...]
    required_fields: tuple[ReleaseChecklistField, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "target_board": self.target_board,
            "required_categories": list(self.required_categories),
            "checklist_items": [item.as_dict() for item in self.checklist_items],
            "required_fields": [field.as_dict() for field in self.required_fields],
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class ReleaseChecklistRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class ReleaseChecklistAudit:
    status: str
    message: str
    evidence_path: str
    rc_decision: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == RC_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "rc_decision": self.rc_decision,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def release_candidate_checklist_profile() -> ReleaseCandidateChecklistProfile:
    return ReleaseCandidateChecklistProfile(
        story=RELEASE_CANDIDATE_CHECKLIST_STORY,
        status=RELEASE_CANDIDATE_CHECKLIST_STATUS,
        evidence_path=RELEASE_CANDIDATE_CHECKLIST_EVIDENCE,
        target_board=fpga_first_test.TARGET_BOARD_NAME,
        required_categories=(
            "local_checks",
            "verilator",
            "fpga_evidence",
            "traceability",
            "known_limitations",
            "artifacts",
        ),
        checklist_items=(
            ReleaseChecklistItem(
                "local_checks",
                "local_checks",
                True,
                LOCAL_CHECKS_GATE,
                "full local gate transcript with zero exit status",
                "local_checks_status=passed",
            ),
            ReleaseChecklistItem(
                "spec_reference_drift",
                "traceability",
                True,
                SPEC_REFERENCE_GATE,
                "spec/story reference drift transcript",
                "spec_reference_status=passed",
            ),
            ReleaseChecklistItem(
                "story_coverage_drift",
                "traceability",
                True,
                STORY_COVERAGE_GATE,
                "story coverage drift transcript",
                "story_coverage_status=passed",
            ),
            ReleaseChecklistItem(
                "verilator_fast_suite",
                "verilator",
                True,
                VERILATOR_FAST_GATE,
                "fast-suite summary and selected cases",
                "fast_verilator_status=passed",
            ),
            ReleaseChecklistItem(
                "verilator_full_suite",
                "verilator",
                True,
                VERILATOR_FULL_GATE,
                "full-suite or accepted skip/blocker transcript",
                "full_verilator_status=passed",
            ),
            ReleaseChecklistItem(
                "first_cpu_pass_archive",
                "fpga_evidence",
                True,
                fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
                "I31-S05 first physical CPU pass or classified blocker archive",
                "first_pass_archive_status=archived",
            ),
            ReleaseChecklistItem(
                "interactive_board_session",
                "fpga_evidence",
                True,
                fpga_monitor_board_session.FPGA_MONITOR_BOARD_SESSION_TOOL,
                "I32-S06 interactive multi-program board-session archive",
                "monitor_board_session_status=accepted",
            ),
            ReleaseChecklistItem(
                "reproducible_build_manifest",
                "artifacts",
                True,
                fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
                "I28-S05 reproducible build manifest with tool versions and bitstream hash",
                "reproducible_build_status=captured",
            ),
            ReleaseChecklistItem(
                "known_limitations",
                "known_limitations",
                True,
                KNOWN_LIMITATIONS_PATH.as_posix(),
                "single-core v0.1 known limitations and deferred surfaces",
                "known_limitations_status=published",
            ),
            ReleaseChecklistItem(
                "release_bundle",
                "artifacts",
                True,
                RELEASE_BUNDLE_PATH.as_posix(),
                "release-candidate bundle path reserved for I33-S05",
                "artifact_manifest_status=reserved",
            ),
        ),
        required_fields=(
            ReleaseChecklistField("story", True, "Must be I33-S01."),
            ReleaseChecklistField("release_candidate_id", True, "Human-readable RC identifier."),
            ReleaseChecklistField("repository_commit", True, "Commit being evaluated for RC readiness."),
            ReleaseChecklistField("target_board", True, "FPGA board target for physical evidence."),
            ReleaseChecklistField("local_checks_status", True, "Status of python tools\\local_checks.py."),
            ReleaseChecklistField("spec_reference_status", True, "Status of spec reference drift check."),
            ReleaseChecklistField("story_coverage_status", True, "Status of story coverage drift check."),
            ReleaseChecklistField("fast_verilator_status", True, "Status of fast Verilator suite."),
            ReleaseChecklistField("full_verilator_status", True, "Status of full Verilator suite."),
            ReleaseChecklistField("first_pass_archive_status", True, "I31-S05 archive audit status."),
            ReleaseChecklistField("monitor_board_session_status", True, "I32-S06 board-session audit status."),
            ReleaseChecklistField("reproducible_build_status", True, "I28-S05 manifest status."),
            ReleaseChecklistField("known_limitations_status", True, "Known-limitations document status."),
            ReleaseChecklistField("artifact_manifest_status", True, "Release bundle manifest status."),
            ReleaseChecklistField("known_limitations_path", True, "Path to known-limitations document."),
            ReleaseChecklistField("artifact_manifest_path", True, "Path reserved for release bundle manifest."),
            ReleaseChecklistField("rc_decision", True, "ready_for_rc_tag or blocked."),
            ReleaseChecklistField("residual_blockers", True, "none, or named release blockers."),
            ReleaseChecklistField("signed_off_by", True, "Person or process recording the checklist."),
            ReleaseChecklistField("signed_off_at", True, "Local sign-off timestamp."),
        ),
        blockers=(
            "I31-S05 first physical CPU pass or classified blocker archive must close before RC readiness",
            "I32-S06 interactive board-session evidence must be accepted before RC readiness",
            "full Verilator and local checks must pass or the checklist remains blocked",
            "known limitations and release artifacts are required before tagging",
        ),
        handoffs=(
            "I33-S02 consumes this checklist to run full regression and artifact capture",
            "I33-S04 consumes the known limitations path and blocker inventory",
            "I33-S05 consumes the artifact manifest path and required evidence list",
        ),
    )


def release_candidate_checklist_template(
    profile: ReleaseCandidateChecklistProfile | None = None,
) -> str:
    if profile is None:
        profile = release_candidate_checklist_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            "release_candidate_id=single-core-v0.1-rc1",
            "repository_commit=",
            f"target_board={profile.target_board}",
            "local_checks_status=passed",
            "spec_reference_status=passed",
            "story_coverage_status=passed",
            "fast_verilator_status=passed",
            "full_verilator_status=passed",
            "first_pass_archive_status=archived",
            "monitor_board_session_status=accepted",
            "reproducible_build_status=captured",
            "known_limitations_status=published",
            "artifact_manifest_status=reserved",
            f"known_limitations_path={KNOWN_LIMITATIONS_PATH.as_posix()}",
            f"artifact_manifest_path={RELEASE_BUNDLE_PATH.as_posix()}",
            f"rc_decision={RC_DECISION_READY}",
            "residual_blockers=none",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_candidate_checklist(text: str) -> ReleaseChecklistRecord:
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
    return ReleaseChecklistRecord(fields)


def audit_release_candidate_checklist(
    record: ReleaseChecklistRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ReleaseCandidateChecklistProfile | None = None,
) -> ReleaseChecklistAudit:
    if profile is None:
        profile = release_candidate_checklist_profile()

    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S01")
    if record.value("target_board") and record.value("target_board") != profile.target_board:
        missing_fields.append("target_board_must_match_fpga_first_test")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            RC_INVALID,
            "Release-candidate checklist evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I33-S01 fields", "rerun the RC checklist audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            RC_INVALID,
            "Release-candidate checklist statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix status fields and artifact paths before RC review",),
        )
    if blocker_issues:
        return _audit(
            RC_NEEDS_FOLLOWUP,
            "Release-candidate checklist still has unresolved blockers.",
            evidence_path,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("close blockers or set rc_decision=blocked with concrete follow-up",),
        )
    return _audit(
        RC_ACCEPTED,
        "Single-core v0.1 release-candidate checklist is ready for I33-S02.",
        evidence_path,
        record,
        actions=("run I33-S02 full regression and artifact capture",),
    )


def load_release_candidate_checklist_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> ReleaseChecklistAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_candidate_checklist_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            RC_BLOCKED,
            "No release-candidate checklist evidence has been captured yet.",
            relative_path.as_posix(),
            ReleaseChecklistRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the checklist template",
                "capture local checks, Verilator suites, FPGA evidence, known limitations, artifacts, blockers, and sign-off",
            ),
        )
    try:
        record = parse_release_candidate_checklist(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            RC_INVALID,
            "Release-candidate checklist evidence could not be parsed.",
            relative_path.as_posix(),
            ReleaseChecklistRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value checklist record", "rerun the I33-S01 audit"),
        )
    return audit_release_candidate_checklist(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_candidate_checklist_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_candidate_checklist_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_release_candidate_checklist(
    profile: ReleaseCandidateChecklistProfile | None = None,
) -> str:
    if profile is None:
        profile = release_candidate_checklist_profile()
    lines = [
        "# Release Candidate Checklist",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Target board: `{profile.target_board}`",
        "",
        "## Checklist Items",
        "",
        "| Item | Category | Gate | Acceptance |",
        "| --- | --- | --- | --- |",
    ]
    for item in profile.checklist_items:
        lines.append(
            f"| `{item.item_id}` | `{item.category}` | `{item.gate}` | `{item.acceptance}` |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_release_candidate_checklist(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_candidate_checklist_profile()
    issues: list[str] = []

    if profile.story != RELEASE_CANDIDATE_CHECKLIST_STORY:
        issues.append(f"release checklist story must be {RELEASE_CANDIDATE_CHECKLIST_STORY}")
    if profile.status != RELEASE_CANDIDATE_CHECKLIST_STATUS:
        issues.append("release checklist status must stay blocked until evidence exists")
    if profile.target_board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("release checklist target board must match FPGA first-test target")

    issues.extend(fpga_first_pass_archive.validate_fpga_first_pass_archive(root))
    issues.extend(fpga_monitor_board_session.validate_fpga_monitor_board_session(root))
    issues.extend(fpga_reproducible_build.validate_fpga_reproducible_build(root))

    categories = {item.category for item in profile.checklist_items}
    for category in profile.required_categories:
        if category not in categories:
            issues.append(f"release checklist missing category {category}")
    item_ids = [item.item_id for item in profile.checklist_items]
    if len(item_ids) != len(set(item_ids)):
        issues.append("release checklist item IDs must be unique")
    for item in profile.checklist_items:
        if item.required and not item.gate:
            issues.append(f"{item.item_id}: required item must name a gate")
        if item.required and not item.acceptance:
            issues.append(f"{item.item_id}: required item must name acceptance")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "release_candidate_id",
        "repository_commit",
        "target_board",
        "local_checks_status",
        "spec_reference_status",
        "story_coverage_status",
        "fast_verilator_status",
        "full_verilator_status",
        "first_pass_archive_status",
        "monitor_board_session_status",
        "reproducible_build_status",
        "known_limitations_status",
        "artifact_manifest_status",
        "known_limitations_path",
        "artifact_manifest_path",
        "rc_decision",
        "residual_blockers",
        "signed_off_by",
        "signed_off_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing release checklist field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    ready_record = parse_release_candidate_checklist(
        release_candidate_checklist_template()
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T16:00:00")
    )
    if not audit_release_candidate_checklist(ready_record).accepted:
        issues.append("complete release checklist record must audit as accepted")

    blocked_record = parse_release_candidate_checklist(
        release_candidate_checklist_template()
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T16:00:00")
        .replace(f"rc_decision={RC_DECISION_READY}", f"rc_decision={RC_DECISION_BLOCKED}")
    )
    if audit_release_candidate_checklist(blocked_record).status != RC_NEEDS_FOLLOWUP:
        issues.append("blocked RC decision without residual blockers must need follow-up")

    default_audit = load_release_candidate_checklist_audit(root)
    if default_audit.status != RC_BLOCKED:
        issues.append("default release checklist audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_CANDIDATE_CHECKLIST_DOC)
    for token in (
        "Story: I33-S01",
        RELEASE_CANDIDATE_CHECKLIST_TOOL,
        RELEASE_CANDIDATE_CHECKLIST_EVIDENCE.as_posix(),
        LOCAL_CHECKS_GATE,
        VERILATOR_FAST_GATE,
        VERILATOR_FULL_GATE,
        fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        fpga_monitor_board_session.FPGA_MONITOR_BOARD_SESSION_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        "known_limitations_path",
        "artifact_manifest_path",
        "ready_for_rc_tag",
        "residual_blockers",
        "I33-S02",
        "I33-S04",
        "I33-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_CANDIDATE_CHECKLIST_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release checklist objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: ReleaseChecklistRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> ReleaseChecklistAudit:
    return ReleaseChecklistAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        rc_decision=record.value("rc_decision"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _status_issues(record: ReleaseChecklistRecord) -> list[str]:
    issues: list[str] = []
    expected_pass = (
        "local_checks_status",
        "spec_reference_status",
        "story_coverage_status",
        "fast_verilator_status",
        "full_verilator_status",
    )
    for field in expected_pass:
        if record.value(field) and record.value(field) != "passed":
            issues.append(f"{field} must be passed")
    if record.value("first_pass_archive_status") and record.value("first_pass_archive_status") != "archived":
        issues.append("first_pass_archive_status must be archived")
    if record.value("monitor_board_session_status") and record.value("monitor_board_session_status") != "accepted":
        issues.append("monitor_board_session_status must be accepted")
    if record.value("reproducible_build_status") and record.value("reproducible_build_status") != "captured":
        issues.append("reproducible_build_status must be captured")
    if record.value("known_limitations_status") and record.value("known_limitations_status") != "published":
        issues.append("known_limitations_status must be published")
    if record.value("artifact_manifest_status") and record.value("artifact_manifest_status") != "reserved":
        issues.append("artifact_manifest_status must be reserved")
    if record.value("rc_decision") and record.value("rc_decision") not in {
        RC_DECISION_READY,
        RC_DECISION_BLOCKED,
    }:
        issues.append("rc_decision must be ready_for_rc_tag or blocked")
    return issues


def _artifact_issues(record: ReleaseChecklistRecord) -> list[str]:
    issues: list[str] = []
    if record.value("known_limitations_path") and record.value("known_limitations_path") != KNOWN_LIMITATIONS_PATH.as_posix():
        issues.append(f"known_limitations_path must be {KNOWN_LIMITATIONS_PATH.as_posix()}")
    if record.value("artifact_manifest_path") and record.value("artifact_manifest_path") != RELEASE_BUNDLE_PATH.as_posix():
        issues.append(f"artifact_manifest_path must be {RELEASE_BUNDLE_PATH.as_posix()}")
    return issues


def _blocker_issues(record: ReleaseChecklistRecord) -> list[str]:
    issues: list[str] = []
    blockers = record.value("residual_blockers").strip().lower()
    if record.value("rc_decision") == RC_DECISION_READY and blockers != "none":
        issues.append("ready_for_rc_tag requires residual_blockers=none")
    if record.value("rc_decision") == RC_DECISION_BLOCKED and blockers == "none":
        issues.append("blocked RC decision requires named residual_blockers")
    return issues


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

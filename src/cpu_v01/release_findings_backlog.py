"""Single-core v0.1 release-findings backlog gate.

Owner stories:
- I33-S06: open the next backlog from release findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import release_candidate_bundle


JsonValue = Any

RELEASE_FINDINGS_STORY = "I33-S06"
RELEASE_FINDINGS_DOC = Path("docs/implementation/release-findings-backlog.md")
RELEASE_FINDINGS_TOOL = "python tools\\release_findings_backlog.py --check"
RELEASE_FINDINGS_EVIDENCE = Path(
    "docs/implementation/evidence/i33_s06_release_findings_backlog.txt"
)
RELEASE_FINDINGS_MANIFEST = Path(
    "docs/implementation/evidence/i33_s06_release_findings_backlog.json"
)
RETEST_COMMANDS_PATH = Path(
    "docs/implementation/evidence/i33_s06_retest_commands.txt"
)
RELEASE_FINDINGS_STATUS = "blocked_until_release_findings_triage"

FINDINGS_ACCEPTED = "accepted"
FINDINGS_BLOCKED = "blocked"
FINDINGS_INVALID = "invalid"
FINDINGS_NEEDS_FOLLOWUP = "needs_followup"

FINDINGS_RESULT_OPENED = "release_findings_backlog_opened"
FINDINGS_RESULT_BLOCKER = "release_findings_blocker_captured"

FROZEN_CONTRACT_UNCHANGED = "unchanged"


@dataclass(frozen=True)
class FindingRoute:
    finding_id: str
    source: str
    category: str
    target_backlog: str
    disposition: str
    frozen_contract_impact: str
    evidence: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "finding_id": self.finding_id,
            "source": self.source,
            "category": self.category,
            "target_backlog": self.target_backlog,
            "disposition": self.disposition,
            "frozen_contract_impact": self.frozen_contract_impact,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class FindingsField:
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
class ReleaseFindingsProfile:
    story: str
    status: str
    evidence_path: Path
    manifest_path: Path
    release_bundle_gate: str
    release_bundle_evidence: Path
    release_bundle_manifest: Path
    required_categories: tuple[str, ...]
    routes: tuple[FindingRoute, ...]
    required_fields: tuple[FindingsField, ...]
    accepted_results: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "manifest_path": self.manifest_path.as_posix(),
            "release_bundle_gate": self.release_bundle_gate,
            "release_bundle_evidence": self.release_bundle_evidence.as_posix(),
            "release_bundle_manifest": self.release_bundle_manifest.as_posix(),
            "required_categories": list(self.required_categories),
            "routes": [route.as_dict() for route in self.routes],
            "required_fields": [field.as_dict() for field in self.required_fields],
            "accepted_results": list(self.accepted_results),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class FindingsRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FindingsAudit:
    status: str
    message: str
    evidence_path: str
    findings_result: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == FINDINGS_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "findings_result": self.findings_result,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def release_findings_profile() -> ReleaseFindingsProfile:
    return ReleaseFindingsProfile(
        story=RELEASE_FINDINGS_STORY,
        status=RELEASE_FINDINGS_STATUS,
        evidence_path=RELEASE_FINDINGS_EVIDENCE,
        manifest_path=RELEASE_FINDINGS_MANIFEST,
        release_bundle_gate=release_candidate_bundle.RELEASE_BUNDLE_TOOL,
        release_bundle_evidence=release_candidate_bundle.RELEASE_BUNDLE_EVIDENCE,
        release_bundle_manifest=release_candidate_bundle.RELEASE_BUNDLE_MANIFEST,
        required_categories=(
            "release_blockers",
            "implementation_followups",
            "architecture_findings",
            "board_followups",
            "retest_commands",
            "tag_decision_handoff",
        ),
        routes=_finding_routes(),
        required_fields=(
            FindingsField("story", True, "Must be I33-S06."),
            FindingsField("triaged_at", True, "Local triage timestamp."),
            FindingsField("repository_commit", True, "Commit under release-findings triage."),
            FindingsField("release_candidate_bundle", True, "I33-S05 bundle evidence path."),
            FindingsField("release_bundle_status", True, "I33-S05 audit status."),
            FindingsField("bundle_manifest", True, "I33-S05 bundle manifest path."),
            FindingsField("release_blockers", True, "none, or blockers carried from I33-S05."),
            FindingsField("implementation_findings", True, "Implementation follow-up finding IDs."),
            FindingsField("architecture_findings", True, "Architecture errata or none-known finding IDs."),
            FindingsField("board_findings", True, "Board evidence or target follow-up finding IDs."),
            FindingsField("deferred_work_status", True, "triaged, blocked, or incomplete."),
            FindingsField("post_v0_1_backlog", True, "Post-v0.1 backlog manifest path."),
            FindingsField("post_v0_1_backlog_status", True, "opened, blocked, or incomplete."),
            FindingsField("frozen_contract_status", True, "Must remain unchanged."),
            FindingsField("tag_decision_status", True, "Tag decision handoff status."),
            FindingsField("retest_commands", True, "Retest-command capture path."),
            FindingsField("retest_status", True, "captured, blocked, or failed."),
            FindingsField("findings_result", True, "Findings triage result."),
            FindingsField("findings_blockers", True, "none, or untriaged blocker IDs."),
            FindingsField("signed_off_by", True, "Person or process recording the triage."),
            FindingsField("signed_off_at", True, "Local sign-off timestamp."),
        ),
        accepted_results=(FINDINGS_RESULT_OPENED, FINDINGS_RESULT_BLOCKER),
        handoffs=(
            "post-v0.1 implementation backlog consumes implementation_findings and board_findings",
            "Architecture backlog consumes architecture_findings without changing the frozen v0.1 contract",
            "A tag decision consumes the I33-S05 bundle and I33-S06 findings manifest",
        ),
    )


def release_findings_template(
    profile: ReleaseFindingsProfile | None = None,
) -> str:
    if profile is None:
        profile = release_findings_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            "triaged_at=",
            "repository_commit=",
            f"release_candidate_bundle={profile.release_bundle_evidence.as_posix()}",
            "release_bundle_status=accepted",
            f"bundle_manifest={profile.release_bundle_manifest.as_posix()}",
            "release_blockers=physical_board_pass_blocked,release_candidate_not_tagged",
            "implementation_findings=rtl_unsupported_capability_subset,multicore_fabric_deferred",
            "architecture_findings=architecture_errata_none_known,cacheable_tag_policy_deferred",
            "board_findings=physical_board_pass_blocked,ddr_board_ip_deferred,retro_console_60k_deferred",
            "deferred_work_status=triaged",
            f"post_v0_1_backlog={profile.manifest_path.as_posix()}",
            "post_v0_1_backlog_status=opened",
            f"frozen_contract_status={FROZEN_CONTRACT_UNCHANGED}",
            "tag_decision_status=blocked_until_board_evidence_and_bundle_signoff",
            f"retest_commands={RETEST_COMMANDS_PATH.as_posix()}",
            "retest_status=captured",
            f"findings_result={FINDINGS_RESULT_OPENED}",
            "findings_blockers=none",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_findings(text: str) -> FindingsRecord:
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
    return FindingsRecord(fields)


def audit_release_findings(
    record: FindingsRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ReleaseFindingsProfile | None = None,
) -> FindingsAudit:
    if profile is None:
        profile = release_findings_profile()
    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S06")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record, profile)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            FINDINGS_INVALID,
            "Release-findings backlog evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I33-S06 fields", "rerun the findings audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            FINDINGS_INVALID,
            "Release-findings statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix findings statuses and artifact paths",),
        )
    if blocker_issues:
        return _audit(
            FINDINGS_NEEDS_FOLLOWUP,
            "Release-findings backlog needs blocker disposition.",
            evidence_path,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("name untriaged findings blockers or rerun the bundle audit",),
        )
    return _audit(
        FINDINGS_ACCEPTED,
        "Release-findings backlog is accepted for post-v0.1 planning.",
        evidence_path,
        record,
        actions=("hand findings manifest to post-v0.1 implementation and architecture backlogs",),
    )


def load_release_findings_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> FindingsAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_findings_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            FINDINGS_BLOCKED,
            "No release-findings backlog evidence has been captured yet.",
            relative_path.as_posix(),
            FindingsRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the findings template",
                "triage release blockers, deferred work, retest commands, and tag-decision handoff",
            ),
        )
    try:
        record = parse_release_findings(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            FINDINGS_INVALID,
            "Release-findings backlog evidence could not be parsed.",
            relative_path.as_posix(),
            FindingsRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value findings record", "rerun the I33-S06 audit"),
        )
    return audit_release_findings(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_findings_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_findings_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def release_findings_manifest_template(*, indent: int = 2) -> str:
    profile = release_findings_profile()
    manifest = profile.as_dict()
    manifest["repository_commit"] = ""
    manifest["created_at"] = ""
    manifest["release_blockers"] = (
        "physical_board_pass_blocked,release_candidate_not_tagged"
    )
    manifest["frozen_contract_status"] = FROZEN_CONTRACT_UNCHANGED
    return json.dumps(manifest, indent=indent, sort_keys=True) + "\n"


def render_release_findings(
    profile: ReleaseFindingsProfile | None = None,
) -> str:
    if profile is None:
        profile = release_findings_profile()
    lines = [
        "# Release Findings Backlog",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Manifest path: `{profile.manifest_path.as_posix()}`",
        "",
        "## Finding Routes",
        "",
        "| Finding | Category | Target | Contract impact |",
        "| --- | --- | --- | --- |",
    ]
    for route in profile.routes:
        lines.append(
            f"| `{route.finding_id}` | `{route.category}` | `{route.target_backlog}` | `{route.frozen_contract_impact}` |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_release_findings(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_findings_profile()
    issues: list[str] = []

    if profile.story != RELEASE_FINDINGS_STORY:
        issues.append(f"release findings story must be {RELEASE_FINDINGS_STORY}")
    if profile.status != RELEASE_FINDINGS_STATUS:
        issues.append("release findings status must stay blocked until evidence exists")
    if profile.release_bundle_gate != release_candidate_bundle.RELEASE_BUNDLE_TOOL:
        issues.append("release findings must depend on I33-S05 bundle gate")
    if profile.release_bundle_evidence != release_candidate_bundle.RELEASE_BUNDLE_EVIDENCE:
        issues.append("release findings must consume the I33-S05 bundle evidence")
    if profile.release_bundle_manifest != release_candidate_bundle.RELEASE_BUNDLE_MANIFEST:
        issues.append("release findings must consume the I33-S05 bundle manifest")

    issues.extend(release_candidate_bundle.validate_release_bundle(root))

    categories = {route.category for route in profile.routes}
    for category in profile.required_categories:
        if category not in categories:
            issues.append(f"release findings missing category {category}")
    route_ids = [route.finding_id for route in profile.routes]
    if len(route_ids) != len(set(route_ids)):
        issues.append("release finding IDs must be unique")
    for route in profile.routes:
        if route.frozen_contract_impact != FROZEN_CONTRACT_UNCHANGED:
            issues.append(f"{route.finding_id}: frozen contract impact must be unchanged")
        if not route.target_backlog:
            issues.append(f"{route.finding_id}: target backlog is required")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "triaged_at",
        "repository_commit",
        "release_candidate_bundle",
        "release_bundle_status",
        "bundle_manifest",
        "release_blockers",
        "implementation_findings",
        "architecture_findings",
        "board_findings",
        "deferred_work_status",
        "post_v0_1_backlog",
        "post_v0_1_backlog_status",
        "frozen_contract_status",
        "tag_decision_status",
        "retest_commands",
        "retest_status",
        "findings_result",
        "findings_blockers",
        "signed_off_by",
        "signed_off_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing release findings field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    complete = parse_release_findings(
        release_findings_template(profile)
        .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
    )
    if not audit_release_findings(complete).accepted:
        issues.append("complete release findings record must audit as accepted")

    blocker = parse_release_findings(
        release_findings_template(profile)
        .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("release_bundle_status=accepted", "release_bundle_status=blocked")
        .replace("post_v0_1_backlog_status=opened", "post_v0_1_backlog_status=blocked")
        .replace(f"findings_result={FINDINGS_RESULT_OPENED}", f"findings_result={FINDINGS_RESULT_BLOCKER}")
        .replace("findings_blockers=none", "findings_blockers=bundle_evidence_missing")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
    )
    if not audit_release_findings(blocker).accepted:
        issues.append("explained release findings blocker record must audit as accepted")

    followup = parse_release_findings(
        release_findings_template(profile)
        .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(f"findings_result={FINDINGS_RESULT_OPENED}", f"findings_result={FINDINGS_RESULT_BLOCKER}")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
    )
    if audit_release_findings(followup).status != FINDINGS_NEEDS_FOLLOWUP:
        issues.append("findings blocker without named blockers must need follow-up")

    default_audit = load_release_findings_audit(root)
    if default_audit.status != FINDINGS_BLOCKED:
        issues.append("default release findings audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_FINDINGS_DOC)
    for token in (
        "Story: I33-S06",
        RELEASE_FINDINGS_TOOL,
        RELEASE_FINDINGS_EVIDENCE.as_posix(),
        RELEASE_FINDINGS_MANIFEST.as_posix(),
        release_candidate_bundle.RELEASE_BUNDLE_TOOL,
        release_candidate_bundle.RELEASE_BUNDLE_EVIDENCE.as_posix(),
        release_candidate_bundle.RELEASE_BUNDLE_MANIFEST.as_posix(),
        "release_blockers",
        "implementation_findings",
        "architecture_findings",
        "board_findings",
        "frozen_contract_status",
        "post_v0_1_backlog",
        "retest_commands",
        FINDINGS_RESULT_OPENED,
        FINDINGS_RESULT_BLOCKER,
        "post-v0.1",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_FINDINGS_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        release_findings_manifest_template()
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release findings objects are not JSON serializable: {exc}")

    return tuple(issues)


def _finding_routes() -> tuple[FindingRoute, ...]:
    return (
        FindingRoute(
            "physical_board_pass_blocked",
            "I33-S04/I33-S05 release_blockers",
            "release_blockers",
            "I31/I32 board-evidence rerun",
            "Carry as release blocker until board pass or blocker archive exists.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/fpga-first-pass-archive.md",
        ),
        FindingRoute(
            "release_candidate_not_tagged",
            "I33-S04/I33-S05 release_blockers",
            "tag_decision_handoff",
            "release tag decision",
            "Keep tag decision blocked until bundle and findings evidence are accepted.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/release-candidate-bundle.md",
        ),
        FindingRoute(
            "rtl_unsupported_capability_subset",
            "I33-S04 known limitations",
            "implementation_followups",
            "post-v0.1 RTL capability backlog",
            "File capability-transform RTL expansion without changing v0.1 semantics.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/rtl-semantic-closure.md",
        ),
        FindingRoute(
            "multicore_fabric_deferred",
            "I33-S04 known limitations",
            "implementation_followups",
            "post-v0.1 multicore/fabric backlog",
            "Keep multicore and fabric work outside the single-core release claim.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/external-fabric-cpu-boundary.md",
        ),
        FindingRoute(
            "ddr_board_ip_deferred",
            "I33-S04 known limitations",
            "board_followups",
            "I29 external-memory board evidence",
            "Require DDR controller IP and calibrated board evidence before release claims.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/fpga-ddr-wrapper.md",
        ),
        FindingRoute(
            "retro_console_60k_deferred",
            "I34 alternate target",
            "board_followups",
            "I34-S03 through I34-S06",
            "Keep Retro Console 60K work deferred from the 138K first CPU target.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/fpga-retro-console-identity.md",
        ),
        FindingRoute(
            "cacheable_tag_policy_deferred",
            "I33-S04 known limitations",
            "architecture_findings",
            "post-v0.1 architecture or implementation backlog",
            "Require explicit cacheable/tag-sidecar policy before changing external-memory behavior.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/fpga-external-memory-policy.md",
        ),
        FindingRoute(
            "architecture_errata_none_known",
            "I33-S04 known limitations",
            "architecture_findings",
            "architecture backlog only if a late erratum appears",
            "Record that no architecture errata are known for the frozen single-core contract.",
            FROZEN_CONTRACT_UNCHANGED,
            "docs/implementation/release-traceability-audit.md",
        ),
        FindingRoute(
            "release_retest_commands",
            "I33-S05 rerun commands",
            "retest_commands",
            "post-v0.1 retest matrix",
            "Preserve exact rerun commands for every blocker and follow-up route.",
            FROZEN_CONTRACT_UNCHANGED,
            RETEST_COMMANDS_PATH.as_posix(),
        ),
    )


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: FindingsRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> FindingsAudit:
    return FindingsAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        findings_result=record.value("findings_result"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _status_issues(record: FindingsRecord) -> list[str]:
    result = record.value("findings_result")
    issues: list[str] = []
    if result not in {FINDINGS_RESULT_OPENED, FINDINGS_RESULT_BLOCKER, ""}:
        issues.append(f"findings_result must be {FINDINGS_RESULT_OPENED} or {FINDINGS_RESULT_BLOCKER}")
    if record.value("frozen_contract_status") and record.value("frozen_contract_status") != FROZEN_CONTRACT_UNCHANGED:
        issues.append("frozen_contract_status must be unchanged")
    tag_status = record.value("tag_decision_status")
    if tag_status and tag_status == "tagged":
        issues.append("tag_decision_status must not claim a release tag")

    if result == FINDINGS_RESULT_OPENED or not result:
        expected = {
            "release_bundle_status": "accepted",
            "deferred_work_status": "triaged",
            "post_v0_1_backlog_status": "opened",
            "retest_status": "captured",
        }
        for field, value in expected.items():
            if record.value(field) and record.value(field) != value:
                issues.append(f"{field} must be {value}")
    elif result == FINDINGS_RESULT_BLOCKER:
        allowed = {
            "release_bundle_status": {"accepted", "blocked", "failed"},
            "deferred_work_status": {"triaged", "blocked", "incomplete"},
            "post_v0_1_backlog_status": {"opened", "blocked", "incomplete"},
            "retest_status": {"captured", "blocked", "failed"},
        }
        for field, values in allowed.items():
            if record.value(field) and record.value(field) not in values:
                issues.append(f"{field} must be one of {', '.join(sorted(values))}")
    return issues


def _artifact_issues(
    record: FindingsRecord,
    profile: ReleaseFindingsProfile,
) -> list[str]:
    issues: list[str] = []
    concrete_fields = (
        "release_candidate_bundle",
        "bundle_manifest",
        "post_v0_1_backlog",
        "retest_commands",
    )
    for field in concrete_fields:
        if _empty(record.value(field)):
            issues.append(f"{field} must name a concrete artifact path")
    if record.value("release_candidate_bundle") and record.value("release_candidate_bundle") != profile.release_bundle_evidence.as_posix():
        issues.append(f"release_candidate_bundle must be {profile.release_bundle_evidence.as_posix()}")
    if record.value("bundle_manifest") and record.value("bundle_manifest") != profile.release_bundle_manifest.as_posix():
        issues.append(f"bundle_manifest must be {profile.release_bundle_manifest.as_posix()}")
    if record.value("post_v0_1_backlog") and record.value("post_v0_1_backlog") != profile.manifest_path.as_posix():
        issues.append(f"post_v0_1_backlog must be {profile.manifest_path.as_posix()}")
    if record.value("retest_commands") and "i33_s06" not in record.value("retest_commands").lower():
        issues.append("retest_commands must reference I33-S06")
    return issues


def _blocker_issues(record: FindingsRecord) -> list[str]:
    result = record.value("findings_result")
    blockers = record.value("findings_blockers").strip().lower()
    issues: list[str] = []
    if result == FINDINGS_RESULT_BLOCKER and blockers == "none":
        issues.append(f"{FINDINGS_RESULT_BLOCKER} requires named findings_blockers")
    return issues


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

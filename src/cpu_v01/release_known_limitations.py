"""Single-core v0.1 known-limitations and errata freeze gate.

Owner stories:
- I33-S04: freeze known limitations and errata for the single-core release.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import release_candidate_checklist, release_traceability_audit


JsonValue = Any

RELEASE_LIMITATIONS_STORY = "I33-S04"
RELEASE_LIMITATIONS_DOC = release_candidate_checklist.KNOWN_LIMITATIONS_PATH
RELEASE_LIMITATIONS_TOOL = "python tools\\release_known_limitations.py --check"
RELEASE_LIMITATIONS_EVIDENCE = Path(
    "docs/implementation/evidence/i33_s04_known_limitations_freeze.txt"
)
RELEASE_LIMITATIONS_STATUS = "blocked_until_known_limitations_freeze"

LIMITATIONS_ACCEPTED = "accepted"
LIMITATIONS_BLOCKED = "blocked"
LIMITATIONS_INVALID = "invalid"
LIMITATIONS_NEEDS_FOLLOWUP = "needs_followup"

LIMITATIONS_RESULT_FROZEN = "known_limitations_frozen"
LIMITATIONS_RESULT_BLOCKER = "known_limitations_blocker_captured"


@dataclass(frozen=True)
class LimitationItem:
    item_id: str
    category: str
    severity: str
    release_blocker: bool
    title: str
    disposition: str
    evidence: str
    follow_up: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "severity": self.severity,
            "release_blocker": self.release_blocker,
            "title": self.title,
            "disposition": self.disposition,
            "evidence": self.evidence,
            "follow_up": self.follow_up,
        }


@dataclass(frozen=True)
class LimitationField:
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
class ReleaseLimitationsProfile:
    story: str
    status: str
    document_path: Path
    evidence_path: Path
    traceability_gate: str
    required_categories: tuple[str, ...]
    items: tuple[LimitationItem, ...]
    required_fields: tuple[LimitationField, ...]
    accepted_results: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "document_path": self.document_path.as_posix(),
            "evidence_path": self.evidence_path.as_posix(),
            "traceability_gate": self.traceability_gate,
            "required_categories": list(self.required_categories),
            "items": [item.as_dict() for item in self.items],
            "required_fields": [field.as_dict() for field in self.required_fields],
            "accepted_results": list(self.accepted_results),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class LimitationsRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class LimitationsAudit:
    status: str
    message: str
    evidence_path: str
    limitations_result: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == LIMITATIONS_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "limitations_result": self.limitations_result,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def release_limitations_profile() -> ReleaseLimitationsProfile:
    return ReleaseLimitationsProfile(
        story=RELEASE_LIMITATIONS_STORY,
        status=RELEASE_LIMITATIONS_STATUS,
        document_path=RELEASE_LIMITATIONS_DOC,
        evidence_path=RELEASE_LIMITATIONS_EVIDENCE,
        traceability_gate=release_traceability_audit.RELEASE_TRACEABILITY_TOOL,
        required_categories=(
            "unsupported_features",
            "board_blockers",
            "multicore_fabric",
            "ddr_external_memory",
            "cacheable_tag_behavior",
            "architecture_errata",
            "release_scope",
        ),
        items=(
            LimitationItem(
                "rtl_unsupported_capability_subset",
                "unsupported_features",
                "release_note",
                False,
                "Selected capability-transform mnemonics remain outside the single-core RTL release.",
                "CINCADDR, CSETBOUNDS, CSEAL, and CUNSEAL remain documented RTL deferrals.",
                "docs/implementation/rtl-semantic-closure.md",
                "Post-v0.1 RTL capability expansion story.",
            ),
            LimitationItem(
                "physical_board_pass_blocked",
                "board_blockers",
                "release_blocker",
                True,
                "Physical FPGA pass evidence is not yet archived.",
                "Release-candidate tagging remains blocked until I31/I32 evidence is captured or explicitly classified.",
                "docs/implementation/fpga-first-pass-archive.md",
                "Run the Tang Mega Dock with 138K SOM board evidence path.",
            ),
            LimitationItem(
                "retro_console_60k_deferred",
                "board_blockers",
                "release_note",
                False,
                "Tang Retro Console with 60K SOM is a second-board target.",
                "The single-core release target remains Tang Mega Dock with 138K SOM.",
                "docs/implementation/fpga-retro-console-identity.md",
                "Resume I34-S03 through I34-S06 after Mega Dock evidence.",
            ),
            LimitationItem(
                "single_core_only",
                "multicore_fabric",
                "release_note",
                False,
                "The release is single-core only.",
                "Multicore startup, fabric links, coherence, and cross-core debug remain deferred.",
                "docs/implementation/rtl-semantic-closure.md",
                "Open post-v0.1 multicore/fabric RTL backlog.",
            ),
            LimitationItem(
                "ddr_board_ip_deferred",
                "ddr_external_memory",
                "release_note",
                False,
                "Board-specific DDR controller IP and calibrated DDR pass are not claimed.",
                "DDR policy and calibration wrappers exist, but vendor IP, pins, training, and board evidence remain deferred.",
                "docs/implementation/fpga-ddr-wrapper.md",
                "Complete I29-S05 board evidence before claiming DDR pass.",
            ),
            LimitationItem(
                "external_cacheable_tags_deferred",
                "cacheable_tag_behavior",
                "release_note",
                False,
                "External DDR remains normal-uncacheable with no tag sidecar.",
                "Capability CLC/CSC to external DDR fault until a cacheable/tag policy is implemented and verified.",
                "docs/implementation/fpga-external-memory-policy.md",
                "Add coherent/cacheable and tag-sidecar evidence in a later story.",
            ),
            LimitationItem(
                "architecture_errata_none_known",
                "architecture_errata",
                "release_note",
                False,
                "No architecture errata are known for the frozen single-core contract.",
                "Any future erratum must be filed without silently changing the frozen v0.1 contract.",
                "docs/implementation/release-traceability-audit.md",
                "Feed any late errata into I33-S06 release-findings backlog.",
            ),
            LimitationItem(
                "release_candidate_not_tagged",
                "release_scope",
                "release_blocker",
                True,
                "This freeze is not a release tag.",
                "I33-S05 must still build the reproducible bundle and I33-S06 must triage findings.",
                "docs/implementation/release-candidate-checklist.md",
                "Finish I33-S05 and I33-S06 before a tag decision.",
            ),
        ),
        required_fields=(
            LimitationField("story", True, "Must be I33-S04."),
            LimitationField("frozen_at", True, "Local freeze timestamp."),
            LimitationField("repository_commit", True, "Commit under limitations freeze."),
            LimitationField("traceability_audit", True, "I33-S03 traceability evidence path."),
            LimitationField("traceability_status", True, "I33-S03 audit status."),
            LimitationField("limitations_doc", True, "Known-limitations document path."),
            LimitationField("unsupported_features_status", True, "listed or incomplete."),
            LimitationField("board_blockers_status", True, "listed or incomplete."),
            LimitationField("multicore_fabric_status", True, "listed or incomplete."),
            LimitationField("ddr_external_memory_status", True, "listed or incomplete."),
            LimitationField("cacheable_tag_status", True, "listed or incomplete."),
            LimitationField("architecture_errata_status", True, "none_known, listed, or incomplete."),
            LimitationField("release_scope_status", True, "listed or incomplete."),
            LimitationField("limitations_result", True, "Freeze result."),
            LimitationField("release_blockers", True, "none, or named release blockers."),
            LimitationField("signed_off_by", True, "Person or process recording the freeze."),
            LimitationField("signed_off_at", True, "Local sign-off timestamp."),
        ),
        accepted_results=(LIMITATIONS_RESULT_FROZEN, LIMITATIONS_RESULT_BLOCKER),
        handoffs=(
            "I33-S05 consumes the frozen limitations document in the release bundle",
            "I33-S06 consumes release_blockers and errata follow-up as release findings",
        ),
    )


def release_limitations_template(
    profile: ReleaseLimitationsProfile | None = None,
) -> str:
    if profile is None:
        profile = release_limitations_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            "frozen_at=",
            "repository_commit=",
            f"traceability_audit={release_traceability_audit.RELEASE_TRACEABILITY_EVIDENCE.as_posix()}",
            "traceability_status=accepted",
            f"limitations_doc={profile.document_path.as_posix()}",
            "unsupported_features_status=listed",
            "board_blockers_status=listed",
            "multicore_fabric_status=listed",
            "ddr_external_memory_status=listed",
            "cacheable_tag_status=listed",
            "architecture_errata_status=none_known",
            "release_scope_status=listed",
            f"limitations_result={LIMITATIONS_RESULT_FROZEN}",
            "release_blockers=physical_board_pass_blocked,release_candidate_not_tagged",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_limitations(text: str) -> LimitationsRecord:
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
    return LimitationsRecord(fields)


def audit_release_limitations(
    record: LimitationsRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ReleaseLimitationsProfile | None = None,
) -> LimitationsAudit:
    if profile is None:
        profile = release_limitations_profile()
    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S04")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record, profile)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            LIMITATIONS_INVALID,
            "Known-limitations freeze evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I33-S04 fields", "rerun the limitations freeze audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            LIMITATIONS_INVALID,
            "Known-limitations freeze statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix limitation category statuses and artifact paths",),
        )
    if blocker_issues:
        return _audit(
            LIMITATIONS_NEEDS_FOLLOWUP,
            "Known-limitations freeze needs blocker disposition.",
            evidence_path,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("name release blockers or move them to I33-S06 findings",),
        )
    return _audit(
        LIMITATIONS_ACCEPTED,
        "Known-limitations and errata freeze is accepted for release bundling.",
        evidence_path,
        record,
        actions=("hand limitations document to I33-S05", "hand release blockers to I33-S06"),
    )


def load_release_limitations_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> LimitationsAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_limitations_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            LIMITATIONS_BLOCKED,
            "No known-limitations freeze evidence has been captured yet.",
            relative_path.as_posix(),
            LimitationsRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the limitations template",
                "freeze unsupported features, board blockers, deferred DDR/cache/tag behavior, architecture errata, and release scope",
            ),
        )
    try:
        record = parse_release_limitations(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            LIMITATIONS_INVALID,
            "Known-limitations freeze evidence could not be parsed.",
            relative_path.as_posix(),
            LimitationsRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value limitations record", "rerun the I33-S04 audit"),
        )
    return audit_release_limitations(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_limitations_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_limitations_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_release_limitations(
    profile: ReleaseLimitationsProfile | None = None,
) -> str:
    if profile is None:
        profile = release_limitations_profile()
    lines = [
        "# Single-Core v0.1 Known Limitations",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Document path: `{profile.document_path.as_posix()}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        "",
        "## Limitation Items",
        "",
        "| Item | Category | Severity | Release blocker | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in profile.items:
        lines.append(
            f"| `{item.item_id}` | `{item.category}` | `{item.severity}` | `{str(item.release_blocker).lower()}` | `{item.evidence}` |"
        )
    lines.append("")
    return "\n".join(lines)


def validate_release_limitations(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_limitations_profile()
    issues: list[str] = []

    if profile.story != RELEASE_LIMITATIONS_STORY:
        issues.append(f"release limitations story must be {RELEASE_LIMITATIONS_STORY}")
    if profile.status != RELEASE_LIMITATIONS_STATUS:
        issues.append("release limitations status must stay blocked until evidence exists")
    if profile.traceability_gate != release_traceability_audit.RELEASE_TRACEABILITY_TOOL:
        issues.append("release limitations must depend on I33-S03 traceability audit")

    issues.extend(release_traceability_audit.validate_release_traceability(root))

    categories = {item.category for item in profile.items}
    for category in profile.required_categories:
        if category not in categories:
            issues.append(f"release limitations missing category {category}")
    item_ids = [item.item_id for item in profile.items]
    if len(item_ids) != len(set(item_ids)):
        issues.append("release limitation item IDs must be unique")
    for item in profile.items:
        if not item.evidence:
            issues.append(f"{item.item_id}: evidence path is required")
        if not item.follow_up:
            issues.append(f"{item.item_id}: follow-up is required")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "frozen_at",
        "repository_commit",
        "traceability_audit",
        "traceability_status",
        "limitations_doc",
        "unsupported_features_status",
        "board_blockers_status",
        "multicore_fabric_status",
        "ddr_external_memory_status",
        "cacheable_tag_status",
        "architecture_errata_status",
        "release_scope_status",
        "limitations_result",
        "release_blockers",
        "signed_off_by",
        "signed_off_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing release limitations field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    complete = parse_release_limitations(
        release_limitations_template(profile)
        .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
    )
    if not audit_release_limitations(complete).accepted:
        issues.append("complete release limitations record must audit as accepted")

    blocker = parse_release_limitations(
        release_limitations_template(profile)
        .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("board_blockers_status=listed", "board_blockers_status=incomplete")
        .replace(f"limitations_result={LIMITATIONS_RESULT_FROZEN}", f"limitations_result={LIMITATIONS_RESULT_BLOCKER}")
        .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=board_blocker_inventory_incomplete")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
    )
    if not audit_release_limitations(blocker).accepted:
        issues.append("explained release limitations blocker record must audit as accepted")

    followup = parse_release_limitations(
        release_limitations_template(profile)
        .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(f"limitations_result={LIMITATIONS_RESULT_FROZEN}", f"limitations_result={LIMITATIONS_RESULT_BLOCKER}")
        .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=none")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
    )
    if audit_release_limitations(followup).status != LIMITATIONS_NEEDS_FOLLOWUP:
        issues.append("limitations blocker without release blockers must need follow-up")

    default_audit = load_release_limitations_audit(root)
    if default_audit.status != LIMITATIONS_BLOCKED:
        issues.append("default release limitations audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_LIMITATIONS_DOC)
    for token in (
        "Story: I33-S04",
        RELEASE_LIMITATIONS_TOOL,
        RELEASE_LIMITATIONS_EVIDENCE.as_posix(),
        release_traceability_audit.RELEASE_TRACEABILITY_TOOL,
        release_traceability_audit.RELEASE_TRACEABILITY_EVIDENCE.as_posix(),
        "Unsupported Features",
        "Board Blockers",
        "Multicore And Fabric",
        "DDR And External Memory",
        "Cacheable And Tag Behavior",
        "Architecture Errata",
        "Tang Mega Dock with 138K SOM",
        "Tang Retro Console with 60K SOM",
        "CINCADDR",
        "CSETBOUNDS",
        "CSEAL",
        "CUNSEAL",
        "known_limitations_frozen",
        "known_limitations_blocker_captured",
        "I33-S05",
        "I33-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_LIMITATIONS_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release limitations objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: LimitationsRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> LimitationsAudit:
    return LimitationsAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        limitations_result=record.value("limitations_result"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _status_issues(record: LimitationsRecord) -> list[str]:
    result = record.value("limitations_result")
    issues: list[str] = []
    if record.value("traceability_status") and record.value("traceability_status") != "accepted":
        issues.append("traceability_status must be accepted")
    if result not in {LIMITATIONS_RESULT_FROZEN, LIMITATIONS_RESULT_BLOCKER, ""}:
        issues.append(f"limitations_result must be {LIMITATIONS_RESULT_FROZEN} or {LIMITATIONS_RESULT_BLOCKER}")

    expected = {
        "unsupported_features_status": "listed",
        "board_blockers_status": "listed",
        "multicore_fabric_status": "listed",
        "ddr_external_memory_status": "listed",
        "cacheable_tag_status": "listed",
        "release_scope_status": "listed",
    }
    if result == LIMITATIONS_RESULT_FROZEN or not result:
        for field, value in expected.items():
            if record.value(field) and record.value(field) != value:
                issues.append(f"{field} must be {value}")
        if record.value("architecture_errata_status") and record.value("architecture_errata_status") not in {"none_known", "listed"}:
            issues.append("architecture_errata_status must be none_known or listed")
    elif result == LIMITATIONS_RESULT_BLOCKER:
        for field in (*expected, "architecture_errata_status"):
            if record.value(field) and record.value(field) not in {"listed", "none_known", "incomplete"}:
                issues.append(f"{field} must be listed, none_known, or incomplete")
    return issues


def _artifact_issues(
    record: LimitationsRecord,
    profile: ReleaseLimitationsProfile,
) -> list[str]:
    issues: list[str] = []
    traceability = record.value("traceability_audit")
    if _empty(traceability):
        issues.append("traceability_audit must name a concrete artifact path")
    elif "i33_s03" not in traceability.lower():
        issues.append("traceability_audit must reference I33-S03 evidence")
    if record.value("limitations_doc") and record.value("limitations_doc") != profile.document_path.as_posix():
        issues.append(f"limitations_doc must be {profile.document_path.as_posix()}")
    return issues


def _blocker_issues(record: LimitationsRecord) -> list[str]:
    result = record.value("limitations_result")
    blockers = record.value("release_blockers").strip().lower()
    issues: list[str] = []
    if result == LIMITATIONS_RESULT_FROZEN and blockers == "none":
        issues.append(f"{LIMITATIONS_RESULT_FROZEN} requires named release_blockers when release blockers remain")
    if result == LIMITATIONS_RESULT_BLOCKER and blockers == "none":
        issues.append(f"{LIMITATIONS_RESULT_BLOCKER} requires named release_blockers")
    return issues


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""Single-core v0.1 release-candidate bundle gate.

Owner stories:
- I33-S05: produce the reproducible release-candidate bundle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_bram_images,
    fpga_gowin_reports,
    fpga_program_manifest,
    fpga_reproducible_build,
    release_candidate_checklist,
    release_known_limitations,
    release_regression_capture,
    release_traceability_audit,
)


JsonValue = Any

RELEASE_BUNDLE_STORY = "I33-S05"
RELEASE_BUNDLE_DOC = Path("docs/implementation/release-candidate-bundle.md")
RELEASE_BUNDLE_TOOL = "python tools\\release_candidate_bundle.py --check"
RELEASE_BUNDLE_EVIDENCE = release_candidate_checklist.RELEASE_BUNDLE_PATH
RELEASE_BUNDLE_MANIFEST = Path(
    "docs/implementation/evidence/i33_s05_release_candidate_manifest.json"
)
RELEASE_BUNDLE_STATUS = "blocked_until_release_candidate_bundle"

BUNDLE_ACCEPTED = "accepted"
BUNDLE_BLOCKED = "blocked"
BUNDLE_INVALID = "invalid"
BUNDLE_NEEDS_FOLLOWUP = "needs_followup"

BUNDLE_RESULT_CAPTURED = "release_candidate_bundle_captured"
BUNDLE_RESULT_BLOCKER = "release_candidate_bundle_blocker_captured"

TOOL_VERSIONS_PATH = Path("docs/implementation/evidence/i33_s05_tool_versions.txt")
GENERATED_IMAGES_MANIFEST = Path(
    "docs/implementation/evidence/i33_s05_generated_images_manifest.json"
)
BITSTREAM_HASHES_PATH = Path("docs/implementation/evidence/i33_s05_bitstream_hashes.txt")
RERUN_COMMANDS_PATH = Path("docs/implementation/evidence/i33_s05_rerun_commands.txt")


@dataclass(frozen=True)
class BundleArtifact:
    name: str
    category: str
    path: str
    required: bool
    producer_gate: str
    expected_status: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "category": self.category,
            "path": self.path,
            "required": self.required,
            "producer_gate": self.producer_gate,
            "expected_status": self.expected_status,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class BundleField:
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
class ReleaseBundleProfile:
    story: str
    status: str
    evidence_path: Path
    manifest_path: Path
    release_candidate_id: str
    limitations_gate: str
    reproducible_build_gate: str
    required_categories: tuple[str, ...]
    artifacts: tuple[BundleArtifact, ...]
    required_fields: tuple[BundleField, ...]
    accepted_results: tuple[str, ...]
    rerun_commands: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "manifest_path": self.manifest_path.as_posix(),
            "release_candidate_id": self.release_candidate_id,
            "limitations_gate": self.limitations_gate,
            "reproducible_build_gate": self.reproducible_build_gate,
            "required_categories": list(self.required_categories),
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "required_fields": [field.as_dict() for field in self.required_fields],
            "accepted_results": list(self.accepted_results),
            "rerun_commands": list(self.rerun_commands),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class BundleRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class BundleAudit:
    status: str
    message: str
    evidence_path: str
    bundle_result: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == BUNDLE_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "bundle_result": self.bundle_result,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def release_bundle_profile() -> ReleaseBundleProfile:
    return ReleaseBundleProfile(
        story=RELEASE_BUNDLE_STORY,
        status=RELEASE_BUNDLE_STATUS,
        evidence_path=RELEASE_BUNDLE_EVIDENCE,
        manifest_path=RELEASE_BUNDLE_MANIFEST,
        release_candidate_id="single-core-v0.1-rc1",
        limitations_gate=release_known_limitations.RELEASE_LIMITATIONS_TOOL,
        reproducible_build_gate=fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        required_categories=(
            "commit",
            "tool_versions",
            "generated_images",
            "bitstream_hashes",
            "reports",
            "evidence_archives",
            "documents",
            "rerun_commands",
        ),
        artifacts=_bundle_artifacts(),
        required_fields=(
            BundleField("story", True, "Must be I33-S05."),
            BundleField("bundled_at", True, "Local bundle timestamp."),
            BundleField("repository_commit", True, "Commit used for the release-candidate bundle."),
            BundleField("release_candidate_id", True, "Human-readable release candidate ID."),
            BundleField("release_checklist", True, "I33-S01 checklist evidence path."),
            BundleField("release_checklist_status", True, "I33-S01 audit status."),
            BundleField("regression_capture", True, "I33-S02 regression capture evidence path."),
            BundleField("regression_status", True, "I33-S02 audit status."),
            BundleField("traceability_audit", True, "I33-S03 traceability evidence path."),
            BundleField("traceability_status", True, "I33-S03 audit status."),
            BundleField("known_limitations", True, "I33-S04 known-limitations document path."),
            BundleField("known_limitations_status", True, "I33-S04 audit status."),
            BundleField("reproducible_build_manifest", True, "I28-S05 manifest path."),
            BundleField("reproducible_build_status", True, "captured, blocked, or failed."),
            BundleField("tool_versions_path", True, "Tool-version capture path."),
            BundleField("tool_versions_status", True, "captured, blocked, or failed."),
            BundleField("generated_images_manifest", True, "Generated BRAM image manifest path."),
            BundleField("generated_images_status", True, "captured, blocked, or failed."),
            BundleField("bitstream_hashes", True, "Bitstream hash capture path."),
            BundleField("bitstream_status", True, "captured, blocked, or failed."),
            BundleField("gowin_reports", True, "Gowin report bundle path."),
            BundleField("report_status", True, "captured, blocked, or failed."),
            BundleField("evidence_archives", True, "Evidence archive root or manifest path."),
            BundleField("evidence_status", True, "captured, blocked, or failed."),
            BundleField("docs_archive", True, "Document archive path."),
            BundleField("docs_status", True, "captured, blocked, or failed."),
            BundleField("rerun_commands", True, "Rerun-command capture path."),
            BundleField("rerun_status", True, "captured, blocked, or failed."),
            BundleField("bundle_manifest", True, "Release-candidate bundle manifest path."),
            BundleField("bundle_result", True, "Bundle result."),
            BundleField("release_blockers", True, "none, or named release blockers."),
            BundleField("signed_off_by", True, "Person or process recording the bundle."),
            BundleField("signed_off_at", True, "Local sign-off timestamp."),
        ),
        accepted_results=(BUNDLE_RESULT_CAPTURED, BUNDLE_RESULT_BLOCKER),
        rerun_commands=(
            release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_TOOL,
            release_regression_capture.RELEASE_REGRESSION_TOOL,
            release_traceability_audit.RELEASE_TRACEABILITY_TOOL,
            release_known_limitations.RELEASE_LIMITATIONS_TOOL,
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            fpga_program_manifest.FPGA_PROGRAM_MANIFEST_TOOL,
            fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            RELEASE_BUNDLE_TOOL,
        ),
        handoffs=(
            "I33-S06 consumes the release_blockers and bundle manifest to open the release-findings backlog",
            "A tag decision must consume this bundle, not rebuild artifacts silently",
        ),
    )


def release_bundle_template(
    profile: ReleaseBundleProfile | None = None,
) -> str:
    if profile is None:
        profile = release_bundle_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            "bundled_at=",
            "repository_commit=",
            f"release_candidate_id={profile.release_candidate_id}",
            f"release_checklist={release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_EVIDENCE.as_posix()}",
            "release_checklist_status=accepted",
            f"regression_capture={release_regression_capture.RELEASE_REGRESSION_EVIDENCE.as_posix()}",
            "regression_status=accepted",
            f"traceability_audit={release_traceability_audit.RELEASE_TRACEABILITY_EVIDENCE.as_posix()}",
            "traceability_status=accepted",
            f"known_limitations={release_known_limitations.RELEASE_LIMITATIONS_DOC.as_posix()}",
            "known_limitations_status=accepted",
            f"reproducible_build_manifest={fpga_reproducible_build.FPGA_REPRO_BUILD_MANIFEST.as_posix()}",
            "reproducible_build_status=captured",
            f"tool_versions_path={TOOL_VERSIONS_PATH.as_posix()}",
            "tool_versions_status=captured",
            f"generated_images_manifest={GENERATED_IMAGES_MANIFEST.as_posix()}",
            "generated_images_status=captured",
            f"bitstream_hashes={BITSTREAM_HASHES_PATH.as_posix()}",
            "bitstream_status=captured",
            "gowin_reports=build/fpga/tang_mega_138k/first_test/impl",
            "report_status=captured",
            "evidence_archives=docs/implementation/evidence",
            "evidence_status=captured",
            "docs_archive=docs/implementation",
            "docs_status=captured",
            f"rerun_commands={RERUN_COMMANDS_PATH.as_posix()}",
            "rerun_status=captured",
            f"bundle_manifest={profile.manifest_path.as_posix()}",
            f"bundle_result={BUNDLE_RESULT_CAPTURED}",
            "release_blockers=physical_board_pass_blocked,release_candidate_not_tagged",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_bundle(text: str) -> BundleRecord:
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
    return BundleRecord(fields)


def audit_release_bundle(
    record: BundleRecord,
    *,
    evidence_path: str = "<inline>",
    profile: ReleaseBundleProfile | None = None,
) -> BundleAudit:
    if profile is None:
        profile = release_bundle_profile()
    missing_fields = [
        field.name
        for field in profile.required_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S05")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record, profile)
    blocker_issues = _blocker_issues(record)

    if missing_fields:
        return _audit(
            BUNDLE_INVALID,
            "Release-candidate bundle evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required I33-S05 fields", "rerun the bundle audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            BUNDLE_INVALID,
            "Release-candidate bundle statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("fix bundle statuses and artifact paths",),
        )
    if blocker_issues:
        return _audit(
            BUNDLE_NEEDS_FOLLOWUP,
            "Release-candidate bundle needs blocker disposition.",
            evidence_path,
            record,
            blocker_issues=tuple(blocker_issues),
            actions=("name bundle blockers or rerun missing captures",),
        )
    return _audit(
        BUNDLE_ACCEPTED,
        "Release-candidate bundle is accepted for release-findings triage.",
        evidence_path,
        record,
        actions=("hand release blockers and manifest to I33-S06",),
    )


def load_release_bundle_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> BundleAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_bundle_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            BUNDLE_BLOCKED,
            "No release-candidate bundle evidence has been captured yet.",
            relative_path.as_posix(),
            BundleRecord({}),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            actions=(
                f"create {relative_path.as_posix()} from the bundle template",
                "capture commit, tool versions, generated images, bitstream hashes, reports, evidence archives, docs, and rerun commands",
            ),
        )
    try:
        record = parse_release_bundle(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            BUNDLE_INVALID,
            "Release-candidate bundle evidence could not be parsed.",
            relative_path.as_posix(),
            BundleRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value bundle record", "rerun the I33-S05 audit"),
        )
    return audit_release_bundle(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_bundle_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_bundle_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def release_bundle_manifest_template(*, indent: int = 2) -> str:
    profile = release_bundle_profile()
    manifest = profile.as_dict()
    manifest["repository_commit"] = ""
    manifest["bundle_sha256"] = ""
    manifest["created_at"] = ""
    manifest["release_blockers"] = (
        "physical_board_pass_blocked,release_candidate_not_tagged"
    )
    return json.dumps(manifest, indent=indent, sort_keys=True) + "\n"


def render_release_bundle(
    profile: ReleaseBundleProfile | None = None,
) -> str:
    if profile is None:
        profile = release_bundle_profile()
    lines = [
        "# Release Candidate Bundle",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Manifest path: `{profile.manifest_path.as_posix()}`",
        "",
        "## Artifacts",
        "",
        "| Name | Category | Path | Gate | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for artifact in profile.artifacts:
        lines.append(
            f"| `{artifact.name}` | `{artifact.category}` | `{artifact.path}` | `{artifact.producer_gate}` | `{artifact.expected_status}` |"
        )
    lines.extend(["", "## Rerun Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.rerun_commands)
    lines.append("")
    return "\n".join(lines)


def validate_release_bundle(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_bundle_profile()
    issues: list[str] = []

    if profile.story != RELEASE_BUNDLE_STORY:
        issues.append(f"release bundle story must be {RELEASE_BUNDLE_STORY}")
    if profile.status != RELEASE_BUNDLE_STATUS:
        issues.append("release bundle status must stay blocked until evidence exists")
    if profile.limitations_gate != release_known_limitations.RELEASE_LIMITATIONS_TOOL:
        issues.append("release bundle must depend on I33-S04 limitations freeze")
    if profile.reproducible_build_gate != fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL:
        issues.append("release bundle must depend on I28-S05 reproducible build")

    issues.extend(release_known_limitations.validate_release_limitations(root))
    issues.extend(fpga_reproducible_build.validate_fpga_reproducible_build(root))

    categories = {artifact.category for artifact in profile.artifacts}
    for category in profile.required_categories:
        if category not in categories:
            issues.append(f"release bundle missing category {category}")
    artifact_names = [artifact.name for artifact in profile.artifacts]
    if len(artifact_names) != len(set(artifact_names)):
        issues.append("release bundle artifact names must be unique")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "bundled_at",
        "repository_commit",
        "release_candidate_id",
        "release_checklist",
        "release_checklist_status",
        "regression_capture",
        "regression_status",
        "traceability_audit",
        "traceability_status",
        "known_limitations",
        "known_limitations_status",
        "reproducible_build_manifest",
        "reproducible_build_status",
        "tool_versions_path",
        "tool_versions_status",
        "generated_images_manifest",
        "generated_images_status",
        "bitstream_hashes",
        "bitstream_status",
        "gowin_reports",
        "report_status",
        "evidence_archives",
        "evidence_status",
        "docs_archive",
        "docs_status",
        "rerun_commands",
        "rerun_status",
        "bundle_manifest",
        "bundle_result",
        "release_blockers",
        "signed_off_by",
        "signed_off_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing release bundle field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    for command in (
        release_known_limitations.RELEASE_LIMITATIONS_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        fpga_program_manifest.FPGA_PROGRAM_MANIFEST_TOOL,
        fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
    ):
        if command not in profile.rerun_commands:
            issues.append(f"release bundle missing rerun command {command}")

    complete = parse_release_bundle(
        release_bundle_template(profile)
        .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
    )
    if not audit_release_bundle(complete).accepted:
        issues.append("complete release bundle record must audit as accepted")

    blocker = parse_release_bundle(
        release_bundle_template(profile)
        .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("report_status=captured", "report_status=blocked")
        .replace(f"bundle_result={BUNDLE_RESULT_CAPTURED}", f"bundle_result={BUNDLE_RESULT_BLOCKER}")
        .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=gowin_reports_missing")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
    )
    if not audit_release_bundle(blocker).accepted:
        issues.append("explained release bundle blocker record must audit as accepted")

    followup = parse_release_bundle(
        release_bundle_template(profile)
        .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(f"bundle_result={BUNDLE_RESULT_CAPTURED}", f"bundle_result={BUNDLE_RESULT_BLOCKER}")
        .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=none")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
    )
    if audit_release_bundle(followup).status != BUNDLE_NEEDS_FOLLOWUP:
        issues.append("bundle blocker without release blockers must need follow-up")

    default_audit = load_release_bundle_audit(root)
    if default_audit.status != BUNDLE_BLOCKED:
        issues.append("default release bundle audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_BUNDLE_DOC)
    for token in (
        "Story: I33-S05",
        RELEASE_BUNDLE_TOOL,
        RELEASE_BUNDLE_EVIDENCE.as_posix(),
        RELEASE_BUNDLE_MANIFEST.as_posix(),
        release_known_limitations.RELEASE_LIMITATIONS_TOOL,
        release_known_limitations.RELEASE_LIMITATIONS_DOC.as_posix(),
        fpga_reproducible_build.FPGA_REPRO_BUILD_MANIFEST.as_posix(),
        fpga_program_manifest.FPGA_PROGRAM_MANIFEST_TOOL,
        fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        "tool_versions_path",
        "generated_images_manifest",
        "bitstream_hashes",
        "gowin_reports",
        "evidence_archives",
        "docs_archive",
        "rerun_commands",
        BUNDLE_RESULT_CAPTURED,
        BUNDLE_RESULT_BLOCKER,
        "I33-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_BUNDLE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        release_bundle_manifest_template()
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release bundle objects are not JSON serializable: {exc}")

    return tuple(issues)


def _bundle_artifacts() -> tuple[BundleArtifact, ...]:
    return (
        BundleArtifact(
            "repository_commit",
            "commit",
            "<git commit>",
            True,
            "git rev-parse HEAD",
            "captured",
            "bind every release artifact to one commit",
        ),
        BundleArtifact(
            "tool_versions",
            "tool_versions",
            TOOL_VERSIONS_PATH.as_posix(),
            True,
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            "captured",
            "record Python, Verilator, Gowin EDA, and Gowin Programmer versions",
        ),
        BundleArtifact(
            "generated_images",
            "generated_images",
            GENERATED_IMAGES_MANIFEST.as_posix(),
            True,
            fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
            "captured",
            "record generated BRAM image names, hashes, and manifest image IDs",
        ),
        BundleArtifact(
            "bitstream_hashes",
            "bitstream_hashes",
            BITSTREAM_HASHES_PATH.as_posix(),
            True,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            "captured",
            "record exact bitstream paths and SHA-256 hashes",
        ),
        BundleArtifact(
            "gowin_reports",
            "reports",
            "build/fpga/tang_mega_138k/first_test/impl",
            True,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            "captured",
            "archive timing, utilization, ports, warning, and clock reports",
        ),
        BundleArtifact(
            "evidence_archives",
            "evidence_archives",
            "docs/implementation/evidence",
            True,
            release_regression_capture.RELEASE_REGRESSION_TOOL,
            "captured",
            "archive release checklist, regression, traceability, limitations, and board evidence records",
        ),
        BundleArtifact(
            "documentation",
            "documents",
            "docs/implementation",
            True,
            release_known_limitations.RELEASE_LIMITATIONS_TOOL,
            "captured",
            "archive implementation docs needed to read the release candidate",
        ),
        BundleArtifact(
            "rerun_commands",
            "rerun_commands",
            RERUN_COMMANDS_PATH.as_posix(),
            True,
            RELEASE_BUNDLE_TOOL,
            "captured",
            "record exact validation and reproduction commands",
        ),
    )


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: BundleRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    blocker_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> BundleAudit:
    return BundleAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        bundle_result=record.value("bundle_result"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        blocker_issues=blocker_issues,
        actions=actions,
    )


def _status_issues(record: BundleRecord) -> list[str]:
    result = record.value("bundle_result")
    issues: list[str] = []
    expected_accepted = {
        "release_checklist_status": "accepted",
        "regression_status": "accepted",
        "traceability_status": "accepted",
        "known_limitations_status": "accepted",
    }
    for field, value in expected_accepted.items():
        if record.value(field) and record.value(field) != value:
            issues.append(f"{field} must be {value}")
    if result not in {BUNDLE_RESULT_CAPTURED, BUNDLE_RESULT_BLOCKER, ""}:
        issues.append(f"bundle_result must be {BUNDLE_RESULT_CAPTURED} or {BUNDLE_RESULT_BLOCKER}")
    expected_captured = (
        "reproducible_build_status",
        "tool_versions_status",
        "generated_images_status",
        "bitstream_status",
        "report_status",
        "evidence_status",
        "docs_status",
        "rerun_status",
    )
    if result == BUNDLE_RESULT_CAPTURED or not result:
        for field in expected_captured:
            if record.value(field) and record.value(field) != "captured":
                issues.append(f"{field} must be captured")
    elif result == BUNDLE_RESULT_BLOCKER:
        for field in expected_captured:
            if record.value(field) and record.value(field) not in {"captured", "blocked", "failed"}:
                issues.append(f"{field} must be captured, blocked, or failed")
    return issues


def _artifact_issues(
    record: BundleRecord,
    profile: ReleaseBundleProfile,
) -> list[str]:
    issues: list[str] = []
    concrete_fields = (
        "release_checklist",
        "regression_capture",
        "traceability_audit",
        "known_limitations",
        "reproducible_build_manifest",
        "tool_versions_path",
        "generated_images_manifest",
        "bitstream_hashes",
        "gowin_reports",
        "evidence_archives",
        "docs_archive",
        "rerun_commands",
        "bundle_manifest",
    )
    for field in concrete_fields:
        if _empty(record.value(field)):
            issues.append(f"{field} must name a concrete artifact path")
    checks = (
        ("release_checklist", "i33_s01"),
        ("regression_capture", "i33_s02"),
        ("traceability_audit", "i33_s03"),
        ("reproducible_build_manifest", "i28_s05"),
        ("tool_versions_path", "i33_s05"),
        ("generated_images_manifest", "i33_s05"),
        ("bitstream_hashes", "i33_s05"),
        ("rerun_commands", "i33_s05"),
        ("bundle_manifest", "i33_s05"),
    )
    for field, token in checks:
        value = record.value(field)
        if value and token not in value.lower():
            issues.append(f"{field} must reference {token.upper().replace('_', '-')}")
    if record.value("known_limitations") and record.value("known_limitations") != release_known_limitations.RELEASE_LIMITATIONS_DOC.as_posix():
        issues.append(f"known_limitations must be {release_known_limitations.RELEASE_LIMITATIONS_DOC.as_posix()}")
    if record.value("bundle_manifest") and record.value("bundle_manifest") != profile.manifest_path.as_posix():
        issues.append(f"bundle_manifest must be {profile.manifest_path.as_posix()}")
    return issues


def _blocker_issues(record: BundleRecord) -> list[str]:
    result = record.value("bundle_result")
    blockers = record.value("release_blockers").strip().lower()
    issues: list[str] = []
    if result == BUNDLE_RESULT_BLOCKER and blockers == "none":
        issues.append(f"{BUNDLE_RESULT_BLOCKER} requires named release_blockers")
    return issues


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

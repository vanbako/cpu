"""Release-candidate traceability audit gate.

Owner stories:
- I33-S03: audit traceability from architecture stories to implementation artifacts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import release_regression_capture


JsonValue = Any

RELEASE_TRACEABILITY_STORY = "I33-S03"
RELEASE_TRACEABILITY_DOC = Path("docs/implementation/release-traceability-audit.md")
RELEASE_TRACEABILITY_TOOL = "python tools\\release_traceability_audit.py --check"
RELEASE_TRACEABILITY_EVIDENCE = Path(
    "docs/implementation/evidence/i33_s03_release_traceability_audit.txt"
)
RELEASE_TRACEABILITY_SUMMARY = Path(
    "docs/implementation/evidence/i33_s03_traceability_summary.json"
)
RELEASE_TRACEABILITY_STATUS = "blocked_until_traceability_evidence"

TRACEABILITY_ACCEPTED = "accepted"
TRACEABILITY_BLOCKED = "blocked"
TRACEABILITY_INVALID = "invalid"
TRACEABILITY_NEEDS_FOLLOWUP = "needs_followup"

TRACEABILITY_RESULT_CLEAN = "traceability_audit_clean"
TRACEABILITY_RESULT_BLOCKER = "traceability_blocker_captured"

CONFORMANCE_INDEX = Path("docs/implementation/conformance-test-index.md")
BACKLOG_PATH = Path("agile-impl-v0.1.md")
SPEC_REFERENCE_GATE = "python tools\\spec_reference_check.py"
STORY_COVERAGE_GATE = "python tools\\story_coverage.py --check-drift"
TEST_INDEX_GATE = "python -m unittest tests.conformance.test_i01_s03_test_index"
STORY_DRIFT_GATE = "python -m unittest tests.conformance.test_i12_s03_story_drift"

BACKLOG_ROW_RE = re.compile(r"^\| (?P<story>I\d{2}-S\d{2}) \|", re.MULTILINE)
INDEX_ROW_RE = re.compile(
    r"^\| `(?P<path>[^`]+)` \| `(?P<story>I\d{2}-S\d{2})` \| "
    r"(?P<owners>[^|]+) \| (?P<coverage>[^|]+) \|$",
    re.MULTILINE,
)
TEST_STORY_RE = re.compile(r"test_i(?P<epic>\d{2})_s(?P<story>\d{2})_.*\.py$")
DOC_STORY_RE = re.compile(r"^Story: I\d{2}-S\d{2}$", re.MULTILINE)
OWNER_STORY_RE = re.compile(r"`E\d{2}-S\d{2}`")
E15_RE = re.compile(r"`E15-S\d{2}`")


@dataclass(frozen=True)
class TraceabilityCommand:
    name: str
    command: str
    required: bool
    expected_status_field: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "command": self.command,
            "required": self.required,
            "expected_status_field": self.expected_status_field,
        }


@dataclass(frozen=True)
class TraceabilityScope:
    name: str
    required: bool
    rule: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "rule": self.rule,
        }


@dataclass(frozen=True)
class TraceabilityIndexRow:
    path: str
    story: str
    owners: str
    coverage: str

    @property
    def is_test(self) -> bool:
        return self.path.startswith("tests\\")

    @property
    def is_litmus(self) -> bool:
        return self.path.startswith("tests\\litmus\\")

    @property
    def is_rtl(self) -> bool:
        return self.path.startswith("rtl\\")

    @property
    def is_evidence_note(self) -> bool:
        name = Path(self.path.replace("\\", "/")).stem
        return self.path.startswith("docs\\implementation\\") and "evidence" in name

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "path": self.path,
            "story": self.story,
            "owners": self.owners,
            "coverage": self.coverage,
        }


@dataclass(frozen=True)
class TraceabilityInventory:
    backlog_story_count: int
    indexed_artifact_count: int
    indexed_story_count: int
    missing_stories: tuple[str, ...]
    conformance_test_count: int
    litmus_test_count: int
    indexed_conformance_test_count: int
    indexed_litmus_test_count: int
    rtl_artifact_rows: int
    evidence_note_rows: int
    stale_paths: tuple[str, ...]
    unindexed_tests: tuple[str, ...]
    stale_test_rows: tuple[str, ...]
    duplicate_rows: tuple[str, ...]
    unknown_story_rows: tuple[str, ...]
    filename_story_issues: tuple[str, ...]
    owner_coverage_issues: tuple[str, ...]
    unowned_docs: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not (
            self.stale_paths
            or self.unindexed_tests
            or self.stale_test_rows
            or self.duplicate_rows
            or self.unknown_story_rows
            or self.filename_story_issues
            or self.owner_coverage_issues
            or self.unowned_docs
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "backlog_story_count": self.backlog_story_count,
            "indexed_artifact_count": self.indexed_artifact_count,
            "indexed_story_count": self.indexed_story_count,
            "missing_stories": list(self.missing_stories),
            "conformance_test_count": self.conformance_test_count,
            "litmus_test_count": self.litmus_test_count,
            "indexed_conformance_test_count": self.indexed_conformance_test_count,
            "indexed_litmus_test_count": self.indexed_litmus_test_count,
            "rtl_artifact_rows": self.rtl_artifact_rows,
            "evidence_note_rows": self.evidence_note_rows,
            "stale_paths": list(self.stale_paths),
            "unindexed_tests": list(self.unindexed_tests),
            "stale_test_rows": list(self.stale_test_rows),
            "duplicate_rows": list(self.duplicate_rows),
            "unknown_story_rows": list(self.unknown_story_rows),
            "filename_story_issues": list(self.filename_story_issues),
            "owner_coverage_issues": list(self.owner_coverage_issues),
            "unowned_docs": list(self.unowned_docs),
        }


@dataclass(frozen=True)
class TraceabilityProfile:
    story: str
    status: str
    index_path: Path
    evidence_path: Path
    summary_path: Path
    release_regression_gate: str
    commands: tuple[TraceabilityCommand, ...]
    scopes: tuple[TraceabilityScope, ...]
    accepted_results: tuple[str, ...]
    deferred_missing_stories: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "index_path": self.index_path.as_posix(),
            "evidence_path": self.evidence_path.as_posix(),
            "summary_path": self.summary_path.as_posix(),
            "release_regression_gate": self.release_regression_gate,
            "commands": [command.as_dict() for command in self.commands],
            "scopes": [scope.as_dict() for scope in self.scopes],
            "accepted_results": list(self.accepted_results),
            "deferred_missing_stories": list(self.deferred_missing_stories),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class TraceabilityRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class TraceabilityAudit:
    status: str
    message: str
    evidence_path: str
    traceability_result: str
    missing_fields: tuple[str, ...]
    status_issues: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    traceability_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.status == TRACEABILITY_ACCEPTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "traceability_result": self.traceability_result,
            "missing_fields": list(self.missing_fields),
            "status_issues": list(self.status_issues),
            "artifact_issues": list(self.artifact_issues),
            "traceability_issues": list(self.traceability_issues),
            "actions": list(self.actions),
        }


def release_traceability_profile() -> TraceabilityProfile:
    return TraceabilityProfile(
        story=RELEASE_TRACEABILITY_STORY,
        status=RELEASE_TRACEABILITY_STATUS,
        index_path=CONFORMANCE_INDEX,
        evidence_path=RELEASE_TRACEABILITY_EVIDENCE,
        summary_path=RELEASE_TRACEABILITY_SUMMARY,
        release_regression_gate=release_regression_capture.RELEASE_REGRESSION_TOOL,
        commands=(
            TraceabilityCommand(
                "release_regression_capture",
                release_regression_capture.RELEASE_REGRESSION_TOOL,
                True,
                "release_regression_status",
            ),
            TraceabilityCommand("spec_reference", SPEC_REFERENCE_GATE, True, "spec_reference_status"),
            TraceabilityCommand("story_coverage", STORY_COVERAGE_GATE, True, "story_coverage_status"),
            TraceabilityCommand("test_index", TEST_INDEX_GATE, True, "test_index_status"),
            TraceabilityCommand("story_drift", STORY_DRIFT_GATE, True, "story_drift_status"),
            TraceabilityCommand(
                "traceability_summary",
                "python tools\\release_traceability_audit.py --summary-json",
                True,
                "traceability_status",
            ),
        ),
        scopes=(
            TraceabilityScope(
                "implementation_stories",
                True,
                "Every indexed implementation story must exist in agile-impl-v0.1.md; future stories must be explicitly deferred.",
            ),
            TraceabilityScope(
                "conformance_tests",
                True,
                "Every tests\\conformance\\test_*.py file must have an index row and matching story-derived filename.",
            ),
            TraceabilityScope(
                "litmus_tests",
                True,
                "Every tests\\litmus\\test_*.py file must have an index row and matching story-derived filename.",
            ),
            TraceabilityScope(
                "rtl_gate_rows",
                True,
                "Indexed RTL artifacts must exist and name architecture owners plus E15 coverage.",
            ),
            TraceabilityScope(
                "evidence_notes",
                True,
                "Indexed evidence-note rows must exist and carry owner/E15 metadata.",
            ),
            TraceabilityScope(
                "owner_coverage",
                True,
                "Every index row must name at least one E-story owner and at least one E15 coverage item.",
            ),
            TraceabilityScope(
                "stale_references",
                True,
                "Spec-reference and story-coverage drift checks must report zero stale references.",
            ),
        ),
        accepted_results=(TRACEABILITY_RESULT_CLEAN, TRACEABILITY_RESULT_BLOCKER),
        deferred_missing_stories=(),
        handoffs=(
            "I33-S04 consumes this audit's clean owner/E15 inventory before freezing limitations",
            "I33-S05 consumes the traceability summary and command logs for the release bundle",
            "I33-S06 consumes any traceability_blockers as post-release backlog input",
        ),
    )


def implementation_story_ids(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    return tuple(
        match.group("story")
        for match in BACKLOG_ROW_RE.finditer((root / BACKLOG_PATH).read_text(encoding="utf-8"))
    )


def indexed_artifacts(root: Path | None = None) -> tuple[TraceabilityIndexRow, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    return tuple(
        TraceabilityIndexRow(
            path=match.group("path"),
            story=match.group("story"),
            owners=match.group("owners"),
            coverage=match.group("coverage"),
        )
        for match in INDEX_ROW_RE.finditer((root / CONFORMANCE_INDEX).read_text(encoding="utf-8"))
    )


def traceability_inventory(root: Path | None = None) -> TraceabilityInventory:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    stories = implementation_story_ids(root)
    story_set = set(stories)
    rows = indexed_artifacts(root)
    indexed_paths = [row.path for row in rows]
    indexed_story_set = {row.story for row in rows}

    current_conformance_tests = {
        _repo_path(path, root)
        for path in (root / "tests" / "conformance").glob("test_*.py")
    }
    current_litmus_tests = {
        _repo_path(path, root)
        for path in (root / "tests" / "litmus").glob("test_*.py")
    }
    indexed_conformance_tests = {
        row.path for row in rows if row.path.startswith("tests\\conformance\\")
    }
    indexed_litmus_tests = {
        row.path for row in rows if row.path.startswith("tests\\litmus\\")
    }

    stale_paths = sorted(
        path
        for path in indexed_paths
        if path.startswith(("docs\\", "tools\\", "tests\\", "src\\", "rtl\\", "constraints\\"))
        and not (root / path.replace("\\", "/")).exists()
    )
    unindexed_tests = sorted(
        (current_conformance_tests | current_litmus_tests)
        - (indexed_conformance_tests | indexed_litmus_tests)
    )
    stale_test_rows = sorted(
        (indexed_conformance_tests | indexed_litmus_tests)
        - (current_conformance_tests | current_litmus_tests)
    )

    seen: set[tuple[str, str]] = set()
    duplicate_rows: list[str] = []
    filename_story_issues: list[str] = []
    owner_coverage_issues: list[str] = []
    unknown_story_rows: list[str] = []
    for row in rows:
        key = (row.path, row.story)
        if key in seen:
            duplicate_rows.append(f"{row.path}:{row.story}")
        seen.add(key)
        if row.story not in story_set:
            unknown_story_rows.append(f"{row.path}:{row.story}")
        if row.is_test:
            match = TEST_STORY_RE.match(Path(row.path).name)
            expected_story = f"I{match.group('epic')}-S{match.group('story')}" if match else ""
            if not match or row.story != expected_story:
                filename_story_issues.append(f"{row.path}:{row.story}")
        if not OWNER_STORY_RE.search(row.owners):
            owner_coverage_issues.append(f"{row.path}:missing_owner")
        if not E15_RE.search(row.coverage):
            owner_coverage_issues.append(f"{row.path}:missing_e15")

    unowned_docs = sorted(
        _repo_path(path, root)
        for path in (root / "docs" / "implementation").glob("*.md")
        if path.name != "README.md"
        and not DOC_STORY_RE.search(path.read_text(encoding="utf-8"))
    )

    return TraceabilityInventory(
        backlog_story_count=len(stories),
        indexed_artifact_count=len(rows),
        indexed_story_count=len(indexed_story_set),
        missing_stories=tuple(story for story in stories if story not in indexed_story_set),
        conformance_test_count=len(current_conformance_tests),
        litmus_test_count=len(current_litmus_tests),
        indexed_conformance_test_count=len(indexed_conformance_tests),
        indexed_litmus_test_count=len(indexed_litmus_tests),
        rtl_artifact_rows=sum(row.is_rtl for row in rows),
        evidence_note_rows=sum(row.is_evidence_note for row in rows),
        stale_paths=tuple(stale_paths),
        unindexed_tests=tuple(unindexed_tests),
        stale_test_rows=tuple(stale_test_rows),
        duplicate_rows=tuple(sorted(duplicate_rows)),
        unknown_story_rows=tuple(sorted(unknown_story_rows)),
        filename_story_issues=tuple(sorted(filename_story_issues)),
        owner_coverage_issues=tuple(sorted(owner_coverage_issues)),
        unowned_docs=tuple(unowned_docs),
    )


def traceability_current_issues(
    root: Path | None = None,
    profile: TraceabilityProfile | None = None,
) -> tuple[str, ...]:
    if profile is None:
        profile = release_traceability_profile()
    inventory = traceability_inventory(root)
    issues: list[str] = []
    for field in (
        "stale_paths",
        "unindexed_tests",
        "stale_test_rows",
        "duplicate_rows",
        "unknown_story_rows",
        "filename_story_issues",
        "owner_coverage_issues",
        "unowned_docs",
    ):
        for value in getattr(inventory, field):
            issues.append(f"{field}: {value}")
    unexpected_missing = sorted(
        set(inventory.missing_stories) - set(profile.deferred_missing_stories)
    )
    for story in unexpected_missing:
        issues.append(f"missing implementation story is not deferred: {story}")
    stale_deferred = sorted(
        set(profile.deferred_missing_stories) - set(inventory.missing_stories)
    )
    for story in stale_deferred:
        issues.append(f"deferred missing story is no longer missing: {story}")
    return tuple(issues)


def release_traceability_template(
    profile: TraceabilityProfile | None = None,
    inventory: TraceabilityInventory | None = None,
    root: Path | None = None,
) -> str:
    if profile is None:
        profile = release_traceability_profile()
    if inventory is None:
        inventory = traceability_inventory(root)
    return "\n".join(
        (
            f"story={profile.story}",
            "audited_at=",
            "repository_commit=",
            f"release_regression_capture={release_regression_capture.RELEASE_REGRESSION_EVIDENCE.as_posix()}",
            "release_regression_status=accepted",
            "spec_reference_log=docs/implementation/evidence/i33_s03_spec_reference.log",
            "spec_reference_status=passed",
            "story_coverage_log=docs/implementation/evidence/i33_s03_story_coverage.log",
            "story_coverage_status=passed",
            "test_index_log=docs/implementation/evidence/i33_s03_test_index.log",
            "test_index_status=passed",
            "story_drift_log=docs/implementation/evidence/i33_s03_story_drift.log",
            "story_drift_status=passed",
            f"traceability_summary={profile.summary_path.as_posix()}",
            "traceability_status=passed",
            f"indexed_artifact_count={inventory.indexed_artifact_count}",
            f"indexed_story_count={inventory.indexed_story_count}",
            f"conformance_test_count={inventory.conformance_test_count}",
            f"litmus_test_count={inventory.litmus_test_count}",
            f"rtl_artifact_rows={inventory.rtl_artifact_rows}",
            f"evidence_note_rows={inventory.evidence_note_rows}",
            "unindexed_tests=none",
            "stale_references=none",
            "missing_owner_coverage=none",
            f"deferred_missing_stories={','.join(profile.deferred_missing_stories) or 'none'}",
            f"traceability_result={TRACEABILITY_RESULT_CLEAN}",
            "traceability_blockers=none",
            "signed_off_by=",
            "signed_off_at=",
            "",
        )
    )


def parse_release_traceability(text: str) -> TraceabilityRecord:
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
    return TraceabilityRecord(fields)


def audit_release_traceability(
    record: TraceabilityRecord,
    *,
    evidence_path: str = "<inline>",
    profile: TraceabilityProfile | None = None,
) -> TraceabilityAudit:
    if profile is None:
        profile = release_traceability_profile()

    required_fields = (
        "story",
        "audited_at",
        "repository_commit",
        "release_regression_capture",
        "release_regression_status",
        "spec_reference_log",
        "spec_reference_status",
        "story_coverage_log",
        "story_coverage_status",
        "test_index_log",
        "test_index_status",
        "story_drift_log",
        "story_drift_status",
        "traceability_summary",
        "traceability_status",
        "indexed_artifact_count",
        "indexed_story_count",
        "conformance_test_count",
        "litmus_test_count",
        "rtl_artifact_rows",
        "evidence_note_rows",
        "unindexed_tests",
        "stale_references",
        "missing_owner_coverage",
        "deferred_missing_stories",
        "traceability_result",
        "traceability_blockers",
        "signed_off_by",
        "signed_off_at",
    )
    missing_fields = [field for field in required_fields if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I33-S03")

    status_issues = _status_issues(record)
    artifact_issues = _artifact_issues(record, profile)
    traceability_issues = _traceability_record_issues(record, profile)

    if missing_fields:
        return _audit(
            TRACEABILITY_INVALID,
            "Release traceability audit evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            traceability_issues=tuple(traceability_issues),
            actions=("complete all required I33-S03 fields", "rerun the traceability audit"),
        )
    if status_issues or artifact_issues:
        return _audit(
            TRACEABILITY_INVALID,
            "Release traceability audit statuses or artifacts are inconsistent.",
            evidence_path,
            record,
            status_issues=tuple(status_issues),
            artifact_issues=tuple(artifact_issues),
            traceability_issues=tuple(traceability_issues),
            actions=("fix traceability command statuses and artifact paths",),
        )
    if traceability_issues:
        return _audit(
            TRACEABILITY_NEEDS_FOLLOWUP,
            "Release traceability audit needs blocker disposition.",
            evidence_path,
            record,
            traceability_issues=tuple(traceability_issues),
            actions=("fix index ownership or file concrete release blockers",),
        )
    return _audit(
        TRACEABILITY_ACCEPTED,
        "Release traceability audit is accepted for limitations freeze.",
        evidence_path,
        record,
        actions=("hand traceability summary to I33-S04 and I33-S05",),
    )


def load_release_traceability_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> TraceabilityAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_traceability_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return _audit(
            TRACEABILITY_BLOCKED,
            "No release traceability audit evidence has been captured yet.",
            relative_path.as_posix(),
            TraceabilityRecord({}),
            missing_fields=(
                "audited_at",
                "repository_commit",
                "traceability_summary",
                "signed_off_by",
                "signed_off_at",
            ),
            actions=(
                f"create {relative_path.as_posix()} from the traceability template",
                "capture spec-reference, story-coverage, test-index, story-drift, and traceability-summary logs",
            ),
        )
    try:
        record = parse_release_traceability(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            TRACEABILITY_INVALID,
            "Release traceability audit evidence could not be parsed.",
            relative_path.as_posix(),
            TraceabilityRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value traceability record", "rerun the I33-S03 audit"),
        )
    return audit_release_traceability(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def release_traceability_json(*, indent: int = 2) -> str:
    return json.dumps(
        release_traceability_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def traceability_summary_json(root: Path | None = None, *, indent: int = 2) -> str:
    return json.dumps(
        traceability_inventory(root).as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_release_traceability(
    profile: TraceabilityProfile | None = None,
) -> str:
    if profile is None:
        profile = release_traceability_profile()
    lines = [
        "# Release Traceability Audit",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Index path: `{profile.index_path.as_posix()}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Summary path: `{profile.summary_path.as_posix()}`",
        "",
        "## Commands",
        "",
        "| Name | Command | Status field |",
        "| --- | --- | --- |",
    ]
    for command in profile.commands:
        lines.append(
            f"| `{command.name}` | `{command.command}` | `{command.expected_status_field}` |"
        )
    lines.extend(["", "## Scopes", ""])
    lines.extend(f"- `{scope.name}`: {scope.rule}" for scope in profile.scopes)
    lines.extend(["", "## Deferred Missing Stories", ""])
    lines.extend(f"- `{story}`" for story in profile.deferred_missing_stories)
    lines.append("")
    return "\n".join(lines)


def validate_release_traceability(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = release_traceability_profile()
    issues: list[str] = []

    if profile.story != RELEASE_TRACEABILITY_STORY:
        issues.append(f"release traceability story must be {RELEASE_TRACEABILITY_STORY}")
    if profile.status != RELEASE_TRACEABILITY_STATUS:
        issues.append("release traceability status must stay blocked until evidence exists")
    if profile.release_regression_gate != release_regression_capture.RELEASE_REGRESSION_TOOL:
        issues.append("release traceability must depend on I33-S02 regression capture")

    issues.extend(release_regression_capture.validate_release_regression_capture(root))

    command_names = {command.name for command in profile.commands}
    for required in (
        "release_regression_capture",
        "spec_reference",
        "story_coverage",
        "test_index",
        "story_drift",
        "traceability_summary",
    ):
        if required not in command_names:
            issues.append(f"release traceability missing command {required}")
    scope_names = {scope.name for scope in profile.scopes}
    for required in (
        "implementation_stories",
        "conformance_tests",
        "litmus_tests",
        "rtl_gate_rows",
        "evidence_notes",
        "owner_coverage",
        "stale_references",
    ):
        if required not in scope_names:
            issues.append(f"release traceability missing scope {required}")

    inventory = traceability_inventory(root)
    for current_issue in traceability_current_issues(root, profile):
        issues.append(f"current traceability issue: {current_issue}")
    if inventory.conformance_test_count != inventory.indexed_conformance_test_count:
        issues.append("conformance test count must match indexed conformance test count")
    if inventory.litmus_test_count != inventory.indexed_litmus_test_count:
        issues.append("litmus test count must match indexed litmus test count")
    if inventory.rtl_artifact_rows <= 0:
        issues.append("release traceability must see indexed RTL artifact rows")
    if inventory.evidence_note_rows <= 0:
        issues.append("release traceability must see indexed evidence-note rows")

    complete = parse_release_traceability(
        release_traceability_template(profile, inventory)
        .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
    )
    if not audit_release_traceability(complete).accepted:
        issues.append("complete release traceability record must audit as accepted")

    blocker = parse_release_traceability(
        release_traceability_template(profile, inventory)
        .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("traceability_status=passed", "traceability_status=failed")
        .replace("unindexed_tests=none", "unindexed_tests=tests\\conformance\\test_i99_s01_new.py")
        .replace(f"traceability_result={TRACEABILITY_RESULT_CLEAN}", f"traceability_result={TRACEABILITY_RESULT_BLOCKER}")
        .replace("traceability_blockers=none", "traceability_blockers=unindexed_test")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
    )
    if not audit_release_traceability(blocker).accepted:
        issues.append("explained release traceability blocker record must audit as accepted")

    followup = parse_release_traceability(
        release_traceability_template(profile, inventory)
        .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("unindexed_tests=none", "unindexed_tests=tests\\conformance\\test_i99_s01_new.py")
        .replace(f"traceability_result={TRACEABILITY_RESULT_CLEAN}", f"traceability_result={TRACEABILITY_RESULT_BLOCKER}")
        .replace("signed_off_by=", "signed_off_by=release-manager")
        .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
    )
    if audit_release_traceability(followup).status != TRACEABILITY_NEEDS_FOLLOWUP:
        issues.append("traceability blocker without named blockers must need follow-up")

    default_audit = load_release_traceability_audit(root)
    if default_audit.status != TRACEABILITY_BLOCKED:
        issues.append("default release traceability audit must be blocked without evidence")

    doc = _read_if_exists(root / RELEASE_TRACEABILITY_DOC)
    for token in (
        "Story: I33-S03",
        RELEASE_TRACEABILITY_TOOL,
        RELEASE_TRACEABILITY_EVIDENCE.as_posix(),
        RELEASE_TRACEABILITY_SUMMARY.as_posix(),
        release_regression_capture.RELEASE_REGRESSION_TOOL,
        release_regression_capture.RELEASE_REGRESSION_EVIDENCE.as_posix(),
        SPEC_REFERENCE_GATE,
        STORY_COVERAGE_GATE,
        TEST_INDEX_GATE,
        STORY_DRIFT_GATE,
        "conformance-test-index.md",
        "owner_coverage",
        "E15",
        "rtl_artifact_rows",
        "evidence_note_rows",
        TRACEABILITY_RESULT_CLEAN,
        TRACEABILITY_RESULT_BLOCKER,
        "I33-S04",
        "I33-S05",
        "I33-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{RELEASE_TRACEABILITY_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(inventory.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"release traceability objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: TraceabilityRecord,
    *,
    missing_fields: tuple[str, ...] = (),
    status_issues: tuple[str, ...] = (),
    artifact_issues: tuple[str, ...] = (),
    traceability_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> TraceabilityAudit:
    return TraceabilityAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        traceability_result=record.value("traceability_result"),
        missing_fields=missing_fields,
        status_issues=status_issues,
        artifact_issues=artifact_issues,
        traceability_issues=traceability_issues,
        actions=actions,
    )


def _status_issues(record: TraceabilityRecord) -> list[str]:
    result = record.value("traceability_result")
    issues: list[str] = []
    if record.value("release_regression_status") and record.value("release_regression_status") != "accepted":
        issues.append("release_regression_status must be accepted")
    if result not in {TRACEABILITY_RESULT_CLEAN, TRACEABILITY_RESULT_BLOCKER, ""}:
        issues.append(f"traceability_result must be {TRACEABILITY_RESULT_CLEAN} or {TRACEABILITY_RESULT_BLOCKER}")

    expected = {
        "spec_reference_status": "passed",
        "story_coverage_status": "passed",
        "test_index_status": "passed",
        "story_drift_status": "passed",
        "traceability_status": "passed",
    }
    if result == TRACEABILITY_RESULT_CLEAN or not result:
        for field, value in expected.items():
            if record.value(field) and record.value(field) != value:
                issues.append(f"{field} must be {value}")
    elif result == TRACEABILITY_RESULT_BLOCKER:
        for field in expected:
            if record.value(field) and record.value(field) not in {"passed", "failed", "blocked"}:
                issues.append(f"{field} must be passed, failed, or blocked")
    return issues


def _artifact_issues(
    record: TraceabilityRecord,
    profile: TraceabilityProfile,
) -> list[str]:
    issues: list[str] = []
    artifacts = (
        "release_regression_capture",
        "spec_reference_log",
        "story_coverage_log",
        "test_index_log",
        "story_drift_log",
        "traceability_summary",
    )
    for field in artifacts:
        if _empty(record.value(field)):
            issues.append(f"{field} must name a concrete artifact path")
    regression = record.value("release_regression_capture")
    if regression and "i33_s02" not in regression.lower():
        issues.append("release_regression_capture must reference I33-S02 evidence")
    summary = record.value("traceability_summary")
    if summary and summary != profile.summary_path.as_posix():
        issues.append(f"traceability_summary must be {profile.summary_path.as_posix()}")
    return issues


def _traceability_record_issues(
    record: TraceabilityRecord,
    profile: TraceabilityProfile,
) -> list[str]:
    result = record.value("traceability_result")
    blockers = record.value("traceability_blockers").strip().lower()
    issues: list[str] = []
    issue_fields = (
        "unindexed_tests",
        "stale_references",
        "missing_owner_coverage",
    )
    if result == TRACEABILITY_RESULT_CLEAN:
        for field in issue_fields:
            if record.value(field).strip().lower() != "none":
                issues.append(f"{TRACEABILITY_RESULT_CLEAN} requires {field}=none")
        if blockers != "none":
            issues.append(f"{TRACEABILITY_RESULT_CLEAN} requires traceability_blockers=none")
    if result == TRACEABILITY_RESULT_BLOCKER and blockers == "none":
        issues.append(f"{TRACEABILITY_RESULT_BLOCKER} requires named traceability_blockers")
    deferred = tuple(
        value.strip()
        for value in record.value("deferred_missing_stories").split(",")
        if value.strip() and value.strip().lower() != "none"
    )
    if deferred != profile.deferred_missing_stories:
        issues.append("deferred_missing_stories must match the explicit future-story backlog")
    for field in (
        "indexed_artifact_count",
        "indexed_story_count",
        "conformance_test_count",
        "litmus_test_count",
        "rtl_artifact_rows",
        "evidence_note_rows",
    ):
        value = record.value(field)
        if value and not value.isdigit():
            issues.append(f"{field} must be numeric")
    return issues


def _empty(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "missing", "blocked"}


def _repo_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix().replace("/", "\\")


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

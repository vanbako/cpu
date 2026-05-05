#!/usr/bin/env python3
"""Report implementation story coverage from backlog and test index.

Owner stories:
- I01-S03: story-derived conformance test index.
- I12-S02: story coverage report.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


STORY_ROW_RE = re.compile(r"^\| (?P<story>I\d{2}-S\d{2}) \|")
DOC_STORY_RE = re.compile(r"^Story: I\d{2}-S\d{2}$", re.MULTILINE)
INDEX_ROW_RE = re.compile(
    r"^\| `(?P<path>[^`]+)` \| `(?P<story>I\d{2}-S\d{2})` \| "
    r"(?P<owners>[^|]+) \| (?P<coverage>[^|]+) \|$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class IndexedArtifact:
    story: str
    path: str
    owners: str
    coverage: str

    @property
    def is_test(self) -> bool:
        return self.path.startswith("tests\\")


@dataclass(frozen=True)
class StoryCoverageRow:
    story: str
    status: str
    artifacts: tuple[IndexedArtifact, ...]

    @property
    def artifact_paths(self) -> tuple[str, ...]:
        return tuple(artifact.path for artifact in self.artifacts)


@dataclass(frozen=True)
class StoryCoverageReport:
    rows: tuple[StoryCoverageRow, ...]

    @property
    def tested_count(self) -> int:
        return sum(row.status == "tested" for row in self.rows)

    @property
    def docs_or_tool_count(self) -> int:
        return sum(row.status == "docs/tool" for row in self.rows)

    @property
    def missing_count(self) -> int:
        return sum(row.status == "missing" for row in self.rows)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def implementation_story_ids(backlog_path: Path) -> tuple[str, ...]:
    stories: list[str] = []
    for line in backlog_path.read_text(encoding="utf-8").splitlines():
        match = STORY_ROW_RE.match(line)
        if match:
            stories.append(match.group("story"))
    return tuple(stories)


def indexed_artifacts(index_path: Path) -> tuple[IndexedArtifact, ...]:
    return tuple(
        IndexedArtifact(
            story=match.group("story"),
            path=match.group("path"),
            owners=match.group("owners"),
            coverage=match.group("coverage"),
        )
        for match in INDEX_ROW_RE.finditer(index_path.read_text(encoding="utf-8"))
    )


def coverage_report(root: Path | None = None) -> StoryCoverageReport:
    if root is None:
        root = repo_root()
    stories = implementation_story_ids(root / "agile-impl-v0.1.md")
    artifacts_by_story: dict[str, list[IndexedArtifact]] = {story: [] for story in stories}
    for artifact in indexed_artifacts(root / "docs" / "implementation" / "conformance-test-index.md"):
        artifacts_by_story.setdefault(artifact.story, []).append(artifact)

    rows: list[StoryCoverageRow] = []
    for story in stories:
        artifacts = tuple(artifacts_by_story.get(story, ()))
        if any(artifact.is_test for artifact in artifacts):
            status = "tested"
        elif artifacts:
            status = "docs/tool"
        else:
            status = "missing"
        rows.append(StoryCoverageRow(story, status, artifacts))
    return StoryCoverageReport(tuple(rows))


def drift_issues(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = repo_root()
    artifacts = indexed_artifacts(root / "docs" / "implementation" / "conformance-test-index.md")
    indexed_paths = [artifact.path for artifact in artifacts]
    current_test_paths = {
        _repo_path(path, root)
        for directory in (root / "tests" / "conformance", root / "tests" / "litmus")
        for path in directory.glob("test_*.py")
    }
    missing_artifact_paths: list[str] = []
    for path in indexed_paths:
        if not path.startswith(("tests\\", "docs\\", "tools\\")):
            continue
        if not (root / Path(path.replace("\\", "/"))).exists():
            missing_artifact_paths.append(path)

    unowned_doc_paths: list[str] = []
    for path in sorted((root / "docs" / "implementation").glob("*.md")):
        if path.name == "README.md":
            continue
        if not DOC_STORY_RE.search(path.read_text(encoding="utf-8")):
            unowned_doc_paths.append(_repo_path(path, root))

    return drift_issues_from_inventory(
        indexed_paths=indexed_paths,
        current_test_paths=current_test_paths,
        missing_artifact_paths=missing_artifact_paths,
        unowned_doc_paths=unowned_doc_paths,
    )


def drift_issues_from_inventory(
    *,
    indexed_paths: Sequence[str],
    current_test_paths: Sequence[str] | set[str],
    missing_artifact_paths: Sequence[str] = (),
    unowned_doc_paths: Sequence[str] = (),
) -> tuple[str, ...]:
    indexed_test_paths = {path for path in indexed_paths if path.startswith("tests\\")}
    current_test_path_set = set(current_test_paths)

    issues: list[str] = []
    for path in sorted(current_test_path_set - indexed_test_paths):
        issues.append(f"test file is missing from conformance index: {path}")
    for path in sorted(indexed_test_paths - current_test_path_set):
        issues.append(f"conformance index has stale test artifact: {path}")
    for path in sorted(missing_artifact_paths):
        issues.append(f"conformance index artifact does not exist: {path}")
    for path in sorted(unowned_doc_paths):
        issues.append(f"implementation doc has no Story owner: {path}")

    return tuple(issues)


def render_report(report: StoryCoverageReport) -> str:
    lines = [
        "# Implementation Story Coverage",
        "",
        f"Stories: {len(report.rows)}",
        f"Tested: {report.tested_count}",
        f"Docs/tool only: {report.docs_or_tool_count}",
        f"Missing: {report.missing_count}",
        "",
        "| Story | Status | Artifacts |",
        "| --- | --- | --- |",
    ]
    for row in report.rows:
        artifacts = ", ".join(f"`{path}`" for path in row.artifact_paths) or "-"
        lines.append(f"| `{row.story}` | {row.status} | {artifacts} |")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="print only missing story rows",
    )
    parser.add_argument(
        "--check-drift",
        action="store_true",
        help="fail if tests, index rows, or implementation docs drift",
    )
    args = parser.parse_args(argv)

    if args.check_drift:
        issues = drift_issues()
        if issues:
            print("Story coverage drift issues:")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print("Story coverage drift issues: 0")
        return 0

    report = coverage_report()
    if args.missing_only:
        report = StoryCoverageReport(
            tuple(row for row in report.rows if row.status == "missing")
        )
    print(render_report(report))
    return 0


def _repo_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix().replace("/", "\\")


if __name__ == "__main__":
    raise SystemExit(main())

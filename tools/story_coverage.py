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
    args = parser.parse_args(argv)

    report = coverage_report()
    if args.missing_only:
        report = StoryCoverageReport(
            tuple(row for row in report.rows if row.status == "missing")
        )
    print(render_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

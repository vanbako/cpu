#!/usr/bin/env python3
"""Check CPU v0.1 spec story IDs, artifact links, and local references."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


STORY_RE = re.compile(r"E\d{2}-S\d{2}")
HEADING_RE = re.compile(r"^#### (E\d{2}-S\d{2}):")
PATH_RE = re.compile(r"`((?:spec|spikes|tools)/[^`]+|design\.md|agile-v0\.1\.md)`")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def story_prefix(story_id: str) -> int:
    return int(story_id[1:3])


def markdown_files(root: Path) -> list[Path]:
    files = [root / "agile-v0.1.md", root / "design.md"]
    files.extend(sorted((root / "spec").glob("*.md")))
    files.extend(sorted((root / "spikes").glob("*.md")))
    return [p for p in files if p.exists()]


def parse_story_blocks(agile_text: str) -> dict[str, str]:
    lines = agile_text.splitlines()
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            starts.append((match.group(1), index))

    blocks: dict[str, str] = {}
    for block_index, (story_id, start) in enumerate(starts):
        end = starts[block_index + 1][1] if block_index + 1 < len(starts) else len(lines)
        blocks[story_id] = "\n".join(lines[start:end])
    return blocks


def agile_line_story_map(agile_text: str) -> dict[int, str]:
    lines = agile_text.splitlines()
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            starts.append((match.group(1), index))

    story_by_line: dict[int, str] = {}
    for block_index, (story_id, start) in enumerate(starts):
        end = starts[block_index + 1][1] if block_index + 1 < len(starts) else len(lines) + 1
        for line_no in range(start, end):
            story_by_line[line_no] = story_id
    return story_by_line


def artifact_story_id(path: Path) -> str | None:
    match = STORY_RE.search(path.name)
    return match.group(0) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-epic",
        action="append",
        default=[],
        help="Also require artifacts for this epic number, for example 15.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    include_epics = {int(value) for value in args.include_epic}
    completed_epics = set(range(1, 15)) | include_epics

    agile = read_text(root / "agile-v0.1.md")
    blocks = parse_story_blocks(agile)
    agile_story_by_line = agile_line_story_map(agile)
    required_ids = {
        story_id for story_id in blocks
        if story_prefix(story_id) in completed_epics
    }

    artifact_paths = sorted((root / "spec").glob("E??-S??-*.md"))
    artifact_paths.extend(sorted((root / "spikes").glob("E??-S??-*.md")))
    artifact_ids = {artifact_story_id(path): path for path in artifact_paths if artifact_story_id(path)}

    issues: list[str] = []

    for story_id in sorted(required_ids):
        block = blocks[story_id]
        linked_paths = [match.group(1) for match in PATH_RE.finditer(block)]
        matching_links = [p for p in linked_paths if story_id in Path(p).name]
        if not matching_links:
            issues.append(f"{story_id}: no matching artifact path listed in agile story block")
            continue
        for path_text in matching_links:
            if not (root / path_text).exists():
                issues.append(f"{story_id}: artifact path does not exist: {path_text}")

    for story_id, path in sorted(artifact_ids.items()):
        if story_prefix(story_id) in completed_epics and story_id not in blocks:
            issues.append(f"{rel(path, root)}: artifact has no detailed agile story block")

        text = read_text(path)
        first_line = text.splitlines()[0] if text.splitlines() else ""
        if not first_line.startswith(f"# {story_id}:"):
            issues.append(f"{rel(path, root)}: title does not start with '# {story_id}:'")
        if f"Story: {story_id}" not in text:
            issues.append(f"{rel(path, root)}: missing 'Story: {story_id}' header")
        if not re.search(r"^Status: (Complete|Spike complete|In progress)$", text, re.MULTILINE):
            issues.append(f"{rel(path, root)}: missing recognized Status header")

    valid_story_ids = set(blocks) | set(artifact_ids)
    for path in markdown_files(root):
        text = read_text(path)
        for match in STORY_RE.finditer(text):
            story_id = match.group(0)
            if story_id not in valid_story_ids:
                line_no = text.count("\n", 0, match.start()) + 1
                issues.append(f"{rel(path, root)}:{line_no}: unknown story ID {story_id}")

        for match in PATH_RE.finditer(text):
            path_text = match.group(1)
            if not (root / path_text).exists():
                line_no = text.count("\n", 0, match.start()) + 1
                current_story = agile_story_by_line.get(line_no) if path.name == "agile-v0.1.md" else None
                if current_story and story_prefix(current_story) not in completed_epics:
                    continue
                issues.append(f"{rel(path, root)}:{line_no}: missing local reference {path_text}")

    print(f"Required story IDs checked: {len(required_ids)}")
    print(f"Artifact story IDs found: {len(artifact_ids)}")
    print(f"Markdown files scanned: {len(markdown_files(root))}")
    print(f"Issues: {len(issues)}")
    for issue in issues:
        print(f"- {issue}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

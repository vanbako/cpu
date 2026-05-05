"""I01-S03 conformance tests for the story-derived test index."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs" / "implementation" / "conformance-test-index.md"
LOCAL_CHECKS = "docs\\implementation\\local-checks.md"

ROW_RE = re.compile(
    r"^\| `(?P<path>[^`]+)` \| `(?P<story>I\d{2}-S\d{2})` \| "
    r"(?P<owners>[^|]+) \| (?P<coverage>[^|]+) \|$",
    re.MULTILINE,
)
TEST_STORY_RE = re.compile(r"test_i(?P<epic>\d{2})_s(?P<story>\d{2})_.*\.py$")
ARCH_STORY_RE = re.compile(r"`E\d{2}-S\d{2}`")


def repo_path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("/", "\\")


def indexed_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for match in ROW_RE.finditer(INDEX.read_text(encoding="utf-8")):
        rows[match.group("path")] = {
            "story": match.group("story"),
            "owners": match.group("owners"),
            "coverage": match.group("coverage"),
        }
    return rows


class ConformanceTestIndexTests(unittest.TestCase):
    def test_index_artifact_exists_and_identifies_story(self) -> None:
        text = INDEX.read_text(encoding="utf-8")

        self.assertIn("# Conformance Test Index", text)
        self.assertIn("Story: I01-S03", text)

    def test_every_current_test_file_is_indexed_once(self) -> None:
        expected = {
            repo_path(path)
            for directory in (ROOT / "tests" / "conformance", ROOT / "tests" / "litmus")
            for path in directory.glob("test_*.py")
        }
        rows = indexed_rows()

        self.assertEqual(set(rows) & expected, expected)

    def test_test_rows_match_filename_story_and_name_e15_coverage(self) -> None:
        for path, row in indexed_rows().items():
            if not path.startswith("tests\\"):
                continue

            match = TEST_STORY_RE.match(Path(path).name)
            self.assertIsNotNone(match, path)
            expected_story = f"I{match.group('epic')}-S{match.group('story')}"

            self.assertEqual(row["story"], expected_story, path)
            self.assertRegex(row["coverage"], r"`E15-S\d{2}`|`tools\\[^`]+`", path)
            self.assertRegex(row["owners"], ARCH_STORY_RE, path)

    def test_local_checks_acceptance_artifact_is_indexed(self) -> None:
        rows = indexed_rows()

        self.assertIn(LOCAL_CHECKS, rows)
        self.assertEqual(rows[LOCAL_CHECKS]["story"], "I01-S02")
        self.assertIn("E15-S01", rows[LOCAL_CHECKS]["coverage"])
        self.assertIn("E15-S02", rows[LOCAL_CHECKS]["coverage"])


if __name__ == "__main__":
    unittest.main()

"""I12-S02 conformance tests for implementation story coverage reporting."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "story_coverage.py"


def load_story_coverage_module():
    spec = importlib.util.spec_from_file_location("story_coverage_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StoryCoverageReportTests(unittest.TestCase):
    def test_backlog_story_parser_covers_i01_through_i15_rows(self) -> None:
        tool = load_story_coverage_module()

        stories = tool.implementation_story_ids(ROOT / "agile-impl-v0.1.md")

        self.assertIn("I01-S01", stories)
        self.assertIn("I12-S02", stories)
        self.assertIn("I15-S03", stories)
        self.assertEqual(len(stories), len(set(stories)))

    def test_report_classifies_tested_doc_only_and_missing_stories(self) -> None:
        tool = load_story_coverage_module()

        report = tool.coverage_report(ROOT)
        rows = {row.story: row for row in report.rows}

        self.assertEqual(rows["I01-S01"].status, "tested")
        self.assertEqual(rows["I01-S02"].status, "docs/tool")
        self.assertEqual(rows["I12-S02"].status, "tested")
        self.assertEqual(rows["I12-S03"].status, "tested")
        self.assertEqual(rows["I13-S02"].status, "tested")
        self.assertEqual(rows["I13-S03"].status, "tested")
        self.assertEqual(rows["I14-S01"].status, "missing")
        self.assertGreater(report.tested_count, 0)
        self.assertGreater(report.missing_count, 0)

    def test_rendered_report_lists_artifacts_and_missing_future_work(self) -> None:
        tool = load_story_coverage_module()

        rendered = tool.render_report(tool.coverage_report(ROOT))

        self.assertIn("# Implementation Story Coverage", rendered)
        self.assertIn("`I12-S02` | tested", rendered)
        self.assertIn("test_i12_s02_story_coverage.py", rendered)
        self.assertIn("`I14-S01` | missing", rendered)

    def test_missing_only_cli_filters_report_rows(self) -> None:
        tool = load_story_coverage_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--missing-only"])

        output = stream.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("`I14-S01` | missing", output)
        self.assertNotIn("`I01-S01` | tested", output)

    def test_documentation_artifact_names_command_and_statuses(self) -> None:
        text = (ROOT / "docs" / "implementation" / "story-coverage.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I12-S02", text)
        self.assertIn("python tools\\story_coverage.py", text)
        self.assertIn("`tested`", text)
        self.assertIn("`docs/tool`", text)
        self.assertIn("`missing`", text)


if __name__ == "__main__":
    unittest.main()

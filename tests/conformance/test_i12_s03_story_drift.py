"""I12-S03 conformance tests for story coverage drift checks."""

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
    spec = importlib.util.spec_from_file_location("story_coverage_tool_drift", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StoryCoverageDriftTests(unittest.TestCase):
    def test_current_repo_has_no_story_coverage_drift(self) -> None:
        tool = load_story_coverage_module()

        self.assertEqual(tool.drift_issues(ROOT), ())

    def test_drift_check_finds_missing_stale_and_unowned_artifacts(self) -> None:
        tool = load_story_coverage_module()

        issues = "\n".join(
            tool.drift_issues_from_inventory(
                indexed_paths=("tests\\conformance\\test_i99_s98_stale.py",),
                current_test_paths={"tests\\conformance\\test_i99_s99_new.py"},
                missing_artifact_paths=("tests\\conformance\\test_i99_s98_stale.py",),
                unowned_doc_paths=("docs\\implementation\\unowned.md",),
            )
        )

        self.assertIn("missing from conformance index", issues)
        self.assertIn("stale test artifact", issues)
        self.assertIn("artifact does not exist", issues)
        self.assertIn("implementation doc has no Story owner", issues)

    def test_check_drift_cli_succeeds_for_current_repo(self) -> None:
        tool = load_story_coverage_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check-drift"])

        self.assertEqual(result, 0)
        self.assertIn("Story coverage drift issues: 0", stream.getvalue())


if __name__ == "__main__":
    unittest.main()

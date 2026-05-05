"""I12-S01 conformance tests for the one-command local check runner."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "local_checks.py"


def load_local_checks_module():
    spec = importlib.util.spec_from_file_location("local_checks_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LocalCheckRunnerTests(unittest.TestCase):
    def test_runner_plan_covers_spec_tests_litmus_and_whitespace(self) -> None:
        tool = load_local_checks_module()

        checks = tool.local_checks(python="python")
        labels = tuple(check.label for check in checks)
        commands = tuple(check.command for check in checks)

        self.assertEqual(
            labels,
            (
                "spec references",
                "constants model",
                "story coverage drift",
                "conformance tests",
                "litmus tests",
                "whitespace",
            ),
        )
        self.assertIn(("python", "tools/spec_reference_check.py"), commands)
        self.assertIn(("python", "tools/spec_constants_model.py"), commands)
        self.assertIn(
            (
                "python",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/conformance",
                "-p",
                "test_*.py",
            ),
            commands,
        )
        self.assertIn(("python", "tools/story_coverage.py", "--check-drift"), commands)
        self.assertIn(
            (
                "python",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/litmus",
                "-p",
                "test_*.py",
            ),
            commands,
        )
        self.assertIn(("git", "diff", "--check"), commands)

    def test_list_mode_reports_commands_without_running_them(self) -> None:
        tool = load_local_checks_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        output = stream.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("spec references:", output)
        self.assertIn("story coverage drift:", output)
        self.assertIn("conformance tests:", output)
        self.assertIn("git diff --check", output)

    def test_local_checks_documentation_names_one_command_runner(self) -> None:
        text = (ROOT / "docs" / "implementation" / "local-checks.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I01-S02", text)
        self.assertIn("I12-S01", text)
        self.assertIn("python tools\\local_checks.py", text)


if __name__ == "__main__":
    unittest.main()

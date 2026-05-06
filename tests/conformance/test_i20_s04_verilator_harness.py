"""I20-S04 conformance tests for the Verilator differential harness skeleton."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "verilator_diff_harness.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import golden_traces, verilator_harness


def load_tool_module():
    spec = importlib.util.spec_from_file_location("verilator_diff_harness_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerilatorHarnessTests(unittest.TestCase):
    def test_missing_verilator_skips_cleanly_unless_required(self) -> None:
        skipped = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(skipped.status, verilator_harness.HarnessStatus.SKIPPED)
        self.assertTrue(skipped.ok)
        self.assertIn("not found", skipped.message)
        self.assertGreater(skipped.case_count, 0)

        failed = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                verilator_executable="verilator-not-on-path-for-test",
                require_verilator=True,
            )
        )
        self.assertEqual(failed.status, verilator_harness.HarnessStatus.FAILED)
        self.assertFalse(failed.ok)

    def test_compare_retire_traces_accepts_golden_corpus_shape(self) -> None:
        expected = golden_traces.golden_trace_corpus_as_dicts()

        self.assertIsNone(verilator_harness.compare_retire_traces(expected, expected))

    def test_compare_retire_traces_reports_first_mismatch_by_case_and_packet(self) -> None:
        expected = golden_traces.golden_trace_corpus_as_dicts()
        observed = json.loads(json.dumps(expected))
        observed[1]["packets"][0]["mnemonic"] = "BAD"

        mismatch = verilator_harness.compare_retire_traces(expected, tuple(observed))

        self.assertIsNotNone(mismatch)
        assert mismatch is not None
        self.assertEqual(mismatch.case_id, "integer_ops.add_mul")
        self.assertEqual(mismatch.sequence, 0)
        self.assertEqual(mismatch.field, "mnemonic")
        self.assertIn("integer_ops.add_mul packet 0", mismatch.message())

    def test_observed_trace_comparison_passes_for_matching_json(self) -> None:
        expected = golden_traces.golden_trace_corpus_as_dicts()

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                observed_cases=expected,
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.PASSED)
        self.assertEqual(
            result.packet_count,
            sum(len(case["packets"]) for case in expected),
        )
        self.assertIn("matches", result.message)

    def test_non_dry_run_names_integrated_top_level_boundary(self) -> None:
        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                dry_run=False,
                verilator_executable=sys.executable,
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.SKIPPED)
        self.assertIn("integrated cpu_v01_core top-level", result.message)
        self.assertNotIn("I20-S05", result.message)

    def test_cli_returns_success_for_skip_and_failure_for_required_missing_verilator(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--verilator", "verilator-not-on-path-for-test"])

        self.assertEqual(result, 0)
        self.assertIn("Status: SKIPPED", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--verilator",
                    "verilator-not-on-path-for-test",
                    "--require-verilator",
                ]
            )

        self.assertEqual(result, 1)
        self.assertIn("Status: FAILED", stream.getvalue())

    def test_documentation_artifact_names_commands_and_mismatch_behavior(self) -> None:
        text = (ROOT / "docs" / "implementation" / "verilator-differential-harness.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S04", text)
        self.assertIn("python tools\\verilator_diff_harness.py", text)
        self.assertIn("retire_trace.json", text)
        self.assertIn("first mismatch by case ID", text)
        self.assertIn("skips cleanly", text)


if __name__ == "__main__":
    unittest.main()

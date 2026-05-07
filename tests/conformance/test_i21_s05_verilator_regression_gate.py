"""I21-S05 conformance tests for the Verilator regression-suite gate."""

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

from cpu_v01 import verilator_harness


def load_tool_module():
    spec = importlib.util.spec_from_file_location("verilator_diff_harness_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerilatorRegressionGateTests(unittest.TestCase):
    def test_regression_registry_partitions_fast_and_slow_cases(self) -> None:
        fast = verilator_harness.regression_cases(verilator_harness.HarnessSuite.FAST)
        slow = verilator_harness.regression_cases(verilator_harness.HarnessSuite.SLOW)
        all_cases = verilator_harness.regression_cases(verilator_harness.HarnessSuite.ALL)

        self.assertGreater(len(fast), 0)
        self.assertGreater(len(slow), 0)
        self.assertEqual(len(all_cases), len(fast) + len(slow))
        self.assertIn("integer_ops.add_mul", {case.case_id for case in fast})
        self.assertIn(
            "syscall_trap.sys_pause_iret_binary",
            {case.case_id for case in fast},
        )
        self.assertIn(
            "relocation.branch_call_data_object",
            {case.case_id for case in slow},
        )
        self.assertIn(
            "debug_metadata.lines_symbols_registers",
            {case.case_id for case in slow},
        )

    def test_case_id_selection_builds_golden_and_toolchain_expected_traces(self) -> None:
        expected = verilator_harness.expected_retire_cases(
            case_ids=(
                "integer_ops.add_mul",
                "syscall_trap.sys_pause_iret_binary",
            )
        )

        self.assertEqual(
            tuple(case["case_id"] for case in expected),
            ("integer_ops.add_mul", "syscall_trap.sys_pause_iret_binary"),
        )
        self.assertEqual(expected[0]["regression_source"], "golden")
        self.assertEqual(expected[1]["regression_source"], "toolchain")
        self.assertEqual(expected[1]["source_golden_case_id"], "traps.sys_iret_return")

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                observed_cases=expected,
                case_ids=(
                    "integer_ops.add_mul",
                    "syscall_trap.sys_pause_iret_binary",
                ),
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.PASSED)
        self.assertEqual(result.case_count, 2)
        self.assertEqual(result.packet_count, 4)

    def test_first_mismatch_diagnostics_use_selected_case_id(self) -> None:
        expected = verilator_harness.expected_retire_cases(
            case_ids=("syscall_trap.sys_pause_iret_binary",)
        )
        observed = json.loads(json.dumps(expected))
        observed[0]["packets"][1]["mnemonic"] = "BAD"

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                observed_cases=tuple(observed),
                case_ids=("syscall_trap.sys_pause_iret_binary",),
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.FAILED)
        self.assertIsNotNone(result.mismatch)
        assert result.mismatch is not None
        self.assertEqual(result.mismatch.case_id, "syscall_trap.sys_pause_iret_binary")
        self.assertEqual(result.mismatch.sequence, 1)
        self.assertIn("packet 1", result.message)

    def test_missing_verilator_skip_preserves_selected_fast_suite(self) -> None:
        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                suite=verilator_harness.HarnessSuite.FAST,
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.SKIPPED)
        self.assertTrue(result.ok)
        self.assertEqual(result.suite, verilator_harness.HarnessSuite.FAST)
        self.assertEqual(
            result.case_count,
            len(verilator_harness.regression_cases(verilator_harness.HarnessSuite.FAST)),
        )
        self.assertIn("not found", result.message)

    def test_cli_lists_cases_and_filters_by_case_id(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--suite", "fast", "--list-cases"])

        self.assertEqual(result, 0)
        output = stream.getvalue()
        self.assertIn("integer_ops.add_mul\tgolden\tfast", output)
        self.assertIn("syscall_trap.sys_pause_iret_binary\ttoolchain\tfast", output)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--case-id",
                    "syscall_trap.sys_pause_iret_binary",
                    "--verilator",
                    "verilator-not-on-path-for-test",
                ]
            )

        self.assertEqual(result, 0)
        output = stream.getvalue()
        self.assertIn("Status: SKIPPED", output)
        self.assertIn("Selected cases: syscall_trap.sys_pause_iret_binary", output)

    def test_documentation_artifact_names_regression_gate_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "verilator-regression-gate.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I21-S05", text)
        self.assertIn("python tools\\verilator_diff_harness.py --suite fast", text)
        self.assertIn("--case-id", text)
        self.assertIn("fast and slow", text)
        self.assertIn("toolchain", text)
        self.assertIn("first mismatch", text)
        self.assertIn("skips cleanly", text)


if __name__ == "__main__":
    unittest.main()

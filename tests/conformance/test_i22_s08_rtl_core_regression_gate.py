"""I22-S08 conformance tests for the integrated core regression gate."""

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


class RtlCoreRegressionGateTests(unittest.TestCase):
    def test_regression_registry_includes_fast_and_slow_integrated_core_cases(self) -> None:
        fast = verilator_harness.regression_cases(verilator_harness.HarnessSuite.FAST)
        slow = verilator_harness.regression_cases(verilator_harness.HarnessSuite.SLOW)

        fast_integrated = {case.case_id: case for case in fast if case.source == "integrated"}
        slow_integrated = {case.case_id: case for case in slow if case.source == "integrated"}

        self.assertIn("core.shell.reset_idle", fast_integrated)
        self.assertIn("core.fetch_decode.slot1_48bit_placement", fast_integrated)
        self.assertIn("core.scalar.integer_ops_add_mul", fast_integrated)
        self.assertIn("core.cap_mem.memory_tag_ops", slow_integrated)
        self.assertIn("core.control_trap.sys_iret", slow_integrated)
        self.assertIn("core.mmu_tlb.translation_sfence", slow_integrated)
        self.assertIn("core.atomic_cache.llsc_cache", slow_integrated)
        self.assertEqual(
            fast_integrated["core.scalar.integer_ops_add_mul"].top_module,
            "cpu_v01_core_scalar_control_tb",
        )
        self.assertIn(
            "rtl/cpu_v01_core.sv",
            fast_integrated["core.scalar.integer_ops_add_mul"].source_files,
        )
        self.assertEqual(
            slow_integrated["core.control_trap.sys_iret"].golden_trace_case_id,
            "traps.sys_iret_return",
        )

    def test_integrated_case_id_selection_builds_expected_retire_trace(self) -> None:
        expected = verilator_harness.expected_retire_cases(
            case_ids=("core.scalar.integer_ops_add_mul",)
        )

        self.assertEqual(len(expected), 1)
        self.assertEqual(expected[0]["case_id"], "core.scalar.integer_ops_add_mul")
        self.assertEqual(expected[0]["regression_source"], "integrated")
        self.assertEqual(expected[0]["source_golden_case_id"], "integer_ops.add_mul")
        self.assertEqual(len(expected[0]["packets"]), 2)

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                observed_cases=expected,
                case_ids=("core.scalar.integer_ops_add_mul",),
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.PASSED)
        self.assertEqual(result.selected_case_ids, ("core.scalar.integer_ops_add_mul",))

    def test_integrated_first_mismatch_uses_core_case_id(self) -> None:
        expected = verilator_harness.expected_retire_cases(
            case_ids=("core.control_trap.sys_iret",)
        )
        observed = json.loads(json.dumps(expected))
        observed[0]["packets"][1]["mnemonic"] = "BAD"

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                observed_cases=tuple(observed),
                case_ids=("core.control_trap.sys_iret",),
                verilator_executable="verilator-not-on-path-for-test",
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.FAILED)
        self.assertIsNotNone(result.mismatch)
        assert result.mismatch is not None
        self.assertEqual(result.mismatch.case_id, "core.control_trap.sys_iret")
        self.assertIn("packet 1", result.message)

    def test_integrated_verilator_commands_and_deferrals_are_explicit(self) -> None:
        commands = verilator_harness.integrated_core_verilator_commands(
            verilator_harness.HarnessSuite.ALL
        )
        deferrals = verilator_harness.integrated_core_deferrals(
            verilator_harness.HarnessSuite.ALL
        )

        self.assertTrue(
            any("--top-module cpu_v01_core_atomic_cache_tb" in command for command in commands)
        )
        self.assertTrue(
            any("rtl/cpu_v01_core_mmu_tlb_tb.sv" in command for command in commands)
        )
        self.assertTrue(any("No retire trace" in deferral for deferral in deferrals))
        self.assertTrue(any("translation and TLB metadata" in deferral for deferral in deferrals))
        self.assertTrue(any("reservation and cache metadata" in deferral for deferral in deferrals))

        result = verilator_harness.run_harness(
            verilator_harness.HarnessConfig(
                build_dir=ROOT / "build" / "verilator",
                case_ids=("core.atomic_cache.llsc_cache",),
                dry_run=False,
                verilator_executable=sys.executable,
            )
        )

        self.assertEqual(result.status, verilator_harness.HarnessStatus.SKIPPED)
        self.assertIn("integrated cpu_v01_core top-level", result.message)
        self.assertTrue(result.deferrals)

    def test_cli_lists_and_selects_integrated_core_cases(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--suite", "all", "--list-cases"])

        self.assertEqual(result, 0)
        output = stream.getvalue()
        self.assertIn("core.scalar.integer_ops_add_mul\tintegrated\tfast\tinteger_ops.add_mul", output)
        self.assertIn("core.atomic_cache.llsc_cache\tintegrated\tslow\t-", output)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--case-id",
                    "core.scalar.integer_ops_add_mul",
                    "--verilator",
                    "verilator-not-on-path-for-test",
                ]
            )

        self.assertEqual(result, 0)
        output = stream.getvalue()
        self.assertIn("Status: SKIPPED", output)
        self.assertIn("Selected cases: core.scalar.integer_ops_add_mul", output)

    def test_documentation_artifact_names_integrated_gate_scope(self) -> None:
        text = (
            ROOT
            / "docs"
            / "implementation"
            / "rtl-integrated-core-regression-gate.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S08", text)
        self.assertIn("python tools\\verilator_diff_harness.py --suite fast", text)
        self.assertIn("core.scalar.integer_ops_add_mul", text)
        self.assertIn("core.atomic_cache.llsc_cache", text)
        self.assertIn("cpu_v01_core_atomic_cache_tb", text)
        self.assertIn("retire_trace.json", text)
        self.assertIn("first mismatch", text)
        self.assertIn("Explicit Deferrals", text)


if __name__ == "__main__":
    unittest.main()

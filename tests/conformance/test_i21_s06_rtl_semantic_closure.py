"""I21-S06 conformance tests for the RTL semantic closure report."""

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
TOOL = ROOT / "tools" / "rtl_semantic_closure.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_readiness, rtl_semantic_closure


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_semantic_closure_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlSemanticClosureTests(unittest.TestCase):
    def test_closure_report_self_validates_and_serializes(self) -> None:
        self.assertEqual(rtl_semantic_closure.validate_rtl_semantic_closure(ROOT), ())
        parsed = json.loads(rtl_semantic_closure.rtl_semantic_closure_json())

        self.assertEqual(
            parsed["status"],
            "single-core fixture-slice semantic closure published",
        )
        self.assertTrue(parsed["instruction_families"])
        self.assertTrue(parsed["golden_cases"])
        self.assertTrue(parsed["invariants"])

    def test_instruction_family_rows_account_for_all_mandatory_mnemonics(self) -> None:
        report = rtl_semantic_closure.rtl_semantic_closure_report()
        mandatory = set(opcodes.mandatory_mnemonics())
        accounted = {
            mnemonic
            for family in report.instruction_families
            for mnemonic in (*family.mnemonics, *family.unsupported_mnemonics)
            if mnemonic in mandatory
        }

        self.assertEqual(accounted, mandatory)
        by_family = {family.family: family for family in report.instruction_families}
        self.assertIn("I21-S01", by_family["integer"].rtl_stories)
        self.assertIn("I21-S02", by_family["system-ordering-csr"].rtl_stories)
        self.assertIn("I21-S03", by_family["cache-maintenance"].rtl_stories)
        self.assertIn("I21-S04", by_family["control-trap"].rtl_stories)
        self.assertEqual(
            set(report.unsupported_mnemonics),
            set(rtl_readiness.rtl_readiness_report().unsupported_mnemonics),
        )

    def test_closure_maps_golden_cases_invariants_and_gates(self) -> None:
        report = rtl_semantic_closure.rtl_semantic_closure_report()

        golden_by_id = {case.case_id: case for case in report.golden_cases}
        self.assertIn("integer_ops.add_mul", golden_by_id)
        self.assertIn("traps.sys_iret_return", golden_by_id)
        self.assertIn("I21-S01", golden_by_id["integer_ops.add_mul"].rtl_status)

        invariant_keys = {invariant.key for invariant in report.invariants}
        self.assertGreaterEqual(
            invariant_keys,
            {
                "capability_monotonicity",
                "tag_non_forgery",
                "precise_fault_effects",
            },
        )
        self.assertIn(
            "python tools/verilator_diff_harness.py --suite fast".replace("/", "\\"),
            report.local_gate_commands,
        )
        self.assertTrue(any("multicore/fabric" in item for item in report.readiness_criteria))

    def test_cli_validates_and_renders_markdown_and_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL semantic closure issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main([])

        self.assertEqual(result, 0)
        markdown = stream.getvalue()
        self.assertIn("Story: I21-S06", markdown)
        self.assertIn("Instruction Families", markdown)
        self.assertIn("Readiness Criteria", markdown)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--format", "json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertIn("unsupported_mnemonics", parsed)

    def test_documentation_artifact_names_closure_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-semantic-closure.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I21-S06", text)
        self.assertIn("python tools\\rtl_semantic_closure.py --check", text)
        self.assertIn("Instruction Families", text)
        self.assertIn("Golden Cases", text)
        self.assertIn("Invariants", text)
        self.assertIn("Unsupported Deferrals", text)
        self.assertIn("Readiness Criteria", text)
        self.assertIn("multicore/fabric", text)


if __name__ == "__main__":
    unittest.main()

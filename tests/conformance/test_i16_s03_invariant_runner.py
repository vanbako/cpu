"""I16-S03 conformance tests for the seed-stable invariant runner."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "invariant_runner.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import invariant_runner


def load_invariant_runner_tool():
    spec = importlib.util.spec_from_file_location("invariant_runner_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InvariantRunnerTests(unittest.TestCase):
    def test_runner_lists_families_and_case_ids(self) -> None:
        families = invariant_runner.available_families()
        case_ids = invariant_runner.invariant_case_ids()

        self.assertEqual(families, ("capability_derivation", "invalid_tag_derivation"))
        self.assertGreater(len(case_ids), 20)
        self.assertTrue(
            any(case_id.startswith("capability_derivation/") for case_id in case_ids)
        )
        self.assertTrue(
            any(case_id.startswith("invalid_tag_derivation/") for case_id in case_ids)
        )

    def test_seed_controls_order_but_not_case_identity(self) -> None:
        first = invariant_runner.run_invariants(seed=7)
        second = invariant_runner.run_invariants(seed=7)
        different = invariant_runner.run_invariants(seed=8)

        self.assertTrue(first.passed)
        self.assertEqual(first.case_ids, second.case_ids)
        self.assertEqual(set(first.case_ids), set(different.case_ids))
        self.assertNotEqual(first.case_ids, different.case_ids)

    def test_family_and_exact_case_replay_are_supported(self) -> None:
        family_ids = invariant_runner.invariant_case_ids(("invalid_tag_derivation",))
        selected_id = family_ids[0]

        report = invariant_runner.run_invariants(
            seed=99,
            families=("invalid_tag_derivation",),
            case_ids=(selected_id,),
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.case_count, 1)
        self.assertEqual(report.case_ids, (selected_id,))
        self.assertEqual(report.requested_families, ("invalid_tag_derivation",))

    def test_invalid_family_or_case_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            invariant_runner.invariant_case_ids(("missing",))
        with self.assertRaises(ValueError):
            invariant_runner.run_invariants(case_ids=("missing/case",))

    def test_rendered_report_records_seed_counts_and_case_statuses(self) -> None:
        selected_id = invariant_runner.invariant_case_ids(("capability_derivation",))[0]
        report = invariant_runner.run_invariants(
            seed=3,
            families=("capability_derivation",),
            case_ids=(selected_id,),
        )

        rendered = invariant_runner.render_report(report)

        self.assertIn("Invariant Run", rendered)
        self.assertIn("Seed: 3", rendered)
        self.assertIn("Cases: 1", rendered)
        self.assertIn("Failed: 0", rendered)
        self.assertIn(f"PASS {selected_id}", rendered)

    def test_cli_lists_and_runs_selected_cases(self) -> None:
        tool = load_invariant_runner_tool()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--family", "invalid_tag_derivation", "--list"])

        self.assertEqual(result, 0)
        self.assertIn("invalid_tag_derivation:", stream.getvalue())

        selected_id = invariant_runner.invariant_case_ids(("invalid_tag_derivation",))[0]
        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--seed",
                    "11",
                    "--family",
                    "invalid_tag_derivation",
                    "--case-id",
                    selected_id,
                ]
            )

        output = stream.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Seed: 11", output)
        self.assertIn(f"PASS {selected_id}", output)


if __name__ == "__main__":
    unittest.main()

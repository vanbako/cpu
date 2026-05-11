"""I31-S06 conformance tests for the first-pass board retest matrix."""

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
TOOL = ROOT / "tools" / "fpga_first_pass_retest_matrix.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_archive, fpga_first_pass_retest_matrix


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_retest_matrix_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaFirstPassRetestMatrixTests(unittest.TestCase):
    def test_first_pass_retest_matrix_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_first_pass_retest_matrix.validate_fpga_first_pass_retest_matrix(ROOT),
            (),
        )

    def test_profile_names_archive_gate_phases_commands_and_assumptions(self) -> None:
        profile = fpga_first_pass_retest_matrix.fpga_first_pass_retest_matrix_profile()

        self.assertEqual(profile.story, "I31-S06")
        self.assertEqual(profile.status, "published_first_cpu_retest_matrix")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.archive_gate, "python tools\\fpga_first_pass_archive.py --check")

        phases = {row.phase for row in profile.matrix_rows}
        for phase in (
            "identity_constraints",
            "sram_programming_observation",
            "failure_replay_classification",
            "final_archive",
            "local_regression_gate",
        ):
            self.assertIn(phase, phases)

        commands = {row.command for row in profile.matrix_rows}
        for command in (
            "python tools\\fpga_first_board_archive.py --check",
            "python tools\\fpga_first_pass_programming.py --check",
            "python tools\\fpga_first_pass_replay.py --check",
            "python tools\\fpga_first_pass_archive.py --check",
            "python tools\\local_checks.py",
        ):
            self.assertIn(command, commands)

        joined = " ".join(profile.known_board_assumptions)
        self.assertIn("Sipeed Tang Mega Dock with 138K SOM", joined)
        self.assertIn("SRAM mode", joined)
        self.assertIn("I25-S01 32-byte packet", joined)

    def test_each_matrix_row_names_captures_rerun_and_acceptance_criteria(self) -> None:
        profile = fpga_first_pass_retest_matrix.fpga_first_pass_retest_matrix_profile()

        for row in profile.matrix_rows:
            self.assertTrue(row.required_captures, row.phase)
            self.assertTrue(row.board_assumptions, row.phase)
            self.assertTrue(row.rerun_when, row.phase)
            self.assertTrue(row.accept_when, row.phase)
            self.assertEqual(
                row.evidence_handoff,
                fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix(),
            )

        programming = profile.row_by_phase("sram_programming_observation")
        self.assertTrue(any("bitstream_sha256" in capture for capture in programming.required_captures))
        self.assertTrue(any("retire_count at least 8" in criterion for criterion in programming.accept_when))

        replay = profile.row_by_phase("failure_replay_classification")
        self.assertTrue(any("first_mismatch" in capture for capture in replay.required_captures))
        self.assertTrue(any("classified" in criterion for criterion in replay.accept_when))

    def test_rendered_matrix_contains_commands_and_acceptance_rules(self) -> None:
        rendered = fpga_first_pass_retest_matrix.render_fpga_first_pass_retest_matrix()

        self.assertIn("Story: I31-S06", rendered)
        self.assertIn("python tools\\fpga_first_pass_archive.py --check", rendered)
        self.assertIn("identity_constraints", rendered)
        self.assertIn("sram_programming_observation", rendered)
        self.assertIn("failure_replay_classification", rendered)
        self.assertIn("first_pass_archived", rendered)
        self.assertIn("blocker_disposition_archived", rendered)

    def test_cli_validates_json_commands_captures_and_criteria(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass retest matrix issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S06")
        self.assertIn("matrix_rows", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--commands"])

        self.assertEqual(result, 0)
        self.assertIn("local_regression_gate", stream.getvalue())
        self.assertIn("local_checks.py", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--captures"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--criteria"])

        self.assertEqual(result, 0)
        self.assertIn("first_pass:", stream.getvalue())
        self.assertIn("blocker:", stream.getvalue())

    def test_documentation_names_commands_captures_assumptions_and_criteria(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-retest-matrix.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S06",
            "python tools\\fpga_first_pass_retest_matrix.py --check",
            "python tools\\fpga_first_pass_archive.py --check",
            "python tools\\fpga_first_board_archive.py --check",
            "python tools\\fpga_first_pass_programming.py --check",
            "python tools\\fpga_first_pass_replay.py --check",
            "python tools\\local_checks.py",
            "identity_constraints",
            "sram_programming_observation",
            "failure_replay_classification",
            "final_archive",
            "local_regression_gate",
            "required captures",
            "known board assumptions",
            "rerun criteria",
            "acceptance criteria",
            "first_pass_archived",
            "blocker_disposition_archived",
            "I31-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

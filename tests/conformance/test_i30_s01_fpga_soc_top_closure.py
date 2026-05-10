"""I30-S01 conformance tests for the FPGA SoC top-level closure plan."""

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
TOOL = ROOT / "tools" / "fpga_soc_top_closure.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_closure


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_top_closure_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocTopClosureTests(unittest.TestCase):
    def test_soc_top_closure_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_top_closure.validate_fpga_soc_top_closure(ROOT), ())

    def test_profile_names_dependency_gates_and_order(self) -> None:
        profile = fpga_soc_top_closure.fpga_soc_top_closure_profile()

        self.assertEqual(profile.story, "I30-S01")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.soc_smoke_gate, "python tools\\fpga_soc_smoke.py --check")
        self.assertEqual(profile.program_loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(profile.debug_evidence_gate, "python tools\\fpga_debug_evidence.py --check")
        self.assertEqual(profile.sequence[0], "I30-S02 data/MMIO decoder")
        self.assertEqual(profile.sequence[-1], "I30-S06 closure evidence archive")
        self.assertIn("physical board pass claims before I31", profile.non_goals)

    def test_shortcut_matrix_maps_blockers_to_owners_tests_validators_and_evidence(self) -> None:
        profile = fpga_soc_top_closure.fpga_soc_top_closure_profile()
        shortcuts = {shortcut.shortcut_id: shortcut for shortcut in profile.shortcuts}

        self.assertIn("data_mmio_decoder_bypass", shortcuts)
        self.assertIn("timer_interrupt_tied_off", shortcuts)
        self.assertIn("uart_pin_mux_missing", shortcuts)
        self.assertIn("gpio_status_led_mux_missing", shortcuts)
        self.assertIn("loader_handoff_absent", shortcuts)
        self.assertIn("top_smoke_evidence_missing", shortcuts)
        self.assertEqual(shortcuts["data_mmio_decoder_bypass"].owner_story, "I30-S02")
        self.assertEqual(shortcuts["loader_handoff_absent"].owner_story, "I30-S04")
        self.assertEqual(shortcuts["top_smoke_evidence_missing"].owner_story, "I30-S05")

        for shortcut in profile.shortcuts:
            with self.subTest(shortcut=shortcut.shortcut_id):
                self.assertTrue(shortcut.testbench.startswith("rtl/"))
                self.assertTrue(shortcut.testbench.endswith(".sv"))
                self.assertTrue(shortcut.validator.startswith("python tools\\"))
                self.assertTrue(shortcut.validator.endswith("--check"))
                self.assertIn("I30-S", shortcut.owner_story)
                self.assertTrue(shortcut.board_evidence_handoff)
                self.assertTrue(shortcut.closure_criteria)

    def test_current_rtl_shortcut_tokens_are_visible(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for shortcut in fpga_soc_top_closure.fpga_soc_top_closure_profile().shortcuts:
            with self.subTest(shortcut=shortcut.shortcut_id):
                self.assertIn(shortcut.rtl_token, top)

    def test_cli_validates_json_matrix_sequence_and_shortcut(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC top closure issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S01")
        self.assertIn("shortcuts", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--matrix"])

        self.assertEqual(result, 0)
        self.assertIn("data_mmio_decoder_bypass\tI30-S02", stream.getvalue())
        self.assertIn("loader_handoff_absent\tI30-S04", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--sequence"])

        self.assertEqual(result, 0)
        self.assertIn("I30-S06 closure evidence archive", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--shortcut", "uart_pin_mux_missing"])

        self.assertEqual(result, 0)
        shortcut = json.loads(stream.getvalue())
        self.assertEqual(shortcut["owner_story"], "I30-S03")

    def test_documentation_names_matrix_commands_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-top-closure.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I30-S01", text)
        self.assertIn("python tools\\fpga_soc_top_closure.py --check", text)
        self.assertIn("python tools\\fpga_soc_smoke.py --check", text)
        self.assertIn("python tools\\fpga_program_loader.py --check", text)
        self.assertIn("python tools\\fpga_debug_evidence.py --check", text)
        for token in (
            "cpu_v01_fpga_top",
            "data_mmio_decoder_bypass",
            "timer_interrupt_tied_off",
            "uart_pin_mux_missing",
            "gpio_status_led_mux_missing",
            "loader_handoff_absent",
            "top_smoke_evidence_missing",
            "I30-S02",
            "I30-S03",
            "I30-S04",
            "I30-S05",
            "I30-S06",
            "rtl/cpu_v01_fpga_top_soc_decoder_tb.sv",
            "python tools\\fpga_soc_top_decoder.py --check",
            "board-evidence handoff",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

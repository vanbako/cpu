"""I23-S05 conformance tests for the FPGA synthesis gate."""

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
TOOL = ROOT / "tools" / "fpga_synthesis_gate.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_synthesis


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_synthesis_gate_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSynthesisGateTests(unittest.TestCase):
    def test_synthesis_gate_self_validation_passes(self) -> None:
        self.assertEqual(fpga_synthesis.validate_fpga_synthesis_gate(ROOT), ())

    def test_gate_names_tang_mega_138k_target_and_sources(self) -> None:
        gate = fpga_synthesis.fpga_synthesis_gate()

        self.assertEqual(gate.story, "I23-S05")
        self.assertEqual(gate.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(gate.device, "GW5AST-LV138PG484A")
        self.assertEqual(gate.ide_package, "PBG484A")
        self.assertEqual(gate.top_module, "cpu_v01_fpga_top")
        self.assertEqual(gate.target_clock_hz, 25_000_000)

        sources = {path.as_posix() for path in gate.source_files}
        self.assertIn("rtl/cpu_v01_pkg.sv", sources)
        self.assertIn("rtl/cpu_v01_core.sv", sources)
        self.assertIn("rtl/cpu_v01_fpga_memories.sv", sources)
        self.assertIn("rtl/cpu_v01_fpga_top.sv", sources)

    def test_gate_requires_gowin_tools_and_optional_openfpgaloader(self) -> None:
        tools = {tool.name: tool for tool in fpga_synthesis.fpga_synthesis_gate().tool_requirements}

        self.assertTrue(tools["Verilator"].required)
        self.assertEqual(tools["Gowin EDA command shell"].executable, "gw_sh")
        self.assertTrue(tools["Gowin Programmer"].required)
        self.assertFalse(tools["openFPGALoader"].required)
        self.assertIn("tangmega138k", tools["openFPGALoader"].role)

    def test_gate_fails_on_missing_clock_reset_and_led_constraints(self) -> None:
        constraints = {
            constraint.logical_signal: constraint
            for constraint in fpga_synthesis.fpga_synthesis_gate().constraint_requirements
        }

        for signal in (
            "board_clk_i",
            "board_reset_n_i",
            "pass_led_o",
            "fail_led_o",
            "heartbeat_led_o",
        ):
            with self.subTest(signal=signal):
                self.assertIn(signal, constraints)
                self.assertTrue(constraints[signal].fail_if_missing)

        self.assertIn("40 ns", constraints["board_clk_i"].constraint_kind)
        self.assertIn("PMOD LED", constraints["pass_led_o"].constraint_kind)

    def test_command_plan_and_gowin_tcl_name_required_flow(self) -> None:
        plan = fpga_synthesis.fpga_synthesis_command_plan()

        self.assertIn("python tools\\fpga_synthesis_gate.py --check", plan)
        self.assertIn("python tools\\fpga_synthesis_gate.py --gowin-tcl", plan)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", plan)

        tcl = fpga_synthesis.gowin_tcl_script()
        self.assertIn("set_device -device_version <verified_B_or_C> GW5AST-LV138PG484A", tcl)
        self.assertIn("set_option -top_module cpu_v01_fpga_top", tcl)
        self.assertIn("add_file -type sv rtl/cpu_v01_pkg.sv", tcl)
        self.assertIn("add_file -type sv rtl/cpu_v01_core.sv", tcl)
        self.assertIn("add_file -type cst constraints/tang_mega_138k_first_test.cst", tcl)
        self.assertIn("add_file -type sdc constraints/tang_mega_138k_first_test.sdc", tcl)
        self.assertIn("run all", tcl)

    def test_gate_reports_and_blockers_are_explicit(self) -> None:
        gate = fpga_synthesis.fpga_synthesis_gate()

        report_paths = {report.path for report in gate.reports}
        self.assertTrue(any("gwsynthesis" in path for path in report_paths))
        self.assertTrue(any("timing" in path for path in report_paths))
        self.assertTrue(any("ports" in path for path in report_paths))
        self.assertTrue(any(path.endswith("*.fs") for path in report_paths))

        blockers = " ".join(gate.blockers)
        self.assertIn("PG484", blockers)
        self.assertIn("FPG676", blockers)
        self.assertIn("board_clk_i", blockers)
        self.assertIn("pass_led_o", blockers)

    def test_cli_validates_renders_json_plan_and_gowin_template(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA synthesis gate issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I23-S05")
        self.assertEqual(parsed["board"], "Sipeed Tang Mega 138K Dock")
        self.assertEqual(parsed["top_module"], "cpu_v01_fpga_top")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--gowin-tcl"])

        self.assertEqual(result, 0)
        self.assertIn("run all", stream.getvalue())

    def test_documentation_artifact_names_commands_constraints_and_next_story(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-synthesis-gate.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S05", text)
        self.assertIn("python tools\\fpga_synthesis_gate.py --check", text)
        self.assertIn("Sipeed Tang Mega 138K Dock", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("cpu_v01_fpga_top", text)
        self.assertIn("gw_sh", text)
        self.assertIn("run all", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("unconstrained_clock_or_reset", text)
        self.assertIn("negative_timing_slack_at_first_test_clock", text)
        self.assertIn("I23-S06", text)


if __name__ == "__main__":
    unittest.main()

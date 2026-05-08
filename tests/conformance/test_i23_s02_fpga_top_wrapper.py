"""I23-S02 conformance tests for the FPGA top wrapper."""

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
TOOL = ROOT / "tools" / "fpga_top_wrapper.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_top


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_top_wrapper_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaTopWrapperTests(unittest.TestCase):
    def test_fpga_top_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(fpga_top.validate_fpga_top_wrapper(ROOT), ())
        for path in fpga_top.FPGA_TOP_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_port_projection_covers_board_status_and_debug_groups(self) -> None:
        ports = fpga_top.fpga_top_ports()
        by_name = {port.name: port for port in ports}

        self.assertEqual(by_name["board_clk_i"].group, "clock_reset")
        self.assertEqual(by_name["board_reset_n_i"].group, "clock_reset")
        self.assertEqual(by_name["pass_led_o"].group, "status")
        self.assertEqual(by_name["fail_led_o"].width, "1")
        self.assertEqual(by_name["status_fault_code_o"].width, "16")
        self.assertEqual(by_name["status_retire_count_o"].width, "32")
        self.assertEqual(by_name["debug_pcc_cursor_low_o"].group, "debug")
        self.assertEqual(by_name["debug_sr_low_o"].width, "8")

    def test_top_source_instantiates_core_synchronizes_reset_and_ties_idle_inputs(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_top",
            "board_clk_i",
            "board_reset_n_i",
            "parameter int RESET_SYNC_STAGES = 2",
            "reset_sync_q <= {reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1}",
            "assign core_rst_n = reset_sync_q[RESET_SYNC_STAGES-1]",
            "cpu_v01_core #(",
            ".RESET_VECTOR(RESET_VECTOR)",
            ".ENABLE_FETCH(1'b0)",
            ".timer_interrupt_pending(1'b0)",
            ".software_interrupt_pending(1'b0)",
            ".external_interrupt_pending(1'b0)",
            ".external_event_valid(1'b0)",
            ".external_event_cause(16'd0)",
            ".debug_halt_request(debug_halt_request_i)",
            ".retire_ready(1'b1)",
            "assign imem_req_ready = 1'b1",
            "assign imem_rsp_valid = 1'b0",
            "assign dmem_req_ready = 1'b1",
            "assign dmem_rsp_valid = 1'b0",
            "assign tagmem_req_ready = 1'b1",
            "assign tagmem_rsp_valid = 1'b0",
            "assign pass_led_o = reset_observed && core_idle && !fault_sticky_q",
            "assign fail_led_o = fault_sticky_q",
            "debug_pcc_cursor_low_o",
            "debug_sr_low_o",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_testbench_checks_reset_status_and_pre_bram_idle_behavior(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_top_tb.sv").read_text(encoding="utf-8")

        self.assertIn("module cpu_v01_fpga_top_tb", tb)
        self.assertIn("FPGA top wrapper reset synchronization failed", tb)
        self.assertIn("FPGA top wrapper did not expose reset-idle status", tb)
        self.assertIn("FPGA top wrapper should not retire before BRAM adapters", tb)
        self.assertIn("FPGA top wrapper should stay memory idle before BRAM adapters", tb)
        self.assertIn("FPGA top wrapper reset debug projection mismatch", tb)
        self.assertIn("debug_pcc_cursor_low_o != 32'h0000_1000", tb)
        self.assertIn("debug_sr_low_o != 8'hC0", tb)

    def test_cli_validates_and_renders_port_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA top wrapper issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        names = {row["name"] for row in parsed}
        self.assertIn("board_clk_i", names)
        self.assertIn("board_reset_n_i", names)
        self.assertIn("pass_led_o", names)
        self.assertIn("status_core_port_activity_o", names)
        self.assertIn("debug_pcc_cursor_low_o", names)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-top-wrapper.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S02", text)
        self.assertIn("rtl/cpu_v01_fpga_top.sv", text)
        self.assertIn("rtl/cpu_v01_fpga_top_tb.sv", text)
        self.assertIn("python tools\\fpga_top_wrapper.py --check", text)
        self.assertIn("cpu_v01_fpga_top_tb", text)
        self.assertIn("cpu_v01_core", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("I23-S03", text)
        self.assertIn("BRAM adapters", text)

    def test_verilator_command_names_fpga_top_sources(self) -> None:
        command = fpga_top.fpga_top_verilator_command()

        self.assertIn("--top-module cpu_v01_fpga_top_tb", command)
        self.assertIn("rtl/cpu_v01_pkg.sv", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_fpga_top.sv", command)
        self.assertIn("rtl/cpu_v01_fpga_top_tb.sv", command)


if __name__ == "__main__":
    unittest.main()

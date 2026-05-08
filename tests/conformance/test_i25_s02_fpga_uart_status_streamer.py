"""I25-S02 conformance tests for the FPGA UART status streamer."""

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
TOOL = ROOT / "tools" / "fpga_uart_status_streamer.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_uart_status


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_uart_status_streamer_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaUartStatusStreamerTests(unittest.TestCase):
    def test_uart_status_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_uart_status.validate_fpga_uart_status(ROOT), ())

    def test_profile_names_uart_packet_gate_and_scenarios(self) -> None:
        profile = fpga_uart_status.fpga_uart_status_profile()

        self.assertEqual(profile.story, "I25-S02")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.output_port, "uart_tx_o")
        self.assertEqual(profile.baud, 115200)
        self.assertEqual(profile.clock_hz, 25_000_000)
        self.assertEqual(profile.interval_cycles, 25_000)
        self.assertEqual(profile.packet_gate, "python tools\\fpga_debug_status_packet.py --check")

        scenarios = {scenario.name: scenario for scenario in profile.scenarios}
        self.assertEqual(scenarios["idle"].pass_fail_state, "idle_or_reset")
        self.assertIn("reset_observed", scenarios["idle"].required_flags)
        self.assertEqual(scenarios["pass"].pass_fail_state, "first_pass")
        self.assertIn("retire_valid", scenarios["pass"].required_flags)
        self.assertEqual(scenarios["fault"].pass_fail_state, "failed")
        self.assertIn("fault_valid", scenarios["fault"].required_flags)
        self.assertTrue(any("retire_ready" in rule for rule in profile.non_interference_rules))

    def test_top_source_assembles_packet_and_instantiates_uart_streamer(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "output logic uart_tx_o",
            "parameter int UART_STATUS_BAUD = 115_200",
            "parameter logic [31:0] DEBUG_BUILD_ID = 32'h2501_C0DE",
            "STATUS_PACKET_MAGIC = 16'hC501",
            "STATUS_PACKET_VERSION = 8'd1",
            "STATUS_PACKET_SIZE_BYTES = 8'd32",
            "uart_status_packet[0 +: 16]",
            "uart_status_packet[224 +: 32] = uart_status_sequence_q",
            "cpu_v01_fpga_uart_status_streamer #(",
            "module cpu_v01_fpga_uart_status_streamer",
            "assign uart_tx_o = (!ENABLE || !tx_busy_q) ? 1'b1 : tx_shift_q[0]",
            "packet_started_o",
            ".retire_ready(1'b1)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_testbenches_check_uart_activity_for_idle_and_pass_paths(self) -> None:
        top_tb = (ROOT / "rtl" / "cpu_v01_fpga_top_tb.sv").read_text(encoding="utf-8")
        first_tb = (ROOT / "rtl" / "cpu_v01_fpga_first_test_tb.sv").read_text(
            encoding="utf-8"
        )

        for text in (top_tb, first_tb):
            self.assertIn(".UART_STATUS_CLOCK_HZ(10)", text)
            self.assertIn(".UART_STATUS_BAUD(10)", text)
            self.assertIn(".UART_STATUS_INTERVAL_CYCLES(2)", text)
            self.assertIn("uart_seen_low_q", text)
            self.assertIn("did not stream a UART status packet", text)

    def test_cli_validates_json_and_command_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA UART status streamer issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I25-S02")
        self.assertEqual(parsed["baud"], 115200)
        self.assertEqual(parsed["output_port"], "uart_tx_o")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        plan = stream.getvalue()
        self.assertIn("cpu_v01_fpga_top_tb", plan)
        self.assertIn("cpu_v01_fpga_first_test_tb", plan)

    def test_documentation_names_uart_profile_scenarios_and_board_procedure(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-uart-status-streamer.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I25-S02", text)
        self.assertIn("python tools\\fpga_uart_status_streamer.py --check", text)
        self.assertIn("115200", text)
        self.assertIn("uart_tx_o", text)
        self.assertIn("32-byte", text)
        self.assertIn("python tools\\fpga_debug_status_packet.py --check", text)
        self.assertIn("idle_or_reset", text)
        self.assertIn("first_pass", text)
        self.assertIn("failed", text)
        self.assertIn("reset_observed", text)
        self.assertIn("retire_valid", text)
        self.assertIn("fault_valid", text)
        self.assertIn("retire_ready", text)
        self.assertIn("Verilator", text)
        self.assertIn("board procedure", text)


if __name__ == "__main__":
    unittest.main()

"""I30-S04 conformance tests for the FPGA SoC loader handoff."""

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
TOOL = ROOT / "tools" / "fpga_soc_loader_handoff.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_program_loader, fpga_soc_loader_handoff


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_loader_handoff_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocLoaderHandoffTests(unittest.TestCase):
    def test_soc_loader_handoff_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_loader_handoff.validate_fpga_soc_loader_handoff(ROOT), ())

    def test_profile_names_dependency_gates_rules_and_bounds(self) -> None:
        profile = fpga_soc_loader_handoff.fpga_soc_loader_handoff_profile()
        rules = {rule.name: rule for rule in profile.rules}

        self.assertEqual(profile.story, "I30-S04")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.program_loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(profile.peripheral_gate, "python tools\\fpga_soc_top_peripherals.py --check")
        self.assertEqual(profile.status_stream_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.debug_packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(profile.target_memory, "data_ram")
        self.assertEqual(profile.target_base_cell, 0x00010000)
        self.assertEqual(profile.target_size_cells, 0x1000)
        self.assertEqual(profile.max_chunk_cells, 16)
        self.assertEqual(profile.status_codes["TAG_POLICY"], 0x2605)
        self.assertIn("--top-module cpu_v01_fpga_top_loader_tb", profile.verilator_command)

        for name in (
            "bounded_data_ram",
            "no_instruction_rom",
            "clear_tag_sidecar",
            "reject_tag_bearing",
            "uart_arbitration",
            "debug_status_report",
        ):
            self.assertIn(name, rules)
        self.assertIn("I30-S05", profile.remaining_handoffs[0])

    def test_executable_handoff_model_covers_accept_reject_and_uart_arbitration(self) -> None:
        ok = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(0x00010004)
        self.assertTrue(ok.accepted)
        self.assertTrue(ok.ram_write)
        self.assertTrue(ok.tag_clear)
        self.assertEqual(ok.status_name, "OK")

        bad_target = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(0x00001000)
        self.assertFalse(bad_target.ram_write)
        self.assertEqual(bad_target.status_code, fpga_program_loader.LOAD_STATUS_BAD_TARGET)

        tagged = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(0x00010004, tag=True)
        self.assertFalse(tagged.ram_write)
        self.assertEqual(tagged.status_code, fpga_program_loader.LOAD_STATUS_TAG_POLICY)

        malformed = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(0x00010004, write=False)
        self.assertFalse(malformed.ram_write)
        self.assertEqual(malformed.status_code, fpga_program_loader.LOAD_STATUS_MALFORMED)

        uart_low = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(
            0x00010004,
            loader_uart_tx=False,
        )
        self.assertFalse(uart_low.uart_tx_o)

    def test_rtl_top_wires_loader_handoff_memory_status_and_uart_arbitration(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "input  logic loader_req_valid_i",
            "output logic loader_req_ready_o",
            "input  cpu_v01_pkg::addr_t loader_req_addr_i",
            "input  cpu_v01_pkg::cell_t loader_req_wdata_i",
            "input  logic loader_req_tag_i",
            "input  logic loader_uart_tx_i",
            "output logic loader_status_valid_o",
            "output logic [15:0] loader_status_code_o",
            "output logic status_fault_valid_o",
            "output logic [15:0] status_fault_code_o",
            "module cpu_v01_fpga_soc_loader_handoff",
            "LOAD_STATUS_BAD_TARGET = 16'h2603",
            "LOAD_STATUS_TAG_POLICY = 16'h2605",
            "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
            "assign tagram_req_wtag = loader_tag_clear_valid ? 1'b0 : tagmem_req_wtag;",
            "loader_status_code_q",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_loader_testbench_covers_accept_reject_status_and_uart_cases(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_top_loader_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_top_loader_tb",
            "FPGA SoC loader handoff did not report LOAD OK",
            "FPGA SoC loader handoff did not write data_ram and clear tag_ram",
            "FPGA SoC loader handoff did not reject instruction_rom target",
            "FPGA SoC loader handoff did not expose debug/status failure code",
            "FPGA SoC loader handoff did not reject tag-bearing traffic",
            "FPGA SoC loader handoff did not reject malformed non-write traffic",
            "FPGA SoC loader handoff did not arbitrate loader UART TX",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_rules_plan_and_decode(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC loader handoff issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S04")
        self.assertIn("rules", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--rules"])

        self.assertEqual(result, 0)
        self.assertIn("bounded_data_ram", stream.getvalue())
        self.assertIn("uart_arbitration", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("rtl/cpu_v01_fpga_top_loader_tb.sv", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--decode", "0x1000"])

        self.assertEqual(result, 0)
        decoded = json.loads(stream.getvalue())
        self.assertEqual(decoded["status_name"], "BAD_TARGET")

    def test_documentation_names_commands_policies_handoffs_and_acceptance(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-loader-handoff.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I30-S04", text)
        self.assertIn("python tools\\fpga_soc_loader_handoff.py --check", text)
        self.assertIn("python tools\\fpga_program_loader.py --check", text)
        self.assertIn("rtl/cpu_v01_fpga_top_loader_tb.sv", text)
        for token in (
            "cpu_v01_fpga_soc_loader_handoff",
            "data_ram",
            "instruction_rom",
            "tag_ram",
            "LOAD_STATUS_BAD_TARGET",
            "TAG_POLICY",
            "loader_uart_tx_i",
            "loader_status_code_o",
            "I30-S05",
            "I32-S01",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

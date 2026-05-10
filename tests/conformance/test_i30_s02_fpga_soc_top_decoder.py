"""I30-S02 conformance tests for the FPGA SoC top data/MMIO decoder."""

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
TOOL = ROOT / "tools" / "fpga_soc_top_decoder.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_decoder


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_top_decoder_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocTopDecoderTests(unittest.TestCase):
    def test_soc_top_decoder_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_top_decoder.validate_fpga_soc_top_decoder(ROOT), ())

    def test_profile_names_gates_sources_and_decode_windows(self) -> None:
        profile = fpga_soc_top_decoder.fpga_soc_top_decoder_profile()
        windows = {window.target: window for window in profile.windows}

        self.assertEqual(profile.story, "I30-S02")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.closure_gate, "python tools\\fpga_soc_top_closure.py --check")
        self.assertEqual(profile.platform_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(profile.uart_gate, "python tools\\fpga_uart_mmio.py --check")
        self.assertEqual(profile.timer_gate, "python tools\\fpga_timer_mmio.py --check")
        self.assertEqual(profile.gpio_gate, "python tools\\fpga_gpio_status.py --check")
        self.assertEqual(profile.testbench, "rtl/cpu_v01_fpga_top_soc_decoder_tb.sv")
        self.assertIn("--top-module cpu_v01_fpga_top_soc_decoder_tb", profile.verilator_command)

        self.assertEqual(windows["data_ram"].base_cell, 0x00010000)
        self.assertEqual(windows["data_ram"].end_cell, 0x00011000)
        self.assertTrue(windows["data_ram"].tag_sidecar)
        self.assertEqual(windows["uart"].base_cell, 0x00F00000)
        self.assertEqual(windows["timer"].base_cell, 0x00F00100)
        self.assertEqual(windows["gpio_status"].base_cell, 0x00F00200)
        self.assertEqual(windows["interrupt_controller"].base_cell, 0x00F00300)
        self.assertEqual(windows["system_identity"].base_cell, 0x00F00400)
        self.assertTrue(all(not window.tag_sidecar for name, window in windows.items() if name != "data_ram"))
        self.assertIn("I30-S03", profile.remaining_handoffs[0])

    def test_executable_decoder_classifies_ram_mmio_reserved_and_length_faults(self) -> None:
        decode = fpga_soc_top_decoder.decode_soc_top_address

        ram = decode(0x00010004, len_cells=2)
        self.assertEqual(ram.target, "data_ram")
        self.assertEqual(ram.response, "data_response")
        self.assertTrue(ram.tag_sidecar)
        self.assertFalse(ram.fault_on_read)

        for address, target in (
            (0x00F00002, "uart"),
            (0x00F00101, "timer"),
            (0x00F00200, "gpio_status"),
            (0x00F00300, "interrupt_controller"),
            (0x00F00401, "system_identity"),
        ):
            with self.subTest(target=target):
                result = decode(address, len_cells=1)
                self.assertEqual(result.target, target)
                self.assertFalse(result.tag_sidecar)
                self.assertEqual(result.response, "mmio_response_or_register_fault")

        reserved = decode(0x00F00500, len_cells=1)
        self.assertEqual(reserved.target, "fault")
        self.assertTrue(reserved.fault_on_read)
        self.assertEqual(reserved.response, "EXC_ACCESS_FAULT")

        invalid_length = decode(0x00010000, len_cells=0)
        self.assertEqual(invalid_length.target, "fault")
        self.assertTrue(invalid_length.fault_on_read)

        reserved_write = decode(0x00F00500, len_cells=1, write=True)
        self.assertEqual(reserved_write.response, "no_response")
        self.assertFalse(reserved_write.fault_on_read)

    def test_rtl_top_instantiates_decoder_peripherals_and_tag_sidecar_gate(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_soc_dmem_decoder",
            "cpu_v01_fpga_soc_dmem_decoder #(",
            ".core_req_valid(dmem_req_valid)",
            ".ram_req_valid(ram_req_valid)",
            ".uart_req_valid(uart_req_valid)",
            ".timer_req_valid(timer_req_valid)",
            ".gpio_req_valid(gpio_req_valid)",
            ".irq_req_valid(irq_req_valid)",
            ".identity_req_valid(identity_req_valid)",
            "cpu_v01_fpga_uart_mmio #(",
            "cpu_v01_fpga_timer_mmio firmware_timer",
            "cpu_v01_fpga_gpio_status firmware_gpio_status",
            "module cpu_v01_fpga_irq_mmio",
            "module cpu_v01_fpga_system_identity_mmio",
            "fault_rsp_valid_q",
            "tagmem_req_in_data_ram",
            "tagmem_bypass_rsp_valid_q",
            "assign tagram_req_valid = tagmem_req_valid && tagmem_req_in_data_ram",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_decoder_testbench_covers_ram_mmio_reserved_and_invalid_length_cases(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_top_soc_decoder_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_top_soc_decoder_tb",
            "cpu_v01_fpga_soc_dmem_decoder #(",
            "FPGA SoC top decoder did not route RAM read/write traffic",
            "FPGA SoC top decoder did not select only the UART window",
            "FPGA SoC top decoder UART status read mismatch",
            "FPGA SoC top decoder timer compare readback mismatch",
            "FPGA SoC top decoder GPIO/status readback mismatch",
            "FPGA SoC top decoder interrupt-controller pending read mismatch",
            "FPGA SoC top decoder system identity reset-cause mismatch",
            "FPGA SoC top decoder system identity build-id mismatch",
            "FPGA SoC top decoder reserved window did not fault",
            "FPGA SoC top decoder invalid length did not fault",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_windows_plan_and_decode(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC top decoder issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S02")
        self.assertIn("windows", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--windows"])

        self.assertEqual(result, 0)
        self.assertIn("data_ram\t0x00010000\t0x00011000", stream.getvalue())
        self.assertIn("system_identity\t0x00F00400\t0x00F00500", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_decoder_tb.sv", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--decode", "0x00F00300"])

        self.assertEqual(result, 0)
        decoded = json.loads(stream.getvalue())
        self.assertEqual(decoded["target"], "interrupt_controller")

    def test_documentation_names_commands_policies_handoffs_and_acceptance(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-top-decoder.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I30-S02", text)
        self.assertIn("python tools\\fpga_soc_top_decoder.py --check", text)
        self.assertIn("python tools\\fpga_soc_platform.py --check", text)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_decoder_tb.sv", text)
        for token in (
            "cpu_v01_fpga_soc_dmem_decoder",
            "data_ram",
            "uart",
            "timer",
            "gpio_status",
            "interrupt_controller",
            "system_identity",
            "EXC_ACCESS_FAULT",
            "tag_ram",
            "tagmem_req_in_data_ram",
            "I30-S03",
            "I30-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

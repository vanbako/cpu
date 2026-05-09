"""I27-S02 conformance tests for the FPGA UART MMIO peripheral."""

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
TOOL = ROOT / "tools" / "fpga_uart_mmio.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_platform, fpga_uart_mmio


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_uart_mmio_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaUartMmioTests(unittest.TestCase):
    def test_uart_mmio_self_validation_passes(self) -> None:
        self.assertEqual(fpga_uart_mmio.validate_fpga_uart_mmio(ROOT), ())

    def test_profile_matches_soc_uart_window_and_gates(self) -> None:
        profile = fpga_uart_mmio.fpga_uart_mmio_profile()
        soc_uart = fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("uart")

        self.assertEqual(profile.story, "I27-S02")
        self.assertEqual(profile.soc_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(profile.packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(profile.status_stream_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.base_cell, soc_uart.base_cell)
        self.assertEqual(profile.size_cells, soc_uart.size_cells)
        self.assertEqual(profile.interrupt_lines, ("uart_rx_ready", "uart_tx_ready"))
        self.assertEqual(profile.baud, 115_200)
        self.assertEqual(profile.clock_hz, 25_000_000)
        self.assertEqual(profile.default_baud_div, 217)
        self.assertEqual(profile.fifo_depth, 4)

    def test_registers_and_status_control_bits_are_explicit(self) -> None:
        profile = fpga_uart_mmio.fpga_uart_mmio_profile()

        self.assertEqual(profile.register_by_name("UART_TXDATA").absolute_cell, 0x00F00000)
        self.assertEqual(profile.register_by_name("UART_TXDATA").access, "wo")
        self.assertEqual(profile.register_by_name("UART_RXDATA").access, "ro")
        self.assertEqual(profile.register_by_name("UART_STATUS").access, "ro")
        self.assertEqual(profile.register_by_name("UART_CONTROL").access, "rw")
        self.assertEqual(profile.register_by_name("UART_BAUD_DIV").width_bits, 24)
        self.assertEqual(profile.status_bits["TX_READY"], 0x01)
        self.assertEqual(profile.status_bits["RX_VALID"], 0x04)
        self.assertEqual(profile.status_bits["RX_OVERRUN"], 0x08)
        self.assertEqual(profile.status_bits["FRAME_ERROR"], 0x10)
        self.assertEqual(profile.control_bits["TX_IRQ_ENABLE"], 0x01)
        self.assertEqual(profile.control_bits["RX_IRQ_ENABLE"], 0x02)
        self.assertEqual(profile.control_bits["CLEAR_ERRORS"], 0x04)

    def test_executable_model_covers_tx_rx_irq_and_sticky_errors(self) -> None:
        state = fpga_uart_mmio.fpga_uart_mmio_state()

        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_TX_READY)
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_TX_EMPTY)

        state.write_register("UART_TXDATA", 0x1A5)
        self.assertFalse(state.status() & fpga_uart_mmio.STATUS_TX_EMPTY)
        self.assertEqual(state.host_transmit_byte(), 0xA5)

        state.write_register(
            "UART_CONTROL",
            fpga_uart_mmio.CONTROL_TX_IRQ_ENABLE | fpga_uart_mmio.CONTROL_RX_IRQ_ENABLE,
        )
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_TX_IRQ_PENDING)

        state.receive_byte(0x5A)
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_RX_VALID)
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_RX_IRQ_PENDING)
        self.assertEqual(state.read_register("UART_RXDATA"), 0x5A)
        self.assertFalse(state.status() & fpga_uart_mmio.STATUS_RX_VALID)

        for value in range(state.fifo_depth + 1):
            state.receive_byte(value)
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_RX_OVERRUN)

        state.receive_byte(0x00, frame_ok=False)
        self.assertTrue(state.status() & fpga_uart_mmio.STATUS_FRAME_ERROR)
        state.write_register("UART_CONTROL", fpga_uart_mmio.CONTROL_CLEAR_ERRORS)
        self.assertFalse(state.status() & fpga_uart_mmio.STATUS_RX_OVERRUN)
        self.assertFalse(state.status() & fpga_uart_mmio.STATUS_FRAME_ERROR)

    def test_rtl_sources_name_mmio_block_registers_fifo_and_testbench(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_uart_mmio.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_uart_mmio_tb.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_uart_mmio",
            "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0000",
            "parameter int TX_FIFO_DEPTH = 4",
            "parameter int RX_FIFO_DEPTH = 4",
            "UART_TXDATA_OFFSET",
            "UART_RXDATA_OFFSET",
            "UART_STATUS_OFFSET",
            "UART_CONTROL_OFFSET",
            "UART_BAUD_DIV_OFFSET",
            "STATUS_TX_READY = 8'h01",
            "STATUS_RX_OVERRUN = 8'h08",
            "CONTROL_CLEAR_ERRORS_BIT = 2",
            "assign req_ready = 1'b1",
            "irq_rx_ready_o",
            "irq_tx_ready_o",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_uart_mmio_tb",
            "cpu_v01_fpga_uart_mmio #(",
            "write_cell(UART_BASE + 48'd0, 24'h000055)",
            "drive_uart_byte(8'hA6)",
            "FPGA UART MMIO TX path did not pull uart_tx_o low",
            "FPGA UART MMIO RX path did not return injected byte",
            "FPGA UART MMIO RX overrun bit did not set",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_lists_plan_and_demo(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA UART MMIO issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I27-S02")
        self.assertEqual(parsed["base_cell"], 0x00F00000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers"])

        self.assertEqual(result, 0)
        self.assertIn("UART_TXDATA\t0x00F00000", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--top-module cpu_v01_fpga_uart_mmio_tb", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertEqual(demo["tx_fifo"], [0x41])
        self.assertEqual(demo["rx_fifo"], [0x52])

    def test_documentation_names_registers_commands_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-uart-mmio.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I27-S02", text)
        self.assertIn("python tools\\fpga_uart_mmio.py --check", text)
        self.assertIn("python tools\\fpga_soc_platform.py --check", text)
        self.assertIn("python tools\\fpga_debug_status_packet.py --check", text)
        self.assertIn("python tools\\fpga_uart_status_streamer.py --check", text)
        for token in (
            "rtl/cpu_v01_fpga_uart_mmio.sv",
            "rtl/cpu_v01_fpga_uart_mmio_tb.sv",
            "UART_TXDATA",
            "UART_RXDATA",
            "UART_STATUS",
            "UART_CONTROL",
            "UART_BAUD_DIV",
            "TX_READY",
            "RX_VALID",
            "RX_OVERRUN",
            "FRAME_ERROR",
            "uart_rx_ready",
            "uart_tx_ready",
            "bounded commands",
            "I26-S04",
            "I25-S02",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

"""I30-S03 conformance tests for FPGA SoC top peripheral handoffs."""

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
TOOL = ROOT / "tools" / "fpga_soc_top_peripherals.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_peripherals


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_top_peripherals_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocTopPeripheralsTests(unittest.TestCase):
    def test_soc_top_peripherals_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_top_peripherals.validate_fpga_soc_top_peripherals(ROOT), ())

    def test_profile_names_dependency_gates_handoffs_and_interrupt_order(self) -> None:
        profile = fpga_soc_top_peripherals.fpga_soc_top_peripherals_profile()
        handoffs = {handoff.name: handoff for handoff in profile.handoffs}

        self.assertEqual(profile.story, "I30-S03")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.decoder_gate, "python tools\\fpga_soc_top_decoder.py --check")
        self.assertEqual(profile.platform_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(profile.uart_gate, "python tools\\fpga_uart_mmio.py --check")
        self.assertEqual(profile.timer_gate, "python tools\\fpga_timer_mmio.py --check")
        self.assertEqual(profile.gpio_gate, "python tools\\fpga_gpio_status.py --check")
        self.assertEqual(profile.reset_cdc_gate, "python tools\\fpga_reset_cdc.py --check")
        self.assertEqual(profile.interrupt_lines, ("uart_rx_ready", "uart_tx_ready", "timer_compare", "gpio_status"))
        self.assertIn("--top-module cpu_v01_fpga_top_soc_peripherals_tb", profile.verilator_command)

        for name in (
            "firmware_uart_rx",
            "uart_tx_mux",
            "timer_interrupt",
            "external_interrupts",
            "gpio_status_leds",
            "system_identity",
        ):
            self.assertIn(name, handoffs)
        self.assertIn("I30-S04", profile.remaining_handoffs[0])

    def test_executable_handoff_model_covers_uart_interrupts_and_leds(self) -> None:
        result = fpga_soc_top_peripherals.evaluate_soc_top_peripherals(
            uart_mmio_tx=False,
            status_uart_tx=True,
            timer_compare_irq=True,
            irq_pending_enabled=0x000B,
            pass_sticky=True,
            fault_sticky=False,
            gpio_fail_led=True,
            gpio_heartbeat_led=True,
        )

        self.assertFalse(result.uart_tx_o)
        self.assertTrue(result.timer_interrupt_pending)
        self.assertTrue(result.external_interrupt_pending)
        self.assertTrue(result.pass_led_o)
        self.assertTrue(result.fail_led_o)
        self.assertTrue(result.heartbeat_led_o)

        faulted = fpga_soc_top_peripherals.evaluate_soc_top_peripherals(
            pass_sticky=True,
            fault_sticky=True,
        )
        self.assertFalse(faulted.pass_led_o)
        self.assertTrue(faulted.fail_led_o)

    def test_rtl_top_wires_uart_timer_interrupts_gpio_leds_and_identity(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "input  logic uart_rx_i",
            "logic status_uart_tx",
            "assign uart_tx_o = uart_mmio_tx & status_uart_tx;",
            ".uart_rx_i(uart_rx_i)",
            ".uart_tx_o(status_uart_tx)",
            "assign timer_interrupt_pending = timer_compare_irq;",
            ".timer_interrupt_pending(timer_interrupt_pending)",
            "assign external_interrupt_pending = |(irq_pending_enabled & 16'h000B);",
            ".external_interrupt_pending(external_interrupt_pending)",
            "assign pass_led_o = pass_sticky_q && !fault_sticky_q || gpio_pass_led;",
            "assign fail_led_o = fault_sticky_q || gpio_fail_led;",
            "assign heartbeat_led_o = debug_retire_sequence[0] || gpio_heartbeat_led;",
            "cpu_v01_fpga_system_identity_mmio #(",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_peripherals_testbench_covers_story_owned_handoffs(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_top_soc_peripherals_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_top_soc_peripherals_tb",
            ".uart_rx_i(uart_rx_i)",
            "FPGA SoC top peripherals did not wire firmware UART RX",
            "FPGA SoC top peripherals UART TX mux policy mismatch",
            "FPGA SoC top peripherals did not route timer interrupt pending",
            "FPGA SoC top peripherals external interrupt aggregate mismatch",
            "FPGA SoC top peripherals GPIO pass LED mux mismatch",
            "FPGA SoC top peripherals GPIO fail LED mux mismatch",
            "FPGA SoC top peripherals GPIO heartbeat LED mux mismatch",
            "FPGA SoC top peripherals reset-idle status projection changed",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_handoffs_plan_and_demo(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC top peripheral handoff issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S03")
        self.assertIn("handoffs", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--handoffs"])

        self.assertEqual(result, 0)
        self.assertIn("firmware_uart_rx\tuart_rx_i", stream.getvalue())
        self.assertIn("timer_interrupt\tcpu_v01_fpga_timer_mmio", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertFalse(demo["uart_tx_o"])
        self.assertTrue(demo["timer_interrupt_pending"])

    def test_documentation_names_commands_policies_handoffs_and_acceptance(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-soc-top-peripherals.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I30-S03", text)
        self.assertIn("python tools\\fpga_soc_top_peripherals.py --check", text)
        self.assertIn("python tools\\fpga_soc_top_decoder.py --check", text)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv", text)
        for token in (
            "uart_rx_i",
            "assign uart_tx_o = uart_mmio_tx & status_uart_tx;",
            "timer_interrupt_pending",
            "external_interrupt_pending",
            "GPIO/status LEDs",
            "system_identity",
            "I30-S04",
            "I30-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

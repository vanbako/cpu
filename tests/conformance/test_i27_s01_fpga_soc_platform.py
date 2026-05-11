"""I27-S01 conformance tests for the FPGA SoC platform profile."""

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
TOOL = ROOT / "tools" / "fpga_soc_platform.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_platform, platform


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_platform_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocPlatformTests(unittest.TestCase):
    def test_soc_platform_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_platform.validate_fpga_soc_platform(ROOT), ())

    def test_profile_names_board_top_and_platform_device_window(self) -> None:
        profile = fpga_soc_platform.fpga_soc_platform_profile()
        device = platform.TEST_PLATFORM_PROFILE.region_by_name("platform_devices")

        self.assertEqual(profile.story, "I27-S01")
        self.assertEqual(profile.name, "cpu_v01_fpga_minimal_soc")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.fpga_top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.reset_vector, platform.RESET_VECTOR)
        self.assertEqual(profile.mmio_base_cell, platform.DEVICE_BASE)
        self.assertEqual(profile.mmio_size_cells, platform.DEVICE_CELLS)
        self.assertEqual(profile.mmio_base_cell, device.base)
        self.assertEqual(profile.mmio_base_cell + profile.mmio_size_cells, platform.MAILBOX_BASE)
        self.assertEqual(profile.upstream_board_gate, "python tools\\fpga_first_board_archive.py --check")

    def test_peripherals_are_non_overlapping_and_cover_required_roles(self) -> None:
        profile = fpga_soc_platform.fpga_soc_platform_profile()
        peripherals = {peripheral.name: peripheral for peripheral in profile.peripherals}

        self.assertEqual(
            set(peripherals),
            {"uart", "timer", "gpio_status", "interrupt_controller", "system_identity"},
        )
        self.assertEqual(peripherals["uart"].base_cell, 0x00F00000)
        self.assertEqual(peripherals["timer"].base_cell, 0x00F00100)
        self.assertEqual(peripherals["gpio_status"].base_cell, 0x00F00200)
        self.assertEqual(peripherals["interrupt_controller"].base_cell, 0x00F00300)
        self.assertEqual(peripherals["system_identity"].base_cell, 0x00F00400)

        sorted_peripherals = sorted(profile.peripherals, key=lambda peripheral: peripheral.base_cell)
        for left, right in zip(sorted_peripherals, sorted_peripherals[1:]):
            self.assertLessEqual(left.end_cell, right.base_cell)
        self.assertLessEqual(sorted_peripherals[-1].end_cell, platform.DEVICE_BASE + platform.DEVICE_CELLS)

    def test_register_map_assigns_uart_timer_gpio_irq_and_identity_registers(self) -> None:
        profile = fpga_soc_platform.fpga_soc_platform_profile()

        uart = profile.peripheral_by_name("uart")
        self.assertEqual(uart.register_by_name("UART_TXDATA").access, "wo")
        self.assertEqual(uart.register_by_name("UART_RXDATA").access, "ro")
        self.assertEqual(uart.register_by_name("UART_BAUD_DIV").width_bits, 24)
        self.assertIn("uart_rx_ready", uart.interrupt_lines)

        timer = profile.peripheral_by_name("timer")
        self.assertEqual(timer.register_by_name("TIMER_VALUE").width_bits, 48)
        self.assertEqual(timer.register_by_name("TIMER_COMPARE").access, "rw")
        self.assertIn("timer_compare", timer.interrupt_lines)

        gpio = profile.peripheral_by_name("gpio_status")
        self.assertEqual(gpio.register_by_name("GPIO_OUT").access, "rw")
        self.assertEqual(gpio.register_by_name("STATUS_LEDS").width_bits, 8)

        irq = profile.peripheral_by_name("interrupt_controller")
        self.assertEqual(irq.register_by_name("IRQ_PENDING").access, "ro")
        self.assertEqual(irq.register_by_name("IRQ_ACK").access, "w1c")

        identity = profile.peripheral_by_name("system_identity")
        self.assertEqual(identity.register_by_name("RESET_CAUSE").access, "w1c")
        for index in range(6):
            self.assertEqual(identity.register_by_name(f"IMAGE_SHA256_{index}").access, "ro")

    def test_interrupt_lines_and_non_goals_are_explicit(self) -> None:
        profile = fpga_soc_platform.fpga_soc_platform_profile()

        self.assertEqual(
            set(profile.interrupt_lines),
            {"uart_rx_ready", "uart_tx_ready", "timer_compare", "gpio_status"},
        )
        self.assertIn("external_ddr_controller", profile.non_goals)
        self.assertIn("program_loader_protocol", profile.non_goals)

    def test_cli_validates_renders_json_lists_and_registers(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC platform issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I27-S01")
        self.assertEqual(parsed["mmio_base_cell"], platform.DEVICE_BASE)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("uart\t0x00F00000", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers", "system_identity"])

        self.assertEqual(result, 0)
        self.assertIn("IMAGE_SHA256_5", stream.getvalue())

    def test_documentation_names_commands_map_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-platform.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I27-S01", text)
        self.assertIn("python tools\\fpga_soc_platform.py --check", text)
        self.assertIn("python tools\\fpga_first_test_profile.py --check", text)
        self.assertIn("python tools\\fpga_first_board_archive.py --check", text)
        self.assertIn("platform_devices", text)
        self.assertIn("0x00F00000", text)
        self.assertIn("0x00F01000", text)
        for token in (
            "uart",
            "timer",
            "gpio_status",
            "interrupt_controller",
            "system_identity",
            "UART_TXDATA",
            "TIMER_COMPARE",
            "GPIO_OUT",
            "IRQ_PENDING",
            "RESET_CAUSE",
            "IMAGE_SHA256_0",
            "I27-S02",
            "I27-S03",
            "I27-S04",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

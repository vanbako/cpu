"""I27-S04 conformance tests for the FPGA GPIO/status MMIO peripheral."""

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
TOOL = ROOT / "tools" / "fpga_gpio_status.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gpio_status, fpga_soc_platform


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_gpio_status_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaGpioStatusTests(unittest.TestCase):
    def test_gpio_status_self_validation_passes(self) -> None:
        self.assertEqual(fpga_gpio_status.validate_fpga_gpio_status(ROOT), ())

    def test_profile_matches_soc_gpio_window_and_handoffs(self) -> None:
        profile = fpga_gpio_status.fpga_gpio_status_profile()
        soc_gpio = fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("gpio_status")

        self.assertEqual(profile.story, "I27-S04")
        self.assertEqual(profile.soc_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(profile.smoke_firmware_gate, "python tools\\fpga_smoke_firmware.py --check")
        self.assertEqual(profile.base_cell, soc_gpio.base_cell)
        self.assertEqual(profile.size_cells, soc_gpio.size_cells)
        self.assertEqual(profile.gpio_width, 16)
        self.assertEqual(profile.interrupt_line, "gpio_status")
        self.assertIn("RESET_CAUSE", profile.diagnostic_handoff_registers)
        self.assertIn("BUILD_ID_LO", profile.diagnostic_handoff_registers)

    def test_registers_led_bits_and_debug_force_are_explicit(self) -> None:
        profile = fpga_gpio_status.fpga_gpio_status_profile()

        self.assertEqual(profile.register_by_name("GPIO_OUT").absolute_cell, 0x00F00200)
        self.assertEqual(profile.register_by_name("GPIO_OUT").access, "rw")
        self.assertEqual(profile.register_by_name("GPIO_IN").access, "ro")
        self.assertEqual(profile.register_by_name("GPIO_DIR").width_bits, 16)
        self.assertEqual(profile.register_by_name("STATUS_LEDS").width_bits, 8)
        self.assertEqual(profile.register_by_name("DEBUG_STATUS_SELECT").access, "rw")
        self.assertEqual(profile.status_led_bits["PASS"], 0x01)
        self.assertEqual(profile.status_led_bits["FAIL"], 0x02)
        self.assertEqual(profile.status_led_bits["HEARTBEAT"], 0x04)
        self.assertEqual(profile.status_led_bits["SOFTWARE3"], 0x40)
        self.assertEqual(profile.debug_select_bits["SOFTWARE_FORCE_IRQ"], 0x80)

    def test_executable_model_covers_gpio_leds_inputs_and_force_irq(self) -> None:
        state = fpga_gpio_status.fpga_gpio_status_state()

        state.write_register("GPIO_DIR", 0x00FF)
        state.write_register("GPIO_OUT", 0xA5A5)
        self.assertEqual(state.gpio_outputs, 0x00A5)

        state.write_register(
            "STATUS_LEDS",
            fpga_gpio_status.STATUS_LED_PASS
            | fpga_gpio_status.STATUS_LED_HEARTBEAT
            | fpga_gpio_status.STATUS_LED_SOFTWARE1,
        )
        self.assertTrue(state.pass_led)
        self.assertFalse(state.fail_led)
        self.assertTrue(state.heartbeat_led)
        self.assertEqual(state.status_led_vector, 0x2)

        state.set_gpio_inputs(0x1234)
        self.assertTrue(state.interrupt_pending)
        self.assertEqual(state.read_register("GPIO_IN"), 0x1234)
        self.assertFalse(state.interrupt_pending)

        state.write_register("DEBUG_STATUS_SELECT", fpga_gpio_status.DEBUG_SELECT_SOFTWARE_FORCE_IRQ)
        self.assertTrue(state.interrupt_pending)
        state.write_register("DEBUG_STATUS_SELECT", 0)
        self.assertFalse(state.interrupt_pending)

    def test_rtl_sources_name_gpio_status_block_registers_and_testbench(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_gpio_status.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_gpio_status_tb.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_gpio_status",
            "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0200",
            "GPIO_OUT_OFFSET",
            "GPIO_IN_OFFSET",
            "GPIO_DIR_OFFSET",
            "STATUS_LEDS_OFFSET",
            "DEBUG_STATUS_SELECT_OFFSET",
            "STATUS_LED_PASS = 8'h01",
            "DEBUG_SELECT_FORCE_IRQ_BIT = 7",
            "assign gpio_out_o = gpio_out_q & gpio_dir_q",
            "gpio_status_irq_o",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_gpio_status_tb",
            "cpu_v01_fpga_gpio_status #(",
            "write_cell(GPIO_BASE + 48'd0, 24'h00A5A5)",
            "FPGA GPIO/status output mask mismatch",
            "FPGA GPIO/status LEDs did not follow STATUS_LEDS",
            "FPGA GPIO/status input change did not assert interrupt",
            "FPGA GPIO/status DEBUG_STATUS_SELECT force did not assert interrupt",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_lists_plan_and_demo(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA GPIO/status issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I27-S04")
        self.assertEqual(parsed["base_cell"], 0x00F00200)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers"])

        self.assertEqual(result, 0)
        self.assertIn("GPIO_OUT\t0x00F00200", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--top-module cpu_v01_fpga_gpio_status_tb", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertEqual(demo["gpio_outputs"], 0x00A5)
        self.assertTrue(demo["pass_led"])
        self.assertTrue(demo["interrupt_pending"])

    def test_documentation_names_registers_commands_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-gpio-status.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I27-S04", text)
        self.assertIn("python tools\\fpga_gpio_status.py --check", text)
        self.assertIn("python tools\\fpga_soc_platform.py --check", text)
        self.assertIn("python tools\\fpga_smoke_firmware.py --check", text)
        for token in (
            "rtl/cpu_v01_fpga_gpio_status.sv",
            "rtl/cpu_v01_fpga_gpio_status_tb.sv",
            "GPIO_OUT",
            "GPIO_IN",
            "GPIO_DIR",
            "STATUS_LEDS",
            "DEBUG_STATUS_SELECT",
            "PASS",
            "FAIL",
            "HEARTBEAT",
            "gpio_status",
            "RESET_CAUSE",
            "BUILD_ID_LO",
            "I27-S05",
            "first-test pass/fail",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

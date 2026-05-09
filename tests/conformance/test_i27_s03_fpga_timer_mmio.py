"""I27-S03 conformance tests for the FPGA timer MMIO peripheral."""

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
TOOL = ROOT / "tools" / "fpga_timer_mmio.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_platform, fpga_timer_mmio, kernel


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_timer_mmio_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaTimerMmioTests(unittest.TestCase):
    def test_timer_mmio_self_validation_passes(self) -> None:
        self.assertEqual(fpga_timer_mmio.validate_fpga_timer_mmio(ROOT), ())

    def test_profile_matches_soc_timer_window_and_interrupt_contract(self) -> None:
        profile = fpga_timer_mmio.fpga_timer_mmio_profile()
        soc_timer = fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("timer")

        self.assertEqual(profile.story, "I27-S03")
        self.assertEqual(profile.soc_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(
            profile.kernel_timer_gate,
            "python -m unittest tests.conformance.test_i14_s02_kernel_handlers",
        )
        self.assertEqual(profile.core_control_trap_gate, "python tools\\rtl_core_control_trap.py --check")
        self.assertEqual(profile.base_cell, soc_timer.base_cell)
        self.assertEqual(profile.size_cells, soc_timer.size_cells)
        self.assertEqual(profile.interrupt_line, "timer_compare")
        self.assertEqual(profile.interrupt_bit, kernel.InterruptSource.TIMER.bit)
        self.assertEqual(profile.interrupt_cause_value, kernel.InterruptSource.TIMER.cause_value)
        self.assertEqual(profile.counter_bits, 48)

    def test_registers_control_status_and_firmware_rules_are_explicit(self) -> None:
        profile = fpga_timer_mmio.fpga_timer_mmio_profile()

        self.assertEqual(profile.register_by_name("TIMER_VALUE").absolute_cell, 0x00F00100)
        self.assertEqual(profile.register_by_name("TIMER_VALUE").access, "ro")
        self.assertEqual(profile.register_by_name("TIMER_VALUE").cells, 2)
        self.assertEqual(profile.register_by_name("TIMER_COMPARE").access, "rw")
        self.assertEqual(profile.register_by_name("TIMER_COMPARE").cells, 2)
        self.assertEqual(profile.register_by_name("TIMER_CONTROL").width_bits, 4)
        self.assertEqual(profile.register_by_name("TIMER_STATUS").access, "w1c")
        self.assertEqual(profile.control_bits["ENABLE"], 0x1)
        self.assertEqual(profile.control_bits["IRQ_ENABLE"], 0x2)
        self.assertEqual(profile.control_bits["ONESHOT"], 0x4)
        self.assertEqual(profile.control_bits["CLEAR_VALUE"], 0x8)
        self.assertEqual(profile.status_bits["PENDING"], 0x1)
        self.assertEqual(profile.status_bits["OVERFLOW"], 0x2)
        self.assertTrue(any("STATUS_PENDING" in rule for rule in profile.firmware_rules))

    def test_executable_model_covers_compare_ack_oneshot_and_overflow(self) -> None:
        state = fpga_timer_mmio.fpga_timer_mmio_state()

        state.write_register("TIMER_COMPARE", 3)
        state.write_register(
            "TIMER_CONTROL",
            fpga_timer_mmio.CONTROL_ENABLE | fpga_timer_mmio.CONTROL_IRQ_ENABLE,
        )
        state.tick(2)
        self.assertFalse(state.interrupt_pending)
        state.tick(1)
        self.assertTrue(state.interrupt_pending)
        self.assertEqual(state.read_register("TIMER_VALUE"), 3)
        state.write_register("TIMER_STATUS", fpga_timer_mmio.STATUS_PENDING)
        self.assertFalse(state.interrupt_pending)

        state.write_register("TIMER_COMPARE", state.value + 2)
        state.write_register(
            "TIMER_CONTROL",
            fpga_timer_mmio.CONTROL_ENABLE
            | fpga_timer_mmio.CONTROL_IRQ_ENABLE
            | fpga_timer_mmio.CONTROL_ONESHOT,
        )
        state.tick(2)
        self.assertTrue(state.status & fpga_timer_mmio.STATUS_PENDING)
        self.assertFalse(state.control & fpga_timer_mmio.CONTROL_ENABLE)

        state.value = fpga_timer_mmio.TIMER_MASK
        state.write_register("TIMER_CONTROL", fpga_timer_mmio.CONTROL_ENABLE)
        state.tick(1)
        self.assertTrue(state.status & fpga_timer_mmio.STATUS_OVERFLOW)
        state.write_register("TIMER_CONTROL", fpga_timer_mmio.CONTROL_CLEAR_VALUE)
        self.assertEqual(state.value, 0)
        self.assertEqual(state.status, 0)

    def test_rtl_sources_name_timer_block_registers_and_testbench(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_timer_mmio.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_timer_mmio_tb.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_timer_mmio",
            "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0100",
            "TIMER_VALUE_OFFSET",
            "TIMER_COMPARE_OFFSET",
            "TIMER_CONTROL_OFFSET",
            "TIMER_STATUS_OFFSET",
            "CONTROL_ENABLE = 4'h1",
            "STATUS_PENDING = 4'h1",
            "assign req_ready = 1'b1",
            "timer_interrupt_o",
            "pack_timer_value",
            "unpack_timer_value",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_timer_mmio_tb",
            "cpu_v01_fpga_timer_mmio #(",
            "write_48(TIMER_BASE + 48'd1, 48'd3)",
            "FPGA timer MMIO did not raise timer_interrupt_o",
            "FPGA timer MMIO acknowledgement did not clear interrupt",
            "FPGA timer MMIO clear-value control did not reset value",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_lists_plan_and_demo(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA timer MMIO issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I27-S03")
        self.assertEqual(parsed["base_cell"], 0x00F00100)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers"])

        self.assertEqual(result, 0)
        self.assertIn("TIMER_VALUE\t0x00F00100", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--top-module cpu_v01_fpga_timer_mmio_tb", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertEqual(demo["value"], 3)
        self.assertTrue(demo["interrupt_pending"])

    def test_documentation_names_registers_commands_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-timer-mmio.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I27-S03", text)
        self.assertIn("python tools\\fpga_timer_mmio.py --check", text)
        self.assertIn("python tools\\fpga_soc_platform.py --check", text)
        self.assertIn("python -m unittest tests.conformance.test_i14_s02_kernel_handlers", text)
        self.assertIn("python tools\\rtl_core_control_trap.py --check", text)
        for token in (
            "rtl/cpu_v01_fpga_timer_mmio.sv",
            "rtl/cpu_v01_fpga_timer_mmio_tb.sv",
            "TIMER_VALUE",
            "TIMER_COMPARE",
            "TIMER_CONTROL",
            "TIMER_STATUS",
            "ENABLE",
            "IRQ_ENABLE",
            "ONESHOT",
            "PENDING",
            "OVERFLOW",
            "timer_compare",
            "STATUS_PENDING",
            "I27-S05",
            "first-test pass/fail",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

"""I30-S05 conformance tests for the FPGA SoC top-level smoke."""

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
TOOL = ROOT / "tools" / "fpga_soc_top_smoke.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_smoke


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_top_smoke_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocTopSmokeTests(unittest.TestCase):
    def test_soc_top_smoke_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_top_smoke.validate_fpga_soc_top_smoke(ROOT), ())

    def test_profile_names_dependency_gates_fixture_and_handoffs(self) -> None:
        profile = fpga_soc_top_smoke.fpga_soc_top_smoke_profile()
        steps = {step.name: step for step in profile.steps}

        self.assertEqual(profile.story, "I30-S05")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.modeled_smoke_gate, "python tools\\fpga_soc_smoke.py --check")
        self.assertEqual(
            profile.peripheral_gate,
            "python tools\\fpga_soc_top_peripherals.py --check",
        )
        self.assertEqual(profile.loader_gate, "python tools\\fpga_soc_loader_handoff.py --check")
        self.assertEqual(profile.reset_vector, 0x00001000)
        self.assertEqual(profile.uart_text, "I30S")
        self.assertEqual(profile.timer_compare_value, 3)
        self.assertEqual(profile.timer_control_value, 7)
        self.assertEqual(profile.gpio_status_led_value, 5)
        self.assertEqual(profile.first_failure_status, "EXC_SYSCALL_TRAP")
        self.assertEqual(profile.first_failure_code, 0x0008)
        self.assertIn("--binary --timing", profile.verilator_command)
        self.assertIn("--Mdir obj_dir\\soc_top_smoke", profile.verilator_command)
        self.assertIn("--top-module cpu_v01_fpga_top_soc_smoke_tb", profile.verilator_command)
        self.assertIn("Vcpu_v01_fpga_top_soc_smoke_tb.exe", profile.run_command)

        for name in (
            "uart_output",
            "timer_service",
            "syscall_trap_return",
            "gpio_pass_fail",
            "first_failure_status",
        ):
            self.assertIn(name, steps)
        self.assertIn("I30-S06", profile.closure_handoffs[0])
        self.assertIn("I31-S01", profile.closure_handoffs[1])

    def test_executable_model_covers_uart_timer_syscall_gpio_and_status(self) -> None:
        run = fpga_soc_top_smoke.run_fpga_soc_top_smoke_model()

        self.assertEqual(run.story, "I30-S05")
        self.assertEqual(run.uart_text, "I30S")
        self.assertTrue(run.timer_interrupt_seen)
        self.assertTrue(run.timer_ack_seen)
        self.assertTrue(run.timer_cleared_after_ack)
        self.assertTrue(run.syscall_trap_seen)
        self.assertTrue(run.iret_seen)
        self.assertTrue(run.gpio_pass_led)
        self.assertTrue(run.gpio_fail_led)
        self.assertTrue(run.gpio_heartbeat_led)
        self.assertEqual(run.first_failure_status, "EXC_SYSCALL_TRAP")
        self.assertEqual(run.first_failure_code, 0x0008)
        self.assertTrue(run.loader_idle)
        self.assertTrue(run.passed)

    def test_rtl_testbench_contains_integrated_firmware_smoke_evidence(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_top_soc_smoke_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "SOC_MMIO_BASE = 48'h0000_00F0_0000",
            "SOC_MMIO_LIMIT = 48'h0000_00F0_1000",
            "address_allows_unaligned_integer_mmio",
            "MEMORY_TYPE_DEVICE_ORDERED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

        for token in (
            "module cpu_v01_fpga_top_soc_smoke_tb",
            ".ENABLE_FETCH(1'b1)",
            ".UART_STATUS_ENABLE(1'b0)",
            "ST48 C1, D0, D1",
            "ST48 C2, D7, D10",
            "ST48 C2, D9, D12",
            "ST48 C3, D9, D13",
            "SYS; PAUSE",
            "IRET",
            "timer_interrupt_pending",
            "status_fault_code_o == EXC_SYSCALL_TRAP",
            "FPGA SoC top smoke UART firmware output mismatch",
            "FPGA SoC top smoke acknowledged timer before pending asserted",
            "FPGA SoC top smoke did not complete UART timer syscall GPIO checks",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_run_steps_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC top smoke issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S05")
        self.assertEqual(parsed["uart_text"], "I30S")
        self.assertIn("run_command", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["passed"])
        self.assertEqual(run["first_failure_code"], 0x0008)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--steps"])

        self.assertEqual(result, 0)
        self.assertIn("uart_output", stream.getvalue())
        self.assertIn("syscall_trap_return", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--binary --timing", stream.getvalue())
        self.assertIn("rtl/cpu_v01_fpga_top_soc_smoke_tb.sv", stream.getvalue())

    def test_documentation_names_commands_scope_and_acceptance(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-top-smoke.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I30-S05", text)
        self.assertIn("python tools\\fpga_soc_top_smoke.py --check", text)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_smoke_tb.sv", text)
        self.assertIn("verilator --binary --timing", text)
        self.assertIn("obj_dir\\soc_top_smoke\\Vcpu_v01_fpga_top_soc_smoke_tb.exe", text)
        for token in (
            "cpu_v01_fpga_top",
            "I27-S05",
            "I30-S03",
            "I30-S04",
            "UART output",
            "timer interrupt",
            "syscall/trap",
            "GPIO pass/fail",
            "first-failure status",
            "unaligned integer MMIO",
            "EXC_SYSCALL_TRAP",
            "I30-S06",
            "I31-S01",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

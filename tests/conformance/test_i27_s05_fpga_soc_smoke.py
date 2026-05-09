"""I27-S05 conformance tests for the FPGA SoC smoke evidence profile."""

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
TOOL = ROOT / "tools" / "fpga_soc_smoke.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_smoke, syscall_demo


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_smoke_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSocSmokeTests(unittest.TestCase):
    def test_soc_smoke_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_smoke.validate_fpga_soc_smoke(ROOT), ())

    def test_profile_names_dependency_gates_program_and_blockers(self) -> None:
        profile = fpga_soc_smoke.fpga_soc_smoke_profile()

        self.assertEqual(profile.story, "I27-S05")
        self.assertEqual(profile.platform_gate, "python tools\\fpga_soc_platform.py --check")
        self.assertEqual(profile.uart_gate, "python tools\\fpga_uart_mmio.py --check")
        self.assertEqual(profile.timer_gate, "python tools\\fpga_timer_mmio.py --check")
        self.assertEqual(profile.gpio_gate, "python tools\\fpga_gpio_status.py --check")
        self.assertEqual(
            profile.syscall_gate,
            "python -m unittest tests.conformance.test_i18_s03_syscall_demo",
        )
        self.assertEqual(profile.smoke_corpus_gate, "python tools\\fpga_smoke_corpus.py --check")
        self.assertEqual(profile.program_id, "syscall_trap.sys_pause_iret_fpga")
        self.assertEqual(profile.smoke_case_id, "trap_syscall.sys_pause_iret")
        self.assertEqual(profile.board_status, "documented_blocker_run")
        self.assertEqual(len(profile.steps), 4)
        self.assertTrue(any("MMIO decoder" in blocker for blocker in profile.documented_blockers))
        self.assertTrue(any("timer_interrupt_pending" in blocker for blocker in profile.documented_blockers))

    def test_run_evidence_covers_uart_timer_syscall_and_gpio(self) -> None:
        run = fpga_soc_smoke.run_fpga_soc_smoke()

        self.assertEqual(run.story, "I27-S05")
        self.assertEqual(run.board_status, "documented_blocker_run")
        for token in ("I27-S05", "timer", "syscall", "GPIO", "pass"):
            self.assertIn(token, run.uart_text)
        self.assertEqual(tuple(ord(ch) for ch in run.uart_text), run.uart_bytes)
        self.assertTrue(run.timer_mmio_pending_before_ack)
        self.assertFalse(run.timer_mmio_pending_after_ack)
        self.assertTrue(run.timer_handler_entered)
        self.assertEqual(run.timer_handler_source, "timer")
        self.assertEqual(run.timer_handler_new_timecmp, 100)
        self.assertEqual(run.syscall_status, syscall_demo.SyscallDemoStatus.OK.name)
        self.assertTrue(run.syscall_trap_entered)
        self.assertTrue(run.syscall_final_user_mode)
        self.assertTrue(run.gpio_pass_led)
        self.assertFalse(run.gpio_fail_led)
        self.assertTrue(run.gpio_heartbeat_led)
        self.assertTrue(run.gpio_interrupt_seen)

    def test_top_level_blocker_tokens_are_still_visible(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        self.assertIn("cpu_v01_fpga_data_ram #(", top)
        self.assertIn(".timer_interrupt_pending(1'b0)", top)
        self.assertIn(".uart_tx_o(uart_tx_o)", top)
        self.assertIn("status_core_port_activity_o", top)

    def test_cli_validates_json_run_steps_and_blockers(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC smoke issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I27-S05")
        self.assertEqual(parsed["program_id"], "syscall_trap.sys_pause_iret_fpga")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["timer_mmio_pending_before_ack"])
        self.assertEqual(run["syscall_status"], "OK")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--steps"])

        self.assertEqual(result, 0)
        self.assertIn("uart_output", stream.getvalue())
        self.assertIn("syscall_trap_progress", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--blockers"])

        self.assertEqual(result, 0)
        self.assertIn("MMIO decoder", stream.getvalue())

    def test_documentation_names_commands_observations_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-smoke.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I27-S05", text)
        self.assertIn("python tools\\fpga_soc_smoke.py --check", text)
        self.assertIn("python tools\\fpga_uart_mmio.py --check", text)
        self.assertIn("python tools\\fpga_timer_mmio.py --check", text)
        self.assertIn("python tools\\fpga_gpio_status.py --check", text)
        self.assertIn("python -m unittest tests.conformance.test_i18_s03_syscall_demo", text)
        self.assertIn("python tools\\fpga_smoke_corpus.py --check", text)
        for token in (
            "syscall_trap.sys_pause_iret_fpga",
            "UART output",
            "timer interrupt",
            "syscall/trap",
            "GPIO pass/fail",
            "documented_blocker_run",
            "cpu_v01_fpga_top",
            "dmem directly",
            "timer_interrupt_pending",
            "UART firmware/status TX mux",
            "I26-S04",
            "I28-S01",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

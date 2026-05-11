"""I32-S03 conformance tests for FPGA monitor multi-program sessions."""

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
TOOL = ROOT / "tools" / "fpga_monitor_session.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_firmware, fpga_monitor_session


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_monitor_session_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMonitorSessionTests(unittest.TestCase):
    def test_monitor_session_self_validation_passes(self) -> None:
        self.assertEqual(fpga_monitor_session.validate_fpga_monitor_session(ROOT), ())

    def test_profile_names_dependencies_and_selected_programs(self) -> None:
        profile = fpga_monitor_session.fpga_monitor_session_profile()

        self.assertEqual(profile.story, "I32-S03")
        self.assertEqual(profile.status, "multi_program_session_fixture")
        self.assertEqual(profile.monitor_firmware_gate, "python tools\\fpga_monitor_firmware.py --check")
        self.assertEqual(profile.bram_image_gate, "python tools\\fpga_bram_images.py --check")
        self.assertEqual(profile.smoke_corpus_gate, "python tools\\fpga_smoke_corpus.py --check")
        self.assertGreaterEqual(len(profile.selected_cases), 2)

        scalar = profile.selection_by_case_id("scalar_control.call_return")
        trap = profile.selection_by_case_id("trap_syscall.sys_pause_iret")
        self.assertEqual(scalar.program_id, "call_return.direct_call_ret_fpga")
        self.assertEqual(trap.program_id, "syscall_trap.sys_pause_iret_fpga")
        self.assertEqual(len(scalar.manifest_image_sha256), 64)
        self.assertEqual(len(trap.ram_image_sha256), 64)
        self.assertNotEqual(scalar.expected_uart_signature, trap.expected_uart_signature)

    def test_session_loads_starts_two_programs_and_preserves_distinct_signatures(self) -> None:
        run = fpga_monitor_session.run_monitor_session()

        self.assertTrue(run.passed)
        self.assertTrue(run.initial_hello.passed)
        self.assertEqual(
            run.loaded_program_ids,
            ("call_return.direct_call_ret_fpga", "syscall_trap.sys_pause_iret_fpga"),
        )
        self.assertEqual(run.final_snapshot.monitor_state, fpga_monitor_firmware.STATE_PROGRAM_RUNNING)
        self.assertEqual(run.final_snapshot.loaded_program_id, "syscall_trap.sys_pause_iret_fpga")
        self.assertEqual(run.final_snapshot.tag_bits_set, 0)

        signatures = {program.observation.signature_digest for program in run.program_runs}
        self.assertEqual(len(signatures), len(run.program_runs))

        for program in run.program_runs:
            with self.subTest(case_id=program.case_id):
                self.assertTrue(program.passed)
                self.assertLessEqual(
                    len(program.command_results),
                    fpga_monitor_firmware.MAX_MONITOR_COMMANDS,
                )
                self.assertEqual(
                    program.observation.monitor_status_sequence,
                    ("OK", "OK", "OK", "OK"),
                )
                self.assertEqual(program.observation.loader_status_name, "OK")
                self.assertEqual(program.observation.loaded_cells, 0x1000)
                self.assertTrue(program.observation.started)
                self.assertEqual(program.observation.start_pc_cell, 0x1000)
                self.assertEqual(program.observation.status_packet_fault_code, 0)
                self.assertTrue(program.observation.expected_led_signature)
                self.assertTrue(program.observation.expected_uart_signature)
                self.assertTrue(program.observation.expected_probe_signature)
                self.assertTrue(program.observation.replay_case_id)

        self.assertEqual(run.program_runs[0].observation.debug_signature_kind, "pass_progress")
        self.assertEqual(run.program_runs[1].observation.debug_signature_kind, "trap_debug")

    def test_session_rejects_duplicate_or_non_distinct_observations_in_audit(self) -> None:
        duplicate = fpga_monitor_session.run_monitor_session(
            ("scalar_control.call_return", "scalar_control.call_return")
        )

        self.assertFalse(duplicate.passed)
        self.assertIn("session loaded duplicate programs", duplicate.issues)
        self.assertIn("session observations are not distinct", duplicate.issues)

    def test_cli_validates_lists_prints_profile_and_run_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA monitor session issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S03")
        self.assertIn("selected_cases", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("scalar_control.call_return", stream.getvalue())
        self.assertIn("trap_syscall.sys_pause_iret", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["passed"])
        self.assertEqual(len(run["program_runs"]), 2)

    def test_documentation_names_command_flow_signatures_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-monitor-multi-program-session.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I32-S03",
            "python tools\\fpga_monitor_session.py --check",
            "python tools\\fpga_monitor_firmware.py --check",
            "python tools\\fpga_bram_images.py --check",
            "python tools\\fpga_smoke_corpus.py --check",
            "scalar_control.call_return",
            "trap_syscall.sys_pause_iret",
            "LOAD_IMAGE",
            "RESUME",
            "manifest_image_sha256",
            "ram_image_sha256",
            "expected LED",
            "expected UART",
            "expected probe",
            "signature_digest",
            "I32-S04",
            "I32-S05",
            "I32-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

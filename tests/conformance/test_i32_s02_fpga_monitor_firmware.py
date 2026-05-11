"""I32-S02 conformance tests for FPGA monitor firmware fixtures."""

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
TOOL = ROOT / "tools" / "fpga_monitor_firmware.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status, fpga_monitor_firmware, fpga_monitor_profile


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_monitor_firmware_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMonitorFirmwareTests(unittest.TestCase):
    def test_monitor_firmware_self_validation_passes(self) -> None:
        self.assertEqual(fpga_monitor_firmware.validate_fpga_monitor_firmware(ROOT), ())

    def test_profile_names_dependencies_states_and_fixtures(self) -> None:
        profile = fpga_monitor_firmware.fpga_monitor_firmware_profile()

        self.assertEqual(profile.story, "I32-S02")
        self.assertEqual(profile.status, "rom_monitor_trap_shell_fixtures")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.command_profile_gate, "python tools\\fpga_monitor_profile.py --check")
        self.assertEqual(profile.program_loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(profile.uart_status_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.debug_packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(
            profile.kernel_handler_gate,
            "python -m unittest tests.conformance.test_i14_s02_kernel_handlers",
        )
        self.assertEqual(profile.max_commands, 8)
        self.assertEqual(profile.allowed_entry_memory, "instruction_rom")

        fixture_ids = {fixture.fixture_id for fixture in profile.fixtures}
        self.assertIn("rom_monitor.load_resume_ok", fixture_ids)
        self.assertIn("rom_monitor.reject_bad_hash", fixture_ids)
        self.assertIn("trap_shell.bad_command_idle", fixture_ids)

    def test_load_resume_fixture_installs_program_clears_tags_and_resumes(self) -> None:
        run = fpga_monitor_firmware.run_monitor_firmware_fixture(
            "rom_monitor.load_resume_ok"
        )

        self.assertTrue(run.passed)
        self.assertEqual(run.final_snapshot.monitor_state, "program_running")
        self.assertFalse(run.final_snapshot.halted)
        self.assertEqual(run.final_snapshot.loaded_program_id, "relocation.branch_call_data_fpga")
        self.assertNotEqual(run.final_snapshot.data_ram_checksum, 0)
        self.assertEqual(run.final_snapshot.tag_bits_set, 0)
        self.assertEqual(
            tuple(result.status_name for result in run.command_results),
            ("OK", "OK", "OK", "OK", "OK"),
        )
        load_result = run.command_results[2]
        self.assertEqual(load_result.loader_status_name, "OK")
        self.assertEqual(load_result.installed_cells, 0x1000)
        self.assertEqual(load_result.report.debug_packet.pass_fail_state, 0)

        resume_result = run.command_results[-1]
        self.assertEqual(resume_result.report.debug_packet.pass_fail_state, 1)
        self.assertEqual(
            fpga_debug_status.validate_debug_status_packet(resume_result.report.debug_packet),
            (),
        )

    def test_bad_hash_fixture_reports_loader_error_without_memory_mutation(self) -> None:
        run = fpga_monitor_firmware.run_monitor_firmware_fixture(
            "rom_monitor.reject_bad_hash"
        )

        self.assertTrue(run.passed)
        self.assertEqual(run.final_snapshot.monitor_state, "safe_idle")
        self.assertTrue(run.final_snapshot.halted)
        self.assertEqual(run.final_snapshot.loaded_program_id, "")
        self.assertEqual(run.final_snapshot.data_ram_checksum, run.initial_snapshot.data_ram_checksum)
        self.assertEqual(run.final_snapshot.tag_bits_set, 0)

        load_result = run.command_results[-1]
        self.assertEqual(load_result.status_name, "LOADER_ERROR")
        self.assertEqual(load_result.loader_status_name, "BAD_HASH")
        self.assertIn("BAD_HASH", load_result.report.uart_message)
        self.assertEqual(load_result.report.debug_packet.pass_fail_state, 4)
        self.assertTrue(
            load_result.report.debug_packet.flags
            & fpga_debug_status.debug_status_flag_mask("fault_valid")
        )

    def test_trap_shell_fixture_rejects_bad_command_and_restores_with_iret(self) -> None:
        run = fpga_monitor_firmware.run_monitor_firmware_fixture(
            "trap_shell.bad_command_idle"
        )

        self.assertTrue(run.passed)
        self.assertEqual(run.final_snapshot.monitor_state, "trap_shell_idle")
        self.assertTrue(run.final_snapshot.halted)
        self.assertTrue(run.final_snapshot.trap_shell_active)
        self.assertEqual(run.final_snapshot.data_ram_checksum, run.initial_snapshot.data_ram_checksum)

        bad_command = run.command_results[1]
        self.assertEqual(bad_command.status_name, "BAD_COMMAND")
        self.assertEqual(bad_command.report.debug_packet.pass_fail_state, 4)

        self.assertIsNotNone(run.trap_shell_restore)
        assert run.trap_shell_restore is not None
        self.assertTrue(run.trap_shell_restore.passed)
        self.assertEqual(
            run.trap_shell_restore.final_pcc_cell,
            run.trap_shell_restore.restored_epcc_cell,
        )
        self.assertEqual(
            run.trap_shell_restore.final_pcc_slot,
            run.trap_shell_restore.restored_epcc_slot,
        )

    def test_bounded_stream_rejects_overlong_command_list_before_mutation(self) -> None:
        commands = tuple(
            fpga_monitor_firmware.MonitorFirmwareCommandRequest(
                fpga_monitor_profile.COMMAND_HELLO
            )
            for _ in range(fpga_monitor_firmware.MAX_MONITOR_COMMANDS + 1)
        )

        state, results = fpga_monitor_firmware.run_monitor_firmware_stream(commands)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status_name, "BAD_LENGTH")
        self.assertEqual(state.monitor_state, "safe_idle")
        self.assertEqual(state.loader_state.loaded_program_id, "")
        self.assertEqual(sum(state.loader_state.data_ram), 0)

    def test_cli_validates_lists_json_and_runs_fixtures(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA monitor firmware issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S02")
        self.assertIn("fixtures", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("rom_monitor.load_resume_ok", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fixtures"])

        self.assertEqual(result, 0)
        fixture_runs = json.loads(stream.getvalue())
        self.assertTrue(all(run["passed"] for run in fixture_runs))

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run-fixture", "trap_shell.bad_command_idle"])

        self.assertEqual(result, 0)
        parsed_run = json.loads(stream.getvalue())
        self.assertEqual(parsed_run["final_snapshot"]["monitor_state"], "trap_shell_idle")

    def test_documentation_names_fixture_commands_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-monitor-firmware-fixtures.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I32-S02",
            "python tools\\fpga_monitor_firmware.py --check",
            "python tools\\fpga_monitor_profile.py --check",
            "python tools\\fpga_program_loader.py --check",
            "python tools\\fpga_uart_status_streamer.py --check",
            "python tools\\fpga_debug_status_packet.py --check",
            "python -m unittest tests.conformance.test_i14_s02_kernel_handlers",
            "rom_monitor.load_resume_ok",
            "rom_monitor.reject_bad_hash",
            "trap_shell.bad_command_idle",
            "LOAD_IMAGE",
            "BAD_HASH",
            "LOADER_ERROR",
            "safe_idle",
            "trap_shell_idle",
            "tag_ram",
            "I32-S03",
            "I32-S04",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

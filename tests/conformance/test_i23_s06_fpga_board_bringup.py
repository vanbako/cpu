"""I23-S06 conformance tests for the FPGA board bring-up runbook."""

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
TOOL = ROOT / "tools" / "fpga_bringup_runbook.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_bringup


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_bringup_runbook_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaBoardBringupTests(unittest.TestCase):
    def test_bringup_runbook_self_validation_passes(self) -> None:
        self.assertEqual(fpga_bringup.validate_fpga_board_bringup(ROOT), ())

    def test_runbook_names_tang_mega_target_and_synthesis_dependency(self) -> None:
        runbook = fpga_bringup.fpga_board_bringup_runbook()

        self.assertEqual(runbook.story, "I23-S06")
        self.assertEqual(runbook.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(runbook.device, "GW5AST-LV138PG484A")
        self.assertEqual(runbook.ide_package, "PBG484A")
        self.assertEqual(runbook.top_module, "cpu_v01_fpga_top")
        self.assertEqual(
            runbook.synthesis_gate,
            "python tools\\fpga_synthesis_gate.py --check",
        )
        self.assertIn("SRAM first", runbook.programming_mode)

    def test_prerequisites_gate_physical_execution(self) -> None:
        prerequisites = {
            item.name: item
            for item in fpga_bringup.fpga_board_bringup_runbook().prerequisites
        }

        for name in (
            "device_package_confirmed",
            "i23_s05_gate_passed",
            "constraints_verified",
            "board_power_and_usb_ready",
            "programmer_selected",
        ):
            with self.subTest(name=name):
                self.assertIn(name, prerequisites)
                self.assertTrue(prerequisites[name].required)

        self.assertIn("GW5AST-LV138PG484A", prerequisites["device_package_confirmed"].evidence)
        self.assertIn("PBG484A", prerequisites["device_package_confirmed"].evidence)
        self.assertIn("PG484", prerequisites["device_package_confirmed"].blocker_if_missing)
        self.assertIn("FPG676", prerequisites["device_package_confirmed"].blocker_if_missing)
        self.assertIn("board_clk_i", prerequisites["constraints_verified"].evidence)
        self.assertIn("pass_led_o", prerequisites["constraints_verified"].evidence)

    def test_procedure_programs_sram_resets_and_captures_evidence(self) -> None:
        procedure = {
            step.name: step
            for step in fpga_bringup.fpga_board_bringup_runbook().procedure
        }

        for name in (
            "record_board_identity",
            "verify_synthesis_gate",
            "prepare_board",
            "program_sram",
            "release_reset",
            "capture_evidence",
        ):
            self.assertIn(name, procedure)

        self.assertIn("gw_sh", procedure["verify_synthesis_gate"].action)
        self.assertIn("SRAM", procedure["program_sram"].action)
        self.assertIn("board_reset_n_i", procedure["release_reset"].action)
        self.assertIn("pass_led_o", procedure["release_reset"].expected_observation)
        self.assertIn("fail_led_o", procedure["release_reset"].expected_observation)
        self.assertIn("heartbeat_led_o", procedure["release_reset"].expected_observation)

    def test_observation_and_evidence_contract_is_explicit(self) -> None:
        runbook = fpga_bringup.fpga_board_bringup_runbook()
        observations = {item.name: item for item in runbook.observations}
        evidence = {item.name: item for item in runbook.evidence}

        for name in ("heartbeat_led_o", "pass_led_o", "fail_led_o"):
            with self.subTest(name=name):
                self.assertIn(name, observations)
                self.assertTrue(observations[name].required)

        self.assertIn("status_retire_count_o", observations)
        self.assertIn("status_fault_code_o", observations)

        for name in (
            "device_scan_record",
            "i23_s05_report_bundle",
            "bitstream_path",
            "programming_log",
            "reset_observation",
            "led_photo_or_video",
            "documented_blocker",
        ):
            with self.subTest(name=name):
                self.assertIn(name, evidence)
                self.assertTrue(evidence[name].required)

    def test_triage_cases_cover_board_and_design_failures(self) -> None:
        symptoms = {
            case.symptom
            for case in fpga_bringup.fpga_board_bringup_runbook().triage
        }

        self.assertIn("no_jtag_device", symptoms)
        self.assertIn("programmer_rejects_device_or_package", symptoms)
        self.assertIn("no_heartbeat", symptoms)
        self.assertIn("fail_led_asserted", symptoms)
        self.assertIn("pass_never_asserts", symptoms)
        self.assertIn("timing_or_report_missing", symptoms)

    def test_command_plan_and_cli_work(self) -> None:
        plan = fpga_bringup.fpga_bringup_command_plan()
        self.assertIn("python tools\\fpga_synthesis_gate.py --check", plan)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", plan)
        self.assertTrue(any("Gowin Programmer SRAM mode" in command for command in plan))
        self.assertTrue(any("release board_reset_n_i" in command for command in plan))

        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA board bring-up issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I23-S06")
        self.assertEqual(parsed["board"], "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(parsed["top_module"], "cpu_v01_fpga_top")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("Gowin Programmer SRAM mode", stream.getvalue())

    def test_documentation_names_commands_observations_and_blocker(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-board-bringup.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S06", text)
        self.assertIn("python tools\\fpga_bringup_runbook.py --check", text)
        self.assertIn("Sipeed Tang Mega Dock with 138K SOM", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("python tools\\fpga_synthesis_gate.py --check", text)
        self.assertIn("Gowin Programmer SRAM", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("status_retire_count_o", text)
        self.assertIn("status_fault_code_o", text)
        self.assertIn("programming_log", text)
        self.assertIn("led_photo_or_video", text)
        self.assertIn("documented blocker", text)
        self.assertIn("PG484", text)
        self.assertIn("FPG676", text)


if __name__ == "__main__":
    unittest.main()

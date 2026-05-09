"""I29-S02 conformance tests for the FPGA DDR wrapper profile."""

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
TOOL = ROOT / "tools" / "fpga_ddr_wrapper.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_ddr_wrapper


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_ddr_wrapper_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaDdrWrapperTests(unittest.TestCase):
    def test_ddr_wrapper_self_validation_passes(self) -> None:
        self.assertEqual(fpga_ddr_wrapper.validate_fpga_ddr_wrapper(ROOT), ())

    def test_profile_names_story_status_gates_sources_and_plan(self) -> None:
        profile = fpga_ddr_wrapper.fpga_ddr_wrapper_profile()

        self.assertEqual(profile.story, "I29-S02")
        self.assertEqual(profile.status, "rtl_calibration_gate_board_ip_blocked")
        self.assertEqual(profile.boundary_gate, "python tools\\fpga_external_memory.py --check")
        self.assertEqual(profile.reset_cdc_gate, "python tools\\fpga_reset_cdc.py --check")
        self.assertIn("rtl/cpu_v01_fpga_ddr_calibration_gate.sv", profile.rtl_sources)
        self.assertIn("rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv", profile.rtl_sources)
        self.assertTrue(
            any("cpu_v01_fpga_ddr_calibration_gate_tb" in command for command in profile.verilator_commands)
        )
        self.assertTrue(any("MAKEFLAGS" in command and "PYTHON3" in command for command in profile.verilator_commands))
        self.assertTrue(any("--binary" in command and "--Mdir obj_dir\\ddr_gate" in command for command in profile.verilator_commands))
        self.assertIn(
            "obj_dir\\ddr_gate\\Vcpu_v01_fpga_ddr_calibration_gate_tb.exe",
            profile.verilator_commands,
        )

    def test_visibility_signals_cover_calibration_ready_timeout_and_visible_fail(self) -> None:
        profile = fpga_ddr_wrapper.fpga_ddr_wrapper_profile()

        for signal in (
            "status_calibration_done_o",
            "status_calibration_error_o",
            "status_init_in_progress_o",
            "status_controller_ready_o",
            "status_access_gate_closed_o",
            "status_timeout_o",
            "status_error_code_o",
            "fail_visible_o",
        ):
            with self.subTest(signal=signal):
                self.assertEqual(profile.visibility_by_name(signal).name, signal)

        self.assertEqual(profile.visibility_by_name("status_error_code_o").width, "16")
        self.assertIn("DDR training completed", profile.visibility_by_name("status_calibration_done_o").visible_use)
        self.assertIn("blocked", profile.visibility_by_name("status_access_gate_closed_o").visible_use)
        self.assertIn("LED, UART/status", profile.visibility_by_name("fail_visible_o").visible_use)

    def test_gate_rules_capture_access_gating_faults_timeout_and_reset(self) -> None:
        profile = fpga_ddr_wrapper.fpga_ddr_wrapper_profile()

        gate = profile.rule_by_name("gate_until_controller_ready")
        self.assertIn("controller_ready is false", gate.condition)
        self.assertIn("ACCESS_FAULT", gate.behavior)

        ready = profile.rule_by_name("pass_ready_requests")
        self.assertIn("one CPU request", ready.behavior)

        controller_error = profile.rule_by_name("controller_error_fault")
        self.assertIn("ctrl_rsp_error_i", controller_error.condition)
        self.assertIn("fail_visible_o", controller_error.behavior)

        timeout = profile.rule_by_name("calibration_timeout_visible_fail")
        self.assertIn("CALIBRATION_TIMEOUT_CYCLES", timeout.condition)
        self.assertIn("status_timeout_o", timeout.behavior)

        reset = profile.rule_by_name("reset_request_clears_sticky_status")
        self.assertIn("controller_reset_o", reset.behavior)

    def test_rtl_and_testbench_name_calibration_gate_behavior(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_ddr_calibration_gate.sv").read_text(
            encoding="utf-8"
        )
        tb = (ROOT / "rtl" / "cpu_v01_fpga_ddr_calibration_gate_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_ddr_calibration_gate",
            "parameter int CALIBRATION_TIMEOUT_CYCLES = 25_000_000",
            "calibration_done_i",
            "calibration_error_i",
            "init_in_progress_i",
            "controller_ready",
            "assign ctrl_req_valid_o = cpu_req_valid_i && controller_ready && !outstanding_q",
            "assign status_access_gate_closed_o = !controller_ready",
            "assign fail_visible_o = calibration_error_i || timeout_q || controller_error_seen_q",
            "EXC_ACCESS_FAULT",
            "controller_reset_o",
            "status_timeout_o",
            "status_error_code_o",
        ):
            self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_ddr_calibration_gate_tb",
            ".CALIBRATION_TIMEOUT_CYCLES(4)",
            "FPGA DDR calibration gate forwarded request before controller_ready",
            "FPGA DDR calibration gate did not expose controller_ready",
            "FPGA DDR calibration gate did not convert controller error to CPU fault",
            "FPGA DDR calibration gate did not fail visibly on calibration timeout",
            "FPGA DDR calibration gate did not forward reset_request",
        ):
            self.assertIn(token, tb)

    def test_cli_validates_renders_json_and_lists_sections(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA DDR wrapper issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I29-S02")
        self.assertEqual(parsed["status"], "rtl_calibration_gate_board_ip_blocked")

        for flag, expected in (
            ("--signals", "status_controller_ready_o\t1"),
            ("--rules", "gate_until_controller_ready"),
            ("--plan", "cpu_v01_fpga_ddr_calibration_gate_tb"),
            ("--blockers", "vendor DDR controller IP"),
        ):
            with self.subTest(flag=flag):
                stream = StringIO()
                with contextlib.redirect_stdout(stream):
                    result = tool.main([flag])
                self.assertEqual(result, 0)
                self.assertIn(expected, stream.getvalue())

    def test_documentation_names_visibility_gating_blockers_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-ddr-wrapper.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I29-S02",
            "python tools\\fpga_ddr_wrapper.py --check",
            "python tools\\fpga_external_memory.py --check",
            "python tools\\fpga_reset_cdc.py --check",
            "rtl/cpu_v01_fpga_ddr_calibration_gate.sv",
            "rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv",
            "calibration_done",
            "calibration_error",
            "controller_ready",
            "access_gate_closed",
            "fail_visible_o",
            "ACCESS_FAULT",
            "UART/status",
            "board-specific DDR IP",
            "cpu_v01_fpga_top still needs an external-memory decoder",
            "I29-S03",
            "I29-S04",
            "I29-S05",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

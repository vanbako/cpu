"""I29-S01 conformance tests for the FPGA external-memory boundary profile."""

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
TOOL = ROOT / "tools" / "fpga_external_memory.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory, mmu, platform


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_external_memory_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaExternalMemoryTests(unittest.TestCase):
    def test_external_memory_self_validation_passes(self) -> None:
        self.assertEqual(fpga_external_memory.validate_fpga_external_memory(ROOT), ())

    def test_profile_names_target_and_prerequisite_gates(self) -> None:
        profile = fpga_external_memory.fpga_external_memory_profile()

        self.assertEqual(profile.story, "I29-S01")
        self.assertEqual(profile.name, "cpu_v01_fpga_external_memory_boundary")
        self.assertEqual(profile.status, "boundary_profile")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.fpga_top_module, "cpu_v01_fpga_top")
        for gate in (
            "python tools\\fpga_soc_platform.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "python -m unittest tests.conformance.test_i19_s03_external_transfers",
            "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
        ):
            self.assertIn(gate, profile.prerequisite_gates)

    def test_external_ddr_window_is_non_overlapping_and_uncacheable(self) -> None:
        profile = fpga_external_memory.fpga_external_memory_profile()
        window = profile.window_by_name("external_ddr_payload")

        self.assertEqual(window.base_cell, 0x01000000)
        self.assertEqual(window.end_cell, 0x02000000)
        self.assertEqual(window.size_cells, 0x01000000)
        self.assertEqual(window.memory_type, mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE)
        self.assertEqual(window.memory_type_name, "normal_uncacheable")
        self.assertIn("normal uncacheable", window.cacheability)
        self.assertIn("controller_ready", window.access_policy)
        self.assertIn("tag sidecar deferred", window.tag_policy)
        self.assertIn("I29-S04", window.tag_policy)

        for region in platform.TEST_PLATFORM_PROFILE.memory_regions:
            with self.subTest(region=region.name):
                self.assertFalse(window.overlaps_platform_region(region))

    def test_controller_signals_and_calibration_status_are_explicit(self) -> None:
        profile = fpga_external_memory.fpga_external_memory_profile()

        for signal in (
            "ext_mem_req_valid",
            "ext_mem_req_ready",
            "ext_mem_req_addr",
            "ext_mem_req_wdata",
            "ext_mem_rsp_valid",
            "ext_mem_rsp_rdata",
            "ext_mem_rsp_error",
            "ddr_ui_clk",
            "ddr_ui_reset",
        ):
            with self.subTest(signal=signal):
                self.assertEqual(profile.signal_by_name(signal).name, signal)

        self.assertEqual(profile.signal_by_name("ext_mem_req_addr").width, "48")
        self.assertEqual(profile.signal_by_name("ext_mem_req_valid").direction, "out")
        self.assertEqual(profile.signal_by_name("ext_mem_req_ready").direction, "in")

        self.assertEqual(profile.status_by_name("calibration_done").access, "ro")
        self.assertEqual(profile.status_by_name("calibration_done").reset_value, 0)
        self.assertEqual(profile.status_by_name("calibration_error").access, "ro")
        self.assertEqual(profile.status_by_name("init_in_progress").reset_value, 1)
        self.assertIn("calibration_done", profile.status_by_name("controller_ready").purpose)
        self.assertEqual(profile.status_by_name("reset_request").access, "wo")

    def test_cpu_owned_fault_rules_cover_calibration_controller_decode_and_tags(self) -> None:
        profile = fpga_external_memory.fpga_external_memory_profile()

        for rule_name in (
            "calibration_not_ready",
            "controller_error",
            "external_window_decode",
            "tag_sidecar_unavailable",
            "cache_policy_mismatch",
        ):
            with self.subTest(rule=rule_name):
                self.assertEqual(profile.fault_rule_by_name(rule_name).owner, "CPU")

        not_ready = profile.fault_rule_by_name("calibration_not_ready")
        self.assertIn("controller_ready", not_ready.condition)
        self.assertIn("ACCESS_FAULT", not_ready.architectural_result)

        tag_rule = profile.fault_rule_by_name("tag_sidecar_unavailable")
        self.assertIn("CLC or CSC", tag_rule.condition)
        self.assertIn("payload LD/ST", tag_rule.architectural_result)

        self.assertTrue(any("board-specific I29-S02 wrapper" in item for item in profile.board_ip_separation))
        self.assertTrue(any("I29-S05" in item for item in profile.next_story_handoffs))

    def test_cli_validates_renders_json_and_lists_profile_sections(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA external memory issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I29-S01")
        self.assertEqual(parsed["memory_windows"][0]["memory_type_name"], "normal_uncacheable")

        for flag, expected in (
            ("--windows", "external_ddr_payload\t0x01000000"),
            ("--signals", "ext_mem_req_valid\tout"),
            ("--status", "calibration_done\tro"),
            ("--faults", "tag_sidecar_unavailable\tCPU"),
        ):
            with self.subTest(flag=flag):
                stream = StringIO()
                with contextlib.redirect_stdout(stream):
                    result = tool.main([flag])
                self.assertEqual(result, 0)
                self.assertIn(expected, stream.getvalue())

    def test_documentation_names_boundary_window_status_faults_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-external-memory.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I29-S01",
            "python tools\\fpga_external_memory.py --check",
            "python tools\\fpga_soc_platform.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "python -m unittest tests.conformance.test_i19_s03_external_transfers",
            "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
            "0x01000000",
            "0x02000000",
            "normal uncacheable",
            "DDR controller",
            "calibration_done",
            "calibration_error",
            "controller_ready",
            "tag policy",
            "CPU-owned fault",
            "board-specific IP",
            "I29-S02",
            "I29-S04",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

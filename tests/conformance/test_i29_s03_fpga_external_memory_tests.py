"""I29-S03 conformance tests for FPGA external-memory test firmware."""

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
TOOL = ROOT / "tools" / "fpga_external_memory_tests.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory, fpga_external_memory_tests


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_external_memory_tests_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaExternalMemoryTestsFirmwareTests(unittest.TestCase):
    def test_external_memory_tests_self_validation_passes(self) -> None:
        self.assertEqual(fpga_external_memory_tests.validate_fpga_external_memory_tests(ROOT), ())

    def test_profile_names_gates_window_categories_and_blockers(self) -> None:
        profile = fpga_external_memory_tests.fpga_external_memory_tests_profile()
        external = fpga_external_memory.fpga_external_memory_profile().window_by_name(
            "external_ddr_payload"
        )

        self.assertEqual(profile.story, "I29-S03")
        self.assertEqual(profile.program_id, "external_memory.ddr_bram_resident_test")
        self.assertEqual(profile.execution_region, "bram_resident")
        self.assertEqual(profile.board_status, "blocked_until_board_ddr_ip")
        self.assertEqual(profile.ddr_wrapper_gate, "python tools\\fpga_ddr_wrapper.py --check")
        self.assertEqual(profile.smoke_corpus_gate, "python tools\\fpga_smoke_corpus.py --check")
        self.assertEqual(profile.debug_status_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(profile.external_window_name, "external_ddr_payload")
        self.assertEqual(profile.external_window_base, external.base_cell)
        self.assertEqual(profile.external_window_end, external.end_cell)
        self.assertEqual(
            set(profile.required_categories),
            fpga_external_memory_tests.REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES,
        )
        self.assertEqual(
            {case.category for case in profile.cases},
            fpga_external_memory_tests.REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES,
        )
        self.assertTrue(any("external-memory decoder" in blocker for blocker in profile.blockers))
        self.assertTrue(any("I29-S05" in handoff for handoff in profile.handoffs))

    def test_cases_cover_required_firmware_behaviors_and_observation_signatures(self) -> None:
        profile = fpga_external_memory_tests.fpga_external_memory_tests_profile()

        for case_id, category in (
            ("walking_pattern.low_window", "walking_pattern"),
            ("address_line.power_of_two_offsets", "address_line"),
            ("burst.contiguous_cells", "burst"),
            ("alignment.integer_object", "alignment"),
            ("fault_injection.controller_error", "fault_injection"),
        ):
            with self.subTest(case_id=case_id):
                case = profile.case_by_id(case_id)
                self.assertEqual(case.category, category)
                self.assertTrue(case.addresses)
                self.assertGreaterEqual(case.progress_code, fpga_external_memory_tests.PROGRESS_CODE_BASE)
                self.assertIn("UART/status", case.expected_uart_signature)
                self.assertIn("probe", case.expected_probe_signature.lower())

        self.assertEqual(
            profile.case_by_id("fault_injection.controller_error").fault_injection,
            "controller_error",
        )
        address_line = profile.case_by_id("address_line.power_of_two_offsets")
        self.assertIn(address_line.start_cell + 64, address_line.addresses)

    def test_modeled_run_passes_and_records_expected_fault_samples(self) -> None:
        run = fpga_external_memory_tests.run_fpga_external_memory_tests()

        self.assertEqual(run.story, "I29-S03")
        self.assertEqual(run.program_id, "external_memory.ddr_bram_resident_test")
        self.assertEqual(run.execution_region, "bram_resident")
        self.assertEqual(run.board_status, "blocked_until_board_ddr_ip")
        self.assertTrue(run.controller_ready_required)
        self.assertTrue(run.passed)
        self.assertTrue(run.pass_led)
        self.assertFalse(run.fail_led)
        self.assertEqual(run.status_codes[-1], fpga_external_memory_tests.PROGRESS_CODE_PASS)
        self.assertEqual(len(run.results), 5)
        self.assertTrue(all(result.passed for result in run.results))
        self.assertTrue(run.result_by_id("alignment.integer_object").fault_observed)
        self.assertTrue(run.result_by_id("fault_injection.controller_error").fault_observed)
        self.assertGreater(run.result_by_id("walking_pattern.low_window").writes, 0)
        self.assertGreater(run.result_by_id("burst.contiguous_cells").reads, 0)

    def test_cli_validates_renders_lists_runs_and_prints_progress(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA external-memory test issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I29-S03")
        self.assertIn("cases", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["passed"])
        self.assertEqual(run["status_codes"][-1], fpga_external_memory_tests.PROGRESS_CODE_PASS)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--cases"])

        self.assertEqual(result, 0)
        self.assertIn("walking_pattern.low_window", stream.getvalue())
        self.assertIn("fault_injection.controller_error", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--progress"])

        self.assertEqual(result, 0)
        self.assertIn("0x2903F0", stream.getvalue())

    def test_documentation_names_commands_cases_observations_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-external-memory-tests.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I29-S03",
            "python tools\\fpga_external_memory_tests.py --check",
            "python tools\\fpga_ddr_wrapper.py --check",
            "python tools\\fpga_smoke_corpus.py --check",
            "python tools\\fpga_debug_status_packet.py --check",
            "BRAM-resident",
            "external_ddr_payload",
            "controller_ready",
            "walking_pattern",
            "address_line",
            "burst",
            "alignment",
            "fault_injection",
            "debug/status",
            "UART/status",
            "ACCESS_FAULT",
            "I29-S04",
            "I29-S05",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

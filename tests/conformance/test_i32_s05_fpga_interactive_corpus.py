"""I32-S05 conformance tests for the FPGA interactive program corpus."""

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
TOOL = ROOT / "tools" / "fpga_interactive_corpus.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_interactive_corpus, fpga_program_loader


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_interactive_corpus_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaInteractiveCorpusTests(unittest.TestCase):
    def test_interactive_corpus_self_validation_passes(self) -> None:
        self.assertEqual(fpga_interactive_corpus.validate_fpga_interactive_corpus(ROOT), ())

    def test_profile_names_dependencies_and_required_categories(self) -> None:
        profile = fpga_interactive_corpus.fpga_interactive_corpus_profile()

        self.assertEqual(profile.story, "I32-S05")
        self.assertEqual(profile.status, "published_interactive_board_program_corpus")
        self.assertEqual(profile.monitor_session_gate, "python tools\\fpga_monitor_session.py --check")
        self.assertEqual(profile.toolchain_corpus_gate, "python tools\\toolchain_corpus.py --check")
        self.assertEqual(profile.smoke_corpus_gate, "python tools\\fpga_smoke_corpus.py --check")
        self.assertEqual(profile.loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(
            set(profile.required_categories),
            {
                "scalar_control",
                "capability_memory",
                "trap_syscall",
                "loader_rejection",
                "failure_path",
            },
        )
        self.assertEqual({case.category for case in profile.cases}, set(profile.required_categories))

    def test_image_ready_cases_publish_loader_hashes_and_expected_observations(self) -> None:
        profile = fpga_interactive_corpus.fpga_interactive_corpus_profile()

        for case_id in fpga_interactive_corpus.IMAGE_READY_CASE_IDS:
            case = profile.case_by_id(case_id)
            request = fpga_program_loader.program_load_request_for_program(case.program_id)

            with self.subTest(case_id=case_id):
                self.assertEqual(case.load_mode, "monitor_load_image")
                self.assertEqual(case.manifest_hash_kind, "generated_bram_manifest")
                self.assertEqual(case.manifest_image_sha256, request.manifest_image_sha256)
                self.assertEqual(case.ram_image_sha256, request.ram_image_sha256)
                self.assertEqual(len(case.manifest_image_sha256), 64)
                self.assertEqual(len(case.ram_image_sha256), 64)
                self.assertEqual(case.expected_monitor_status, "OK")
                self.assertEqual(case.expected_loader_status, "OK")
                self.assertTrue(case.expected_uart_signature)
                self.assertTrue(case.expected_probe_signature)
                self.assertIn("verilator_diff_harness.py --case-id", case.replay_command)

    def test_loader_rejection_case_reports_bad_hash_without_memory_mutation(self) -> None:
        profile = fpga_interactive_corpus.fpga_interactive_corpus_profile()
        case = profile.case_by_id("loader_rejection.bad_hash")
        run = fpga_interactive_corpus.run_loader_rejection_case()

        self.assertEqual(case.load_mode, "monitor_loader_rejection")
        self.assertEqual(case.expected_monitor_status, "LOADER_ERROR")
        self.assertEqual(case.expected_loader_status, "BAD_HASH")
        self.assertEqual(case.rejected_manifest_image_sha256, "0" * 64)
        self.assertNotEqual(case.rejected_manifest_image_sha256, case.manifest_image_sha256)
        self.assertIn("BAD_HASH", case.expected_uart_signature)
        self.assertIn("LOADER_ERROR", case.expected_uart_signature)
        self.assertIn("fpga_monitor_firmware.py --run-fixture", case.replay_command)

        self.assertTrue(run.passed)
        failed = run.command_results[-1]
        self.assertEqual(failed.status_name, "LOADER_ERROR")
        self.assertEqual(failed.loader_status_name, "BAD_HASH")
        self.assertEqual(run.final_snapshot.loaded_program_id, run.initial_snapshot.loaded_program_id)
        self.assertEqual(run.final_snapshot.data_ram_checksum, run.initial_snapshot.data_ram_checksum)
        self.assertEqual(run.final_snapshot.tag_bits_set, run.initial_snapshot.tag_bits_set)

    def test_failure_path_is_replay_only_with_planned_hashes(self) -> None:
        profile = fpga_interactive_corpus.fpga_interactive_corpus_profile()
        case = profile.case_by_id("failure_path.divide_by_zero")

        self.assertEqual(case.load_mode, "replay_only_until_fault_harness")
        self.assertEqual(case.expected_monitor_status, "REPLAY_ONLY")
        self.assertEqual(case.expected_loader_status, "REPLAY_ONLY")
        self.assertEqual(case.replay_case_id, "fault_cases.divide_by_zero")
        self.assertIn("--case-id fault_cases.divide_by_zero", case.replay_command)
        self.assertIn("planned", case.manifest_hash_kind)
        self.assertEqual(len(case.manifest_image_sha256), 64)
        self.assertEqual(len(case.ram_image_sha256), 64)
        self.assertIn("fault_code", case.expected_uart_signature)
        self.assertTrue(case.expected_probe_signature)

    def test_cli_validates_lists_and_prints_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA interactive corpus issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S05")
        self.assertEqual(len(parsed["cases"]), 5)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("loader_rejection.bad_hash", stream.getvalue())
        self.assertIn("failure_path.divide_by_zero", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--case", "loader_rejection.bad_hash"])

        self.assertEqual(result, 0)
        case = json.loads(stream.getvalue())
        self.assertEqual(case["expected_loader_status"], "BAD_HASH")

    def test_documentation_names_corpus_hashes_observations_and_handoff(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-interactive-program-corpus.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I32-S05",
            "python tools\\fpga_interactive_corpus.py --check",
            "python tools\\fpga_monitor_session.py --check",
            "python tools\\toolchain_corpus.py --check",
            "python tools\\fpga_smoke_corpus.py --check",
            "python tools\\fpga_program_loader.py --check",
            "scalar/control",
            "capability memory",
            "trap/syscall",
            "loader rejection",
            "failure-path",
            "scalar_control.call_return",
            "capability_memory.csc_clc_st48_ld48",
            "trap_syscall.sys_pause_iret",
            "loader_rejection.bad_hash",
            "failure_path.divide_by_zero",
            "manifest_image_sha256",
            "ram_image_sha256",
            "rejected_manifest_image_sha256",
            "expected UART",
            "expected probe",
            "BAD_HASH",
            "LOADER_ERROR",
            "python tools\\verilator_diff_harness.py --case-id fault_cases.divide_by_zero",
            "I32-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

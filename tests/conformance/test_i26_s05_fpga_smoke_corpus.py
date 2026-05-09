"""I26-S05 conformance tests for the FPGA smoke-program corpus."""

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
TOOL = ROOT / "tools" / "fpga_smoke_corpus.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_bram_images, fpga_smoke_corpus


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_smoke_corpus_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSmokeCorpusTests(unittest.TestCase):
    def test_smoke_corpus_self_validation_passes(self) -> None:
        self.assertEqual(fpga_smoke_corpus.validate_fpga_smoke_corpus(ROOT), ())

    def test_profile_covers_required_categories_and_gates(self) -> None:
        profile = fpga_smoke_corpus.fpga_smoke_corpus_profile()

        self.assertEqual(profile.story, "I26-S05")
        self.assertEqual(profile.bram_image_gate, "python tools\\fpga_bram_images.py --check")
        self.assertEqual(profile.replay_gate, "python tools\\fpga_replay_mapper.py --check")
        self.assertEqual(set(profile.required_categories), fpga_smoke_corpus.REQUIRED_SMOKE_CATEGORIES)
        self.assertEqual({case.category for case in profile.cases}, fpga_smoke_corpus.REQUIRED_SMOKE_CATEGORIES)
        self.assertEqual(len({case.case_id for case in profile.cases}), len(profile.cases))

    def test_image_ready_cases_are_generated_by_i26_s02(self) -> None:
        profile = fpga_smoke_corpus.fpga_smoke_corpus_profile()
        image_ready = {
            case.program_id for case in profile.cases if case.bram_image_status == "image_ready"
        }
        generated = {bundle.program_id for bundle in fpga_bram_images.fpga_bram_image_bundles()}

        self.assertIn("call_return.direct_call_ret_fpga", image_ready)
        self.assertIn("capability_memory.csc_clc_st48_ld48_fpga", image_ready)
        self.assertIn("syscall_trap.sys_pause_iret_fpga", image_ready)
        self.assertTrue(image_ready <= generated)

    def test_cases_name_expected_led_uart_probe_signatures_and_replay(self) -> None:
        profile = fpga_smoke_corpus.fpga_smoke_corpus_profile()

        for case in profile.cases:
            with self.subTest(case_id=case.case_id):
                self.assertTrue(case.expected_led_signature)
                self.assertTrue(case.expected_uart_signature)
                self.assertTrue(case.expected_probe_signature)
                self.assertIn("led", case.expected_led_signature.lower())
                self.assertTrue(
                    any(
                        token in case.expected_uart_signature.lower()
                        for token in ("fault", "pass", "retire", "trap")
                    )
                )
                self.assertTrue(case.replay_case_id)

        self.assertEqual(
            profile.case_by_id("capability_memory.csc_clc_st48_ld48").replay_case_id,
            "core.cap_mem.memory_tag_ops",
        )
        self.assertEqual(
            profile.case_by_id("translation_fault.mmu_tlb_page_fault").replay_case_id,
            "core.mmu_tlb.translation_sfence",
        )
        self.assertEqual(
            profile.case_by_id("failure_path.divide_by_zero").replay_case_id,
            "fault_cases.divide_by_zero",
        )

    def test_cli_validates_lists_prints_json_and_case(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA smoke corpus issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("capability_memory.csc_clc_st48_ld48", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--case", "trap_syscall.sys_pause_iret"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["category"], "trap_syscall")
        self.assertEqual(parsed["program_id"], "syscall_trap.sys_pause_iret_fpga")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I26-S05")
        self.assertIn("cases", parsed)

    def test_documentation_names_categories_signatures_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-smoke-program-corpus.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I26-S05", text)
        self.assertIn("python tools\\fpga_smoke_corpus.py --check", text)
        self.assertIn("python tools\\fpga_bram_images.py --check", text)
        self.assertIn("python tools\\fpga_replay_mapper.py --check", text)
        for token in (
            "reset_pass",
            "scalar_control",
            "capability_memory",
            "trap_syscall",
            "translation_fault",
            "failure_path",
            "expected LED",
            "expected UART",
            "expected probe",
            "call_return.direct_call_ret_fpga",
            "capability_memory.csc_clc_st48_ld48_fpga",
            "I26-S04",
            "I24-S05",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

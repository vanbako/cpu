"""I22-S06 conformance tests for integrated core MMU/TLB execution."""

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
TOOL = ROOT / "tools" / "rtl_core_mmu_tlb.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_mmu_tlb, rtl_mmu_tlb


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_mmu_tlb_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreMmuTlbTests(unittest.TestCase):
    def test_rtl_core_mmu_tlb_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_mmu_tlb.validate_rtl_core_mmu_tlb(ROOT), ())
        for path in rtl_core_mmu_tlb.RTL_CORE_MMU_TLB_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_i21_mmu_tlb_cases(self) -> None:
        rows = rtl_core_mmu_tlb.integrated_mmu_tlb_coverage_rows()
        by_case = {row.case_id: row for row in rows}
        covered = {row.mnemonic for row in rows}

        self.assertGreaterEqual(covered, set(rtl_mmu_tlb.MMU_TLB_MNEMONICS))
        self.assertIn(
            "translation:bare_identity",
            by_case["bare_mode.ld48_identity"].retire_effects,
        )
        self.assertIn("dtlb_fill", by_case["radix4.ld48_page_walk_fill"].retire_effects)
        self.assertIn(
            "dtlb_hit_stale",
            by_case["tlb.stale_hit_before_va_asid_sfence"].retire_effects,
        )
        self.assertEqual(
            by_case["sfence.vm_va_asid_invalidates_stale"].retire_effects,
            ("tlb_invalidate:VA_ASID",),
        )
        self.assertEqual(
            by_case["radix4.permission_page_fault"].retire_effects,
            ("fault:PAGE_FAULT", "translation_fault:NORMAL_COHERENT"),
        )
        self.assertEqual(
            by_case["radix4.reserved_memory_type_page_fault"].retire_effects,
            ("fault:PAGE_FAULT", "translation_fault:RESERVED"),
        )

    def test_core_names_translation_tlb_and_sfence_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "MMU_TLB_VIRTUAL_ADDRESS",
            "translation_result_t",
            "satp_mode_value",
            "satp_root_ppn",
            "current_asid",
            "translate_instruction_address",
            "translate_data_address",
            "mark_translation_fault",
            "commit_tlb_invalidate",
            "mem_effective_address_q",
            "dtlb_valid_q",
            "mapping_a_removed_q",
            "retire_packet_q.translation_valid",
            "retire_packet_q.tlb_fill_valid",
            "retire_packet_q.tlb_invalidate_valid",
            "OPC_SFENCE_VM_24",
            "OPC_SFENCE_VM_VA_ASID_24",
            "EXC_PAGE_FAULT",
            "MEMORY_TYPE_RESERVED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_mmu_tlb_testbench_checks_translation_sfence_and_fault_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_mmu_tlb_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_core_mmu_tlb_tb",
            "cpu_v01_core_mmu_tlb_fixture",
            "CCSRRD C1, PCC",
            "CSRWR SATP, D4",
            "SFENCE.VM.VA_ASID D2, D6",
            "SFENCE.VM.ASID D6",
            "bare SATP identity translation result mismatch",
            "RADIX4 page-walk translation result mismatch",
            "stale TLB hit before SFENCE result mismatch",
            "ASID/global TLB scope result mismatch",
            "permission page fault mismatch",
            "reserved memory type page fault mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_and_renders_integrated_mmu_tlb_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core MMU/TLB issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        by_case = {row["case_id"]: row for row in parsed}
        self.assertIn("radix4.ld48_page_walk_fill", by_case)
        self.assertIn("sfence.vm_va_asid_invalidates_stale", by_case)
        self.assertEqual(
            by_case["radix4.reserved_memory_type_page_fault"]["retire_effects"],
            ["fault:PAGE_FAULT", "translation_fault:RESERVED"],
        )

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "rtl-integrated-core-mmu-tlb.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S06", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_mmu_tlb_tb.sv", text)
        self.assertIn("python tools\\rtl_core_mmu_tlb.py --check", text)
        self.assertIn("cpu_v01_core_mmu_tlb_tb", text)
        self.assertIn("SATP", text)
        self.assertIn("ASID", text)
        self.assertIn("RADIX4", text)
        self.assertIn("SFENCE.VM", text)
        self.assertIn("SFENCE.VM.VA_ASID", text)
        self.assertIn("PAGE_FAULT", text)
        self.assertIn("memory-type", text)
        self.assertIn("stale TLB", text)
        self.assertIn("I22-S07", text)

    def test_verilator_command_names_integrated_mmu_tlb_top(self) -> None:
        command = rtl_core_mmu_tlb.core_mmu_tlb_verilator_command()

        self.assertIn("--top-module cpu_v01_core_mmu_tlb_tb", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_core_mmu_tlb_tb.sv", command)


if __name__ == "__main__":
    unittest.main()

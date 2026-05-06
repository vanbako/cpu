"""I21-S02 conformance tests for MMU/TLB RTL coverage."""

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
TOOL = ROOT / "tools" / "rtl_mmu_tlb_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import csrs, mmu, opcodes, rtl_mmu_tlb, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_mmu_tlb_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlMmuTlbSliceTests(unittest.TestCase):
    def test_rtl_mmu_tlb_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_mmu_tlb.validate_rtl_mmu_tlb_slice(ROOT), ())
        for path in rtl_mmu_tlb.RTL_MMU_TLB_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_translation_fault_tlb_and_sfence_cases(self) -> None:
        rows = rtl_mmu_tlb.mmu_tlb_coverage_rows()
        by_case = {row.case_id: row for row in rows}

        bare = by_case["bare_mode.ld48_identity"]
        self.assertEqual(bare.satp_mode, "BARE")
        self.assertEqual(bare.physical_address, rtl_mmu_tlb.VIRTUAL_ADDRESS)
        self.assertEqual(bare.tlb_effect, "none")

        page_walk = by_case["radix4.ld48_page_walk_fill"]
        self.assertEqual(page_walk.satp_mode, "RADIX4")
        self.assertEqual(page_walk.physical_address, rtl_mmu_tlb.PHYSICAL_ADDRESS_A)
        self.assertEqual(page_walk.page_walk_levels, 4)
        self.assertEqual(page_walk.tlb_entries_after, 1)

        stale = by_case["tlb.stale_hit_before_va_asid_sfence"]
        self.assertEqual(stale.tlb_effect, "dtlb_hit_stale")
        self.assertEqual(stale.physical_address, rtl_mmu_tlb.PHYSICAL_ADDRESS_A)

        for case_id in (
            "radix4.load_after_sfence_page_fault",
            "radix4.permission_page_fault",
            "radix4.reserved_memory_type_page_fault",
        ):
            with self.subTest(case_id=case_id):
                fault = by_case[case_id]
                self.assertEqual(fault.fault_cause, "PAGE_FAULT")
                self.assertEqual(fault.fault_tval, rtl_mmu_tlb.VIRTUAL_ADDRESS)

    def test_projection_covers_all_sfence_forms_and_defers_later_memory_ordering(self) -> None:
        rows = rtl_mmu_tlb.mmu_tlb_coverage_rows()
        covered_mnemonics = {row.mnemonic for row in rows}

        for mnemonic in rtl_mmu_tlb.MMU_TLB_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, covered_mnemonics)
                forms = opcodes.opcode_forms_for(mnemonic)
                self.assertEqual(tuple(form.size.bits for form in forms), (24,))

        for mnemonic in rtl_mmu_tlb.DEFERRED_MNEMONICS:
            with self.subTest(deferred=mnemonic):
                self.assertNotIn(mnemonic, covered_mnemonics)

    def test_package_and_sv_contract_expose_mmu_tlb_retire_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_SFENCE_VM_24",
            "OPC_SFENCE_VM_ASID_24",
            "OPC_SFENCE_VM_VA_24",
            "OPC_SFENCE_VM_VA_ASID_24",
            "EXC_PAGE_FAULT",
            "EXC_PRIVILEGE_FAULT",
            "SATP_MODE_BARE",
            "SATP_MODE_RADIX4",
            "PTE_V_BIT",
            "PTE_MT_SHIFT",
            "MEMORY_TYPE_DEVICE_ORDERED",
            "MEMORY_TYPE_RESERVED",
            "TLB_INV_ALL",
            "TLB_INV_VA_ASID",
            "translation_valid",
            "physical_address",
            "translation_tlb_hit",
            "tlb_fill_valid",
            "tlb_invalidate_valid",
            "tlb_invalidate_kind",
        ):
            with self.subTest(token=token):
                self.assertIn(token, package)

        retire_fields = {
            field.name
            for struct in sv_contract.systemverilog_contract().structs
            if struct.name == "retire_packet_t"
            for field in struct.fields
        }
        self.assertGreaterEqual(
            retire_fields,
            {
                "translation_valid",
                "effective_address",
                "physical_address",
                "translation_memory_type",
                "translation_tlb_hit",
                "tlb_fill_valid",
                "tlb_fill_global",
                "tlb_fill_asid",
                "page_walk_level",
                "tlb_invalidate_valid",
                "tlb_invalidate_kind",
                "tlb_invalidate_va",
                "tlb_invalidate_asid",
            },
        )

    def test_mmu_tlb_core_names_states_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_mmu_tlb_core.sv").read_text(encoding="utf-8")

        for token in (
            "ST_BARE_LOAD",
            "ST_SATP_RADIX4",
            "ST_PAGE_WALK_L0",
            "ST_PAGE_WALK_L3",
            "ST_DTLB_STALE_HIT",
            "ST_SFENCE_VM_VA_ASID",
            "ST_LOAD_AFTER_SFENCE_FAULT",
            "ST_ASID_SCOPE",
            "ST_GLOBAL_SCOPE",
            "ST_SFENCE_VM",
            "ST_SFENCE_VM_ASID",
            "ST_SFENCE_VM_VA",
            "ST_PAGE_FAULT_PERMISSION",
            "ST_PAGE_FAULT_MEMTYPE",
            "retire_packet_q.translation_valid <= 1'b1",
            "retire_packet_q.tlb_fill_valid <= tlb_fill",
            "retire_packet_q.tlb_invalidate_kind <= kind",
            "start_fault_packet(OPC_LD48_24, VIRTUAL_ADDRESS, EXC_PAGE_FAULT)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_testbench_checks_i21_s02_coverage_groups(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_mmu_tlb_tb.sv").read_text(encoding="utf-8")

        self.assertIn("bare SATP identity translation result mismatch", tb)
        self.assertIn("RADIX4 page-walk translation result mismatch", tb)
        self.assertIn("stale TLB hit before SFENCE result mismatch", tb)
        self.assertIn("SFENCE.VM invalidation result mismatch", tb)
        self.assertIn("ASID/global TLB scope result mismatch", tb)
        self.assertIn("RADIX4 page fault result mismatch", tb)

    def test_fixture_constants_match_semantic_mmu_model(self) -> None:
        satp = csrs.pack_satp(
            csrs.SATP_MODE_RADIX4,
            rtl_mmu_tlb.FIXTURE_ASID,
            rtl_mmu_tlb.ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT,
        )

        self.assertEqual(csrs.satp_mode(satp), csrs.SATP_MODE_RADIX4)
        self.assertEqual(csrs.satp_asid(satp), rtl_mmu_tlb.FIXTURE_ASID)
        self.assertEqual(mmu.MEMORY_TYPE_RESERVED, 0b11)
        self.assertEqual(mmu.PTE_MT_SHIFT, 8)

    def test_cli_validates_and_renders_mmu_tlb_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL MMU/TLB slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        case_ids = {row["case_id"] for row in parsed}
        self.assertIn("radix4.ld48_page_walk_fill", case_ids)
        self.assertIn("sfence.vm_va_asid_invalidates_stale", case_ids)
        self.assertIn("radix4.reserved_memory_type_page_fault", case_ids)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-mmu-tlb-slice.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I21-S02", text)
        self.assertIn("rtl/cpu_v01_mmu_tlb_core.sv", text)
        self.assertIn("python tools\\rtl_mmu_tlb_slice.py --check", text)
        self.assertIn("RADIX4", text)
        self.assertIn("SFENCE.VM.VA_ASID", text)
        self.assertIn("PAGE_FAULT", text)
        self.assertIn("remain for later I21 stories", text)


if __name__ == "__main__":
    unittest.main()

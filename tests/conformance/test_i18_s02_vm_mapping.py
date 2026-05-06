"""I18-S02 conformance tests for VM allocation and page mapping fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import csrs, instructions, mmu, platform, user_process, vm
from cpu_v01.memory import TaggedMemory


class VmMappingFixtureTests(unittest.TestCase):
    def test_allocator_context_and_identity_mappings_install_radix4_user_space(self) -> None:
        allocator = vm.VmPageAllocator()
        tables = vm.allocate_fixture_tables(allocator)

        self.assertEqual(
            tables.pages,
            (vm.VM_ROOT_TABLE, vm.VM_L1_TABLE, vm.VM_L2_TABLE, vm.VM_L3_TABLE),
        )
        self.assertEqual(allocator.allocated_pages, tables.pages)

        fixture = vm.prepare_vm_fixture(tables=tables)
        core = fixture.core
        memory = fixture.memory

        self.assertEqual(csrs.satp_mode(core.read_csr(csrs.CSR_SATP)), csrs.SATP_MODE_RADIX4)
        self.assertEqual(core.read_csr(csrs.CSR_ASID), user_process.USER_ASID)
        self.assertEqual(
            csrs.satp_root_ppn(core.read_csr(csrs.CSR_SATP)),
            tables.root >> csrs.SATP_ROOT_PPN_SHIFT,
        )

        fetch = mmu.translate(
            core,
            memory,
            user_process.USER_ENTRY_CELL,
            mmu.AccessType.FETCH,
            instructions.InstructionLocation(core.pcc),
        )
        self.assertIsInstance(fetch, mmu.Translation)
        self.assertEqual(fetch.physical_address, user_process.USER_ENTRY_CELL)
        self.assertTrue(fetch.executable)
        self.assertTrue(fetch.user)

        load = mmu.translate(
            core,
            memory,
            vm.USER_VM_ADDRESS,
            mmu.AccessType.LOAD,
            instructions.InstructionLocation(core.pcc),
        )
        self.assertIsInstance(load, mmu.Translation)
        self.assertEqual(load.physical_address, vm.USER_VM_PHYSICAL_PAGE_A + vm.USER_VM_OFFSET)

    def test_map_unmap_uses_stale_tlb_until_va_asid_sfence_commits(self) -> None:
        report = vm.run_map_unmap_fixture()

        self.assertTrue(report.first_load.is_normal_retire)
        self.assertTrue(report.stale_load_after_unmap.is_normal_retire)
        self.assertTrue(report.sfence.is_normal_retire)
        self.assertTrue(report.load_after_sfence.is_fault)
        self.assertEqual(report.first_value, vm.USER_VM_VALUE)
        self.assertEqual(report.stale_value, vm.USER_VM_VALUE)
        self.assertEqual(report.leaf_pte_after_unmap, 0)
        self.assertEqual(report.tlb_entries_after_sfence, 0)
        self.assertEqual(
            report.load_after_sfence.fault_packet.cause,
            instructions.ExceptionCause.PAGE_FAULT,
        )
        self.assertEqual(report.load_after_sfence.fault_packet.tval, vm.USER_VM_ADDRESS)

    def test_read_only_permission_fixture_rejects_store_without_physical_write(self) -> None:
        report = vm.run_permission_fixture()

        self.assertTrue(report.load_result.is_normal_retire)
        self.assertTrue(report.store_result.is_fault)
        self.assertEqual(report.loaded_value, vm.USER_VM_VALUE)
        self.assertEqual(report.physical_value_after_store_attempt, vm.USER_VM_VALUE)
        self.assertEqual(
            report.store_result.fault_packet.cause,
            instructions.ExceptionCause.PAGE_FAULT,
        )
        self.assertEqual(report.store_result.fault_packet.tval, vm.USER_VM_ADDRESS)

    def test_device_memory_type_fixture_faults_cache_clean_with_physical_tval(self) -> None:
        report = vm.run_memory_type_fixture()

        self.assertEqual(report.mapped_memory_type, mmu.MEMORY_TYPE_DEVICE_ORDERED)
        self.assertTrue(report.cache_result.is_fault)
        self.assertEqual(
            report.cache_result.fault_packet.cause,
            instructions.ExceptionCause.ACCESS_FAULT,
        )
        device_mapping = vm.VmMapping(physical_page=platform.DEVICE_BASE)
        self.assertEqual(report.fault_tval, device_mapping.physical_address())

    def test_capability_fault_priority_precedes_unmapped_page_walk(self) -> None:
        report = vm.run_fault_priority_fixture()

        self.assertTrue(report.load_result.is_fault)
        self.assertEqual(
            report.load_result.fault_packet.cause,
            instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
        )
        self.assertEqual(report.load_result.fault_packet.capcause, instructions.CapCause.TAG)
        self.assertEqual(
            report.load_result.fault_packet.fault_cap_idx,
            instructions.FaultCapIndex.C1,
        )
        self.assertEqual(report.d0_after_fault, 0x1234)
        self.assertEqual(report.tlb_entries_after_fault, 0)

    def test_invalid_reserved_memory_type_rejects_mapping_without_pte_write(self) -> None:
        memory = TaggedMemory()
        mapping = vm.VmMapping(memory_type=mmu.MEMORY_TYPE_RESERVED)

        with self.assertRaises(vm.VmFixtureError) as raised:
            vm.install_page_mapping(memory, mapping)

        self.assertIn("memory_type must not be reserved", str(raised.exception))
        self.assertEqual(memory.ld48(vm.VM_ROOT_TABLE), 0)
        self.assertEqual(memory.ld48(vm.leaf_pte_address()), 0)

    def test_documentation_artifact_names_map_unmap_and_fault_priority_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "vm-page-mapping.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I18-S02", text)
        self.assertIn("SFENCE.VM.VA_ASID", text)
        self.assertIn("memory type", text)
        self.assertIn("fault priority", text)


if __name__ == "__main__":
    unittest.main()

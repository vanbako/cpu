"""I06-S01 conformance tests for RADIX4 translation and page permissions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, execution, instructions, memory_ops, mmu, reset
from cpu_v01.memory import TaggedMemory


ROOT_TABLE = 0x8000
L1_TABLE = 0x8800
L2_TABLE = 0x9000
L3_TABLE = 0x9800
PHYSICAL_PAGE = 0xA000
VIRTUAL_PAGE = 0x1234_5678_9000
VIRTUAL_ADDRESS = VIRTUAL_PAGE + 0x120
PHYSICAL_ADDRESS = PHYSICAL_PAGE + 0x120


def authority(
    *,
    cursor: int = VIRTUAL_ADDRESS,
    base: int = 0,
    top: int = 1 << 48,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability(payload, tag)


def install_radix4_root(core, root_base: int = ROOT_TABLE, asid: int = 0) -> None:
    core.write_csr_raw(
        csrs.CSR_SATP,
        csrs.pack_satp(csrs.SATP_MODE_RADIX4, asid, root_base >> csrs.SATP_ROOT_PPN_SHIFT),
    )


def install_mapping(
    memory: TaggedMemory,
    virtual_address: int = VIRTUAL_ADDRESS,
    physical_page: int = PHYSICAL_PAGE,
    *,
    root: int = ROOT_TABLE,
    leaf_read: bool = True,
    leaf_write: bool = True,
    leaf_execute: bool = False,
    leaf_user: bool = False,
    leaf_accessed: bool = True,
    leaf_memory_type: int = mmu.MEMORY_TYPE_NORMAL_COHERENT,
    leaf_global: bool = False,
    leaf_software: bool = True,
    leaf_reserved_zero: bool = False,
    nonleaf_reserved: bool = False,
) -> None:
    l0, l1, l2, l3 = mmu.vpn_indexes(virtual_address)
    nonleaf_user = nonleaf_reserved
    nonleaf_global = nonleaf_reserved
    nonleaf_accessed = nonleaf_reserved
    nonleaf_memory_type = 1 if nonleaf_reserved else 0
    memory.st48(
        root + (l0 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(
            L1_TABLE >> csrs.SATP_ROOT_PPN_SHIFT,
            user=nonleaf_user,
            global_mapping=nonleaf_global,
            accessed=nonleaf_accessed,
            memory_type=nonleaf_memory_type,
        ),
    )
    memory.st48(
        L1_TABLE + (l1 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L2_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        L2_TABLE + (l2 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L3_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        L3_TABLE + (l3 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(
            physical_page >> csrs.SATP_ROOT_PPN_SHIFT,
            read=leaf_read,
            write=leaf_write,
            execute=leaf_execute,
            user=leaf_user,
            accessed=leaf_accessed,
            memory_type=leaf_memory_type,
            global_mapping=leaf_global,
            software=leaf_software,
            reserved_zero=leaf_reserved_zero,
        ),
    )


def execute_and_commit(core, memory, decoded):
    result = memory_ops.execute_memory(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class Radix4TranslationTests(unittest.TestCase):
    def test_satp_and_asid_helpers_match_e09_s02(self) -> None:
        satp = csrs.pack_satp(csrs.SATP_MODE_RADIX4, 1, 0x12345)

        self.assertEqual(satp, 0x2020_0001_2345)
        self.assertEqual(csrs.satp_mode(satp), csrs.SATP_MODE_RADIX4)
        self.assertEqual(csrs.satp_asid(satp), 1)
        self.assertEqual(csrs.satp_root_ppn(satp), 0x12345)

        core = reset.cold_reset_core(0, 0x1000)
        core.write_csr_raw(csrs.CSR_SATP, satp)
        self.assertEqual(core.read_csr(csrs.CSR_ASID), 1)
        core.write_csr_raw(csrs.CSR_ASID, 7)
        self.assertEqual(core.read_csr(csrs.CSR_ASID), 7)
        self.assertEqual(csrs.satp_mode(core.read_csr(csrs.CSR_SATP)), csrs.SATP_MODE_RADIX4)
        self.assertEqual(csrs.satp_root_ppn(core.read_csr(csrs.CSR_SATP)), 0x12345)

        with self.assertRaises(ValueError):
            csrs.pack_satp(0b010, 0, 0)
        with self.assertRaises(ValueError):
            csrs.pack_satp(csrs.SATP_MODE_BARE, 0, 1)
        with self.assertRaises(ValueError):
            core.write_csr_raw(csrs.CSR_ASID, 0x100)

    def test_bare_mode_uses_effective_address_as_physical_even_with_asid(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        core.write_csr_raw(csrs.CSR_SATP, csrs.pack_satp(csrs.SATP_MODE_BARE, 9, 0))
        core.write_c(1, authority(cursor=0x1800, base=0x1000, top=0x2000, permissions=int(caps.CapabilityPermission.LD)))
        core.write_d(2, 0)
        memory.st48(0x1800, 0xAABBCCDDEEFF)

        result = execute_and_commit(
            core,
            memory,
            memory_ops.memory_instruction("LD48", (0, 1, 2)),
        )

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.read_d(0), 0xAABBCCDDEEFF)

    def test_radix4_ld48_and_st48_use_translated_physical_address(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory)
        memory.st48(PHYSICAL_ADDRESS, 0x1010_2020_3030)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST)))
        core.write_d(2, 0)
        core.write_d(3, 0x4040_5050_6060)

        load = execute_and_commit(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        store = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("ST48", (1, 2, 3)))

        self.assertTrue(load.is_normal_retire)
        self.assertEqual(core.read_d(0), 0x1010_2020_3030)
        self.assertTrue(store.is_normal_retire)
        self.assertEqual(memory.ld48(PHYSICAL_ADDRESS), 0x1010_2020_3030)
        execution.commit_normal_result(core, store, memory)
        self.assertEqual(memory.ld48(PHYSICAL_ADDRESS), 0x4040_5050_6060)
        self.assertEqual(memory.ld48(VIRTUAL_ADDRESS), 0)

    def test_radix4_clc_and_csc_translate_capability_slots(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        virtual_slot = VIRTUAL_PAGE + 0x140
        physical_slot = PHYSICAL_PAGE + 0x140
        install_radix4_root(core)
        install_mapping(memory, virtual_slot)
        stored = authority(cursor=0x1900, base=0x1000, top=0x2000)
        replacement = authority(cursor=0x1A00, base=0x1000, top=0x2000)
        memory.csc(physical_slot, stored)
        core.write_c(
            1,
            authority(
                cursor=virtual_slot,
                permissions=int(
                    caps.CapabilityPermission.LD
                    | caps.CapabilityPermission.LC
                    | caps.CapabilityPermission.ST
                    | caps.CapabilityPermission.SC
                ),
            ),
        )
        core.write_c(2, replacement)
        core.write_d(3, 0)

        load = execute_and_commit(core, memory, memory_ops.memory_instruction("CLC", (0, 1, 3)))
        store = execute_and_commit(core, memory, memory_ops.memory_instruction("CSC", (1, 3, 2)))

        self.assertTrue(load.is_normal_retire)
        self.assertEqual(core.read_c(0), stored)
        self.assertTrue(store.is_normal_retire)
        self.assertEqual(memory.clc(physical_slot), replacement)
        self.assertTrue(memory.clc(virtual_slot).is_invalid)

    def test_radix4_fetch_translation_requires_execute_page_permission(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory, leaf_read=True, leaf_write=False, leaf_execute=False)
        location = instructions.InstructionLocation(core.pcc)

        result = mmu.translate(
            core,
            memory,
            VIRTUAL_ADDRESS,
            mmu.AccessType.FETCH,
            location,
        )

        self.assertIsInstance(result, instructions.FaultPacket)
        self.assertEqual(result.cause, instructions.ExceptionCause.PAGE_FAULT)
        self.assertEqual(result.tval, VIRTUAL_ADDRESS)

        install_mapping(memory, leaf_read=True, leaf_write=False, leaf_execute=True)
        result = mmu.translate(
            core,
            memory,
            VIRTUAL_ADDRESS,
            mmu.AccessType.FETCH,
            location,
        )

        self.assertIsInstance(result, mmu.Translation)
        self.assertEqual(result.physical_address, PHYSICAL_ADDRESS)

    def test_page_faults_report_original_virtual_address_without_side_effects(self) -> None:
        cases = (
            {},
            {"leaf_read": False},
            {"leaf_accessed": False},
            {"leaf_memory_type": mmu.MEMORY_TYPE_RESERVED},
            {"leaf_reserved_zero": True},
            {"nonleaf_reserved": True},
        )
        for options in cases:
            with self.subTest(options=options):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                install_radix4_root(core)
                if options:
                    install_mapping(memory, **options)
                core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
                core.write_d(2, 0)
                original_d0 = core.read_d(0)

                result = memory_ops.execute_memory(
                    core,
                    memory,
                    memory_ops.memory_instruction("LD48", (0, 1, 2)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.PAGE_FAULT)
                self.assertEqual(result.fault_packet.capcause, instructions.CapCause.NONE)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.NONE)
                self.assertEqual(result.fault_packet.tval, VIRTUAL_ADDRESS)
                self.assertEqual(core.read_d(0), original_d0)

    def test_user_mode_cannot_access_kernel_only_leaf_but_kernel_can(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory, leaf_user=False)
        memory.st48(PHYSICAL_ADDRESS, 0xCAFE)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
        core.write_d(2, 0)
        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT),
        )

        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.PAGE_FAULT)

        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) | (1 << csrs.SR_PRIV_BIT),
        )
        result = execute_and_commit(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.read_d(0), 0xCAFE)

    def test_capability_fault_priority_precedes_radix4_page_fault(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        core.write_c(1, authority(tag=False, permissions=int(caps.CapabilityPermission.LD)))
        core.write_d(2, 0)

        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction("LD48", (0, 1, 2)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_TAG_FAULT)
        self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.C1)


if __name__ == "__main__":
    unittest.main()

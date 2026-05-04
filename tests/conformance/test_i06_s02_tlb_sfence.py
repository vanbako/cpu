"""I06-S02 conformance tests for TLBs and `SFENCE.VM` forms."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, execution, fence_ops, instructions, memory_ops, mmu, reset
from cpu_v01.memory import TaggedMemory
from cpu_v01.tlb import TlbKind


ROOT_TABLE = 0x8000
L1_TABLE = 0x8800
L2_TABLE = 0x9000
L3_TABLE = 0x9800
PHYSICAL_PAGE_1 = 0xA000
PHYSICAL_PAGE_2 = 0xB000
VIRTUAL_PAGE = 0x1234_5678_9000
VIRTUAL_ADDRESS = VIRTUAL_PAGE + 0x120
PHYSICAL_ADDRESS_1 = PHYSICAL_PAGE_1 + 0x120
PHYSICAL_ADDRESS_2 = PHYSICAL_PAGE_2 + 0x120


def authority(
    *,
    cursor: int = VIRTUAL_ADDRESS,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0, 1 << 48),
        permissions=permissions,
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability(payload, tag)


def install_radix4_root(core, *, asid: int = 0) -> None:
    core.write_csr_raw(
        csrs.CSR_SATP,
        csrs.pack_satp(csrs.SATP_MODE_RADIX4, asid, ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )


def install_mapping(
    memory: TaggedMemory,
    physical_page: int,
    *,
    virtual_address: int = VIRTUAL_ADDRESS,
    read: bool = True,
    write: bool = True,
    execute: bool = False,
    user: bool = False,
    global_mapping: bool = False,
) -> None:
    l0, l1, l2, l3 = mmu.vpn_indexes(virtual_address)
    memory.st48(
        ROOT_TABLE + (l0 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L1_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
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
            read=read,
            write=write,
            execute=execute,
            user=user,
            accessed=True,
            global_mapping=global_mapping,
        ),
    )


def execute_and_commit_memory(core, memory, decoded):
    result = memory_ops.execute_memory(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def execute_and_commit_fence(core, decoded):
    result = fence_ops.execute_fence(core, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


def load_virtual(core, memory):
    core.write_d(2, 0)
    return execute_and_commit_memory(
        core,
        memory,
        memory_ops.memory_instruction("LD48", (0, 1, 2)),
    )


class TlbAndSfenceTests(unittest.TestCase):
    def test_dtlb_hit_uses_cached_translation_until_va_asid_sfence_commits(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory, PHYSICAL_PAGE_1)
        memory.st48(PHYSICAL_ADDRESS_1, 0x1111)
        memory.st48(PHYSICAL_ADDRESS_2, 0x2222)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))

        first = load_virtual(core, memory)
        install_mapping(memory, PHYSICAL_PAGE_2)
        stale = load_virtual(core, memory)

        self.assertTrue(first.is_normal_retire)
        self.assertEqual(core.read_d(0), 0x1111)
        self.assertEqual(core.tlbs.entry_count(TlbKind.DATA), 1)
        self.assertTrue(stale.is_normal_retire)
        self.assertEqual(core.read_d(0), 0x1111)

        core.write_d(4, VIRTUAL_ADDRESS)
        core.write_d(5, 0)
        fence = fence_ops.execute_fence(
            core,
            fence_ops.fence_instruction("SFENCE.VM.VA_ASID", (4, 5)),
        )
        self.assertTrue(fence.is_normal_retire)
        self.assertEqual(core.tlbs.entry_count(TlbKind.DATA), 1)
        execution.commit_normal_result(core, fence)

        refreshed = load_virtual(core, memory)
        self.assertTrue(refreshed.is_normal_retire)
        self.assertEqual(core.read_d(0), 0x2222)

    def test_asid_matching_and_global_entry_invalidation_scope(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core, asid=1)
        install_mapping(memory, PHYSICAL_PAGE_1)
        memory.st48(PHYSICAL_ADDRESS_1, 0xAAAA)
        memory.st48(PHYSICAL_ADDRESS_2, 0xBBBB)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))

        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0xAAAA)
        core.write_csr_raw(csrs.CSR_ASID, 2)
        install_mapping(memory, PHYSICAL_PAGE_2)
        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0xBBBB)

        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core, asid=1)
        install_mapping(memory, PHYSICAL_PAGE_1, global_mapping=True)
        memory.st48(PHYSICAL_ADDRESS_1, 0x1111)
        memory.st48(PHYSICAL_ADDRESS_2, 0x2222)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0x1111)

        core.write_csr_raw(csrs.CSR_ASID, 2)
        install_mapping(memory, PHYSICAL_PAGE_2)
        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0x1111)

        core.write_d(6, 2)
        execute_and_commit_fence(
            core,
            fence_ops.fence_instruction("SFENCE.VM.ASID", (6,)),
        )
        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0x1111)

        core.write_d(7, VIRTUAL_ADDRESS)
        execute_and_commit_fence(
            core,
            fence_ops.fence_instruction("SFENCE.VM.VA", (7,)),
        )
        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0x2222)

    def test_tlb_hit_rechecks_current_privilege(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory, PHYSICAL_PAGE_1, user=False)
        memory.st48(PHYSICAL_ADDRESS_1, 0xCAFE)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))

        load_virtual(core, memory)
        self.assertEqual(core.read_d(0), 0xCAFE)
        self.assertEqual(core.tlbs.entry_count(TlbKind.DATA), 1)

        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT),
        )
        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction("LD48", (0, 1, 2)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.PAGE_FAULT)
        self.assertEqual(result.fault_packet.tval, VIRTUAL_ADDRESS)

    def test_fence_privilege_and_tlb_side_effects(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_root(core)
        install_mapping(memory, PHYSICAL_PAGE_1, read=True, execute=True)
        memory.st48(PHYSICAL_ADDRESS_1, 0x1234)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
        load_virtual(core, memory)
        fetch = mmu.translate(
            core,
            memory,
            VIRTUAL_ADDRESS,
            mmu.AccessType.FETCH,
            instructions.InstructionLocation(core.pcc),
        )
        self.assertIsInstance(fetch, mmu.Translation)
        self.assertEqual(core.tlbs.entry_count(TlbKind.DATA), 1)
        self.assertEqual(core.tlbs.entry_count(TlbKind.INSTRUCTION), 1)

        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT),
        )
        fence = execute_and_commit_fence(core, fence_ops.fence_instruction("FENCE"))
        fence_i = fence_ops.execute_fence(core, fence_ops.fence_instruction("FENCE.I"))
        sfence = fence_ops.execute_fence(core, fence_ops.fence_instruction("SFENCE.VM"))

        self.assertTrue(fence.is_normal_retire)
        self.assertTrue(fence_i.is_fault)
        self.assertEqual(fence_i.fault_packet.cause, instructions.ExceptionCause.PRIVILEGE_FAULT)
        self.assertTrue(sfence.is_fault)
        self.assertEqual(sfence.fault_packet.cause, instructions.ExceptionCause.PRIVILEGE_FAULT)
        self.assertEqual(core.tlbs.entry_count(), 2)

        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) | (1 << csrs.SR_PRIV_BIT),
        )
        fence_i = execute_and_commit_fence(core, fence_ops.fence_instruction("FENCE.I"))
        self.assertTrue(fence_i.is_normal_retire)
        self.assertEqual(core.tlbs.entry_count(), 2)

        sfence = execute_and_commit_fence(core, fence_ops.fence_instruction("SFENCE.VM"))
        self.assertTrue(sfence.is_normal_retire)
        self.assertEqual(core.tlbs.entry_count(), 0)

    def test_unknown_or_malformed_fence_reports_illegal_instruction(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)

        result = fence_ops.execute_fence(
            core,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_24),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = fence_ops.execute_fence(
            core,
            fence_ops.fence_instruction("SFENCE.VM", (0,)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

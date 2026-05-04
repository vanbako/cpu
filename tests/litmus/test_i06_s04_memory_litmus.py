"""I06-S04 executable litmus tests from `tools/memory_consistency_litmus.md`."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import atomic_ops, cache_ops, capabilities as caps, csrs, execution
from cpu_v01 import instructions, litmus, mmu, reset
from cpu_v01.memory import TaggedMemory


ROOT_TABLE = 0x8000
L1_TABLE = 0x8800
L2_TABLE = 0x9000
L3_TABLE = 0x9800
VIRTUAL_ADDRESS = 0x4000
PHYSICAL_PAGE = 0xA000
PHYSICAL_ADDRESS = PHYSICAL_PAGE


def capability(
    cursor: int = VIRTUAL_ADDRESS,
    *,
    base: int = 0,
    top: int = 1 << 48,
    permissions: int = int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
    tag: bool = True,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability(payload, tag)


def data_capability(cursor: int = 0x1234) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0, 1 << 48),
        permissions=int(caps.CapabilityPermission.LD),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def install_mapping(
    core,
    memory: TaggedMemory,
    *,
    memory_type: int = mmu.MEMORY_TYPE_NORMAL_COHERENT,
) -> None:
    core.write_csr_raw(
        csrs.CSR_SATP,
        csrs.pack_satp(csrs.SATP_MODE_RADIX4, 0, ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    l0, l1, l2, l3 = mmu.vpn_indexes(VIRTUAL_ADDRESS)
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
            PHYSICAL_PAGE >> csrs.SATP_ROOT_PPN_SHIFT,
            read=True,
            write=True,
            accessed=True,
            memory_type=memory_type,
        ),
    )


def execute_and_commit_atomic(core, memory, decoded):
    result = atomic_ops.execute_atomic(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def execute_and_commit_cache(core, memory, decoded):
    result = cache_ops.execute_cache(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class MemoryLitmusTests(unittest.TestCase):
    def test_mem_lit_040_store_buffering_allows_both_old_values(self) -> None:
        model = litmus.TsoMemoryModel(core_count=2)
        x = 0x1000
        y = 0x2000

        model.st48(0, x, 1)
        model.st48(1, y, 1)
        r0 = model.ld48(0, y)
        r1 = model.ld48(1, x)

        self.assertEqual((r0, r1), (0, 0))
        self.assertEqual(model.pending_count(0), 1)
        self.assertEqual(model.pending_count(1), 1)

    def test_mem_lit_041_and_042_fence_drains_store_buffer_in_fifo_order(self) -> None:
        model = litmus.TsoMemoryModel(core_count=2)
        x = 0x1000
        y = 0x2000

        model.st48(0, x, 1)
        model.fence(0)
        model.st48(1, y, 1)
        model.fence(1)

        self.assertEqual(model.ld48(0, y), 1)
        self.assertEqual(model.ld48(1, x), 1)

        model = litmus.TsoMemoryModel(core_count=2)
        a = 0x3000
        b = 0x4000
        model.st48(0, a, 1)
        model.st48(0, b, 1)
        model.drain_one(0)
        self.assertEqual(model.visible_value(b), 0)
        model.drain_one(0)

        self.assertEqual(model.visible_value(b), 1)
        self.assertEqual(model.visible_value(a), 1)

    def test_mem_lit_100_101_and_103_dma_sequences_require_clean_and_inval(self) -> None:
        model = litmus.CacheDmaModel(core_count=2)
        stored = data_capability(0x1234)
        replacement = data_capability(0x5678)
        replacement_cells = caps.payload_to_cells(replacement.payload)

        model.csc(0, 0x1000, stored)
        self.assertEqual(model.dma_read_cells(0x1000, 4), (0, 0, 0, 0))
        model.cache_clean(0x1000)
        self.assertEqual(model.dma_read_cells(0x1000, 4), caps.payload_to_cells(stored.payload))

        self.assertEqual(model.clc(1, 0x1000), stored)
        model.dma_write_cells(0x1000, replacement_cells)
        self.assertFalse(model.memory_capability_tag(0x1000))
        self.assertEqual(model.clc(1, 0x1000), stored)

        model.cache_inval(0x1000)
        observed = model.clc(1, 0x1000)
        self.assertEqual(observed.payload, replacement.payload)
        self.assertTrue(observed.is_invalid)

    def test_mem_lit_008_cache_clean_device_range_access_faults(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_mapping(core, memory, memory_type=mmu.MEMORY_TYPE_DEVICE_ORDERED)
        core.write_c(1, capability())
        core.write_d(2, 0)
        core.write_d(3, 16)

        result = cache_ops.execute_cache(
            core,
            memory,
            cache_ops.cache_instruction("CACHE.CLEAN", (1, 2, 3)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ACCESS_FAULT)
        self.assertEqual(result.fault_packet.tval, PHYSICAL_ADDRESS)

    def test_mem_lit_063_cache_inval_clears_matching_llsc_reservation(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_mapping(core, memory)
        memory.st48(PHYSICAL_ADDRESS, 0xAAAA)
        core.write_c(1, capability())
        core.write_d(2, 0)
        core.write_d(3, 16)
        core.write_d(4, 0xBBBB)

        ll = execute_and_commit_atomic(
            core,
            memory,
            atomic_ops.atomic_instruction("LL48", (0, 1, 2)),
        )
        self.assertTrue(ll.is_normal_retire)
        self.assertTrue(core.reservation.valid)

        inval = execute_and_commit_cache(
            core,
            memory,
            cache_ops.cache_instruction("CACHE.INVAL", (1, 2, 3)),
        )
        self.assertTrue(inval.is_normal_retire)
        self.assertFalse(core.reservation.valid)

        sc = execute_and_commit_atomic(
            core,
            memory,
            atomic_ops.atomic_instruction("SC48", (5, 4, 1, 2)),
        )
        self.assertTrue(sc.is_normal_retire)
        self.assertEqual(core.read_d(5), 1)
        self.assertEqual(memory.ld48(PHYSICAL_ADDRESS), 0xAAAA)


if __name__ == "__main__":
    unittest.main()

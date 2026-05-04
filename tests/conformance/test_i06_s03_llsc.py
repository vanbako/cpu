"""I06-S03 conformance tests for `LL48`/`SC48` reservations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import atomic_ops, capabilities as caps, csrs, execution
from cpu_v01 import fence_ops, instructions, memory_ops, mmu, reset, reservations, state, traps
from cpu_v01.memory import TaggedMemory


ROOT_TABLE = 0x8000
L1_TABLE = 0x8800
L2_TABLE = 0x9000
L3_TABLE = 0x9800
VIRTUAL_ADDRESS = 0x4000
PHYSICAL_PAGE = 0xA000
PHYSICAL_ADDRESS = PHYSICAL_PAGE


def authority(
    *,
    cursor: int = 0x1000,
    base: int = 0x1000,
    top: int = 0x2000,
    permissions: int = int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
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


def sample_capability(cursor: int = 0x1400) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x1000, 0x2000),
        permissions=int(caps.CapabilityPermission.LD),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def execute_and_commit_atomic(core, memory, decoded):
    result = atomic_ops.execute_atomic(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def execute_and_commit_memory(core, memory, decoded):
    result = memory_ops.execute_memory(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def install_radix4_mapping(
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


def install_tvc(core) -> None:
    core.write_ccsr(
        state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"],
        authority(cursor=0x8000, base=0x8000, top=0x9000, permissions=int(caps.CapabilityPermission.EX)),
    )


class LlScReservationTests(unittest.TestCase):
    def test_ll48_loads_and_sc48_success_stores_result_and_clears_tag(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        tagged = sample_capability()
        memory.csc(0x1000, tagged)
        core.write_c(1, authority())
        core.write_d(2, 0)
        core.write_d(3, 0x2222)

        ll = execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        sc = execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)))

        expected_cells = caps.payload_to_cells(tagged.payload)[:2]
        self.assertTrue(ll.is_normal_retire)
        self.assertEqual(core.read_d(0), expected_cells[0] | (expected_cells[1] << 24))
        self.assertTrue(sc.is_normal_retire)
        self.assertEqual(core.read_d(4), 0)
        self.assertEqual(memory.ld48(0x1000), 0x2222)
        self.assertFalse(memory.capability_tag(0x1000))
        self.assertFalse(core.reservation.valid)

    def test_sc48_failures_return_one_without_memory_or_tag_updates(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.csc(0x1000, sample_capability())
        original = memory.clc(0x1000)
        core.write_c(1, authority())
        core.write_d(2, 0)
        core.write_d(3, 0x3333)

        no_reservation = execute_and_commit_atomic(
            core,
            memory,
            atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)),
        )
        self.assertTrue(no_reservation.is_normal_retire)
        self.assertEqual(core.read_d(4), 1)
        self.assertEqual(memory.clc(0x1000), original)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        core.write_d(2, 2)
        different_word = execute_and_commit_atomic(
            core,
            memory,
            atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)),
        )
        self.assertEqual(core.read_d(4), 1)
        self.assertEqual(memory.clc(0x1000), original)
        self.assertFalse(core.reservation.valid)

        core.write_d(2, 0)
        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        spurious = execute_and_commit_atomic(
            core,
            memory,
            instructions.DecodedInstruction(
                "SC48",
                instructions.InstructionSize.BITS_24,
                operands=(4, 3, 1, 2),
                attributes={"force_spurious_failure": True},
            ),
        )
        self.assertTrue(spurious.is_normal_retire)
        self.assertEqual(core.read_d(4), 1)
        self.assertEqual(memory.clc(0x1000), original)
        self.assertFalse(core.reservation.valid)

    def test_faulting_ll48_and_sc48_clear_existing_reservation_without_side_effects(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.st48(0x1000, 0xAAAA)
        core.write_c(1, authority())
        core.write_d(2, 0)
        core.write_d(3, 1)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        result = atomic_ops.execute_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (5, 1, 3)))
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertFalse(core.reservation.valid)
        self.assertEqual(core.read_d(5), 0)

        core.write_d(3, 0xBBBB)
        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
        result = atomic_ops.execute_atomic(core, memory, atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)))
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT)
        self.assertFalse(core.reservation.valid)
        self.assertEqual(core.read_d(4), 0)
        self.assertEqual(memory.ld48(0x1000), 0xAAAA)

    def test_same_core_and_other_core_conflicting_stores_clear_reservations(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.st48(0x1000, 0x10)
        core.write_c(1, authority())
        core.write_d(2, 0)
        core.write_d(3, 0x20)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        execute_and_commit_memory(core, memory, memory_ops.memory_instruction("ST48", (1, 2, 3)))
        self.assertFalse(core.reservation.valid)

        core_a = reset.cold_reset_core(0, 0x1000)
        core_b = reset.cold_reset_core(1, 0x1000)
        core_a.write_c(1, authority())
        core_b.write_c(1, authority())
        core_a.write_d(2, 0)
        core_b.write_d(2, 0)
        core_a.write_d(3, 0x30)
        core_b.write_d(3, 0x40)
        execute_and_commit_atomic(core_a, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        execute_and_commit_memory(core_b, memory, memory_ops.memory_instruction("ST48", (1, 2, 3)))
        reservations.clear_conflicting_reservations((core_a,), 0x1000, 2)

        failed = execute_and_commit_atomic(core_a, memory, atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)))
        self.assertTrue(failed.is_normal_retire)
        self.assertEqual(core_a.read_d(4), 1)
        self.assertEqual(memory.ld48(0x1000), 0x40)

    def test_trap_csr_and_sfence_clear_active_reservation(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.st48(0x1000, 0x11)
        core.write_c(1, authority())
        core.write_d(2, 0)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        core.write_csr_raw(csrs.CSR_ASID, 1)
        self.assertFalse(core.reservation.valid)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        sfence = fence_ops.execute_fence(core, fence_ops.fence_instruction("SFENCE.VM"))
        execution.commit_normal_result(core, sfence)
        self.assertFalse(core.reservation.valid)

        execute_and_commit_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        install_tvc(core)
        packet = instructions.FaultPacket(
            instructions.ExceptionCause.BREAKPOINT,
            instructions.InstructionLocation(core.pcc),
        )
        trap_result = traps.enter_trap(core, packet)
        self.assertTrue(trap_result.entered)
        self.assertFalse(core.reservation.valid)

    def test_llsc_rejects_noncoherent_page_memory_type_with_access_fault(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_radix4_mapping(core, memory, memory_type=mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE)
        memory.st48(PHYSICAL_ADDRESS, 0x5555)
        core.write_c(
            1,
            authority(
                cursor=VIRTUAL_ADDRESS,
                base=0,
                top=1 << 48,
                permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
            ),
        )
        core.write_d(2, 0)
        core.write_d(3, 0x6666)

        ll = atomic_ops.execute_atomic(core, memory, atomic_ops.atomic_instruction("LL48", (0, 1, 2)))
        sc = atomic_ops.execute_atomic(core, memory, atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)))

        self.assertTrue(ll.is_fault)
        self.assertEqual(ll.fault_packet.cause, instructions.ExceptionCause.ACCESS_FAULT)
        self.assertEqual(ll.fault_packet.tval, PHYSICAL_ADDRESS)
        self.assertTrue(sc.is_fault)
        self.assertEqual(sc.fault_packet.cause, instructions.ExceptionCause.ACCESS_FAULT)
        self.assertEqual(memory.ld48(PHYSICAL_ADDRESS), 0x5555)


if __name__ == "__main__":
    unittest.main()

"""I03-S04 conformance tests for memory operation execution."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import execution, instructions, memory_ops, reset
from cpu_v01.memory import TaggedMemory


def authority(
    *,
    base: int = 0x1000,
    top: int = 0x2000,
    cursor: int = 0x1000,
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


def sample_capability(
    cursor: int = 0x1400,
    *,
    tag: bool = True,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x1000, 0x2000),
        permissions=int(caps.CapabilityPermission.LD),
        flags=flags,
    )
    return caps.Capability(payload, tag)


def execute_and_commit(core, memory, decoded):
    result = memory_ops.execute_memory(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class MemoryOperationExecutionTests(unittest.TestCase):
    def test_ld48_loads_two_cells_as_integer_without_creating_capability_tag(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        cap = sample_capability(tag=True)
        memory.csc(0x1000, cap)
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.LD)))
        core.write_d(2, 0)

        result = execute_and_commit(
            core,
            memory,
            memory_ops.memory_instruction("LD48", (0, 1, 2)),
        )

        expected_cells = caps.payload_to_cells(cap.payload)[:2]
        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.read_d(0), expected_cells[0] | (expected_cells[1] << 24))
        self.assertTrue(memory.capability_tag(0x1000))

    def test_st48_commits_at_retire_and_clears_overlapped_capability_tag(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.csc(0x1000, sample_capability(tag=True))
        core.write_c(1, authority(permissions=int(caps.CapabilityPermission.ST)))
        core.write_d(2, 0)
        core.write_d(3, 0x123456789ABC)

        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction("ST48", (1, 2, 3)),
        )

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(memory.ld48(0x1000), caps.payload_to_cells(sample_capability().payload)[0] | (caps.payload_to_cells(sample_capability().payload)[1] << 24))
        self.assertTrue(memory.capability_tag(0x1000))

        execution.commit_normal_result(core, result, memory)

        self.assertEqual(memory.ld48(0x1000), 0x123456789ABC)
        self.assertFalse(memory.capability_tag(0x1000))

    def test_clc_loads_payload_and_tag_and_untagged_slot_is_not_a_fault(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        valid = sample_capability(cursor=0x1500, tag=True)
        invalid = sample_capability(cursor=0x1600, tag=False)
        memory.csc(0x1000, valid)
        memory.csc(0x1004, invalid)
        core.write_c(
            1,
            authority(
                permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.LC)
            ),
        )

        core.write_d(2, 0)
        execute_and_commit(core, memory, memory_ops.memory_instruction("CLC", (0, 1, 2)))
        self.assertEqual(core.read_c(0), valid)

        core.write_d(2, 4)
        execute_and_commit(core, memory, memory_ops.memory_instruction("CLC", (0, 1, 2)))
        self.assertEqual(core.read_c(0), invalid)
        self.assertTrue(core.read_c(0).is_invalid)

    def test_csc_stores_payload_and_tag_atomically_at_retire(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        stored = sample_capability(cursor=0x1700, tag=True)
        core.write_c(
            1,
            authority(
                permissions=int(
                    caps.CapabilityPermission.ST | caps.CapabilityPermission.SC
                )
            ),
        )
        core.write_c(2, stored)
        core.write_d(3, 0)

        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction("CSC", (1, 3, 2)),
        )

        self.assertTrue(result.is_normal_retire)
        self.assertFalse(memory.capability_tag(0x1000))
        execution.commit_normal_result(core, result, memory)
        self.assertEqual(memory.clc(0x1000), stored)

    def test_effective_address_uses_signed_48_bit_offset(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.st48(0x1000, 0xA)
        memory.st48(0x1002, 0xB)
        core.write_c(1, authority(cursor=0x1002, permissions=int(caps.CapabilityPermission.LD)))
        core.write_d(2, (1 << 48) - 2)

        execute_and_commit(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))

        self.assertEqual(core.read_d(0), 0xA)

    def test_access_fault_priority_tag_seal_representability_alignment_bounds_permission(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        original_d0 = core.read_d(0)

        core.write_c(1, authority(tag=False, permissions=0))
        core.write_d(2, 1)
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_TAG_FAULT)

        core.write_c(1, authority(otype=0x22, permissions=0))
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT)

        core.write_c(1, authority(cursor=0, permissions=0))
        core.write_d(2, (1 << 48) - 1)
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT)
        self.assertEqual(result.fault_packet.tval, 0)

        core.write_c(1, authority(permissions=0))
        core.write_d(2, 1)
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(result.fault_packet.tval, 0x1001)

        core.write_d(2, 0x1000)
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT)
        self.assertEqual(result.fault_packet.tval, 0x2000)

        core.write_d(2, 0)
        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("LD48", (0, 1, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT)
        self.assertEqual(core.read_d(0), original_d0)

    def test_misaligned_clc_and_csc_fault_before_memory_or_register_side_effects(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        original = sample_capability(cursor=0x1800)
        stored = sample_capability(cursor=0x1900)
        memory.csc(0x1000, original)
        core.write_c(0, original)
        core.write_c(1, authority())
        core.write_c(2, stored)
        core.write_d(3, 2)

        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("CLC", (0, 1, 3)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(core.read_c(0), original)

        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("CSC", (1, 3, 2)))
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(memory.clc(0x1000), original)

    def test_csc_storing_valid_local_capability_requires_sl(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        local = sample_capability(flags=0)
        core.write_c(
            1,
            authority(
                permissions=int(
                    caps.CapabilityPermission.ST | caps.CapabilityPermission.SC
                )
            ),
        )
        core.write_c(2, local)
        core.write_d(3, 0)

        result = memory_ops.execute_memory(core, memory, memory_ops.memory_instruction("CSC", (1, 3, 2)))

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_LOCAL_STORE_FAULT)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.LOCAL_STORE)
        self.assertFalse(memory.capability_tag(0x1000))

        core.write_c(
            1,
            authority(
                permissions=int(
                    caps.CapabilityPermission.ST
                    | caps.CapabilityPermission.SC
                    | caps.CapabilityPermission.SL
                )
            ),
        )
        execute_and_commit(core, memory, memory_ops.memory_instruction("CSC", (1, 3, 2)))
        self.assertEqual(memory.clc(0x1000), local)

    def test_protected_return_stack_storage_blocks_ordinary_accesses(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        protected = sample_capability(cursor=0x1500)
        memory.csc(0x1000, protected)
        memory.protect_range(0x1000, 4)
        core.write_c(1, authority())
        core.write_c(2, sample_capability(cursor=0x1600))
        core.write_d(3, 0)
        core.write_d(4, 0x1234)

        cases = [
            memory_ops.memory_instruction("LD48", (0, 1, 3)),
            memory_ops.memory_instruction("ST48", (1, 3, 4)),
            memory_ops.memory_instruction("CLC", (0, 1, 3)),
            memory_ops.memory_instruction("CSC", (1, 3, 2)),
        ]
        for decoded in cases:
            with self.subTest(decoded=decoded.mnemonic):
                result = memory_ops.execute_memory(core, memory, decoded)
                self.assertTrue(result.is_fault)
                self.assertEqual(
                    result.fault_packet.cause,
                    instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
                )
                self.assertEqual(memory.clc(0x1000), protected)

    def test_unknown_or_malformed_memory_instruction_reports_illegal_instruction(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()

        result = memory_ops.execute_memory(
            core,
            memory,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_24),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction("LD48", (0, 1)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

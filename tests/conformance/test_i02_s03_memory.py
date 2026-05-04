"""I02-S03 conformance tests for memory cells and capability tags."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01.memory import MemoryAlignmentError, TaggedMemory


class TaggedMemoryTests(unittest.TestCase):
    def sample_capability(self, cursor: int = 0x1000, tag: bool = True) -> caps.Capability:
        payload = caps.CapabilityPayload(
            cursor=cursor,
            bounds_metadata=0x1234567,
            permissions=(
                caps.CapabilityPermission.LD
                | caps.CapabilityPermission.ST
                | caps.CapabilityPermission.LC
                | caps.CapabilityPermission.SC
            ),
            otype=caps.OTYPE_UNSEALED,
            flags=caps.CapabilityFlag.G,
        )
        return caps.Capability(payload=payload, tag=tag)

    def test_ld48_and_st48_move_two_24_bit_cells(self) -> None:
        memory = TaggedMemory()
        memory.st48(0x1000, 0x123456789ABC)

        self.assertEqual(memory.read_cell(0x1000), 0x789ABC)
        self.assertEqual(memory.read_cell(0x1001), 0x123456)
        self.assertEqual(memory.ld48(0x1000), 0x123456789ABC)

        with self.assertRaises(MemoryAlignmentError):
            memory.ld48(0x1001)
        with self.assertRaises(MemoryAlignmentError):
            memory.st48(0x1001, 0)

    def test_csc_and_clc_move_payload_and_tag_atomically(self) -> None:
        memory = TaggedMemory()
        cap = self.sample_capability()

        memory.csc(0x1000, cap)
        loaded = memory.clc(0x1000)

        self.assertEqual(loaded, cap)
        self.assertTrue(memory.capability_tag(0x1000))
        self.assertEqual(
            tuple(memory.read_cell(0x1000 + offset) for offset in range(4)),
            caps.payload_to_cells(cap.payload),
        )

    def test_clc_from_untagged_slot_loads_invalid_capability(self) -> None:
        memory = TaggedMemory()
        cap = self.sample_capability(tag=False)

        memory.csc(0x1000, cap)
        loaded = memory.clc(0x1000)

        self.assertEqual(loaded.payload, cap.payload)
        self.assertFalse(loaded.tag)
        self.assertFalse(memory.capability_tag(0x1000))

    def test_st48_clears_first_or_second_half_capability_slot_tag(self) -> None:
        memory = TaggedMemory()
        slot0 = self.sample_capability(cursor=0x1000)
        slot1 = self.sample_capability(cursor=0x2000)

        memory.csc(0x1000, slot0)
        memory.csc(0x1004, slot1)
        memory.st48(0x1000, 0xAAAAAA555555)
        self.assertFalse(memory.capability_tag(0x1000))
        self.assertTrue(memory.capability_tag(0x1004))

        memory.csc(0x1000, slot0)
        memory.st48(0x1002, 0xBBBBBB666666)
        self.assertFalse(memory.capability_tag(0x1000))
        self.assertTrue(memory.capability_tag(0x1004))

    def test_ld48_reads_capability_payload_bits_without_tag(self) -> None:
        memory = TaggedMemory()
        cap = self.sample_capability()
        memory.csc(0x1000, cap)

        first_two_cells = caps.payload_to_cells(cap.payload)[:2]
        expected_integer = first_two_cells[0] | (first_two_cells[1] << 24)

        self.assertEqual(memory.ld48(0x1000), expected_integer)
        self.assertTrue(memory.capability_tag(0x1000))

    def test_misaligned_clc_and_csc_have_no_side_effects(self) -> None:
        memory = TaggedMemory()
        cap = self.sample_capability()

        with self.assertRaises(MemoryAlignmentError):
            memory.csc(0x1002, cap)
        self.assertFalse(memory.capability_tag(0x1000))

        memory.csc(0x1000, cap)
        before = memory.clc(0x1000)
        with self.assertRaises(MemoryAlignmentError):
            memory.clc(0x1002)
        self.assertEqual(memory.clc(0x1000), before)

    def test_ordinary_cell_writes_clear_all_overlapped_tags(self) -> None:
        memory = TaggedMemory()
        memory.csc(0x1000, self.sample_capability(cursor=0x1000))
        memory.csc(0x1004, self.sample_capability(cursor=0x2000))

        memory.write_cells(0x1003, [0x1, 0x2])

        self.assertFalse(memory.capability_tag(0x1000))
        self.assertFalse(memory.capability_tag(0x1004))


if __name__ == "__main__":
    unittest.main()

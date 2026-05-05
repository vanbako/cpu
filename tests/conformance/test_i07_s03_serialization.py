"""I07-S03 conformance tests for the 24-bit cell serialization profile."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly
from cpu_v01 import cells
from cpu_v01 import serialization


class CellSerializationProfileTests(unittest.TestCase):
    def test_single_cells_use_little_endian_three_octet_payloads(self) -> None:
        self.assertEqual(serialization.CELL_BYTE_ORDER, "little")
        self.assertEqual(serialization.serialize_cell(0x123456), bytes((0x56, 0x34, 0x12)))
        self.assertEqual(serialization.deserialize_cell(bytes((0x56, 0x34, 0x12))), 0x123456)

        with self.assertRaises(ValueError):
            serialization.serialize_cell(0x1000000)
        with self.assertRaises(serialization.SerializationError):
            serialization.deserialize_cell(b"\x00\x00")

    def test_cell_sequences_round_trip_and_reject_partial_cells(self) -> None:
        values = (0x000000, 0xABCDEF, 0xFFFFFF)
        payload = serialization.serialize_cells(values)

        self.assertEqual(payload, bytes((0x00, 0x00, 0x00, 0xEF, 0xCD, 0xAB, 0xFF, 0xFF, 0xFF)))
        self.assertEqual(serialization.deserialize_cells(payload), values)

        with self.assertRaises(serialization.SerializationError):
            serialization.deserialize_cells(payload + b"\x00")

    def test_page_and_cache_line_payloads_use_architectural_cell_counts(self) -> None:
        base_page = tuple(0 for _ in range(cells.BASE_PAGE_CELLS))
        cache_line = tuple(range(cells.CACHE_LINE_CELLS))

        self.assertEqual(serialization.serialized_size_cells(cells.BASE_PAGE_CELLS), 6144)
        self.assertEqual(len(serialization.serialize_base_page(base_page)), 6144)
        self.assertEqual(serialization.deserialize_base_page(b"\x00" * 6144), base_page)
        self.assertEqual(serialization.serialized_size_cells(cells.CACHE_LINE_CELLS), 48)
        self.assertEqual(len(serialization.serialize_cache_line(cache_line)), 48)
        self.assertEqual(serialization.deserialize_cache_line(serialization.serialize_cache_line(cache_line)), cache_line)

        with self.assertRaises(serialization.SerializationError):
            serialization.serialize_base_page(base_page[:-1])
        with self.assertRaises(serialization.SerializationError):
            serialization.deserialize_cache_line(b"\x00" * 47)

    def test_container_offsets_are_external_cell_boundaries(self) -> None:
        self.assertEqual(serialization.cell_address_to_container_offset(0x1000), 0x3000)
        self.assertEqual(serialization.container_offset_to_cell_address(0x3000), 0x1000)

        with self.assertRaises(serialization.SerializationError):
            serialization.container_offset_to_cell_address(0x3001)
        with self.assertRaises(ValueError):
            serialization.container_offset_to_cell_address(-3)

    def test_sections_are_cell_addressed_and_payloads_are_serialized_cells(self) -> None:
        section = serialization.CellSection(
            name="text",
            base_cell=0x1000,
            alignment_cells=2,
            payload_cells=(0x05B053, 0x12123A),
        )

        self.assertEqual(section.size_cells, 2)
        self.assertEqual(section.size_octets, 6)
        self.assertEqual(section.payload_octets, bytes((0x53, 0xB0, 0x05, 0x3A, 0x12, 0x12)))
        self.assertTrue(section.contains_cell(0x1000))
        self.assertTrue(section.contains_cell(0x1001))
        self.assertFalse(section.contains_cell(0x1002))
        self.assertEqual(serialization.validate_section(section), ())

        with self.assertRaises(serialization.SerializationError):
            serialization.CellSection("data", base_cell=0x1001, alignment_cells=2, payload_cells=())
        with self.assertRaises(ValueError):
            serialization.CellSection("data", base_cell=0x1000, alignment_cells=2, payload_cells=(0x1000000,))

    def test_assembler_fixtures_can_be_written_as_cell_payloads(self) -> None:
        program = assembly.assemble_program(("RET", "PAUSE"))
        payload = serialization.serialize_cells(program)

        self.assertEqual(program, (0x05B053,))
        self.assertEqual(payload, bytes((0x53, 0xB0, 0x05)))
        self.assertEqual(serialization.deserialize_cells(payload), program)


if __name__ == "__main__":
    unittest.main()

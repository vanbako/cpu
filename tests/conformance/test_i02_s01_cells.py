"""I02-S01 conformance tests for E01-S01 cell-address helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import cells


class CellAddressModelTests(unittest.TestCase):
    def test_core_constants_match_e01_s01(self) -> None:
        self.assertEqual(cells.CELL_BITS, 24)
        self.assertEqual(cells.CELL_BYTES, 3)
        self.assertEqual(cells.ADDRESS_BITS, 48)
        self.assertEqual(cells.ADDRESS_SPACE_CELLS, 1 << 48)
        self.assertEqual(cells.INTEGER_OBJECT_CELLS, 2)
        self.assertEqual(cells.CAPABILITY_OBJECT_CELLS, 4)
        self.assertEqual(cells.FETCH_GROUP_CELLS, 2)
        self.assertEqual(cells.BASE_PAGE_CELLS, 1 << 11)
        self.assertEqual(cells.CACHE_LINE_CELLS, 16)

    def test_cell_value_masking_and_validation(self) -> None:
        self.assertEqual(cells.mask_cell(0x1234567), 0x234567)
        self.assertEqual(cells.mask_cell(-1), 0xFFFFFF)
        self.assertTrue(cells.is_cell_value(0))
        self.assertTrue(cells.is_cell_value(0xFFFFFF))
        self.assertFalse(cells.is_cell_value(0x1000000))
        self.assertFalse(cells.is_cell_value(True))
        self.assertEqual(cells.require_cell_value(0xFFFFFF), 0xFFFFFF)
        with self.assertRaises(ValueError):
            cells.require_cell_value(0x1000000)
        with self.assertRaises(TypeError):
            cells.mask_cell(True)

    def test_cell_address_bounds(self) -> None:
        self.assertTrue(cells.is_cell_address(0))
        self.assertTrue(cells.is_cell_address((1 << 48) - 1))
        self.assertFalse(cells.is_cell_address(1 << 48))
        self.assertFalse(cells.is_cell_address(-1))
        self.assertFalse(cells.is_cell_address(False))
        self.assertEqual(cells.require_cell_address((1 << 48) - 1), (1 << 48) - 1)
        with self.assertRaises(ValueError):
            cells.require_cell_address(1 << 48)

    def test_alignment_examples_from_e01_s01(self) -> None:
        self.assertTrue(cells.is_aligned(0x1000, 2))
        self.assertTrue(cells.is_aligned(0x1000, 4))
        self.assertTrue(cells.is_aligned(0x1000, 16))
        self.assertFalse(cells.is_aligned(0x1001, 2))
        self.assertFalse(cells.is_aligned(0x1001, 4))
        self.assertFalse(cells.is_aligned(0x1001, 16))
        self.assertTrue(cells.is_aligned(0x1002, 2))
        self.assertFalse(cells.is_aligned(0x1002, 4))
        self.assertTrue(cells.is_aligned(0x1004, 4))
        self.assertTrue(cells.is_aligned(0x1010, 16))

    def test_half_open_ranges_use_cell_counts(self) -> None:
        page = cells.cell_range(0x1000, 0x800)
        self.assertEqual(page.base, 0x1000)
        self.assertEqual(page.top, 0x1800)
        self.assertEqual(page.length, 0x800)
        self.assertTrue(page.contains_address(0x1000))
        self.assertTrue(page.contains_address(0x17FF))
        self.assertFalse(page.contains_address(0x1800))
        self.assertTrue(page.contains_range(cells.cell_range(0x1100, 0x10)))
        self.assertFalse(page.contains_range(cells.cell_range(0x17F0, 0x20)))

    def test_object_ranges_reject_address_space_overflow(self) -> None:
        last_integer = cells.integer_object_range((1 << 48) - 2)
        self.assertEqual(last_integer.top, 1 << 48)
        with self.assertRaises(ValueError):
            cells.integer_object_range((1 << 48) - 1)
        with self.assertRaises(ValueError):
            cells.object_range(0, 0)

    def test_fetch_group_and_cache_line_bases_are_cell_based(self) -> None:
        self.assertEqual(cells.fetch_group_base(0x1001), 0x1000)
        self.assertEqual(cells.fetch_group_range(0x1001), cells.CellRange(0x1000, 0x1002))
        self.assertEqual(cells.cache_line_base(0x101F), 0x1010)
        self.assertEqual(cells.cache_line_range(0x101F), cells.CellRange(0x1010, 0x1020))

    def test_base_page_range_requires_page_alignment(self) -> None:
        self.assertEqual(cells.base_page_range(0x1800), cells.CellRange(0x1800, 0x2000))
        with self.assertRaises(ValueError):
            cells.base_page_range(0x1801)


if __name__ == "__main__":
    unittest.main()

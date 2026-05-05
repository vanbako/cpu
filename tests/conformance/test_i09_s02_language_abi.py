"""I09-S02 conformance tests for the language ABI supplement."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import abi, cells


class LanguageAbiSupplementTests(unittest.TestCase):
    def test_profile_constants_match_public_call_boundary_contract(self) -> None:
        self.assertEqual(abi.validate_language_abi_profile(), ())
        self.assertEqual(abi.INTEGER_ABI_SLOT_CELLS, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(abi.CAPABILITY_ABI_SLOT_CELLS, cells.CAPABILITY_OBJECT_CELLS)
        self.assertEqual(abi.PUBLIC_STACK_ALIGNMENT_CELLS, cells.CAPABILITY_OBJECT_CELLS)
        self.assertEqual((abi.INTEGER_SPILL_STORE, abi.INTEGER_SPILL_LOAD), ("ST48", "LD48"))
        self.assertEqual((abi.CAPABILITY_SPILL_STORE, abi.CAPABILITY_SPILL_LOAD), ("CSC", "CLC"))

    def test_first_six_integer_arguments_use_d0_through_d5(self) -> None:
        layout = abi.layout_language_arguments([abi.AbiValueKind.INTEGER] * 6)

        self.assertEqual(layout.overflow_size_cells, 0)
        for index, location in enumerate(layout.locations):
            self.assertIs(location.value_kind, abi.AbiValueKind.INTEGER)
            self.assertIs(location.location_kind, abi.AbiLocationKind.INTEGER_REGISTER)
            self.assertEqual(location.register_index, index)
            self.assertFalse(location.tag_required)

    def test_seventh_integer_argument_uses_first_two_cell_overflow_slot(self) -> None:
        layout = abi.layout_language_arguments([abi.AbiValueKind.INTEGER] * 7)
        seventh = layout.location_for_argument(6)

        self.assertTrue(seventh.is_stack)
        self.assertEqual(seventh.offset_cells, 0)
        self.assertEqual(seventh.size_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(seventh.alignment_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(layout.overflow_size_cells, cells.CAPABILITY_OBJECT_CELLS)

    def test_first_four_capability_arguments_use_c0_through_c3(self) -> None:
        layout = abi.layout_language_arguments([abi.AbiValueKind.CAPABILITY] * 4)

        self.assertEqual(layout.overflow_size_cells, 0)
        for index, location in enumerate(layout.locations):
            self.assertIs(location.value_kind, abi.AbiValueKind.CAPABILITY)
            self.assertIs(location.location_kind, abi.AbiLocationKind.CAPABILITY_REGISTER)
            self.assertEqual(location.register_index, index)
            self.assertTrue(location.tag_required)

    def test_fifth_capability_argument_uses_tagged_four_cell_overflow_slot(self) -> None:
        layout = abi.layout_language_arguments([abi.AbiValueKind.CAPABILITY] * 5)
        fifth = layout.location_for_argument(4)

        self.assertTrue(fifth.is_stack)
        self.assertEqual(fifth.offset_cells, 0)
        self.assertEqual(fifth.size_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertEqual(fifth.alignment_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertTrue(fifth.tag_required)
        self.assertEqual(layout.overflow_size_cells, cells.CAPABILITY_OBJECT_CELLS)

    def test_mixed_overflow_arguments_are_laid_out_in_source_order_with_alignment(self) -> None:
        arguments = (
            [abi.AbiValueKind.INTEGER] * 6
            + [abi.AbiValueKind.CAPABILITY] * 4
            + [abi.AbiValueKind.INTEGER, abi.AbiValueKind.CAPABILITY, abi.AbiValueKind.INTEGER]
        )
        layout = abi.layout_language_arguments(arguments)

        first_overflow_integer = layout.location_for_argument(10)
        overflow_capability = layout.location_for_argument(11)
        second_overflow_integer = layout.location_for_argument(12)
        self.assertEqual(first_overflow_integer.offset_cells, 0)
        self.assertEqual(first_overflow_integer.size_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(overflow_capability.offset_cells, 4)
        self.assertEqual(overflow_capability.size_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertTrue(overflow_capability.tag_required)
        self.assertEqual(second_overflow_integer.offset_cells, 8)
        self.assertEqual(layout.overflow_size_cells, 12)

    def test_bad_argument_kind_and_unknown_argument_index_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            abi.layout_language_arguments(["FLOAT"])

        layout = abi.layout_language_arguments([abi.AbiValueKind.INTEGER])
        with self.assertRaises(KeyError):
            layout.location_for_argument(1)


if __name__ == "__main__":
    unittest.main()

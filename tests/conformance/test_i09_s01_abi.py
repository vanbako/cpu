"""I09-S01 conformance tests for trap-frame and context-switch ABI supplements."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import abi, cells, state


class TrapFrameAndContextAbiTests(unittest.TestCase):
    def test_calling_convention_save_sets_match_e05_contracts(self) -> None:
        self.assertEqual(abi.INTEGER_ARGUMENT_REGS, (0, 1, 2, 3, 4, 5))
        self.assertEqual(abi.INTEGER_RETURN_REGS, (0, 1))
        self.assertEqual(abi.INTEGER_CALLER_SAVED_REGS, tuple(range(12)))
        self.assertEqual(abi.INTEGER_CALLEE_SAVED_REGS, (12, 13, 14, 15))

        self.assertEqual(abi.CAPABILITY_ARGUMENT_REGS, (0, 1, 2, 3))
        self.assertEqual(abi.CAPABILITY_RETURN_REGS, (0,))
        self.assertEqual(abi.CAPABILITY_CALLER_SAVED_REGS, tuple(range(6)))
        self.assertEqual(abi.CAPABILITY_CALLEE_SAVED_REGS, (6, 7))

    def test_minimum_nested_trap_frame_preserves_epcc_slot_and_reporting_state(self) -> None:
        self.assertEqual(abi.validate_trap_frame_layout(), ())
        self.assertEqual(abi.TRAP_FRAME_SIZE_CELLS, 16)
        self.assertEqual(abi.TRAP_FRAME_ALIGNMENT_CELLS, cells.CAPABILITY_OBJECT_CELLS)

        epcc = abi.trap_frame_field("epcc")
        epcc_slot = abi.trap_frame_field("EPCC_SLOT")
        self.assertEqual(epcc.offset_cells, 0)
        self.assertEqual(epcc.size_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertEqual(epcc_slot.offset_cells, 4)
        self.assertEqual(epcc_slot.size_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertIs(epcc.kind, abi.AbiFieldKind.CAPABILITY)
        self.assertIs(epcc_slot.kind, abi.AbiFieldKind.CONTROL)

        for name in ("SR", "CAUSE", "TVAL", "CAPCAUSE", "FAULTCAPIDX"):
            self.assertEqual(abi.trap_frame_field(name).size_cells, cells.INTEGER_OBJECT_CELLS)

    def test_trap_frame_layout_has_no_overlap_and_preserves_stack_alignment(self) -> None:
        occupied: set[int] = set()
        for field in abi.TRAP_FRAME_FIELDS:
            self.assertEqual(field.offset_cells % field.alignment_cells, 0)
            field_cells = set(range(field.offset_cells, field.end_cells))
            self.assertFalse(occupied & field_cells)
            occupied |= field_cells
        self.assertEqual(max(occupied) + 1, abi.TRAP_FRAME_SIZE_CELLS)
        self.assertEqual(abi.TRAP_FRAME_SIZE_CELLS % cells.CAPABILITY_OBJECT_CELLS, 0)

    def test_context_switch_save_sets_cover_all_architectural_register_files(self) -> None:
        self.assertEqual(abi.validate_context_switch_save_sets(), ())
        self.assertEqual(abi.CONTEXT_SWITCH_INTEGER_REGS, tuple(range(state.INTEGER_REGISTER_COUNT)))
        self.assertEqual(
            abi.CONTEXT_SWITCH_CAPABILITY_REGS,
            tuple(range(state.GENERAL_CAPABILITY_REGISTER_COUNT)),
        )
        self.assertEqual(abi.CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS, state.SPECIAL_CAPABILITY_NAMES)
        self.assertIn("EPCC", abi.CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS)
        self.assertIn("PCC", abi.CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS)

    def test_nested_return_sequence_requires_epccwr_before_iret(self) -> None:
        sequence = abi.NESTED_TRAP_RESTORE_SEQUENCE
        self.assertIn("EPCCWR Cs, Ds", sequence)
        self.assertNotIn("CCSRWR EPCC, Cs", sequence)
        self.assertLess(sequence.index("EPCCWR Cs, Ds"), sequence.index("IRET"))
        self.assertEqual(sequence[-1], "IRET")
        self.assertIn("slot1_iret_restore", abi.TRAP_RETURN_TEST_SCENARIOS)
        self.assertIn("nested_frame_restores_epcc_slot", abi.TRAP_RETURN_TEST_SCENARIOS)

    def test_unknown_trap_frame_field_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            abi.trap_frame_field("NOPE")


if __name__ == "__main__":
    unittest.main()

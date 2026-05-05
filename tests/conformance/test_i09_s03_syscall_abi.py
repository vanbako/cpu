"""I09-S03 conformance tests for the baseline syscall ABI supplement."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import abi, assembly, cells


class SyscallAbiSupplementTests(unittest.TestCase):
    def test_syscall_profile_identifies_source_spellings_and_trap_cause(self) -> None:
        self.assertEqual(abi.validate_syscall_abi_profile(), ())
        self.assertEqual(abi.SYSCALL_CANONICAL_MNEMONIC, "SYS")
        self.assertEqual(abi.SYSCALL_SOURCE_SYNONYMS, ("SCALL",))
        self.assertEqual(abi.SYSCALL_TRAP_CAUSE, "SYSCALL_TRAP")
        self.assertEqual(assembly.assemble_line("SCALL").source, "SYS")

    def test_integer_syscall_service_arguments_and_returns_use_baseline_registers(self) -> None:
        layout = abi.layout_syscall_arguments([abi.AbiValueKind.INTEGER] * 5)

        self.assertEqual(abi.SYSCALL_SERVICE_REGISTER, 0)
        self.assertEqual(abi.SYSCALL_INTEGER_ARGUMENT_REGS, (1, 2, 3, 4, 5))
        self.assertEqual(abi.SYSCALL_INTEGER_RETURN_REGS, (0, 1))
        self.assertEqual(layout.overflow_size_cells, 0)
        self.assertEqual(
            tuple(location.register_index for location in layout.locations),
            abi.SYSCALL_INTEGER_ARGUMENT_REGS,
        )

    def test_sixth_integer_syscall_argument_uses_first_overflow_slot(self) -> None:
        layout = abi.layout_syscall_arguments([abi.AbiValueKind.INTEGER] * 6)
        sixth = layout.location_for_argument(5)

        self.assertTrue(sixth.is_stack)
        self.assertEqual(sixth.offset_cells, 0)
        self.assertEqual(sixth.size_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(layout.overflow_size_cells, cells.CAPABILITY_OBJECT_CELLS)

    def test_capability_syscall_arguments_returns_and_overflow_preserve_tags(self) -> None:
        layout = abi.layout_syscall_arguments([abi.AbiValueKind.CAPABILITY] * 5)
        fifth = layout.location_for_argument(4)

        self.assertEqual(abi.SYSCALL_CAPABILITY_ARGUMENT_REGS, (0, 1, 2, 3))
        self.assertEqual(abi.SYSCALL_CAPABILITY_RETURN_REGS, (0,))
        self.assertTrue(fifth.is_stack)
        self.assertEqual(fifth.offset_cells, 0)
        self.assertEqual(fifth.size_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertTrue(fifth.tag_required)

    def test_mixed_syscall_overflow_reuses_language_abi_stack_layout(self) -> None:
        arguments = (
            [abi.AbiValueKind.INTEGER] * 5
            + [abi.AbiValueKind.CAPABILITY] * 4
            + [abi.AbiValueKind.INTEGER, abi.AbiValueKind.CAPABILITY]
        )
        layout = abi.layout_syscall_arguments(arguments)

        overflow_integer = layout.location_for_argument(9)
        overflow_capability = layout.location_for_argument(10)
        self.assertEqual(overflow_integer.offset_cells, 0)
        self.assertEqual(overflow_integer.size_cells, cells.INTEGER_OBJECT_CELLS)
        self.assertEqual(overflow_capability.offset_cells, 4)
        self.assertEqual(overflow_capability.size_cells, cells.CAPABILITY_OBJECT_CELLS)
        self.assertTrue(overflow_capability.tag_required)
        self.assertEqual(layout.overflow_size_cells, 8)

    def test_syscalls_share_caller_saved_volatility_policy(self) -> None:
        self.assertEqual(abi.SYSCALL_VOLATILE_INTEGER_REGS, abi.INTEGER_CALLER_SAVED_REGS)
        self.assertEqual(abi.SYSCALL_VOLATILE_CAPABILITY_REGS, abi.CAPABILITY_CALLER_SAVED_REGS)
        self.assertIn(0, abi.SYSCALL_VOLATILE_INTEGER_REGS)
        self.assertIn(0, abi.SYSCALL_VOLATILE_CAPABILITY_REGS)


if __name__ == "__main__":
    unittest.main()

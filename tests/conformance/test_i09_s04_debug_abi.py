"""I09-S04 conformance tests for debugger register and unwind ABI supplements."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities, csrs, debug_abi, state


class DebugAbiSupplementTests(unittest.TestCase):
    def test_debug_register_inventory_matches_architectural_state(self) -> None:
        self.assertEqual(debug_abi.validate_debug_abi_profile(), ())
        self.assertEqual(
            len(debug_abi.debug_register_views(debug_abi.DebugRegisterClass.INTEGER)),
            state.INTEGER_REGISTER_COUNT,
        )
        self.assertEqual(
            len(debug_abi.debug_register_views(debug_abi.DebugRegisterClass.CAPABILITY)),
            state.GENERAL_CAPABILITY_REGISTER_COUNT,
        )
        self.assertEqual(
            tuple(
                view.name
                for view in debug_abi.debug_register_views(debug_abi.DebugRegisterClass.SPECIAL_CAPABILITY)
            ),
            state.SPECIAL_CAPABILITY_NAMES,
        )

    def test_debug_views_preserve_capability_tags_and_hidden_slots(self) -> None:
        self.assertFalse(debug_abi.debug_register_view("D0").tag_visible)
        self.assertTrue(debug_abi.debug_register_view("C0").tag_visible)
        self.assertTrue(debug_abi.debug_register_view("PCC").tag_visible)
        self.assertTrue(debug_abi.debug_register_view("PCC").slot_visible)
        self.assertTrue(debug_abi.debug_register_view("EPCC").slot_visible)
        self.assertFalse(debug_abi.debug_register_view("RSC").slot_visible)

    def test_scalar_csr_debug_views_are_scalar_and_respect_readonly_profile(self) -> None:
        sr = debug_abi.debug_register_view("SR")
        coreid = debug_abi.debug_register_view("COREID")
        debugctl = debug_abi.debug_register_view("DEBUGCTL")

        self.assertEqual(sr.index, csrs.CSR_SR)
        self.assertTrue(sr.readable)
        self.assertTrue(sr.writable)
        self.assertFalse(sr.tag_visible)
        self.assertFalse(coreid.writable)
        self.assertTrue(debugctl.writable)

    def test_direct_debug_register_access_requires_debug_halted_lifecycle(self) -> None:
        self.assertTrue(debug_abi.direct_register_access_allowed(state.CoreLifecycle.DEBUG_HALTED))
        self.assertFalse(debug_abi.direct_register_access_allowed(state.CoreLifecycle.RUNNING))
        self.assertFalse(debug_abi.direct_register_access_allowed(state.CoreLifecycle.DEBUG_MONITOR))

    def test_protected_return_stack_unwind_rules_are_precise_and_atomic(self) -> None:
        peek = debug_abi.debug_unwind_rule(debug_abi.DebugUnwindOperation.PEEK)
        drop = debug_abi.debug_unwind_rule(debug_abi.DebugUnwindOperation.DROP)
        replace = debug_abi.debug_unwind_rule(debug_abi.DebugUnwindOperation.REPLACE)

        self.assertEqual(debug_abi.RETURN_STACK_ENTRY_CELLS, 4)
        self.assertEqual(debug_abi.DEBUG_RETURN_REPLACEMENT_OTYPE, capabilities.OTYPE_RETURN)
        self.assertFalse(peek.updates_rsc_cursor)
        self.assertFalse(peek.writes_return_slot)
        self.assertTrue(drop.updates_rsc_cursor)
        self.assertFalse(drop.writes_return_slot)
        self.assertFalse(replace.updates_rsc_cursor)
        self.assertTrue(replace.writes_return_slot)
        self.assertTrue(replace.requires_valid_return_capability)
        self.assertTrue(replace.atomic_payload_tag)

    def test_unknown_debug_register_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            debug_abi.debug_register_view("NOPE")


if __name__ == "__main__":
    unittest.main()

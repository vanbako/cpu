"""I10-S01 conformance tests for RTL handoff artifacts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl


class RtlHandoffTests(unittest.TestCase):
    def test_rtl_handoff_self_validation_passes(self) -> None:
        self.assertEqual(rtl.validate_rtl_handoff(), ())

    def test_decoder_table_is_derived_from_opcode_forms(self) -> None:
        opcode_keys = {
            (form.mnemonic, form.size.bits, form.opcode_id, form.fixed_mask, form.fixed_value)
            for form in opcodes.all_opcode_forms()
        }
        decoder_keys = {
            (row.mnemonic, row.size_bits, row.opcode_id, row.fixed_mask, row.fixed_value)
            for row in rtl.DECODER_TABLE
        }

        self.assertEqual(decoder_keys, opcode_keys)
        self.assertEqual(rtl.decoder_row_for("SCALL"), rtl.decoder_row_for("SYS"))
        self.assertGreater(len(rtl.decoder_row_for("CSRRD")), 1)

    def test_commit_point_checklist_names_multi_effect_boundaries(self) -> None:
        names = {item.name for item in rtl.COMMIT_POINT_CHECKLIST}
        self.assertIn("normal_retire_packet", names)
        self.assertIn("fault_packet_priority", names)
        self.assertIn("payload_tag_memory_commit", names)
        self.assertIn("protected_return_stack_transaction", names)
        self.assertIn("reservation_update", names)
        self.assertIn("tlb_cache_maintenance", names)

    def test_fault_packet_and_tag_path_interfaces_are_explicit(self) -> None:
        self.assertEqual(
            rtl.FAULT_PACKET_FIELDS,
            ("cause", "faulting_location", "tval", "capcause", "fault_cap_idx"),
        )
        tag_names = {item.name for item in rtl.TAG_PATH_CHECKLIST}
        self.assertIn("register_capability_tags", tag_names)
        self.assertIn("memory_capability_tags", tag_names)
        self.assertIn("capability_load_store_tags", tag_names)
        self.assertIn("ccsr_tag_copy", tag_names)

    def test_conformance_hooks_include_suite_and_spec_commands(self) -> None:
        hooks = "\n".join(rtl.CONFORMANCE_HOOKS)
        self.assertIn("tests\\conformance", hooks)
        self.assertIn("tests\\litmus", hooks)
        self.assertIn("spec_reference_check.py", hooks)
        self.assertIn("spec_constants_model.py", hooks)


if __name__ == "__main__":
    unittest.main()

"""I07-S01 conformance tests for the mandatory v0.1 opcode table."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import instructions
from cpu_v01 import opcodes


SPEC_REQUIRED_MNEMONICS = (
    "CPY",
    "NEG",
    "ADD",
    "ADDU",
    "SUB",
    "SUBU",
    "MUL",
    "MULU",
    "DIV",
    "DIVU",
    "MOD",
    "MODU",
    "NOT",
    "AND",
    "OR",
    "XOR",
    "SHL",
    "SHRS",
    "SHRU",
    "ROL",
    "ROR",
    "CMP",
    "CMPU",
    "TST",
    "SETcc",
    "CMOVcc",
    "BSET",
    "BCLR",
    "LD48",
    "ST48",
    "CLC",
    "CSC",
    "CMOVE",
    "CGETADDR",
    "CSETADDR",
    "CINCADDR",
    "CSETBOUNDS",
    "CANDPERM",
    "CSEAL",
    "CUNSEAL",
    "BRA",
    "Bcc",
    "CALL",
    "RET",
    "JMP",
    "BRK",
    "SYS",
    "SCALL",
    "IRET",
    "EPCCRD",
    "EPCCWR",
    "WFI",
    "PAUSE",
    "LL48",
    "SC48",
    "FENCE",
    "FENCE.I",
    "SFENCE.VM",
    "SFENCE.VM.ASID",
    "SFENCE.VM.VA",
    "SFENCE.VM.VA_ASID",
    "CSRRD",
    "CSRWR",
    "CSRSET",
    "CSRCLR",
    "CCSRRD",
    "CCSRWR",
    "CALLC",
    "CACHE.CLEAN",
    "CACHE.INVAL",
    "CACHE.CLEANINVAL",
)


class MandatoryOpcodeTableTests(unittest.TestCase):
    def test_opcode_table_self_validation_passes(self) -> None:
        self.assertEqual(opcodes.validate_opcode_table(), ())

    def test_every_required_mnemonic_has_canonical_form_or_synonym(self) -> None:
        self.assertEqual(opcodes.missing_mandatory_mnemonics(SPEC_REQUIRED_MNEMONICS), ())

        canonical = set(opcodes.mandatory_mnemonics())
        self.assertIn("SETCC", canonical)
        self.assertIn("CMOVCC", canonical)
        self.assertIn("BCC", canonical)
        self.assertNotIn("SCALL", canonical)
        self.assertEqual(opcodes.canonical_mnemonic("SCALL"), "SYS")
        self.assertEqual(opcodes.opcode_form_for("SCALL"), opcodes.opcode_form_for("SYS"))

    def test_excluded_optional_instructions_are_absent(self) -> None:
        for mnemonic in ("CAS48", "CAS96", "AMOADD", "AMO.CAS", "DMA.TAG.FLUSH"):
            self.assertTrue(opcodes.is_excluded_mnemonic(mnemonic))
            with self.assertRaises(KeyError):
                opcodes.opcode_forms_for(mnemonic)

    def test_final_opcode_selectors_do_not_collide(self) -> None:
        seen: dict[tuple[instructions.InstructionSize, int], str] = {}
        for form in opcodes.all_opcode_forms():
            key = (form.size, form.opcode_id)
            self.assertNotIn(key, seen, f"{form.mnemonic} collides with {seen.get(key)}")
            seen[key] = form.mnemonic
            self.assertEqual(form.fixed_value & form.fixed_mask, form.fixed_value)

    def test_instruction_sizes_match_owner_story_placement_contracts(self) -> None:
        for mnemonic in ("RET", "BRK", "SYS", "WFI", "PAUSE"):
            self.assertEqual(opcodes.opcode_form_for(mnemonic).size, instructions.InstructionSize.BITS_12)

        for mnemonic in ("CMOVE", "CGETADDR", "CSETADDR", "CCSRRD", "CCSRWR"):
            self.assertEqual(opcodes.opcode_form_for(mnemonic).size, instructions.InstructionSize.BITS_48)
            self.assertTrue(opcodes.opcode_form_for(mnemonic).size.is_legal_start(0x2000, 0))
            self.assertFalse(opcodes.opcode_form_for(mnemonic).size.is_legal_start(0x2001, 0))

        csr_sizes = {form.size for form in opcodes.opcode_forms_for("CSRRD")}
        self.assertEqual(csr_sizes, {instructions.InstructionSize.BITS_24, instructions.InstructionSize.BITS_48})

    def test_privilege_classes_cover_user_kernel_and_csr_specific_forms(self) -> None:
        self.assertEqual(opcodes.opcode_form_for("FENCE").privilege, opcodes.PrivilegeClass.USER)
        self.assertEqual(opcodes.opcode_form_for("PAUSE").privilege, opcodes.PrivilegeClass.USER)
        self.assertEqual(opcodes.opcode_form_for("FENCE.I").privilege, opcodes.PrivilegeClass.KERNEL)
        self.assertEqual(opcodes.opcode_form_for("SFENCE.VM").privilege, opcodes.PrivilegeClass.KERNEL)
        self.assertEqual(opcodes.opcode_form_for("CCSRRD").privilege, opcodes.PrivilegeClass.KERNEL)
        self.assertEqual(opcodes.opcode_form_for("CACHE.CLEAN").privilege, opcodes.PrivilegeClass.KERNEL)
        for form in opcodes.opcode_forms_for("CSRSET"):
            self.assertEqual(form.privilege, opcodes.PrivilegeClass.CSR_SPECIFIC)

    def test_condition_families_use_the_shared_condition_namespace(self) -> None:
        self.assertEqual(opcodes.canonical_condition("AL"), "AL")
        self.assertEqual(opcodes.canonical_condition("HS"), "CS")
        self.assertEqual(opcodes.canonical_condition("LO"), "CC")
        with self.assertRaises(KeyError):
            opcodes.canonical_condition("NV")

        self.assertEqual(opcodes.opcode_form_for("SETcc").source_mnemonic, "SETcc")
        self.assertEqual(opcodes.opcode_form_for("CMOVcc").source_mnemonic, "CMOVcc")
        self.assertEqual(opcodes.opcode_form_for("Bcc").source_mnemonic, "Bcc")


if __name__ == "__main__":
    unittest.main()

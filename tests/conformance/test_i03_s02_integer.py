"""I03-S02 conformance tests for baseline integer operations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import csrs, execution, integer, instructions, reset


def execute_and_commit(core, decoded):
    result = integer.execute_integer(core, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


class IntegerOperationTests(unittest.TestCase):
    def test_all_mandatory_integer_mnemonics_are_recognized(self) -> None:
        expected = {
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
            "SETCC",
            "CMOVCC",
            "BSET",
            "BCLR",
        }
        self.assertEqual(integer.MANDATORY_INTEGER_MNEMONICS, expected)

    def test_width_write_forms_zero_and_sign_extend_without_merging(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(1, 0x123456789AFF)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "CPY",
                (0, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0x0000000000FF)

        core.write_d(0, 0x555555555555)
        execute_and_commit(
            core,
            integer.integer_instruction(
                "CPY",
                (0, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.SIGN_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFFFFFFFFFFFF)

    def test_add_sub_and_neg_wrap_and_leave_flags_unchanged(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        old_sr = core.read_csr(csrs.CSR_SR)
        core.write_d(1, 0xFF)
        core.write_d(2, 0x02)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "ADD",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0x01)
        self.assertEqual(core.read_csr(csrs.CSR_SR), old_sr)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "SUBU",
                (0, 2, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0x03)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "NEG",
                (0, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0x01)

    def test_multiply_signed_and_unsigned_write_low_width_bits(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(1, 0xFF)
        core.write_d(2, 0x02)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "MUL",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.SIGN_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFFFFFFFFFFFE)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "MULU",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFE)

    def test_divide_and_modulo_normal_cases_and_signed_overflow(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(1, 0xF6)  # -10 in W8
        core.write_d(2, 0x03)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "DIV",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.SIGN_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFFFFFFFFFFFD)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "MOD",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.SIGN_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFFFFFFFFFFFF)

        core.write_d(1, 0x80)
        core.write_d(2, 0xFF)
        execute_and_commit(
            core,
            integer.integer_instruction(
                "DIV",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0x80)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "MOD",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0)

    def test_divide_by_zero_fault_leaves_destination_flags_and_instret(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(0, 0xAAAA)
        core.write_d(1, 10)
        core.write_d(2, 0)
        old_sr = core.read_csr(csrs.CSR_SR)
        old_instret = core.read_csr(csrs.CSR_INSTRET)

        result = integer.execute_integer(
            core,
            integer.integer_instruction(
                "DIVU",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
            ),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.DIVIDE_BY_ZERO)
        self.assertEqual(core.read_d(0), 0xAAAA)
        self.assertEqual(core.read_csr(csrs.CSR_SR), old_sr)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), old_instret)

    def test_shift_rotate_and_bit_operations(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(1, 0b10000001)
        core.write_d(2, 9)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "SHL",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "SHRS",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
            ),
        )
        self.assertEqual(core.read_d(0), 0xFF)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "ROL",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0b00000011)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "ROR",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0b11000000)

        core.write_d(2, 8)
        execute_and_commit(
            core,
            integer.integer_instruction(
                "BCLR",
                (0, 1, 2),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0b10000000)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "BSET",
                (0, 0, 2),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0b10000001)

    def test_logical_binary_and_not(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(1, 0b1010)
        core.write_d(2, 0b1100)

        for mnemonic, expected in (("AND", 0b1000), ("OR", 0b1110), ("XOR", 0b0110)):
            execute_and_commit(
                core,
                integer.integer_instruction(
                    mnemonic,
                    (0, 1, 2),
                    width=integer.IntegerWidth.W8,
                ),
            )
            self.assertEqual(core.read_d(0), expected)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "NOT",
                (0, 1),
                width=integer.IntegerWidth.W8,
            ),
        )
        self.assertEqual(core.read_d(0), 0xF5)

    def test_cmp_cmpu_and_tst_update_flags_only(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(0, 0xAAAA)
        core.write_d(1, 0x80)
        core.write_d(2, 0x01)

        execute_and_commit(
            core,
            integer.integer_instruction("CMP", (1, 2), width=integer.IntegerWidth.W8),
        )
        sr = core.read_csr(csrs.CSR_SR)
        self.assertFalse(sr & (1 << csrs.SR_Z_BIT))
        self.assertFalse(sr & (1 << csrs.SR_N_BIT))
        self.assertTrue(sr & (1 << csrs.SR_C_BIT))
        self.assertTrue(sr & (1 << csrs.SR_V_BIT))
        self.assertEqual(core.read_d(0), 0xAAAA)

        execute_and_commit(
            core,
            integer.integer_instruction("CMPU", (2, 1), width=integer.IntegerWidth.W8),
        )
        sr = core.read_csr(csrs.CSR_SR)
        self.assertFalse(sr & (1 << csrs.SR_C_BIT))

        execute_and_commit(
            core,
            integer.integer_instruction("TST", (1, 2), width=integer.IntegerWidth.W8),
        )
        sr = core.read_csr(csrs.CSR_SR)
        self.assertTrue(sr & (1 << csrs.SR_Z_BIT))
        self.assertFalse(sr & (1 << csrs.SR_C_BIT))
        self.assertFalse(sr & (1 << csrs.SR_V_BIT))

    def test_setcc_and_cmovcc_use_condition_flags(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_csr_raw(csrs.CSR_SR, csrs.SR_RESET_VALUE | (1 << csrs.SR_Z_BIT))
        core.write_d(1, 0xFF)
        core.write_d(2, 0x1234)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "SETCC",
                (0,),
                condition=integer.ConditionCode.EQ,
            ),
        )
        self.assertEqual(core.read_d(0), 1)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "CMOVCC",
                (2, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
                condition="NE",
            ),
        )
        self.assertEqual(core.read_d(2), 0x1234)

        execute_and_commit(
            core,
            integer.integer_instruction(
                "CMOVCC",
                (2, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
                condition="HS",
            ),
        )
        self.assertEqual(core.read_d(2), 0x1234)

        core.write_csr_raw(csrs.CSR_SR, core.read_csr(csrs.CSR_SR) | (1 << csrs.SR_C_BIT))
        execute_and_commit(
            core,
            integer.integer_instruction(
                "CMOVCC",
                (2, 1),
                width=integer.IntegerWidth.W8,
                write_form=integer.WriteForm.ZERO_EXTEND,
                condition="HS",
            ),
        )
        self.assertEqual(core.read_d(2), 0xFF)

    def test_normal_integer_retire_increments_instret_once(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

        execute_and_commit(
            core,
            integer.integer_instruction("CPY", (0, 1)),
        )
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_unknown_or_malformed_integer_instruction_reports_illegal_instruction(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        result = integer.execute_integer(
            core,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_24),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = integer.execute_integer(
            core,
            integer.integer_instruction("ADD", (0, 1)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

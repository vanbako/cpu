"""I07-S02 conformance tests for assembler/disassembler binary fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly
from cpu_v01 import instructions


class AssemblerDisassemblerFixtureTests(unittest.TestCase):
    def test_single_instruction_round_trips_to_canonical_source(self) -> None:
        cases = {
            "ADD D1, D2, D3": "ADD D1, D2, D3",
            "ADD.W32.S D1, D2, D3": "ADD.W32.S D1, D2, D3",
            "CMOVE C1, C2": "CMOVE C1, C2",
            "LD48 D4, C1, D2": "LD48 D4, C1, D2",
            "CACHE.CLEAN C1, D2, D3": "CACHE.CLEAN C1, D2, D3",
            "SFENCE.VM.VA_ASID D4, D5": "SFENCE.VM.VA_ASID D4, D5",
            "Bcc EQ, 0x34": "Bcc EQ, 0x34",
            "BEQ 0x34": "Bcc EQ, 0x34",
            "SETEQ D1": "SETcc D1, EQ",
            "CMOVNE D1, D2": "CMOVcc D1, D2, NE",
            "SCALL": "SYS",
        }
        for source, canonical in cases.items():
            with self.subTest(source=source):
                encoded = assembly.assemble_line(source)
                self.assertEqual(encoded.source, canonical)
                decoded = assembly.decode_value(encoded.size, encoded.value)
                self.assertEqual(decoded.source, canonical)

    def test_program_packs_12_24_and_48_bit_binary_fixtures(self) -> None:
        cells = assembly.assemble_program(
            (
                "RET",
                "PAUSE",
                "ADD D1, D2, D3",
                "CMOVE C1, C2",
            )
        )

        self.assertEqual(cells, (0x05B053, 0x12123A, 0x400000, 0x120000))
        self.assertEqual(
            assembly.disassemble_program(cells),
            ("RET", "PAUSE", "ADD D1, D2, D3", "CMOVE C1, C2"),
        )

    def test_csr_fast_long_and_forced_long_forms_round_trip(self) -> None:
        fast = assembly.assemble_line("CSRRD D1, SR")
        forced_long = assembly.assemble_line("CSRRD.L D1, SR")
        extended = assembly.assemble_line("CSRRD D1, FAULTCAPIDX")

        self.assertEqual(fast.size, instructions.InstructionSize.BITS_24)
        self.assertEqual(fast.cells, (0x661000,))
        self.assertEqual(forced_long.size, instructions.InstructionSize.BITS_48)
        self.assertEqual(forced_long.cells, (0x6A0000, 0x100000))
        self.assertEqual(extended.size, instructions.InstructionSize.BITS_48)
        self.assertEqual(extended.cells, (0x6A0000, 0x14A000))
        self.assertEqual(assembly.disassemble_program(forced_long.cells), ("CSRRD.L D1, SR",))
        self.assertEqual(assembly.disassemble_program(extended.cells), ("CSRRD D1, FAULTCAPIDX",))

    def test_mandatory_forms_have_representative_fixture_encodings(self) -> None:
        representatives = (
            "CPY D1, D2",
            "CMP D1, D2",
            "SETcc D1, EQ",
            "CMOVcc D1, D2, NE",
            "ST48 C1, D2, D3",
            "CLC C1, C2, D3",
            "CSC C1, D2, C3",
            "LL48 D1, C2, D3",
            "SC48 D1, C2, D3, D4",
            "CGETADDR D1, C2",
            "CSETBOUNDS C1, C2, D3",
            "CSEAL C1, C2, C3",
            "BRA 0x1234",
            "CALL 0x1234",
            "JMP C2",
            "BRK",
            "SYS",
            "IRET",
            "EPCCRD C1, D2",
            "EPCCWR C1, D2",
            "WFI",
            "FENCE",
            "FENCE.I",
            "SFENCE.VM",
            "SFENCE.VM.ASID D1",
            "CSRWR SR, D1",
            "CSRSET D1, SR, D2",
            "CSRCLR D1, SR, D2",
            "CCSRRD C1, PCC",
            "CCSRWR PCC, C1",
            "CALLC C1",
            "CACHE.INVAL C1, D2, D3",
            "CACHE.CLEANINVAL C1, D2, D3",
        )
        for source in representatives:
            with self.subTest(source=source):
                encoded = assembly.assemble_line(source)
                self.assertEqual(assembly.decode_value(encoded.size, encoded.value).source, encoded.source)

    def test_illegal_or_malformed_source_is_rejected(self) -> None:
        for source in (
            "CAS48 D1, C2, D3",
            "AMOADD D1, C2, D3",
            "ADD D16, D2, D3",
            "CMOVE C8, C1",
            "CSRRD D1, 0x100",
            "CSRRD D1, SR, D2",
            "Bcc NV, 0x10",
            "Bcc EQ, 0x1000",
            "CSRRD.L.L D1, SR",
        ):
            with self.subTest(source=source):
                with self.assertRaises(assembly.AssemblyError):
                    assembly.assemble_line(source)

    def test_illegal_or_malformed_binary_is_rejected(self) -> None:
        with self.assertRaises(assembly.DecodeError):
            assembly.decode_value(instructions.InstructionSize.BITS_24, 0xAA0000)

        malformed_cmove = 0x400000 | 0xF000
        with self.assertRaises(assembly.DecodeError):
            assembly.disassemble_program((malformed_cmove, 0x000000))

        reserved_condition = 0x510000 | 0xF000
        with self.assertRaises(assembly.DecodeError):
            assembly.decode_value(instructions.InstructionSize.BITS_24, reserved_condition)

        with self.assertRaises(assembly.DecodeError):
            assembly.disassemble_program((0x000000, 0x400000, 0x000000))

    def test_program_placement_rules_reject_slot_and_fetch_group_violations(self) -> None:
        with self.assertRaises(assembly.AssemblyError):
            assembly.assemble_program(("RET", "ADD D1, D2, D3"))

        with self.assertRaises(assembly.AssemblyError):
            assembly.assemble_program(("ADD D1, D2, D3", "CMOVE C1, C2"))


if __name__ == "__main__":
    unittest.main()

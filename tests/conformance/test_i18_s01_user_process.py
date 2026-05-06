"""I18-S01 conformance tests for user process entry-context fixtures."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import abi, assembly, capabilities as caps, csrs, platform
from cpu_v01 import program_image, state, user_process
from cpu_v01.memory import TaggedMemory
from cpu_v01.tlb import TlbEntry, TlbKind


class UserProcessEntryFixtureTests(unittest.TestCase):
    def test_user_process_manifest_loads_text_and_data(self) -> None:
        context = user_process.default_user_entry_context()
        memory = TaggedMemory()

        report = user_process.load_user_process_image(context, memory)

        self.assertEqual(user_process.validate_user_process_image(context.manifest), ())
        self.assertEqual(context.manifest.entry_cell, user_process.USER_ENTRY_CELL)
        self.assertIs(
            context.manifest.entry_source,
            program_image.EntryCapabilitySource.MANIFEST_ENTRY,
        )
        self.assertEqual(report.sections_loaded, 2)
        expected_cells = user_process.USER_TEXT_CELLS + user_process.USER_DATA_CELLS
        self.assertEqual(report.cells_loaded, expected_cells)
        self.assertEqual(
            memory.read_cell(user_process.USER_ENTRY_CELL),
            assembly.assemble_program(user_process.USER_TEXT_SOURCE)[0],
        )
        self.assertEqual(memory.read_cell(user_process.USER_DATA_BASE), user_process.USER_ARG0)

    def test_enter_context_installs_user_state_abi_registers_and_protected_stack(self) -> None:
        context = user_process.default_user_entry_context()
        core = platform.cold_reset_cores()[0]
        memory = TaggedMemory()
        core.write_d(0, 0xBAD)
        core.write_d(7, 0xBAD)
        core.write_c(0, caps.Capability.invalid())
        core.tlbs.insert(
            TlbEntry(
                kind=TlbKind.DATA,
                mode=csrs.SATP_MODE_BARE,
                vpn=1,
                asid=1,
                ppn=1,
                user=True,
                readable=True,
                writable=True,
                executable=False,
                memory_type=0,
            )
        )

        report = user_process.enter_user_process_context(core, context, memory)

        self.assertTrue(report.user_mode)
        self.assertTrue(report.interrupt_enable)
        self.assertTrue(report.return_stack_protected)
        self.assertEqual(core.pcc, context.pcc)
        self.assertEqual(core.pcc.payload.cursor, user_process.USER_ENTRY_CELL)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(core.special_capabilities.read("DSC"), context.dsc)
        self.assertEqual(core.special_capabilities.read("RSC"), context.rsc)
        self.assertEqual(core.read_csr(csrs.CSR_SATP), context.satp)
        self.assertEqual(core.read_csr(csrs.CSR_ASID), user_process.USER_ASID)
        self.assertFalse(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_PRIV_BIT))
        self.assertFalse(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_EXL_BIT))
        self.assertTrue(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_IE_BIT))
        self.assertEqual(core.read_d(abi.INTEGER_ARGUMENT_REGS[0]), user_process.USER_ARG0)
        self.assertEqual(core.read_d(abi.INTEGER_ARGUMENT_REGS[1]), user_process.USER_ARG1)
        self.assertEqual(core.read_d(7), 0)
        self.assertEqual(
            core.read_c(abi.CAPABILITY_ARGUMENT_REGS[0]),
            context.capability_arguments[0],
        )
        self.assertEqual(core.tlbs.entry_count(), 0)
        self.assertTrue(
            memory.overlaps_protected_range(
                user_process.USER_RETURN_STACK_BASE,
                user_process.USER_RETURN_STACK_CELLS,
            )
        )
        self.assertEqual(report.integer_argument_registers, abi.INTEGER_ARGUMENT_REGS[:2])
        self.assertEqual(report.capability_argument_registers, abi.CAPABILITY_ARGUMENT_REGS[:1])

    def test_invalid_manifest_rejects_load_without_memory_writes(self) -> None:
        context = user_process.default_user_entry_context()
        bad_manifest = replace(
            context.manifest,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
        )
        bad_context = replace(context, manifest=bad_manifest)
        memory = TaggedMemory()

        with self.assertRaises(user_process.UserProcessError) as raised:
            user_process.load_user_process_image(bad_context, memory)

        self.assertIn("user process image must use MANIFEST_ENTRY", str(raised.exception))
        self.assertEqual(memory.read_cell(user_process.USER_ENTRY_CELL), 0)
        self.assertEqual(memory.read_cell(user_process.USER_DATA_BASE), 0)

    def test_invalid_context_rejects_entry_without_partial_core_state(self) -> None:
        context = user_process.default_user_entry_context()
        bad_context = replace(context, dsc=context.dsc.with_tag(False))
        core = platform.cold_reset_cores()[0]
        core.write_d(0, 0x1234)
        original_pcc = core.pcc
        original_sr = core.read_csr(csrs.CSR_SR)
        original_satp = core.read_csr(csrs.CSR_SATP)
        original_c0 = core.read_c(0)

        with self.assertRaises(user_process.UserProcessError) as raised:
            user_process.enter_user_process_context(core, bad_context, TaggedMemory())

        self.assertIn("user DSC must carry a valid tag", str(raised.exception))
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.read_csr(csrs.CSR_SR), original_sr)
        self.assertEqual(core.read_csr(csrs.CSR_SATP), original_satp)
        self.assertEqual(core.read_d(0), 0x1234)
        self.assertEqual(core.read_c(0), original_c0)

    def test_documentation_artifact_names_image_context_and_partial_state_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "user-process-entry.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I18-S01", text)
        self.assertIn("MANIFEST_ENTRY", text)
        self.assertIn("SATP", text)
        self.assertIn("without partial state", text)


if __name__ == "__main__":
    unittest.main()

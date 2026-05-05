"""I11-S03 conformance tests for reset-to-trap smoke execution."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly, csrs, platform, smoke, state
from cpu_v01 import program_image
from cpu_v01.memory import TaggedMemory


class ResetToTrapSmokeTests(unittest.TestCase):
    def test_smoke_manifest_contains_serialized_main_and_handler_sections(self) -> None:
        manifest = smoke.reset_to_trap_smoke_manifest()
        memory = TaggedMemory()

        self.assertEqual(program_image.validate_program_image_manifest(manifest), ())
        report = program_image.load_program_image(manifest, memory)

        main_cells = assembly.assemble_program(smoke.SMOKE_MAIN_SOURCE)
        handler_cells = assembly.assemble_program(smoke.SMOKE_HANDLER_SOURCE)
        self.assertEqual(report.sections_loaded, 2)
        self.assertEqual(
            tuple(memory.read_cell(platform.RESET_VECTOR + offset) for offset in range(len(main_cells))),
            main_cells,
        )
        self.assertEqual(
            tuple(memory.read_cell(smoke.SMOKE_HANDLER_CELL + offset) for offset in range(len(handler_cells))),
            handler_cells,
        )
        self.assertEqual(assembly.disassemble_program(main_cells), smoke.SMOKE_MAIN_SOURCE)
        self.assertEqual(assembly.disassemble_program(handler_cells), smoke.SMOKE_HANDLER_SOURCE)

    def test_decoded_program_layout_matches_packed_sys_pause_slot_shape(self) -> None:
        decoded = smoke.reset_to_trap_smoke_decoded_program()

        self.assertTrue(decoded.contains_location(platform.RESET_VECTOR + 3, state.SLOT_0))
        self.assertTrue(decoded.contains_location(platform.RESET_VECTOR + 3, state.SLOT_1))
        self.assertTrue(decoded.contains_location(smoke.SMOKE_HANDLER_CELL, state.SLOT_0))
        self.assertFalse(decoded.contains_location(platform.RESET_VECTOR + 4, state.SLOT_0))

    def test_reset_to_trap_smoke_runs_through_syscall_and_iret(self) -> None:
        report = smoke.run_reset_to_trap_smoke_program()

        self.assertEqual(report.image_load.sections_loaded, 2)
        self.assertEqual(report.steps, 8)
        self.assertTrue(report.trap_entered)
        self.assertEqual(report.syscall_cause.name, "SYSCALL_TRAP")
        self.assertEqual(report.stored_value, 0x30)
        self.assertEqual(report.loaded_value, 0x30)
        self.assertEqual(report.pcc_after_iret_address, platform.RESET_VECTOR + 3)
        self.assertEqual(report.pcc_after_iret_slot, state.SLOT_1)
        self.assertEqual(report.final_pcc_address, platform.RESET_VECTOR + 4)
        self.assertEqual(report.final_pcc_slot, state.SLOT_0)
        self.assertEqual(report.instret, 8)

    def test_smoke_reset_starts_from_platform_pcc_and_tvc_enters_handler(self) -> None:
        cores = platform.cold_reset_cores()
        core = cores[0]

        self.assertEqual(core.pcc.payload.cursor, platform.RESET_VECTOR)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), state.SLOT_0)

    def test_documentation_artifact_names_slot_iret_boundary(self) -> None:
        doc = ROOT / "docs" / "implementation" / "reset-to-trap-smoke.md"
        text = doc.read_text(encoding="utf-8")

        self.assertIn("Story: I11-S03", text)
        self.assertIn("SYS` and `PAUSE` are packed 12-bit instructions", text)
        self.assertIn("restores `EPCC` to slot 1", text)


if __name__ == "__main__":
    unittest.main()

"""I14-S01 conformance tests for tiny ROM initialization and handoff."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly, capabilities as caps, firmware, platform, program_image, state
from cpu_v01.memory import TaggedMemory


class TinyRomInitializationTests(unittest.TestCase):
    def test_tiny_rom_manifest_loads_init_and_handoff_sections(self) -> None:
        manifest = firmware.tiny_rom_manifest()
        memory = TaggedMemory()

        self.assertEqual(program_image.validate_program_image_manifest(manifest), ())
        report = program_image.load_program_image(manifest, memory)

        init_cells = assembly.assemble_program(firmware.ROM_INIT_SOURCE)
        handoff_cells = assembly.assemble_program(firmware.KERNEL_HANDOFF_SOURCE)
        self.assertEqual(report.sections_loaded, 2)
        self.assertEqual(
            tuple(memory.read_cell(platform.RESET_VECTOR + offset) for offset in range(len(init_cells))),
            init_cells,
        )
        self.assertEqual(
            tuple(memory.read_cell(firmware.KERNEL_HANDOFF_CELL + offset) for offset in range(len(handoff_cells))),
            handoff_cells,
        )

    def test_tiny_rom_initialization_installs_kernel_handoff_capabilities(self) -> None:
        memory = TaggedMemory()
        report = firmware.run_tiny_rom_initialization(memory=memory)
        handoff = report.handoff

        self.assertEqual(report.profile_issues, ())
        self.assertEqual(report.image_load.sections_loaded, 2)
        self.assertEqual(report.steps, 3)
        self.assertEqual(handoff.pcc.payload.cursor, firmware.KERNEL_HANDOFF_CELL)
        self.assertEqual(handoff.pcc.slot, state.SLOT_0)
        self.assertTrue(handoff.pcc.payload.has_permissions(caps.CapabilityPermission.EX))

        self.assertTrue(handoff.krc.is_valid)
        self.assertTrue(handoff.krc.is_global)
        self.assertTrue(handoff.krc.payload.has_permissions(caps.CapabilityPermission.SEAL))
        self.assertTrue(handoff.ksc.is_local)
        self.assertTrue(handoff.dsc.is_local)
        self.assertTrue(handoff.rsc.is_local)
        self.assertFalse(handoff.ksc.payload.has_permissions(caps.CapabilityPermission.EX))
        self.assertFalse(handoff.dsc.payload.has_permissions(caps.CapabilityPermission.EX))
        self.assertFalse(handoff.rsc.payload.has_permissions(caps.CapabilityPermission.EX))
        self.assertTrue(handoff.tvc.payload.has_permissions(caps.CapabilityPermission.EX))
        self.assertTrue(handoff.ddc.is_invalid)
        self.assertEqual(handoff.general_capability_tags, (False,) * 8)
        self.assertEqual(handoff.handoff_magic, firmware.ROM_HANDOFF_MAGIC)
        self.assertTrue(
            memory.overlaps_protected_range(
                handoff.protected_return_stack_base,
                handoff.protected_return_stack_cells,
            )
        )

    def test_tiny_rom_layout_validation_rejects_bad_platform_profile(self) -> None:
        bad_profile = replace(platform.TEST_PLATFORM_PROFILE, reset_vector=platform.RAM_BASE)

        issues = firmware.validate_tiny_rom_layout(bad_profile)

        self.assertIn("reset vector is not in a ROM region", "; ".join(issues))
        with self.assertRaises(firmware.TinyRomError):
            firmware.run_tiny_rom_initialization(profile=bad_profile)

    def test_stack_cursors_are_ram_bounded_and_publicly_aligned(self) -> None:
        handoff = firmware.run_tiny_rom_initialization().handoff
        ram = platform.TEST_PLATFORM_PROFILE.region_by_name("main_ram")

        for capability in (handoff.ksc, handoff.dsc, handoff.rsc):
            self.assertTrue(ram.range.contains_address(capability.payload.cursor))
            self.assertEqual(capability.payload.cursor % 4, 0)
            self.assertTrue(
                capability.payload.has_permissions(
                    caps.CapabilityPermission.LD
                    | caps.CapabilityPermission.ST
                    | caps.CapabilityPermission.LC
                    | caps.CapabilityPermission.SC
                    | caps.CapabilityPermission.SL
                )
            )

    def test_documentation_artifact_names_rom_handoff_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "tiny-rom.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I14-S01", text)
        self.assertIn("kernel handoff", text)
        self.assertIn("KRC", text)


if __name__ == "__main__":
    unittest.main()

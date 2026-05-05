"""I11-S01 conformance tests for program-image manifest boundaries."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import platform, program_image


def text_section(base: int = platform.RESET_VECTOR) -> program_image.ProgramImageSection:
    return program_image.ProgramImageSection.from_cells(
        name="text",
        region_name="boot_rom",
        base_cell=base,
        alignment_cells=2,
        payload_cells=(0x05B053, 0x000000),
        kind=program_image.ProgramImageSectionKind.TEXT,
    )


class ProgramImageManifestTests(unittest.TestCase):
    def test_reset_pcc_manifest_accepts_rom_text_and_ram_data(self) -> None:
        manifest = program_image.ProgramImageManifest(
            name="smoke",
            entry_cell=platform.RESET_VECTOR,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(
                text_section(),
                program_image.ProgramImageSection.from_cells(
                    name="data",
                    region_name="main_ram",
                    base_cell=platform.RAM_BASE,
                    alignment_cells=2,
                    payload_cells=(0x12, 0x34),
                    kind=program_image.ProgramImageSectionKind.DATA,
                ),
            ),
        )

        self.assertTrue(manifest.uses_reset_pcc)
        self.assertEqual(program_image.validate_program_image_manifest(manifest), ())
        self.assertIs(program_image.require_valid_program_image_manifest(manifest), manifest)

    def test_entry_source_and_slot_are_checked(self) -> None:
        wrong_reset_entry = program_image.ProgramImageManifest(
            name="bad-entry",
            entry_cell=platform.RESET_VECTOR + 1,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(text_section(),),
        )
        manifest_entry = replace(
            wrong_reset_entry,
            entry_source=program_image.EntryCapabilitySource.MANIFEST_ENTRY,
        )
        slot_one_entry = replace(manifest_entry, entry_slot=1)

        self.assertIn(
            "RESET_PCC entry source requires entry_cell",
            "; ".join(program_image.validate_program_image_manifest(wrong_reset_entry)),
        )
        self.assertEqual(program_image.validate_program_image_manifest(manifest_entry), ())
        self.assertIn(
            "entry must enter slot 0",
            "; ".join(program_image.validate_program_image_manifest(slot_one_entry)),
        )

    def test_sections_must_fit_loadable_regions_with_compatible_permissions(self) -> None:
        text_in_ram = replace(text_section(platform.RAM_BASE), region_name="main_ram")
        data_in_rom = program_image.ProgramImageSection.from_cells(
            name="data",
            region_name="boot_rom",
            base_cell=platform.ROM_BASE + 4,
            alignment_cells=2,
            payload_cells=(0x1, 0x2),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        device_section = program_image.ProgramImageSection.from_cells(
            name="device",
            region_name="platform_devices",
            base_cell=platform.DEVICE_BASE,
            alignment_cells=2,
            payload_cells=(0x1, 0x2),
            kind=program_image.ProgramImageSectionKind.RODATA,
        )
        outside_rom = program_image.ProgramImageSection.from_cells(
            name="outside",
            region_name="boot_rom",
            base_cell=platform.ROM_BASE + platform.ROM_CELLS - 1,
            alignment_cells=1,
            payload_cells=(0x1, 0x2),
            kind=program_image.ProgramImageSectionKind.TEXT,
        )

        manifest = program_image.ProgramImageManifest(
            name="bad-placement",
            entry_cell=platform.RESET_VECTOR,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(text_in_ram, data_in_rom, device_section, outside_rom),
        )
        issues = "; ".join(program_image.validate_program_image_manifest(manifest))

        self.assertIn("TEXT section 'text' must target an executable region", issues)
        self.assertIn("DATA section 'data' must target writable RAM", issues)
        self.assertIn("targets non-loadable region 'platform_devices'", issues)
        self.assertIn("section 'outside' does not fit in region 'boot_rom'", issues)

    def test_names_ranges_and_empty_sections_are_invalid_image_failures(self) -> None:
        duplicate = replace(text_section(platform.ROM_BASE + 4), cell_section=text_section().cell_section)
        overlap = program_image.ProgramImageSection.from_cells(
            name="overlap",
            region_name="boot_rom",
            base_cell=platform.RESET_VECTOR + 1,
            alignment_cells=1,
            payload_cells=(0x1, 0x2),
            kind=program_image.ProgramImageSectionKind.TEXT,
        )
        empty = program_image.ProgramImageSection.from_cells(
            name="empty",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=1,
            payload_cells=(),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        manifest = program_image.ProgramImageManifest(
            name="bad-shape",
            entry_cell=platform.RESET_VECTOR,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(text_section(), duplicate, overlap, empty),
        )
        issues = "; ".join(program_image.validate_program_image_manifest(manifest))

        self.assertIn("duplicate section name 'text'", issues)
        self.assertIn("sections 'text' and 'text' overlap", issues)
        self.assertIn("sections 'text' and 'overlap' overlap", issues)
        self.assertIn("section 'empty' must not be empty", issues)

    def test_tag_sidecar_is_limited_to_aligned_capdata_in_ram(self) -> None:
        capdata = program_image.ProgramImageSection.from_cells(
            name="captable",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=4,
            payload_cells=(0, 0, 0, 0),
            kind=program_image.ProgramImageSectionKind.CAPDATA,
            tag_policy=program_image.ProgramImageTagPolicy.TRUSTED_CAPABILITY_SIDECAR,
        )
        bad_capdata = program_image.ProgramImageSection.from_cells(
            name="bad-captable",
            region_name="main_ram",
            base_cell=platform.RAM_BASE + 2,
            alignment_cells=2,
            payload_cells=(0, 0, 0, 0),
            kind=program_image.ProgramImageSectionKind.CAPDATA,
            tag_policy=program_image.ProgramImageTagPolicy.TRUSTED_CAPABILITY_SIDECAR,
        )
        ordinary_data_sidecar = replace(
            capdata,
            cell_section=replace(capdata.cell_section, name="data-sidecar"),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        capdata_without_sidecar = replace(
            capdata,
            cell_section=replace(capdata.cell_section, name="missing-sidecar"),
            tag_policy=program_image.ProgramImageTagPolicy.UNTYPED_CELLS,
        )
        manifest = program_image.ProgramImageManifest(
            name="capdata",
            entry_cell=platform.RESET_VECTOR,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(text_section(), capdata),
        )

        self.assertTrue(capdata.uses_tag_sidecar)
        self.assertEqual(program_image.validate_program_image_manifest(manifest), ())

        issues = "; ".join(
            program_image.validate_program_image_manifest(
                replace(
                    manifest,
                    sections=(
                        text_section(),
                        bad_capdata,
                        ordinary_data_sidecar,
                        capdata_without_sidecar,
                    ),
                )
            )
        )
        self.assertIn("must start on a capability slot", issues)
        self.assertIn("only CAPDATA section 'data-sidecar' may request", issues)
        self.assertIn("CAPDATA section 'missing-sidecar' requires", issues)

    def test_invalid_manifest_can_be_rejected_as_one_exception(self) -> None:
        manifest = program_image.ProgramImageManifest(
            name="bad",
            entry_cell=platform.RAM_BASE,
            entry_source=program_image.EntryCapabilitySource.RESET_PCC,
            sections=(text_section(),),
        )

        with self.assertRaises(program_image.ProgramImageError) as raised:
            program_image.require_valid_program_image_manifest(manifest)

        self.assertIn("RESET_PCC entry source requires", str(raised.exception))
        self.assertIn("entry_cell must be covered", str(raised.exception))

    def test_documentation_artifact_names_loader_boundary(self) -> None:
        doc = ROOT / "docs" / "implementation" / "program-image-manifest.md"
        text = doc.read_text(encoding="utf-8")

        self.assertIn("Story: I11-S01", text)
        self.assertIn("I11-S02", text)
        self.assertIn("I11-S03", text)
        self.assertIn("Ordinary section payload cells never create valid capability tags", text)


if __name__ == "__main__":
    unittest.main()

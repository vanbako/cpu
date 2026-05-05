"""I11-S02 conformance tests for program-image loading."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import platform, program_image, serialization
from cpu_v01.memory import TaggedMemory


def text_section(payload_cells: tuple[int, ...] = (0x05B053, 0x000000)) -> program_image.ProgramImageSection:
    return program_image.ProgramImageSection.from_serialized_cells(
        name="text",
        region_name="boot_rom",
        base_cell=platform.RESET_VECTOR,
        alignment_cells=2,
        payload_octets=serialization.serialize_cells(payload_cells),
        kind=program_image.ProgramImageSectionKind.TEXT,
    )


def manifest_with(*sections: program_image.ProgramImageSection) -> program_image.ProgramImageManifest:
    return program_image.ProgramImageManifest(
        name="loadable",
        entry_cell=platform.RESET_VECTOR,
        entry_source=program_image.EntryCapabilitySource.RESET_PCC,
        sections=(text_section(), *sections),
    )


def capability(cursor: int, *, tag: bool = True) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0, 1 << 48),
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability(payload, tag)


class ProgramImageLoaderTests(unittest.TestCase):
    def test_little_endian_serialized_cells_load_into_rom_and_ram(self) -> None:
        data = program_image.ProgramImageSection.from_serialized_cells(
            name="data",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=2,
            payload_octets=serialization.serialize_cells((0x123456, 0xABCDEF)),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        memory = TaggedMemory()

        report = program_image.load_program_image(manifest_with(data), memory)

        self.assertEqual(report.sections_loaded, 2)
        self.assertEqual(report.cells_loaded, 4)
        self.assertEqual(report.sidecar_slots_loaded, 0)
        self.assertEqual(memory.read_cell(platform.RESET_VECTOR), 0x05B053)
        self.assertEqual(memory.read_cell(platform.RESET_VECTOR + 1), 0x000000)
        self.assertEqual(memory.read_cell(platform.RAM_BASE), 0x123456)
        self.assertEqual(memory.read_cell(platform.RAM_BASE + 1), 0xABCDEF)

    def test_partial_serialized_cells_and_bad_section_alignment_fail(self) -> None:
        with self.assertRaises(serialization.SerializationError):
            program_image.ProgramImageSection.from_serialized_cells(
                name="partial",
                region_name="main_ram",
                base_cell=platform.RAM_BASE,
                alignment_cells=2,
                payload_octets=b"\x00",
                kind=program_image.ProgramImageSectionKind.DATA,
            )

        with self.assertRaises(serialization.SerializationError):
            program_image.ProgramImageSection.from_serialized_cells(
                name="misaligned",
                region_name="main_ram",
                base_cell=platform.RAM_BASE + 1,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells((0, 0)),
                kind=program_image.ProgramImageSectionKind.DATA,
            )

    def test_ordinary_image_load_clears_existing_capability_tags(self) -> None:
        data = program_image.ProgramImageSection.from_serialized_cells(
            name="data",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=4,
            payload_octets=serialization.serialize_cells((1, 2, 3, 4)),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        memory = TaggedMemory()
        memory.csc(platform.RAM_BASE, capability(0x1234))
        self.assertTrue(memory.capability_tag(platform.RAM_BASE))

        program_image.load_program_image(manifest_with(data), memory)

        self.assertEqual(
            tuple(memory.read_cell(platform.RAM_BASE + offset) for offset in range(4)),
            (1, 2, 3, 4),
        )
        self.assertFalse(memory.capability_tag(platform.RAM_BASE))

    def test_explicit_sidecar_installs_capability_payload_and_tag_after_cell_load(self) -> None:
        cap = capability(0x5555, tag=True)
        capdata = program_image.ProgramImageSection.from_serialized_cells(
            name="captable",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=4,
            payload_octets=serialization.serialize_cells((0, 0, 0, 0)),
            kind=program_image.ProgramImageSectionKind.CAPDATA,
            tag_policy=program_image.ProgramImageTagPolicy.TRUSTED_CAPABILITY_SIDECAR,
        )
        memory = TaggedMemory()
        sidecar = program_image.CapabilitySidecarEntry("captable", platform.RAM_BASE, cap)

        report = program_image.load_program_image(manifest_with(capdata), memory, sidecars=(sidecar,))

        self.assertEqual(report.sidecar_slots_loaded, 1)
        self.assertEqual(memory.clc(platform.RAM_BASE), cap)
        self.assertTrue(memory.capability_tag(platform.RAM_BASE))

    def test_capdata_requires_explicit_sidecar_for_every_slot(self) -> None:
        capdata = program_image.ProgramImageSection.from_serialized_cells(
            name="captable",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=4,
            payload_octets=serialization.serialize_cells((0, 0, 0, 0, 0, 0, 0, 0)),
            kind=program_image.ProgramImageSectionKind.CAPDATA,
            tag_policy=program_image.ProgramImageTagPolicy.TRUSTED_CAPABILITY_SIDECAR,
        )
        manifest = manifest_with(capdata)
        first_slot = program_image.CapabilitySidecarEntry("captable", platform.RAM_BASE, capability(0x1))
        wrong_section = program_image.CapabilitySidecarEntry("text", platform.RESET_VECTOR, capability(0x2))
        misaligned = program_image.CapabilitySidecarEntry("captable", platform.RAM_BASE + 2, capability(0x3))
        outside = program_image.CapabilitySidecarEntry("captable", platform.RAM_BASE + 8, capability(0x4))

        issues = "; ".join(
            program_image.validate_program_image_load(
                manifest,
                TaggedMemory(),
                sidecars=(first_slot, wrong_section, misaligned, outside),
            )
        )

        self.assertIn("section 'captable' is missing sidecar slots", issues)
        self.assertIn("sidecar targets section 'text' without sidecar policy", issues)
        self.assertIn("is not capability-slot aligned", issues)
        self.assertIn("is outside section 'captable'", issues)

    def test_protected_region_rejection_happens_before_any_image_write(self) -> None:
        data = program_image.ProgramImageSection.from_serialized_cells(
            name="data",
            region_name="main_ram",
            base_cell=platform.RAM_BASE,
            alignment_cells=2,
            payload_octets=serialization.serialize_cells((0xAAAAAA, 0xBBBBBB)),
            kind=program_image.ProgramImageSectionKind.DATA,
        )
        memory = TaggedMemory()
        memory.write_cells(platform.RAM_BASE, (0x111111, 0x222222))
        memory.protect_range(platform.RAM_BASE, 2)

        with self.assertRaises(program_image.ProgramImageError) as raised:
            program_image.load_program_image(manifest_with(data), memory)

        self.assertIn("overlaps protected memory", str(raised.exception))
        self.assertEqual(memory.read_cell(platform.RAM_BASE), 0x111111)
        self.assertEqual(memory.read_cell(platform.RAM_BASE + 1), 0x222222)

    def test_invalid_manifest_rejects_load_without_writes(self) -> None:
        bad_manifest = replace(manifest_with(), entry_cell=platform.RAM_BASE)
        memory = TaggedMemory()

        with self.assertRaises(program_image.ProgramImageError):
            program_image.load_program_image(bad_manifest, memory)

        self.assertEqual(memory.read_cell(platform.RESET_VECTOR), 0)

    def test_documentation_artifact_names_tag_and_protected_storage_boundaries(self) -> None:
        doc = ROOT / "docs" / "implementation" / "program-image-loader.md"
        text = doc.read_text(encoding="utf-8")

        self.assertIn("Story: I11-S02", text)
        self.assertIn("Serialized section octets never fabricate valid capability tags", text)
        self.assertIn("overlaps `TaggedMemory` protected storage", text)


if __name__ == "__main__":
    unittest.main()

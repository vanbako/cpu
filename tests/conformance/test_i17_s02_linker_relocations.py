"""I17-S02 conformance tests for linker relocation fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly, linker, object_metadata as obj, state


def metadata(
    name: str = "main",
    *,
    text_cells: int = 3,
    data_cells: int = 2,
) -> obj.RelocatableObjectMetadata:
    return obj.RelocatableObjectMetadata(
        name=name,
        sections=(
            obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, text_cells),
            obj.ObjectSection("data", obj.ObjectSectionKind.DATA, 2, data_cells),
        ),
        symbols=(
            obj.ObjectSymbol(
                "_start",
                "text",
                0,
                obj.ObjectSymbolKind.ENTRY,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "target",
                "text",
                text_cells - 1,
                obj.ObjectSymbolKind.FUNCTION,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "data_word",
                "data",
                0,
                obj.ObjectSymbolKind.OBJECT,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
        ),
        abi_attributes=(
            obj.AbiAttribute.CELL_ADDRESSED,
            obj.AbiAttribute.SLOT_AWARE_PCC,
            obj.AbiAttribute.PURE_CAPABILITY,
        ),
    )


def linker_object(name: str = "main") -> linker.LinkerObject:
    return linker.LinkerObject(
        metadata(name),
        section_payloads=(
            linker.SectionPayload(
                "text",
                (
                    assembly.assemble_line("BRA 0").cells[0],
                    assembly.assemble_line("Bcc EQ, 0").cells[0],
                    assembly.assemble_line("CALL 0").cells[0],
                ),
            ),
            linker.SectionPayload("data", (0, 0)),
        ),
        relocations=(
            linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "target"),
            linker.Relocation("text", 1, linker.RelocationKind.CONDITIONAL_TARGET12, "target"),
            linker.Relocation("data", 0, linker.RelocationKind.ABSOLUTE_CELL48, "target"),
        ),
    )


class LinkerRelocationFixtureTests(unittest.TestCase):
    def test_linker_places_sections_and_applies_branch_call_and_data_relocations(self) -> None:
        image = linker.link_objects((linker_object(),), base_cell=0x0200)
        text = image.section_by_name("main", "text")
        data = image.section_by_name("main", "data")
        target = image.symbol_by_name("target")

        self.assertEqual(text.base_cell, 0x0200)
        self.assertEqual(data.base_cell, 0x0204)
        self.assertEqual(target.cell_address, 0x0202)
        self.assertEqual(target.slot, state.SLOT_0)
        self.assertEqual(text.payload_cells[0], assembly.assemble_line("BRA 0x202").cells[0])
        self.assertEqual(text.payload_cells[1], assembly.assemble_line("Bcc EQ, 0x202").cells[0])
        self.assertEqual(data.payload_cells, (0x0202, 0x000000))

    def test_section_placement_respects_alignment_constraints(self) -> None:
        fixture = linker.LinkerObject(
            obj.RelocatableObjectMetadata(
                name="aligned",
                sections=(
                    obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 3),
                    obj.ObjectSection(
                        "captable",
                        obj.ObjectSectionKind.CAPDATA,
                        4,
                        4,
                        obj.CapabilitySidecarProvenance.TRUSTED_LOADER,
                    ),
                ),
                symbols=(
                    obj.ObjectSymbol("_start", "text", 0, obj.ObjectSymbolKind.ENTRY),
                    obj.ObjectSymbol(
                        "root_cap",
                        "captable",
                        0,
                        obj.ObjectSymbolKind.CAPABILITY_OBJECT,
                    ),
                ),
                abi_attributes=(
                    obj.AbiAttribute.CELL_ADDRESSED,
                    obj.AbiAttribute.SLOT_AWARE_PCC,
                    obj.AbiAttribute.PURE_CAPABILITY,
                    obj.AbiAttribute.CAPABILITY_TAG_SIDECARS,
                ),
            ),
            section_payloads=(
                linker.SectionPayload("text", (0, 0, 0)),
                linker.SectionPayload("captable", (0, 0, 0, 0)),
            ),
        )

        image = linker.link_objects((fixture,), base_cell=0x1000)

        self.assertEqual(image.section_by_name("aligned", "text").base_cell, 0x1000)
        self.assertEqual(image.section_by_name("aligned", "captable").base_cell, 0x1004)

    def test_validation_reports_payload_duplicate_and_section_failures(self) -> None:
        fixture = linker.LinkerObject(
            metadata(),
            section_payloads=(
                linker.SectionPayload("text", (0, 0, 0)),
                linker.SectionPayload("text", (0, 0, 0)),
                linker.SectionPayload("extra", (0,)),
            ),
            relocations=(linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "missing"),),
        )

        issues = "; ".join(linker.validate_linker_inputs((fixture,)))

        self.assertIn("duplicate payload for section main:text", issues)
        self.assertIn("payload targets unknown section main:extra", issues)
        self.assertIn("missing payload for section main:data", issues)
        self.assertNotIn("undefined symbol 'missing' in main", issues)

    def test_validation_reports_undefined_symbol_failure(self) -> None:
        fixture = linker.LinkerObject(
            metadata(),
            section_payloads=(
                linker.SectionPayload("text", (assembly.assemble_line("BRA 0").cells[0], 0, 0)),
                linker.SectionPayload("data", (0, 0)),
            ),
            relocations=(linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "missing"),),
        )

        issues = "; ".join(linker.validate_linker_inputs((fixture,)))

        self.assertIn("undefined symbol 'missing' in main", issues)

    def test_duplicate_exported_symbols_are_rejected(self) -> None:
        left = linker_object("left")
        right = linker_object("right")

        issues = "; ".join(linker.validate_linker_inputs((left, right)))

        self.assertIn("duplicate exported symbol '_start'", issues)
        self.assertIn("duplicate exported symbol 'target'", issues)

    def test_relocation_overflow_and_slot_mismatch_are_rejected(self) -> None:
        slot_object = linker.LinkerObject(
            obj.RelocatableObjectMetadata(
                name="slot",
                sections=(obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 1),),
                symbols=(
                    obj.ObjectSymbol("_start", "text", 0, obj.ObjectSymbolKind.ENTRY),
                    obj.ObjectSymbol(
                        "slot1",
                        "text",
                        0,
                        obj.ObjectSymbolKind.FUNCTION,
                        slot=state.SLOT_1,
                    ),
                ),
                abi_attributes=(
                    obj.AbiAttribute.CELL_ADDRESSED,
                    obj.AbiAttribute.SLOT_AWARE_PCC,
                    obj.AbiAttribute.PURE_CAPABILITY,
                ),
            ),
            section_payloads=(
                linker.SectionPayload("text", (assembly.assemble_line("BRA 0").cells[0],)),
            ),
            relocations=(linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "slot1"),),
        )
        overflow_object = linker_object("overflow")

        slot_issues = "; ".join(linker.validate_linker_inputs((slot_object,)))
        overflow_issues = "; ".join(linker.validate_linker_inputs((overflow_object,), base_cell=0x10000))

        self.assertIn("DIRECT_TARGET16 cannot encode slot 1 target 'slot1'", slot_issues)
        self.assertIn("DIRECT_TARGET16 relocation to 'target' overflows 16 bits", overflow_issues)

    def test_invalid_link_inputs_raise_one_linker_exception(self) -> None:
        fixture = linker.LinkerObject(
            metadata(),
            section_payloads=(
                linker.SectionPayload("text", (assembly.assemble_line("BRA 0").cells[0], 0, 0)),
                linker.SectionPayload("data", (0, 0)),
            ),
            relocations=(linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "missing"),),
        )

        with self.assertRaises(linker.LinkerError) as raised:
            linker.link_objects((fixture,))

        self.assertIn("undefined symbol 'missing'", str(raised.exception))

    def test_documentation_artifact_names_relocation_fixture_boundaries(self) -> None:
        text = (ROOT / "docs" / "implementation" / "linker-relocation-fixtures.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I17-S02", text)
        self.assertIn("section placement", text)
        self.assertIn("DIRECT_TARGET16", text)
        self.assertIn("ABSOLUTE_CELL48", text)


if __name__ == "__main__":
    unittest.main()

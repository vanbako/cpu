"""I17-S01 conformance tests for relocatable object metadata."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import object_metadata as obj
from cpu_v01 import state


def valid_object() -> obj.RelocatableObjectMetadata:
    return obj.RelocatableObjectMetadata(
        name="toolchain-smoke",
        sections=(
            obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 4),
            obj.ObjectSection("data", obj.ObjectSectionKind.DATA, 2, 2),
            obj.ObjectSection(
                "captable",
                obj.ObjectSectionKind.CAPDATA,
                4,
                4,
                obj.CapabilitySidecarProvenance.TRUSTED_LOADER,
            ),
        ),
        symbols=(
            obj.ObjectSymbol(
                "_start",
                "text",
                0,
                obj.ObjectSymbolKind.ENTRY,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol("slot1_helper", "text", 0, obj.ObjectSymbolKind.FUNCTION, slot=state.SLOT_1),
            obj.ObjectSymbol("global_value", "data", 0, obj.ObjectSymbolKind.OBJECT),
            obj.ObjectSymbol("root_cap", "captable", 0, obj.ObjectSymbolKind.CAPABILITY_OBJECT),
        ),
        abi_attributes=(
            obj.AbiAttribute.CELL_ADDRESSED,
            obj.AbiAttribute.SLOT_AWARE_PCC,
            obj.AbiAttribute.PURE_CAPABILITY,
            obj.AbiAttribute.CAPABILITY_TAG_SIDECARS,
        ),
    )


class RelocatableObjectMetadataTests(unittest.TestCase):
    def test_valid_metadata_records_sections_symbols_and_abi_attributes(self) -> None:
        metadata = valid_object()

        self.assertEqual(obj.validate_relocatable_object_metadata(metadata), ())
        self.assertIs(obj.require_valid_relocatable_object_metadata(metadata), metadata)
        self.assertEqual(metadata.section_by_name("captable").alignment_cells, 4)
        self.assertEqual(metadata.symbol_by_name("slot1_helper").location_label, "text+0:slot1")

        encoded = metadata.as_dict()
        self.assertEqual(encoded["abi_attributes"][0], "CELL_ADDRESSED")
        self.assertEqual(encoded["sections"][2]["sidecar_provenance"], "TRUSTED_LOADER")
        self.assertEqual(encoded["symbols"][1]["slot"], 1)

    def test_validation_reports_duplicate_and_missing_metadata_deterministically(self) -> None:
        metadata = valid_object()
        bad = replace(
            metadata,
            sections=(
                *metadata.sections,
                replace(metadata.sections[0], size_cells=2),
            ),
            symbols=(
                *metadata.symbols,
                obj.ObjectSymbol("_start", "missing", 0, obj.ObjectSymbolKind.FUNCTION),
            ),
            abi_attributes=(obj.AbiAttribute.CELL_ADDRESSED,),
        )

        issues = obj.validate_relocatable_object_metadata(bad)

        self.assertIn("object ABI attributes must include PURE_CAPABILITY", issues)
        self.assertIn("object ABI attributes must include SLOT_AWARE_PCC", issues)
        self.assertIn("duplicate section name 'text'", issues)
        self.assertIn("duplicate symbol name '_start'", issues)
        self.assertIn("symbol '_start' targets unknown section 'missing'", issues)

    def test_capability_sidecar_provenance_is_limited_to_slot_aligned_capdata(self) -> None:
        metadata = valid_object()
        bad = replace(
            metadata,
            sections=(
                obj.ObjectSection("captable", obj.ObjectSectionKind.CAPDATA, 2, 6),
                obj.ObjectSection(
                    "data",
                    obj.ObjectSectionKind.DATA,
                    2,
                    2,
                    obj.CapabilitySidecarProvenance.TRUSTED_LOADER,
                ),
            ),
            symbols=(),
        )

        issues = "; ".join(obj.validate_relocatable_object_metadata(bad))

        self.assertIn("must declare TRUSTED_LOADER sidecar provenance", issues)
        self.assertIn("alignment must preserve capability slots", issues)
        self.assertIn("must cover whole capability slots", issues)
        self.assertIn("non-CAPDATA section 'data' must not declare", issues)

    def test_symbol_kinds_and_slot_locations_match_section_kind(self) -> None:
        metadata = valid_object()
        bad = replace(
            metadata,
            symbols=(
                obj.ObjectSymbol("too_far", "text", 4, obj.ObjectSymbolKind.FUNCTION),
                obj.ObjectSymbol("bad_slot", "data", 0, obj.ObjectSymbolKind.OBJECT, slot=state.SLOT_1),
                obj.ObjectSymbol("bad_function", "data", 0, obj.ObjectSymbolKind.FUNCTION),
                obj.ObjectSymbol("bad_object", "text", 0, obj.ObjectSymbolKind.OBJECT),
                obj.ObjectSymbol("bad_cap", "data", 0, obj.ObjectSymbolKind.CAPABILITY_OBJECT),
                obj.ObjectSymbol("bad_section", "text", 1, obj.ObjectSymbolKind.SECTION),
            ),
        )

        issues = "; ".join(obj.validate_relocatable_object_metadata(bad))

        self.assertIn("symbol 'too_far' is outside section 'text'", issues)
        self.assertIn("symbol 'bad_slot' uses slot 1 outside a TEXT section", issues)
        self.assertIn("FUNCTION symbol 'bad_function' must target TEXT", issues)
        self.assertIn("OBJECT symbol 'bad_object' must target DATA or RODATA", issues)
        self.assertIn("CAPABILITY_OBJECT symbol 'bad_cap' must target CAPDATA", issues)
        self.assertIn("section symbol 'bad_section' must point at section slot 0", issues)

    def test_invalid_metadata_can_be_rejected_as_one_exception(self) -> None:
        metadata = replace(valid_object(), abi_attributes=())

        with self.assertRaises(obj.RelocatableObjectError) as raised:
            obj.require_valid_relocatable_object_metadata(metadata)

        self.assertIn("CELL_ADDRESSED", str(raised.exception))
        self.assertIn("PURE_CAPABILITY", str(raised.exception))

    def test_documentation_artifact_names_profile_boundaries(self) -> None:
        text = (ROOT / "docs" / "implementation" / "relocatable-object-metadata.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I17-S01", text)
        self.assertIn("cell-addressed", text)
        self.assertIn("slot-aware symbols", text)
        self.assertIn("capability sidecar provenance", text)


if __name__ == "__main__":
    unittest.main()

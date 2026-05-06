"""I17-S03 conformance tests for debug metadata fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly, debug_abi, debug_metadata, linker, object_metadata as obj, state


def debug_object_metadata() -> obj.RelocatableObjectMetadata:
    return obj.RelocatableObjectMetadata(
        name="dbg",
        sections=(
            obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 2),
            obj.ObjectSection("data", obj.ObjectSectionKind.DATA, 2, 2),
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
                "cleanup",
                "text",
                1,
                obj.ObjectSymbolKind.FUNCTION,
                slot=state.SLOT_1,
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
            obj.AbiAttribute.PROTECTED_RETURN_STACK,
        ),
    )


def linked_image() -> linker.LinkedImage:
    packed_ret_brk = assembly.assemble_program(("RET", "BRK"))[0]
    fixture = linker.LinkerObject(
        debug_object_metadata(),
        section_payloads=(
            linker.SectionPayload(
                "text",
                (
                    assembly.assemble_line("BRA 0").cells[0],
                    packed_ret_brk,
                ),
            ),
            linker.SectionPayload("data", (0, 0)),
        ),
    )
    return linker.link_objects((fixture,), base_cell=0x0200)


def debug_object() -> debug_metadata.DebugObject:
    return debug_metadata.DebugObject(
        "dbg",
        source_lines=(
            debug_metadata.SourceLine("text", 0, state.SLOT_0, "kernel/main.cv01", 10, source_text="BRA cleanup"),
            debug_metadata.SourceLine("text", 1, state.SLOT_0, "kernel/main.cv01", 11, source_text="RET"),
            debug_metadata.SourceLine("text", 1, state.SLOT_1, "kernel/main.cv01", 12, source_text="BRK"),
        ),
        function_ranges=(
            debug_metadata.FunctionRange("_start", 2, "kernel/main.cv01"),
            debug_metadata.FunctionRange("cleanup", 1, "kernel/main.cv01"),
        ),
    )


class DebugMetadataFixtureTests(unittest.TestCase):
    def test_debug_metadata_maps_pcc_cell_and_slot_to_source_and_function(self) -> None:
        image = linked_image()
        metadata = debug_metadata.emit_debug_metadata(image, (debug_object(),))

        start_line = metadata.line_for_pcc(0x0200, state.SLOT_0)
        cleanup_line = metadata.line_for_pcc(0x0201, state.SLOT_1)
        function = metadata.function_for_pcc(0x0201, state.SLOT_0)
        cleanup = metadata.function_for_pcc(0x0201, state.SLOT_1)

        self.assertIsNotNone(start_line)
        self.assertEqual(start_line.source_label, "kernel/main.cv01:10:1")
        self.assertIsNotNone(cleanup_line)
        self.assertEqual(cleanup_line.source_text, "BRK")
        self.assertIsNotNone(function)
        self.assertEqual(function.name, "_start")
        self.assertIsNotNone(cleanup)
        self.assertEqual(cleanup.name, "cleanup")

    def test_register_metadata_includes_abi_roles_tags_slots_and_unwind_hints(self) -> None:
        metadata = debug_metadata.emit_debug_metadata(linked_image(), (debug_object(),))

        d0 = metadata.register_by_name("d0")
        c0 = metadata.register_by_name("C0")
        pcc = metadata.register_by_name("PCC")
        replace = metadata.unwind_hint(debug_abi.DebugUnwindOperation.REPLACE)
        drop = metadata.unwind_hint("DROP")

        self.assertIn(debug_metadata.RegisterAbiRole.INTEGER_ARGUMENT, d0.abi_roles)
        self.assertIn(debug_metadata.RegisterAbiRole.INTEGER_RETURN, d0.abi_roles)
        self.assertIn(debug_metadata.RegisterAbiRole.SYSCALL_SERVICE, d0.abi_roles)
        self.assertFalse(d0.tag_visible)
        self.assertIn(debug_metadata.RegisterAbiRole.CAPABILITY_ARGUMENT, c0.abi_roles)
        self.assertIn(debug_metadata.RegisterAbiRole.CAPABILITY_RETURN, c0.abi_roles)
        self.assertTrue(c0.tag_visible)
        self.assertFalse(c0.slot_visible)
        self.assertTrue(pcc.tag_visible)
        self.assertTrue(pcc.slot_visible)
        self.assertIn(debug_metadata.RegisterAbiRole.CONTEXT_SWITCH, pcc.abi_roles)
        self.assertTrue(replace.writes_return_slot)
        self.assertTrue(replace.requires_valid_return_capability)
        self.assertTrue(replace.atomic_payload_tag)
        self.assertEqual(replace.entry_cells, 4)
        self.assertTrue(drop.updates_rsc_cursor)

    def test_symbolic_disassembly_prints_matching_locations(self) -> None:
        image = linked_image()
        metadata = debug_metadata.emit_debug_metadata(image, (debug_object(),))

        lines = debug_metadata.disassemble_linked_section(image, "dbg", "text", metadata)

        self.assertIn("0x0200:slot0 <_start> kernel/main.cv01:10:1: BRA 0x0", lines)
        self.assertIn("0x0201:slot0 <_start+0x1> kernel/main.cv01:11:1: RET", lines)
        self.assertIn("0x0201:slot1 <cleanup> kernel/main.cv01:12:1: BRK", lines)

    def test_validation_rejects_bad_line_and_function_metadata(self) -> None:
        bad = debug_metadata.DebugObject(
            "dbg",
            source_lines=(
                debug_metadata.SourceLine("text", 3, state.SLOT_0, "bad.cv01", 1),
                debug_metadata.SourceLine("data", 0, state.SLOT_1, "bad.cv01", 2),
            ),
            function_ranges=(
                debug_metadata.FunctionRange("missing", 1),
                debug_metadata.FunctionRange("data_word", 1),
                debug_metadata.FunctionRange("_start", 3),
            ),
        )

        issues = "; ".join(debug_metadata.validate_debug_metadata(linked_image(), (bad,)))

        self.assertIn("bad.cv01:1 targets cell 3 outside dbg:text", issues)
        self.assertIn("bad.cv01:2 uses slot 1 outside TEXT", issues)
        self.assertIn("function range references unknown symbol dbg:missing", issues)
        self.assertIn("function range dbg:data_word targets OBJECT symbol", issues)
        self.assertIn("function range dbg:_start exceeds section text", issues)
        with self.assertRaises(debug_metadata.DebugMetadataError):
            debug_metadata.emit_debug_metadata(linked_image(), (bad,))

    def test_documentation_artifact_names_debug_metadata_boundaries(self) -> None:
        text = (ROOT / "docs" / "implementation" / "debug-metadata.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I17-S03", text)
        self.assertIn("PCC cell plus slot", text)
        self.assertIn("protected return-stack unwind", text)
        self.assertIn("symbolic disassembly", text)


if __name__ == "__main__":
    unittest.main()

"""I26-S01 conformance tests for the FPGA program-image manifest."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_program_manifest.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_program_manifest, platform, smoke, toolchain_corpus


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_program_manifest_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaProgramManifestTests(unittest.TestCase):
    def test_manifest_self_validation_passes(self) -> None:
        self.assertEqual(fpga_program_manifest.validate_fpga_program_manifest(ROOT), ())

    def test_profile_names_dependencies_formats_and_entries(self) -> None:
        profile = fpga_program_manifest.fpga_program_manifest_profile()

        self.assertEqual(profile.story, "I26-S01")
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.fpga_top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.source_corpus_tool, "python tools\\toolchain_corpus.py --check")
        self.assertEqual(profile.memory_adapter_tool, "python tools\\fpga_memory_adapters.py --check")
        self.assertEqual(profile.rom_format, "hex24-cells-v1")
        self.assertEqual(profile.data_format, "hex24-cells-v1")
        self.assertEqual(profile.tag_format, "hex1-tags-v1")
        self.assertEqual(
            {entry.program_id for entry in profile.entries},
            {
                "reset_smoke.reset_to_trap_fpga",
                "syscall_trap.sys_pause_iret_fpga",
                "relocation.branch_call_data_fpga",
            },
        )

    def test_reset_smoke_entry_places_main_and_trap_handler_in_instruction_rom(self) -> None:
        entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(
            "reset_smoke.reset_to_trap_fpga"
        )
        rom = entry.materialized_cells("instruction_rom")
        data = entry.materialized_cells("data_ram")
        tags = entry.materialized_cells("tag_ram")
        source = toolchain_corpus.toolchain_case_by_id("reset_smoke.reset_to_trap_image")
        source_sections = {section.name: section for section in source.binary_sections}

        reset_offset = platform.RESET_VECTOR - platform.RESET_VECTOR
        handler_offset = smoke.SMOKE_HANDLER_CELL - platform.RESET_VECTOR

        self.assertEqual(
            rom[reset_offset : reset_offset + len(source_sections["main"].payload_cells)],
            source_sections["main"].payload_cells,
        )
        self.assertEqual(
            rom[handler_offset : handler_offset + len(source_sections["trap_handler"].payload_cells)],
            source_sections["trap_handler"].payload_cells,
        )
        self.assertTrue(all(value == 0 for value in data))
        self.assertTrue(all(value == 0 for value in tags))
        self.assertEqual(entry.entry_capability.source, "RESET_PCC")
        self.assertEqual(entry.entry_capability.slot, 0)
        self.assertEqual(entry.entry_cell, platform.RESET_VECTOR)

    def test_relocation_entry_binds_text_to_rom_and_data_to_data_ram(self) -> None:
        entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(
            "relocation.branch_call_data_fpga"
        )
        sections = {section.source_section: section for section in entry.sections}
        images = {image.memory_name: image for image in entry.memory_images()}

        self.assertIn("reloc:text", sections)
        self.assertIn("reloc:data", sections)
        self.assertEqual(sections["reloc:text"].target_memory, "instruction_rom")
        self.assertEqual(sections["reloc:data"].target_memory, "data_ram")
        self.assertEqual(sections["reloc:data"].base_cell, platform.RAM_BASE)
        self.assertEqual(images["instruction_rom"].format_name, "hex24-cells-v1")
        self.assertEqual(images["data_ram"].format_name, "hex24-cells-v1")
        self.assertEqual(images["tag_ram"].format_name, "hex1-tags-v1")
        for image in images.values():
            self.assertEqual(len(image.image_sha256), 64)
            self.assertTrue(image.artifact_path.as_posix().startswith("build/fpga/programs/"))
        self.assertEqual(len(entry.image_sha256), 64)

    def test_materialized_images_use_stable_fill_and_hash_contracts(self) -> None:
        entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(
            "syscall_trap.sys_pause_iret_fpga"
        )
        rom = entry.materialized_cells("instruction_rom")
        data = entry.materialized_cells("data_ram")
        tags = entry.materialized_cells("tag_ram")
        images = {image.memory_name: image for image in entry.memory_images()}

        self.assertIn(0x05B05B, rom)
        self.assertEqual(images["instruction_rom"].fill_value, 0x05B05B)
        self.assertTrue(all(value == 0 for value in data))
        self.assertTrue(all(value == 0 for value in tags))
        self.assertEqual(images["data_ram"].fill_value, 0)
        self.assertEqual(images["tag_ram"].fill_value, 0)

    def test_cli_validates_lists_and_prints_entry_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA program manifest issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("reset_smoke.reset_to_trap_fpga", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--entry", "relocation.branch_call_data_fpga"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["program_id"], "relocation.branch_call_data_fpga")
        self.assertIn("memory_images", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I26-S01")
        self.assertIn("entries", parsed)

    def test_documentation_names_command_fields_entries_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-program-image-manifest.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I26-S01", text)
        self.assertIn("python tools\\fpga_program_manifest.py --check", text)
        self.assertIn("python tools\\toolchain_corpus.py --check", text)
        self.assertIn("python tools\\fpga_memory_adapters.py --check", text)
        self.assertIn("build/fpga/programs", text)
        self.assertIn("entry capability", text)
        self.assertIn("image_sha256", text)
        self.assertIn("instruction_rom", text)
        self.assertIn("data_ram", text)
        self.assertIn("tag_ram", text)
        self.assertIn("hex24-cells-v1", text)
        self.assertIn("hex1-tags-v1", text)
        self.assertIn("reset_smoke.reset_to_trap_fpga", text)
        self.assertIn("syscall_trap.sys_pause_iret_fpga", text)
        self.assertIn("relocation.branch_call_data_fpga", text)
        self.assertIn("I26-S02", text)
        self.assertIn("I26-S03", text)
        self.assertIn("I26-S05", text)


if __name__ == "__main__":
    unittest.main()

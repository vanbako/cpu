"""I26-S02 conformance tests for FPGA BRAM image generation."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_bram_images.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_bram_images, fpga_program_manifest, platform, smoke, toolchain_corpus


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_bram_images_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaBramImageTests(unittest.TestCase):
    def test_bram_image_generator_self_validation_passes(self) -> None:
        self.assertEqual(fpga_bram_images.validate_fpga_bram_images(ROOT), ())

    def test_bundles_cover_manifest_entries_and_hashes_match(self) -> None:
        manifest_entries = {
            entry.program_id
            for entry in fpga_program_manifest.fpga_program_manifest_profile().entries
        }
        bundles = fpga_bram_images.fpga_bram_image_bundles()

        self.assertEqual({bundle.program_id for bundle in bundles}, manifest_entries)
        for bundle in bundles:
            self.assertTrue(bundle.passed)
            self.assertEqual(len(bundle.manifest_image_sha256), 64)
            artifacts = {artifact.memory_name: artifact for artifact in bundle.artifacts}
            self.assertEqual(set(artifacts), {"instruction_rom", "data_ram", "tag_ram"})
            for artifact in artifacts.values():
                self.assertTrue(artifact.matches_manifest)
                self.assertEqual(len(artifact.image_sha256), 64)

    def test_reset_smoke_rendered_rom_matches_manifest_cells(self) -> None:
        program_id = "reset_smoke.reset_to_trap_fpga"
        entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(program_id)
        rom_lines = fpga_bram_images.render_bram_image(program_id, "instruction_rom").splitlines()
        data_lines = fpga_bram_images.render_bram_image(program_id, "data_ram").splitlines()
        tag_lines = fpga_bram_images.render_bram_image(program_id, "tag_ram").splitlines()
        source = toolchain_corpus.toolchain_case_by_id("reset_smoke.reset_to_trap_image")
        source_sections = {section.name: section for section in source.binary_sections}
        handler_offset = smoke.SMOKE_HANDLER_CELL - platform.RESET_VECTOR

        self.assertEqual(len(rom_lines), 1024)
        self.assertEqual(len(data_lines), 4096)
        self.assertEqual(len(tag_lines), 4096)
        self.assertEqual(rom_lines[0], f"{source_sections['main'].payload_cells[0]:06x}")
        self.assertEqual(
            rom_lines[handler_offset],
            f"{source_sections['trap_handler'].payload_cells[0]:06x}",
        )
        self.assertEqual(tuple(int(line, 16) for line in rom_lines), entry.materialized_cells("instruction_rom"))
        self.assertTrue(all(line == "000000" for line in data_lines))
        self.assertTrue(all(line == "0" for line in tag_lines))

    def test_relocation_rendered_data_matches_manifest_cells(self) -> None:
        program_id = "relocation.branch_call_data_fpga"
        entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(program_id)
        data_lines = fpga_bram_images.render_bram_image(program_id, "data_ram").splitlines()
        expected = entry.materialized_cells("data_ram")

        self.assertEqual(tuple(int(line, 16) for line in data_lines), expected)
        self.assertNotEqual(data_lines[0], "000000")
        self.assertTrue(all(line == "000000" for line in data_lines[2:]))

    def test_write_and_verify_images_under_explicit_output_root(self) -> None:
        program_id = "syscall_trap.sys_pause_iret_fpga"
        with tempfile.TemporaryDirectory(prefix="tmp_i26_s02_", dir=ROOT) as tmp:
            output_root = Path(tmp)
            report = fpga_bram_images.write_bram_images(output_root, program_id)

            self.assertTrue(report.passed)
            self.assertEqual(len(report.files_written), 3)
            self.assertEqual(fpga_bram_images.verify_written_bram_images(output_root, program_id), ())
            for path in report.files_written:
                self.assertTrue(path.exists())
                self.assertTrue(path.read_text(encoding="ascii").endswith("\n"))

    def test_cli_validates_lists_prints_and_writes_images(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA BRAM image issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("reset_smoke.reset_to_trap_fpga", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--print-image", "syscall_trap.sys_pause_iret_fpga", "tag_ram"])

        self.assertEqual(result, 0)
        self.assertTrue(set(stream.getvalue().splitlines()) <= {"0"})

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json", "--program", "relocation.branch_call_data_fpga"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed[0]["program_id"], "relocation.branch_call_data_fpga")

        with tempfile.TemporaryDirectory(prefix="tmp_i26_s02_cli_", dir=ROOT) as tmp:
            rel_tmp = Path(tmp).relative_to(ROOT)
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(
                    [
                        "--write",
                        "--out-dir",
                        rel_tmp.as_posix(),
                        "--program",
                        "syscall_trap.sys_pause_iret_fpga",
                    ]
                )
            self.assertEqual(result, 0)
            parsed = json.loads(stream.getvalue())
            self.assertEqual(len(parsed["files_written"]), 3)

            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(
                    [
                        "--verify",
                        rel_tmp.as_posix(),
                        "--program",
                        "syscall_trap.sys_pause_iret_fpga",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertIn("verification issues: 0", stream.getvalue())

    def test_documentation_names_commands_artifacts_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-bram-image-generation.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I26-S02", text)
        self.assertIn("python tools\\fpga_bram_images.py --check", text)
        self.assertIn("python tools\\fpga_program_manifest.py --check", text)
        self.assertIn("python tools\\fpga_smoke_firmware.py --check", text)
        self.assertIn("--write", text)
        self.assertIn("--print-image", text)
        self.assertIn("rom.mem", text)
        self.assertIn("data.mem", text)
        self.assertIn("tags.mem", text)
        self.assertIn("hex24-cells-v1", text)
        self.assertIn("hex1-tags-v1", text)
        self.assertIn("instruction_rom", text)
        self.assertIn("data_ram", text)
        self.assertIn("tag_ram", text)
        self.assertIn("image_sha256", text)
        self.assertIn("simulator-visible expected cells and tags", text)
        self.assertIn("I26-S03", text)


if __name__ == "__main__":
    unittest.main()

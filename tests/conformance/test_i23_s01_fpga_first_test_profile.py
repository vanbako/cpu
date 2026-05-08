"""I23-S01 conformance tests for the FPGA first-test profile."""

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
TOOL = ROOT / "tools" / "fpga_first_test_profile.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import cells, fpga_first_test, platform


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_test_profile_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaFirstTestProfileTests(unittest.TestCase):
    def test_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_test.validate_fpga_first_test_profile(root=ROOT), ())

    def test_profile_names_board_clock_reset_and_core_boundary(self) -> None:
        profile = fpga_first_test.FPGA_FIRST_TEST_PROFILE

        self.assertEqual(profile.name, "cpu_v01_fpga_first_test_bram_smoke")
        self.assertEqual(profile.story, "I23-S01")
        self.assertEqual(profile.fpga_top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.core_top_module, "cpu_v01_core")
        self.assertEqual(profile.target_board.name, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.target_board.fpga_device, "GW5AST-LV138PG484A")
        self.assertEqual(profile.target_board.ide_package, "PBG484A")
        self.assertIn("onboard_usb_jtag_uart", profile.target_board.programming_interfaces)
        self.assertIn("pmod_led_x8", profile.target_board.observation_interfaces)
        self.assertIn("All PIN Constraints", profile.target_board.constraint_source)
        self.assertTrue(profile.target_board.open_items)
        self.assertEqual(profile.clock_reset.input_clock, "board_clk_i")
        self.assertEqual(profile.clock_reset.input_reset, "board_reset_n_i")
        self.assertIn("sync_release", profile.clock_reset.reset_polarity)
        self.assertGreaterEqual(profile.clock_reset.reset_sync_stages, 2)
        self.assertLessEqual(profile.clock_reset.maximum_core_clock_hz, 25_000_000)

    def test_memory_map_covers_bram_rom_ram_and_tag_sidecar(self) -> None:
        profile = fpga_first_test.FPGA_FIRST_TEST_PROFILE
        rom = profile.memory_by_name("instruction_rom")
        ram = profile.memory_by_name("data_ram")
        tags = profile.memory_by_name("tag_ram")

        self.assertEqual(rom.kind, "rom")
        self.assertEqual(rom.port, "imem")
        self.assertTrue(rom.contains(platform.RESET_VECTOR))
        self.assertEqual(rom.initialization, "build/fpga/first_test_rom.mem")

        self.assertEqual(ram.kind, "ram")
        self.assertEqual(ram.port, "dmem")
        self.assertEqual(tags.kind, "tag_sidecar")
        self.assertEqual(tags.port, "tagmem")
        self.assertEqual(tags.base_cell, ram.base_cell)
        self.assertEqual(tags.size_cells, ram.size_cells)
        self.assertIn("integer_store_clears", tags.tag_policy)

    def test_image_format_is_24_bit_cell_memory_init(self) -> None:
        image_format = fpga_first_test.FPGA_FIRST_TEST_PROFILE.image_format

        self.assertEqual(image_format.name, "hex24-cells-v1")
        self.assertEqual(image_format.cell_bits, cells.CELL_BITS)
        self.assertEqual(image_format.rom_init_file, "build/fpga/first_test_rom.mem")
        self.assertEqual(image_format.data_init_file, "build/fpga/first_test_data.mem")
        self.assertIn("6-hex-digit", image_format.line_format)
        self.assertEqual(image_format.source_fixture, "tiny_rom_reset_smoke")

    def test_observations_and_synthesis_flow_cover_first_board_smoke(self) -> None:
        profile = fpga_first_test.FPGA_FIRST_TEST_PROFILE

        for name in ("pass_led", "fail_led", "heartbeat_led"):
            with self.subTest(name=name):
                observation = profile.observation_by_name(name)
                self.assertTrue(observation.required)

        flow = profile.build_flow
        self.assertIn("lint_or_elaborate_cpu_v01_fpga_top", flow.required_steps)
        self.assertIn("synthesize_bram_smoke_design", flow.required_steps)
        self.assertIn("place_and_route_with_board_constraints", flow.required_steps)
        self.assertIn("board_clk_i_clock_period", flow.required_constraints)
        self.assertIn("no_unconstrained_paths", flow.required_constraints)
        self.assertIn("unconstrained_clock_or_reset", flow.failure_conditions)
        self.assertIn("external_dram_controller", profile.non_goals)
        self.assertIn("multicore_startup", profile.non_goals)
        self.assertIn("fabric_links_or_switches", profile.non_goals)

    def test_cli_validates_and_renders_profile_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-test profile issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["name"], "cpu_v01_fpga_first_test_bram_smoke")
        self.assertEqual(parsed["fpga_top_module"], "cpu_v01_fpga_top")
        self.assertEqual(parsed["target_board"]["name"], "Sipeed Tang Mega 138K Dock")
        self.assertEqual(parsed["target_board"]["fpga_device"], "GW5AST-LV138PG484A")
        self.assertEqual(parsed["image_format"]["name"], "hex24-cells-v1")
        self.assertEqual(parsed["memories"][0]["name"], "instruction_rom")

    def test_documentation_artifact_names_command_and_required_surfaces(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-test-plan.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S01", text)
        self.assertIn("python tools\\fpga_first_test_profile.py --check", text)
        self.assertIn("cpu_v01_fpga_first_test_bram_smoke", text)
        self.assertIn("cpu_v01_fpga_top", text)
        self.assertIn("cpu_v01_core", text)
        self.assertIn("Sipeed Tang Mega 138K Dock", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("All PIN Constraints", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("instruction_rom", text)
        self.assertIn("data_ram", text)
        self.assertIn("tag_ram", text)
        self.assertIn("hex24-cells-v1", text)
        self.assertIn("pass_led", text)
        self.assertIn("fail_led", text)
        self.assertIn("external DRAM", text)


if __name__ == "__main__":
    unittest.main()

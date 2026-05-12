"""I35-S03 conformance tests for FPGA video output boundary handling."""

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
TOOL = ROOT / "tools" / "fpga_video_output.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_output


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_output_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaVideoOutputBoundaryTests(unittest.TestCase):
    def test_video_output_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_output.validate_fpga_video_output(ROOT), ())

    def test_profile_names_prerequisites_clock_and_handoffs(self) -> None:
        profile = fpga_video_output.fpga_video_output_profile()

        self.assertEqual(profile.story, "I35-S03")
        self.assertEqual(profile.timing_gate, "python tools\\fpga_video_timing.py --check")
        self.assertEqual(profile.clock_profile_gate, "python tools\\fpga_clock_profiles.py --check")
        self.assertEqual(profile.reset_cdc_gate, "python tools\\fpga_reset_cdc.py --check")
        self.assertEqual(profile.output_module, "cpu_v01_fpga_video_output_boundary")
        self.assertEqual(profile.testbench_module, "cpu_v01_fpga_video_output_boundary_tb")
        self.assertEqual(profile.pixel_clock_name, "video_pixel_clk")
        self.assertEqual(profile.pixel_clock_hz, 74_250_000)
        self.assertEqual(profile.reset_sync_stages, 2)
        self.assertIn("create_generated_clock -name video_pixel_clk", profile.generated_clock_sdc)
        self.assertIn("-multiply_by 297 -divide_by 100", profile.generated_clock_sdc)
        self.assertIn("I35-S06", " ".join(profile.board_handoffs))
        self.assertIn("I28-S03", " ".join(profile.board_handoffs))
        self.assertIn("cross_multi_bit_mmio_config_without_I35_S04_latch", profile.non_goals)

    def test_output_signals_and_cdc_rules_are_complete(self) -> None:
        profile = fpga_video_output.fpga_video_output_profile()
        signal_names = {signal.name for signal in profile.output_signals}
        cdc_names = {rule.name for rule in profile.cdc_rules}

        self.assertEqual(profile.signal_by_name("video_rgb_o").width_bits, 24)
        for signal_name in (
            "video_rgb_o",
            "video_hsync_o",
            "video_vsync_o",
            "video_de_o",
            "video_pixel_clk_o",
            "video_output_enable_o",
        ):
            with self.subTest(signal=signal_name):
                self.assertIn(signal_name, signal_names)

        for rule_name in (
            "pixel_reset_release",
            "scanout_enable_sync",
            "output_enable_sync",
            "registered_board_outputs",
            "stable_pattern_config_boundary",
        ):
            with self.subTest(rule=rule_name):
                self.assertIn(rule_name, cdc_names)

    def test_rtl_sources_name_boundary_testbench_and_cdc_tokens(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_video_output_boundary.sv").read_text(
            encoding="utf-8"
        )
        tb = (ROOT / "rtl" / "cpu_v01_fpga_video_output_boundary_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_video_output_boundary",
            "parameter int RESET_SYNC_STAGES = 2",
            "pixel_reset_sync_q",
            "scanout_enable_sync_q",
            "output_enable_sync_q",
            "cpu_v01_fpga_video_timing u_timing",
            "assign video_pixel_clk_o = pixel_clk_i",
            "assign video_output_enable_o = output_enable_sync_q[1]",
            "video_rgb_o <= timing_de ? timing_rgb : 24'h000000",
            "video_hsync_o <= timing_hsync",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_video_output_boundary_tb",
            "cpu_v01_fpga_video_output_boundary dut",
            "VIDEO output reset did not hold outputs blank",
            "VIDEO output enable did not blank RGB",
            "VIDEO output did not forward hsync",
            "VIDEO output did not expose pixel clock",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_signals_sdc_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video output boundary issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S03")
        self.assertEqual(parsed["pixel_clock_hz"], 74_250_000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--signals"])

        self.assertEqual(result, 0)
        self.assertIn("video_rgb_o\t24", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--sdc"])

        self.assertEqual(result, 0)
        self.assertIn("create_generated_clock -name video_pixel_clk", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--top-module cpu_v01_fpga_video_output_boundary_tb", stream.getvalue())

    def test_documentation_names_boundary_outputs_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-video-output-boundary.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I35-S03", text)
        self.assertIn("python tools\\fpga_video_output.py --check", text)
        self.assertIn("74.25 MHz", text)
        self.assertIn("create_generated_clock -name video_pixel_clk", text)
        self.assertIn("cpu_v01_fpga_video_output_boundary", text)
        self.assertIn("pixel_reset_sync_q", text)
        self.assertIn("scanout_enable_sync_q", text)
        self.assertIn("video_rgb_o", text)
        self.assertIn("video_hsync_o", text)
        self.assertIn("video_vsync_o", text)
        self.assertIn("video_de_o", text)
        self.assertIn("I35-S04", text)
        self.assertIn("I35-S06", text)
        self.assertIn("I28-S03", text)


if __name__ == "__main__":
    unittest.main()

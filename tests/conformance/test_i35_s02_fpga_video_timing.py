"""I35-S02 conformance tests for FPGA 720p timing scanout."""

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
TOOL = ROOT / "tools" / "fpga_video_timing.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_timing


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_timing_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaVideoTimingTests(unittest.TestCase):
    def test_video_timing_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_timing.validate_fpga_video_timing(ROOT), ())

    def test_profile_matches_720p_display_timing_and_outputs(self) -> None:
        profile = fpga_video_timing.fpga_video_timing_profile()

        self.assertEqual(profile.story, "I35-S02")
        self.assertEqual(profile.display_gate, "python tools\\fpga_video_display.py --check")
        self.assertEqual(profile.timing_name, "cea_720p60")
        self.assertEqual((profile.active_width, profile.active_height), (1280, 720))
        self.assertEqual((profile.h_total, profile.v_total), (1650, 750))
        self.assertEqual(profile.pixel_clock_hz, 74_250_000)
        self.assertIn("color_bars", profile.pattern_names)
        self.assertIn("checkerboard", profile.pattern_names)
        self.assertIn("pixel_x_o", profile.output_signals)
        self.assertIn("frame_count_o", profile.output_signals)
        self.assertIn("I36-S02", profile.handoff_stories)
        self.assertIn("framebuffer_fetch", profile.non_goals)

    def test_executable_timing_model_counts_one_frame(self) -> None:
        summary = fpga_video_timing.summarize_one_frame()

        self.assertEqual(summary.active_pixels, 1280 * 720)
        self.assertEqual(summary.hsync_pixels, 40 * 750)
        self.assertEqual(summary.vsync_pixels, 5 * 1650)
        self.assertEqual(summary.vblank_pixels, 30 * 1650)
        self.assertEqual(summary.frames_completed, 1)
        self.assertEqual(summary.final_h_count, 0)
        self.assertEqual(summary.final_v_count, 0)

    def test_patterns_are_deterministic(self) -> None:
        state = fpga_video_timing.fpga_video_timing_state()
        sample = state.sample()

        self.assertTrue(sample.data_enable)
        self.assertEqual((sample.pixel_x, sample.pixel_y), (0, 0))
        self.assertEqual(sample.rgb, 0xFF0000)

        state.pattern_select = fpga_video_timing.PATTERN_CHECKERBOARD
        self.assertEqual(state.pattern_rgb(0, 0), 0x000000)
        self.assertEqual(state.pattern_rgb(32, 0), 0xFFFFFF)
        self.assertEqual(state.pattern_rgb(32, 32), 0x000000)

        state.pattern_select = fpga_video_timing.PATTERN_BACKGROUND
        state.background_rgb = 0x123456
        self.assertEqual(state.pattern_rgb(100, 100), 0x123456)

    def test_rtl_sources_name_timing_module_patterns_and_testbench(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_video_timing.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_video_timing_tb.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_video_timing",
            "H_ACTIVE = 1280",
            "H_TOTAL = H_ACTIVE + H_FRONT + H_SYNC + H_BACK",
            "PATTERN_COLOR_BARS = 4'd1",
            "assign de_o = active_pixel",
            "assign hsync_o = hsync_active",
            "assign vsync_o = vsync_active",
            "color_bar_rgb",
            "checkerboard_rgb",
            "frame_count_o",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_video_timing_tb",
            "cpu_v01_fpga_video_timing dut",
            "ACTIVE_PIXELS mismatch",
            "HSYNC_PIXELS mismatch",
            "VSYNC_PIXELS mismatch",
            "FRAME_COUNT did not advance",
            "COLOR_BAR first pixel mismatch",
            "CHECKERBOARD did not toggle",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_plan_and_frame_summary(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video timing issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S02")
        self.assertEqual(parsed["active_width"], 1280)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("--top-module cpu_v01_fpga_video_timing_tb", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--frame-summary"])

        self.assertEqual(result, 0)
        summary = json.loads(stream.getvalue())
        self.assertEqual(summary["active_pixels"], 921600)
        self.assertEqual(summary["frames_completed"], 1)

    def test_documentation_names_timing_outputs_patterns_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-video-timing-scanout.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I35-S02", text)
        self.assertIn("python tools\\fpga_video_timing.py --check", text)
        self.assertIn("1280x720", text)
        self.assertIn("74.25 MHz", text)
        self.assertIn("cpu_v01_fpga_video_timing", text)
        self.assertIn("color_bars", text)
        self.assertIn("checkerboard", text)
        self.assertIn("hsync_o", text)
        self.assertIn("vsync_o", text)
        self.assertIn("de_o", text)
        self.assertIn("I35-S03", text)
        self.assertIn("I36-S02", text)


if __name__ == "__main__":
    unittest.main()

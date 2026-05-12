"""I36-S01 conformance tests for compositor framebuffer policy."""

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
TOOL = ROOT / "tools" / "fpga_compositor_framebuffer.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_framebuffer, fpga_external_memory, fpga_video_display


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_framebuffer_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorFramebufferPolicyTests(unittest.TestCase):
    def test_framebuffer_policy_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_framebuffer.validate_fpga_compositor_framebuffer(ROOT), ())

    def test_framebuffer_heap_is_inside_external_ddr_payload(self) -> None:
        profile = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()
        external = fpga_external_memory.fpga_external_memory_profile().window_by_name(
            "external_ddr_payload"
        )
        window = profile.framebuffer_window

        self.assertEqual(profile.story, "I36-S01")
        self.assertEqual(profile.display_profile, "cpu_v01_fpga_720p_display_profile")
        self.assertEqual(window.name, "external_ddr_framebuffer_heap")
        self.assertEqual(window.base_cell, 0x01100000)
        self.assertEqual(window.end_cell, 0x01500000)
        self.assertGreaterEqual(window.base_cell, external.base_cell)
        self.assertLessEqual(window.end_cell, external.end_cell)
        self.assertEqual(window.memory_type, "normal_uncacheable")
        self.assertEqual(window.tag_policy, "payload_only_no_capability_tags")

    def test_pixel_formats_size_720p_frames_and_aligned_strides(self) -> None:
        profile = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()
        timing = fpga_video_display.fpga_video_display_profile().timing

        rgb565 = profile.format_by_name("rgb565")
        xrgb = profile.format_by_name("xrgb8888")
        indexed = profile.format_by_name("indexed8")

        self.assertEqual(rgb565.frame_bytes(timing.active_width, timing.active_height), 1_843_200)
        self.assertEqual(rgb565.frame_cells(timing.active_width, timing.active_height), 307_200)
        self.assertEqual(xrgb.frame_bytes(timing.active_width, timing.active_height), 3_686_400)
        self.assertEqual(xrgb.frame_cells(timing.active_width, timing.active_height), 614_400)
        self.assertEqual(indexed.frame_bytes(timing.active_width, timing.active_height), 921_600)
        self.assertEqual(indexed.frame_cells(timing.active_width, timing.active_height), 153_600)
        self.assertEqual(xrgb.stride_cells(timing.active_width) % profile.stride_align_cells, 0)
        self.assertGreaterEqual(profile.framebuffer_window.size_cells, xrgb.frame_cells(1280, 720) * 2)

    def test_line_buffer_and_memory_ownership_policy_are_explicit(self) -> None:
        profile = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()

        self.assertEqual(profile.payload_bytes_per_cell, 6)
        self.assertEqual(profile.framebuffer_align_cells, 16)
        self.assertEqual(profile.stride_align_cells, 16)
        self.assertEqual(profile.line_buffer.active_width, 1280)
        self.assertEqual(profile.line_buffer.max_bytes_per_pixel, 4)
        self.assertEqual(profile.line_buffer.buffered_lines, 2)
        self.assertEqual(profile.line_buffer.required_cells, 1707)
        self.assertGreaterEqual(profile.line_buffer.allocated_cells, profile.line_buffer.required_cells)
        self.assertEqual(profile.line_buffer.underflow_counter, "VIDEO_UNDERFLOW_COUNT")
        self.assertIn("I36-S08", profile.handoff_stories)
        self.assertIn("capability_tag_sidecar_for_framebuffers", profile.non_goals)
        self.assertTrue(
            any("not capability-tag-bearing" in rule for rule in profile.memory_ownership_rules)
        )

    def test_cli_validates_renders_json_formats_and_windows(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor framebuffer policy issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S01")
        self.assertEqual(parsed["framebuffer_window"]["base_cell"], 0x01100000)
        self.assertEqual(parsed["line_buffer"]["underflow_counter"], "VIDEO_UNDERFLOW_COUNT")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--formats"])

        self.assertEqual(result, 0)
        self.assertIn("rgb565\t2", stream.getvalue())
        self.assertIn("xrgb8888\t4", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--windows"])

        self.assertEqual(result, 0)
        self.assertIn("external_ddr_framebuffer_heap\t0x01100000\t0x01500000", stream.getvalue())

    def test_documentation_names_policy_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-compositor-framebuffer-policy.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I36-S01", text)
        self.assertIn("python tools\\fpga_compositor_framebuffer.py --check", text)
        self.assertIn("0x01100000", text)
        self.assertIn("external_ddr_framebuffer_heap", text)
        self.assertIn("rgb565", text)
        self.assertIn("xrgb8888", text)
        self.assertIn("indexed8", text)
        self.assertIn("VIDEO_UNDERFLOW_COUNT", text)
        self.assertIn("normal uncacheable", text)
        self.assertIn("payload-only", text)
        self.assertIn("capability tags", text)
        self.assertIn("I36-S02", text)
        self.assertIn("I36-S08", text)


if __name__ == "__main__":
    unittest.main()

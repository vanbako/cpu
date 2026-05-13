"""I36-S02 conformance tests for single-plane framebuffer fetch."""

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
TOOL = ROOT / "tools" / "fpga_compositor_fetch.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_fetch


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_fetch_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorFetchTests(unittest.TestCase):
    def test_compositor_fetch_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_fetch.validate_fpga_compositor_fetch(ROOT), ())

    def test_profile_names_dependencies_read_master_and_handoffs(self) -> None:
        profile = fpga_compositor_fetch.fpga_compositor_fetch_profile()

        self.assertEqual(profile.story, "I36-S02")
        self.assertEqual(profile.framebuffer_gate, "python tools\\fpga_compositor_framebuffer.py --check")
        self.assertEqual(profile.timing_gate, "python tools\\fpga_video_timing.py --check")
        self.assertEqual(profile.ddr_wrapper_gate, "python tools\\fpga_ddr_wrapper.py --check")
        self.assertEqual(profile.fetch_module, "cpu_v01_fpga_single_plane_fetch")
        self.assertEqual(profile.testbench_module, "cpu_v01_fpga_single_plane_fetch_tb")
        self.assertEqual(profile.line_buffer_pixels, 1280)
        self.assertEqual(profile.line_buffered_lines, 2)
        self.assertIn("rgb565", profile.supported_formats)
        self.assertIn("xrgb8888", profile.supported_formats)
        self.assertEqual(profile.format_selects["rgb565"], 0)
        self.assertEqual(profile.format_selects["xrgb8888"], 1)
        for signal in (
            "video_rd_req_valid_o",
            "video_rd_req_ready_i",
            "video_rd_req_addr_o",
            "video_rd_req_len_cells_o",
            "video_rd_rsp_valid_i",
            "video_rd_rsp_ready_o",
            "video_rd_rsp_data_i",
            "video_rd_rsp_error_i",
        ):
            self.assertIn(signal, profile.read_master_signals)
        self.assertIn("I36-S08", " ".join(profile.handoffs))
        self.assertIn("shared_cpu_compositor_memory_arbiter", profile.non_goals)

    def test_rgb565_and_xrgb8888_conversion_helpers(self) -> None:
        self.assertEqual(fpga_compositor_fetch.rgb565_to_rgb888(0xF800), 0xFF0000)
        self.assertEqual(fpga_compositor_fetch.rgb565_to_rgb888(0x07E0), 0x00FF00)
        self.assertEqual(fpga_compositor_fetch.rgb565_to_rgb888(0x001F), 0x0000FF)
        self.assertEqual(fpga_compositor_fetch.rgb565_to_rgb888(0xFFFF), 0xFFFFFF)
        self.assertEqual(fpga_compositor_fetch.xrgb8888_to_rgb888(0xAA123456), 0x123456)

    def test_fetch_line_uses_stride_addresses_and_reports_underflow(self) -> None:
        descriptor = fpga_compositor_fetch.default_plane_descriptor("rgb565")
        memory = {
            descriptor.base_cell + descriptor.stride_cells + 0: 0xF800,
            descriptor.base_cell + descriptor.stride_cells + 1: 0x07E0,
            descriptor.base_cell + descriptor.stride_cells + 2: 0x001F,
            descriptor.base_cell + descriptor.stride_cells + 3: 0xFFFF,
        }

        result = fpga_compositor_fetch.fetch_line(descriptor, 1, memory)

        self.assertEqual(result.requests[0].addr_cell, descriptor.base_cell + descriptor.stride_cells)
        self.assertEqual(result.requests[3].addr_cell, descriptor.base_cell + descriptor.stride_cells + 3)
        self.assertEqual(result.rgb_pixels[:4], (0xFF0000, 0x00FF00, 0x0000FF, 0xFFFFFF))
        self.assertTrue(result.underflow)
        self.assertEqual(len(result.error_cells), 4)

        complete = fpga_compositor_fetch.demo_fetch_line()
        self.assertFalse(complete.underflow)
        self.assertEqual(complete.rgb_pixels[:4], (0xFF0000, 0x00FF00, 0x0000FF, 0xFFFFFF))

    def test_xrgb_underflow_demo_preserves_valid_pixels(self) -> None:
        result = fpga_compositor_fetch.demo_underflow_line()

        self.assertTrue(result.underflow)
        self.assertEqual(result.rgb_pixels[0], 0x123456)
        self.assertEqual(result.rgb_pixels[1], result.descriptor.background_rgb)
        self.assertEqual(result.rgb_pixels[2], 0xABCDEF)
        self.assertIn(result.descriptor.base_cell + 1, result.error_cells)

    def test_rtl_testbench_names_fetch_line_buffer_and_underflow_contract(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_single_plane_fetch.sv").read_text(
            encoding="utf-8"
        )
        tb = (ROOT / "rtl" / "cpu_v01_fpga_single_plane_fetch_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_single_plane_fetch",
            "FORMAT_RGB565 = 2'd0",
            "FORMAT_XRGB8888 = 2'd1",
            "line_rgb_q",
            "line_valid_q",
            "assign video_rd_req_valid_o = fetch_active_q",
            "assign video_rd_req_len_cells_o = 8'd1",
            "rgb565_to_rgb888",
            "xrgb8888_to_rgb888",
            "underflow_pulse_o",
            "video_rd_req_addr_o",
            "plane_stride_cells_i",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_single_plane_fetch_tb",
            "cpu_v01_fpga_single_plane_fetch dut",
            "single-plane fetch RGB565 red mismatch",
            "single-plane fetch XRGB8888 conversion mismatch",
            "single-plane fetch did not report deterministic underflow",
            "single-plane fetch request address mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_signals_demos_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor fetch issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S02")
        self.assertIn("video_rd_req_valid_o", parsed["read_master_signals"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--signals"])

        self.assertEqual(result, 0)
        self.assertIn("video_rd_rsp_error_i", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertFalse(demo["underflow"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--underflow-demo"])

        self.assertEqual(result, 0)
        underflow = json.loads(stream.getvalue())
        self.assertTrue(underflow["underflow"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("cpu_v01_fpga_single_plane_fetch_tb", stream.getvalue())

    def test_documentation_names_fetch_contract_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-compositor-fetch.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I36-S02",
            "python tools\\fpga_compositor_fetch.py --check",
            "python tools\\fpga_compositor_framebuffer.py --check",
            "python tools\\fpga_video_timing.py --check",
            "python tools\\fpga_ddr_wrapper.py --check",
            "cpu_v01_fpga_single_plane_fetch",
            "video_rd_req_valid_o",
            "video_rd_rsp_valid_i",
            "rgb565",
            "xrgb8888",
            "line_rgb_q",
            "VIDEO_UNDERFLOW_COUNT",
            "I36-S03",
            "I36-S08",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

"""I35-S01 conformance tests for the FPGA video display profile."""

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
TOOL = ROOT / "tools" / "fpga_video_display.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_platform, fpga_video_display, platform


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_display_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaVideoDisplayProfileTests(unittest.TestCase):
    def test_video_display_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_display.validate_fpga_video_display(ROOT), ())

    def test_720p_timing_is_fixed(self) -> None:
        timing = fpga_video_display.fpga_video_display_profile().timing

        self.assertEqual(timing.name, "cea_720p60")
        self.assertEqual((timing.active_width, timing.active_height), (1280, 720))
        self.assertEqual((timing.h_total, timing.v_total), (1650, 750))
        self.assertEqual(timing.pixel_clock_hz, 74_250_000)
        self.assertEqual(timing.frame_rate_millihz, 60_000)
        self.assertTrue(timing.hsync_active_high)
        self.assertTrue(timing.vsync_active_high)

    def test_mmio_window_fits_after_existing_soc_peripherals(self) -> None:
        profile = fpga_video_display.fpga_video_display_profile()
        device = platform.TEST_PLATFORM_PROFILE.region_by_name("platform_devices")
        soc = fpga_soc_platform.fpga_soc_platform_profile()

        self.assertEqual(profile.story, "I35-S01")
        self.assertEqual(profile.name, "cpu_v01_fpga_720p_display_profile")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.fpga_top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.mmio.base_cell, 0x00F00500)
        self.assertEqual(profile.mmio.end_cell, 0x00F00600)
        self.assertTrue(device.contains(profile.mmio.base_cell))
        self.assertLessEqual(profile.mmio.end_cell, device.end)
        for peripheral in soc.peripherals:
            self.assertFalse(
                profile.mmio.base_cell < peripheral.end_cell
                and peripheral.base_cell < profile.mmio.end_cell,
                peripheral.name,
            )

    def test_registers_and_vblank_interrupt_are_assigned(self) -> None:
        mmio = fpga_video_display.fpga_video_display_profile().mmio

        self.assertEqual(mmio.interrupt_line, "video_vblank")
        self.assertEqual(mmio.interrupt_bit, 4)
        self.assertEqual(mmio.register_by_name("VIDEO_CONTROL").access, "rw")
        self.assertEqual(mmio.register_by_name("VIDEO_MODE").reset_value, 0)
        self.assertEqual(mmio.register_by_name("VIDEO_STATUS").access, "ro")
        self.assertEqual(mmio.register_by_name("VIDEO_IRQ_ACK").access, "w1c")
        self.assertEqual(mmio.register_by_name("VIDEO_FRAME_COUNT").width_bits, 48)
        self.assertEqual(mmio.register_by_name("VIDEO_BG_COLOR").width_bits, 24)
        self.assertEqual(mmio.register_by_name("VIDEO_FB_MASTER_STATUS").access, "ro")

    def test_same_fpga_interface_excludes_pcie_like_fabric(self) -> None:
        profile = fpga_video_display.fpga_video_display_profile()
        signal_names = {signal.name for signal in profile.read_master_signals}

        self.assertEqual(profile.cpu_control_interface, "local_mmio_device_ordered_48bit_cells")
        self.assertEqual(
            profile.framebuffer_read_master,
            "display_payload_read_master_without_capability_tags",
        )
        self.assertIn("PCIe_like_fabric", profile.excluded_interfaces)
        self.assertIn("display_master_tag_sidecar", profile.excluded_interfaces)
        self.assertIn("rgb565", profile.pixel_formats)
        self.assertIn("xrgb8888", profile.pixel_formats)
        self.assertIn("video_rd_req_valid", signal_names)
        self.assertIn("video_rd_req_addr", signal_names)
        self.assertIn("video_rd_rsp_data", signal_names)
        self.assertIn("video_rd_rsp_error", signal_names)
        self.assertIn("I36-S08", profile.handoff_stories)

    def test_cli_validates_renders_json_registers_and_signals(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video display profile issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S01")
        self.assertEqual(parsed["timing"]["active_width"], 1280)
        self.assertEqual(parsed["mmio"]["base_cell"], 0x00F00500)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers"])

        self.assertEqual(result, 0)
        self.assertIn("VIDEO_CONTROL\t0x00F00500", stream.getvalue())
        self.assertIn("VIDEO_FB_MASTER_STATUS", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--signals"])

        self.assertEqual(result, 0)
        self.assertIn("video_rd_req_valid", stream.getvalue())
        self.assertIn("video_rd_rsp_data", stream.getvalue())

    def test_documentation_names_interface_timing_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-video-display-profile.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I35-S01", text)
        self.assertIn("python tools\\fpga_video_display.py --check", text)
        self.assertIn("1280x720", text)
        self.assertIn("74.25 MHz", text)
        self.assertIn("0x00F00500", text)
        self.assertIn("VIDEO_CONTROL", text)
        self.assertIn("VIDEO_IRQ_ACK", text)
        self.assertIn("VIDEO_FB_MASTER_STATUS", text)
        self.assertIn("video_vblank", text)
        self.assertIn("local MMIO", text)
        self.assertIn("framebuffer read master", text)
        self.assertIn("PCIe-like", text)
        self.assertIn("I35-S04", text)
        self.assertIn("I36-S01", text)
        self.assertIn("I36-S08", text)


if __name__ == "__main__":
    unittest.main()

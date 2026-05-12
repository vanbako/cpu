"""I35-S04 conformance tests for FPGA video MMIO and vblank IRQ routing."""

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
TOOL = ROOT / "tools" / "fpga_video_mmio.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_decoder, fpga_soc_top_peripherals, fpga_video_mmio


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_mmio_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaVideoMmioIrqTests(unittest.TestCase):
    def test_video_mmio_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_mmio.validate_fpga_video_mmio(ROOT), ())

    def test_profile_names_mmio_window_irq_and_handoffs(self) -> None:
        profile = fpga_video_mmio.fpga_video_mmio_profile()

        self.assertEqual(profile.story, "I35-S04")
        self.assertEqual(profile.display_gate, "python tools\\fpga_video_display.py --check")
        self.assertEqual(profile.output_gate, "python tools\\fpga_video_output.py --check")
        self.assertEqual(profile.decoder_gate, "python tools\\fpga_soc_top_decoder.py --check")
        self.assertEqual(profile.peripheral_gate, "python tools\\fpga_soc_top_peripherals.py --check")
        self.assertEqual(profile.mmio_base_cell, 0x00F00500)
        self.assertEqual(profile.mmio_end_cell, 0x00F00600)
        self.assertEqual(profile.irq_line, "video_vblank")
        self.assertEqual(profile.irq_bit, 4)
        self.assertEqual(profile.irq_controller_mask, 0x0010)
        self.assertEqual(profile.external_irq_mask, 0x001B)
        self.assertEqual(profile.rtl_module, "cpu_v01_fpga_video_mmio")
        self.assertIn("--top-module cpu_v01_fpga_video_mmio_tb", profile.verilator_command)
        self.assertIn("I35-S05", profile.deferred_handoffs[0])

    def test_register_behaviors_and_executable_vblank_irq_demo(self) -> None:
        profile = fpga_video_mmio.fpga_video_mmio_profile()
        demo = fpga_video_mmio.simulate_video_mmio_irq_demo()

        for register in (
            "VIDEO_CONTROL",
            "VIDEO_MODE",
            "VIDEO_STATUS",
            "VIDEO_IRQ_ENABLE",
            "VIDEO_IRQ_ACK",
            "VIDEO_FRAME_COUNT",
            "VIDEO_LINE_COUNT",
            "VIDEO_PIXEL_COUNT",
            "VIDEO_TEST_PATTERN",
            "VIDEO_BG_COLOR",
            "VIDEO_UNDERFLOW_COUNT",
            "VIDEO_FB_MASTER_STATUS",
        ):
            with self.subTest(register=register):
                self.assertEqual(profile.behavior_by_register(register).register, register)

        self.assertTrue(demo.after_program.scanout_enabled)
        self.assertTrue(demo.after_program.output_enabled)
        self.assertEqual(demo.after_program.test_pattern, 2)
        self.assertEqual(demo.after_program.bg_color, 0x123456)
        self.assertTrue(demo.after_vblank.irq_asserted)
        self.assertTrue(demo.after_vblank.status & fpga_video_mmio.VIDEO_STATUS_VBLANK_PENDING)
        self.assertFalse(demo.after_ack.irq_asserted)
        self.assertEqual(demo.irq_controller_mask, 0x0010)

    def test_decoder_and_external_irq_models_include_video_display(self) -> None:
        decoded = fpga_soc_top_decoder.decode_soc_top_address(0x00F00500, len_cells=1)
        external = fpga_soc_top_peripherals.evaluate_soc_top_peripherals(
            irq_pending_enabled=0x0010
        )

        self.assertEqual(decoded.target, "video_display")
        self.assertEqual(decoded.response, "mmio_response_or_register_fault")
        self.assertFalse(decoded.tag_sidecar)
        self.assertTrue(external.external_interrupt_pending)

    def test_rtl_top_testbenches_name_video_mmio_and_irq_tokens(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")
        tb = (ROOT / "rtl" / "cpu_v01_fpga_video_mmio_tb.sv").read_text(encoding="utf-8")
        decoder_tb = (ROOT / "rtl" / "cpu_v01_fpga_top_soc_decoder_tb.sv").read_text(
            encoding="utf-8"
        )
        peripheral_tb = (ROOT / "rtl" / "cpu_v01_fpga_top_soc_peripherals_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_video_mmio",
            "VIDEO_CONTROL_OFFSET",
            "VIDEO_IRQ_ENABLE_OFFSET",
            "vblank_pending_q",
            "underflow_count_q",
            "assign video_vblank_irq_o = |(irq_enable_q & irq_pending_q);",
            "TARGET_VIDEO",
            "VIDEO_BASE = 48'h0000_00F0_0500",
            "video_req_valid",
            ".video_req_valid(video_req_valid)",
            "cpu_v01_fpga_video_mmio firmware_video",
            "video_vblank_irq",
            "assign external_interrupt_pending = |(irq_pending_enabled & 16'h001B);",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

        for token in (
            "module cpu_v01_fpga_video_mmio_tb",
            "cpu_v01_fpga_video_mmio dut",
            "FPGA video MMIO did not enable scanout outputs",
            "FPGA video MMIO did not report vblank status",
            "FPGA video MMIO did not raise video_vblank_irq_o",
            "FPGA video MMIO acknowledgement did not clear vblank IRQ",
            "FPGA video MMIO frame count readback mismatch",
            "FPGA video MMIO underflow count mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

        self.assertIn("FPGA SoC top decoder video control readback mismatch", decoder_tb)
        self.assertIn("FPGA SoC top peripherals video vblank external interrupt mismatch", peripheral_tb)

    def test_cli_validates_json_registers_irq_demo_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video MMIO issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S04")
        self.assertEqual(parsed["irq_bit"], 4)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--registers"])

        self.assertEqual(result, 0)
        self.assertIn("VIDEO_CONTROL", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--irq-demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertTrue(demo["after_vblank"]["irq_asserted"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("rtl/cpu_v01_fpga_video_mmio_tb.sv", stream.getvalue())

    def test_documentation_names_registers_irq_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-video-mmio-irq.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I35-S04", text)
        self.assertIn("python tools\\fpga_video_mmio.py --check", text)
        self.assertIn("0x00F00500", text)
        self.assertIn("VIDEO_CONTROL", text)
        self.assertIn("VIDEO_STATUS", text)
        self.assertIn("VIDEO_IRQ_ENABLE", text)
        self.assertIn("VIDEO_IRQ_ACK", text)
        self.assertIn("VIDEO_FRAME_COUNT", text)
        self.assertIn("VIDEO_LINE_COUNT", text)
        self.assertIn("VIDEO_PIXEL_COUNT", text)
        self.assertIn("VIDEO_UNDERFLOW_COUNT", text)
        self.assertIn("VIDEO_FB_MASTER_STATUS", text)
        self.assertIn("video_vblank", text)
        self.assertIn("bit 4", text)
        self.assertIn("16'h001B", text)
        self.assertIn("cpu_v01_fpga_video_mmio", text)
        self.assertIn("cpu_v01_fpga_soc_dmem_decoder", text)
        self.assertIn("I35-S05", text)
        self.assertIn("I36-S04", text)


if __name__ == "__main__":
    unittest.main()

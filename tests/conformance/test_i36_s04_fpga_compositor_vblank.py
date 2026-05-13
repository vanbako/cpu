"""I36-S04 conformance tests for vblank-atomic compositor descriptors."""

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
TOOL = ROOT / "tools" / "fpga_compositor_vblank.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_vblank


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_vblank_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorVblankTests(unittest.TestCase):
    def test_compositor_vblank_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_vblank.validate_fpga_compositor_vblank(ROOT), ())

    def test_profile_names_dependencies_fields_status_and_handoffs(self) -> None:
        profile = fpga_compositor_vblank.fpga_compositor_vblank_profile()

        self.assertEqual(profile.story, "I36-S04")
        self.assertEqual(profile.pipeline_gate, "python tools\\fpga_compositor_pipeline.py --check")
        self.assertEqual(profile.video_mmio_gate, "python tools\\fpga_video_mmio.py --check")
        self.assertEqual(profile.latch_module, "cpu_v01_fpga_compositor_descriptor_latch")
        self.assertEqual(profile.testbench_module, "cpu_v01_fpga_compositor_descriptor_latch_tb")
        self.assertEqual(profile.plane_count, 2)
        for field in (
            "control",
            "base_cell",
            "stride_cells",
            "position_xy",
            "size_wh",
            "format_z_alpha",
            "color_key_rgb",
        ):
            self.assertIn(field, profile.descriptor_fields)
        for bit in ("descriptor_pending", "descriptor_applied_pulse", "applied_count"):
            self.assertIn(bit, profile.status_bits)
        self.assertIn("I36-S05", " ".join(profile.handoffs))
        self.assertIn("I36-S08", " ".join(profile.handoffs))
        self.assertIn("full_video_mmio_register_map_for_planes", profile.non_goals)

    def test_descriptor_demo_keeps_active_stable_until_vblank(self) -> None:
        before, mid_frame, after = fpga_compositor_vblank.demo_vblank_update()

        self.assertTrue(before.pending)
        self.assertTrue(mid_frame.pending)
        self.assertFalse(before.active[0].enable)
        self.assertFalse(mid_frame.active[0].enable)
        self.assertEqual(before.active[0].base_cell, 0)
        self.assertEqual(mid_frame.active[0].base_cell, 0)

        self.assertFalse(after.pending)
        self.assertEqual(after.applied_count, 1)
        self.assertTrue(after.active[0].enable)
        self.assertEqual(after.active[0].base_cell, 0x0110_0000)
        self.assertEqual(after.active[0].stride_cells, 16)
        self.assertEqual(after.active[0].x, 0x0014)
        self.assertEqual(after.active[0].y, 0x000A)
        self.assertEqual(after.active[0].width, 0x0040)
        self.assertEqual(after.active[0].height, 0x0080)
        self.assertEqual(after.active[0].pixel_format, 0)
        self.assertEqual(after.active[0].z, 1)
        self.assertEqual(after.active[0].alpha, 0xFF)
        self.assertTrue(after.active[0].color_key_enable)
        self.assertEqual(after.active[0].color_key_rgb, 0x00FF00)

    def test_field_writes_validate_plane_and_field_bounds(self) -> None:
        state = fpga_compositor_vblank.initial_latch_state()

        with self.assertRaises(ValueError):
            state.write_field(2, fpga_compositor_vblank.FIELD_BASE, 0)
        with self.assertRaises(ValueError):
            state.write_field(0, 7, 0)

    def test_rtl_testbench_names_descriptor_latch_contract(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_compositor_descriptor_latch.sv").read_text(
            encoding="utf-8"
        )
        tb = (
            ROOT / "rtl" / "cpu_v01_fpga_compositor_descriptor_latch_tb.sv"
        ).read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_compositor_descriptor_latch",
            "shadow_plane0_base_q",
            "shadow_plane1_base_q",
            "active_plane0_base_q",
            "active_plane1_base_q",
            "descriptor_pending_o",
            "descriptor_applied_pulse_o",
            "applied_count_o",
            "vblank_q",
            "if (vblank_i && !vblank_q && descriptor_pending_o)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_compositor_descriptor_latch_tb",
            "cpu_v01_fpga_compositor_descriptor_latch dut",
            "descriptor latch active base changed before vblank",
            "descriptor latch did not apply on vblank",
            "descriptor latch did not expose pending status",
            "descriptor latch color key mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_fields_demo_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor vblank issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S04")
        self.assertEqual(parsed["plane_count"], 2)
        self.assertIn("descriptor_pending", parsed["status_bits"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("format_z_alpha", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertTrue(demo[0]["pending"])
        self.assertFalse(demo[2]["pending"])
        self.assertEqual(demo[2]["active"][0]["base_cell"], 0x0110_0000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("cpu_v01_fpga_compositor_descriptor_latch_tb", stream.getvalue())

    def test_documentation_names_vblank_descriptor_contract_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-compositor-vblank-descriptors.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I36-S04",
            "python tools\\fpga_compositor_vblank.py --check",
            "python tools\\fpga_compositor_pipeline.py --check",
            "python tools\\fpga_video_mmio.py --check",
            "cpu_v01_fpga_compositor_descriptor_latch",
            "shadow descriptor",
            "active descriptor",
            "vblank",
            "descriptor_pending",
            "descriptor_applied_pulse",
            "applied_count",
            "mid-frame tearing",
            "I36-S05",
            "I36-S08",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

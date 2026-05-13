"""I36-S03 conformance tests for multi-plane compositor pipeline."""

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
TOOL = ROOT / "tools" / "fpga_compositor_pipeline.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_pipeline


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_pipeline_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorPipelineTests(unittest.TestCase):
    def test_compositor_pipeline_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_pipeline.validate_fpga_compositor_pipeline(ROOT), ())

    def test_profile_names_dependency_rules_outputs_and_handoffs(self) -> None:
        profile = fpga_compositor_pipeline.fpga_compositor_pipeline_profile()

        self.assertEqual(profile.story, "I36-S03")
        self.assertEqual(profile.fetch_gate, "python tools\\fpga_compositor_fetch.py --check")
        self.assertEqual(profile.compositor_module, "cpu_v01_fpga_compositor_pipeline")
        self.assertEqual(profile.testbench_module, "cpu_v01_fpga_compositor_pipeline_tb")
        self.assertEqual(profile.max_planes, 2)
        for token in ("higher z wins", "color-keyed pixels", "alpha 255"):
            self.assertTrue(any(token in rule for rule in profile.composition_rules))
        for signal in ("rgb_o", "de_o", "selected_plane_o", "plane0_sample_o", "plane1_sample_o"):
            self.assertIn(signal, profile.output_signals)
        self.assertIn("I36-S04", " ".join(profile.handoffs))
        self.assertIn("I36-S08", " ".join(profile.handoffs))
        self.assertIn("descriptor_shadow_latch", profile.non_goals)

    def test_alpha_blend_and_demo_composition_behaviors(self) -> None:
        self.assertEqual(fpga_compositor_pipeline.alpha_blend(0xFF0000, 0x000000, 255), 0xFF0000)
        self.assertEqual(fpga_compositor_pipeline.alpha_blend(0xFF0000, 0x000000, 0), 0x000000)
        self.assertEqual(
            fpga_compositor_pipeline.alpha_blend(0x0000FF, 0xFF0000, 128),
            0x7F0080,
        )

        plane0_only, overlap, keyed, clipped = fpga_compositor_pipeline.demo_composition()

        self.assertEqual(plane0_only.rgb, 0xFF0000)
        self.assertEqual(plane0_only.selected_plane, "plane0")
        self.assertEqual(overlap.rgb, 0x7F0080)
        self.assertEqual(overlap.selected_plane, "plane1")
        self.assertEqual(keyed.rgb, 0xFF0000)
        self.assertEqual(keyed.selected_plane, "plane0")
        self.assertEqual(clipped.rgb, 0x102030)
        self.assertEqual(clipped.sampled_planes, ())

    def test_compose_pixel_clips_disabled_and_out_of_bounds_planes(self) -> None:
        disabled = fpga_compositor_pipeline.PlaneState(
            name="plane0",
            enabled=False,
            x=0,
            y=0,
            width=4,
            height=4,
            z=0,
            alpha=255,
            color_key_enabled=False,
            color_key_rgb=0,
            rgb=0xFFFFFF,
        )
        outside = fpga_compositor_pipeline.PlaneState(
            name="plane1",
            enabled=True,
            x=8,
            y=8,
            width=2,
            height=2,
            z=1,
            alpha=255,
            color_key_enabled=False,
            color_key_rgb=0,
            rgb=0x0000FF,
        )

        result = fpga_compositor_pipeline.compose_pixel(
            pixel_x=1,
            pixel_y=1,
            background_rgb=0x010203,
            planes=(disabled, outside),
        )

        self.assertEqual(result.rgb, 0x010203)
        self.assertEqual(result.selected_plane, "background")
        self.assertEqual(result.sampled_planes, ())
        self.assertEqual(set(result.clipped_planes), {"plane0", "plane1"})

    def test_rtl_testbench_names_pipeline_contract(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_compositor_pipeline.sv").read_text(
            encoding="utf-8"
        )
        tb = (ROOT / "rtl" / "cpu_v01_fpga_compositor_pipeline_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_compositor_pipeline",
            "plane0_sample_o",
            "plane1_sample_o",
            "selected_plane_o",
            "alpha_blend",
            "plane0_key_hit",
            "plane1_key_hit",
            "plane1_over_plane0",
            "rgb_o <= composed_rgb",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_compositor_pipeline_tb",
            "cpu_v01_fpga_compositor_pipeline dut",
            "compositor pipeline did not select plane0",
            "compositor pipeline did not alpha blend plane1",
            "compositor pipeline did not honor color key",
            "compositor pipeline sampled clipped planes",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_rules_demo_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor pipeline issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S03")
        self.assertEqual(parsed["max_planes"], 2)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--rules"])

        self.assertEqual(result, 0)
        self.assertIn("higher z wins", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertEqual(demo[1]["selected_plane"], "plane1")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("cpu_v01_fpga_compositor_pipeline_tb", stream.getvalue())

    def test_documentation_names_pipeline_contract_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-compositor-pipeline.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I36-S03",
            "python tools\\fpga_compositor_pipeline.py --check",
            "python tools\\fpga_compositor_fetch.py --check",
            "cpu_v01_fpga_compositor_pipeline",
            "plane0_sample_o",
            "plane1_sample_o",
            "selected_plane_o",
            "global alpha",
            "color-key",
            "z-order",
            "clipping",
            "I36-S04",
            "I36-S08",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

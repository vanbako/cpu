"""I36-S05 conformance tests for compositor firmware and monitor demos."""

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
TOOL = ROOT / "tools" / "fpga_compositor_demo.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_demo, fpga_compositor_pipeline


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_demo_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorDemoTests(unittest.TestCase):
    def test_compositor_demo_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_demo.validate_fpga_compositor_demo(ROOT), ())

    def test_profile_names_dependencies_cases_commands_and_handoffs(self) -> None:
        profile = fpga_compositor_demo.fpga_compositor_demo_profile()

        self.assertEqual(profile.story, "I36-S05")
        self.assertEqual(profile.status, "firmware_monitor_demo_fixture")
        self.assertEqual(profile.vblank_gate, "python tools\\fpga_compositor_vblank.py --check")
        self.assertEqual(profile.loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(profile.monitor_session_gate, "python tools\\fpga_monitor_session.py --check")
        self.assertEqual(profile.framebuffer_gate, "python tools\\fpga_compositor_framebuffer.py --check")
        for command in ("COMPOSITOR_FILL", "PROGRAM_PLANE", "WAIT_VBLANK", "SWAP_DESCRIPTOR"):
            self.assertIn(command, profile.command_vocabulary)

        self.assertEqual(
            {case.case_id for case in profile.cases},
            {"one_plane_fill", "overlay_swap", "error_path_underflow"},
        )
        self.assertEqual({case.actor for case in profile.cases}, {"firmware", "monitor"})
        overlay = profile.case_by_id("overlay_swap")
        self.assertEqual(overlay.monitor_case_id, "scalar_control.call_return")
        self.assertEqual(len(overlay.phases), 2)
        self.assertEqual(len(overlay.manifest_image_sha256), 64)
        self.assertEqual(len(overlay.ram_image_sha256), 64)
        self.assertIn("I36-S06", " ".join(profile.handoffs))
        self.assertIn("I36-S08", " ".join(profile.handoffs))
        self.assertIn("cycle_accurate_firmware_binary", profile.non_goals)

    def test_demo_run_observes_one_plane_overlay_swap_and_underflow(self) -> None:
        run = fpga_compositor_demo.run_compositor_demo()

        self.assertTrue(run.passed)
        self.assertEqual(len(run.observations), 4)

        one = run.observation_by_phase("one_plane_fill", "one_plane")
        self.assertEqual(one.rgb, fpga_compositor_demo.RGB_RED)
        self.assertEqual(one.selected_plane, "plane0")
        self.assertFalse(one.underflow)
        self.assertTrue(one.pending_before_vblank)
        self.assertFalse(one.pending_after_vblank)
        self.assertEqual(one.applied_count, 1)

        overlay = run.observation_by_phase("overlay_swap", "overlay")
        self.assertEqual(
            overlay.rgb,
            fpga_compositor_pipeline.alpha_blend(
                fpga_compositor_demo.RGB_BLUE,
                fpga_compositor_demo.RGB_RED,
                128,
            ),
        )
        self.assertEqual(overlay.selected_plane, "plane1")
        self.assertFalse(overlay.underflow)
        self.assertEqual(overlay.applied_count, 1)

        swap = run.observation_by_phase("overlay_swap", "swap")
        self.assertEqual(swap.rgb, fpga_compositor_demo.RGB_GREEN)
        self.assertEqual(swap.selected_plane, "plane1")
        self.assertFalse(swap.underflow)
        self.assertEqual(swap.applied_count, 2)

        error = run.observation_by_phase("error_path_underflow", "bad_base")
        self.assertEqual(error.rgb, fpga_compositor_demo.DEMO_BACKGROUND_RGB)
        self.assertEqual(error.selected_plane, "background")
        self.assertTrue(error.underflow)
        self.assertIn("UNDERFLOW_ERROR", error.signature.uart)

        digests = {observation.signature.digest for observation in run.observations}
        self.assertEqual(len(digests), len(run.observations))

    def test_demo_run_reports_duplicate_case_selection(self) -> None:
        run = fpga_compositor_demo.run_compositor_demo(("one_plane_fill", "one_plane_fill"))

        self.assertFalse(run.passed)
        self.assertIn("demo run selected duplicate cases", run.issues)

    def test_descriptor_field_writes_match_vblank_latch_contract(self) -> None:
        profile = fpga_compositor_demo.fpga_compositor_demo_profile()
        overlay = profile.case_by_id("overlay_swap")
        writes = overlay.phases[0].descriptor_programs[0].field_writes()

        self.assertEqual([write.field_name for write in writes], [
            "base_cell",
            "stride_cells",
            "position_xy",
            "size_wh",
            "format_z_alpha",
            "color_key_rgb",
            "control",
        ])
        self.assertEqual(writes[-1].value, 1)
        self.assertEqual(overlay.phases[1].descriptor_programs[0].plane, 1)

    def test_cli_validates_json_cases_plan_and_run(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor demo issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S05")
        self.assertEqual(len(parsed["cases"]), 3)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--cases"])

        self.assertEqual(result, 0)
        self.assertIn("one_plane_fill", stream.getvalue())
        self.assertIn("overlay_swap", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("WAIT_VBLANK", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["passed"])
        self.assertEqual(len(run["observations"]), 4)

    def test_documentation_names_demo_contract_signatures_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-compositor-firmware-monitor-demos.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I36-S05",
            "python tools\\fpga_compositor_demo.py --check",
            "python tools\\fpga_compositor_vblank.py --check",
            "python tools\\fpga_program_loader.py --check",
            "python tools\\fpga_monitor_session.py --check",
            "one_plane_fill",
            "overlay_swap",
            "error_path_underflow",
            "COMPOSITOR_FILL",
            "PROGRAM_PLANE",
            "WAIT_VBLANK",
            "SWAP_DESCRIPTOR",
            "descriptor_pending",
            "applied_count",
            "expected LED",
            "expected UART",
            "expected probe",
            "UNDERFLOW_ERROR",
            "I36-S06",
            "I36-S07",
            "Acceptance Review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

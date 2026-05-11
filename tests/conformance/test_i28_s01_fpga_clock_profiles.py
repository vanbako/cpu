"""I28-S01 conformance tests for FPGA clock and PLL profiles."""

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
TOOL = ROOT / "tools" / "fpga_clock_profiles.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_clock_profiles


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_clock_profiles_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaClockProfileTests(unittest.TestCase):
    def test_clock_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_clock_profiles.validate_fpga_clock_profiles(ROOT), ())

    def test_profile_set_names_target_gates_and_defaults(self) -> None:
        profile_set = fpga_clock_profiles.fpga_clock_profile_set()

        self.assertEqual(profile_set.story, "I28-S01")
        self.assertEqual(profile_set.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile_set.device, "GW5AST-LV138PG484A")
        self.assertEqual(profile_set.package, "PBG484A")
        self.assertEqual(profile_set.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile_set.board_clock, "board_clk_i")
        self.assertEqual(profile_set.board_clock_hz, 25_000_000)
        self.assertEqual(profile_set.board_clock_period_ns, 40.000)
        self.assertEqual(profile_set.default_profile_id, "debug_direct_25mhz")
        self.assertEqual(profile_set.release_profile_id, "release_pll_25mhz")
        self.assertEqual(
            profile_set.constraints_gate,
            "python tools\\fpga_constraints_overlay.py --check",
        )
        self.assertEqual(profile_set.gowin_gate, "python tools\\fpga_gowin_build.py --check")
        self.assertEqual(
            profile_set.timing_sdc_path.as_posix(),
            "constraints/tang_mega_138k_first_test.sdc",
        )

    def test_debug_profile_matches_current_direct_clock_and_sdc(self) -> None:
        profile_set = fpga_clock_profiles.fpga_clock_profile_set()
        debug = profile_set.profile_by_id("debug_direct_25mhz")
        sdc = fpga_clock_profiles.clock_profile_sdc("debug_direct_25mhz")

        self.assertTrue(debug.selected_for_current_build)
        self.assertEqual(debug.role, "debug")
        self.assertEqual(debug.pll.primitive, "none")
        self.assertEqual(debug.pll.output_clock, "board_clk_i")
        self.assertEqual(debug.pll.output_hz, 25_000_000)
        self.assertEqual(debug.minimum_slack_ns, 0.000)
        self.assertGreaterEqual(debug.target_slack_ns, 1.000)
        self.assertIn("create_clock -name board_clk_i -period 40.000", sdc)
        self.assertIn("set_false_path -from [get_ports {board_reset_n_i}]", sdc)
        clock_names = {clock.name for clock in debug.generated_clocks}
        self.assertIn("core_clk", clock_names)
        self.assertIn("uart_status_clk", clock_names)
        self.assertIn("timer_gpio_clk", clock_names)

    def test_release_profile_records_pll_generated_clock_and_blocker(self) -> None:
        profile_set = fpga_clock_profiles.fpga_clock_profile_set()
        release = profile_set.profile_by_id("release_pll_25mhz")
        sdc = fpga_clock_profiles.clock_profile_sdc("release_pll_25mhz")

        self.assertFalse(release.selected_for_current_build)
        self.assertEqual(release.role, "release")
        self.assertIn("blocked", release.status)
        self.assertEqual(release.pll.primitive, "Gowin rPLL")
        self.assertEqual(release.pll.input_clock, "board_clk_i")
        self.assertEqual(release.pll.output_clock, "cpu_clk")
        self.assertEqual(release.pll.input_divide, 1)
        self.assertEqual(release.pll.feedback_multiply, 1)
        self.assertEqual(release.pll.output_divide, 1)
        self.assertEqual(release.pll.phase_degrees, 0.0)
        self.assertEqual(release.pll.duty_cycle_percent, 50.0)
        self.assertEqual(release.pll.output_hz, 25_000_000)
        self.assertIn("create_generated_clock -name cpu_clk", sdc)
        self.assertIn("u_clock_pll/clkout", sdc)
        self.assertGreaterEqual(release.target_slack_ns, 1.500)
        self.assertTrue(any("I28-S03" in blocker for blocker in profile_set.blockers))
        self.assertTrue(any("I28-S04" in blocker for blocker in profile_set.blockers))

    def test_cli_validates_json_lists_profiles_plan_and_sdc(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA clock profile issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I28-S01")
        self.assertEqual(parsed["default_profile_id"], "debug_direct_25mhz")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--profiles"])

        self.assertEqual(result, 0)
        self.assertIn("debug_direct_25mhz", stream.getvalue())
        self.assertIn("release_pll_25mhz", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("python tools\\fpga_gowin_build.py --check", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--sdc", "release_pll_25mhz"])

        self.assertEqual(result, 0)
        self.assertIn("create_generated_clock", stream.getvalue())

    def test_documentation_names_profiles_constraints_margins_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-clock-profiles.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I28-S01", text)
        self.assertIn("python tools\\fpga_clock_profiles.py --check", text)
        self.assertIn("debug_direct_25mhz", text)
        self.assertIn("release_pll_25mhz", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("25 MHz", text)
        self.assertIn("Gowin rPLL", text)
        self.assertIn("create_clock", text)
        self.assertIn("create_generated_clock", text)
        self.assertIn("minimum slack", text)
        self.assertIn("target slack", text)
        self.assertIn("I28-S02", text)
        self.assertIn("I28-S03", text)
        self.assertIn("I28-S04", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

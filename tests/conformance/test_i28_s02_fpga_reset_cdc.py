"""I28-S02 conformance tests for FPGA reset and CDC audit coverage."""

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
TOOL = ROOT / "tools" / "fpga_reset_cdc.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_reset_cdc


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_reset_cdc_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaResetCdcTests(unittest.TestCase):
    def test_reset_cdc_self_validation_passes(self) -> None:
        self.assertEqual(fpga_reset_cdc.validate_fpga_reset_cdc(ROOT), ())

    def test_profile_names_dependency_gates_and_clock_profiles(self) -> None:
        profile = fpga_reset_cdc.fpga_reset_cdc_profile()

        self.assertEqual(profile.story, "I28-S02")
        self.assertEqual(
            profile.clock_profile_gate,
            "python tools\\fpga_clock_profiles.py --check",
        )
        self.assertEqual(profile.top_wrapper_gate, "python tools\\fpga_top_wrapper.py --check")
        self.assertEqual(
            profile.uart_status_gate,
            "python tools\\fpga_uart_status_streamer.py --check",
        )
        self.assertEqual(profile.current_clock_profile, "debug_direct_25mhz")
        self.assertEqual(profile.release_clock_profile, "release_pll_25mhz")
        self.assertTrue(any("--top-module cpu_v01_fpga_top_tb" in command for command in profile.lint_commands))

    def test_audit_items_cover_reset_uart_debug_and_generated_clock(self) -> None:
        profile = fpga_reset_cdc.fpga_reset_cdc_profile()
        items = {item.name: item for item in profile.items}

        for name in (
            "board_clk_i",
            "board_reset_n_i",
            "core_rst_n",
            "debug_halt_request_i",
            "uart_tx_o",
            "uart_rx_i",
            "loader_handoff_inputs",
            "status_debug_outputs",
            "release_pll_domain",
        ):
            with self.subTest(name=name):
                self.assertIn(name, items)

        self.assertEqual(items["board_reset_n_i"].status, "implemented_two_stage_sync_release")
        self.assertIn("RESET_SYNC_STAGES", " ".join(items["board_reset_n_i"].evidence_tokens))
        self.assertEqual(items["core_rst_n"].status, "implemented_same_domain_fanout")
        self.assertEqual(items["debug_halt_request_i"].status, "documented_open_issue")
        self.assertIn("two-flop synchronizer", items["debug_halt_request_i"].required_action)
        self.assertEqual(items["uart_tx_o"].status, "implemented_same_domain_output")
        self.assertEqual(items["uart_rx_i"].status, "implemented_two_stage_sync")
        self.assertIn("uart_rx_sync_q", " ".join(items["uart_rx_i"].evidence_tokens))
        self.assertEqual(items["status_debug_outputs"].status, "implemented_same_domain_outputs")
        self.assertEqual(items["release_pll_domain"].status, "blocked_until_pll_wrapper")
        self.assertIn("create_generated_clock", " ".join(items["release_pll_domain"].evidence_tokens))

    def test_open_issues_record_raw_halt_pll_and_loader_sync_boundary(self) -> None:
        profile = fpga_reset_cdc.fpga_reset_cdc_profile()
        text = " ".join(profile.open_issues)

        self.assertIn("debug_halt_request_i", text)
        self.assertIn("release_pll_25mhz", text)
        self.assertIn("loader handoff inputs", text)
        self.assertIn("I28-S03", " ".join(profile.handoffs))
        self.assertIn("I28-S05", " ".join(profile.handoffs))

    def test_cli_validates_json_lists_items_plan_and_open_issues(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA reset/CDC issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I28-S02")
        self.assertEqual(parsed["current_clock_profile"], "debug_direct_25mhz")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--items"])

        self.assertEqual(result, 0)
        self.assertIn("debug_halt_request_i", stream.getvalue())
        self.assertIn("release_pll_domain", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("python tools\\fpga_clock_profiles.py --check", stream.getvalue())
        self.assertIn("verilator --lint-only --timing", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--open-issues"])

        self.assertEqual(result, 0)
        self.assertIn("loader handoff inputs", stream.getvalue())

    def test_documentation_names_reset_cdc_items_evidence_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-reset-cdc-audit.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I28-S02", text)
        self.assertIn("python tools\\fpga_reset_cdc.py --check", text)
        self.assertIn("python tools\\fpga_clock_profiles.py --check", text)
        self.assertIn("python tools\\fpga_top_wrapper.py --check", text)
        self.assertIn("python tools\\fpga_uart_status_streamer.py --check", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("RESET_SYNC_STAGES", text)
        self.assertIn("core_rst_n", text)
        self.assertIn("debug_halt_request_i", text)
        self.assertIn("documented_open_issue", text)
        self.assertIn("uart_tx_o", text)
        self.assertIn("uart_rx_i", text)
        self.assertIn("implemented_two_stage_sync", text)
        self.assertIn("status_debug_outputs", text)
        self.assertIn("release_pll_25mhz", text)
        self.assertIn("create_generated_clock", text)
        self.assertIn("loader handoff inputs", text)
        self.assertIn("I28-S03", text)
        self.assertIn("I28-S05", text)


if __name__ == "__main__":
    unittest.main()

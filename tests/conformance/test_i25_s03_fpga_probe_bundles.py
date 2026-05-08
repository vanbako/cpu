"""I25-S03 conformance tests for FPGA GAO/ILA probe bundles."""

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
TOOL = ROOT / "tools" / "fpga_probe_bundles.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_probe_bundles


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_probe_bundles_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaProbeBundleTests(unittest.TestCase):
    def test_probe_bundle_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_probe_bundles.validate_fpga_probe_bundles(ROOT), ())

    def test_profile_names_prerequisite_gates_and_tools(self) -> None:
        profile = fpga_probe_bundles.fpga_probe_bundle_profile()

        self.assertEqual(profile.story, "I25-S03")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(profile.constraints_gate, "python tools\\fpga_constraints_overlay.py --check")
        self.assertIn("Gowin GAO", profile.supported_tools)
        self.assertIn("generic ILA", profile.supported_tools)
        self.assertIn("does not instantiate analyzer IP", profile.release_policy)

    def test_probe_signals_cover_status_and_memory_failure_capture(self) -> None:
        signals = {signal.name: signal for signal in fpga_probe_bundles.fpga_probe_bundle_profile().signals}

        for required in (
            "probe_board_clk",
            "probe_board_reset_n",
            "probe_core_rst_n",
            "probe_pcc_cursor_low",
            "probe_pc_slot",
            "probe_retire_count",
            "probe_fault_code",
            "probe_pass_led",
            "probe_fail_led",
            "probe_heartbeat",
            "probe_imem_req_valid",
            "probe_imem_req_ready",
            "probe_dmem_req_valid",
            "probe_dmem_req_ready",
            "probe_tagmem_req_valid",
            "probe_tagmem_req_ready",
        ):
            with self.subTest(required=required):
                self.assertIn(required, signals)
                self.assertTrue(signals[required].required_for_failure_capture)

        bundles = {signal.bundle for signal in signals.values()}
        self.assertIn("clock_reset", bundles)
        self.assertIn("status_packet", bundles)
        self.assertIn("memory_handshake", bundles)
        self.assertEqual(signals["probe_pcc_cursor_low"].width, 32)
        self.assertEqual(signals["probe_fault_code"].width, 16)

    def test_triggers_and_non_interference_rules_are_explicit(self) -> None:
        profile = fpga_probe_bundles.fpga_probe_bundle_profile()
        triggers = {trigger.name: trigger for trigger in profile.triggers}

        self.assertIn("reset_release", triggers)
        self.assertIn("first_pass", triggers)
        self.assertIn("first_fault", triggers)
        self.assertIn("memory_stall", triggers)
        self.assertIn("fault", triggers["first_fault"].purpose)
        self.assertTrue(any("retire_ready" in rule for rule in profile.non_interference_rules))
        self.assertTrue(any("same cpu_v01_fpga_top ports" in rule for rule in profile.non_interference_rules))

    def test_cli_validates_json_plan_and_probe_list(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA probe bundle issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I25-S03")
        self.assertEqual(parsed["top_module"], "cpu_v01_fpga_top")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("python tools\\fpga_debug_status_packet.py --check", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        probe_list = stream.getvalue()
        self.assertIn("bundle,name,width,source,required_for_failure_capture", probe_list)
        self.assertIn("memory_handshake,probe_imem_req_valid,1,imem_req_valid,true", probe_list)

    def test_documentation_names_bundles_triggers_and_release_policy(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-probe-bundles.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I25-S03", text)
        self.assertIn("python tools\\fpga_probe_bundles.py --check", text)
        self.assertIn("GAO", text)
        self.assertIn("ILA", text)
        self.assertIn("clock_reset", text)
        self.assertIn("status_packet", text)
        self.assertIn("memory_handshake", text)
        self.assertIn("probe_pcc_cursor_low", text)
        self.assertIn("probe_pc_slot", text)
        self.assertIn("probe_retire_count", text)
        self.assertIn("probe_fault_code", text)
        self.assertIn("probe_pass_led", text)
        self.assertIn("probe_fail_led", text)
        self.assertIn("probe_heartbeat", text)
        self.assertIn("probe_imem_req_valid", text)
        self.assertIn("probe_dmem_req_valid", text)
        self.assertIn("probe_tagmem_req_valid", text)
        self.assertIn("first_fault", text)
        self.assertIn("retire_ready", text)
        self.assertIn("release build", text)


if __name__ == "__main__":
    unittest.main()

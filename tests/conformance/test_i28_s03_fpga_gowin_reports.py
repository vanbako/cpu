"""I28-S03 conformance tests for the automated Gowin report parser."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
from io import StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_gowin_reports.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gowin_reports


BITSTREAM_BYTES = b"i28-s03-bitstream-fixture"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_gowin_reports_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_report_bundle(
    root: Path,
    *,
    timing_text: str | None = None,
    ports_text: str | None = None,
    synthesis_text: str | None = None,
    utilization_text: str | None = None,
) -> None:
    synthesis = root / "impl" / "gwsynthesis"
    pnr = root / "impl" / "pnr"
    synthesis.mkdir(parents=True)
    pnr.mkdir(parents=True)
    (synthesis / "synth.rpt").write_text(
        synthesis_text
        or "\n".join(
            (
                "Top cpu_v01_fpga_top",
                "Instance cpu_v01_core",
                "Warnings: 0",
                "Errors: 0",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "first_timing.rpt").write_text(
        timing_text
        or "\n".join(
            (
                "Clock Summary",
                "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                "Worst Slack: 1.250 ns",
                "Unconstrained paths: 0",
                "Warnings: 0",
                "Errors: 0",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "first_ports.rpt").write_text(
        ports_text
        or "\n".join(
            (
                "board_clk_i LOC P1 IO_TYPE=LVCMOS33",
                "board_reset_n_i LOC P2 IO_TYPE=LVCMOS33",
                "pass_led_o LOC P3 IO_TYPE=LVCMOS33",
                "fail_led_o LOC P4 IO_TYPE=LVCMOS33",
                "heartbeat_led_o LOC P5 IO_TYPE=LVCMOS33",
                "uart_tx_o LOC P6 IO_TYPE=LVCMOS33",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "first_util.rpt").write_text(
        utilization_text or "LUT 10\nRegister 20\nB-SRAM 1\n",
        encoding="utf-8",
    )
    (pnr / "first.fs").write_bytes(BITSTREAM_BYTES)


class FpgaGowinReportsTests(unittest.TestCase):
    def test_gowin_report_parser_self_validation_passes(self) -> None:
        self.assertEqual(fpga_gowin_reports.validate_fpga_gowin_reports(ROOT), ())

    def test_parser_profile_names_globs_gates_and_policies(self) -> None:
        profile = fpga_gowin_reports.fpga_gowin_report_parser_profile()

        self.assertEqual(profile.story, "I28-S03")
        self.assertEqual(profile.build_root.as_posix(), "build/fpga/tang_mega_138k/first_test")
        self.assertEqual(profile.clock_profile_gate, "python tools\\fpga_clock_profiles.py --check")
        self.assertEqual(profile.gowin_build_gate, "python tools\\fpga_gowin_build.py --check")
        self.assertEqual(profile.default_clock_profile, "debug_direct_25mhz")
        for kind in ("synthesis", "timing", "ports", "utilization", "bitstream"):
            self.assertIn(kind, profile.report_globs)
        for port in (
            "board_clk_i",
            "board_reset_n_i",
            "pass_led_o",
            "fail_led_o",
            "heartbeat_led_o",
            "uart_tx_o",
        ):
            self.assertIn(port, profile.required_ports)
        self.assertIn("LUT", profile.required_utilization_metrics)
        self.assertIn("Register", profile.required_utilization_metrics)

    def test_complete_bundle_passes_and_extracts_report_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_gowin_reports.audit_gowin_reports(build_root)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.parse.worst_slack_ns, 1.250)
        self.assertEqual(audit.parse.unconstrained_paths, 0)
        self.assertEqual(audit.policy_violations, ())
        self.assertEqual(audit.missing_ports, ())
        clocks = {clock.name: clock for clock in audit.parse.clock_summary}
        self.assertEqual(clocks["board_clk_i"].frequency_mhz, 25.000)
        self.assertEqual(clocks["board_clk_i"].period_ns, 40.000)
        ports = {port.signal: port for port in audit.parse.port_assignments}
        self.assertEqual(ports["pass_led_o"].location, "P3")
        utilization = {metric.name: metric.value for metric in audit.parse.utilization}
        self.assertEqual(utilization["LUT"], 10)
        self.assertEqual(utilization["Register"], 20)
        self.assertEqual(audit.parse.bitstreams[0].size_bytes, len(BITSTREAM_BYTES))
        self.assertEqual(
            audit.parse.bitstreams[0].sha256,
            hashlib.sha256(BITSTREAM_BYTES).hexdigest(),
        )

    def test_policy_fails_negative_slack_unconstrained_missing_port_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(
                build_root,
                timing_text="\n".join(
                    (
                        "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                        "Worst Slack: -0.100 ns",
                        "Unconstrained paths: 2",
                    )
                ),
                ports_text="board_clk_i LOC P1\nboard_reset_n_i LOC P2\npass_led_o LOC P3\n",
                synthesis_text="Top cpu_v01_fpga_top\nERROR black box cpu_v01_core\n",
            )

            audit = fpga_gowin_reports.audit_gowin_reports(build_root)

        self.assertEqual(audit.status, "failed")
        self.assertIn("negative_timing_slack_at_first_test_clock", audit.policy_violations)
        self.assertIn("unconstrained_paths_present", audit.policy_violations)
        self.assertIn("missing_status_or_uart_observation_pin", audit.policy_violations)
        self.assertIn("forbidden_report_token:black box", audit.policy_violations)
        self.assertIn("gowin_error_or_failed_marker_present", audit.policy_violations)
        self.assertIn("fail_led_o", audit.missing_ports)
        self.assertIn("heartbeat_led_o", audit.missing_ports)
        self.assertIn("uart_tx_o", audit.missing_ports)

    def test_margin_warning_is_not_failure_for_nonnegative_slack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(
                build_root,
                timing_text="\n".join(
                    (
                        "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                        "Worst Slack: 0.500 ns",
                        "Unconstrained paths: 0",
                    )
                ),
            )

            audit = fpga_gowin_reports.audit_gowin_reports(build_root)

        self.assertEqual(audit.status, "passed")
        self.assertIn("timing_slack_below_target_margin", audit.margin_warnings)

    def test_cli_validates_profile_json_and_audits_fixture_bundle(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Gowin report parser issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I28-S03")
        self.assertEqual(parsed["default_clock_profile"], "debug_direct_25mhz")

        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)
            relative = build_root.relative_to(ROOT)

            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit-reports", str(relative)])

        self.assertEqual(result, 0)
        parsed_audit = json.loads(stream.getvalue())
        self.assertEqual(parsed_audit["status"], "passed")
        self.assertEqual(parsed_audit["parse"]["worst_slack_ns"], 1.25)

    def test_documentation_names_parser_outputs_policy_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-gowin-report-parser.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I28-S03", text)
        self.assertIn("python tools\\fpga_gowin_reports.py --check", text)
        self.assertIn("python tools\\fpga_clock_profiles.py --check", text)
        self.assertIn("python tools\\fpga_gowin_build.py --check", text)
        self.assertIn("python tools\\fpga_gowin_reports.py --audit-reports", text)
        self.assertIn("worst slack", text)
        self.assertIn("utilization", text)
        self.assertIn("unconstrained paths", text)
        self.assertIn("port assignments", text)
        self.assertIn("warnings", text)
        self.assertIn("bitstream identity", text)
        self.assertIn("clock summary", text)
        self.assertIn("negative_timing_slack_at_first_test_clock", text)
        self.assertIn("missing_status_or_uart_observation_pin", text)
        self.assertIn("I28-S04", text)
        self.assertIn("I28-S05", text)


if __name__ == "__main__":
    unittest.main()

"""I28-S04 conformance tests for FPGA frequency-margin tracking."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_frequency_margin.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_frequency_margin, fpga_gowin_reports


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_frequency_margin_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_report_bundle(root: Path, *, slack: float = 1.250) -> None:
    synthesis = root / "impl" / "gwsynthesis"
    pnr = root / "impl" / "pnr"
    synthesis.mkdir(parents=True)
    pnr.mkdir(parents=True)
    (synthesis / "synth.rpt").write_text(
        "Top cpu_v01_fpga_top\nInstance cpu_v01_core\nWarnings: 0\nErrors: 0\n",
        encoding="utf-8",
    )
    (pnr / "first_timing.rpt").write_text(
        "\n".join(
            (
                "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                f"Worst Slack: {slack:.3f} ns",
                "Unconstrained paths: 0",
                "Warnings: 0",
                "Errors: 0",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "first_ports.rpt").write_text(
        "\n".join(
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
    (pnr / "first_util.rpt").write_text("LUT 10\nRegister 20\n", encoding="utf-8")
    (pnr / "first.fs").write_bytes(b"i28-s04-bitstream")


class FpgaFrequencyMarginTests(unittest.TestCase):
    def test_frequency_margin_self_validation_passes(self) -> None:
        self.assertEqual(fpga_frequency_margin.validate_fpga_frequency_margin(ROOT), ())

    def test_default_summary_keeps_conservative_blocker_defaults(self) -> None:
        summary = fpga_frequency_margin.fpga_frequency_margin_summary()

        self.assertEqual(summary.story, "I28-S04")
        self.assertEqual(summary.status, "documented_blocker")
        self.assertEqual(summary.parser_gate, "python tools\\fpga_gowin_reports.py --check")
        self.assertEqual(summary.clock_profile_gate, "python tools\\fpga_clock_profiles.py --check")
        self.assertEqual(summary.current_default_profile, "debug_direct_25mhz")
        self.assertEqual(summary.selected_debug_default_hz, 25_000_000)
        self.assertEqual(summary.selected_release_default_hz, 25_000_000)
        self.assertIsNone(summary.maximum_passing_hz)
        self.assertEqual(summary.maximum_passing_profile, "")
        self.assertIn("i28_s04_frequency_sweep.json", summary.evidence_path.as_posix())
        self.assertTrue(any("25 MHz" in blocker for blocker in summary.blockers))

    def test_report_audits_become_sweep_points_and_track_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first_root = Path(first_tmp)
            second_root = Path(second_tmp)
            write_report_bundle(first_root, slack=1.250)
            write_report_bundle(second_root, slack=2.000)

            first_audit = fpga_gowin_reports.audit_gowin_reports(first_root)
            second_audit = fpga_gowin_reports.audit_gowin_reports(second_root)
            first = fpga_frequency_margin.sweep_point_from_report_audit(
                first_audit,
                requested_hz=25_000_000,
                notes="baseline",
            )
            second = fpga_frequency_margin.sweep_point_from_report_audit(
                second_audit,
                requested_hz=40_000_000,
                notes="sweep high",
            )
            summary = fpga_frequency_margin.fpga_frequency_margin_summary((second, first))

        self.assertTrue(first.passed)
        self.assertTrue(second.passed)
        self.assertEqual(first.worst_slack_ns, 1.250)
        self.assertEqual(second.requested_hz, 40_000_000)
        self.assertEqual(summary.status, "evidence_recorded")
        self.assertEqual(summary.maximum_passing_hz, 40_000_000)
        self.assertEqual(summary.maximum_passing_profile, "debug_direct_25mhz")
        self.assertEqual(summary.selected_debug_default_hz, 25_000_000)
        self.assertEqual(summary.selected_release_default_hz, 25_000_000)

    def test_margin_warning_is_preserved_in_sweep_point(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root, slack=0.500)
            audit = fpga_gowin_reports.audit_gowin_reports(build_root)
            point = fpga_frequency_margin.sweep_point_from_report_audit(audit)

        self.assertTrue(point.passed)
        self.assertFalse(point.target_margin_met)
        self.assertIn("timing_slack_below_target_margin", point.margin_warnings)

    def test_cli_validates_json_template_and_audits_fixture_bundle(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA frequency margin issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I28-S04")
        self.assertEqual(parsed["selected_debug_default_hz"], 25_000_000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)
            relative = build_root.relative_to(ROOT)

            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(
                    ["--audit-reports", str(relative), "--requested-hz", "25000000"]
                )

        self.assertEqual(result, 0)
        audit_json = json.loads(stream.getvalue())
        self.assertEqual(audit_json["status"], "evidence_recorded")
        self.assertEqual(audit_json["maximum_passing_hz"], 25_000_000)

    def test_documentation_names_defaults_sweep_fields_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-frequency-margin.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I28-S04", text)
        self.assertIn("python tools\\fpga_frequency_margin.py --check", text)
        self.assertIn("python tools\\fpga_gowin_reports.py --check", text)
        self.assertIn("debug_direct_25mhz", text)
        self.assertIn("25 MHz", text)
        self.assertIn("maximum passing", text)
        self.assertIn("selected_debug_default_hz", text)
        self.assertIn("selected_release_default_hz", text)
        self.assertIn("documented_blocker", text)
        self.assertIn("frequency sweep", text)
        self.assertIn("worst slack", text)
        self.assertIn("bitstream_sha256", text)
        self.assertIn("I28-S05", text)
        self.assertIn("I29", text)


if __name__ == "__main__":
    unittest.main()

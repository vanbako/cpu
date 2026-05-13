"""I35-S05 conformance tests for the FPGA video scanout evidence gate."""

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
TOOL = ROOT / "tools" / "fpga_video_scanout_gate.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_scanout_gate


BITSTREAM_BYTES = b"i35-s05-video-scanout-gate-fixture"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_scanout_gate_tool", TOOL)
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
                "Warnings: 0",
                "Errors: 0",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "video_timing.rpt").write_text(
        timing_text
        or "\n".join(
            (
                "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                "Clock video_pixel_clk Frequency 74.250 MHz Period 13.468 ns",
                "Worst Slack: 1.000 ns",
                "Unconstrained paths: 0",
                "Warnings: 0",
                "Errors: 0",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "video_ports.rpt").write_text(
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
    (pnr / "video_util.rpt").write_text(
        utilization_text or "LUT 128\nRegister 256\nB-SRAM 2\n",
        encoding="utf-8",
    )
    (pnr / "video.fs").write_bytes(BITSTREAM_BYTES)


class FpgaVideoScanoutGateTests(unittest.TestCase):
    def test_video_scanout_gate_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_scanout_gate.validate_fpga_video_scanout_gate(ROOT), ())

    def test_profile_names_prerequisites_exact_timing_and_evidence(self) -> None:
        profile = fpga_video_scanout_gate.fpga_video_scanout_gate_profile()

        self.assertEqual(profile.story, "I35-S05")
        self.assertEqual(profile.timing_gate, "python tools\\fpga_video_timing.py --check")
        self.assertEqual(profile.output_gate, "python tools\\fpga_video_output.py --check")
        self.assertEqual(profile.mmio_gate, "python tools\\fpga_video_mmio.py --check")
        self.assertEqual(profile.report_gate, "python tools\\fpga_gowin_reports.py --check")
        self.assertEqual(profile.active_width, 1280)
        self.assertEqual(profile.active_height, 720)
        self.assertEqual(profile.h_total, 1650)
        self.assertEqual(profile.v_total, 750)
        self.assertEqual(profile.pixel_clock_hz, 74_250_000)
        self.assertEqual(profile.vblank_start_cycles, 1_188_000)
        self.assertEqual(profile.frame_cycles, 1_237_500)
        self.assertIn("rtl/cpu_v01_fpga_video_scanout_gate_tb.sv", profile.testbench)
        self.assertIn("--top-module cpu_v01_fpga_video_scanout_gate_tb", profile.verilator_commands[0])
        check_names = {check.name for check in profile.evidence_checks}
        self.assertIn("combined_scanout_mmio_irq", check_names)
        self.assertIn("gowin_report_fields", check_names)
        self.assertIn("cdc", profile.cdc_warning_tokens)

    def test_executable_summary_proves_timing_and_vblank_irq(self) -> None:
        summary = fpga_video_scanout_gate.simulate_video_scanout_gate_summary()

        self.assertEqual(summary.active_pixels, 921_600)
        self.assertEqual(summary.hsync_pixels, 30_000)
        self.assertEqual(summary.vsync_pixels, 8_250)
        self.assertEqual(summary.vblank_pixels, 49_500)
        self.assertEqual(summary.vblank_start_cycle, 1_188_000)
        self.assertEqual(summary.frame_cycles, 1_237_500)
        self.assertEqual(summary.frames_completed, 1)
        self.assertEqual((summary.final_h_count, summary.final_v_count), (0, 0))
        self.assertTrue(summary.irq_asserted_on_vblank)
        self.assertTrue(summary.irq_cleared_after_ack)
        self.assertEqual(summary.pattern_select, 2)
        self.assertEqual(summary.background_rgb, 0x123456)

    def test_report_audit_passes_video_clock_and_fails_cdc_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_video_scanout_gate.audit_video_scanout_reports(build_root)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.video_clock_frequency_mhz, 74.250)
        self.assertEqual(audit.unconstrained_paths, 0)
        self.assertIn("LUT", audit.utilization_metrics)
        self.assertEqual(audit.policy_violations, ())
        self.assertEqual(audit.missing_fields, ())

        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(
                build_root,
                timing_text="\n".join(
                    (
                        "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                        "Clock video_pixel_clk Frequency 74.250 MHz Period 13.468 ns",
                        "Worst Slack: 1.000 ns",
                        "Unconstrained paths: 0",
                        "Warning: CDC path between board_clk_i and video_pixel_clk",
                        "Errors: 0",
                    )
                ),
            )

            audit = fpga_video_scanout_gate.audit_video_scanout_reports(build_root)

        self.assertEqual(audit.status, "failed")
        self.assertIn("unexpected_video_cdc_warning", audit.policy_violations)
        self.assertTrue(audit.cdc_warning_lines)

    def test_report_audit_fails_missing_or_wrong_video_clock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(
                build_root,
                timing_text="\n".join(
                    (
                        "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                        "Worst Slack: 1.000 ns",
                        "Unconstrained paths: 0",
                        "Warnings: 0",
                        "Errors: 0",
                    )
                ),
            )

            audit = fpga_video_scanout_gate.audit_video_scanout_reports(build_root)

        self.assertEqual(audit.status, "failed")
        self.assertIn("video_pixel_clk_clock_summary", audit.missing_fields)

        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(
                build_root,
                timing_text="\n".join(
                    (
                        "Clock board_clk_i Frequency 25.000 MHz Period 40.000 ns",
                        "Clock video_pixel_clk Frequency 25.000 MHz Period 40.000 ns",
                        "Worst Slack: 1.000 ns",
                        "Unconstrained paths: 0",
                        "Warnings: 0",
                        "Errors: 0",
                    )
                ),
            )

            audit = fpga_video_scanout_gate.audit_video_scanout_reports(build_root)

        self.assertEqual(audit.status, "failed")
        self.assertIn("video_pixel_clk_frequency_mismatch", audit.policy_violations)

    def test_rtl_and_documentation_name_scanout_gate_contract(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_video_scanout_gate_tb.sv").read_text(
            encoding="utf-8"
        )
        doc = (ROOT / "docs" / "implementation" / "fpga-video-scanout-gate.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_video_scanout_gate_tb",
            "VBLANK_START_CYCLES = 720 * 1650",
            "FULL_FRAME_CYCLES = 750 * 1650",
            "cpu_v01_fpga_video_output_boundary video_output",
            "cpu_v01_fpga_video_mmio video_mmio",
            "FPGA video scanout gate did not reach vblank",
            "FPGA video scanout gate did not raise vblank IRQ",
            "FPGA video scanout gate frame count readback mismatch",
            "FPGA video scanout gate unexpected underflow count",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

        for token in (
            "Story: I35-S05",
            "python tools\\fpga_video_scanout_gate.py --check",
            "python tools\\fpga_video_timing.py --check",
            "python tools\\fpga_video_output.py --check",
            "python tools\\fpga_video_mmio.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "cpu_v01_fpga_video_scanout_gate_tb",
            "1280x720",
            "74.25 MHz",
            "vblank IRQ",
            "video_pixel_clk",
            "utilization",
            "unconstrained paths",
            "unexpected_video_cdc_warning",
            "I35-S06",
            "I36-S04",
        ):
            with self.subTest(token=token):
                self.assertIn(token, doc)

    def test_cli_validates_json_summary_plan_and_report_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video scanout gate issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S05")
        self.assertEqual(parsed["frame_cycles"], 1_237_500)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--summary"])

        self.assertEqual(result, 0)
        summary = json.loads(stream.getvalue())
        self.assertTrue(summary["irq_asserted_on_vblank"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("cpu_v01_fpga_video_scanout_gate_tb", stream.getvalue())

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
        self.assertEqual(
            parsed_audit["video_clock_frequency_mhz"],
            74.25,
        )

    def test_fixture_bitstream_hash_is_stable(self) -> None:
        self.assertEqual(
            hashlib.sha256(BITSTREAM_BYTES).hexdigest(),
            "8df83bf2f74a884bbb8d28917ab338f2def4edfd929da14b581c15dab7bdb5d5",
        )


if __name__ == "__main__":
    unittest.main()

"""I31-S02 conformance tests for first-pass Gowin build evidence."""

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
TOOL = ROOT / "tools" / "fpga_first_pass_gowin.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_bundle, fpga_first_pass_gowin


BITSTREAM_BYTES = b"i31-s02-bitstream-fixture"
BITSTREAM_SHA = hashlib.sha256(BITSTREAM_BYTES).hexdigest()


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_gowin_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def frozen_bundle_audit() -> fpga_first_pass_bundle.FirstPassBundleAudit:
    return fpga_first_pass_bundle.FirstPassBundleAudit(
        status="frozen",
        message="frozen",
        evidence_path="i31_s01.txt",
        missing_fields=(),
        link_issues=(),
        selection_issues=(),
        blocker_issues=(),
        actions=(),
    )


def complete_gowin_text() -> str:
    return (
        fpga_first_pass_gowin.first_pass_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-10T12:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("bitstream_sha256=", f"bitstream_sha256={BITSTREAM_SHA}")
        .replace("worst_slack_ns=", "worst_slack_ns=1.250")
    )


def write_report_bundle(root: Path, *, timing_text: str | None = None) -> None:
    synthesis = root / "impl" / "gwsynthesis"
    pnr = root / "impl" / "pnr"
    synthesis.mkdir(parents=True)
    pnr.mkdir(parents=True)
    (synthesis / "synth.rpt").write_text(
        "Top cpu_v01_fpga_top\nInstance cpu_v01_core\nWarnings: 0\nErrors: 0\n",
        encoding="utf-8",
    )
    (pnr / "place_route.rpt").write_text("Place route completed\n", encoding="utf-8")
    (pnr / "first_timing.rpt").write_text(
        timing_text
        or "\n".join(
            (
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
    (pnr / "warnings.rpt").write_text("Warnings: 0\nErrors: 0\n", encoding="utf-8")
    (pnr / "first.fs").write_bytes(BITSTREAM_BYTES)


class FpgaFirstPassGowinTests(unittest.TestCase):
    def test_first_pass_gowin_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_pass_gowin.validate_fpga_first_pass_gowin(ROOT), ())

    def test_profile_names_bundle_report_gates_selection_and_requirements(self) -> None:
        profile = fpga_first_pass_gowin.fpga_first_pass_gowin_profile()

        self.assertEqual(profile.story, "I31-S02")
        self.assertEqual(profile.status, "blocked_until_gowin_reports")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i31_s02_gowin_build_timing.txt",
        )
        self.assertEqual(profile.bundle_gate, "python tools\\fpga_first_pass_bundle.py --check")
        self.assertEqual(profile.gowin_build_gate, "python tools\\fpga_gowin_build.py --check")
        self.assertEqual(profile.gowin_reports_gate, "python tools\\fpga_gowin_reports.py --check")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.selected_image, "builtin.first_test_pause_stream")
        self.assertEqual(profile.clock_profile, "debug_direct_25mhz")
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", profile.gowin_run_command)

        requirements = {requirement.name: requirement for requirement in profile.requirements}
        for requirement in (
            "synthesis",
            "place_route",
            "timing",
            "utilization",
            "ports",
            "warning_policy",
            "bitstream",
        ):
            self.assertIn(requirement, requirements)
        self.assertEqual(requirements["bitstream"].field, "bitstream_path")
        self.assertIn("unconstrained", requirements["timing"].required_policy)
        self.assertIn("uart_tx_o", profile.required_ports)

    def test_template_and_key_value_audit_accept_complete_record(self) -> None:
        template = fpga_first_pass_gowin.first_pass_gowin_template()
        self.assertIn("story=I31-S02", template)
        self.assertIn("synthesis_report=", template)
        self.assertIn("place_route_report=", template)
        self.assertIn("bitstream_sha256=", template)
        self.assertIn("build_result=gowin_build_pass", template)

        audit = fpga_first_pass_gowin.audit_first_pass_gowin(
            fpga_first_pass_gowin.parse_first_pass_gowin(complete_gowin_text())
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.timing_issues, ())
        self.assertEqual(audit.policy_issues, ())
        self.assertIn("I31-S03", " ".join(audit.actions))

    def test_key_value_audit_rejects_negative_slack_unconstrained_and_bad_hash(self) -> None:
        negative = complete_gowin_text().replace("worst_slack_ns=1.250", "worst_slack_ns=-0.100")
        audit = fpga_first_pass_gowin.audit_first_pass_gowin(
            fpga_first_pass_gowin.parse_first_pass_gowin(negative)
        )
        self.assertEqual(audit.status, "failed")
        self.assertIn("negative_timing_slack_at_first_test_clock", audit.timing_issues)

        unconstrained = complete_gowin_text().replace("unconstrained_paths=0", "unconstrained_paths=2")
        audit = fpga_first_pass_gowin.audit_first_pass_gowin(
            fpga_first_pass_gowin.parse_first_pass_gowin(unconstrained)
        )
        self.assertEqual(audit.status, "failed")
        self.assertIn("unconstrained_paths_present", audit.timing_issues)

        bad_hash = complete_gowin_text().replace(f"bitstream_sha256={BITSTREAM_SHA}", "bitstream_sha256=bad")
        audit = fpga_first_pass_gowin.audit_first_pass_gowin(
            fpga_first_pass_gowin.parse_first_pass_gowin(bad_hash)
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256 must be a 64-character hex digest", audit.policy_issues)

    def test_report_bundle_audit_passes_fixture_and_fails_timing_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_first_pass_gowin.audit_first_pass_gowin_reports(
                build_root,
                bundle_audit=frozen_bundle_audit(),
            )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.report_status, "passed")
        self.assertTrue(any(path.endswith(".fs") for path in audit.bitstreams))

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
            )

            audit = fpga_first_pass_gowin.audit_first_pass_gowin_reports(
                build_root,
                bundle_audit=frozen_bundle_audit(),
            )

        self.assertEqual(audit.status, "failed")
        self.assertIn("negative_timing_slack_at_first_test_clock", audit.policy_issues)
        self.assertIn("unconstrained_paths_present", audit.policy_issues)

    def test_default_report_audit_blocks_without_frozen_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_first_pass_gowin.audit_first_pass_gowin_reports(build_root)

        self.assertEqual(audit.status, "blocked")
        self.assertNotEqual(audit.bundle_status, "frozen")

    def test_cli_validates_json_template_requirements_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass Gowin issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S02")
        self.assertEqual(parsed["clock_profile"], "debug_direct_25mhz")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--requirements"])

        self.assertEqual(result, 0)
        self.assertIn("timing", stream.getvalue())
        self.assertIn("bitstream", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_gowin_reports.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i31_s02.txt"
            evidence.write_text(complete_gowin_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "passed")

    def test_documentation_names_reports_policy_bitstream_and_handoff(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-gowin-build.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S02",
            "python tools\\fpga_first_pass_gowin.py --check",
            "docs/implementation/evidence/i31_s02_gowin_build_timing.txt",
            "python tools\\fpga_first_pass_bundle.py --check",
            "python tools\\fpga_gowin_build.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "synthesis_report",
            "place_route_report",
            "timing_report",
            "utilization_report",
            "ports_report",
            "warning_policy",
            "bitstream_path",
            "bitstream_sha256",
            "negative_timing_slack_at_first_test_clock",
            "unconstrained_paths",
            "I31-S03",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

"""I34-S03 conformance tests for Retro Console Gowin build audit."""

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
TOOL = ROOT / "tools" / "fpga_retro_console_gowin.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import (
    fpga_retro_console_constraints,
    fpga_retro_console_gowin,
    fpga_retro_console_identity,
)


BITSTREAM_BYTES = b"i34-s03-retro-console-bitstream-fixture"
BITSTREAM_SHA = hashlib.sha256(BITSTREAM_BYTES).hexdigest()


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_retro_console_gowin_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def selected_identity_audit() -> fpga_retro_console_identity.RetroConsoleIdentityAudit:
    record = fpga_retro_console_identity.parse_identity_record(
        "\n".join(
            (
                "story=I34-S01",
                "board=Sipeed Tang Retro Console with 60K SOM",
                "source=programmer_jtag_scan",
                "observed_device=GW5AT-60B",
                "observed_idcode=0x0001481B",
                "observed_package=scan_recorded_package",
                "observed_device_version=B",
                "gowin_part=GW5AT-60B-scan-recorded",
                "programming_path=Gowin Programmer SRAM",
                "clock_sources=verified Retro Console oscillator",
                "reset_sources=verified Retro Console reset input",
                "visible_outputs=heartbeat/pass/fail outputs",
                "uart_debug_access=verified UART status path",
                "selected_first_target=no",
                "primary_138k_target=Sipeed Tang Mega Dock with 138K SOM",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-11T12:00:00",
            )
        )
    )
    return fpga_retro_console_identity.audit_identity_record(record)


def confirmed_constraints_audit() -> fpga_retro_console_constraints.RetroConstraintAudit:
    return fpga_retro_console_constraints.RetroConstraintAudit(
        status="confirmed",
        message="confirmed",
        evidence_path="docs/implementation/evidence/i34_s02_retro_console_pins.txt",
        identity_status="alternate_target_verified",
        missing_fields=(),
        missing_pins=(),
        actions=(),
    )


def complete_gowin_text() -> str:
    return (
        fpga_retro_console_gowin.retro_console_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-11T22:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("gowin_part=", "gowin_part=GW5AT-60B-scan-recorded")
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
    (pnr / "retro_first.fs").write_bytes(BITSTREAM_BYTES)


class FpgaRetroConsoleGowinTests(unittest.TestCase):
    def test_retro_console_gowin_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_retro_console_gowin.validate_fpga_retro_console_gowin(ROOT),
            (),
        )

    def test_profile_names_prerequisites_target_and_requirements(self) -> None:
        profile = fpga_retro_console_gowin.fpga_retro_console_gowin_profile()

        self.assertEqual(profile.story, "I34-S03")
        self.assertEqual(profile.status, "blocked_until_retro_console_gowin_reports")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt",
        )
        self.assertEqual(profile.board, "Sipeed Tang Retro Console with 60K SOM")
        self.assertEqual(profile.identity_gate, "python tools\\fpga_retro_console_identity.py --check")
        self.assertEqual(profile.constraints_gate, "python tools\\fpga_retro_console_constraints.py --check")
        self.assertEqual(profile.report_parser_gate, "python tools\\fpga_gowin_reports.py --check")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.clock_profile, "debug_direct_25mhz")
        self.assertEqual(profile.build_root.as_posix(), "build/fpga/tang_60k_retro_console/first_test")
        self.assertIn("gw_sh build/fpga/tang_60k_retro_console/first_test/run_gowin.tcl", profile.gowin_run_command)

        requirements = {requirement.name: requirement for requirement in profile.requirements}
        for requirement in (
            "identity",
            "constraints",
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
        self.assertIn("I34-S04", " ".join(profile.handoffs))

    def test_template_and_key_value_audit_accept_complete_record(self) -> None:
        template = fpga_retro_console_gowin.retro_console_gowin_template()
        self.assertIn("story=I34-S03", template)
        self.assertIn("board=Sipeed Tang Retro Console with 60K SOM", template)
        self.assertIn("build_root=build/fpga/tang_60k_retro_console/first_test", template)
        self.assertIn("synthesis_report=", template)
        self.assertIn("place_route_report=", template)
        self.assertIn("bitstream_sha256=", template)
        self.assertIn("build_result=retro_console_gowin_build_pass", template)

        audit = fpga_retro_console_gowin.audit_retro_console_gowin(
            fpga_retro_console_gowin.parse_retro_console_gowin(complete_gowin_text())
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.timing_issues, ())
        self.assertEqual(audit.policy_issues, ())
        self.assertIn("I34-S04", " ".join(audit.actions))

    def test_key_value_audit_rejects_wrong_target_negative_slack_and_bad_hash(self) -> None:
        wrong_target = complete_gowin_text().replace(
            "build_root=build/fpga/tang_60k_retro_console/first_test",
            "build_root=build/fpga/tang_mega_138k/first_test",
        )
        audit = fpga_retro_console_gowin.audit_retro_console_gowin(
            fpga_retro_console_gowin.parse_retro_console_gowin(wrong_target)
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("build_root", " ".join(audit.link_issues))

        negative = complete_gowin_text().replace("worst_slack_ns=1.250", "worst_slack_ns=-0.100")
        audit = fpga_retro_console_gowin.audit_retro_console_gowin(
            fpga_retro_console_gowin.parse_retro_console_gowin(negative)
        )
        self.assertEqual(audit.status, "failed")
        self.assertIn("negative_timing_slack_at_first_test_clock", audit.timing_issues)

        bad_hash = complete_gowin_text().replace(f"bitstream_sha256={BITSTREAM_SHA}", "bitstream_sha256=bad")
        audit = fpga_retro_console_gowin.audit_retro_console_gowin(
            fpga_retro_console_gowin.parse_retro_console_gowin(bad_hash)
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256 must be a 64-character hex digest", audit.policy_issues)

    def test_report_bundle_audit_passes_fixture_and_fails_timing_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_retro_console_gowin.audit_retro_console_gowin_reports(
                build_root,
                identity_audit=selected_identity_audit(),
                constraints_audit=confirmed_constraints_audit(),
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

            audit = fpga_retro_console_gowin.audit_retro_console_gowin_reports(
                build_root,
                identity_audit=selected_identity_audit(),
                constraints_audit=confirmed_constraints_audit(),
            )

        self.assertEqual(audit.status, "failed")
        self.assertIn("negative_timing_slack_at_first_test_clock", audit.policy_issues)
        self.assertIn("unconstrained_paths_present", audit.policy_issues)

    def test_default_report_audit_blocks_without_identity_or_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_report_bundle(build_root)

            audit = fpga_retro_console_gowin.audit_retro_console_gowin_reports(build_root)

        self.assertEqual(audit.status, "blocked")
        self.assertNotEqual(audit.constraints_status, "confirmed")

    def test_cli_validates_json_template_requirements_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Retro Console Gowin issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I34-S03")
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
        self.assertIn("fpga_retro_console_constraints.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i34_s03.txt"
            evidence.write_text(complete_gowin_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "passed")

    def test_documentation_names_reports_policy_bitstream_and_handoff(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-retro-console-gowin-build.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I34-S03",
            "python tools\\fpga_retro_console_gowin.py --check",
            "docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt",
            "python tools\\fpga_retro_console_identity.py --check",
            "python tools\\fpga_retro_console_constraints.py --check",
            "python tools\\fpga_clock_profiles.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "Sipeed Tang Retro Console with 60K SOM",
            "build/fpga/tang_60k_retro_console/first_test",
            "gowin_part",
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
            "not claim a Tang Mega Dock with 138K SOM pass",
            "I34-S04",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

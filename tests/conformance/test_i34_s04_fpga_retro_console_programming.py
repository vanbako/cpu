"""I34-S04 conformance tests for Retro Console programming observations."""

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
TOOL = ROOT / "tools" / "fpga_retro_console_programming.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import (
    fpga_debug_status,
    fpga_retro_console_gowin,
    fpga_retro_console_programming,
)


BITSTREAM_SHA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_retro_console_programming_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def passed_gowin() -> fpga_retro_console_gowin.RetroConsoleGowinAudit:
    return fpga_retro_console_gowin.RetroConsoleGowinAudit(
        status="passed",
        message="passed",
        evidence_path="docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt",
        identity_status="alternate_target_verified",
        constraints_status="confirmed",
        report_status="passed",
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=("build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs",),
        actions=(),
    )


def complete_programming_text() -> str:
    return (
        fpga_retro_console_programming.retro_console_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-11T23:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("bitstream_sha256=", f"bitstream_sha256={BITSTREAM_SHA}")
    )


def failure_packet_hex() -> str:
    packet = fpga_debug_status.DebugStatusPacket(
        flags=fpga_debug_status.debug_status_flag_mask(
            "reset_observed",
            "retire_valid",
            "fault_valid",
            "fail_led",
            "heartbeat",
        ),
        slot=0,
        pass_fail_state=3,
        pc_cell=0x1008,
        retire_count=4,
        fault_code=8,
        trap_cause=8,
        build_id=0x3404C0DE,
        sequence=2,
    )
    return fpga_debug_status.encode_debug_status_packet(packet).hex()


class FpgaRetroConsoleProgrammingTests(unittest.TestCase):
    def test_retro_console_programming_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_retro_console_programming.validate_fpga_retro_console_programming(ROOT),
            (),
        )

    def test_profile_names_gates_fields_and_blockers(self) -> None:
        profile = fpga_retro_console_programming.fpga_retro_console_programming_profile()

        self.assertEqual(profile.story, "I34-S04")
        self.assertEqual(profile.status, "blocked_until_retro_console_sram_observation")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i34_s04_retro_console_programming.txt",
        )
        self.assertEqual(profile.board, "Sipeed Tang Retro Console with 60K SOM")
        self.assertEqual(profile.gowin_gate, "python tools\\fpga_retro_console_gowin.py --check")
        self.assertEqual(profile.identity_gate, "python tools\\fpga_retro_console_identity.py --check")
        self.assertEqual(profile.uart_status_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.probe_gate, "python tools\\fpga_probe_bundles.py --check")
        self.assertEqual(profile.required_mode, "SRAM")
        self.assertGreaterEqual(profile.minimum_observation_seconds, 10)

        for field in (
            "bitstream_sha256",
            "programming_log",
            "reset_released",
            "reset_observation",
            "heartbeat_observed",
            "pass_output_observed",
            "fail_output_observed",
            "status_retire_count",
            "status_fault_code",
            "pass_fail_state",
            "primary_138k_claim",
        ):
            self.assertTrue(profile.field_by_name(field).required)
        self.assertFalse(profile.field_by_name("uart_status_packet_hex").required)
        self.assertFalse(profile.field_by_name("probe_capture").required)

    def test_template_and_audit_accept_smoke_pass_record(self) -> None:
        template = fpga_retro_console_programming.retro_console_programming_template()
        self.assertIn("story=I34-S04", template)
        self.assertIn("programming_mode=SRAM", template)
        self.assertIn("primary_138k_claim=no", template)
        self.assertIn("uart_status_packet_hex=", template)
        self.assertIn("probe_capture=none", template)

        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(complete_programming_text()),
            gowin_audit=passed_gowin(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "observed")
        self.assertEqual(audit.board_result, "retro_console_smoke_pass")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.observation_issues, ())
        self.assertEqual(audit.packet_issues, ())
        self.assertIn("I34-S06", " ".join(audit.actions))

    def test_audit_accepts_failure_capture_for_i34_s05_handoff(self) -> None:
        text = (
            complete_programming_text()
            .replace("pass_output_observed=yes", "pass_output_observed=no")
            .replace("fail_output_observed=no", "fail_output_observed=yes")
            .replace("board_result=retro_console_smoke_pass", "board_result=failure_observed")
            .replace(
                "uart_status_packet_hex="
                + fpga_debug_status.encode_debug_status_packet(
                    fpga_debug_status.example_debug_status_packet()
                ).hex(),
                "uart_status_packet_hex=" + failure_packet_hex(),
            )
            .replace("status_retire_count=8", "status_retire_count=4")
            .replace("status_fault_code=0", "status_fault_code=8")
            .replace("pass_fail_state=first_pass", "pass_fail_state=failed")
            .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i34_s04_probe.csv")
        )
        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(text),
            gowin_audit=passed_gowin(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.board_result, "failure_observed")
        self.assertIn("I34-S05", " ".join(audit.actions))

    def test_audit_blocks_without_passed_gowin_and_rejects_bad_claim_or_observation(self) -> None:
        blocked_gowin = fpga_retro_console_gowin.RetroConsoleGowinAudit(
            status="blocked",
            message="blocked",
            evidence_path="i34_s03.txt",
            identity_status="blocked",
            constraints_status="blocked",
            report_status="blocked",
            missing_fields=(),
            link_issues=(),
            timing_issues=(),
            policy_issues=(),
            bitstreams=(),
            actions=(),
        )
        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(complete_programming_text()),
            gowin_audit=blocked_gowin,
        )
        self.assertEqual(audit.status, "blocked")

        bad_claim = complete_programming_text().replace("primary_138k_claim=no", "primary_138k_claim=yes")
        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(bad_claim),
            gowin_audit=passed_gowin(),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("primary_138k_claim must be no", audit.link_issues)

        bad_packet = complete_programming_text().replace(
            "uart_status_packet_hex=",
            "uart_status_packet_hex=bad",
        )
        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(bad_packet),
            gowin_audit=passed_gowin(),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("uart_status_packet_hex must encode exactly 32 bytes", audit.packet_issues)

        no_capture = (
            complete_programming_text()
            .replace("uart_log=docs/implementation/evidence/i34_s04_uart.log", "uart_log=none")
            .replace(
                "uart_status_packet_hex="
                + fpga_debug_status.encode_debug_status_packet(
                    fpga_debug_status.example_debug_status_packet()
                ).hex(),
                "uart_status_packet_hex=none",
            )
        )
        audit = fpga_retro_console_programming.audit_retro_console_programming(
            fpga_retro_console_programming.parse_retro_console_programming(no_capture),
            gowin_audit=passed_gowin(),
        )
        self.assertEqual(audit.status, "needs_capture")
        self.assertIn("UART status packet or probe_capture evidence is required", audit.observation_issues)

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_retro_console_programming.load_retro_console_programming_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("primary_138k_claim", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Retro Console programming issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I34-S04")
        self.assertEqual(parsed["required_mode"], "SRAM")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("primary_138k_claim=no", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_retro_console_gowin.py", stream.getvalue())
        self.assertIn("fpga_uart_status_streamer.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i34_s04.txt"
            evidence.write_text(complete_programming_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "observed")

    def test_documentation_names_required_evidence_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-retro-console-programming.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I34-S04",
            "python tools\\fpga_retro_console_programming.py --check",
            "docs/implementation/evidence/i34_s04_retro_console_programming.txt",
            "python tools\\fpga_retro_console_gowin.py --check",
            "python tools\\fpga_uart_status_streamer.py --check",
            "python tools\\fpga_probe_bundles.py --check",
            "Sipeed Tang Retro Console with 60K SOM",
            "programming_log",
            "reset_released",
            "heartbeat_observed",
            "pass_output_observed",
            "fail_output_observed",
            "uart_status_packet_hex",
            "probe_capture",
            "bitstream_sha256",
            "primary_138k_claim=no",
            "retro_console_smoke_pass",
            "failure_observed",
            "not claim a Tang Mega Dock with 138K SOM pass",
            "I34-S05",
            "I34-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

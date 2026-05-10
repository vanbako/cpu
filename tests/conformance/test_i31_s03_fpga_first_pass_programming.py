"""I31-S03 conformance tests for integrated CPU programming observations."""

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
TOOL = ROOT / "tools" / "fpga_first_pass_programming.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status, fpga_first_pass_gowin, fpga_first_pass_programming


BITSTREAM_SHA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_programming_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def passed_gowin() -> fpga_first_pass_gowin.FirstPassGowinAudit:
    return fpga_first_pass_gowin.FirstPassGowinAudit(
        status="passed",
        message="passed",
        evidence_path="docs/implementation/evidence/i31_s02_gowin_build_timing.txt",
        bundle_status="frozen",
        report_status="passed",
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=("build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",),
        actions=(),
    )


def complete_programming_text() -> str:
    return (
        fpga_first_pass_programming.first_pass_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-10T12:00:00")
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
        build_id=0x2501C0DE,
        sequence=2,
    )
    return fpga_debug_status.encode_debug_status_packet(packet).hex()


class FpgaFirstPassProgrammingTests(unittest.TestCase):
    def test_first_pass_programming_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_pass_programming.validate_fpga_first_pass_programming(ROOT), ())

    def test_profile_names_gates_fields_and_blockers(self) -> None:
        profile = fpga_first_pass_programming.fpga_first_pass_programming_profile()

        self.assertEqual(profile.story, "I31-S03")
        self.assertEqual(profile.status, "blocked_until_sram_observation")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt",
        )
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.selected_image, "builtin.first_test_pause_stream")
        self.assertEqual(profile.gowin_gate, "python tools\\fpga_first_pass_gowin.py --check")
        self.assertEqual(profile.base_programming_gate, "python tools\\fpga_board_programming.py --check")
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
            "pass_led_observed",
            "fail_led_observed",
            "uart_status_packet_hex",
            "decoded_status_packet",
            "status_retire_count",
            "status_fault_code",
            "pass_fail_state",
        ):
            self.assertTrue(profile.field_by_name(field).required)
        self.assertFalse(profile.field_by_name("probe_capture").required)

    def test_template_and_audit_accept_first_pass_record(self) -> None:
        template = fpga_first_pass_programming.first_pass_programming_template()
        self.assertIn("story=I31-S03", template)
        self.assertIn("programming_mode=SRAM", template)
        self.assertIn("uart_status_packet_hex=", template)
        self.assertIn("probe_capture=none", template)

        audit = fpga_first_pass_programming.audit_first_pass_programming(
            fpga_first_pass_programming.parse_first_pass_programming(complete_programming_text()),
            gowin_audit=passed_gowin(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "observed")
        self.assertEqual(audit.board_result, "first_pass")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.observation_issues, ())
        self.assertEqual(audit.packet_issues, ())
        self.assertIn("I31-S05", " ".join(audit.actions))

    def test_audit_accepts_failure_capture_for_i31_s04_handoff(self) -> None:
        text = (
            complete_programming_text()
            .replace("pass_led_observed=yes", "pass_led_observed=no")
            .replace("fail_led_observed=no", "fail_led_observed=yes")
            .replace("board_result=first_pass", "board_result=failure_observed")
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
            .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i31_s03_probe.csv")
        )
        audit = fpga_first_pass_programming.audit_first_pass_programming(
            fpga_first_pass_programming.parse_first_pass_programming(text),
            gowin_audit=passed_gowin(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.board_result, "failure_observed")
        self.assertIn("I31-S04", " ".join(audit.actions))

    def test_audit_blocks_without_passed_gowin_and_rejects_bad_packet_or_observation(self) -> None:
        blocked_gowin = fpga_first_pass_gowin.FirstPassGowinAudit(
            status="blocked",
            message="blocked",
            evidence_path="i31_s02.txt",
            bundle_status="blocked",
            report_status="blocked",
            missing_fields=(),
            link_issues=(),
            timing_issues=(),
            policy_issues=(),
            bitstreams=(),
            actions=(),
        )
        audit = fpga_first_pass_programming.audit_first_pass_programming(
            fpga_first_pass_programming.parse_first_pass_programming(complete_programming_text()),
            gowin_audit=blocked_gowin,
        )
        self.assertEqual(audit.status, "blocked")

        bad_packet = complete_programming_text().replace(
            "uart_status_packet_hex=",
            "uart_status_packet_hex=bad",
        )
        audit = fpga_first_pass_programming.audit_first_pass_programming(
            fpga_first_pass_programming.parse_first_pass_programming(bad_packet),
            gowin_audit=passed_gowin(),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("uart_status_packet_hex must encode exactly 32 bytes", audit.packet_issues)

        bad_observation = complete_programming_text().replace(
            "heartbeat_observed=yes",
            "heartbeat_observed=no",
        )
        audit = fpga_first_pass_programming.audit_first_pass_programming(
            fpga_first_pass_programming.parse_first_pass_programming(bad_observation),
            gowin_audit=passed_gowin(),
        )
        self.assertEqual(audit.status, "needs_capture")
        self.assertIn("heartbeat_observed must be yes", audit.observation_issues)

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_first_pass_programming.load_first_pass_programming_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("uart_status_packet_hex", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass programming issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S03")
        self.assertEqual(parsed["required_mode"], "SRAM")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("decoded_status_packet", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("uart_status_packet_hex", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_first_pass_gowin.py", stream.getvalue())
        self.assertIn("fpga_uart_status_streamer.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i31_s03.txt"
            evidence.write_text(complete_programming_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "observed")

    def test_documentation_names_required_evidence_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-programming.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S03",
            "python tools\\fpga_first_pass_programming.py --check",
            "docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt",
            "python tools\\fpga_first_pass_gowin.py --check",
            "python tools\\fpga_board_programming.py --check",
            "python tools\\fpga_uart_status_streamer.py --check",
            "python tools\\fpga_probe_bundles.py --check",
            "programming_log",
            "reset_released",
            "heartbeat_observed",
            "pass_led_observed",
            "fail_led_observed",
            "uart_status_packet_hex",
            "decoded_status_packet",
            "probe_capture",
            "bitstream_sha256",
            "first_pass",
            "failure_observed",
            "I31-S04",
            "I31-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

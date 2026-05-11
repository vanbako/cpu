"""I32-S06 conformance tests for physical monitor board-session evidence."""

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
TOOL = ROOT / "tools" / "fpga_monitor_board_session.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_board_session


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_monitor_board_session_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMonitorBoardSessionTests(unittest.TestCase):
    def test_monitor_board_session_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_monitor_board_session.validate_fpga_monitor_board_session(ROOT),
            (),
        )

    def test_profile_names_dependencies_required_fields_and_blockers(self) -> None:
        profile = fpga_monitor_board_session.fpga_monitor_board_session_profile()

        self.assertEqual(profile.story, "I32-S06")
        self.assertEqual(profile.status, "blocked_until_physical_monitor_session")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.first_pass_archive_gate, "python tools\\fpga_first_pass_archive.py --check")
        self.assertEqual(profile.monitor_session_gate, "python tools\\fpga_monitor_session.py --check")
        self.assertEqual(profile.interactive_corpus_gate, "python tools\\fpga_interactive_corpus.py --check")
        self.assertEqual(profile.snapshot_gate, "python tools\\fpga_monitor_snapshot.py --check")
        self.assertEqual(profile.required_program_count, 2)
        self.assertIn("multi_program_session_passed", profile.accepted_results)
        self.assertIn("classified_board_session_blocker", profile.accepted_results)

        fields = {field.name: field for field in profile.required_fields}
        for name in (
            "story",
            "captured_at",
            "repository_commit",
            "board",
            "first_pass_archive",
            "first_pass_archive_status",
            "monitor_transport",
            "bitstream_sha256",
            "interactive_corpus",
            "loaded_case_ids",
            "program_run_count",
            "loader_connect_log",
            "command_transcript",
            "status_packet_hex",
            "uart_capture",
            "snapshot_evidence",
            "replay_command",
            "pass_fail_result",
            "residual_blockers",
            "evidence_archive",
            "retest_steps",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)

        blockers = " ".join(profile.blockers)
        self.assertIn("I31-S05", blockers)
        self.assertIn("at least two I32-S05 cases", blockers)
        self.assertIn("classified blockers", blockers)

    def test_template_audits_as_accepted_after_timestamp_and_commit(self) -> None:
        text = (
            fpga_monitor_board_session.board_session_template()
            .replace("captured_at=", "captured_at=2026-05-11T15:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
        )
        record = fpga_monitor_board_session.parse_board_session_record(text)
        audit = fpga_monitor_board_session.audit_board_session_record(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.loaded_case_ids, ("scalar_control.call_return", "trap_syscall.sys_pause_iret"))
        self.assertEqual(audit.pass_fail_result, "multi_program_session_passed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.packet_issues, ())
        self.assertIn("I33-S01", " ".join(audit.actions))

    def test_classified_blocker_requires_residual_blockers_and_replay(self) -> None:
        text = (
            fpga_monitor_board_session.board_session_template()
            .replace("captured_at=", "captured_at=2026-05-11T15:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("first_pass_archive_status=archived", "first_pass_archive_status=needs_followup")
            .replace(
                "pass_fail_result=multi_program_session_passed",
                "pass_fail_result=classified_board_session_blocker",
            )
            .replace(
                "replay_command=python tools\\fpga_monitor_snapshot.py --snapshot-json",
                "replay_command=python tools\\verilator_diff_harness.py --case-id traps.sys_iret_return",
            )
        )
        missing = fpga_monitor_board_session.audit_board_session_record(
            fpga_monitor_board_session.parse_board_session_record(text)
        )
        fixed = fpga_monitor_board_session.audit_board_session_record(
            fpga_monitor_board_session.parse_board_session_record(
                text.replace("residual_blockers=none", "residual_blockers=trap_syscall_uart_timeout")
            )
        )

        self.assertEqual(missing.status, "needs_followup")
        self.assertIn("residual_blockers", " ".join(missing.blocker_issues))
        self.assertTrue(fixed.accepted)
        self.assertEqual(fixed.pass_fail_result, "classified_board_session_blocker")

    def test_bad_case_hash_or_packet_is_invalid_and_missing_file_is_blocked(self) -> None:
        base = (
            fpga_monitor_board_session.board_session_template()
            .replace("captured_at=", "captured_at=2026-05-11T15:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
        )
        bad_case = fpga_monitor_board_session.audit_board_session_record(
            fpga_monitor_board_session.parse_board_session_record(
                base.replace(
                    "loaded_case_ids=scalar_control.call_return,trap_syscall.sys_pause_iret",
                    "loaded_case_ids=scalar_control.call_return,unknown.case",
                )
            )
        )
        bad_hash = fpga_monitor_board_session.audit_board_session_record(
            fpga_monitor_board_session.parse_board_session_record(
                base.replace(
                    "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "bitstream_sha256=not-a-hash",
                )
            )
        )
        bad_packet = fpga_monitor_board_session.audit_board_session_record(
            fpga_monitor_board_session.parse_board_session_record(
                base.replace("status_packet_hex=", "status_packet_hex=00")
            )
        )
        missing = fpga_monitor_board_session.load_board_session_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i32_s06.txt"),
        )

        self.assertEqual(bad_case.status, "invalid")
        self.assertIn("unknown I32-S05 case", " ".join(bad_case.case_issues))
        self.assertEqual(bad_hash.status, "invalid")
        self.assertIn("bitstream_sha256", " ".join(bad_hash.link_issues))
        self.assertEqual(bad_packet.status, "invalid")
        self.assertIn("status_packet_hex", " ".join(bad_packet.packet_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("captured_at", missing.missing_fields)

    def test_cli_validates_prints_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA monitor board-session issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S06")
        self.assertEqual(parsed["required_program_count"], 2)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("loaded_case_ids=scalar_control.call_return,trap_syscall.sys_pause_iret", stream.getvalue())
        self.assertIn("status_packet_hex=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i32_s06.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_evidence_fields_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-monitor-board-session.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I32-S06",
            "python tools\\fpga_monitor_board_session.py --check",
            "docs/implementation/evidence/i32_s06_monitor_board_session.txt",
            "python tools\\fpga_first_pass_archive.py --check",
            "python tools\\fpga_monitor_session.py --check",
            "python tools\\fpga_interactive_corpus.py --check",
            "python tools\\fpga_monitor_snapshot.py --check",
            "loaded_case_ids",
            "program_run_count",
            "status_packet_hex",
            "uart_capture",
            "snapshot_evidence",
            "replay_command",
            "multi_program_session_passed",
            "classified_board_session_blocker",
            "residual_blockers",
            "evidence_archive",
            "I33-S01",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

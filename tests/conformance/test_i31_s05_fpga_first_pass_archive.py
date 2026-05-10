"""I31-S05 conformance tests for first physical CPU pass archive evidence."""

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
TOOL = ROOT / "tools" / "fpga_first_pass_archive.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import (
    fpga_first_board_archive,
    fpga_first_pass_archive,
    fpga_first_pass_programming,
    fpga_first_pass_replay,
)


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_archive_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def first_board(status: str) -> fpga_first_board_archive.FirstBoardArchiveAudit:
    return fpga_first_board_archive.FirstBoardArchiveAudit(
        status=status,
        message=status,
        archive_path=fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE.as_posix(),
        programming_status="passed",
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=(),
    )


def programming(board_result: str) -> fpga_first_pass_programming.FirstPassProgrammingAudit:
    return fpga_first_pass_programming.FirstPassProgrammingAudit(
        status=fpga_first_pass_programming.OBSERVED,
        message="observed",
        evidence_path=fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix(),
        gowin_status="passed",
        board_result=board_result,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=(),
    )


def replay(status: str) -> fpga_first_pass_replay.FirstPassReplayAudit:
    return fpga_first_pass_replay.FirstPassReplayAudit(
        status=status,
        message=status,
        evidence_path=fpga_first_pass_replay.FPGA_FIRST_PASS_REPLAY_EVIDENCE.as_posix(),
        programming_status=fpga_first_pass_programming.OBSERVED,
        debug_evidence_status="accepted",
        failure_class="trap",
        replay_case_id="core.control_trap.sys_iret",
        missing_fields=(),
        link_issues=(),
        capture_issues=(),
        packet_issues=(),
        replay_issues=(),
        classification_issues=(),
        actions=(),
    )


def pass_archive_text() -> str:
    return (
        fpga_first_pass_archive.first_pass_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T15:30:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


def blocker_archive_text() -> str:
    return (
        pass_archive_text()
        .replace("first_board_archive_status=archived", "first_board_archive_status=needs_followup")
        .replace("programming_board_result=first_pass", "programming_board_result=failure_observed")
        .replace(
            "replay_classification=not_required_first_pass",
            "replay_classification=docs/implementation/evidence/i31_s04_failure_replay_classification.txt",
        )
        .replace("replay_status=not_required", "replay_status=classified")
        .replace("replay_case_id=none", "replay_case_id=core.control_trap.sys_iret")
        .replace("first_mismatch=none", "first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch")
        .replace("debug_evidence=none", "debug_evidence=docs/implementation/evidence/i25_s05_debug_evidence.txt")
        .replace("pass_fail_result=first_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=first_pass_archived", "archive_result=blocker_disposition_archived")
        .replace("residual_blockers=none", "residual_blockers=trap_replay_mismatch")
        .replace("filed_issues=none", "filed_issues=CPU-123")
    )


class FpgaFirstPassArchiveTests(unittest.TestCase):
    def test_first_pass_archive_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_pass_archive.validate_fpga_first_pass_archive(ROOT), ())

    def test_profile_names_dependencies_fields_and_results(self) -> None:
        profile = fpga_first_pass_archive.fpga_first_pass_archive_profile()

        self.assertEqual(profile.story, "I31-S05")
        self.assertEqual(profile.status, "blocked_until_pass_or_classified_blocker")
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.first_board_archive_gate, "python tools\\fpga_first_board_archive.py --check")
        self.assertEqual(profile.programming_gate, "python tools\\fpga_first_pass_programming.py --check")
        self.assertEqual(profile.replay_gate, "python tools\\fpga_first_pass_replay.py --check")
        self.assertIn("first_pass_archived", profile.archive_results)
        self.assertIn("blocker_disposition_archived", profile.archive_results)
        for field in (
            "identity_evidence",
            "constraints_evidence",
            "gowin_report_bundle",
            "bitstream_sha256",
            "programming_log",
            "reset_observation",
            "led_evidence",
            "uart_log",
            "decoded_status_packet",
            "probe_capture",
            "replay_classification",
            "first_mismatch",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
        ):
            self.assertTrue(profile.field_by_name(field).required)

    def test_template_and_audit_accept_first_pass_archive(self) -> None:
        template = fpga_first_pass_archive.first_pass_archive_template()
        self.assertIn("story=I31-S05", template)
        self.assertIn("archive_result=first_pass_archived", template)
        self.assertIn("replay_status=not_required", template)

        audit = fpga_first_pass_archive.audit_first_pass_archive(
            fpga_first_pass_archive.parse_first_pass_archive(pass_archive_text()),
            first_board_archive_audit=first_board(fpga_first_board_archive.ARCHIVE_ARCHIVED),
            programming_audit=programming(fpga_first_pass_programming.BOARD_RESULT_FIRST_PASS),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.archive_result, "first_pass_archived")
        self.assertEqual(audit.pass_fail_result, "first_pass")

    def test_audit_accepts_classified_blocker_disposition(self) -> None:
        audit = fpga_first_pass_archive.audit_first_pass_archive(
            fpga_first_pass_archive.parse_first_pass_archive(blocker_archive_text()),
            first_board_archive_audit=first_board(fpga_first_board_archive.ARCHIVE_NEEDS_FOLLOWUP),
            programming_audit=programming(fpga_first_pass_programming.BOARD_RESULT_FAILURE),
            replay_audit=replay(fpga_first_pass_replay.CLASSIFIED),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.archive_result, "blocker_disposition_archived")
        self.assertEqual(audit.pass_fail_result, "failure_observed")
        self.assertEqual(audit.replay_status, "classified")

    def test_audit_rejects_missing_blocker_issue_bad_hash_and_inconsistent_result(self) -> None:
        missing_issue = blocker_archive_text().replace("filed_issues=CPU-123", "filed_issues=none")
        audit = fpga_first_pass_archive.audit_first_pass_archive(
            fpga_first_pass_archive.parse_first_pass_archive(missing_issue),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("filed_issues", " ".join(audit.blocker_issues))

        bad_hash = pass_archive_text().replace(
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "bitstream_sha256=bad",
        )
        audit = fpga_first_pass_archive.audit_first_pass_archive(
            fpga_first_pass_archive.parse_first_pass_archive(bad_hash),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256", " ".join(audit.link_issues))

        inconsistent = pass_archive_text().replace("pass_fail_result=first_pass", "pass_fail_result=failure_observed")
        audit = fpga_first_pass_archive.audit_first_pass_archive(
            fpga_first_pass_archive.parse_first_pass_archive(inconsistent),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("first_pass_archived", " ".join(audit.result_issues))

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_first_pass_archive.load_first_pass_archive_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("identity_evidence", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass archive issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S05")
        self.assertIn("result_rules", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("replay_classification", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_first_pass_programming.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i31_s05.txt"
            evidence.write_text(pass_archive_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_required_archive_fields_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-archive.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S05",
            "python tools\\fpga_first_pass_archive.py --check",
            "docs/implementation/evidence/i31_s05_first_cpu_pass_archive.txt",
            "python tools\\fpga_first_board_archive.py --check",
            "python tools\\fpga_first_pass_programming.py --check",
            "python tools\\fpga_first_pass_replay.py --check",
            "identity_evidence",
            "constraints_evidence",
            "gowin_report_bundle",
            "bitstream_sha256",
            "programming_log",
            "reset_observation",
            "led_evidence",
            "uart_log",
            "decoded_status_packet",
            "probe_capture",
            "replay_classification",
            "first_mismatch",
            "first_pass_archived",
            "blocker_disposition_archived",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
            "I31-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

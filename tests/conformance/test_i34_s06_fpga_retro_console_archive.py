"""I34-S06 conformance tests for Retro Console pass/blocker archive evidence."""

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
TOOL = ROOT / "tools" / "fpga_retro_console_archive.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import (
    fpga_retro_console_archive,
    fpga_retro_console_gowin,
    fpga_retro_console_programming,
    fpga_retro_console_replay,
)


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_retro_console_archive_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def programming(board_result: str) -> fpga_retro_console_programming.RetroConsoleProgrammingAudit:
    return fpga_retro_console_programming.RetroConsoleProgrammingAudit(
        status=fpga_retro_console_programming.OBSERVED,
        message="observed",
        evidence_path=fpga_retro_console_programming.FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE.as_posix(),
        gowin_status=fpga_retro_console_gowin.GOWIN_PASS,
        board_result=board_result,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=(),
    )


def replay(status: str) -> fpga_retro_console_replay.RetroConsoleReplayAudit:
    return fpga_retro_console_replay.RetroConsoleReplayAudit(
        status=status,
        message=status,
        evidence_path=fpga_retro_console_replay.FPGA_RETRO_CONSOLE_REPLAY_EVIDENCE.as_posix(),
        programming_status=fpga_retro_console_programming.OBSERVED,
        debug_evidence_status="accepted",
        board_result=fpga_retro_console_programming.BOARD_RESULT_FAILURE,
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
        fpga_retro_console_archive.retro_console_archive_template()
        .replace("archived_at=", "archived_at=2026-05-12T00:15:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


def blocker_archive_text() -> str:
    return (
        pass_archive_text()
        .replace("programming_board_result=retro_console_smoke_pass", "programming_board_result=failure_observed")
        .replace(
            "replay_classification=not_required_retro_console_smoke_pass",
            "replay_classification=docs/implementation/evidence/i34_s05_retro_console_replay_classification.txt",
        )
        .replace("replay_status=not_required", "replay_status=classified")
        .replace("replay_case_id=none", "replay_case_id=core.control_trap.sys_iret")
        .replace("first_mismatch=none", "first_mismatch=core.control_trap.sys_iret packet 5: pc_cell mismatch")
        .replace("failure_class=none", "failure_class=trap")
        .replace("pass_fail_result=retro_console_smoke_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=retro_console_pass_archived", "archive_result=retro_console_blocker_archived")
        .replace(
            "retro_console_handoff_policy=retro_console_ready_with_138k_i31_i32_active",
            "retro_console_handoff_policy=retro_console_deferred_while_138k_i31_i32_active",
        )
        .replace("residual_blockers=none", "residual_blockers=trap_replay_mismatch")
        .replace("filed_issues=none", "filed_issues=CPU-234")
    )


class FpgaRetroConsoleArchiveTests(unittest.TestCase):
    def test_retro_console_archive_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_retro_console_archive.validate_fpga_retro_console_archive(ROOT),
            (),
        )

    def test_profile_names_dependencies_fields_results_and_handoff(self) -> None:
        profile = fpga_retro_console_archive.fpga_retro_console_archive_profile()

        self.assertEqual(profile.story, "I34-S06")
        self.assertEqual(profile.status, "blocked_until_retro_console_pass_or_blocker")
        self.assertEqual(profile.board, "Sipeed Tang Retro Console with 60K SOM")
        self.assertEqual(profile.identity_gate, "python tools\\fpga_retro_console_identity.py --check")
        self.assertEqual(profile.constraints_gate, "python tools\\fpga_retro_console_constraints.py --check")
        self.assertEqual(profile.gowin_gate, "python tools\\fpga_retro_console_gowin.py --check")
        self.assertEqual(profile.programming_gate, "python tools\\fpga_retro_console_programming.py --check")
        self.assertEqual(profile.replay_gate, "python tools\\fpga_retro_console_replay.py --check")
        self.assertEqual(profile.interactive_corpus_gate, "python tools\\fpga_interactive_corpus.py --check")
        self.assertIn("retro_console_pass_archived", profile.archive_results)
        self.assertIn("retro_console_blocker_archived", profile.archive_results)
        self.assertIn("retro_console_deferred_while_138k_i31_i32_active", profile.handoff_policies)
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
            "failure_class",
            "interactive_corpus",
            "retro_console_handoff_policy",
            "primary_138k_claim",
            "primary_138k_path_status",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
        ):
            self.assertTrue(profile.field_by_name(field).required)

    def test_template_and_audit_accept_retro_console_pass_archive(self) -> None:
        template = fpga_retro_console_archive.retro_console_archive_template()
        self.assertIn("story=I34-S06", template)
        self.assertIn("archive_result=retro_console_pass_archived", template)
        self.assertIn("primary_138k_claim=no", template)
        self.assertIn("primary_138k_path_status=i31_i32_continue_on_tang_mega_138k", template)

        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(pass_archive_text()),
            programming_audit=programming(fpga_retro_console_programming.BOARD_RESULT_SMOKE_PASS),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.archive_result, "retro_console_pass_archived")
        self.assertEqual(audit.pass_fail_result, "retro_console_smoke_pass")
        self.assertEqual(audit.handoff_policy, "retro_console_ready_with_138k_i31_i32_active")

    def test_audit_accepts_classified_retro_console_blocker_archive(self) -> None:
        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(blocker_archive_text()),
            programming_audit=programming(fpga_retro_console_programming.BOARD_RESULT_FAILURE),
            replay_audit=replay(fpga_retro_console_replay.CLASSIFIED),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.archive_result, "retro_console_blocker_archived")
        self.assertEqual(audit.pass_fail_result, "failure_observed")
        self.assertEqual(audit.replay_status, "classified")
        self.assertEqual(audit.handoff_policy, "retro_console_deferred_while_138k_i31_i32_active")

    def test_audit_rejects_missing_blocker_issue_bad_hash_wrong_138k_claim_and_inconsistent_result(self) -> None:
        missing_issue = blocker_archive_text().replace("filed_issues=CPU-234", "filed_issues=none")
        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(missing_issue),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("filed_issues", " ".join(audit.blocker_issues))

        bad_hash = pass_archive_text().replace(
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "bitstream_sha256=bad",
        )
        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(bad_hash),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256", " ".join(audit.link_issues))

        bad_claim = pass_archive_text().replace("primary_138k_claim=no", "primary_138k_claim=yes")
        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(bad_claim),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("primary_138k_claim", " ".join(audit.link_issues))

        inconsistent = pass_archive_text().replace(
            "pass_fail_result=retro_console_smoke_pass",
            "pass_fail_result=failure_observed",
        )
        audit = fpga_retro_console_archive.audit_retro_console_archive(
            fpga_retro_console_archive.parse_retro_console_archive(inconsistent),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("retro_console_pass_archived", " ".join(audit.result_issues))

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_retro_console_archive.load_retro_console_archive_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("identity_evidence", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Retro Console archive issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I34-S06")
        self.assertIn("result_rules", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("primary_138k_claim=no", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("replay_classification", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_retro_console_programming.py", stream.getvalue())
        self.assertIn("fpga_interactive_corpus.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i34_s06.txt"
            evidence.write_text(pass_archive_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_required_archive_fields_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-retro-console-archive.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I34-S06",
            "python tools\\fpga_retro_console_archive.py --check",
            "docs/implementation/evidence/i34_s06_retro_console_archive.txt",
            "python tools\\fpga_retro_console_identity.py --check",
            "python tools\\fpga_retro_console_constraints.py --check",
            "python tools\\fpga_retro_console_gowin.py --check",
            "python tools\\fpga_retro_console_programming.py --check",
            "python tools\\fpga_retro_console_replay.py --check",
            "python tools\\fpga_interactive_corpus.py --check",
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
            "failure_class",
            "retro_console_pass_archived",
            "retro_console_blocker_archived",
            "primary_138k_claim=no",
            "retro_console_deferred_while_138k_i31_i32_active",
            "i31_i32_continue_on_tang_mega_138k",
            "I31/I32",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

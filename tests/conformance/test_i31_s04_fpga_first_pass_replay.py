"""I31-S04 conformance tests for first-pass failure replay classification."""

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
TOOL = ROOT / "tools" / "fpga_first_pass_replay.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import (
    fpga_debug_evidence,
    fpga_debug_status,
    fpga_first_pass_programming,
    fpga_first_pass_replay,
    fpga_replay_mapper,
)


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_replay_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def failure_programming() -> fpga_first_pass_programming.FirstPassProgrammingAudit:
    return fpga_first_pass_programming.FirstPassProgrammingAudit(
        status=fpga_first_pass_programming.OBSERVED,
        message="observed",
        evidence_path=fpga_first_pass_programming.FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix(),
        gowin_status="passed",
        board_result=fpga_first_pass_programming.BOARD_RESULT_FAILURE,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=(),
    )


def accepted_debug_evidence() -> fpga_debug_evidence.DebugEvidenceAudit:
    return fpga_debug_evidence.DebugEvidenceAudit(
        status=fpga_debug_evidence.DEBUG_EVIDENCE_ACCEPTED,
        message="accepted",
        evidence_path=fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_PATH.as_posix(),
        archive_status="archived",
        missing_fields=(),
        capture_issues=(),
        classification_issues=(),
        replay_issues=(),
        actions=(),
    )


def complete_replay_text() -> str:
    return (
        fpga_first_pass_replay.first_pass_replay_template()
        .replace("classified_at=", "classified_at=2026-05-10T13:30:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


def packet_hex(packet: fpga_debug_status.DebugStatusPacket) -> str:
    return fpga_debug_status.encode_debug_status_packet(packet).hex()


class FpgaFirstPassReplayTests(unittest.TestCase):
    def test_first_pass_replay_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_pass_replay.validate_fpga_first_pass_replay(ROOT), ())

    def test_profile_names_dependencies_classes_fields_and_blockers(self) -> None:
        profile = fpga_first_pass_replay.fpga_first_pass_replay_profile()

        self.assertEqual(profile.story, "I31-S04")
        self.assertEqual(profile.status, "blocked_until_failure_capture")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i31_s04_failure_replay_classification.txt",
        )
        self.assertEqual(profile.programming_gate, "python tools\\fpga_first_pass_programming.py --check")
        self.assertEqual(profile.replay_mapper_gate, "python tools\\fpga_replay_mapper.py --check")
        self.assertEqual(profile.debug_evidence_gate, "python tools\\fpga_debug_evidence.py --check")
        for failure_class in (
            "clock_reset",
            "memory",
            "firmware",
            "trap",
            "translation",
            "loader",
            "board_integration",
        ):
            self.assertIn(failure_class, profile.failure_classes)
        for field in (
            "uart_status_packet_hex",
            "replay_case_id",
            "replay_command",
            "observed_trace",
            "first_mismatch",
            "failure_class",
            "debug_evidence_status",
            "followup_issue",
        ):
            self.assertTrue(profile.field_by_name(field).required)

    def test_template_and_audit_accept_trap_failure_classification(self) -> None:
        template = fpga_first_pass_replay.first_pass_replay_template()
        self.assertIn("story=I31-S04", template)
        self.assertIn("failure_class=trap", template)
        self.assertIn("replay_case_id=core.control_trap.sys_iret", template)
        self.assertIn("first_mismatch=", template)

        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(complete_replay_text()),
            programming_audit=failure_programming(),
            debug_evidence_audit=accepted_debug_evidence(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "classified")
        self.assertEqual(audit.failure_class, "trap")
        self.assertEqual(audit.replay_case_id, "core.control_trap.sys_iret")
        self.assertEqual(audit.replay_issues, ())
        self.assertIn("I31-S05", " ".join(audit.actions))

    def test_clock_reset_failure_can_classify_reset_idle_replay(self) -> None:
        packet = fpga_debug_status.DebugStatusPacket(
            flags=fpga_debug_status.debug_status_flag_mask(
                "reset_asserted",
                "reset_observed",
                "core_idle",
            ),
            slot=0,
            pass_fail_state=0,
            pc_cell=0,
            retire_count=0,
            fault_code=0,
            trap_cause=0,
            build_id=0x2501C0DE,
            sequence=9,
        )
        mapping = fpga_replay_mapper.map_debug_status_packet(packet)
        selected = mapping.candidates[0]
        text = (
            complete_replay_text()
            .replace(
                "uart_status_packet_hex="
                + packet_hex(fpga_first_pass_replay.example_failure_status_packet()),
                "uart_status_packet_hex=" + packet_hex(packet),
            )
            .replace("capture_source=uart", "capture_source=gao_ila")
            .replace("uart_log=docs/implementation/evidence/i31_s04_uart_failure.log", "uart_log=none")
            .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i31_s04_reset_probe.csv")
            .replace("replay_case_id=core.control_trap.sys_iret", f"replay_case_id={selected.case_id}")
            .replace(
                "replay_command=python tools\\verilator_diff_harness.py --case-id core.control_trap.sys_iret",
                f"replay_command={selected.replay_command}",
            )
            .replace(
                "observed_trace=build\\fpga\\captures\\status_sequence_4_retire_trace.json",
                "observed_trace=build\\fpga\\captures\\status_sequence_9_retire_trace.json",
            )
            .replace(
                "first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch",
                "first_mismatch=core.shell.reset_idle packet 9: reset stayed asserted",
            )
            .replace("failure_class=trap", "failure_class=clock_reset")
            .replace(
                "classification_rationale=syscall trap captured in first-pass status packet",
                "classification_rationale=board reset stayed asserted and core remained idle",
            )
            .replace("--case-id core.control_trap.sys_iret", f"--case-id {selected.case_id}")
        )

        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(text),
            programming_audit=failure_programming(),
            debug_evidence_audit=accepted_debug_evidence(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.failure_class, "clock_reset")
        self.assertEqual(audit.replay_case_id, "core.shell.reset_idle")

    def test_audit_rejects_missing_mismatch_pass_result_bad_packet_and_wrong_case(self) -> None:
        missing_mismatch = complete_replay_text().replace(
            "first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch",
            "first_mismatch=none",
        )
        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(missing_mismatch),
            programming_audit=failure_programming(),
        )
        self.assertEqual(audit.status, "needs_triage")
        self.assertIn("first_mismatch must preserve", " ".join(audit.replay_issues))

        pass_result = complete_replay_text().replace(
            "programming_board_result=failure_observed",
            "programming_board_result=first_pass",
        )
        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(pass_result),
            programming_audit=failure_programming(),
        )
        self.assertEqual(audit.status, "needs_capture")

        bad_packet = complete_replay_text().replace(
            "uart_status_packet_hex=",
            "uart_status_packet_hex=bad",
        )
        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(bad_packet),
            programming_audit=failure_programming(),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("uart_status_packet_hex must encode exactly 32 bytes", audit.packet_issues)

        wrong_case = complete_replay_text().replace(
            "replay_case_id=core.control_trap.sys_iret",
            "replay_case_id=core.mmu_tlb.translation_sfence",
        ).replace(
            "--case-id core.control_trap.sys_iret",
            "--case-id core.mmu_tlb.translation_sfence",
        )
        audit = fpga_first_pass_replay.audit_first_pass_replay(
            fpga_first_pass_replay.parse_first_pass_replay(wrong_case),
            programming_audit=failure_programming(),
        )
        self.assertEqual(audit.status, "needs_triage")
        self.assertIn("ranked candidates", " ".join(audit.replay_issues))

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_first_pass_replay.load_first_pass_replay_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("uart_status_packet_hex", audit.missing_fields)

    def test_cli_validates_json_template_classes_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass replay issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S04")
        self.assertIn("classification_rules", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("replay_case_id", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--classes"])

        self.assertEqual(result, 0)
        self.assertIn("board_integration", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_first_pass_programming.py", stream.getvalue())
        self.assertIn("verilator_diff_harness.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i31_s04.txt"
            evidence.write_text(complete_replay_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "classified")

    def test_documentation_names_required_replay_fields_classes_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-replay.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S04",
            "python tools\\fpga_first_pass_replay.py --check",
            "docs/implementation/evidence/i31_s04_failure_replay_classification.txt",
            "python tools\\fpga_first_pass_programming.py --check",
            "python tools\\fpga_replay_mapper.py --check",
            "python tools\\fpga_debug_evidence.py --check",
            "uart_status_packet_hex",
            "replay_case_id",
            "replay_command",
            "observed_trace",
            "first_mismatch",
            "clock_reset",
            "memory",
            "firmware",
            "trap",
            "translation",
            "loader",
            "board_integration",
            "debug_evidence_status",
            "followup_issue",
            "I31-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

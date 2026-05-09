"""I25-S05 conformance tests for FPGA debug evidence gating."""

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
TOOL = ROOT / "tools" / "fpga_debug_evidence.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_evidence, fpga_first_board_archive, fpga_first_test


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_debug_evidence_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def archive_audit(status: str = fpga_first_board_archive.ARCHIVE_ARCHIVED):
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


class FpgaDebugEvidenceTests(unittest.TestCase):
    def test_debug_evidence_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_debug_evidence.validate_fpga_debug_evidence(ROOT), ())

    def test_profile_names_dependencies_and_required_capture_classes(self) -> None:
        profile = fpga_debug_evidence.fpga_debug_evidence_profile()

        self.assertEqual(profile.story, "I25-S05")
        self.assertEqual(profile.board, fpga_first_test.TARGET_BOARD_NAME)
        self.assertEqual(profile.archive_gate, "python tools\\fpga_first_board_archive.py --check")
        self.assertEqual(profile.uart_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.probe_gate, "python tools\\fpga_probe_bundles.py --check")
        self.assertEqual(profile.replay_gate, "python tools\\fpga_replay_mapper.py --check")
        self.assertIn("firmware", profile.nontrivial_failure_classes)
        self.assertIn("memory", profile.nontrivial_failure_classes)
        self.assertIn("trap", profile.nontrivial_failure_classes)
        self.assertIn("translation", profile.nontrivial_failure_classes)
        self.assertIn("uart", profile.capture_sources)
        self.assertIn("gao_ila", profile.capture_sources)

    def test_nontrivial_led_only_failure_requires_debug_capture(self) -> None:
        record = fpga_debug_evidence.parse_debug_evidence(
            fpga_debug_evidence.debug_evidence_template()
            .replace("captured_at=", "captured_at=2026-05-09T00:00:00")
            .replace("board_result=", "board_result=fail_led_asserted")
            .replace("symptom_class=", "symptom_class=memory")
            .replace("evidence_source=", "evidence_source=led_only")
        )

        audit = fpga_debug_evidence.audit_debug_evidence(record, archive_audit=archive_audit())

        self.assertEqual(audit.status, fpga_debug_evidence.DEBUG_EVIDENCE_NEEDS_CAPTURE)
        self.assertTrue(any("UART packet hex or GAO/ILA" in issue for issue in audit.capture_issues))

    def test_complete_uart_failure_evidence_is_accepted(self) -> None:
        record = fpga_debug_evidence.parse_debug_evidence(
            "\n".join(
                (
                    "story=I25-S05",
                    f"board={fpga_first_test.TARGET_BOARD_NAME}",
                    "captured_at=2026-05-09T00:00:00",
                    "first_board_archive=docs/implementation/evidence/i24_s05_first_board_archive.txt",
                    "board_result=fail_led_asserted",
                    "symptom_class=trap",
                    "evidence_source=uart",
                    "uart_packet_hex=01c5012000100100021000000000000008000000080000dec001250700000000",
                    "uart_log=docs/implementation/evidence/i25_s05_uart.log",
                    "probe_capture=none",
                    "probe_setup=none",
                    "replay_mapping=docs/implementation/evidence/i25_s05_replay.json",
                    "replay_command=python tools\\verilator_diff_harness.py --case-id core.control_trap.sys_iret",
                    "first_mismatch=core.control_trap.sys_iret packet 7: pc_cell mismatch",
                    "clock_reset_diagnosis=not_applicable",
                    "firmware_diagnosis=not_applicable",
                    "memory_diagnosis=not_applicable",
                    "trap_diagnosis=syscall trap replay selected",
                    "translation_diagnosis=not_applicable",
                    "followup_issue=CPU-123",
                    "retest_steps=rerun first-test bitstream after trap fix",
                )
            )
        )

        audit = fpga_debug_evidence.audit_debug_evidence(record, archive_audit=archive_audit())

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, fpga_debug_evidence.DEBUG_EVIDENCE_ACCEPTED)

    def test_clock_reset_failure_does_not_require_uart_packet(self) -> None:
        record = fpga_debug_evidence.parse_debug_evidence(
            fpga_debug_evidence.debug_evidence_template()
            .replace("captured_at=", "captured_at=2026-05-09T00:00:00")
            .replace("board_result=", "board_result=no_heartbeat")
            .replace("symptom_class=", "symptom_class=clock_reset")
            .replace("evidence_source=", "evidence_source=gao_ila")
            .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i25_s05_reset.vcd")
            .replace("probe_setup=none", "probe_setup=docs/implementation/evidence/i25_s05_probe.csv")
            .replace("clock_reset_diagnosis=not_applicable", "clock_reset_diagnosis=reset released but core_rst_n stayed low")
        )

        audit = fpga_debug_evidence.audit_debug_evidence(record, archive_audit=archive_audit())

        self.assertTrue(audit.passed)

    def test_cli_validates_json_template_and_default_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA debug evidence issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I25-S05")
        self.assertIn("triage_rules", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("story=I25-S05", stream.getvalue())
        self.assertIn("first_mismatch=none", stream.getvalue())

    def test_documentation_names_gates_triage_classes_and_statuses(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-debug-evidence-gate.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I25-S05", text)
        self.assertIn("python tools\\fpga_debug_evidence.py --check", text)
        self.assertIn("docs/implementation/evidence/i25_s05_debug_evidence.txt", text)
        self.assertIn("python tools\\fpga_first_board_archive.py --check", text)
        self.assertIn("python tools\\fpga_uart_status_streamer.py --check", text)
        self.assertIn("python tools\\fpga_probe_bundles.py --check", text)
        self.assertIn("python tools\\fpga_replay_mapper.py --check", text)
        self.assertIn("UART or GAO/ILA", text)
        self.assertIn("clock_reset", text)
        self.assertIn("firmware", text)
        self.assertIn("memory", text)
        self.assertIn("trap", text)
        self.assertIn("translation", text)
        self.assertIn("first_mismatch", text)
        self.assertIn("replay_command", text)
        self.assertIn("needs_capture", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

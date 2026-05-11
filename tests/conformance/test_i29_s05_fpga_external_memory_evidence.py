"""I29-S05 conformance tests for FPGA external-memory board evidence."""

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
TOOL = ROOT / "tools" / "fpga_external_memory_evidence.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory_evidence, fpga_external_memory_policy, fpga_external_memory_tests


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_external_memory_evidence_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaExternalMemoryEvidenceTests(unittest.TestCase):
    def test_external_memory_evidence_self_validation_passes(self) -> None:
        self.assertEqual(fpga_external_memory_evidence.validate_fpga_external_memory_evidence(ROOT), ())

    def test_profile_names_gates_fields_and_blockers(self) -> None:
        profile = fpga_external_memory_evidence.fpga_external_memory_evidence_profile()

        self.assertEqual(profile.story, "I29-S05")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i29_s05_external_memory_board_evidence.txt",
        )
        self.assertEqual(profile.required_result, "external_memory_pass")
        self.assertEqual(profile.ddr_wrapper_gate, "python tools\\fpga_ddr_wrapper.py --check")
        self.assertEqual(profile.memory_test_gate, "python tools\\fpga_external_memory_tests.py --check")
        self.assertEqual(profile.policy_gate, "python tools\\fpga_external_memory_policy.py --check")
        self.assertEqual(profile.reproducible_build_gate, "python tools\\fpga_reproducible_build.py --check")

        for field in (
            "ddr_calibration_evidence",
            "memory_test_result",
            "timing_report_bundle",
            "debug_status_capture",
            "uart_status_capture",
            "probe_capture",
            "bitstream_sha256",
            "policy_status",
            "residual_blockers",
        ):
            self.assertTrue(profile.field_by_name(field).required)
        self.assertTrue(any("DDR controller IP" in blocker for blocker in profile.blockers))

    def test_template_and_audit_accept_complete_evidence(self) -> None:
        template = fpga_external_memory_evidence.external_memory_evidence_template()
        self.assertIn("story=I29-S05", template)
        self.assertIn(
            f"memory_test_program={fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID}",
            template,
        )
        self.assertIn(
            f"policy_status={fpga_external_memory_policy.FPGA_EXTERNAL_MEMORY_POLICY_STATUS}",
            template,
        )

        record = fpga_external_memory_evidence.parse_external_memory_evidence(
            template.replace("captured_at=", "captured_at=2026-05-09T00:00:00")
            .replace(
                "bitstream_sha256=",
                "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            )
        )
        audit = fpga_external_memory_evidence.audit_external_memory_evidence(record)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, fpga_external_memory_evidence.EVIDENCE_ARCHIVED)

    def test_audit_blocks_default_missing_evidence_and_flags_residual_blockers(self) -> None:
        default_audit = fpga_external_memory_evidence.load_external_memory_evidence_audit(ROOT)
        self.assertEqual(default_audit.status, fpga_external_memory_evidence.EVIDENCE_BLOCKED)
        self.assertIn("ddr_calibration_evidence", default_audit.missing_fields)

        record = fpga_external_memory_evidence.parse_external_memory_evidence(
            fpga_external_memory_evidence.external_memory_evidence_template()
            .replace("captured_at=", "captured_at=2026-05-09T00:00:00")
            .replace(
                "bitstream_sha256=",
                "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            )
            .replace("residual_blockers=none", "residual_blockers=timing_margin_not_closed")
        )
        audit = fpga_external_memory_evidence.audit_external_memory_evidence(record)

        self.assertEqual(audit.status, fpga_external_memory_evidence.EVIDENCE_NEEDS_FOLLOWUP)
        self.assertTrue(any("filed_issues" in issue for issue in audit.blocker_issues))
        self.assertTrue(any("retest_steps" in issue for issue in audit.blocker_issues))

    def test_cli_validates_json_template_fields_blockers_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA external-memory evidence issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I29-S05")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("memory_test_result=external_memory_pass", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("ddr_calibration_evidence", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--blockers"])

        self.assertEqual(result, 0)
        self.assertIn("timing reports", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i29_s05.txt"
            evidence.write_text(
                fpga_external_memory_evidence.external_memory_evidence_template()
                .replace("captured_at=", "captured_at=2026-05-09T00:00:00")
                .replace(
                    "bitstream_sha256=",
                    "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                ),
                encoding="utf-8",
            )
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_evidence_fields_and_blocked_status(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-external-memory-evidence.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I29-S05",
            "python tools\\fpga_external_memory_evidence.py --check",
            "docs/implementation/evidence/i29_s05_external_memory_board_evidence.txt",
            "python tools\\fpga_ddr_wrapper.py --check",
            "python tools\\fpga_external_memory_tests.py --check",
            "python tools\\fpga_external_memory_policy.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "DDR calibration",
            "memory-test pass/fail",
            "timing reports",
            "debug/status",
            "UART/status",
            "probe",
            "bitstream_sha256",
            "external_memory_pass",
            "residual_blockers",
            "filed_issues",
            "blocked",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

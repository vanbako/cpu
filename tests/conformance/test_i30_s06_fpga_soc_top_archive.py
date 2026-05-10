"""I30-S06 conformance tests for the FPGA SoC top closure archive."""

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
TOOL = ROOT / "tools" / "fpga_soc_top_archive.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_archive


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_soc_top_archive_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def complete_archive_text() -> str:
    return (
        fpga_soc_top_archive.soc_top_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T12:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


class FpgaSocTopArchiveTests(unittest.TestCase):
    def test_soc_top_archive_self_validation_passes(self) -> None:
        self.assertEqual(fpga_soc_top_archive.validate_fpga_soc_top_archive(ROOT), ())

    def test_profile_names_gates_fields_sources_and_retest_commands(self) -> None:
        profile = fpga_soc_top_archive.fpga_soc_top_archive_profile()

        self.assertEqual(profile.story, "I30-S06")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i30_s06_soc_top_closure_archive.txt",
        )
        self.assertEqual(profile.required_result, "soc_top_closure_pass")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.top_smoke_gate, "python tools\\fpga_soc_top_smoke.py --check")
        self.assertEqual(profile.replay_mapper_gate, "python tools\\fpga_replay_mapper.py --check")
        self.assertEqual(profile.debug_evidence_gate, "python tools\\fpga_debug_evidence.py --check")
        self.assertIn("rtl/cpu_v01_fpga_top.sv", profile.rtl_sources)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_smoke_tb.sv", profile.rtl_sources)
        self.assertIn("obj_dir\\soc_top_smoke\\Vcpu_v01_fpga_top_soc_smoke_tb.exe", profile.run_command)

        for field in (
            "rtl_sources",
            "verilator_build_log",
            "smoke_run_log",
            "decoded_uart_trace",
            "decoded_status_trace",
            "replay_mapping",
            "debug_evidence",
            "remaining_blockers",
            "retest_commands",
        ):
            self.assertTrue(profile.field_by_name(field).required)

        self.assertFalse(profile.field_by_name("probe_trace").required)
        self.assertIn(profile.top_smoke_gate, profile.retest_commands)
        self.assertIn(profile.replay_mapper_gate, profile.retest_commands)
        self.assertIn(profile.debug_evidence_gate, profile.retest_commands)
        self.assertIn(profile.run_command, profile.retest_commands)

    def test_template_and_audit_accept_complete_archive(self) -> None:
        template = fpga_soc_top_archive.soc_top_archive_template()
        self.assertIn("story=I30-S06", template)
        self.assertIn("closure_result=soc_top_closure_pass", template)
        self.assertIn("rtl/cpu_v01_fpga_top_soc_smoke_tb.sv", template)
        self.assertIn("python tools\\fpga_replay_mapper.py --check", template)

        record = fpga_soc_top_archive.parse_soc_top_archive(complete_archive_text())
        audit = fpga_soc_top_archive.audit_soc_top_archive(record)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.blocker_issues, ())
        self.assertIn("I31-S01", " ".join(audit.actions))

    def test_audit_blocks_default_and_flags_missing_replay_and_residual_blockers(self) -> None:
        default_audit = fpga_soc_top_archive.load_soc_top_archive_audit(ROOT)
        self.assertEqual(default_audit.status, "blocked")
        self.assertIn("decoded_uart_trace", default_audit.missing_fields)

        missing_replay = complete_archive_text().replace(
            "replay_mapping=docs/implementation/evidence/i30_s06_replay_mapping.txt",
            "replay_mapping=none",
        )
        audit = fpga_soc_top_archive.audit_soc_top_archive(
            fpga_soc_top_archive.parse_soc_top_archive(missing_replay)
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("replay_mapping must link concrete evidence", audit.link_issues)

        residual = complete_archive_text().replace(
            "remaining_blockers=none",
            "remaining_blockers=timer_irq_core_delivery",
        )
        audit = fpga_soc_top_archive.audit_soc_top_archive(
            fpga_soc_top_archive.parse_soc_top_archive(residual)
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("remaining blockers must have filed_issues", audit.blocker_issues)

    def test_audit_rejects_changed_commands_and_missing_sources(self) -> None:
        bad_text = (
            complete_archive_text()
            .replace("rtl/cpu_v01_core.sv,", "")
            .replace("verilator --binary --timing", "verilator --lint-only")
            .replace("obj_dir\\soc_top_smoke\\Vcpu_v01_fpga_top_soc_smoke_tb.exe", "obj_dir\\bad.exe")
        )
        audit = fpga_soc_top_archive.audit_soc_top_archive(
            fpga_soc_top_archive.parse_soc_top_archive(bad_text)
        )

        self.assertEqual(audit.status, "invalid")
        self.assertIn("rtl_sources must include rtl/cpu_v01_core.sv", audit.link_issues)
        self.assertIn("verilator_command must match the I30-S05 smoke build command", audit.link_issues)
        self.assertIn("smoke_run_command must match the I30-S05 smoke executable", audit.link_issues)

    def test_cli_validates_json_template_fields_blockers_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA SoC top archive issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I30-S06")
        self.assertEqual(parsed["required_result"], "soc_top_closure_pass")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("decoded_status_trace", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("replay_mapping", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--blockers"])

        self.assertEqual(result, 0)
        self.assertIn("decoded UART/status", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_soc_top_smoke.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i30_s06.txt"
            evidence.write_text(complete_archive_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_archive_fields_and_handoff(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-soc-top-archive.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I30-S06",
            "python tools\\fpga_soc_top_archive.py --check",
            "docs/implementation/evidence/i30_s06_soc_top_closure_archive.txt",
            "python tools\\fpga_soc_top_smoke.py --check",
            "python tools\\fpga_replay_mapper.py --check",
            "python tools\\fpga_debug_evidence.py --check",
            "rtl/cpu_v01_fpga_top.sv",
            "rtl/cpu_v01_fpga_top_soc_smoke_tb.sv",
            "Verilator logs",
            "decoded UART/status",
            "probe_trace",
            "replay_mapping",
            "debug_evidence",
            "soc_top_closure_pass",
            "remaining_blockers",
            "filed_issues",
            "retest_commands",
            "blocked",
            "I31-S01",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

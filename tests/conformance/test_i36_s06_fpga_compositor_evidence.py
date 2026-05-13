"""I36-S06 conformance tests for compositor evidence archives."""

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
TOOL = ROOT / "tools" / "fpga_compositor_evidence.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_evidence


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_evidence_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def complete_template() -> str:
    return (
        fpga_compositor_evidence.compositor_evidence_template()
        .replace("archived_at=", "archived_at=2026-05-13T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("utilization_lut=", "utilization_lut=1234")
        .replace("utilization_register=", "utilization_register=5678")
        .replace("utilization_bram=", "utilization_bram=12")
        .replace("timing_slack_ns=", "timing_slack_ns=1.25")
    )


class FpgaCompositorEvidenceTests(unittest.TestCase):
    def test_compositor_evidence_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_evidence.validate_fpga_compositor_evidence(ROOT), ())

    def test_profile_names_gates_metrics_fields_and_blockers(self) -> None:
        profile = fpga_compositor_evidence.fpga_compositor_evidence_profile()

        self.assertEqual(profile.story, "I36-S06")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt",
        )
        self.assertEqual(profile.required_result, "compositor_evidence_archived")
        self.assertEqual(profile.compositor_demo_gate, "python tools\\fpga_compositor_demo.py --check")
        self.assertEqual(profile.gowin_report_gate, "python tools\\fpga_gowin_reports.py --check")
        self.assertEqual(
            profile.external_memory_evidence_gate,
            "python tools\\fpga_external_memory_evidence.py --check",
        )
        self.assertEqual(profile.video_timing_gate, "python tools\\fpga_video_timing.py --check")
        self.assertEqual(profile.pixel_clock_hz, 74_250_000)
        self.assertEqual(profile.bandwidth_assumption.scenario, "two_plane_xrgb8888")
        self.assertEqual(profile.bandwidth_assumption.required_bytes_per_second, 594_000_000)
        self.assertEqual(profile.bandwidth_assumption.required_cells_per_second, 99_000_000)
        self.assertGreaterEqual(profile.line_buffer.allocated_cells, profile.line_buffer.required_cells)
        self.assertEqual(profile.line_buffer.underflow_counter, "VIDEO_UNDERFLOW_COUNT")

        for field in (
            "pixel_clock_hz",
            "required_bandwidth_bytes_per_second",
            "available_bandwidth_bytes_per_second",
            "line_buffer_allocated_cells",
            "utilization_lut",
            "utilization_register",
            "utilization_bram",
            "timing_slack_ns",
            "underflow_counter_one_plane",
            "underflow_counter_overlay",
            "underflow_counter_error",
            "reduced_mode_fallback",
        ):
            self.assertTrue(profile.field_by_name(field).required)
        self.assertTrue(any("underflow counters" in blocker for blocker in profile.blockers))

    def test_template_and_audit_accept_complete_evidence(self) -> None:
        template = fpga_compositor_evidence.compositor_evidence_template()

        self.assertIn("story=I36-S06", template)
        self.assertIn("pixel_clock_hz=74250000", template)
        self.assertIn("required_bandwidth_bytes_per_second=594000000", template)
        self.assertIn("underflow_counter_error=1", template)

        record = fpga_compositor_evidence.parse_compositor_evidence(complete_template())
        audit = fpga_compositor_evidence.audit_compositor_evidence(record)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, fpga_compositor_evidence.ARCHIVE_ARCHIVED)

    def test_audit_blocks_missing_evidence_and_flags_bad_metrics(self) -> None:
        default_audit = fpga_compositor_evidence.load_compositor_evidence_audit(ROOT)
        self.assertEqual(default_audit.status, fpga_compositor_evidence.ARCHIVE_BLOCKED)
        self.assertIn("pixel_clock_hz", default_audit.missing_fields)

        bad_bandwidth = fpga_compositor_evidence.parse_compositor_evidence(
            complete_template().replace(
                "available_bandwidth_bytes_per_second=594000000",
                "available_bandwidth_bytes_per_second=148500000",
            )
        )
        audit = fpga_compositor_evidence.audit_compositor_evidence(bad_bandwidth)
        self.assertEqual(audit.status, fpga_compositor_evidence.ARCHIVE_NEEDS_FOLLOWUP)
        self.assertTrue(any("reduced-mode fallback" in issue for issue in audit.metric_issues))

        bad_underflow = fpga_compositor_evidence.parse_compositor_evidence(
            complete_template().replace("underflow_counter_overlay=0", "underflow_counter_overlay=1")
        )
        audit = fpga_compositor_evidence.audit_compositor_evidence(bad_underflow)
        self.assertEqual(audit.status, fpga_compositor_evidence.ARCHIVE_NEEDS_FOLLOWUP)
        self.assertTrue(any("underflow_counter_overlay" in issue for issue in audit.metric_issues))

    def test_cli_validates_json_template_fields_blockers_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor evidence issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S06")
        self.assertEqual(parsed["bandwidth_assumption"]["required_bytes_per_second"], 594_000_000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("archive_result=compositor_evidence_archived", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("timing_slack_ns", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--blockers"])

        self.assertEqual(result, 0)
        self.assertIn("Gowin timing", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--audit-default"])

        self.assertEqual(result, 0)
        default_audit = json.loads(stream.getvalue())
        self.assertEqual(default_audit["status"], "blocked")

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i36_s06.txt"
            evidence.write_text(complete_template(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_archive_contract_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-compositor-evidence-archive.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I36-S06",
            "python tools\\fpga_compositor_evidence.py --check",
            "docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt",
            "python tools\\fpga_compositor_demo.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "python tools\\fpga_external_memory_evidence.py --check",
            "74.25 MHz",
            "594,000,000 bytes/s",
            "99,000,000 48-bit cells/s",
            "line-buffer depth",
            "utilization_lut",
            "timing_slack_ns",
            "VIDEO_UNDERFLOW_COUNT",
            "DDR calibration",
            "reduced_mode_fallback",
            "blocked",
            "I36-S07",
            "Acceptance Review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

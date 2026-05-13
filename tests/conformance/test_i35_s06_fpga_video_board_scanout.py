"""I35-S06 conformance tests for first board video scanout evidence."""

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
TOOL = ROOT / "tools" / "fpga_video_board_scanout.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_archive, fpga_video_board_scanout


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_video_board_scanout_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def first_pass(status: str) -> fpga_first_pass_archive.FirstPassArchiveAudit:
    return fpga_first_pass_archive.FirstPassArchiveAudit(
        status=status,
        message=status,
        evidence_path=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix(),
        first_board_archive_status="archived",
        programming_status="observed",
        replay_status="not_required",
        archive_result=fpga_first_pass_archive.ARCHIVE_RESULT_PASS,
        pass_fail_result="first_pass",
        missing_fields=(),
        link_issues=(),
        result_issues=(),
        blocker_issues=(),
        actions=(),
    )


def pass_archive_text() -> str:
    return (
        fpga_video_board_scanout.video_board_scanout_template()
        .replace("archived_at=", "archived_at=2026-05-13T09:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


def blocker_archive_text() -> str:
    return (
        pass_archive_text()
        .replace(
            "visible_test_pattern_capture=docs/implementation/evidence/i35_s06_test_pattern.jpg",
            "visible_test_pattern_capture=none",
        )
        .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i35_s06_pixel_clock_probe.vcd")
        .replace("pass_fail_result=scanout_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=board_scanout_pass_archived", "archive_result=board_scanout_blocker_archived")
        .replace("blocker_class=none", "blocker_class=pixel_clock")
        .replace("blocker_evidence=none", "blocker_evidence=docs/implementation/evidence/i35_s06_pixel_clock_blocker.txt")
        .replace("residual_blockers=none", "residual_blockers=video_pixel_clk_unstable")
        .replace("filed_issues=none", "filed_issues=CPU-350")
    )


class FpgaVideoBoardScanoutTests(unittest.TestCase):
    def test_video_board_scanout_self_validation_passes(self) -> None:
        self.assertEqual(fpga_video_board_scanout.validate_fpga_video_board_scanout(ROOT), ())

    def test_profile_names_dependencies_fields_results_and_blocker_classes(self) -> None:
        profile = fpga_video_board_scanout.fpga_video_board_scanout_profile()

        self.assertEqual(profile.story, "I35-S06")
        self.assertEqual(profile.status, "blocked_until_board_scanout_pass_or_classified_blocker")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.scanout_gate, "python tools\\fpga_video_scanout_gate.py --check")
        self.assertEqual(profile.first_pass_archive_gate, "python tools\\fpga_first_pass_archive.py --check")
        self.assertIn("board_scanout_pass_archived", profile.archive_results)
        self.assertIn("board_scanout_blocker_archived", profile.archive_results)
        for blocker_class in (
            "display_adapter",
            "pixel_clock",
            "timing",
            "scanout_mmio",
            "vblank_irq",
            "bitstream",
            "board_integration",
        ):
            self.assertIn(blocker_class, profile.blocker_classes)
        for field in (
            "bitstream_sha256",
            "display_adapter_wiring",
            "pixel_clock_evidence",
            "timing_evidence",
            "visible_test_pattern_capture",
            "probe_capture",
            "video_mmio_register_log",
            "vblank_status_observation",
            "decoded_status_packet",
            "blocker_class",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
        ):
            self.assertTrue(profile.field_by_name(field).required)

    def test_template_and_audit_accept_scanout_pass_archive(self) -> None:
        template = fpga_video_board_scanout.video_board_scanout_template()

        self.assertIn("story=I35-S06", template)
        self.assertIn("archive_result=board_scanout_pass_archived", template)
        self.assertIn("visible_test_pattern_capture", template)

        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(pass_archive_text()),
            first_pass_archive_audit=first_pass("archived"),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.archive_result, "board_scanout_pass_archived")
        self.assertEqual(audit.pass_fail_result, "scanout_pass")
        self.assertEqual(audit.blocker_class, "none")

    def test_audit_accepts_classified_scanout_blocker(self) -> None:
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(blocker_archive_text()),
            first_pass_archive_audit=first_pass("archived"),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.archive_result, "board_scanout_blocker_archived")
        self.assertEqual(audit.pass_fail_result, "failure_observed")
        self.assertEqual(audit.blocker_class, "pixel_clock")

    def test_audit_blocks_on_first_pass_and_rejects_bad_hash_or_missing_capture(self) -> None:
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(pass_archive_text()),
            first_pass_archive_audit=first_pass("blocked"),
        )
        self.assertEqual(audit.status, "blocked")

        bad_hash = pass_archive_text().replace(
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "bitstream_sha256=bad",
        )
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(bad_hash),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256", " ".join(audit.link_issues))

        no_capture = pass_archive_text().replace(
            "visible_test_pattern_capture=docs/implementation/evidence/i35_s06_test_pattern.jpg",
            "visible_test_pattern_capture=none",
        )
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(no_capture),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("visible_test_pattern_capture or probe_capture", " ".join(audit.result_issues))

    def test_audit_requires_blocker_issue_and_concrete_retest_steps(self) -> None:
        missing_issue = blocker_archive_text().replace("filed_issues=CPU-350", "filed_issues=none")
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(missing_issue),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("filed_issues", " ".join(audit.blocker_issues))

        no_retest = blocker_archive_text().replace(
            "retest_steps=python tools\\fpga_video_scanout_gate.py --check ; python tools\\fpga_first_pass_archive.py --check ; python tools\\fpga_video_board_scanout.py --audit docs\\implementation\\evidence\\i35_s06_video_board_scanout.txt",
            "retest_steps=none",
        )
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            fpga_video_board_scanout.parse_video_board_scanout(no_retest),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("retest_steps", " ".join(audit.blocker_issues))

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_video_board_scanout.load_video_board_scanout_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("bitstream_sha256", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA video board scanout issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I35-S06")
        self.assertIn("board_scanout_blocker_archived", parsed["archive_results"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("pixel_clock_evidence", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_video_scanout_gate.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i35_s06.txt"
            evidence.write_text(pass_archive_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_required_evidence_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-video-board-scanout.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I35-S06",
            "python tools\\fpga_video_board_scanout.py --check",
            "docs/implementation/evidence/i35_s06_video_board_scanout.txt",
            "python tools\\fpga_video_scanout_gate.py --check",
            "python tools\\fpga_first_pass_archive.py --check",
            "bitstream_sha256",
            "display_adapter_wiring",
            "pixel_clock_evidence",
            "timing_evidence",
            "visible_test_pattern_capture",
            "probe_capture",
            "video_mmio_register_log",
            "vblank_status_observation",
            "decoded_status_packet",
            "board_scanout_pass_archived",
            "board_scanout_blocker_archived",
            "blocker_class",
            "display_adapter",
            "pixel_clock",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
            "I36-S07",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

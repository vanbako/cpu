"""I36-S07 conformance tests for first board compositor demo evidence."""

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
TOOL = ROOT / "tools" / "fpga_compositor_board.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_board, fpga_compositor_evidence, fpga_video_board_scanout


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_board_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compositor_evidence(status: str) -> fpga_compositor_evidence.CompositorEvidenceAudit:
    return fpga_compositor_evidence.CompositorEvidenceAudit(
        status=status,
        message=status,
        evidence_path=fpga_compositor_evidence.FPGA_COMPOSITOR_EVIDENCE_PATH.as_posix(),
        missing_fields=(),
        link_issues=(),
        metric_issues=(),
        blocker_issues=(),
        actions=(),
    )


def video_scanout(status: str) -> fpga_video_board_scanout.VideoBoardScanoutAudit:
    return fpga_video_board_scanout.VideoBoardScanoutAudit(
        status=status,
        message=status,
        evidence_path=fpga_video_board_scanout.FPGA_VIDEO_BOARD_SCANOUT_EVIDENCE.as_posix(),
        scanout_gate_status="passed",
        first_pass_archive_status="archived",
        archive_result=fpga_video_board_scanout.ARCHIVE_RESULT_PASS,
        pass_fail_result=fpga_video_board_scanout.BOARD_RESULT_PASS,
        blocker_class="none",
        missing_fields=(),
        link_issues=(),
        result_issues=(),
        blocker_issues=(),
        actions=(),
    )


def pass_archive_text() -> str:
    return (
        fpga_compositor_board.compositor_board_template()
        .replace("archived_at=", "archived_at=2026-05-13T10:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


def blocker_archive_text() -> str:
    return (
        pass_archive_text()
        .replace(
            "visible_capture=docs/implementation/evidence/i36_s07_compositor_capture.jpg",
            "visible_capture=none",
        )
        .replace("probe_capture=none", "probe_capture=docs/implementation/evidence/i36_s07_probe_capture.vcd")
        .replace("pass_fail_result=compositor_board_pass", "pass_fail_result=failure_observed")
        .replace("archive_result=compositor_board_pass_archived", "archive_result=compositor_board_blocker_archived")
        .replace("blocker_class=none", "blocker_class=memory_bandwidth")
        .replace("blocker_evidence=none", "blocker_evidence=docs/implementation/evidence/i36_s07_bandwidth_blocker.txt")
        .replace("residual_blockers=none", "residual_blockers=compositor_ddr_bandwidth_shortfall")
        .replace("filed_issues=none", "filed_issues=CPU-360")
    )


class FpgaCompositorBoardTests(unittest.TestCase):
    def test_compositor_board_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_board.validate_fpga_compositor_board(ROOT), ())

    def test_profile_names_dependencies_fields_results_and_blocker_classes(self) -> None:
        profile = fpga_compositor_board.fpga_compositor_board_profile()

        self.assertEqual(profile.story, "I36-S07")
        self.assertEqual(profile.status, "blocked_until_board_demo_pass_or_classified_blocker")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.compositor_evidence_gate, "python tools\\fpga_compositor_evidence.py --check")
        self.assertEqual(profile.video_board_scanout_gate, "python tools\\fpga_video_board_scanout.py --check")
        self.assertEqual(profile.compositor_demo_gate, "python tools\\fpga_compositor_demo.py --check")
        self.assertIn("compositor_board_pass_archived", profile.archive_results)
        self.assertIn("compositor_board_blocker_archived", profile.archive_results)
        for blocker_class in (
            "scanout_precondition",
            "framebuffer_image",
            "firmware_command",
            "vblank_descriptor",
            "underflow_status",
            "visible_output",
            "probe_capture",
            "memory_bandwidth",
            "board_integration",
        ):
            self.assertIn(blocker_class, profile.blocker_classes)
        for field in (
            "bitstream_sha256",
            "framebuffer_image_manifest",
            "framebuffer_image_hashes",
            "firmware_command_log",
            "visible_capture",
            "probe_capture",
            "vblank_log",
            "underflow_log",
            "status_log",
            "replay_or_simulation_commands",
            "blocker_class",
            "residual_blockers",
            "filed_issues",
            "retest_criteria",
        ):
            self.assertTrue(profile.field_by_name(field).required)

    def test_template_and_audit_accept_board_compositor_pass_archive(self) -> None:
        template = fpga_compositor_board.compositor_board_template()

        self.assertIn("story=I36-S07", template)
        self.assertIn("archive_result=compositor_board_pass_archived", template)
        self.assertIn("framebuffer_image_hashes", template)
        self.assertIn("fpga_compositor_demo.py --run", template)

        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(pass_archive_text()),
            compositor_evidence_audit=compositor_evidence("archived"),
            video_board_scanout_audit=video_scanout("archived"),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.archive_result, "compositor_board_pass_archived")
        self.assertEqual(audit.pass_fail_result, "compositor_board_pass")
        self.assertEqual(audit.blocker_class, "none")

    def test_audit_accepts_classified_compositor_blocker(self) -> None:
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(blocker_archive_text()),
            compositor_evidence_audit=compositor_evidence("archived"),
            video_board_scanout_audit=video_scanout("archived"),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.archive_result, "compositor_board_blocker_archived")
        self.assertEqual(audit.pass_fail_result, "failure_observed")
        self.assertEqual(audit.blocker_class, "memory_bandwidth")

    def test_audit_blocks_on_prerequisites_and_rejects_bad_hash_or_missing_capture(self) -> None:
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(pass_archive_text()),
            compositor_evidence_audit=compositor_evidence("blocked"),
            video_board_scanout_audit=video_scanout("archived"),
        )
        self.assertEqual(audit.status, "blocked")

        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(pass_archive_text()),
            compositor_evidence_audit=compositor_evidence("archived"),
            video_board_scanout_audit=video_scanout("blocked"),
        )
        self.assertEqual(audit.status, "blocked")

        bad_hash = pass_archive_text().replace(
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "bitstream_sha256=bad",
        )
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(bad_hash),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("bitstream_sha256", " ".join(audit.link_issues))

        no_capture = pass_archive_text().replace(
            "visible_capture=docs/implementation/evidence/i36_s07_compositor_capture.jpg",
            "visible_capture=none",
        )
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(no_capture),
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("visible_capture or probe_capture", " ".join(audit.result_issues))

    def test_audit_requires_blocker_issue_and_concrete_retest_criteria(self) -> None:
        missing_issue = blocker_archive_text().replace("filed_issues=CPU-360", "filed_issues=none")
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(missing_issue),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("filed_issues", " ".join(audit.blocker_issues))

        no_retest = blocker_archive_text().replace(
            "retest_criteria=python tools\\fpga_compositor_evidence.py --check ; python tools\\fpga_video_board_scanout.py --check ; python tools\\fpga_compositor_demo.py --check ; python tools\\fpga_compositor_board.py --audit docs\\implementation\\evidence\\i36_s07_compositor_board_demo.txt",
            "retest_criteria=none",
        )
        audit = fpga_compositor_board.audit_compositor_board(
            fpga_compositor_board.parse_compositor_board(no_retest),
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("retest_criteria", " ".join(audit.blocker_issues))

    def test_default_load_blocks_without_evidence(self) -> None:
        audit = fpga_compositor_board.load_compositor_board_audit(ROOT)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("framebuffer_image_manifest", audit.missing_fields)

    def test_cli_validates_json_template_fields_retest_blockers_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor board issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S07")
        self.assertIn("compositor_board_blocker_archived", parsed["archive_results"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("framebuffer_image_hashes", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fields"])

        self.assertEqual(result, 0)
        self.assertIn("underflow_log", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_compositor_board.py", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--blockers"])

        self.assertEqual(result, 0)
        self.assertIn("framebuffer images", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--audit-default"])

        self.assertEqual(result, 0)
        default_audit = json.loads(stream.getvalue())
        self.assertEqual(default_audit["status"], "blocked")

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i36_s07.txt"
            evidence.write_text(pass_archive_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "archived")

    def test_documentation_names_required_evidence_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-compositor-board-demo.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I36-S07",
            "python tools\\fpga_compositor_board.py --check",
            "docs/implementation/evidence/i36_s07_compositor_board_demo.txt",
            "python tools\\fpga_compositor_evidence.py --check",
            "python tools\\fpga_video_board_scanout.py --check",
            "python tools\\fpga_compositor_demo.py --check",
            "bitstream_sha256",
            "framebuffer_image_manifest",
            "framebuffer_image_hashes",
            "firmware_command_log",
            "visible_capture",
            "probe_capture",
            "vblank_log",
            "underflow_log",
            "status_log",
            "replay_or_simulation_commands",
            "compositor_board_pass_archived",
            "compositor_board_blocker_archived",
            "blocker_class",
            "memory_bandwidth",
            "residual_blockers",
            "filed_issues",
            "retest_criteria",
            "I36-S08",
            "Acceptance Review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

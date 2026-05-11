"""I33-S01 conformance tests for the release-candidate checklist."""

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
TOOL = ROOT / "tools" / "release_candidate_checklist.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_candidate_checklist


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_candidate_checklist_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseCandidateChecklistTests(unittest.TestCase):
    def test_release_candidate_checklist_self_validation_passes(self) -> None:
        self.assertEqual(
            release_candidate_checklist.validate_release_candidate_checklist(ROOT),
            (),
        )

    def test_profile_names_required_categories_gates_and_handoffs(self) -> None:
        profile = release_candidate_checklist.release_candidate_checklist_profile()

        self.assertEqual(profile.story, "I33-S01")
        self.assertEqual(profile.status, "blocked_until_release_candidate_evidence")
        self.assertEqual(profile.target_board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertIn("local_checks", profile.required_categories)
        self.assertIn("verilator", profile.required_categories)
        self.assertIn("fpga_evidence", profile.required_categories)
        self.assertIn("known_limitations", profile.required_categories)
        self.assertIn("artifacts", profile.required_categories)

        items = {item.item_id: item for item in profile.checklist_items}
        for item_id in (
            "local_checks",
            "spec_reference_drift",
            "story_coverage_drift",
            "verilator_fast_suite",
            "verilator_full_suite",
            "first_cpu_pass_archive",
            "interactive_board_session",
            "reproducible_build_manifest",
            "known_limitations",
            "release_bundle",
        ):
            with self.subTest(item_id=item_id):
                self.assertIn(item_id, items)
                self.assertTrue(items[item_id].required)
                self.assertTrue(items[item_id].gate)
                self.assertTrue(items[item_id].acceptance)

        self.assertIn("I33-S02", " ".join(profile.handoffs))
        self.assertIn("I33-S04", " ".join(profile.handoffs))
        self.assertIn("I33-S05", " ".join(profile.handoffs))

    def test_template_and_required_fields_cover_release_readiness(self) -> None:
        profile = release_candidate_checklist.release_candidate_checklist_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = release_candidate_checklist.release_candidate_checklist_template(profile)

        for name in (
            "story",
            "release_candidate_id",
            "repository_commit",
            "target_board",
            "local_checks_status",
            "spec_reference_status",
            "story_coverage_status",
            "fast_verilator_status",
            "full_verilator_status",
            "first_pass_archive_status",
            "monitor_board_session_status",
            "reproducible_build_status",
            "known_limitations_status",
            "artifact_manifest_status",
            "known_limitations_path",
            "artifact_manifest_path",
            "rc_decision",
            "residual_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S01", template)
        self.assertIn("target_board=Sipeed Tang Mega Dock with 138K SOM", template)
        self.assertIn("rc_decision=ready_for_rc_tag", template)
        self.assertIn("residual_blockers=none", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_candidate_checklist.parse_release_candidate_checklist(
            release_candidate_checklist.release_candidate_checklist_template()
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T16:00:00")
        )

        audit = release_candidate_checklist.audit_release_candidate_checklist(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.rc_decision, "ready_for_rc_tag")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("I33-S02", " ".join(audit.actions))

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_candidate_checklist.release_candidate_checklist_template()
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T16:00:00")
        )
        bad_status = release_candidate_checklist.audit_release_candidate_checklist(
            release_candidate_checklist.parse_release_candidate_checklist(
                base.replace("full_verilator_status=passed", "full_verilator_status=failed")
            )
        )
        bad_artifact = release_candidate_checklist.audit_release_candidate_checklist(
            release_candidate_checklist.parse_release_candidate_checklist(
                base.replace(
                    "known_limitations_path=docs/implementation/single-core-v0.1-known-limitations.md",
                    "known_limitations_path=docs/implementation/wrong.md",
                )
            )
        )
        blocked_without_blockers = release_candidate_checklist.audit_release_candidate_checklist(
            release_candidate_checklist.parse_release_candidate_checklist(
                base.replace("rc_decision=ready_for_rc_tag", "rc_decision=blocked")
            )
        )
        missing = release_candidate_checklist.load_release_candidate_checklist_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s01.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("full_verilator_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("known_limitations_path", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocked_without_blockers.status, "needs_followup")
        self.assertIn("residual_blockers", " ".join(blocked_without_blockers.blocker_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Release-candidate checklist issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S01")
        self.assertIn("fpga_evidence", parsed["required_categories"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("full_verilator_status=passed", stream.getvalue())
        self.assertIn("artifact_manifest_path=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s01.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_checklist_evidence_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "release-candidate-checklist.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S01",
            "python tools\\release_candidate_checklist.py --check",
            "docs/implementation/evidence/i33_s01_release_candidate_checklist.txt",
            "python tools\\local_checks.py",
            "python tools\\verilator_diff_harness.py --suite fast",
            "python tools\\verilator_diff_harness.py --suite all",
            "python tools\\fpga_first_pass_archive.py --check",
            "python tools\\fpga_monitor_board_session.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "known_limitations_path",
            "artifact_manifest_path",
            "ready_for_rc_tag",
            "residual_blockers",
            "I33-S02",
            "I33-S04",
            "I33-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

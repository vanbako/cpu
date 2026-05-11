"""I33-S03 conformance tests for release traceability audit."""

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
TOOL = ROOT / "tools" / "release_traceability_audit.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_traceability_audit


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_traceability_audit_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseTraceabilityAuditTests(unittest.TestCase):
    def test_release_traceability_self_validation_passes(self) -> None:
        self.assertEqual(
            release_traceability_audit.validate_release_traceability(ROOT),
            (),
        )

    def test_profile_names_required_commands_scopes_and_handoffs(self) -> None:
        profile = release_traceability_audit.release_traceability_profile()

        self.assertEqual(profile.story, "I33-S03")
        self.assertEqual(profile.status, "blocked_until_traceability_evidence")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i33_s03_release_traceability_audit.txt",
        )
        self.assertEqual(
            profile.summary_path.as_posix(),
            "docs/implementation/evidence/i33_s03_traceability_summary.json",
        )
        self.assertIn("traceability_audit_clean", profile.accepted_results)
        self.assertIn("traceability_blocker_captured", profile.accepted_results)

        commands = {command.name: command for command in profile.commands}
        for name in (
            "release_regression_capture",
            "spec_reference",
            "story_coverage",
            "test_index",
            "story_drift",
            "traceability_summary",
        ):
            with self.subTest(name=name):
                self.assertIn(name, commands)
                self.assertTrue(commands[name].required)
                self.assertTrue(commands[name].command)

        scopes = {scope.name for scope in profile.scopes}
        for name in (
            "implementation_stories",
            "conformance_tests",
            "litmus_tests",
            "rtl_gate_rows",
            "evidence_notes",
            "owner_coverage",
            "stale_references",
        ):
            self.assertIn(name, scopes)

        self.assertEqual(
            profile.deferred_missing_stories,
            ("I34-S06",),
        )
        self.assertIn("I33-S04", " ".join(profile.handoffs))
        self.assertIn("I33-S05", " ".join(profile.handoffs))
        self.assertIn("I33-S06", " ".join(profile.handoffs))

    def test_current_inventory_has_clean_owner_and_test_coverage(self) -> None:
        inventory = release_traceability_audit.traceability_inventory(ROOT)
        profile = release_traceability_audit.release_traceability_profile()

        self.assertTrue(inventory.clean)
        self.assertEqual(
            inventory.missing_stories,
            profile.deferred_missing_stories,
        )
        self.assertEqual(
            inventory.conformance_test_count,
            inventory.indexed_conformance_test_count,
        )
        self.assertEqual(
            inventory.litmus_test_count,
            inventory.indexed_litmus_test_count,
        )
        self.assertGreater(inventory.rtl_artifact_rows, 0)
        self.assertGreater(inventory.evidence_note_rows, 0)
        self.assertEqual(release_traceability_audit.traceability_current_issues(ROOT, profile), ())

    def test_template_and_required_fields_cover_traceability_capture(self) -> None:
        template = release_traceability_audit.release_traceability_template(root=ROOT)

        for name in (
            "story",
            "audited_at",
            "repository_commit",
            "release_regression_capture",
            "release_regression_status",
            "spec_reference_log",
            "spec_reference_status",
            "story_coverage_log",
            "story_coverage_status",
            "test_index_log",
            "test_index_status",
            "story_drift_log",
            "story_drift_status",
            "traceability_summary",
            "traceability_status",
            "indexed_artifact_count",
            "indexed_story_count",
            "conformance_test_count",
            "litmus_test_count",
            "rtl_artifact_rows",
            "evidence_note_rows",
            "unindexed_tests",
            "stale_references",
            "missing_owner_coverage",
            "deferred_missing_stories",
            "traceability_result",
            "traceability_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S03", template)
        self.assertIn("release_regression_capture=docs/implementation/evidence/i33_s02_release_regression_capture.txt", template)
        self.assertIn("traceability_summary=docs/implementation/evidence/i33_s03_traceability_summary.json", template)
        self.assertIn("unindexed_tests=none", template)
        self.assertIn("traceability_result=traceability_audit_clean", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_traceability_audit.parse_release_traceability(
            release_traceability_audit.release_traceability_template(root=ROOT)
            .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
        )

        audit = release_traceability_audit.audit_release_traceability(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.traceability_result, "traceability_audit_clean")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("I33-S04", " ".join(audit.actions))

    def test_blocker_record_can_be_accepted_when_findings_are_explained(self) -> None:
        record = release_traceability_audit.parse_release_traceability(
            release_traceability_audit.release_traceability_template(root=ROOT)
            .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("traceability_status=passed", "traceability_status=failed")
            .replace("unindexed_tests=none", "unindexed_tests=tests\\conformance\\test_i99_s01_new.py")
            .replace("traceability_result=traceability_audit_clean", "traceability_result=traceability_blocker_captured")
            .replace("traceability_blockers=none", "traceability_blockers=unindexed_test")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
        )

        audit = release_traceability_audit.audit_release_traceability(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.traceability_result, "traceability_blocker_captured")
        self.assertEqual(audit.status_issues, ())

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_traceability_audit.release_traceability_template(root=ROOT)
            .replace("audited_at=", "audited_at=2026-05-11T18:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T18:30:00")
        )
        bad_status = release_traceability_audit.audit_release_traceability(
            release_traceability_audit.parse_release_traceability(
                base.replace("story_coverage_status=passed", "story_coverage_status=failed")
            )
        )
        bad_artifact = release_traceability_audit.audit_release_traceability(
            release_traceability_audit.parse_release_traceability(
                base.replace(
                    "release_regression_capture=docs/implementation/evidence/i33_s02_release_regression_capture.txt",
                    "release_regression_capture=docs/implementation/evidence/wrong.txt",
                )
            )
        )
        blocker_without_blockers = release_traceability_audit.audit_release_traceability(
            release_traceability_audit.parse_release_traceability(
                base.replace(
                    "traceability_result=traceability_audit_clean",
                    "traceability_result=traceability_blocker_captured",
                ).replace("unindexed_tests=none", "unindexed_tests=tests\\conformance\\test_i99_s01_new.py")
            )
        )
        missing = release_traceability_audit.load_release_traceability_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s03.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("story_coverage_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("release_regression_capture", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocker_without_blockers.status, "needs_followup")
        self.assertIn("traceability_blockers", " ".join(blocker_without_blockers.traceability_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_summary_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Release traceability audit issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S03")
        self.assertIn("owner_coverage", [scope["name"] for scope in parsed["scopes"]])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--summary-json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertGreater(parsed["indexed_artifact_count"], 0)
        self.assertEqual(parsed["unindexed_tests"], [])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("traceability_result=traceability_audit_clean", stream.getvalue())
        self.assertIn("deferred_missing_stories=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s03.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_traceability_evidence_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "release-traceability-audit.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S03",
            "python tools\\release_traceability_audit.py --check",
            "docs/implementation/evidence/i33_s03_release_traceability_audit.txt",
            "docs/implementation/evidence/i33_s03_traceability_summary.json",
            "python tools\\release_regression_capture.py --check",
            "docs/implementation/evidence/i33_s02_release_regression_capture.txt",
            "python tools\\spec_reference_check.py",
            "python tools\\story_coverage.py --check-drift",
            "python -m unittest tests.conformance.test_i01_s03_test_index",
            "python -m unittest tests.conformance.test_i12_s03_story_drift",
            "conformance-test-index.md",
            "owner_coverage",
            "E15",
            "rtl_artifact_rows",
            "evidence_note_rows",
            "traceability_audit_clean",
            "traceability_blocker_captured",
            "I33-S04",
            "I33-S05",
            "I33-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

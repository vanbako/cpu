"""I33-S05 conformance tests for the release-candidate bundle."""

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
TOOL = ROOT / "tools" / "release_candidate_bundle.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_candidate_bundle


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_candidate_bundle_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseCandidateBundleTests(unittest.TestCase):
    def test_release_bundle_self_validation_passes(self) -> None:
        self.assertEqual(
            release_candidate_bundle.validate_release_bundle(ROOT),
            (),
        )

    def test_profile_names_required_categories_artifacts_and_handoffs(self) -> None:
        profile = release_candidate_bundle.release_bundle_profile()

        self.assertEqual(profile.story, "I33-S05")
        self.assertEqual(profile.status, "blocked_until_release_candidate_bundle")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i33_s05_release_candidate_bundle.txt",
        )
        self.assertEqual(
            profile.manifest_path.as_posix(),
            "docs/implementation/evidence/i33_s05_release_candidate_manifest.json",
        )
        self.assertIn("release_candidate_bundle_captured", profile.accepted_results)
        self.assertIn("release_candidate_bundle_blocker_captured", profile.accepted_results)

        categories = {artifact.category for artifact in profile.artifacts}
        for category in (
            "commit",
            "tool_versions",
            "generated_images",
            "bitstream_hashes",
            "reports",
            "evidence_archives",
            "documents",
            "rerun_commands",
        ):
            self.assertIn(category, categories)

        commands = " ".join(profile.rerun_commands)
        self.assertIn("release_known_limitations.py", commands)
        self.assertIn("fpga_reproducible_build.py", commands)
        self.assertIn("fpga_bram_images.py", commands)
        self.assertIn("fpga_gowin_reports.py", commands)
        self.assertIn("I33-S06", " ".join(profile.handoffs))

    def test_template_and_required_fields_cover_bundle_record(self) -> None:
        profile = release_candidate_bundle.release_bundle_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = release_candidate_bundle.release_bundle_template(profile)

        for name in (
            "story",
            "bundled_at",
            "repository_commit",
            "release_candidate_id",
            "release_checklist",
            "release_checklist_status",
            "regression_capture",
            "regression_status",
            "traceability_audit",
            "traceability_status",
            "known_limitations",
            "known_limitations_status",
            "reproducible_build_manifest",
            "reproducible_build_status",
            "tool_versions_path",
            "tool_versions_status",
            "generated_images_manifest",
            "generated_images_status",
            "bitstream_hashes",
            "bitstream_status",
            "gowin_reports",
            "report_status",
            "evidence_archives",
            "evidence_status",
            "docs_archive",
            "docs_status",
            "rerun_commands",
            "rerun_status",
            "bundle_manifest",
            "bundle_result",
            "release_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S05", template)
        self.assertIn("release_candidate_id=single-core-v0.1-rc1", template)
        self.assertIn("known_limitations=docs/implementation/single-core-v0.1-known-limitations.md", template)
        self.assertIn("reproducible_build_manifest=docs/implementation/evidence/i28_s05_reproducible_build_manifest.json", template)
        self.assertIn("bundle_result=release_candidate_bundle_captured", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_candidate_bundle.parse_release_bundle(
            release_candidate_bundle.release_bundle_template()
            .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
        )

        audit = release_candidate_bundle.audit_release_bundle(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.bundle_result, "release_candidate_bundle_captured")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("I33-S06", " ".join(audit.actions))

    def test_blocker_record_can_be_accepted_when_findings_are_named(self) -> None:
        record = release_candidate_bundle.parse_release_bundle(
            release_candidate_bundle.release_bundle_template()
            .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("report_status=captured", "report_status=blocked")
            .replace("bundle_result=release_candidate_bundle_captured", "bundle_result=release_candidate_bundle_blocker_captured")
            .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=gowin_reports_missing")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
        )

        audit = release_candidate_bundle.audit_release_bundle(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.bundle_result, "release_candidate_bundle_blocker_captured")

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_candidate_bundle.release_bundle_template()
            .replace("bundled_at=", "bundled_at=2026-05-11T20:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T20:30:00")
        )
        bad_status = release_candidate_bundle.audit_release_bundle(
            release_candidate_bundle.parse_release_bundle(
                base.replace("bitstream_status=captured", "bitstream_status=blocked")
            )
        )
        bad_artifact = release_candidate_bundle.audit_release_bundle(
            release_candidate_bundle.parse_release_bundle(
                base.replace(
                    "bundle_manifest=docs/implementation/evidence/i33_s05_release_candidate_manifest.json",
                    "bundle_manifest=docs/implementation/evidence/wrong.json",
                )
            )
        )
        blocker_without_blockers = release_candidate_bundle.audit_release_bundle(
            release_candidate_bundle.parse_release_bundle(
                base.replace(
                    "bundle_result=release_candidate_bundle_captured",
                    "bundle_result=release_candidate_bundle_blocker_captured",
                ).replace(
                    "release_blockers=physical_board_pass_blocked,release_candidate_not_tagged",
                    "release_blockers=none",
                )
            )
        )
        missing = release_candidate_bundle.load_release_bundle_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s05.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("bitstream_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("bundle_manifest", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocker_without_blockers.status, "needs_followup")
        self.assertIn("release_blockers", " ".join(blocker_without_blockers.blocker_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_templates_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Release-candidate bundle issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S05")
        self.assertIn("generated_images", parsed["required_categories"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--manifest-template"])

        self.assertEqual(result, 0)
        self.assertIn("bundle_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bundle_result=release_candidate_bundle_captured", stream.getvalue())
        self.assertIn("rerun_commands=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s05.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_bundle_artifacts_and_handoff(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "release-candidate-bundle.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S05",
            "python tools\\release_candidate_bundle.py --check",
            "docs/implementation/evidence/i33_s05_release_candidate_bundle.txt",
            "docs/implementation/evidence/i33_s05_release_candidate_manifest.json",
            "python tools\\release_known_limitations.py --check",
            "docs/implementation/single-core-v0.1-known-limitations.md",
            "docs/implementation/evidence/i28_s05_reproducible_build_manifest.json",
            "python tools\\fpga_program_manifest.py --check",
            "python tools\\fpga_bram_images.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "tool_versions_path",
            "generated_images_manifest",
            "bitstream_hashes",
            "gowin_reports",
            "evidence_archives",
            "docs_archive",
            "rerun_commands",
            "release_candidate_bundle_captured",
            "release_candidate_bundle_blocker_captured",
            "I33-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

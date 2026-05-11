"""I33-S02 conformance tests for release regression capture."""

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
TOOL = ROOT / "tools" / "release_regression_capture.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_regression_capture


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_regression_capture_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseRegressionCaptureTests(unittest.TestCase):
    def test_release_regression_capture_self_validation_passes(self) -> None:
        self.assertEqual(
            release_regression_capture.validate_release_regression_capture(ROOT),
            (),
        )

    def test_profile_names_required_commands_artifacts_and_handoffs(self) -> None:
        profile = release_regression_capture.release_regression_capture_profile()

        self.assertEqual(profile.story, "I33-S02")
        self.assertEqual(profile.status, "blocked_until_full_regression_capture")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i33_s02_release_regression_capture.txt",
        )
        self.assertIn("full_regression_artifacts_captured", profile.accepted_results)
        self.assertIn("regression_blocker_captured", profile.accepted_results)

        commands = {command.name: command for command in profile.commands}
        for name in (
            "release_checklist_audit",
            "local_checks",
            "spec_reference",
            "story_coverage",
            "verilator_fast",
            "verilator_slow",
            "verilator_all",
        ):
            with self.subTest(name=name):
                self.assertIn(name, commands)
                self.assertTrue(commands[name].required)
                self.assertTrue(commands[name].command)

        self.assertGreaterEqual(
            len([command for command in profile.commands if command.category == "fpga_validators"]),
            4,
        )
        self.assertIn("release_checklist", profile.artifact_requirements)
        self.assertIn("reproducible_build_manifest", profile.artifact_requirements)
        self.assertIn("command_log_archive", profile.artifact_requirements)
        self.assertIn("I33-S03", " ".join(profile.handoffs))
        self.assertIn("I33-S04", " ".join(profile.handoffs))
        self.assertIn("I33-S05", " ".join(profile.handoffs))

    def test_template_and_required_fields_cover_full_regression_capture(self) -> None:
        profile = release_regression_capture.release_regression_capture_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = release_regression_capture.release_regression_capture_template(profile)

        for name in (
            "story",
            "captured_at",
            "repository_commit",
            "release_candidate_id",
            "release_checklist",
            "release_checklist_status",
            "local_checks_log",
            "local_checks_status",
            "spec_reference_log",
            "spec_reference_status",
            "story_coverage_log",
            "story_coverage_status",
            "fast_verilator_log",
            "fast_verilator_status",
            "slow_verilator_log",
            "slow_verilator_status",
            "full_verilator_log",
            "full_verilator_status",
            "fpga_validator_logs",
            "fpga_validator_status",
            "reproducible_build_manifest",
            "reproducible_build_status",
            "command_log_archive",
            "unexplained_failures",
            "regression_result",
            "residual_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S02", template)
        self.assertIn("release_checklist=docs/implementation/evidence/i33_s01_release_candidate_checklist.txt", template)
        self.assertIn("slow_verilator_status=passed", template)
        self.assertIn("reproducible_build_manifest=docs/implementation/evidence/i28_s05_reproducible_build_manifest.json", template)
        self.assertIn("regression_result=full_regression_artifacts_captured", template)
        self.assertIn("residual_blockers=none", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_regression_capture.parse_release_regression_capture(
            release_regression_capture.release_regression_capture_template()
            .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
        )

        audit = release_regression_capture.audit_release_regression_capture(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.regression_result, "full_regression_artifacts_captured")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("I33-S03", " ".join(audit.actions))

    def test_blocker_record_can_be_accepted_when_failures_are_explained(self) -> None:
        record = release_regression_capture.parse_release_regression_capture(
            release_regression_capture.release_regression_capture_template()
            .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("full_verilator_status=passed", "full_verilator_status=failed")
            .replace(
                "regression_result=full_regression_artifacts_captured",
                "regression_result=regression_blocker_captured",
            )
            .replace("residual_blockers=none", "residual_blockers=verilator_full_timeout")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
        )

        audit = release_regression_capture.audit_release_regression_capture(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.regression_result, "regression_blocker_captured")
        self.assertEqual(audit.status_issues, ())

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_regression_capture.release_regression_capture_template()
            .replace("captured_at=", "captured_at=2026-05-11T17:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T17:30:00")
        )
        bad_status = release_regression_capture.audit_release_regression_capture(
            release_regression_capture.parse_release_regression_capture(
                base.replace("slow_verilator_status=passed", "slow_verilator_status=failed")
            )
        )
        bad_artifact = release_regression_capture.audit_release_regression_capture(
            release_regression_capture.parse_release_regression_capture(
                base.replace(
                    "release_checklist=docs/implementation/evidence/i33_s01_release_candidate_checklist.txt",
                    "release_checklist=docs/implementation/evidence/wrong.txt",
                )
            )
        )
        blocker_without_blockers = release_regression_capture.audit_release_regression_capture(
            release_regression_capture.parse_release_regression_capture(
                base.replace(
                    "regression_result=full_regression_artifacts_captured",
                    "regression_result=regression_blocker_captured",
                )
            )
        )
        missing = release_regression_capture.load_release_regression_capture_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s02.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("slow_verilator_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("release_checklist", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocker_without_blockers.status, "needs_followup")
        self.assertIn("residual_blockers", " ".join(blocker_without_blockers.blocker_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Release regression capture issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S02")
        self.assertIn("release_checklist", parsed["artifact_requirements"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("full_verilator_status=passed", stream.getvalue())
        self.assertIn("command_log_archive=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s02.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_capture_evidence_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "release-regression-capture.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S02",
            "python tools\\release_regression_capture.py --check",
            "docs/implementation/evidence/i33_s02_release_regression_capture.txt",
            "python tools\\release_candidate_checklist.py --audit-evidence",
            "docs/implementation/evidence/i33_s01_release_candidate_checklist.txt",
            "python tools\\local_checks.py",
            "python tools\\spec_reference_check.py",
            "python tools\\story_coverage.py --check-drift",
            "python tools\\verilator_diff_harness.py --suite fast",
            "python tools\\verilator_diff_harness.py --suite slow",
            "python tools\\verilator_diff_harness.py --suite all",
            "fpga_validator_logs",
            "python tools\\fpga_reproducible_build.py --check",
            "reproducible_build_manifest",
            "command_log_archive",
            "unexplained_failures",
            "full_regression_artifacts_captured",
            "regression_blocker_captured",
            "I33-S03",
            "I33-S04",
            "I33-S05",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

"""I33-S06 conformance tests for release-findings backlog triage."""

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
TOOL = ROOT / "tools" / "release_findings_backlog.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_findings_backlog


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_findings_backlog_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseFindingsBacklogTests(unittest.TestCase):
    def test_release_findings_self_validation_passes(self) -> None:
        self.assertEqual(
            release_findings_backlog.validate_release_findings(ROOT),
            (),
        )

    def test_profile_names_required_categories_routes_and_handoffs(self) -> None:
        profile = release_findings_backlog.release_findings_profile()

        self.assertEqual(profile.story, "I33-S06")
        self.assertEqual(profile.status, "blocked_until_release_findings_triage")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i33_s06_release_findings_backlog.txt",
        )
        self.assertEqual(
            profile.manifest_path.as_posix(),
            "docs/implementation/evidence/i33_s06_release_findings_backlog.json",
        )
        self.assertEqual(
            profile.release_bundle_evidence.as_posix(),
            "docs/implementation/evidence/i33_s05_release_candidate_bundle.txt",
        )
        self.assertIn("release_findings_backlog_opened", profile.accepted_results)
        self.assertIn("release_findings_blocker_captured", profile.accepted_results)

        categories = {route.category for route in profile.routes}
        for category in (
            "release_blockers",
            "implementation_followups",
            "architecture_findings",
            "board_followups",
            "retest_commands",
            "tag_decision_handoff",
        ):
            self.assertIn(category, categories)

        routes = {route.finding_id: route for route in profile.routes}
        for finding_id in (
            "physical_board_pass_blocked",
            "release_candidate_not_tagged",
            "rtl_unsupported_capability_subset",
            "multicore_fabric_deferred",
            "ddr_board_ip_deferred",
            "retro_console_60k_deferred",
            "cacheable_tag_policy_deferred",
            "architecture_errata_none_known",
            "release_retest_commands",
        ):
            with self.subTest(finding_id=finding_id):
                self.assertIn(finding_id, routes)
                self.assertEqual(routes[finding_id].frozen_contract_impact, "unchanged")
                self.assertTrue(routes[finding_id].target_backlog)

        self.assertIn("post-v0.1", " ".join(profile.handoffs))
        self.assertIn("Architecture", " ".join(profile.handoffs))
        self.assertIn("tag decision", " ".join(profile.handoffs))

    def test_template_and_required_fields_cover_findings_record(self) -> None:
        profile = release_findings_backlog.release_findings_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = release_findings_backlog.release_findings_template(profile)

        for name in (
            "story",
            "triaged_at",
            "repository_commit",
            "release_candidate_bundle",
            "release_bundle_status",
            "bundle_manifest",
            "release_blockers",
            "implementation_findings",
            "architecture_findings",
            "board_findings",
            "deferred_work_status",
            "post_v0_1_backlog",
            "post_v0_1_backlog_status",
            "frozen_contract_status",
            "tag_decision_status",
            "retest_commands",
            "retest_status",
            "findings_result",
            "findings_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S06", template)
        self.assertIn("release_candidate_bundle=docs/implementation/evidence/i33_s05_release_candidate_bundle.txt", template)
        self.assertIn("bundle_manifest=docs/implementation/evidence/i33_s05_release_candidate_manifest.json", template)
        self.assertIn("post_v0_1_backlog=docs/implementation/evidence/i33_s06_release_findings_backlog.json", template)
        self.assertIn("frozen_contract_status=unchanged", template)
        self.assertIn("findings_result=release_findings_backlog_opened", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_findings_backlog.parse_release_findings(
            release_findings_backlog.release_findings_template()
            .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
        )

        audit = release_findings_backlog.audit_release_findings(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.findings_result, "release_findings_backlog_opened")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("post-v0.1", " ".join(audit.actions))

    def test_blocker_record_can_be_accepted_when_findings_are_named(self) -> None:
        record = release_findings_backlog.parse_release_findings(
            release_findings_backlog.release_findings_template()
            .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("release_bundle_status=accepted", "release_bundle_status=blocked")
            .replace("post_v0_1_backlog_status=opened", "post_v0_1_backlog_status=blocked")
            .replace("findings_result=release_findings_backlog_opened", "findings_result=release_findings_blocker_captured")
            .replace("findings_blockers=none", "findings_blockers=bundle_evidence_missing")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
        )

        audit = release_findings_backlog.audit_release_findings(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.findings_result, "release_findings_blocker_captured")

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_findings_backlog.release_findings_template()
            .replace("triaged_at=", "triaged_at=2026-05-11T21:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T21:30:00")
        )
        bad_status = release_findings_backlog.audit_release_findings(
            release_findings_backlog.parse_release_findings(
                base.replace("frozen_contract_status=unchanged", "frozen_contract_status=changed")
            )
        )
        bad_artifact = release_findings_backlog.audit_release_findings(
            release_findings_backlog.parse_release_findings(
                base.replace(
                    "bundle_manifest=docs/implementation/evidence/i33_s05_release_candidate_manifest.json",
                    "bundle_manifest=docs/implementation/evidence/wrong.json",
                )
            )
        )
        blocker_without_blockers = release_findings_backlog.audit_release_findings(
            release_findings_backlog.parse_release_findings(
                base.replace(
                    "findings_result=release_findings_backlog_opened",
                    "findings_result=release_findings_blocker_captured",
                )
            )
        )
        missing = release_findings_backlog.load_release_findings_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s06.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("frozen_contract_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("bundle_manifest", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocker_without_blockers.status, "needs_followup")
        self.assertIn("findings_blockers", " ".join(blocker_without_blockers.blocker_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_templates_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Release-findings backlog issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S06")
        self.assertIn("release_blockers", parsed["required_categories"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--manifest-template"])

        self.assertEqual(result, 0)
        self.assertIn("frozen_contract_status", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("findings_result=release_findings_backlog_opened", stream.getvalue())
        self.assertIn("retest_commands=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s06.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_findings_routes_and_contract_guard(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "release-findings-backlog.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S06",
            "python tools\\release_findings_backlog.py --check",
            "docs/implementation/evidence/i33_s06_release_findings_backlog.txt",
            "docs/implementation/evidence/i33_s06_release_findings_backlog.json",
            "python tools\\release_candidate_bundle.py --check",
            "docs/implementation/evidence/i33_s05_release_candidate_bundle.txt",
            "docs/implementation/evidence/i33_s05_release_candidate_manifest.json",
            "release_blockers",
            "implementation_findings",
            "architecture_findings",
            "board_findings",
            "frozen_contract_status",
            "post_v0_1_backlog",
            "retest_commands",
            "release_findings_backlog_opened",
            "release_findings_blocker_captured",
            "post-v0.1",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

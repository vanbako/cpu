"""I33-S04 conformance tests for known-limitations freeze."""

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
TOOL = ROOT / "tools" / "release_known_limitations.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_known_limitations


def load_tool_module():
    spec = importlib.util.spec_from_file_location("release_known_limitations_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseKnownLimitationsTests(unittest.TestCase):
    def test_release_limitations_self_validation_passes(self) -> None:
        self.assertEqual(
            release_known_limitations.validate_release_limitations(ROOT),
            (),
        )

    def test_profile_names_required_categories_items_and_handoffs(self) -> None:
        profile = release_known_limitations.release_limitations_profile()

        self.assertEqual(profile.story, "I33-S04")
        self.assertEqual(profile.status, "blocked_until_known_limitations_freeze")
        self.assertEqual(
            profile.document_path.as_posix(),
            "docs/implementation/single-core-v0.1-known-limitations.md",
        )
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i33_s04_known_limitations_freeze.txt",
        )
        self.assertIn("known_limitations_frozen", profile.accepted_results)
        self.assertIn("known_limitations_blocker_captured", profile.accepted_results)

        categories = {item.category for item in profile.items}
        for category in (
            "unsupported_features",
            "board_blockers",
            "multicore_fabric",
            "ddr_external_memory",
            "cacheable_tag_behavior",
            "architecture_errata",
            "release_scope",
        ):
            self.assertIn(category, categories)

        items = {item.item_id: item for item in profile.items}
        for item_id in (
            "rtl_unsupported_capability_subset",
            "physical_board_pass_blocked",
            "retro_console_60k_deferred",
            "single_core_only",
            "ddr_board_ip_deferred",
            "external_cacheable_tags_deferred",
            "architecture_errata_none_known",
            "release_candidate_not_tagged",
        ):
            with self.subTest(item_id=item_id):
                self.assertIn(item_id, items)
                self.assertTrue(items[item_id].evidence)
                self.assertTrue(items[item_id].follow_up)

        self.assertTrue(items["physical_board_pass_blocked"].release_blocker)
        self.assertTrue(items["release_candidate_not_tagged"].release_blocker)
        self.assertIn("I33-S05", " ".join(profile.handoffs))
        self.assertIn("I33-S06", " ".join(profile.handoffs))

    def test_template_and_required_fields_cover_freeze_record(self) -> None:
        profile = release_known_limitations.release_limitations_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = release_known_limitations.release_limitations_template(profile)

        for name in (
            "story",
            "frozen_at",
            "repository_commit",
            "traceability_audit",
            "traceability_status",
            "limitations_doc",
            "unsupported_features_status",
            "board_blockers_status",
            "multicore_fabric_status",
            "ddr_external_memory_status",
            "cacheable_tag_status",
            "architecture_errata_status",
            "release_scope_status",
            "limitations_result",
            "release_blockers",
            "signed_off_by",
            "signed_off_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I33-S04", template)
        self.assertIn("traceability_audit=docs/implementation/evidence/i33_s03_release_traceability_audit.txt", template)
        self.assertIn("limitations_doc=docs/implementation/single-core-v0.1-known-limitations.md", template)
        self.assertIn("architecture_errata_status=none_known", template)
        self.assertIn("limitations_result=known_limitations_frozen", template)

    def test_complete_record_audits_as_accepted(self) -> None:
        record = release_known_limitations.parse_release_limitations(
            release_known_limitations.release_limitations_template()
            .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
        )

        audit = release_known_limitations.audit_release_limitations(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.status, "accepted")
        self.assertEqual(audit.limitations_result, "known_limitations_frozen")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.status_issues, ())
        self.assertIn("I33-S05", " ".join(audit.actions))

    def test_blocker_record_can_be_accepted_when_findings_are_named(self) -> None:
        record = release_known_limitations.parse_release_limitations(
            release_known_limitations.release_limitations_template()
            .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("board_blockers_status=listed", "board_blockers_status=incomplete")
            .replace("limitations_result=known_limitations_frozen", "limitations_result=known_limitations_blocker_captured")
            .replace("release_blockers=physical_board_pass_blocked,release_candidate_not_tagged", "release_blockers=board_blocker_inventory_incomplete")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
        )

        audit = release_known_limitations.audit_release_limitations(record)

        self.assertTrue(audit.accepted)
        self.assertEqual(audit.limitations_result, "known_limitations_blocker_captured")

    def test_bad_status_artifact_or_blocker_record_fails_cleanly(self) -> None:
        base = (
            release_known_limitations.release_limitations_template()
            .replace("frozen_at=", "frozen_at=2026-05-11T19:00:00")
            .replace("repository_commit=", "repository_commit=0123456789abcdef")
            .replace("signed_off_by=", "signed_off_by=release-manager")
            .replace("signed_off_at=", "signed_off_at=2026-05-11T19:30:00")
        )
        bad_status = release_known_limitations.audit_release_limitations(
            release_known_limitations.parse_release_limitations(
                base.replace("ddr_external_memory_status=listed", "ddr_external_memory_status=incomplete")
            )
        )
        bad_artifact = release_known_limitations.audit_release_limitations(
            release_known_limitations.parse_release_limitations(
                base.replace(
                    "traceability_audit=docs/implementation/evidence/i33_s03_release_traceability_audit.txt",
                    "traceability_audit=docs/implementation/evidence/wrong.txt",
                )
            )
        )
        blocker_without_blockers = release_known_limitations.audit_release_limitations(
            release_known_limitations.parse_release_limitations(
                base.replace(
                    "limitations_result=known_limitations_frozen",
                    "limitations_result=known_limitations_blocker_captured",
                ).replace(
                    "release_blockers=physical_board_pass_blocked,release_candidate_not_tagged",
                    "release_blockers=none",
                )
            )
        )
        missing = release_known_limitations.load_release_limitations_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i33_s04.txt"),
        )

        self.assertEqual(bad_status.status, "invalid")
        self.assertIn("ddr_external_memory_status", " ".join(bad_status.status_issues))
        self.assertEqual(bad_artifact.status, "invalid")
        self.assertIn("traceability_audit", " ".join(bad_artifact.artifact_issues))
        self.assertEqual(blocker_without_blockers.status, "needs_followup")
        self.assertIn("release_blockers", " ".join(blocker_without_blockers.blocker_issues))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("repository_commit", missing.missing_fields)

    def test_cli_validates_prints_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Known-limitations freeze issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I33-S04")
        self.assertIn("board_blockers", parsed["required_categories"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("limitations_result=known_limitations_frozen", stream.getvalue())
        self.assertIn("release_blockers=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i33_s04.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_limitations_errata_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "single-core-v0.1-known-limitations.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I33-S04",
            "python tools\\release_known_limitations.py --check",
            "docs/implementation/evidence/i33_s04_known_limitations_freeze.txt",
            "python tools\\release_traceability_audit.py --check",
            "docs/implementation/evidence/i33_s03_release_traceability_audit.txt",
            "Unsupported Features",
            "Board Blockers",
            "Multicore And Fabric",
            "DDR And External Memory",
            "Cacheable And Tag Behavior",
            "Architecture Errata",
            "Tang Mega Dock with 138K SOM",
            "Tang Retro Console with 60K SOM",
            "CINCADDR",
            "CSETBOUNDS",
            "CSEAL",
            "CUNSEAL",
            "known_limitations_frozen",
            "known_limitations_blocker_captured",
            "I33-S05",
            "I33-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

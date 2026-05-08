"""I24-S05 conformance tests for first-board evidence archiving."""

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
TOOL = ROOT / "tools" / "fpga_first_board_archive.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_board_archive, fpga_programming


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_board_archive_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def passed_programming() -> fpga_programming.ProgrammingAudit:
    return fpga_programming.ProgrammingAudit(
        status="passed",
        message="passed",
        evidence_path="docs/implementation/evidence/i24_s04_sram_programming.txt",
        build_status="passed",
        missing_fields=(),
        observation_issues=(),
        actions=(),
    )


def good_record() -> fpga_first_board_archive.FirstBoardArchiveRecord:
    return fpga_first_board_archive.parse_first_board_archive(
        "\n".join(
            (
                "story=I24-S05",
                "board=Sipeed Tang Mega 138K Dock",
                "archived_at=2026-05-08T12:30:00",
                "identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
                "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
                "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
                "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                "programming_evidence=docs/implementation/evidence/i24_s04_sram_programming.txt",
                "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                "reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt",
                "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                "board_result=first_pass",
                "residual_blockers=none",
                "filed_issues=none",
                "retest_steps=none",
            )
        )
    )


class FpgaFirstBoardArchiveTests(unittest.TestCase):
    def test_archive_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_board_archive.validate_fpga_first_board_archive(ROOT), ())

    def test_profile_names_board_gate_path_and_required_links(self) -> None:
        profile = fpga_first_board_archive.fpga_first_board_archive_profile()

        self.assertEqual(profile.story, "I24-S05")
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.programming_gate, "python tools\\fpga_board_programming.py --check")
        self.assertEqual(profile.required_result, "first_pass")
        self.assertEqual(
            profile.archive_path.as_posix(),
            "docs/implementation/evidence/i24_s05_first_board_archive.txt",
        )

        fields = {field.name: field for field in profile.required_fields}
        for name in (
            "identity_evidence",
            "constraints_evidence",
            "gowin_report_bundle",
            "bitstream_path",
            "programming_evidence",
            "programming_log",
            "reset_observation",
            "led_evidence",
            "residual_blockers",
            "filed_issues",
            "retest_steps",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                if name in profile.link_fields:
                    self.assertIn(name, profile.link_fields)

    def test_template_and_passing_archive_audit(self) -> None:
        template = fpga_first_board_archive.first_board_archive_template()
        self.assertIn("story=I24-S05", template)
        self.assertIn("programming_evidence=docs/implementation/evidence/i24_s04_sram_programming.txt", template)
        self.assertIn("board_result=first_pass", template)
        self.assertIn("residual_blockers=none", template)

        audit = fpga_first_board_archive.audit_first_board_archive(
            good_record(),
            programming_audit=passed_programming(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "archived")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.blocker_issues, ())
        self.assertIn("downstream FPGA stories", " ".join(audit.actions))

    def test_archive_blocks_without_passed_programming(self) -> None:
        blocked_programming = fpga_programming.ProgrammingAudit(
            status="blocked",
            message="blocked",
            evidence_path="docs/implementation/evidence/i24_s04_sram_programming.txt",
            build_status="blocked",
            missing_fields=("programming_log",),
            observation_issues=(),
            actions=(),
        )

        audit = fpga_first_board_archive.audit_first_board_archive(
            good_record(),
            programming_audit=blocked_programming,
        )

        self.assertEqual(audit.status, "blocked")
        self.assertIn("I24-S04", " ".join(audit.actions))

    def test_archive_needs_followup_for_unfiled_residual_blockers(self) -> None:
        record = fpga_first_board_archive.parse_first_board_archive(
            "\n".join(
                (
                    "story=I24-S05",
                    "board=Sipeed Tang Mega 138K Dock",
                    "archived_at=2026-05-08T12:30:00",
                    "identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt",
                    "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
                    "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
                    "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                    "programming_evidence=docs/implementation/evidence/i24_s04_sram_programming.txt",
                    "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                    "reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt",
                    "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                    "board_result=first_pass",
                    "residual_blockers=timing margin unclear",
                    "filed_issues=none",
                    "retest_steps=none",
                )
            )
        )

        audit = fpga_first_board_archive.audit_first_board_archive(
            record,
            programming_audit=passed_programming(),
        )

        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("residual blockers must have filed_issues", audit.blocker_issues)
        self.assertIn("residual blockers must have retest_steps", audit.blocker_issues)

    def test_archive_rejects_placeholder_links_and_bad_bitstream(self) -> None:
        record = fpga_first_board_archive.parse_first_board_archive(
            "\n".join(
                (
                    "story=I24-S05",
                    "board=Sipeed Tang Mega 138K Dock",
                    "archived_at=2026-05-08T12:30:00",
                    "identity_evidence=blocked",
                    "constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt",
                    "gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl",
                    "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.bit",
                    "programming_evidence=docs/implementation/evidence/i23_old_programming.txt",
                    "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                    "reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt",
                    "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                    "board_result=first_pass",
                    "residual_blockers=none",
                    "filed_issues=none",
                    "retest_steps=none",
                )
            )
        )

        audit = fpga_first_board_archive.audit_first_board_archive(
            record,
            programming_audit=passed_programming(),
        )

        self.assertEqual(audit.status, "invalid")
        self.assertIn("identity_evidence must link concrete evidence", audit.link_issues)
        self.assertIn("bitstream_path must name a .fs file", audit.link_issues)
        self.assertIn("programming_evidence must link the I24-S04 record", audit.link_issues)

    def test_cli_validates_renders_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-board archive issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I24-S05")
        self.assertEqual(parsed["required_result"], "first_pass")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("residual_blockers=none", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-archive",
                    "docs/implementation/evidence/definitely_missing_i24_s05.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_required_links_and_blocker_disposition(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-board-evidence.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I24-S05", text)
        self.assertIn("python tools\\fpga_first_board_archive.py --check", text)
        self.assertIn("docs/implementation/evidence/i24_s05_first_board_archive.txt", text)
        self.assertIn("python tools\\fpga_board_programming.py --check", text)
        self.assertIn("docs/implementation/evidence/i24_s04_sram_programming.txt", text)
        self.assertIn("identity_evidence", text)
        self.assertIn("constraints_evidence", text)
        self.assertIn("gowin_report_bundle", text)
        self.assertIn("bitstream_path", text)
        self.assertIn("programming_log", text)
        self.assertIn("reset_observation", text)
        self.assertIn("led_evidence", text)
        self.assertIn("board_result=first_pass", text)
        self.assertIn("residual_blockers", text)
        self.assertIn("filed_issues", text)
        self.assertIn("retest_steps", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

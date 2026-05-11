"""I24-S04 conformance tests for SRAM programming evidence."""

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
TOOL = ROOT / "tools" / "fpga_board_programming.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gowin_build, fpga_programming


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_board_programming_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def passed_build() -> fpga_gowin_build.GowinReportAudit:
    return fpga_gowin_build.GowinReportAudit(
        status="passed",
        message="passed",
        build_root="build/fpga/tang_mega_138k/first_test",
        identity_status="confirmed",
        constraints_status="confirmed",
        missing_reports=(),
        token_issues=(),
        failure_markers=(),
        bitstreams=("build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",),
        actions=(),
    )


def good_record() -> fpga_programming.ProgrammingEvidenceRecord:
    return fpga_programming.parse_programming_evidence(
        "\n".join(
            (
                "story=I24-S04",
                "board=Sipeed Tang Mega Dock with 138K SOM",
                "gowin_build_root=build/fpga/tang_mega_138k/first_test",
                "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                "programming_tool=Gowin Programmer",
                "programming_mode=SRAM",
                "programming_result=success",
                "programmed_at=2026-05-08T12:00:00",
                "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                "reset_released=yes",
                "observation_duration_s=10",
                "heartbeat_observed=yes",
                "pass_led_observed=yes",
                "fail_led_observed=no",
                "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                "status_retire_count=8",
                "status_fault_code=0",
            )
        )
    )


class FpgaBoardProgrammingTests(unittest.TestCase):
    def test_programming_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_programming.validate_fpga_programming(ROOT), ())

    def test_profile_names_board_gate_mode_and_required_fields(self) -> None:
        profile = fpga_programming.fpga_programming_profile()

        self.assertEqual(profile.story, "I24-S04")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.build_gate, "python tools\\fpga_gowin_build.py --check")
        self.assertEqual(profile.required_mode, "SRAM")
        self.assertEqual(profile.minimum_observation_seconds, 10)
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i24_s04_sram_programming.txt",
        )

        fields = {field.name: field for field in profile.required_fields}
        for name in (
            "bitstream_path",
            "programming_tool",
            "programming_mode",
            "programming_result",
            "programming_log",
            "reset_released",
            "observation_duration_s",
            "heartbeat_observed",
            "pass_led_observed",
            "fail_led_observed",
            "led_evidence",
            "status_retire_count",
            "status_fault_code",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)

    def test_template_and_passing_audit(self) -> None:
        template = fpga_programming.programming_evidence_template()
        self.assertIn("story=I24-S04", template)
        self.assertIn("programming_mode=SRAM", template)
        self.assertIn("heartbeat_observed=", template)
        self.assertIn("status_fault_code=", template)

        audit = fpga_programming.audit_programming_evidence(
            good_record(),
            build_audit=passed_build(),
        )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.observation_issues, ())
        self.assertIn("I24-S05", " ".join(audit.actions))

    def test_audit_blocks_without_passed_gowin_build(self) -> None:
        blocked_build = fpga_gowin_build.GowinReportAudit(
            status="blocked",
            message="blocked",
            build_root="build/fpga/tang_mega_138k/first_test",
            identity_status="blocked",
            constraints_status="blocked",
            missing_reports=("bitstream",),
            token_issues=(),
            failure_markers=(),
            bitstreams=(),
            actions=(),
        )

        audit = fpga_programming.audit_programming_evidence(
            good_record(),
            build_audit=blocked_build,
        )

        self.assertEqual(audit.status, "blocked")
        self.assertIn("I24-S03", " ".join(audit.actions))

    def test_audit_fails_bad_observations(self) -> None:
        record = fpga_programming.parse_programming_evidence(
            "\n".join(
                (
                    "story=I24-S04",
                    "board=Sipeed Tang Mega Dock with 138K SOM",
                    "gowin_build_root=build/fpga/tang_mega_138k/first_test",
                    "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                    "programming_tool=Gowin Programmer",
                    "programming_mode=flash",
                    "programming_result=success",
                    "programmed_at=2026-05-08T12:00:00",
                    "programming_log=docs/implementation/evidence/i24_s04_programming.log",
                    "reset_released=yes",
                    "observation_duration_s=2",
                    "heartbeat_observed=no",
                    "pass_led_observed=no",
                    "fail_led_observed=yes",
                    "led_evidence=docs/implementation/evidence/i24_s04_led.mp4",
                    "status_retire_count=1",
                    "status_fault_code=3",
                )
            )
        )

        audit = fpga_programming.audit_programming_evidence(record, build_audit=passed_build())

        self.assertEqual(audit.status, "failed")
        self.assertIn("programming_mode must be SRAM", audit.observation_issues)
        self.assertIn("heartbeat_observed must be yes", audit.observation_issues)
        self.assertIn("fail_led_observed must be no", audit.observation_issues)
        self.assertIn("status_fault_code must be 0", audit.observation_issues)

    def test_cli_validates_renders_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA board programming issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I24-S04")
        self.assertEqual(parsed["required_mode"], "SRAM")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("programming_log=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i24_s04.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_required_evidence_and_handoff(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-board-programming.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I24-S04", text)
        self.assertIn("python tools\\fpga_board_programming.py --check", text)
        self.assertIn("python tools\\fpga_gowin_build.py --check", text)
        self.assertIn("docs/implementation/evidence/i24_s04_sram_programming.txt", text)
        self.assertIn("python tools\\fpga_gowin_build.py --audit-reports", text)
        self.assertIn("Gowin Programmer", text)
        self.assertIn("SRAM", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("status_retire_count", text)
        self.assertIn("status_fault_code", text)
        self.assertIn("programming_log", text)
        self.assertIn("led_evidence", text)
        self.assertIn("I24-S05", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

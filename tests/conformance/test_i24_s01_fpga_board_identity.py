"""I24-S01 conformance tests for Tang Mega 138K board identity evidence."""

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
TOOL = ROOT / "tools" / "fpga_board_identity.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_board_identity


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_board_identity_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaBoardIdentityTests(unittest.TestCase):
    def test_board_identity_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_board_identity.validate_fpga_board_identity(ROOT), ())

    def test_expectation_names_assumed_tang_mega_target_and_evidence_path(self) -> None:
        expectation = fpga_board_identity.board_identity_expectation()

        self.assertEqual(expectation.story, "I24-S01")
        self.assertEqual(expectation.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(expectation.assumed_device, "GW5AST-LV138PG484A")
        self.assertEqual(expectation.assumed_package, "PBG484A")
        self.assertIn("JTAG", expectation.assumed_device_version)
        self.assertEqual(
            expectation.evidence_path.as_posix(),
            "docs/implementation/evidence/i24_s01_device_identity.txt",
        )
        self.assertTrue(any("FPG676" in target for target in expectation.alternate_targets))

    def test_required_evidence_fields_and_template_are_explicit(self) -> None:
        expectation = fpga_board_identity.board_identity_expectation()
        fields = {field.name: field for field in expectation.required_fields}
        template = fpga_board_identity.identity_template(expectation)

        for name in (
            "story",
            "board",
            "source",
            "observed_device",
            "observed_package",
            "observed_device_version",
            "observed_tool",
            "observed_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I24-S01", template)
        self.assertIn("board=Sipeed Tang Mega 138K Dock", template)

    def test_identity_record_parser_and_confirmed_audit(self) -> None:
        record = fpga_board_identity.parse_identity_record(
            "\n".join(
                (
                    "story=I24-S01",
                    "board=Sipeed Tang Mega 138K Dock",
                    "source=programmer_jtag_scan",
                    "observed_device=GW5AST-LV138PG484A",
                    "observed_package=PBG484A",
                    "observed_device_version=B",
                    "observed_tool=Gowin Programmer",
                    "observed_at=2026-05-08T12:00:00",
                    "evidence_notes=scan screenshot captured",
                )
            )
        )

        audit = fpga_board_identity.audit_identity_record(record)

        self.assertTrue(audit.confirmed)
        self.assertEqual(audit.status, "confirmed")
        self.assertEqual(audit.observed_device, "GW5AST-LV138PG484A")
        self.assertEqual(audit.observed_package, "PBG484A")
        self.assertIn("I24-S02", " ".join(audit.actions))

    def test_fpg676_record_requires_target_profile_update(self) -> None:
        record = fpga_board_identity.parse_identity_record(
            "\n".join(
                (
                    "story=I24-S01",
                    "board=Sipeed Tang Mega 138K Dock",
                    "source=programmer_jtag_scan",
                    "observed_device=GW5AST-LV138FPG676A",
                    "observed_package=FPG676A",
                    "observed_device_version=C",
                    "observed_tool=Gowin Programmer",
                    "observed_at=2026-05-08T12:00:00",
                )
            )
        )

        audit = fpga_board_identity.audit_identity_record(record)

        self.assertEqual(audit.status, "target_mismatch")
        self.assertIn("FPG676", audit.message)
        self.assertIn("fpga_first_test.py", " ".join(audit.actions))
        self.assertIn("I23-S05", " ".join(audit.actions))

    def test_incomplete_record_is_invalid_and_missing_file_is_blocked(self) -> None:
        invalid_record = fpga_board_identity.parse_identity_record(
            "\n".join(
                (
                    "story=I24-S01",
                    "board=Sipeed Tang Mega 138K Dock",
                    "source=board_marking",
                )
            )
        )
        invalid_audit = fpga_board_identity.audit_identity_record(invalid_record)
        missing_audit = fpga_board_identity.load_identity_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i24_s01.txt"),
        )

        self.assertEqual(invalid_audit.status, "invalid")
        self.assertIn("observed_device", " ".join(invalid_audit.issues))
        self.assertEqual(missing_audit.status, "blocked")
        self.assertIn("missing board marking", " ".join(missing_audit.issues))

    def test_cli_validates_renders_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA board identity issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I24-S01")
        self.assertEqual(parsed["assumed_device"], "GW5AST-LV138PG484A")
        self.assertEqual(parsed["assumed_package"], "PBG484A")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("observed_device=", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i24_s01.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_commands_fields_mismatch_and_blocker(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-board-identity.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I24-S01", text)
        self.assertIn("python tools\\fpga_board_identity.py --check", text)
        self.assertIn("docs/implementation/evidence/i24_s01_device_identity.txt", text)
        self.assertIn("Sipeed Tang Mega 138K Dock", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("Gowin Programmer", text)
        self.assertIn("openFPGALoader --detect", text)
        self.assertIn("board_marking", text)
        self.assertIn("programmer_jtag_scan", text)
        self.assertIn("observed_device", text)
        self.assertIn("observed_package", text)
        self.assertIn("observed_device_version", text)
        self.assertIn("GW5AST-LV138FPG676A", text)
        self.assertIn("FPG676A", text)
        self.assertIn("I24-S02", text)
        self.assertIn("CST", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

"""I34-S01 conformance tests for Tang Retro Console 60K SOM identity."""

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
TOOL = ROOT / "tools" / "fpga_retro_console_identity.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_retro_console_identity


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_retro_console_identity_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaRetroConsoleIdentityTests(unittest.TestCase):
    def test_retro_console_identity_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_retro_console_identity.validate_fpga_retro_console_identity(ROOT),
            (),
        )

    def test_profile_defers_retro_console_60k_to_mega_dock_138k(self) -> None:
        profile = fpga_retro_console_identity.retro_console_identity_profile()

        self.assertEqual(profile.story, "I34-S01")
        self.assertEqual(profile.status, "retro_console_60k_deferred_from_138k_first_pass")
        self.assertEqual(profile.board, "Sipeed Tang Retro Console with 60K SOM")
        self.assertEqual(profile.primary_138k_target, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertFalse(profile.selected_first_target)
        self.assertIn("Tang Mega Dock with 138K SOM", profile.selection_reason)
        self.assertEqual(
            profile.first_test_profile_gate,
            "python tools\\fpga_first_test_profile.py --check",
        )
        self.assertEqual(
            profile.board_bringup_runbook_gate,
            "python -m unittest tests.conformance.test_i23_s06_fpga_board_bringup",
        )

    def test_template_and_required_fields_capture_board_handoff(self) -> None:
        profile = fpga_retro_console_identity.retro_console_identity_profile()
        fields = {field.name: field for field in profile.required_fields}
        template = fpga_retro_console_identity.identity_template(profile)

        for name in (
            "story",
            "board",
            "source",
            "observed_device",
            "observed_idcode",
            "observed_package",
            "observed_device_version",
            "gowin_part",
            "programming_path",
            "clock_sources",
            "reset_sources",
            "visible_outputs",
            "uart_debug_access",
            "selected_first_target",
            "primary_138k_target",
            "observed_tool",
            "observed_at",
        ):
            with self.subTest(name=name):
                self.assertIn(name, fields)
                self.assertTrue(fields[name].required)
                self.assertIn(f"{name}=", template)

        self.assertIn("story=I34-S01", template)
        self.assertIn("board=Sipeed Tang Retro Console with 60K SOM", template)
        self.assertIn("observed_idcode=", template)
        self.assertIn("selected_first_target=no", template)
        self.assertIn("primary_138k_target=Sipeed Tang Mega Dock with 138K SOM", template)

    def test_complete_record_audits_as_60k_alternate_target(self) -> None:
        record = fpga_retro_console_identity.parse_identity_record(
            "\n".join(
                (
                    "story=I34-S01",
                    "board=Sipeed Tang Retro Console with 60K SOM",
                    "source=board_marking+programmer_jtag_scan",
                    "observed_device=GW5AT-60B",
                    "observed_idcode=0x0001481B",
                    "observed_package=scan_recorded_package",
                    "observed_device_version=B",
                    "gowin_part=scan_recorded_gowin_part",
                    "programming_path=Gowin Programmer SRAM",
                    "clock_sources=verified Retro Console oscillator",
                    "reset_sources=verified Retro Console reset input",
                    "visible_outputs=heartbeat/pass/fail outputs from board evidence",
                    "uart_debug_access=verified UART status path",
                    "selected_first_target=no",
                    "primary_138k_target=Sipeed Tang Mega Dock with 138K SOM",
                    "observed_tool=Gowin Programmer",
                    "observed_at=2026-05-11T12:00:00",
                )
            )
        )

        audit = fpga_retro_console_identity.audit_identity_record(record)

        self.assertTrue(audit.selected)
        self.assertTrue(audit.ready_for_constraints)
        self.assertEqual(audit.status, "alternate_target_verified")
        self.assertEqual(audit.observed_device, "GW5AT-60B")
        self.assertEqual(audit.observed_idcode, "0x0001481B")
        self.assertEqual(audit.observed_package, "scan_recorded_package")
        self.assertEqual(audit.gowin_part, "scan_recorded_gowin_part")
        self.assertIn("I34-S02", " ".join(audit.actions))
        self.assertIn("Tang Mega Dock with 138K SOM", " ".join(audit.actions))

    def test_incomplete_or_unselected_record_is_invalid_and_missing_file_is_blocked(self) -> None:
        invalid = fpga_retro_console_identity.parse_identity_record(
            "\n".join(
                (
                    "story=I34-S01",
                    "board=Sipeed Tang Retro Console with 60K SOM",
                    "source=board_marking",
                    "selected_first_target=yes",
                )
            )
        )
        invalid_audit = fpga_retro_console_identity.audit_identity_record(invalid)
        missing_audit = fpga_retro_console_identity.load_identity_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i34_s01.txt"),
        )

        self.assertEqual(invalid_audit.status, "invalid")
        self.assertIn("observed_device", " ".join(invalid_audit.issues))
        self.assertIn("selected_first_target", " ".join(invalid_audit.issues))
        self.assertEqual(missing_audit.status, "blocked")
        self.assertIn("missing Retro Console", " ".join(missing_audit.issues))

    def test_profile_names_required_interfaces_and_blockers(self) -> None:
        profile = fpga_retro_console_identity.retro_console_identity_profile()

        programming = {item.name: item for item in profile.programming_paths}
        clock_reset = {item.name: item for item in profile.clock_reset_sources}
        outputs = {item.name: item for item in profile.visible_outputs}
        debug = {item.name: item for item in profile.debug_access}

        self.assertIn("gowin_programmer_sram", programming)
        self.assertTrue(programming["gowin_programmer_sram"].required)
        self.assertIn("clock_sources", clock_reset)
        self.assertIn("reset_sources", clock_reset)
        self.assertIn("heartbeat_output", outputs)
        self.assertIn("pass_fail_outputs", outputs)
        self.assertIn("uart_status", debug)
        self.assertTrue(debug["uart_status"].required)

        blockers = " ".join(profile.blockers)
        self.assertIn("device/package", blockers)
        self.assertIn("Tang Mega Dock with 138K SOM pin names", blockers)
        self.assertIn("I31/I32", blockers)

    def test_cli_validates_renders_json_template_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Retro Console identity issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I34-S01")
        self.assertEqual(parsed["board"], "Sipeed Tang Retro Console with 60K SOM")
        self.assertFalse(parsed["selected_first_target"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("gowin_part=", stream.getvalue())
        self.assertIn("selected_first_target=no", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i34_s01.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_identity_fields_and_handoffs(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-retro-console-identity.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I34-S01",
            "python tools\\fpga_retro_console_identity.py --check",
            "docs/implementation/evidence/i34_s01_retro_console_identity.txt",
            "Sipeed Tang Retro Console with 60K SOM",
            "GW5AT/GW5A 60B-class",
            "0x0001481B",
            "Sipeed Tang Mega Dock with 138K SOM",
            "python tools\\fpga_first_test_profile.py --check",
            "python -m unittest tests.conformance.test_i23_s06_fpga_board_bringup",
            "selected_first_target=no",
            "primary_138k_target=Sipeed Tang Mega Dock with 138K SOM",
            "observed_device",
            "observed_idcode",
            "observed_package",
            "gowin_part",
            "programming_path",
            "clock_sources",
            "reset_sources",
            "visible_outputs",
            "uart_debug_access",
            "Gowin Programmer SRAM",
            "do not assume Dock pin names",
            "I34-S02",
            "I34-S06",
            "blocked",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

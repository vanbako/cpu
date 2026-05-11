"""I31-S01 conformance tests for the first-pass FPGA build bundle."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_first_pass_bundle.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_bundle


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_first_pass_bundle_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def complete_bundle_text() -> str:
    return (
        fpga_first_pass_bundle.first_pass_bundle_template()
        .replace("prepared_at=", "prepared_at=2026-05-10T12:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )


class FpgaFirstPassBundleTests(unittest.TestCase):
    def test_first_pass_bundle_self_validation_passes(self) -> None:
        self.assertEqual(fpga_first_pass_bundle.validate_fpga_first_pass_bundle(ROOT), ())

    def test_profile_freezes_target_image_constraints_clock_loader_and_gates(self) -> None:
        profile = fpga_first_pass_bundle.fpga_first_pass_bundle_profile()

        self.assertEqual(profile.story, "I31-S01")
        self.assertEqual(profile.status, "blocked_pending_physical_evidence")
        self.assertEqual(
            profile.evidence_path.as_posix(),
            "docs/implementation/evidence/i31_s01_first_pass_build_bundle.txt",
        )
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.device, "GW5AST-LV138PG484A")
        self.assertEqual(profile.package, "PBG484A")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.selected_case, "reset_pass.first_test_pause_stream")
        self.assertEqual(profile.selected_image, "builtin.first_test_pause_stream")
        self.assertEqual(profile.clock_profile, "debug_direct_25mhz")
        self.assertEqual(profile.loader_status, "idle_disabled_for_first_pass_build")
        self.assertEqual(profile.build_root.as_posix(), "build/fpga/tang_mega_138k/first_test")
        self.assertEqual(
            profile.constraints_cst.as_posix(),
            "constraints/tang_mega_138k_first_test.cst",
        )
        self.assertEqual(
            profile.constraints_sdc.as_posix(),
            "constraints/tang_mega_138k_first_test.sdc",
        )

        for gate in (
            "python tools\\fpga_soc_top_archive.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "python tools\\fpga_board_identity.py --check",
            "python tools\\fpga_constraints_overlay.py --check",
            "python tools\\fpga_clock_profiles.py --check",
            "python tools\\fpga_smoke_corpus.py --check",
            "python tools\\fpga_soc_loader_handoff.py --check",
        ):
            self.assertIn(gate, profile.gates)

    def test_items_and_expected_signatures_cover_acceptance_surface(self) -> None:
        profile = fpga_first_pass_bundle.fpga_first_pass_bundle_profile()
        items = {item.name: item for item in profile.items}

        for item in (
            "selected_top",
            "selected_image",
            "constraints_cst",
            "constraints_sdc",
            "clock_profile",
            "loader_status",
            "expected_led_signature",
            "expected_uart_signature",
            "expected_probe_signature",
        ):
            self.assertIn(item, items)

        self.assertEqual(items["selected_top"].value, "cpu_v01_fpga_top")
        self.assertEqual(items["selected_image"].value, "builtin.first_test_pause_stream")
        self.assertEqual(items["loader_status"].value, "idle_disabled_for_first_pass_build")
        self.assertIn("blocked", items["constraints_cst"].status)

        led = profile.signature_by_interface("led").expected
        uart = profile.signature_by_interface("uart").expected
        probe = profile.signature_by_interface("probe").expected
        self.assertIn("led", led.lower())
        self.assertIn("pass", uart.lower())
        self.assertIn("retire", probe.lower())

    def test_template_and_audit_accept_complete_bundle(self) -> None:
        template = fpga_first_pass_bundle.first_pass_bundle_template()
        self.assertIn("story=I31-S01", template)
        self.assertIn("selected_image=builtin.first_test_pause_stream", template)
        self.assertIn("clock_profile=debug_direct_25mhz", template)
        self.assertIn("loader_status=idle_disabled_for_first_pass_build", template)
        self.assertIn("bundle_result=frozen_for_gowin", template)

        record = fpga_first_pass_bundle.parse_first_pass_bundle(complete_bundle_text())
        audit = fpga_first_pass_bundle.audit_first_pass_bundle(record)

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "frozen")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.link_issues, ())
        self.assertEqual(audit.selection_issues, ())
        self.assertEqual(audit.blocker_issues, ())
        self.assertIn("I31-S02", " ".join(audit.actions))

    def test_audit_blocks_default_and_rejects_wrong_selection_or_followup(self) -> None:
        default_audit = fpga_first_pass_bundle.load_first_pass_bundle_audit(ROOT)
        self.assertEqual(default_audit.status, "blocked")
        self.assertIn("selected_image", default_audit.missing_fields)

        wrong_selection = (
            complete_bundle_text()
            .replace("top_module=cpu_v01_fpga_top", "top_module=cpu_v01_core")
            .replace("clock_profile=debug_direct_25mhz", "clock_profile=release_pll_25mhz")
            .replace(
                "selected_image=builtin.first_test_pause_stream",
                "selected_image=call_return.direct_call_ret_fpga",
            )
        )
        audit = fpga_first_pass_bundle.audit_first_pass_bundle(
            fpga_first_pass_bundle.parse_first_pass_bundle(wrong_selection)
        )
        self.assertEqual(audit.status, "invalid")
        self.assertIn("top_module must be cpu_v01_fpga_top", audit.selection_issues)
        self.assertIn("clock_profile must be debug_direct_25mhz", audit.selection_issues)
        self.assertIn("selected_image must be builtin.first_test_pause_stream", audit.selection_issues)

        followup = complete_bundle_text().replace(
            "remaining_blockers=none",
            "remaining_blockers=identity_not_confirmed",
        )
        audit = fpga_first_pass_bundle.audit_first_pass_bundle(
            fpga_first_pass_bundle.parse_first_pass_bundle(followup)
        )
        self.assertEqual(audit.status, "needs_followup")
        self.assertIn("remaining_blockers must be none before I31-S02 handoff", audit.blocker_issues)

    def test_cli_validates_json_template_items_signatures_retest_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA first-pass build bundle issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I31-S01")
        self.assertEqual(parsed["selected_image"], "builtin.first_test_pause_stream")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("expected_uart_signature", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--items"])

        self.assertEqual(result, 0)
        self.assertIn("selected_top", stream.getvalue())
        self.assertIn("loader_status", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--signatures"])

        self.assertEqual(result, 0)
        self.assertIn("uart", stream.getvalue())
        self.assertIn("retire", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--retest"])

        self.assertEqual(result, 0)
        self.assertIn("fpga_gowin_build.py", stream.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = Path(tmpdir) / "i31_s01.txt"
            evidence.write_text(complete_bundle_text(), encoding="utf-8")
            stream = StringIO()
            with contextlib.redirect_stdout(stream):
                result = tool.main(["--audit", str(evidence)])

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status"], "frozen")

    def test_documentation_names_bundle_fields_and_handoff(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-first-pass-build-bundle.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I31-S01",
            "python tools\\fpga_first_pass_bundle.py --check",
            "docs/implementation/evidence/i31_s01_first_pass_build_bundle.txt",
            "python tools\\fpga_soc_top_archive.py --check",
            "python tools\\fpga_reproducible_build.py --check",
            "python tools\\fpga_board_identity.py --check",
            "python tools\\fpga_constraints_overlay.py --check",
            "cpu_v01_fpga_top",
            "builtin.first_test_pause_stream",
            "debug_direct_25mhz",
            "loader_status",
            "expected_led_signature",
            "expected_uart_signature",
            "expected_probe_signature",
            "frozen_for_gowin",
            "I31-S02",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

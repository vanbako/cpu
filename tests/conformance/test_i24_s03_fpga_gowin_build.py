"""I24-S03 conformance tests for the Gowin first-test build audit."""

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
TOOL = ROOT / "tools" / "fpga_gowin_build.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_board_identity, fpga_constraints, fpga_gowin_build


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_gowin_build_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def confirmed_identity() -> fpga_board_identity.BoardIdentityAudit:
    return fpga_board_identity.BoardIdentityAudit(
        status="confirmed",
        message="confirmed",
        evidence_path="identity.txt",
        observed_device="GW5AST-LV138PG484A",
        observed_package="PBG484A",
        observed_device_version="B",
        issues=(),
        actions=(),
    )


def confirmed_constraints() -> fpga_constraints.ConstraintOverlayAudit:
    return fpga_constraints.ConstraintOverlayAudit(
        status="confirmed",
        message="confirmed",
        evidence_path="pins.txt",
        identity_status="confirmed",
        missing_fields=(),
        missing_pins=(),
        actions=(),
    )


def write_fixture_reports(root: Path, *, timing_text: str | None = None) -> None:
    synthesis = root / "impl" / "gwsynthesis"
    pnr = root / "impl" / "pnr"
    synthesis.mkdir(parents=True)
    pnr.mkdir(parents=True)
    (synthesis / "synth.rpt").write_text(
        "Top cpu_v01_fpga_top\nInstance cpu_v01_core\n", encoding="utf-8"
    )
    (pnr / "first_timing.rpt").write_text(
        timing_text or "Clock board_clk_i\nSlack 1.250\n", encoding="utf-8"
    )
    (pnr / "first_ports.rpt").write_text(
        "\n".join(
            (
                "board_clk_i LOC P1",
                "board_reset_n_i LOC P2",
                "pass_led_o LOC P3",
                "fail_led_o LOC P4",
                "heartbeat_led_o LOC P5",
                "uart_tx_o LOC P6",
            )
        ),
        encoding="utf-8",
    )
    (pnr / "first_util.rpt").write_text("LUT 10\nRegister 20\n", encoding="utf-8")
    (pnr / "first.fs").write_text("bitstream", encoding="utf-8")


class FpgaGowinBuildTests(unittest.TestCase):
    def test_gowin_build_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_gowin_build.validate_fpga_gowin_build(ROOT), ())

    def test_profile_names_target_gates_steps_and_report_requirements(self) -> None:
        profile = fpga_gowin_build.fpga_gowin_build_profile()

        self.assertEqual(profile.story, "I24-S03")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.device, "GW5AST-LV138PG484A")
        self.assertEqual(profile.package, "PBG484A")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.build_root.as_posix(), "build/fpga/tang_mega_138k/first_test")
        self.assertEqual(profile.identity_gate, "python tools\\fpga_board_identity.py --check")
        self.assertEqual(profile.constraints_gate, "python tools\\fpga_constraints_overlay.py --check")

        steps = {step.name for step in profile.steps}
        self.assertIn("identity_audit", steps)
        self.assertIn("constraints_audit", steps)
        self.assertIn("gowin_run_all", steps)
        self.assertIn("report_audit", steps)

        requirements = {requirement.name: requirement for requirement in profile.report_requirements}
        self.assertIn("synthesis_report", requirements)
        self.assertIn("timing_report", requirements)
        self.assertIn("ports_report", requirements)
        self.assertIn("utilization_report", requirements)
        self.assertIn("bitstream", requirements)
        self.assertIn("black box", requirements["synthesis_report"].forbidden_tokens)
        self.assertIn("Slack -", requirements["timing_report"].forbidden_tokens)
        self.assertIn("pass_led_o", requirements["ports_report"].required_tokens)
        self.assertIn("uart_tx_o", requirements["ports_report"].required_tokens)

    def test_default_report_audit_is_blocked_without_physical_evidence(self) -> None:
        audit = fpga_gowin_build.audit_gowin_report_bundle(
            ROOT / "build" / "fpga" / "tang_mega_138k" / "first_test"
        )

        self.assertEqual(audit.status, "blocked")
        self.assertIn("identity", " ".join(audit.actions))
        self.assertIn("constraints", " ".join(audit.actions))

    def test_report_audit_passes_complete_fixture_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_fixture_reports(build_root)

            audit = fpga_gowin_build.audit_gowin_report_bundle(
                build_root,
                identity_audit=confirmed_identity(),
                constraints_audit=confirmed_constraints(),
            )

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")
        self.assertEqual(audit.missing_reports, ())
        self.assertEqual(audit.token_issues, ())
        self.assertEqual(audit.failure_markers, ())
        self.assertTrue(any(path.endswith(".fs") for path in audit.bitstreams))
        self.assertIn("I24-S04", " ".join(audit.actions))

    def test_report_audit_fails_negative_timing_and_missing_status_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp)
            write_fixture_reports(build_root, timing_text="Clock board_clk_i\nSlack -0.100\n")
            ports = build_root / "impl" / "pnr" / "first_ports.rpt"
            ports.write_text(
                "board_clk_i LOC P1\nboard_reset_n_i LOC P2\npass_led_o LOC P3\n",
                encoding="utf-8",
            )

            audit = fpga_gowin_build.audit_gowin_report_bundle(
                build_root,
                identity_audit=confirmed_identity(),
                constraints_audit=confirmed_constraints(),
            )

        self.assertEqual(audit.status, "failed")
        self.assertIn("timing_report contains Slack -", audit.failure_markers)
        self.assertIn("ports_report missing fail_led_o", audit.token_issues)
        self.assertIn("ports_report missing heartbeat_led_o", audit.token_issues)
        self.assertIn("ports_report missing uart_tx_o", audit.token_issues)

    def test_command_plan_and_cli_outputs(self) -> None:
        plan = fpga_gowin_build.fpga_gowin_command_plan()
        self.assertIn("python tools\\fpga_board_identity.py --audit-evidence", plan)
        self.assertIn("python tools\\fpga_constraints_overlay.py --audit-evidence", plan)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", plan)
        self.assertTrue(any("fpga_gowin_build.py --audit-reports" in command for command in plan))

        tool = load_tool_module()
        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Gowin build issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I24-S03")
        self.assertEqual(parsed["top_module"], "cpu_v01_fpga_top")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", stream.getvalue())

    def test_documentation_names_report_audit_scope_and_blockers(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-gowin-build.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I24-S03", text)
        self.assertIn("python tools\\fpga_gowin_build.py --check", text)
        self.assertIn("python tools\\fpga_board_identity.py --audit-evidence", text)
        self.assertIn("python tools\\fpga_constraints_overlay.py --audit-evidence", text)
        self.assertIn("python tools\\fpga_synthesis_gate.py --gowin-tcl", text)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", text)
        self.assertIn("python tools\\fpga_gowin_build.py --audit-reports", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("cpu_v01_fpga_top", text)
        self.assertIn("timing", text)
        self.assertIn("utilization", text)
        self.assertIn("ports", text)
        self.assertIn("bitstream", text)
        self.assertIn("black box", text)
        self.assertIn("unconstrained", text)
        self.assertIn("negative_timing_slack_at_first_test_clock", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("uart_tx_o", text)
        self.assertIn("I24-S04", text)
        self.assertIn("blocked", text)


if __name__ == "__main__":
    unittest.main()

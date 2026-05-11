"""I34-S02 conformance tests for Retro Console constraint overlays."""

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
TOOL = ROOT / "tools" / "fpga_retro_console_constraints.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_retro_console_constraints, fpga_retro_console_identity


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_retro_console_constraints_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def selected_identity_audit() -> fpga_retro_console_identity.RetroConsoleIdentityAudit:
    record = fpga_retro_console_identity.parse_identity_record(
        "\n".join(
            (
                "story=I34-S01",
                "board=Sipeed Tang Retro Console with 60K SOM",
                "source=programmer_jtag_scan",
                "observed_device=GW5AT-60B",
                "observed_idcode=0x0001481B",
                "observed_package=scan_recorded_package",
                "observed_device_version=B",
                "gowin_part=scan_recorded_gowin_part",
                "programming_path=Gowin Programmer SRAM",
                "clock_sources=verified Retro Console oscillator",
                "reset_sources=verified Retro Console reset input",
                "visible_outputs=heartbeat/pass/fail outputs",
                "uart_debug_access=verified UART status path",
                "selected_first_target=no",
                "primary_138k_target=Sipeed Tang Mega Dock with 138K SOM",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-11T12:00:00",
            )
        )
    )
    return fpga_retro_console_identity.audit_identity_record(record)


class FpgaRetroConsoleConstraintsTests(unittest.TestCase):
    def test_retro_console_constraints_self_validation_passes(self) -> None:
        self.assertEqual(
            fpga_retro_console_constraints.validate_fpga_retro_console_constraints(ROOT),
            (),
        )

    def test_overlay_names_paths_identity_gate_and_required_signals(self) -> None:
        overlay = fpga_retro_console_constraints.retro_console_constraints_overlay()

        self.assertEqual(overlay.story, "I34-S02")
        self.assertEqual(overlay.board, "Sipeed Tang Retro Console with 60K SOM")
        self.assertEqual(
            overlay.identity_gate,
            "python tools\\fpga_retro_console_identity.py --check",
        )
        self.assertEqual(
            overlay.cst_path.as_posix(),
            "constraints/tang_60k_retro_console_first_test.cst",
        )
        self.assertEqual(
            overlay.cst_template_path.as_posix(),
            "constraints/tang_60k_retro_console_first_test.cst.template",
        )
        self.assertEqual(
            overlay.sdc_path.as_posix(),
            "constraints/tang_60k_retro_console_first_test.sdc",
        )
        self.assertEqual(
            overlay.sdc_template_path.as_posix(),
            "constraints/tang_60k_retro_console_first_test.sdc.template",
        )
        self.assertEqual(overlay.clock_period_placeholder, "I34_S02_BOARD_CLK_PERIOD_NS")

        signals = {signal.name: signal for signal in overlay.signals}
        for name in (
            "board_clk_i",
            "board_reset_n_i",
            "pass_led_o",
            "fail_led_o",
            "heartbeat_led_o",
            "uart_tx_o",
        ):
            with self.subTest(name=name):
                self.assertIn(name, signals)
                self.assertTrue(signals[name].required)
                self.assertTrue(signals[name].io_standard.endswith("_or_recorded"))

    def test_cst_and_sdc_templates_keep_retro_console_placeholders(self) -> None:
        cst = fpga_retro_console_constraints.cst_template()
        sdc = fpga_retro_console_constraints.sdc_template()

        for token in (
            'IO_LOC "board_clk_i" I34_S02_PIN_BOARD_CLK_I;',
            'IO_PORT "board_clk_i" IO_TYPE=LVCMOS33_or_recorded;',
            "I34_S02_PIN_BOARD_RESET_N_I",
            "I34_S02_PIN_PASS_LED_O",
            "I34_S02_PIN_FAIL_LED_O",
            "I34_S02_PIN_HEARTBEAT_LED_O",
            "I34_S02_PIN_UART_TX_O",
        ):
            self.assertIn(token, cst)

        self.assertIn("create_clock -name board_clk_i", sdc)
        self.assertIn("I34_S02_BOARD_CLK_PERIOD_NS", sdc)
        self.assertIn("set_false_path -from [get_ports {board_reset_n_i}]", sdc)

        cst_file = (
            ROOT / "constraints" / "tang_60k_retro_console_first_test.cst.template"
        ).read_text(encoding="utf-8")
        sdc_file = (
            ROOT / "constraints" / "tang_60k_retro_console_first_test.sdc.template"
        ).read_text(encoding="utf-8")
        self.assertIn("I34_S02_PIN_BOARD_CLK_I", cst_file)
        self.assertIn("I34_S02_BOARD_CLK_PERIOD_NS", sdc_file)

    def test_evidence_template_and_audit_confirm_complete_pin_record(self) -> None:
        template = fpga_retro_console_constraints.constraint_evidence_template()

        for token in (
            "story=I34-S02",
            "identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt",
            "source_constraints=",
            "io_voltage=",
            "pin_conflicts=",
            "board_clk_i_pin=",
            "board_reset_n_i_pin=",
            "pass_led_o_pin=",
            "fail_led_o_pin=",
            "heartbeat_led_o_pin=",
            "uart_tx_o_pin=",
            "board_clk_i_clock_period_ns=",
        ):
            self.assertIn(token, template)

        record = fpga_retro_console_constraints.parse_constraint_evidence(
            "\n".join(
                (
                    "story=I34-S02",
                    "identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt",
                    "source_constraints=verified Retro Console schematic",
                    "verified_by=test",
                    "verified_at=2026-05-11T12:00:00",
                    "io_voltage=LVCMOS33",
                    "led_polarity=active_high_or_recorded",
                    "uart_debug_mode=UART status TX",
                    "pin_conflicts=none",
                    "board_clk_i_pin=P1",
                    "board_reset_n_i_pin=P2",
                    "pass_led_o_pin=P3",
                    "fail_led_o_pin=P4",
                    "heartbeat_led_o_pin=P5",
                    "uart_tx_o_pin=P6",
                    "board_clk_i_clock_period_ns=40.000",
                )
            )
        )
        audit = fpga_retro_console_constraints.audit_constraint_evidence(
            record,
            identity_audit=selected_identity_audit(),
        )

        self.assertTrue(audit.confirmed)
        self.assertEqual(audit.status, "confirmed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.missing_pins, ())
        self.assertIn("I34-S03", " ".join(audit.actions))

    def test_audit_blocks_without_identity_and_rejects_missing_pins(self) -> None:
        blocked = fpga_retro_console_constraints.load_constraint_overlay_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i34_s02.txt"),
            Path("docs/implementation/evidence/definitely_missing_i34_s01.txt"),
        )
        self.assertEqual(blocked.status, "blocked")
        self.assertIn("board_clk_i_pin", blocked.missing_pins)

        incomplete = fpga_retro_console_constraints.parse_constraint_evidence(
            "\n".join(
                (
                    "story=I34-S02",
                    "identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt",
                    "source_constraints=verified Retro Console schematic",
                    "verified_by=test",
                    "verified_at=2026-05-11T12:00:00",
                    "io_voltage=LVCMOS33",
                    "led_polarity=active_high",
                    "uart_debug_mode=UART status TX",
                    "pin_conflicts=none",
                    "board_clk_i_pin=P1",
                    "board_clk_i_clock_period_ns=40.000",
                )
            )
        )
        invalid = fpga_retro_console_constraints.audit_constraint_evidence(
            incomplete,
            identity_audit=selected_identity_audit(),
        )
        self.assertEqual(invalid.status, "invalid")
        self.assertIn("board_reset_n_i_pin", invalid.missing_pins)
        self.assertIn("pass_led_o_pin", invalid.missing_pins)

    def test_cli_validates_renders_templates_json_and_blocked_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA Retro Console constraints issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I34-S02")
        self.assertEqual(parsed["clock_period_placeholder"], "I34_S02_BOARD_CLK_PERIOD_NS")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("I34_S02_PIN_BOARD_CLK_I", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--sdc-template"])

        self.assertEqual(result, 0)
        self.assertIn("I34_S02_BOARD_CLK_PERIOD_NS", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i34_s02.txt",
                    "--identity-evidence",
                    "docs/implementation/evidence/definitely_missing_i34_s01.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_constraints_identity_gate_and_blockers(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-retro-console-constraints.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I34-S02",
            "python tools\\fpga_retro_console_constraints.py --check",
            "python tools\\fpga_retro_console_identity.py --check",
            "constraints/tang_60k_retro_console_first_test.cst",
            "constraints/tang_60k_retro_console_first_test.cst.template",
            "constraints/tang_60k_retro_console_first_test.sdc",
            "constraints/tang_60k_retro_console_first_test.sdc.template",
            "docs/implementation/evidence/i34_s02_retro_console_pins.txt",
            "Sipeed Tang Retro Console with 60K SOM",
            "board_clk_i",
            "board_reset_n_i",
            "pass_led_o",
            "fail_led_o",
            "heartbeat_led_o",
            "uart_tx_o",
            "I34_S02_PIN_BOARD_CLK_I",
            "I34_S02_BOARD_CLK_PERIOD_NS",
            "io_voltage",
            "pin_conflicts",
            "not Tang Mega Dock with 138K SOM",
            "I34-S03",
            "blocked",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

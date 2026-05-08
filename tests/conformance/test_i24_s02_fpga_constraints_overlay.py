"""I24-S02 conformance tests for the Tang Mega 138K constraint overlay."""

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
TOOL = ROOT / "tools" / "fpga_constraints_overlay.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_board_identity, fpga_constraints


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_constraints_overlay_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def confirmed_identity_audit() -> fpga_board_identity.BoardIdentityAudit:
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
            )
        )
    )
    return fpga_board_identity.audit_identity_record(record)


class FpgaConstraintsOverlayTests(unittest.TestCase):
    def test_constraints_overlay_self_validation_passes(self) -> None:
        self.assertEqual(fpga_constraints.validate_fpga_constraints_overlay(ROOT), ())

    def test_overlay_names_target_files_identity_gate_and_required_signals(self) -> None:
        overlay = fpga_constraints.fpga_constraints_overlay()

        self.assertEqual(overlay.story, "I24-S02")
        self.assertEqual(overlay.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(overlay.device, "GW5AST-LV138PG484A")
        self.assertEqual(overlay.package, "PBG484A")
        self.assertEqual(overlay.clock_period_ns, 40.000)
        self.assertEqual(overlay.cst_path.as_posix(), "constraints/tang_mega_138k_first_test.cst")
        self.assertEqual(
            overlay.cst_template_path.as_posix(),
            "constraints/tang_mega_138k_first_test.cst.template",
        )
        self.assertEqual(overlay.sdc_path.as_posix(), "constraints/tang_mega_138k_first_test.sdc")
        self.assertEqual(overlay.identity_gate, "python tools\\fpga_board_identity.py --check")

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
                self.assertEqual(signals[name].io_standard, "LVCMOS33")

    def test_cst_template_and_sdc_name_required_constraints(self) -> None:
        cst = fpga_constraints.cst_template()
        sdc = fpga_constraints.sdc_template()

        for token in (
            'IO_LOC "board_clk_i" I24_S02_PIN_BOARD_CLK_I;',
            'IO_PORT "board_clk_i" IO_TYPE=LVCMOS33;',
            "I24_S02_PIN_BOARD_RESET_N_I",
            "I24_S02_PIN_PASS_LED_O",
            "I24_S02_PIN_FAIL_LED_O",
            "I24_S02_PIN_HEARTBEAT_LED_O",
            "I24_S02_PIN_UART_TX_O",
        ):
            with self.subTest(token=token):
                self.assertIn(token, cst)

        self.assertIn("create_clock -name board_clk_i -period 40.000", sdc)
        self.assertIn("set_false_path -from [get_ports {board_reset_n_i}]", sdc)

        cst_file = (ROOT / "constraints" / "tang_mega_138k_first_test.cst.template").read_text(
            encoding="utf-8"
        )
        sdc_file = (ROOT / "constraints" / "tang_mega_138k_first_test.sdc").read_text(
            encoding="utf-8"
        )
        self.assertIn("I24_S02_PIN_BOARD_CLK_I", cst_file)
        self.assertIn("-period 40.000", sdc_file)

    def test_evidence_template_and_audit_confirm_complete_pin_record(self) -> None:
        template = fpga_constraints.constraint_evidence_template()
        for token in (
            "story=I24-S02",
            "identity_evidence=docs/implementation/evidence/i24_s01_device_identity.txt",
            "source_constraints=",
            "board_clk_i_pin=",
            "board_reset_n_i_pin=",
            "pass_led_o_pin=",
            "fail_led_o_pin=",
            "heartbeat_led_o_pin=",
            "uart_tx_o_pin=",
            "board_clk_i_clock_period_ns=40.000",
        ):
            self.assertIn(token, template)

        record = fpga_constraints.parse_constraint_evidence(
            "\n".join(
                (
                    "story=I24-S02",
                    "identity_evidence=docs/implementation/evidence/i24_s01_device_identity.txt",
                    "source_constraints=Sipeed All PIN Constraints verified package",
                    "verified_by=test",
                    "verified_at=2026-05-08T12:00:00",
                    "led_polarity=active_high",
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
        audit = fpga_constraints.audit_constraint_evidence(
            record,
            identity_audit=confirmed_identity_audit(),
        )

        self.assertTrue(audit.confirmed)
        self.assertEqual(audit.status, "confirmed")
        self.assertEqual(audit.missing_fields, ())
        self.assertEqual(audit.missing_pins, ())
        self.assertIn("I24-S03", " ".join(audit.actions))

    def test_audit_blocks_without_identity_and_rejects_missing_pins(self) -> None:
        blocked = fpga_constraints.load_constraint_overlay_audit(
            ROOT,
            Path("docs/implementation/evidence/definitely_missing_i24_s02.txt"),
            Path("docs/implementation/evidence/definitely_missing_i24_s01.txt"),
        )
        self.assertEqual(blocked.status, "blocked")
        self.assertIn("board_clk_i_pin", blocked.missing_pins)

        incomplete = fpga_constraints.parse_constraint_evidence(
            "\n".join(
                (
                    "story=I24-S02",
                    "identity_evidence=docs/implementation/evidence/i24_s01_device_identity.txt",
                    "source_constraints=Sipeed All PIN Constraints verified package",
                    "verified_by=test",
                    "verified_at=2026-05-08T12:00:00",
                    "led_polarity=active_high",
                    "board_clk_i_pin=P1",
                    "board_clk_i_clock_period_ns=40.000",
                )
            )
        )
        invalid = fpga_constraints.audit_constraint_evidence(
            incomplete,
            identity_audit=confirmed_identity_audit(),
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
        self.assertIn("FPGA constraints overlay issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I24-S02")
        self.assertEqual(parsed["clock_period_ns"], 40.0)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("I24_S02_PIN_BOARD_CLK_I", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--sdc"])

        self.assertEqual(result, 0)
        self.assertIn("-period 40.000", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-evidence",
                    "docs/implementation/evidence/definitely_missing_i24_s02.txt",
                    "--identity-evidence",
                    "docs/implementation/evidence/definitely_missing_i24_s01.txt",
                ]
            )

        self.assertEqual(result, 1)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "blocked")

    def test_documentation_names_constraints_identity_gate_and_blockers(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-constraints-overlay.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I24-S02", text)
        self.assertIn("python tools\\fpga_constraints_overlay.py --check", text)
        self.assertIn("constraints/tang_mega_138k_first_test.cst", text)
        self.assertIn("constraints/tang_mega_138k_first_test.cst.template", text)
        self.assertIn("constraints/tang_mega_138k_first_test.sdc", text)
        self.assertIn("docs/implementation/evidence/i24_s02_constraint_pins.txt", text)
        self.assertIn("python tools\\fpga_board_identity.py --check", text)
        self.assertIn("GW5AST-LV138PG484A", text)
        self.assertIn("PBG484A", text)
        self.assertIn("Sipeed All PIN Constraints", text)
        self.assertIn("board_clk_i", text)
        self.assertIn("board_reset_n_i", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("uart_tx_o", text)
        self.assertIn("LVCMOS33", text)
        self.assertIn("40.000", text)
        self.assertIn("I24_S02_PIN_BOARD_CLK_I", text)
        self.assertIn("blocked", text)
        self.assertIn("I24-S03", text)


if __name__ == "__main__":
    unittest.main()

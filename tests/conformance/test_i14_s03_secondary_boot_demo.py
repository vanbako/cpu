"""I14-S03 conformance tests for firmware-controlled secondary-core startup."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import csrs, firmware, startup, state


class SecondaryCoreBootDemoTests(unittest.TestCase):
    def test_firmware_demo_starts_secondary_core_from_trusted_mailbox(self) -> None:
        report = firmware.run_secondary_core_boot_demo()
        target = report.cores[report.started_coreid]

        self.assertEqual(report.initial_lifecycle, state.CoreLifecycle.STOPPED)
        self.assertTrue(report.start_result.accepted)
        self.assertEqual(report.start_result.failure_code, startup.StartupFailureCode.NONE)
        self.assertEqual(report.start_result.mailbox_state, startup.MailboxState.CONSUMED)
        self.assertEqual(report.start_result.lifecycle, state.CoreLifecycle.STARTED)
        self.assertEqual(report.controller.consumed_generations[report.started_coreid], 1)
        self.assertEqual(target.lifecycle, state.CoreLifecycle.STARTED)
        self.assertEqual(target.pcc, report.started_entry)
        self.assertEqual(target.read_d(0), report.started_arg0)
        self.assertTrue(target.read_c(0).is_valid)
        self.assertTrue(target.special_capabilities.read("DSC").is_valid)
        self.assertTrue(target.special_capabilities.read("RSC").is_valid)
        self.assertTrue(target.special_capabilities.read("KSC").is_valid)
        self.assertTrue(target.special_capabilities.read("KRC").is_valid)
        self.assertTrue(target.special_capabilities.read("TVC").is_valid)
        self.assertEqual(target.read_csr(csrs.CSR_SATP), 0)
        self.assertEqual(target.read_csr(csrs.CSR_IENABLE), 0)

    def test_repeated_start_signal_does_not_replace_live_secondary_state(self) -> None:
        report = firmware.run_secondary_core_boot_demo()
        target = report.cores[report.started_coreid]

        self.assertFalse(report.repeated_start_result.accepted)
        self.assertEqual(
            report.repeated_start_result.failure_code,
            startup.StartupFailureCode.ALREADY_STARTED,
        )
        self.assertEqual(target.lifecycle, state.CoreLifecycle.STARTED)
        self.assertEqual(target.pcc, report.started_entry)
        self.assertEqual(target.read_d(0), report.started_arg0)

    def test_invalid_secondary_mailbox_is_rejected_without_partial_state(self) -> None:
        report = firmware.run_secondary_core_boot_demo()
        invalid = report.cores[report.invalid_coreid]

        self.assertFalse(report.invalid_start_result.accepted)
        self.assertEqual(
            report.invalid_start_result.failure_code,
            startup.StartupFailureCode.INVALID_PCC,
        )
        self.assertEqual(invalid.lifecycle, state.CoreLifecycle.START_FAILED)
        self.assertTrue(invalid.pcc.is_invalid)
        self.assertEqual(invalid.read_d(0), 0)
        self.assertEqual(report.controller.mailbox(report.invalid_coreid).state, startup.MailboxState.FAILED)

    def test_boot_core_remains_running_after_secondary_start_demo(self) -> None:
        report = firmware.run_secondary_core_boot_demo()
        boot = report.cores[0]

        self.assertEqual(boot.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(boot.pcc.payload.cursor, firmware.KERNEL_HANDOFF_CELL)
        self.assertTrue(boot.special_capabilities.read("KRC").is_valid)

    def test_documentation_artifact_names_secondary_startup_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "secondary-core-boot-demo.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I14-S03", text)
        self.assertIn("publishes a mailbox", text)
        self.assertIn("STARTED", text)
        self.assertIn("repeated", text)


if __name__ == "__main__":
    unittest.main()

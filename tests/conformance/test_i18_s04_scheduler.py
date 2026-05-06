"""I18-S04 conformance tests for minimal scheduler and context switching."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import abi, csrs, instructions, kernel, scheduler, state, user_process


class MinimalSchedulerFixtureTests(unittest.TestCase):
    def test_timer_preemption_switches_two_tasks_and_resumes_task1_with_iret(self) -> None:
        report = scheduler.run_scheduler_fixture()

        self.assertTrue(report.timer_entry.entered)
        self.assertEqual(report.timer_entry.source, kernel.InterruptSource.TIMER)
        self.assertEqual(report.switch_from_task, scheduler.TASK0_ID)
        self.assertEqual(report.switch_to_task, scheduler.TASK1_ID)
        self.assertTrue(report.iret_result.is_normal_retire)
        self.assertTrue(report.final_user_mode)
        self.assertFalse(report.final_sr & (1 << csrs.SR_EXL_BIT))
        self.assertEqual(report.final_pcc, report.restored_task1.pcc)
        self.assertEqual(report.final_pcc.payload.cursor, user_process.USER_ENTRY_CELL)
        self.assertEqual(report.final_pcc.slot, state.SLOT_0)
        self.assertEqual(report.final_satp, report.restored_task1.satp)
        self.assertEqual(report.final_asid, scheduler.TASK1_ASID)

    def test_saved_context_preserves_abi_registers_capability_tags_and_trap(self) -> None:
        report = scheduler.run_scheduler_fixture()
        saved = report.saved_task0

        self.assertEqual(len(saved.integer_registers), state.INTEGER_REGISTER_COUNT)
        self.assertEqual(
            saved.integer_registers[15],
            scheduler.TASK_REGISTER_BASE + (scheduler.TASK0_ID << 8) + 15,
        )
        self.assertEqual(
            len(saved.capability_registers),
            state.GENERAL_CAPABILITY_REGISTER_COUNT,
        )
        self.assertEqual(
            saved.capability_tags,
            (True, False, True, False, True, False, True, False),
        )
        expected_satp = csrs.pack_satp(
            csrs.SATP_MODE_RADIX4,
            scheduler.TASK0_ASID,
            scheduler.vm.VM_ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT,
        )
        self.assertEqual(saved.satp, expected_satp)
        self.assertEqual(saved.asid, scheduler.TASK0_ASID)
        self.assertEqual(saved.trap_frame.cause, kernel.InterruptSource.TIMER.cause_value)
        self.assertEqual(saved.trap_frame.epcc, saved.pcc)
        self.assertEqual(saved.trap_frame.capcause, instructions.CapCause.NONE)
        self.assertEqual(saved.trap_frame.fault_cap_idx, instructions.FaultCapIndex.NONE)
        self.assertTrue(saved.dsc.is_valid)
        self.assertTrue(saved.rsc.is_valid)
        self.assertTrue(saved.tvc.is_valid)

    def test_restore_installs_full_task1_abi_and_capability_state(self) -> None:
        report = scheduler.run_scheduler_fixture()
        restored = report.restored_task1

        self.assertEqual(report.final_integer_registers, restored.integer_registers)
        self.assertEqual(report.final_capability_tags, restored.capability_tags)
        self.assertEqual(
            report.final_integer_registers[0],
            scheduler.TASK_REGISTER_BASE + (scheduler.TASK1_ID << 8),
        )
        self.assertEqual(
            report.final_integer_registers[abi.CONTEXT_SWITCH_INTEGER_REGS[-1]],
            scheduler.TASK_REGISTER_BASE + (scheduler.TASK1_ID << 8) + 15,
        )
        self.assertEqual(restored.trap_frame.epcc, report.final_pcc)

    def test_scheduler_clears_llsc_reservations_on_preemption_and_switch(self) -> None:
        report = scheduler.run_scheduler_fixture()

        self.assertTrue(report.reservation_valid_before_timer)
        self.assertFalse(report.reservation_valid_after_timer)
        self.assertTrue(report.reservation_valid_before_switch)
        self.assertFalse(report.reservation_valid_after_switch)

    def test_documentation_artifact_names_timer_context_and_reservation_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "minimal-scheduler.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I18-S04", text)
        self.assertIn("Timer preemption", text)
        self.assertIn("SATP", text)
        self.assertIn("LL/SC reservations", text)


if __name__ == "__main__":
    unittest.main()

"""I14-S02 conformance tests for minimal trap, syscall, and timer handlers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, firmware, kernel, platform, state
from cpu_v01.instructions import CapCause, ExceptionCause, FaultCapIndex
from cpu_v01.memory import TaggedMemory


def executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x4000, 0x5000),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def data_capability(cursor: int = platform.RAM_BASE) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(platform.RAM_BASE, platform.RAM_BASE + 0x100),
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def prepared_core(*, user_ie: bool = False) -> state.CoreState:
    memory = TaggedMemory()
    core = platform.cold_reset_cores()[0]
    firmware.initialize_boot_core_for_kernel_handoff(core, memory)
    core.install_pcc(
        state.SlottedCapability.from_capability(
            executable_capability(0x4000),
            state.SLOT_0,
        )
    )
    sr = core.read_csr(csrs.CSR_SR)
    sr &= ~(1 << csrs.SR_PRIV_BIT)
    sr &= ~(1 << csrs.SR_EXL_BIT)
    if user_ie:
        sr |= 1 << csrs.SR_IE_BIT
    else:
        sr &= ~(1 << csrs.SR_IE_BIT)
    core.write_csr_raw(csrs.CSR_SR, sr)
    return core


class MinimalKernelHandlerFixtureTests(unittest.TestCase):
    def test_syscall_handler_saves_frame_reads_arguments_and_returns_with_iret(self) -> None:
        core = prepared_core(user_ie=True)
        core.write_d(0, 7)
        for offset, register in enumerate((1, 2, 3, 4, 5), start=1):
            core.write_d(register, offset)
        core.write_c(0, data_capability())

        report = kernel.run_syscall_handler_fixture(core)

        self.assertTrue(report.trap_entry.entered)
        self.assertEqual(report.saved_frame.cause, int(ExceptionCause.SYSCALL_TRAP))
        self.assertEqual(report.saved_frame.tval, 0)
        self.assertEqual(report.saved_frame.capcause, CapCause.NONE)
        self.assertEqual(report.saved_frame.fault_cap_idx, FaultCapIndex.NONE)
        self.assertEqual(report.saved_frame.epcc.payload.cursor, 0x4000)
        self.assertEqual(report.saved_frame.epcc.slot, state.SLOT_0)
        self.assertEqual(report.service_number, 7)
        self.assertEqual(report.integer_arguments, (1, 2, 3, 4, 5))
        self.assertEqual(report.capability_argument_tags, (True, False, False, False))
        self.assertEqual(report.return_d0, 7)
        self.assertEqual(report.return_d1, 15)
        self.assertTrue(report.iret_result.is_normal_retire)
        self.assertEqual(report.final_pcc.payload.cursor, 0x4000)
        self.assertEqual(report.final_pcc.slot, state.SLOT_1)
        self.assertFalse(report.final_sr & (1 << csrs.SR_PRIV_BIT))
        self.assertFalse(report.final_sr & (1 << csrs.SR_EXL_BIT))
        self.assertTrue(report.final_sr & (1 << csrs.SR_IE_BIT))

    def test_timer_interrupt_dispatches_to_vector_and_iret_restores_user_context(self) -> None:
        core = prepared_core(user_ie=True)
        original_pcc = core.pcc
        core.write_csr_raw(csrs.CSR_TIMER, 25)
        core.write_csr_raw(csrs.CSR_TIMECMP, 25)
        core.write_csr_raw(csrs.CSR_IENABLE, 1 << kernel.InterruptSource.TIMER.bit)

        report = kernel.run_timer_handler_fixture(core, next_timecmp=100)

        self.assertTrue(report.interrupt_entry.entered)
        self.assertEqual(report.interrupt_entry.source, kernel.InterruptSource.TIMER)
        self.assertEqual(report.interrupt_entry.cause_value, kernel.InterruptSource.TIMER.cause_value)
        self.assertEqual(report.interrupt_entry.vector_pcc.payload.cursor, firmware.ROM_TRAP_VECTOR_CELL + 4)
        self.assertEqual(report.saved_frame.cause, kernel.InterruptSource.TIMER.cause_value)
        self.assertEqual(report.saved_frame.tval, 0)
        self.assertEqual(report.saved_frame.capcause, CapCause.NONE)
        self.assertEqual(report.saved_frame.fault_cap_idx, FaultCapIndex.NONE)
        self.assertEqual(report.saved_frame.epcc, original_pcc)
        self.assertEqual(report.old_timecmp, 25)
        self.assertEqual(report.new_timecmp, 100)
        self.assertEqual(kernel.effective_pending_mask(core), 0)
        self.assertTrue(report.iret_result.is_normal_retire)
        self.assertEqual(report.final_pcc, original_pcc)
        self.assertFalse(report.final_sr & (1 << csrs.SR_PRIV_BIT))
        self.assertFalse(report.final_sr & (1 << csrs.SR_EXL_BIT))
        self.assertTrue(report.final_sr & (1 << csrs.SR_IE_BIT))

    def test_interrupt_delivery_masks_and_priority_follow_core_rules(self) -> None:
        core = prepared_core(user_ie=True)
        core.write_csr_raw(csrs.CSR_TIMER, 9)
        core.write_csr_raw(csrs.CSR_TIMECMP, 9)
        core.write_csr_raw(
            csrs.CSR_IENABLE,
            (1 << kernel.InterruptSource.TIMER.bit)
            | (1 << kernel.InterruptSource.SOFTWARE_IPI.bit),
        )
        core.write_csr_raw(csrs.CSR_IPENDING, 1 << kernel.InterruptSource.SOFTWARE_IPI.bit)

        self.assertEqual(
            kernel.selected_interrupt_source(core),
            kernel.InterruptSource.SOFTWARE_IPI,
        )

        core.write_csr_raw(csrs.CSR_SR, core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_IE_BIT))
        self.assertIsNone(kernel.selected_interrupt_source(core))
        self.assertFalse(kernel.enter_pending_interrupt(core).entered)

    def test_trap_frame_restore_preserves_slot_for_iret(self) -> None:
        core = prepared_core(user_ie=False)
        frame = kernel.SoftwareTrapFrame(
            epcc=state.SlottedCapability.from_capability(executable_capability(0x4004), state.SLOT_1),
            sr=(1 << csrs.SR_PRIV_BIT) | (1 << csrs.SR_EXL_BIT),
            cause=int(ExceptionCause.SYSCALL_TRAP),
            tval=0x1234,
            capcause=CapCause.NONE,
            fault_cap_idx=FaultCapIndex.NONE,
        )

        kernel.restore_frame_for_iret(core, frame)
        result = kernel.execute_iret(core)

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.pcc.payload.cursor, 0x4004)
        self.assertEqual(core.pcc.slot, state.SLOT_1)
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x1234)

    def test_documentation_artifact_names_syscall_timer_and_iret_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "minimal-kernel-handlers.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I14-S02", text)
        self.assertIn("syscall arguments", text)
        self.assertIn("timer interrupt", text)
        self.assertIn("IRET", text)


if __name__ == "__main__":
    unittest.main()

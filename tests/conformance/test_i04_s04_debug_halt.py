"""I04-S04 conformance tests for non-monitor debug halt and single-step."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import control_ops, csrs, debug_ops, instructions, program, reset, state


def executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def location(core: state.CoreState) -> instructions.InstructionLocation:
    return instructions.InstructionLocation(core.pcc)


def normal_instruction(
    core: state.CoreState,
    size: instructions.InstructionSize = instructions.InstructionSize.BITS_12,
) -> instructions.DecodedInstruction:
    return instructions.DecodedInstruction("NOP", size, location=location(core))


class DebugHaltAndSingleStepTests(unittest.TestCase):
    def test_brk_default_path_reports_ordinary_breakpoint_fault(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        decoded = debug_ops.debug_instruction("BRK", location=location(core))

        result = debug_ops.execute_debug(core, decoded)

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.BREAKPOINT)
        self.assertEqual(result.fault_packet.tval, 0x1000)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(core.read_csr(csrs.CSR_DEBUGCTL), 0)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

    def test_brkhalt_enters_debug_halted_without_consuming_epcc_or_advancing_pcc(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.install_pcc(core.pcc.with_slot(state.SLOT_1))
        original_pcc = core.pcc
        original_epcc = core.epcc
        original_sr = core.read_csr(csrs.CSR_SR)
        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_BRKHALT_BIT)
        decoded = debug_ops.debug_instruction("BRK", location=location(core))

        result = debug_ops.execute_debug(core, decoded)
        halt = debug_ops.enter_debug_halt_from_result(core, result)

        self.assertTrue(halt.is_debug_event)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.DEBUG_HALTED)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.epcc, original_epcc)
        self.assertEqual(core.read_csr(csrs.CSR_SR), original_sr)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.DEBUG_HALT))
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x1000)
        self.assertEqual(core.read_csr(csrs.CSR_CAPCAUSE), int(instructions.CapCause.NONE))
        self.assertEqual(core.read_csr(csrs.CSR_FAULTCAPIDX), int(instructions.FaultCapIndex.NONE))
        self.assertTrue(core.read_csr(csrs.CSR_DEBUGCTL) & (1 << csrs.DEBUGCTL_HALTED_BIT))
        self.assertFalse(core.read_csr(csrs.CSR_DEBUGCTL) & (1 << csrs.DEBUGCTL_HALTREQ_BIT))
        self.assertEqual(debug_ops.dcause(core), instructions.DebugCause.BRK)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

    def test_haltreq_and_resume_preserve_current_execution_point(self) -> None:
        core = reset.cold_reset_core(0, 0x2000)
        original_pcc = core.pcc

        debug_ops.request_halt(core)
        halt = debug_ops.accept_halt_request(core)

        self.assertIsNotNone(halt)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.DEBUG_HALTED)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(debug_ops.dcause(core), instructions.DebugCause.HALTREQ)
        self.assertTrue(core.read_csr(csrs.CSR_DEBUGCTL) & (1 << csrs.DEBUGCTL_HALTED_BIT))
        self.assertFalse(core.read_csr(csrs.CSR_DEBUGCTL) & (1 << csrs.DEBUGCTL_HALTREQ_BIT))

        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_RESUME_BIT)

        self.assertEqual(core.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(core.pcc, original_pcc)
        self.assertFalse(core.read_csr(csrs.CSR_DEBUGCTL) & (1 << csrs.DEBUGCTL_HALTED_BIT))

    def test_debugctl_reserved_bits_fault_and_leave_state_unchanged(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_BRKHALT_BIT)
        original_debugctl = core.read_csr(csrs.CSR_DEBUGCTL)

        with self.assertRaises(ValueError):
            debug_ops.write_debugctl(core, 1 << 7)
        with self.assertRaises(ValueError):
            debug_ops.write_debugctl(core, 1 << 12)

        self.assertEqual(core.read_csr(csrs.CSR_DEBUGCTL), original_debugctl)

    def test_single_step_retires_one_instruction_then_reenters_debug_halt(self) -> None:
        core = reset.cold_reset_core(0, 0x3000)
        debug_ops.enter_debug_halt(
            core,
            instructions.DebugEventPacket(instructions.DebugCause.HALTREQ, location(core)),
        )
        debug_ops.write_debugctl(
            core,
            (1 << csrs.DEBUGCTL_STEP_BIT) | (1 << csrs.DEBUGCTL_RESUME_BIT),
        )
        self.assertTrue(core.step_active)

        result = program.with_sequential_fallthrough(
            normal_instruction(core).normal_retire()
        )
        step_event = debug_ops.commit_normal_result_with_debug(core, result)

        self.assertIsNotNone(step_event)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.DEBUG_HALTED)
        self.assertFalse(core.step_active)
        self.assertEqual(debug_ops.dcause(core), instructions.DebugCause.SINGLE_STEP)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.DEBUG_HALT))
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x3000)
        self.assertEqual(core.pcc.payload.cursor, 0x3000)
        self.assertEqual(core.pcc.slot, state.SLOT_1)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_clearing_step_before_resume_allows_normal_retire_without_debug_event(self) -> None:
        core = reset.cold_reset_core(0, 0x3000)
        debug_ops.enter_debug_halt(
            core,
            instructions.DebugEventPacket(instructions.DebugCause.HALTREQ, location(core)),
        )
        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_RESUME_BIT)

        result = program.with_sequential_fallthrough(
            normal_instruction(core).normal_retire()
        )
        step_event = debug_ops.commit_normal_result_with_debug(core, result)

        self.assertIsNone(step_event)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertFalse(core.step_active)
        self.assertEqual(core.pcc.slot, state.SLOT_1)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_successful_iret_arms_step_for_restored_context_without_stepping_iret(self) -> None:
        core = reset.cold_reset_core(0, 0x4000)
        epcc = state.SlottedCapability.from_capability(
            executable_capability(0x5000),
            state.SLOT_1,
        )
        core.install_epcc(epcc)
        core.write_csr_raw(
            csrs.CSR_SR,
            (1 << csrs.SR_PRIV_BIT)
            | (1 << csrs.SR_EXL_BIT)
            | (1 << csrs.SR_PIE_BIT),
        )
        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_STEP_BIT)
        decoded = control_ops.control_instruction(
            "IRET",
            location=location(core),
        )
        result = control_ops.execute_control(core, decoded)

        step_event = debug_ops.commit_normal_result_with_debug(core, result)

        self.assertIsNone(step_event)
        self.assertEqual(core.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(core.pcc, epcc)
        self.assertTrue(core.step_active)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_debug_halted_core_suppresses_cycle_and_instruction_retirement(self) -> None:
        core = reset.cold_reset_core(0, 0x6000)
        debug_ops.enter_debug_halt(
            core,
            instructions.DebugEventPacket(instructions.DebugCause.HALTREQ, location(core)),
        )
        core.write_csr_raw(csrs.CSR_CYCLE, 10)
        result = program.with_sequential_fallthrough(
            normal_instruction(core).normal_retire()
        )

        debug_ops.tick_cycle(core, 5)
        with self.assertRaises(RuntimeError):
            debug_ops.commit_normal_result_with_debug(core, result)

        self.assertEqual(core.read_csr(csrs.CSR_CYCLE), 10)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

        debug_ops.write_debugctl(core, 1 << csrs.DEBUGCTL_RESUME_BIT)
        debug_ops.tick_cycle(core, 5)

        self.assertEqual(core.read_csr(csrs.CSR_CYCLE), 15)


if __name__ == "__main__":
    unittest.main()

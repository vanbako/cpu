"""I04-S01 conformance tests for decoded-program fetch and slot sequencing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, instructions, program, reset, state


def decoded(mnemonic: str, size: instructions.InstructionSize) -> instructions.DecodedInstruction:
    return instructions.DecodedInstruction(mnemonic, size)


def retire_noop(
    core: state.CoreState,
    instruction: instructions.DecodedInstruction,
) -> instructions.ExecutionResult:
    del core
    return instruction.normal_retire()


def executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


class DecodedProgramFetchSlotTests(unittest.TestCase):
    def test_two_packed_12_bit_instructions_fall_through_slot_then_next_cell(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        decoded_program = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, decoded("NOP0", instructions.InstructionSize.BITS_12)),
                (0x1000, state.SLOT_1, decoded("NOP1", instructions.InstructionSize.BITS_12)),
            )
        )

        first = decoded_program.step(core, retire_noop)

        self.assertTrue(first.is_normal_retire)
        self.assertEqual(first.instruction.location.address, 0x1000)
        self.assertEqual(first.instruction.location.slot, state.SLOT_0)
        self.assertEqual(core.pcc.payload.cursor, 0x1000)
        self.assertEqual(core.pcc.slot, state.SLOT_1)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), csrs.SLOT_1)

        second = decoded_program.step(core, retire_noop)

        self.assertTrue(second.is_normal_retire)
        self.assertEqual(second.instruction.location.address, 0x1000)
        self.assertEqual(second.instruction.location.slot, state.SLOT_1)
        self.assertEqual(core.pcc.payload.cursor, 0x1001)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), csrs.SLOT_0)

    def test_24_and_48_bit_instructions_advance_by_cell_size_from_slot0(self) -> None:
        core = reset.cold_reset_core(0, 0x1001)
        decoded_program = program.DecodedProgram.from_layout(
            (
                (0x1001, state.SLOT_0, decoded("ONE_CELL", instructions.InstructionSize.BITS_24)),
                (0x1002, state.SLOT_0, decoded("TWO_CELL", instructions.InstructionSize.BITS_48)),
            )
        )

        first = decoded_program.step(core, retire_noop)

        self.assertTrue(first.is_normal_retire)
        self.assertEqual(core.pcc.payload.cursor, 0x1002)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

        second = decoded_program.step(core, retire_noop)

        self.assertTrue(second.is_normal_retire)
        self.assertEqual(core.pcc.payload.cursor, 0x1004)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_illegal_instruction_placement_faults_before_executor_runs(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.install_pcc(core.pcc.with_slot(state.SLOT_1))
        decoded_program = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_1, decoded("BAD24", instructions.InstructionSize.BITS_24)),
            )
        )
        calls: list[str] = []

        def executor(
            core: state.CoreState,
            instruction: instructions.DecodedInstruction,
        ) -> instructions.ExecutionResult:
            del core
            calls.append(instruction.mnemonic)
            return instruction.normal_retire()

        result = decoded_program.step(core, executor)

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(result.fault_packet.tval, 0x1000)
        self.assertEqual(calls, [])
        self.assertEqual(core.pcc.payload.cursor, 0x1000)
        self.assertEqual(core.pcc.slot, state.SLOT_1)

        core.install_pcc(
            state.SlottedCapability.from_capability(executable_capability(0x1001), state.SLOT_0)
        )
        decoded_program = program.DecodedProgram.from_layout(
            (
                (0x1001, state.SLOT_0, decoded("BAD48", instructions.InstructionSize.BITS_48)),
            )
        )

        result = decoded_program.step(core, executor)

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(result.fault_packet.tval, 0x1001)
        self.assertEqual(calls, [])
        self.assertEqual(core.pcc.payload.cursor, 0x1001)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_missing_decoded_entry_reports_illegal_without_retiring(self) -> None:
        core = reset.cold_reset_core(0, 0x2000)
        decoded_program = program.DecodedProgram.from_layout(())

        result = decoded_program.step(core, retire_noop)

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)
        self.assertEqual(result.fault_packet.tval, 0x2000)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)
        self.assertEqual(core.pcc.payload.cursor, 0x2000)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_explicit_control_transfers_normalize_to_slot0_and_reject_slot1(self) -> None:
        branch = instructions.DecodedInstruction(
            "BRA",
            instructions.InstructionSize.BITS_24,
            location=instructions.InstructionLocation(
                state.SlottedCapability.from_capability(executable_capability(0x3000))
            ),
        )
        target_capability = executable_capability(0x4000)
        redirect = program.redirect_to_explicit_target(
            branch,
            instructions.RedirectKind.BRANCH,
            target_capability,
        )

        self.assertTrue(redirect.is_redirect)
        self.assertEqual(redirect.redirect_packet.target.payload.cursor, 0x4000)
        self.assertEqual(redirect.redirect_packet.target.slot, state.SLOT_0)

        slot1_target = state.SlottedCapability.from_capability(
            executable_capability(0x5000),
            state.SLOT_1,
        )
        fault = program.redirect_to_explicit_target(
            branch,
            instructions.RedirectKind.BRANCH,
            slot1_target,
        )

        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(fault.fault_packet.tval, 0x5000)
        with self.assertRaises(ValueError):
            program.explicit_slot0_target(slot1_target)


if __name__ == "__main__":
    unittest.main()

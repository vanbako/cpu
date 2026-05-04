"""I03-S01 conformance tests for decoded instructions and result packets."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import instructions as instr
from cpu_v01 import state


def location(address: int, slot: int = state.SLOT_0) -> instr.InstructionLocation:
    payload = caps.CapabilityPayload(
        cursor=address,
        permissions=caps.CapabilityPermission.EX,
        flags=caps.CapabilityFlag.G,
    )
    pcc = state.SlottedCapability.from_capability(
        caps.Capability.valid(payload),
        slot,
    )
    return instr.InstructionLocation(pcc)


class DecodedInstructionProtocolTests(unittest.TestCase):
    def test_instruction_size_placement_rules_match_e04_s01(self) -> None:
        self.assertTrue(instr.InstructionSize.BITS_12.is_legal_start(0x1000, 0))
        self.assertTrue(instr.InstructionSize.BITS_12.is_legal_start(0x1000, 1))
        self.assertTrue(instr.InstructionSize.BITS_12.is_legal_start(0x1001, 1))

        self.assertTrue(instr.InstructionSize.BITS_24.is_legal_start(0x1000, 0))
        self.assertTrue(instr.InstructionSize.BITS_24.is_legal_start(0x1001, 0))
        self.assertFalse(instr.InstructionSize.BITS_24.is_legal_start(0x1000, 1))

        self.assertTrue(instr.InstructionSize.BITS_48.is_legal_start(0x1000, 0))
        self.assertFalse(instr.InstructionSize.BITS_48.is_legal_start(0x1000, 1))
        self.assertFalse(instr.InstructionSize.BITS_48.is_legal_start(0x1001, 0))

        self.assertEqual(instr.InstructionSize.BITS_12.cells, 1)
        self.assertEqual(instr.InstructionSize.BITS_24.cells, 1)
        self.assertEqual(instr.InstructionSize.BITS_48.cells, 2)

    def test_pipeline_stage_names_match_e13_s01(self) -> None:
        self.assertEqual(
            tuple(stage.value for stage in instr.PipelineStage),
            ("FE0", "FE1", "PD", "XLT", "ISS", "EX", "MEM", "WB", "RT"),
        )

    def test_decoded_instruction_normalizes_identity_and_keeps_location(self) -> None:
        decoded = instr.DecodedInstruction(
            "add",
            instr.InstructionSize.BITS_24,
            operands=("D0", "D1", "D2"),
            location=location(0x1000),
            attributes={"width": 48},
        )

        self.assertEqual(decoded.mnemonic, "ADD")
        self.assertEqual(decoded.length_cells, 1)
        self.assertEqual(decoded.location.address, 0x1000)
        self.assertEqual(decoded.location.slot, state.SLOT_0)
        self.assertEqual(decoded.operands, ("D0", "D1", "D2"))
        self.assertEqual(decoded.attributes["width"], 48)
        with self.assertRaises(TypeError):
            decoded.attributes["width"] = 24  # type: ignore[index]

        with self.assertRaises(ValueError):
            instr.DecodedInstruction("", instr.InstructionSize.BITS_12)

    def test_placement_fault_reports_align_fault_with_cell_tval(self) -> None:
        decoded_24 = instr.DecodedInstruction(
            "LD48",
            instr.InstructionSize.BITS_24,
            location=location(0x1000, state.SLOT_1),
        )
        packet_24 = decoded_24.placement_fault()

        self.assertIsNotNone(packet_24)
        assert packet_24 is not None
        self.assertEqual(packet_24.cause, instr.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(packet_24.tval, 0x1000)
        self.assertEqual(packet_24.faulting_location.slot, state.SLOT_1)
        self.assertEqual(packet_24.capcause, instr.CapCause.NONE)
        self.assertEqual(packet_24.fault_cap_idx, instr.FaultCapIndex.NONE)

        decoded_48 = instr.DecodedInstruction(
            "FARCALL",
            instr.InstructionSize.BITS_48,
            location=location(0x1001, state.SLOT_0),
        )
        packet_48 = decoded_48.placement_fault()
        self.assertIsNotNone(packet_48)
        assert packet_48 is not None
        self.assertEqual(packet_48.cause, instr.ExceptionCause.ALIGN_FAULT)
        self.assertEqual(packet_48.tval, 0x1001)

        legal = instr.DecodedInstruction(
            "NOP",
            instr.InstructionSize.BITS_12,
            location=location(0x1001, state.SLOT_1),
        )
        self.assertIsNone(legal.placement_fault())

    def test_normal_retire_result_carries_atomic_effects(self) -> None:
        decoded = instr.DecodedInstruction("MOV", instr.InstructionSize.BITS_12)
        effects = instr.ArchitecturalEffects(integer_writes=((0, 0x1234),))
        result = decoded.normal_retire(effects)

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(result.kind, instr.ExecutionResultKind.NORMAL_RETIRE)
        self.assertEqual(result.normal.effects.integer_writes, ((0, 0x1234),))
        self.assertFalse(result.normal.effects.is_empty)
        self.assertIsNone(result.fault_packet)

    def test_fault_result_captures_precise_exception_packet(self) -> None:
        decoded = instr.DecodedInstruction(
            "DIV",
            instr.InstructionSize.BITS_24,
            location=location(0x2000),
        )
        packet = instr.FaultPacket(
            cause=instr.ExceptionCause.DIVIDE_BY_ZERO,
            faulting_location=decoded.location,
            tval=0,
        )
        result = decoded.fault(packet)

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instr.ExceptionCause.DIVIDE_BY_ZERO)
        self.assertEqual(result.fault_packet.faulting_location.address, 0x2000)
        self.assertIsNone(result.normal)

    def test_capability_fault_packet_reports_capcause_and_operand(self) -> None:
        decoded = instr.DecodedInstruction(
            "CLC",
            instr.InstructionSize.BITS_48,
            location=location(0x3000),
        )
        packet = instr.FaultPacket(
            cause=instr.ExceptionCause.CAPABILITY_TAG_FAULT,
            faulting_location=decoded.location,
            tval=0x4000,
            capcause=instr.CapCause.TAG,
            fault_cap_idx=instr.FaultCapIndex.C2,
        )

        self.assertEqual(packet.cause, instr.ExceptionCause.CAPABILITY_TAG_FAULT)
        self.assertEqual(packet.capcause, instr.CapCause.TAG)
        self.assertEqual(packet.fault_cap_idx, instr.FaultCapIndex.C2)
        self.assertEqual(packet.tval, 0x4000)

    def test_debug_event_result_reports_debug_halt_and_dcause(self) -> None:
        decoded = instr.DecodedInstruction(
            "BRK",
            instr.InstructionSize.BITS_12,
            location=location(0x5000),
        )
        packet = instr.DebugEventPacket(
            dcause=instr.DebugCause.BRK,
            location=decoded.location,
            tval=0x5000,
        )
        result = decoded.debug_event(packet)

        self.assertTrue(result.is_debug_event)
        self.assertEqual(result.debug_packet.cause, instr.ExceptionCause.DEBUG_HALT)
        self.assertEqual(result.debug_packet.dcause, instr.DebugCause.BRK)
        self.assertEqual(result.debug_packet.capcause, instr.CapCause.NONE)
        self.assertEqual(result.debug_packet.fault_cap_idx, instr.FaultCapIndex.NONE)

    def test_redirect_result_carries_target_and_flush_contract(self) -> None:
        decoded = instr.DecodedInstruction("BRA", instr.InstructionSize.BITS_24)
        target = location(0x6000).pcc
        packet = instr.RedirectPacket(instr.RedirectKind.BRANCH, target)
        result = decoded.redirect(packet)

        self.assertTrue(result.is_redirect)
        self.assertEqual(result.redirect_packet.kind, instr.RedirectKind.BRANCH)
        self.assertEqual(result.redirect_packet.target.payload.cursor, 0x6000)
        self.assertTrue(result.redirect_packet.flush_younger)

    def test_execution_result_requires_one_matching_packet(self) -> None:
        decoded = instr.DecodedInstruction("NOP", instr.InstructionSize.BITS_12)
        normal = instr.NormalRetirePacket()
        packet = instr.FaultPacket(
            instr.ExceptionCause.ILLEGAL_INSTRUCTION,
            location(0x7000),
        )

        with self.assertRaises(ValueError):
            instr.ExecutionResult(
                instruction=decoded,
                kind=instr.ExecutionResultKind.NORMAL_RETIRE,
            )
        with self.assertRaises(ValueError):
            instr.ExecutionResult(
                instruction=decoded,
                kind=instr.ExecutionResultKind.NORMAL_RETIRE,
                normal=normal,
                fault_packet=packet,
            )
        with self.assertRaises(TypeError):
            instr.ExecutionResult(
                instruction=decoded,
                kind=instr.ExecutionResultKind.NORMAL_RETIRE,
                fault_packet=packet,
            )

    def test_in_flight_instruction_tracks_sequence_stage_and_pending_result(self) -> None:
        decoded = instr.DecodedInstruction("NOP", instr.InstructionSize.BITS_12)
        trace = instr.InFlightInstruction(7, decoded)
        retired = decoded.normal_retire()

        self.assertEqual(trace.sequence, 7)
        self.assertEqual(trace.stage, instr.PipelineStage.XLT)
        self.assertEqual(trace.advance_to(instr.PipelineStage.RT).stage, instr.PipelineStage.RT)
        self.assertEqual(trace.with_result(retired).pending_result, retired)

        other = instr.DecodedInstruction("PAUSE", instr.InstructionSize.BITS_12)
        with self.assertRaises(ValueError):
            trace.with_result(other.normal_retire())


if __name__ == "__main__":
    unittest.main()

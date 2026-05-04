"""I04-S02 conformance tests for direct synchronous trap entry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, instructions, reset, state, traps


def capability(
    cursor: int,
    *,
    base: int = 0,
    top: int = 1 << 48,
    permissions: int = int(caps.CapabilityPermission.EX),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability(payload=payload, tag=tag)


def fault_packet(
    core: state.CoreState,
    cause: instructions.ExceptionCause,
    *,
    tval: int = 0,
    capcause: instructions.CapCause = instructions.CapCause.NONE,
    fault_cap_idx: instructions.FaultCapIndex = instructions.FaultCapIndex.NONE,
) -> instructions.FaultPacket:
    return instructions.FaultPacket(
        cause,
        instructions.InstructionLocation(core.pcc),
        tval=tval,
        capcause=capcause,
        fault_cap_idx=fault_cap_idx,
    )


class DirectTrapEntryTests(unittest.TestCase):
    def test_trap_entry_saves_slot1_epcc_reporting_state_and_sr_fields(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        tvc = capability(0x8000)
        faulting_pcc = state.SlottedCapability.from_capability(
            capability(0x1234),
            state.SLOT_1,
        )
        original_c0 = capability(0x4000)
        core.write_d(0, 0x123456)
        core.write_c(0, original_c0)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], tvc)
        core.install_pcc(faulting_pcc)
        old_sr = (
            (1 << csrs.SR_Z_BIT)
            | (1 << csrs.SR_C_BIT)
            | (1 << csrs.SR_IE_BIT)
        )
        core.write_csr_raw(csrs.CSR_SR, old_sr)

        result = traps.enter_trap(
            core,
            fault_packet(core, instructions.ExceptionCause.ALIGN_FAULT, tval=0x1234),
        )

        self.assertTrue(result.entered)
        self.assertEqual(core.epcc.payload, faulting_pcc.payload)
        self.assertEqual(core.epcc.tag, faulting_pcc.tag)
        self.assertEqual(core.epcc.slot, state.SLOT_1)
        self.assertEqual(core.pcc.payload, tvc.payload)
        self.assertEqual(core.pcc.tag, tvc.tag)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.ALIGN_FAULT))
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x1234)
        self.assertEqual(core.read_csr(csrs.CSR_CAPCAUSE), int(instructions.CapCause.NONE))
        self.assertEqual(core.read_csr(csrs.CSR_FAULTCAPIDX), int(instructions.FaultCapIndex.NONE))

        sr = core.read_csr(csrs.CSR_SR)
        self.assertTrue(sr & (1 << csrs.SR_Z_BIT))
        self.assertTrue(sr & (1 << csrs.SR_C_BIT))
        self.assertFalse(sr & (1 << csrs.SR_IE_BIT))
        self.assertTrue(sr & (1 << csrs.SR_PIE_BIT))
        self.assertTrue(sr & (1 << csrs.SR_PRIV_BIT))
        self.assertFalse(sr & (1 << csrs.SR_PPRIV_BIT))
        self.assertTrue(sr & (1 << csrs.SR_EXL_BIT))
        self.assertEqual(csrs.sr_slot(sr), state.SLOT_0)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)
        self.assertEqual(core.read_d(0), 0x123456)
        self.assertEqual(core.read_c(0), original_c0)

    def test_capability_fault_reporting_is_written_for_capability_causes(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], capability(0x8000))
        packet = fault_packet(
            core,
            instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
            tval=0x2000,
            capcause=instructions.CapCause.BOUNDS,
            fault_cap_idx=instructions.FaultCapIndex.PCC,
        )

        result = traps.enter_trap(core, packet)

        self.assertTrue(result.entered)
        self.assertEqual(
            core.read_csr(csrs.CSR_CAUSE),
            int(instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT),
        )
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x2000)
        self.assertEqual(core.read_csr(csrs.CSR_CAPCAUSE), int(instructions.CapCause.BOUNDS))
        self.assertEqual(core.read_csr(csrs.CSR_FAULTCAPIDX), int(instructions.FaultCapIndex.PCC))

    def test_non_capability_trap_entry_clears_capability_reporting(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], capability(0x8000))
        misleading_packet = fault_packet(
            core,
            instructions.ExceptionCause.DIVIDE_BY_ZERO,
            capcause=instructions.CapCause.TAG,
            fault_cap_idx=instructions.FaultCapIndex.C3,
        )

        result = traps.enter_trap(core, misleading_packet)

        self.assertTrue(result.entered)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.DIVIDE_BY_ZERO))
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0)
        self.assertEqual(core.read_csr(csrs.CSR_CAPCAUSE), int(instructions.CapCause.NONE))
        self.assertEqual(core.read_csr(csrs.CSR_FAULTCAPIDX), int(instructions.FaultCapIndex.NONE))

    def test_trap_entry_uses_same_tvc_target_for_different_causes(self) -> None:
        targets: list[int] = []
        for cause in (
            instructions.ExceptionCause.ILLEGAL_INSTRUCTION,
            instructions.ExceptionCause.SYSCALL_TRAP,
        ):
            core = reset.cold_reset_core(0, 0x1000)
            core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], capability(0x9000))

            result = traps.enter_trap(core, fault_packet(core, cause))

            self.assertTrue(result.entered)
            targets.append(core.pcc.payload.cursor)

        self.assertEqual(targets, [0x9000, 0x9000])

    def test_invalid_tvc_reports_fatal_delivery_failure_without_partial_state(self) -> None:
        cases = (
            (capability(0x8000, tag=False), instructions.CapCause.TAG),
            (capability(0x8000, otype=0x22), instructions.CapCause.SEAL_TYPE),
            (capability(0x8000, permissions=0), instructions.CapCause.PERMISSION),
            (capability(0x9000, base=0x8000, top=0x9000), instructions.CapCause.BOUNDS),
        )
        for tvc, expected_capcause in cases:
            with self.subTest(capcause=expected_capcause):
                core = reset.cold_reset_core(0, 0x1000)
                core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], tvc)
                original_pcc = core.pcc
                original_epcc = core.epcc
                original_sr = core.read_csr(csrs.CSR_SR)

                result = traps.enter_trap(
                    core,
                    fault_packet(core, instructions.ExceptionCause.ILLEGAL_INSTRUCTION),
                )

                self.assertTrue(result.fatal)
                self.assertEqual(result.failure.capcause, expected_capcause)
                self.assertEqual(result.failure.fault_cap_idx, instructions.FaultCapIndex.TVC)
                self.assertEqual(result.failure.tval, tvc.payload.cursor)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.epcc, original_epcc)
                self.assertEqual(core.read_csr(csrs.CSR_SR), original_sr)
                self.assertEqual(core.read_csr(csrs.CSR_CAUSE), 0)
                self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0)

    def test_enter_trap_from_result_accepts_only_fault_results(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], capability(0x8000))
        decoded = instructions.DecodedInstruction(
            "DIV",
            instructions.InstructionSize.BITS_24,
            location=instructions.InstructionLocation(core.pcc),
        )
        packet = fault_packet(core, instructions.ExceptionCause.DIVIDE_BY_ZERO)
        fault_result = decoded.fault(packet)

        self.assertTrue(traps.enter_trap_from_result(core, fault_result).entered)
        with self.assertRaises(ValueError):
            traps.enter_trap_from_result(core, decoded.normal_retire())


if __name__ == "__main__":
    unittest.main()

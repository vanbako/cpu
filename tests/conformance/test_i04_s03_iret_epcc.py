"""I04-S03 conformance tests for `IRET` and slot-aware `EPCC` helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import control_ops, csrs, execution, instructions, reset, state


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


def execute_and_commit(
    core: state.CoreState,
    decoded: instructions.DecodedInstruction,
) -> instructions.ExecutionResult:
    result = control_ops.execute_control(core, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


def set_user_mode(core: state.CoreState) -> None:
    core.write_csr_raw(
        csrs.CSR_SR,
        core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT),
    )


class IretAndEpccHelperTests(unittest.TestCase):
    def test_epccrd_copies_epcc_payload_tag_and_slot_to_registers(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        epcc_payload = capability(0x2222, tag=False)
        core.install_epcc(state.SlottedCapability.from_capability(epcc_payload, state.SLOT_1))

        result = execute_and_commit(
            core,
            control_ops.control_instruction("EPCCRD", (2, 3)),
        )

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.read_c(2), epcc_payload)
        self.assertEqual(core.read_d(3), state.SLOT_1)

    def test_epccwr_restores_epcc_tag_and_low_slot_bit_without_validating_target(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = capability(0x3333, tag=False, otype=0x44, permissions=0)
        original_pcc = core.pcc
        original_sr_slot = csrs.sr_slot(core.read_csr(csrs.CSR_SR))
        core.write_c(1, source)
        core.write_d(2, 0xFFFF_FFFF_FFFF)

        result = execute_and_commit(
            core,
            control_ops.control_instruction("EPCCWR", (1, 2)),
        )

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.epcc.without_slot(), source)
        self.assertEqual(core.epcc.slot, state.SLOT_1)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), original_sr_slot)

    def test_iret_restores_pcc_slot_interrupt_enable_and_privilege_atomically(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        epcc = state.SlottedCapability.from_capability(capability(0x4444), state.SLOT_1)
        core.install_epcc(epcc)
        core.write_csr_raw(csrs.CSR_CAUSE, int(instructions.ExceptionCause.SYSCALL_TRAP))
        core.write_csr_raw(csrs.CSR_TVAL, 0x1000)
        core.write_csr_raw(csrs.CSR_CAPCAUSE, int(instructions.CapCause.NONE))
        core.write_csr_raw(csrs.CSR_FAULTCAPIDX, int(instructions.FaultCapIndex.NONE))
        core.write_csr_raw(csrs.CSR_IENABLE, 0x7)
        core.write_csr_raw(csrs.CSR_IPENDING, 0x5)
        old_sr = (
            (1 << csrs.SR_N_BIT)
            | (1 << csrs.SR_V_BIT)
            | (1 << csrs.SR_PIE_BIT)
            | (1 << csrs.SR_PRIV_BIT)
            | (1 << csrs.SR_EXL_BIT)
        )
        core.write_csr_raw(csrs.CSR_SR, old_sr)

        result = execute_and_commit(core, control_ops.control_instruction("IRET"))

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.pcc, epcc)
        sr = core.read_csr(csrs.CSR_SR)
        self.assertTrue(sr & (1 << csrs.SR_N_BIT))
        self.assertTrue(sr & (1 << csrs.SR_V_BIT))
        self.assertTrue(sr & (1 << csrs.SR_IE_BIT))
        self.assertTrue(sr & (1 << csrs.SR_PIE_BIT))
        self.assertFalse(sr & (1 << csrs.SR_PRIV_BIT))
        self.assertFalse(sr & (1 << csrs.SR_PPRIV_BIT))
        self.assertFalse(sr & (1 << csrs.SR_EXL_BIT))
        self.assertEqual(csrs.sr_slot(sr), state.SLOT_1)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.SYSCALL_TRAP))
        self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x1000)
        self.assertEqual(core.read_csr(csrs.CSR_IENABLE), 0x7)
        self.assertEqual(core.read_csr(csrs.CSR_IPENDING), 0x5)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_user_mode_trap_return_helpers_raise_privilege_fault_without_effects(self) -> None:
        for decoded in (
            control_ops.control_instruction("IRET"),
            control_ops.control_instruction("EPCCRD", (0, 0)),
            control_ops.control_instruction("EPCCWR", (0, 0)),
        ):
            with self.subTest(mnemonic=decoded.mnemonic):
                core = reset.cold_reset_core(0, 0x1000)
                original_pcc = core.pcc
                original_epcc = core.epcc
                set_user_mode(core)

                result = control_ops.execute_control(core, decoded)

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.PRIVILEGE_FAULT)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.epcc, original_epcc)
                self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

    def test_faulting_iret_reports_epcc_capability_reason_and_commits_no_restore(self) -> None:
        cases = (
            (
                capability(0x5000, tag=False),
                instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
                instructions.CapCause.TAG,
                0,
            ),
            (
                capability(0x5000, otype=0x22),
                instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
                instructions.CapCause.SEAL_TYPE,
                0,
            ),
            (
                capability(0x5000, permissions=0),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
                instructions.CapCause.PERMISSION,
                0,
            ),
            (
                capability(0x6000, base=0x5000, top=0x6000),
                instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                instructions.CapCause.BOUNDS,
                0x6000,
            ),
        )
        for epcc_cap, expected_cause, expected_capcause, expected_tval in cases:
            with self.subTest(cause=expected_cause):
                core = reset.cold_reset_core(0, 0x1000)
                original_pcc = core.pcc
                original_sr = core.read_csr(csrs.CSR_SR)
                core.install_epcc(
                    state.SlottedCapability.from_capability(epcc_cap, state.SLOT_1)
                )

                result = control_ops.execute_control(
                    core,
                    control_ops.control_instruction("IRET"),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.EPCC)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.read_csr(csrs.CSR_SR), original_sr)
                self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)

    def test_unknown_or_malformed_trap_return_instruction_is_illegal(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)

        unknown = control_ops.execute_control(
            core,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_24),
        )
        malformed = control_ops.execute_control(
            core,
            control_ops.control_instruction("EPCCRD", (0,)),
        )

        self.assertTrue(unknown.is_fault)
        self.assertEqual(unknown.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)
        self.assertTrue(malformed.is_fault)
        self.assertEqual(malformed.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

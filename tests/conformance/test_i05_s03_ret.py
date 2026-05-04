"""I05-S03 conformance tests for `RET` and protected pop."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps, execution, instructions, reset, return_ops, state
from cpu_v01.memory import TaggedMemory


def capability(
    cursor: int,
    *,
    base: int = 0x1000,
    top: int = 0x2000,
    permissions: int = int(caps.CapabilityPermission.EX),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=flags,
    )
    return caps.Capability(payload, tag)


def return_capability(
    cursor: int = 0x1800,
    *,
    permissions: int = int(caps.CapabilityPermission.EX),
    tag: bool = True,
    otype: int = caps.OTYPE_RETURN,
    flags: int = 0,
    base: int = 0x1000,
    top: int = 0x2000,
) -> caps.Capability:
    return capability(
        cursor,
        base=base,
        top=top,
        permissions=permissions,
        tag=tag,
        otype=otype,
        flags=flags,
    )


def rsc_capability(
    cursor: int = 0x303C,
    *,
    base: int = 0x3000,
    top: int = 0x3100,
    permissions: int = int(caps.CapabilityPermission.LD | caps.CapabilityPermission.LC),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
) -> caps.Capability:
    return capability(
        cursor,
        base=base,
        top=top,
        permissions=permissions,
        tag=tag,
        otype=otype,
        flags=0,
    )


def location(core: state.CoreState) -> instructions.InstructionLocation:
    return instructions.InstructionLocation(core.pcc)


def install_rsc(core: state.CoreState, rsc: caps.Capability) -> None:
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], rsc)


def prepared_core() -> tuple[state.CoreState, TaggedMemory]:
    core = reset.cold_reset_core(0, 0x1000)
    memory = TaggedMemory()
    memory.protect_range(0x3000, 0x100)
    install_rsc(core, rsc_capability())
    return core, memory


def execute_and_commit(
    core: state.CoreState,
    memory: TaggedMemory,
    decoded: instructions.DecodedInstruction,
) -> instructions.ExecutionResult:
    result = return_ops.execute_return(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class ProtectedReturnPopTests(unittest.TestCase):
    def test_ret_pops_valid_return_capability_and_installs_unsealed_slot0_pcc(self) -> None:
        core, memory = prepared_core()
        sealed_return = return_capability(0x1800)
        memory.csc(0x303C, sealed_return)
        original_pcc = core.pcc
        original_rsc = core.special_capabilities.read("RSC")
        decoded = return_ops.return_instruction(location=location(core))

        result = return_ops.execute_return(core, memory, decoded)

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
        self.assertEqual(memory.clc(0x303C), sealed_return)

        execution.commit_normal_result(core, result, memory)

        self.assertEqual(core.special_capabilities.read("RSC").payload.cursor, 0x3040)
        self.assertEqual(core.pcc.payload.cursor, 0x1800)
        self.assertEqual(core.pcc.payload.otype, caps.OTYPE_UNSEALED)
        self.assertEqual(core.pcc.payload.permissions, sealed_return.payload.permissions)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(memory.clc(0x303C), sealed_return)

    def test_ret_requires_valid_unsealed_rsc_with_load_capability_permissions(self) -> None:
        cases = (
            (rsc_capability(tag=False), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.TAG, 0),
            (rsc_capability(otype=0x22), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.SEAL_TYPE, 0),
            (rsc_capability(permissions=int(caps.CapabilityPermission.LC)), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.PERMISSION, 0x303C),
            (rsc_capability(permissions=int(caps.CapabilityPermission.LD)), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.PERMISSION, 0x303C),
            (rsc_capability(cursor=0x303D), instructions.ExceptionCause.ALIGN_FAULT, instructions.CapCause.NONE, 0x303D),
        )
        for rsc, expected_cause, expected_capcause, expected_tval in cases:
            with self.subTest(cause=expected_cause, capcause=expected_capcause):
                core, memory = prepared_core()
                install_rsc(core, rsc)
                memory.csc(0x303C, return_capability())
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = return_ops.execute_return(
                    core,
                    memory,
                    return_ops.return_instruction(location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)

    def test_ret_underflows_when_slot_is_inactive_or_wrong_return_type(self) -> None:
        cases = (
            (return_capability(tag=False), instructions.CapCause.TAG),
            (return_capability(otype=caps.OTYPE_UNSEALED), instructions.CapCause.SEAL_TYPE),
            (return_capability(otype=0x22), instructions.CapCause.SEAL_TYPE),
            (return_capability(flags=int(caps.CapabilityFlag.G)), instructions.CapCause.SEAL_TYPE),
        )
        for stored, expected_capcause in cases:
            with self.subTest(capcause=expected_capcause):
                core, memory = prepared_core()
                memory.csc(0x303C, stored)
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = return_ops.execute_return(
                    core,
                    memory,
                    return_ops.return_instruction(location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.RETURN_STACK_UNDERFLOW)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)
                self.assertEqual(result.fault_packet.tval, 0x303C)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)

    def test_ret_rejects_return_target_without_execute_or_bounds(self) -> None:
        cases = (
            (
                return_capability(permissions=0),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
                instructions.CapCause.PERMISSION,
                0x303C,
            ),
            (
                return_capability(cursor=0x2000, base=0x1000, top=0x2000),
                instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                instructions.CapCause.BOUNDS,
                0x2000,
            ),
        )
        for stored, expected_cause, expected_capcause, expected_tval in cases:
            with self.subTest(cause=expected_cause):
                core, memory = prepared_core()
                memory.csc(0x303C, stored)
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = return_ops.execute_return(
                    core,
                    memory,
                    return_ops.return_instruction(location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)

    def test_ret_underflows_for_empty_anchor_or_unprotected_storage(self) -> None:
        core, memory = prepared_core()
        install_rsc(core, rsc_capability(cursor=0x30FC))
        memory.csc(0x30FC, return_capability())

        result = return_ops.execute_return(
            core,
            memory,
            return_ops.return_instruction(location=location(core)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.RETURN_STACK_UNDERFLOW)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.BOUNDS)
        self.assertEqual(result.fault_packet.tval, 0x30FC)

        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_rsc(core, rsc_capability())
        memory.csc(0x303C, return_capability())

        result = return_ops.execute_return(
            core,
            memory,
            return_ops.return_instruction(location=location(core)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.PERMISSION)
        self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)
        self.assertEqual(result.fault_packet.tval, 0x303C)

    def test_unknown_or_malformed_ret_reports_illegal_instruction(self) -> None:
        core, memory = prepared_core()

        result = return_ops.execute_return(
            core,
            memory,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_12),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = return_ops.execute_return(
            core,
            memory,
            instructions.DecodedInstruction(
                "RET",
                instructions.InstructionSize.BITS_12,
                operands=(0,),
            ),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

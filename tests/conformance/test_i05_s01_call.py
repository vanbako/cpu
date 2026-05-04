"""I05-S01 conformance tests for direct `CALL` and protected push."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import call_ops, capabilities as caps, execution, instructions, reset, state
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


def rsc_capability(
    cursor: int = 0x3040,
    *,
    base: int = 0x3000,
    top: int = 0x3100,
    permissions: int = int(
        caps.CapabilityPermission.ST
        | caps.CapabilityPermission.SC
        | caps.CapabilityPermission.SL
    ),
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


def install_pcc(
    core: state.CoreState,
    cursor: int = 0x1000,
    *,
    base: int = 0x1000,
    top: int = 0x2000,
    slot: int = state.SLOT_0,
    permissions: int = int(caps.CapabilityPermission.EX),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
) -> None:
    core.install_pcc(
        state.SlottedCapability.from_capability(
            capability(
                cursor,
                base=base,
                top=top,
                permissions=permissions,
                tag=tag,
                otype=otype,
            ),
            slot,
        )
    )


def install_rsc(core: state.CoreState, rsc: caps.Capability) -> None:
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], rsc)


def execute_and_commit(
    core: state.CoreState,
    memory: TaggedMemory,
    decoded: instructions.DecodedInstruction,
) -> instructions.ExecutionResult:
    result = call_ops.execute_call(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class DirectCallProtectedPushTests(unittest.TestCase):
    def test_call_pushes_sealed_local_return_capability_and_installs_target_at_retire(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.protect_range(0x3000, 0x100)
        install_pcc(core, 0x1000)
        install_rsc(core, rsc_capability(0x3040))
        original_pcc = core.pcc
        original_rsc = core.special_capabilities.read("RSC")
        decoded = call_ops.call_instruction(
            "CALL",
            (0x1800,),
            location=location(core),
        )

        result = call_ops.execute_call(core, memory, decoded)

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
        self.assertFalse(memory.capability_tag(0x303C))

        execution.commit_normal_result(core, result, memory)

        pushed = memory.clc(0x303C)
        self.assertTrue(pushed.tag)
        self.assertEqual(pushed.payload.cursor, 0x1001)
        self.assertEqual(pushed.payload.bounds_metadata, original_pcc.payload.bounds_metadata)
        self.assertEqual(pushed.payload.permissions, original_pcc.payload.permissions)
        self.assertEqual(pushed.payload.otype, caps.OTYPE_RETURN)
        self.assertTrue(pushed.is_local)
        self.assertEqual(core.special_capabilities.read("RSC").payload.cursor, 0x303C)
        self.assertEqual(core.pcc.payload.cursor, 0x1800)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_call_continuation_is_always_slot0_next_cell_or_fetch_group(self) -> None:
        cases = (
            (instructions.InstructionSize.BITS_12, state.SLOT_0, 0x1001),
            (instructions.InstructionSize.BITS_12, state.SLOT_1, 0x1001),
            (instructions.InstructionSize.BITS_24, state.SLOT_0, 0x1001),
            (instructions.InstructionSize.BITS_48, state.SLOT_0, 0x1002),
        )
        for size, slot, expected_continuation in cases:
            with self.subTest(size=size, slot=slot):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                memory.protect_range(0x3000, 0x100)
                install_pcc(core, 0x1000, slot=slot)
                install_rsc(core, rsc_capability(0x3040))
                decoded = call_ops.call_instruction(
                    "CALL",
                    (0x1800,),
                    size=size,
                    location=location(core),
                )

                execute_and_commit(core, memory, decoded)

                pushed = memory.clc(0x303C)
                self.assertEqual(pushed.payload.cursor, expected_continuation)
                self.assertEqual(core.pcc.payload.cursor, 0x1800)
                self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_call_faults_without_side_effects_for_continuation_or_target_bounds(self) -> None:
        cases = (
            (0x0, 0x0, 0x1, 0x1800, 0x1),
            (0x1000, 0x1000, 0x1800, 0x1800, 0x1800),
        )
        for base, cursor, top, target, expected_tval in cases:
            with self.subTest(top=top):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                memory.protect_range(0x3000, 0x100)
                install_pcc(core, cursor, base=base, top=top)
                install_rsc(core, rsc_capability(0x3040))
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = call_ops.execute_call(
                    core,
                    memory,
                    call_ops.call_instruction("CALL", (target,), location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.PCC)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
                self.assertFalse(memory.capability_tag(0x303C))

    def test_call_faults_for_invalid_current_pcc_before_return_stack_side_effects(self) -> None:
        cases = (
            (dict(tag=False), instructions.ExceptionCause.CAPABILITY_TAG_FAULT, instructions.CapCause.TAG),
            (dict(otype=0x22), instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT, instructions.CapCause.SEAL_TYPE),
            (dict(permissions=0), instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT, instructions.CapCause.PERMISSION),
        )
        for pcc_kwargs, expected_cause, expected_capcause in cases:
            with self.subTest(cause=expected_cause):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                memory.protect_range(0x3000, 0x100)
                install_pcc(core, 0x1000, **pcc_kwargs)
                install_rsc(core, rsc_capability(0x3040))

                result = call_ops.execute_call(
                    core,
                    memory,
                    call_ops.call_instruction("CALL", (0x1800,), location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.PCC)
                self.assertFalse(memory.capability_tag(0x303C))

    def test_call_protected_push_requires_rsc_authority_bounds_and_protected_storage(self) -> None:
        cases = (
            (rsc_capability(0x3040, tag=False), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.TAG, 0),
            (rsc_capability(0x3040, otype=0x22), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.SEAL_TYPE, 0),
            (rsc_capability(0x3000), instructions.ExceptionCause.RETURN_STACK_OVERFLOW, instructions.CapCause.BOUNDS, 0x2FFC),
            (rsc_capability(0x3041), instructions.ExceptionCause.ALIGN_FAULT, instructions.CapCause.NONE, 0x303D),
            (rsc_capability(0x3040, permissions=int(caps.CapabilityPermission.SC | caps.CapabilityPermission.SL)), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.PERMISSION, 0x303C),
            (rsc_capability(0x3040, permissions=int(caps.CapabilityPermission.ST | caps.CapabilityPermission.SC)), instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT, instructions.CapCause.LOCAL_STORE, 0x303C),
        )
        for rsc, expected_cause, expected_capcause, expected_tval in cases:
            with self.subTest(cause=expected_cause, capcause=expected_capcause):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                memory.protect_range(0x3000, 0x100)
                install_pcc(core, 0x1000)
                install_rsc(core, rsc)
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = call_ops.execute_call(
                    core,
                    memory,
                    call_ops.call_instruction("CALL", (0x1800,), location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                if expected_cause != instructions.ExceptionCause.ALIGN_FAULT:
                    self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
                self.assertFalse(memory.capability_tag(0x303C))

        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        install_pcc(core, 0x1000)
        install_rsc(core, rsc_capability(0x3040))
        unprotected = call_ops.execute_call(
            core,
            memory,
            call_ops.call_instruction("CALL", (0x1800,), location=location(core)),
        )
        self.assertEqual(unprotected.fault_packet.cause, instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT)
        self.assertEqual(unprotected.fault_packet.capcause, instructions.CapCause.PERMISSION)
        self.assertEqual(unprotected.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)

    def test_unknown_or_malformed_call_instruction_reports_illegal_instruction(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()

        result = call_ops.execute_call(
            core,
            memory,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_24),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = call_ops.execute_call(
            core,
            memory,
            call_ops.call_instruction("CALL", ()),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

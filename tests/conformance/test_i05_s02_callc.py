"""I05-S02 conformance tests for `CALLC` sealed entry calls."""

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


def entry_capability(
    cursor: int = 0x1800,
    *,
    base: int = 0x1000,
    top: int = 0x2000,
    permissions: int = int(caps.CapabilityPermission.EX),
    tag: bool = True,
    otype: int = caps.OTYPE_ENTRY,
) -> caps.Capability:
    return capability(
        cursor,
        base=base,
        top=top,
        permissions=permissions,
        tag=tag,
        otype=otype,
    )


def rsc_capability(
    cursor: int = 0x3040,
    *,
    permissions: int = int(
        caps.CapabilityPermission.ST
        | caps.CapabilityPermission.SC
        | caps.CapabilityPermission.SL
    ),
) -> caps.Capability:
    return capability(
        cursor,
        base=0x3000,
        top=0x3100,
        permissions=permissions,
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


def install_rsc(core: state.CoreState, rsc: caps.Capability | None = None) -> None:
    if rsc is None:
        rsc = rsc_capability()
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], rsc)


def prepared_core() -> tuple[state.CoreState, TaggedMemory]:
    core = reset.cold_reset_core(0, 0x1000)
    memory = TaggedMemory()
    memory.protect_range(0x3000, 0x100)
    install_pcc(core)
    install_rsc(core)
    return core, memory


def execute_and_commit(
    core: state.CoreState,
    memory: TaggedMemory,
    decoded: instructions.DecodedInstruction,
) -> instructions.ExecutionResult:
    result = call_ops.execute_call(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class SealedEntryCallTests(unittest.TestCase):
    def test_callc_unseals_entry_only_into_committed_pcc_and_preserves_source(self) -> None:
        core, memory = prepared_core()
        entry = entry_capability(0x1800, permissions=int(caps.CapabilityPermission.EX | caps.CapabilityPermission.LD))
        core.write_c(2, entry)
        original_pcc = core.pcc
        original_rsc = core.special_capabilities.read("RSC")
        decoded = call_ops.call_instruction("CALLC", (2,), location=location(core))

        result = call_ops.execute_call(core, memory, decoded)

        self.assertTrue(result.is_normal_retire)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
        self.assertEqual(core.read_c(2), entry)
        self.assertFalse(memory.capability_tag(0x303C))

        execution.commit_normal_result(core, result, memory)

        pushed = memory.clc(0x303C)
        self.assertTrue(pushed.tag)
        self.assertEqual(pushed.payload.cursor, 0x1001)
        self.assertEqual(pushed.payload.otype, caps.OTYPE_RETURN)
        self.assertTrue(pushed.is_local)
        self.assertEqual(core.special_capabilities.read("RSC").payload.cursor, 0x303C)
        self.assertEqual(core.pcc.payload.cursor, 0x1800)
        self.assertEqual(core.pcc.payload.otype, caps.OTYPE_UNSEALED)
        self.assertEqual(core.pcc.payload.permissions, entry.payload.permissions)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(core.read_c(2), entry)

    def test_callc_uses_slot0_call_continuation_from_slot1_instruction(self) -> None:
        core, memory = prepared_core()
        install_pcc(core, 0x1000, slot=state.SLOT_1)
        entry = entry_capability(0x1800)
        core.write_c(2, entry)

        execute_and_commit(
            core,
            memory,
            call_ops.call_instruction(
                "CALLC",
                (2,),
                size=instructions.InstructionSize.BITS_12,
                location=location(core),
            ),
        )

        self.assertEqual(memory.clc(0x303C).payload.cursor, 0x1001)
        self.assertEqual(core.pcc.payload.cursor, 0x1800)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_callc_rejects_invalid_entry_capability_in_defined_order(self) -> None:
        cases = (
            (
                entry_capability(tag=False),
                instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
                instructions.CapCause.TAG,
                0,
            ),
            (
                capability(0x1800, otype=caps.OTYPE_UNSEALED),
                instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
                instructions.CapCause.SEAL_TYPE,
                0,
            ),
            (
                entry_capability(otype=0x22),
                instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
                instructions.CapCause.SEAL_TYPE,
                0,
            ),
            (
                entry_capability(permissions=0),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
                instructions.CapCause.PERMISSION,
                0,
            ),
            (
                entry_capability(cursor=0x2000, base=0x1000, top=0x2000),
                instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                instructions.CapCause.BOUNDS,
                0x2000,
            ),
        )
        for entry, expected_cause, expected_capcause, expected_tval in cases:
            with self.subTest(cause=expected_cause, capcause=expected_capcause):
                core, memory = prepared_core()
                core.write_c(2, entry)
                original_pcc = core.pcc
                original_rsc = core.special_capabilities.read("RSC")

                result = call_ops.execute_call(
                    core,
                    memory,
                    call_ops.call_instruction("CALLC", (2,), location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(result.fault_packet.capcause, expected_capcause)
                self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.C2)
                self.assertEqual(result.fault_packet.tval, expected_tval)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
                self.assertEqual(core.read_c(2), entry)
                self.assertFalse(memory.capability_tag(0x303C))

    def test_callc_checks_current_pcc_before_entry_capability(self) -> None:
        core, memory = prepared_core()
        install_pcc(core, 0x1000, permissions=0)
        core.write_c(2, entry_capability(tag=False))

        result = call_ops.execute_call(
            core,
            memory,
            call_ops.call_instruction("CALLC", (2,), location=location(core)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.PERMISSION)
        self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.PCC)

    def test_callc_faulting_protected_push_preserves_entry_source_and_pcc(self) -> None:
        core, memory = prepared_core()
        entry = entry_capability(0x1800)
        core.write_c(2, entry)
        install_rsc(
            core,
            rsc_capability(
                permissions=int(caps.CapabilityPermission.ST | caps.CapabilityPermission.SC),
            ),
        )
        original_pcc = core.pcc
        original_rsc = core.special_capabilities.read("RSC")

        result = call_ops.execute_call(
            core,
            memory,
            call_ops.call_instruction("CALLC", (2,), location=location(core)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.LOCAL_STORE)
        self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.RSC)
        self.assertEqual(result.fault_packet.tval, 0x303C)
        self.assertEqual(core.pcc, original_pcc)
        self.assertEqual(core.special_capabilities.read("RSC"), original_rsc)
        self.assertEqual(core.read_c(2), entry)
        self.assertFalse(memory.capability_tag(0x303C))

    def test_unknown_or_malformed_callc_reports_illegal_instruction(self) -> None:
        core, memory = prepared_core()

        result = call_ops.execute_call(
            core,
            memory,
            call_ops.call_instruction("CALLC", ()),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()

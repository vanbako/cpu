"""I15-S03 property-style tests for precise fault side-effect boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import atomic_ops, call_ops, capabilities as caps, csrs
from cpu_v01 import execution, fence_ops, instructions, memory_ops, mmu
from cpu_v01 import reset, return_ops, state, traps
from cpu_v01.memory import TaggedMemory
from cpu_v01.tlb import TlbEntry, TlbKind, vpn_from_address


DATA_SLOT = 0x1000
VIRTUAL_ADDRESS = 0x4000
ROOT_TABLE = 0x8000
L1_TABLE = 0x8800
L2_TABLE = 0x9000
L3_TABLE = 0x9800
PHYSICAL_PAGE = 0xA000
RETURN_STACK_BASE = 0x3000
RETURN_STACK_TOP = 0x3100
RETURN_SLOT = 0x303C


def capability(
    cursor: int = DATA_SLOT,
    *,
    base: int = 0,
    top: int = 1 << 48,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=permissions,
        otype=otype,
        flags=flags,
    ).with_bounds(base, top)
    return caps.Capability(payload=payload, tag=tag)


def executable_capability(cursor: int = DATA_SLOT, **kwargs) -> caps.Capability:
    return capability(cursor, permissions=int(caps.CapabilityPermission.EX), **kwargs)


def rsc_capability(
    cursor: int = RETURN_SLOT + 4,
    *,
    permissions: int = int(
        caps.CapabilityPermission.ST
        | caps.CapabilityPermission.SC
        | caps.CapabilityPermission.SL
        | caps.CapabilityPermission.LD
        | caps.CapabilityPermission.LC
    ),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
) -> caps.Capability:
    return capability(
        cursor,
        base=RETURN_STACK_BASE,
        top=RETURN_STACK_TOP,
        permissions=permissions,
        tag=tag,
        otype=otype,
        flags=0,
    )


def sealed_return_capability(
    cursor: int = 0x1800,
    *,
    tag: bool = True,
    otype: int = caps.OTYPE_RETURN,
    flags: int = 0,
    permissions: int = int(caps.CapabilityPermission.EX),
) -> caps.Capability:
    return capability(
        cursor,
        base=0x1000,
        top=0x2000,
        permissions=permissions,
        tag=tag,
        otype=otype,
        flags=flags,
    )


def location(core: state.CoreState) -> instructions.InstructionLocation:
    return instructions.InstructionLocation(core.pcc)


def install_radix4_root(core: state.CoreState) -> None:
    core.write_csr_raw(
        csrs.CSR_SATP,
        csrs.pack_satp(
            csrs.SATP_MODE_RADIX4,
            0,
            ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT,
        ),
    )


def install_mapping(
    memory: TaggedMemory,
    *,
    read: bool = True,
    write: bool = True,
    accessed: bool = True,
    reserved_zero: bool = False,
) -> None:
    l0, l1, l2, l3 = mmu.vpn_indexes(VIRTUAL_ADDRESS)
    memory.st48(
        ROOT_TABLE + (l0 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L1_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        L1_TABLE + (l1 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L2_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        L2_TABLE + (l2 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(L3_TABLE >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        L3_TABLE + (l3 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(
            PHYSICAL_PAGE >> csrs.SATP_ROOT_PPN_SHIFT,
            read=read,
            write=write,
            accessed=accessed,
            reserved_zero=reserved_zero,
        ),
    )


def install_sample_tlbs(core: state.CoreState) -> None:
    for kind in (TlbKind.DATA, TlbKind.INSTRUCTION):
        core.tlbs.insert(
            TlbEntry(
                kind=kind,
                mode=csrs.SATP_MODE_RADIX4,
                vpn=vpn_from_address(VIRTUAL_ADDRESS),
                asid=0,
                ppn=PHYSICAL_PAGE >> csrs.SATP_ROOT_PPN_SHIFT,
                user=False,
                readable=True,
                writable=True,
                executable=True,
                memory_type=mmu.MEMORY_TYPE_NORMAL_COHERENT,
            )
        )


class PreciseFaultEffectsPropertyTests(unittest.TestCase):
    def test_memory_faults_suppress_register_memory_tag_and_tlb_effects(self) -> None:
        sentinel_cap = capability(cursor=0x2222, tag=True)
        replacement_cap = capability(cursor=0x3333, tag=True)
        fault_cases = (
            (
                "LD48",
                memory_ops.memory_instruction("LD48", (0, 1, 2)),
                lambda core, memory: core.write_c(1, capability(tag=False)),
                instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
            ),
            (
                "LD48 permission",
                memory_ops.memory_instruction("LD48", (0, 1, 2)),
                lambda core, memory: core.write_c(1, capability(permissions=0)),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            ),
            (
                "LD48 align",
                memory_ops.memory_instruction("LD48", (0, 1, 2)),
                lambda core, memory: (
                    core.write_c(1, capability(permissions=int(caps.CapabilityPermission.LD))),
                    core.write_d(2, 1),
                ),
                instructions.ExceptionCause.ALIGN_FAULT,
            ),
            (
                "LD48 page",
                memory_ops.memory_instruction("LD48", (0, 1, 2)),
                lambda core, memory: (
                    install_radix4_root(core),
                    core.write_c(
                        1,
                        capability(
                            VIRTUAL_ADDRESS,
                            permissions=int(caps.CapabilityPermission.LD),
                        ),
                    ),
                ),
                instructions.ExceptionCause.PAGE_FAULT,
            ),
            (
                "ST48 page",
                memory_ops.memory_instruction("ST48", (1, 2, 3)),
                lambda core, memory: (
                    install_radix4_root(core),
                    core.write_c(
                        1,
                        capability(
                            VIRTUAL_ADDRESS,
                            permissions=int(caps.CapabilityPermission.ST),
                        ),
                    ),
                    core.write_d(3, 0xAAAA),
                ),
                instructions.ExceptionCause.PAGE_FAULT,
            ),
            (
                "CLC page",
                memory_ops.memory_instruction("CLC", (0, 1, 2)),
                lambda core, memory: (
                    install_radix4_root(core),
                    core.write_c(
                        1,
                        capability(
                            VIRTUAL_ADDRESS,
                            permissions=int(
                                caps.CapabilityPermission.LD
                                | caps.CapabilityPermission.LC
                            ),
                        ),
                    ),
                ),
                instructions.ExceptionCause.PAGE_FAULT,
            ),
            (
                "CSC permission",
                memory_ops.memory_instruction("CSC", (1, 2, 4)),
                lambda core, memory: (
                    core.write_c(1, capability(permissions=int(caps.CapabilityPermission.ST))),
                    core.write_c(4, replacement_cap),
                ),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            ),
        )

        for name, decoded, setup, expected_cause in fault_cases:
            with self.subTest(name=name):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                memory.csc(DATA_SLOT, sentinel_cap)
                core.write_d(0, 0x5555)
                core.write_c(0, sentinel_cap)
                setup(core, memory)
                before = (
                    core.read_d(0),
                    core.read_c(0),
                    memory.clc(DATA_SLOT),
                    core.tlbs.entry_count(),
                )

                result = memory_ops.execute_memory(core, memory, decoded)

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(core.read_d(0), before[0])
                self.assertEqual(core.read_c(0), before[1])
                self.assertEqual(memory.clc(DATA_SLOT), before[2])
                self.assertEqual(core.tlbs.entry_count(), before[3])

    def test_page_faults_do_not_install_partial_tlb_entries(self) -> None:
        cases = (
            ("missing root", None),
            ("leaf read denied", {"read": False}),
            ("leaf not accessed", {"accessed": False}),
            ("leaf reserved bit", {"reserved_zero": True}),
        )
        for name, mapping_options in cases:
            with self.subTest(name=name):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                install_radix4_root(core)
                if mapping_options is not None:
                    install_mapping(memory, **mapping_options)
                core.write_c(
                    1,
                    capability(
                        VIRTUAL_ADDRESS,
                        permissions=int(caps.CapabilityPermission.LD),
                    ),
                )
                core.write_d(2, 0)

                result = memory_ops.execute_memory(
                    core,
                    memory,
                    memory_ops.memory_instruction("LD48", (0, 1, 2)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.PAGE_FAULT)
                self.assertEqual(core.tlbs.entry_count(), 0)
                self.assertEqual(core.read_d(0), 0)

    def test_sfence_faults_do_not_apply_tlb_or_reservation_effects(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        install_sample_tlbs(core)
        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT),
        )
        core.reservation.reserve_word(DATA_SLOT, mmu.MEMORY_TYPE_NORMAL_COHERENT)

        fault = fence_ops.execute_fence(core, fence_ops.fence_instruction("SFENCE.VM"))

        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.cause, instructions.ExceptionCause.PRIVILEGE_FAULT)
        self.assertEqual(core.tlbs.entry_count(), 2)
        self.assertTrue(core.reservation.valid)

        core.write_csr_raw(
            csrs.CSR_SR,
            core.read_csr(csrs.CSR_SR) | (1 << csrs.SR_PRIV_BIT),
        )
        install_sample_tlbs(core)
        core.reservation.reserve_word(DATA_SLOT, mmu.MEMORY_TYPE_NORMAL_COHERENT)
        retire = fence_ops.execute_fence(core, fence_ops.fence_instruction("SFENCE.VM"))

        self.assertTrue(retire.is_normal_retire)
        self.assertEqual(core.tlbs.entry_count(), 2)
        self.assertTrue(core.reservation.valid)

        execution.commit_normal_result(core, retire)

        self.assertEqual(core.tlbs.entry_count(), 0)
        self.assertFalse(core.reservation.valid)

    def test_atomic_faults_clear_reservation_without_partial_data_or_tag_effects(self) -> None:
        cases = (
            (
                "LL48 align",
                lambda: atomic_ops.atomic_instruction("LL48", (0, 1, 2)),
                lambda core: (
                    core.write_c(
                        1,
                        capability(permissions=int(caps.CapabilityPermission.LD)),
                    ),
                    core.write_d(2, 1),
                ),
                instructions.ExceptionCause.ALIGN_FAULT,
            ),
            (
                "SC48 permission",
                lambda: atomic_ops.atomic_instruction("SC48", (4, 3, 1, 2)),
                lambda core: (
                    core.write_c(
                        1,
                        capability(permissions=int(caps.CapabilityPermission.LD)),
                    ),
                    core.write_d(2, 0),
                    core.write_d(3, 0x9999),
                ),
                instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
            ),
        )
        for name, decoded_factory, setup, expected_cause in cases:
            with self.subTest(name=name):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                original = capability(cursor=0x4444, tag=True)
                memory.csc(DATA_SLOT, original)
                core.write_d(0, 0x1111)
                core.write_d(4, 0x2222)
                core.reservation.reserve_word(DATA_SLOT, mmu.MEMORY_TYPE_NORMAL_COHERENT)
                setup(core)

                result = atomic_ops.execute_atomic(core, memory, decoded_factory())

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.cause, expected_cause)
                self.assertEqual(core.read_d(0), 0x1111)
                self.assertEqual(core.read_d(4), 0x2222)
                self.assertEqual(memory.clc(DATA_SLOT), original)
                self.assertFalse(core.reservation.valid)

    def test_trap_delivery_failure_preserves_fault_state_except_reservation_clear(self) -> None:
        invalid_tvcs = (
            capability(0x8000, tag=False, permissions=int(caps.CapabilityPermission.EX)),
            capability(0x8000, otype=0x22, permissions=int(caps.CapabilityPermission.EX)),
            capability(0x8000, permissions=0),
            capability(
                0x9000,
                base=0x8000,
                top=0x9000,
                permissions=int(caps.CapabilityPermission.EX),
            ),
        )
        for tvc in invalid_tvcs:
            with self.subTest(tvc=tvc):
                core = reset.cold_reset_core(0, 0x1000)
                core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], tvc)
                core.write_csr_raw(csrs.CSR_CAUSE, 0x123)
                core.write_csr_raw(csrs.CSR_TVAL, 0x456)
                core.reservation.reserve_word(DATA_SLOT, mmu.MEMORY_TYPE_NORMAL_COHERENT)
                original_pcc = core.pcc
                original_epcc = core.epcc
                original_sr = core.read_csr(csrs.CSR_SR)

                result = traps.enter_trap(
                    core,
                    instructions.FaultPacket(
                        instructions.ExceptionCause.ILLEGAL_INSTRUCTION,
                        location(core),
                    ),
                )

                self.assertTrue(result.fatal)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.epcc, original_epcc)
                self.assertEqual(core.read_csr(csrs.CSR_SR), original_sr)
                self.assertEqual(core.read_csr(csrs.CSR_CAUSE), 0x123)
                self.assertEqual(core.read_csr(csrs.CSR_TVAL), 0x456)
                self.assertFalse(core.reservation.valid)

    def test_protected_return_stack_faults_have_no_partial_push_or_pop_effects(self) -> None:
        call_cases = (
            ("invalid rsc", lambda memory: memory.protect_range(RETURN_STACK_BASE, 0x100), rsc_capability(tag=False)),
            ("unprotected rsc", lambda memory: None, rsc_capability()),
            (
                "missing local store",
                lambda memory: memory.protect_range(RETURN_STACK_BASE, 0x100),
                rsc_capability(
                    permissions=int(
                        caps.CapabilityPermission.ST | caps.CapabilityPermission.SC
                    )
                ),
            ),
        )
        for name, protect, rsc in call_cases:
            with self.subTest(path="CALL", name=name):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                protect(memory)
                memory.csc(RETURN_SLOT, sealed_return_capability())
                core.install_pcc(
                    state.SlottedCapability.from_capability(
                        executable_capability(0x1000, base=0x1000, top=0x2000),
                        state.SLOT_0,
                    )
                )
                core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], rsc)
                original_pcc = core.pcc
                original_rsc = core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"])
                original_slot = memory.clc(RETURN_SLOT)

                result = call_ops.execute_call(
                    core,
                    memory,
                    call_ops.call_instruction("CALL", (0x1800,), location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"]), original_rsc)
                self.assertEqual(memory.clc(RETURN_SLOT), original_slot)

        return_cases = (
            ("invalid return", sealed_return_capability(tag=False), True),
            ("wrong return type", sealed_return_capability(otype=0x22), True),
            ("unprotected return", sealed_return_capability(), False),
        )
        for name, stored, protect_stack in return_cases:
            with self.subTest(path="RET", name=name):
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                if protect_stack:
                    memory.protect_range(RETURN_STACK_BASE, 0x100)
                memory.csc(RETURN_SLOT, stored)
                core.write_ccsr(
                    state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"],
                    rsc_capability(cursor=RETURN_SLOT),
                )
                original_pcc = core.pcc
                original_rsc = core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"])
                original_slot = memory.clc(RETURN_SLOT)

                result = return_ops.execute_return(
                    core,
                    memory,
                    return_ops.return_instruction(location=location(core)),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(core.pcc, original_pcc)
                self.assertEqual(core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"]), original_rsc)
                self.assertEqual(memory.clc(RETURN_SLOT), original_slot)


if __name__ == "__main__":
    unittest.main()

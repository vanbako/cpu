"""RADIX4, SATP, ASID, TLB, and SFENCE SystemVerilog slice helpers.

Owner stories:
- I21-S02: RTL RADIX4 page walk, TLB, SATP, ASID, and page-fault behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import csrs, mmu, opcodes


JsonValue = Any

ROOT_TABLE = 0x8000
VIRTUAL_ADDRESS = 0x1234_5678_9120
PHYSICAL_ADDRESS_A = 0xA120
PHYSICAL_ADDRESS_B = 0xB120
USER_FETCH_ADDRESS = 0x4100
FIXTURE_ASID = 0x12
SECOND_ASID = 0x13

RTL_MMU_TLB_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_mmu_tlb_core.sv"),
    Path("rtl/cpu_v01_mmu_tlb_tb.sv"),
)
RTL_MMU_TLB_DOC = Path("docs/implementation/rtl-mmu-tlb-slice.md")

MMU_TLB_MNEMONICS = (
    "SFENCE.VM",
    "SFENCE.VM.ASID",
    "SFENCE.VM.VA",
    "SFENCE.VM.VA_ASID",
)
DEFERRED_MNEMONICS = (
    "FENCE",
    "FENCE.I",
    "LL48",
    "SC48",
    "CACHE.CLEAN",
    "CACHE.INVAL",
    "CACHE.CLEANINVAL",
)


@dataclass(frozen=True)
class RtlMmuTlbCoverageRow:
    case_id: str
    category: str
    mnemonic: str
    satp_mode: str
    asid: int
    virtual_address: int
    physical_address: int | None
    memory_type: str
    tlb_effect: str
    tlb_entries_before: int
    tlb_entries_after: int
    page_walk_levels: int
    fault_cause: str | None = None
    fault_tval: int | None = None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "mnemonic": self.mnemonic,
            "satp_mode": self.satp_mode,
            "asid": self.asid,
            "virtual_address": self.virtual_address,
            "physical_address": self.physical_address,
            "memory_type": self.memory_type,
            "tlb_effect": self.tlb_effect,
            "tlb_entries_before": self.tlb_entries_before,
            "tlb_entries_after": self.tlb_entries_after,
            "page_walk_levels": self.page_walk_levels,
            "fault_cause": self.fault_cause,
            "fault_tval": self.fault_tval,
        }


def mmu_tlb_mnemonics() -> tuple[str, ...]:
    return MMU_TLB_MNEMONICS


def mmu_tlb_coverage_rows() -> tuple[RtlMmuTlbCoverageRow, ...]:
    return (
        RtlMmuTlbCoverageRow(
            "bare_mode.ld48_identity",
            "translation",
            "LD48",
            "BARE",
            9,
            VIRTUAL_ADDRESS,
            VIRTUAL_ADDRESS,
            "NORMAL_COHERENT",
            "none",
            0,
            0,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "radix4.ld48_page_walk_fill",
            "translation",
            "LD48",
            "RADIX4",
            FIXTURE_ASID,
            VIRTUAL_ADDRESS,
            PHYSICAL_ADDRESS_A,
            "NORMAL_COHERENT",
            "dtlb_fill",
            0,
            1,
            4,
        ),
        RtlMmuTlbCoverageRow(
            "tlb.stale_hit_before_va_asid_sfence",
            "tlb",
            "LD48",
            "RADIX4",
            FIXTURE_ASID,
            VIRTUAL_ADDRESS,
            PHYSICAL_ADDRESS_A,
            "NORMAL_COHERENT",
            "dtlb_hit_stale",
            1,
            1,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "sfence.vm_va_asid_invalidates_stale",
            "sfence",
            "SFENCE.VM.VA_ASID",
            "RADIX4",
            FIXTURE_ASID,
            VIRTUAL_ADDRESS,
            None,
            "NORMAL_COHERENT",
            "invalidate_va_asid",
            1,
            0,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "radix4.load_after_sfence_page_fault",
            "fault",
            "LD48",
            "RADIX4",
            FIXTURE_ASID,
            VIRTUAL_ADDRESS,
            None,
            "NORMAL_COHERENT",
            "none",
            0,
            0,
            4,
            fault_cause="PAGE_FAULT",
            fault_tval=VIRTUAL_ADDRESS,
        ),
        RtlMmuTlbCoverageRow(
            "tlb.asid_specific_fill",
            "tlb",
            "LD48",
            "RADIX4",
            SECOND_ASID,
            VIRTUAL_ADDRESS,
            PHYSICAL_ADDRESS_B,
            "NORMAL_COHERENT",
            "dtlb_fill_asid",
            1,
            2,
            4,
        ),
        RtlMmuTlbCoverageRow(
            "tlb.global_entry_survives_asid",
            "tlb",
            "LD48",
            "RADIX4",
            SECOND_ASID,
            USER_FETCH_ADDRESS,
            USER_FETCH_ADDRESS,
            "NORMAL_COHERENT",
            "itlb_global_fill",
            2,
            3,
            4,
        ),
        RtlMmuTlbCoverageRow(
            "sfence.vm_all_invalidates_local",
            "sfence",
            "SFENCE.VM",
            "RADIX4",
            SECOND_ASID,
            0,
            None,
            "NORMAL_COHERENT",
            "invalidate_all",
            3,
            0,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "sfence.vm_asid_preserves_global",
            "sfence",
            "SFENCE.VM.ASID",
            "RADIX4",
            SECOND_ASID,
            0,
            None,
            "NORMAL_COHERENT",
            "invalidate_asid",
            1,
            1,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "sfence.vm_va_invalidates_page",
            "sfence",
            "SFENCE.VM.VA",
            "RADIX4",
            SECOND_ASID,
            VIRTUAL_ADDRESS,
            None,
            "NORMAL_COHERENT",
            "invalidate_va",
            1,
            0,
            0,
        ),
        RtlMmuTlbCoverageRow(
            "radix4.permission_page_fault",
            "fault",
            "LD48",
            "RADIX4",
            SECOND_ASID,
            VIRTUAL_ADDRESS,
            None,
            "NORMAL_COHERENT",
            "none",
            0,
            0,
            4,
            fault_cause="PAGE_FAULT",
            fault_tval=VIRTUAL_ADDRESS,
        ),
        RtlMmuTlbCoverageRow(
            "radix4.reserved_memory_type_page_fault",
            "fault",
            "LD48",
            "RADIX4",
            SECOND_ASID,
            VIRTUAL_ADDRESS,
            None,
            "RESERVED",
            "none",
            0,
            0,
            4,
            fault_cause="PAGE_FAULT",
            fault_tval=VIRTUAL_ADDRESS,
        ),
    )


def mmu_tlb_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in mmu_tlb_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def mmu_tlb_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_MMU_TLB_SOURCE_FILES)
    return f"verilator --binary --timing --top-module cpu_v01_mmu_tlb_tb {sources}"


def validate_rtl_mmu_tlb_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_MMU_TLB_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL MMU/TLB source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_mmu_tlb_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_mmu_tlb_tb.sv")
    doc = _read_if_exists(root / RTL_MMU_TLB_DOC)

    for token in _required_package_tokens():
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_mmu_tlb_core",
        "ST_BARE_LOAD",
        "ST_SATP_RADIX4",
        "ST_PAGE_WALK_L0",
        "ST_PAGE_WALK_L1",
        "ST_PAGE_WALK_L2",
        "ST_PAGE_WALK_L3",
        "ST_DTLB_FILL",
        "ST_DTLB_STALE_HIT",
        "ST_SFENCE_VM_VA_ASID",
        "ST_LOAD_AFTER_SFENCE_FAULT",
        "ST_ASID_SCOPE",
        "ST_GLOBAL_SCOPE",
        "ST_SFENCE_VM",
        "ST_SFENCE_VM_ASID",
        "ST_SFENCE_VM_VA",
        "ST_PAGE_FAULT_PERMISSION",
        "ST_PAGE_FAULT_MEMTYPE",
        "retire_packet_q.translation_valid <= 1'b1",
        "retire_packet_q.tlb_fill_valid <= tlb_fill",
        "retire_packet_q.tlb_invalidate_valid <= 1'b1",
        "retire_packet_q.tlb_invalidate_kind <= kind",
        "start_fault_packet(OPC_LD48_24, VIRTUAL_ADDRESS, EXC_PAGE_FAULT)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_mmu_tlb_core.sv missing {token}")

    for token in (
        "module cpu_v01_mmu_tlb_tb",
        "bare SATP identity translation result mismatch",
        "RADIX4 page-walk translation result mismatch",
        "stale TLB hit before SFENCE result mismatch",
        "SFENCE.VM invalidation result mismatch",
        "ASID/global TLB scope result mismatch",
        "RADIX4 page fault result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_mmu_tlb_tb.sv missing {token}")

    rows = mmu_tlb_coverage_rows()
    by_case = {row.case_id: row for row in rows}
    if by_case["bare_mode.ld48_identity"].physical_address != VIRTUAL_ADDRESS:
        issues.append("bare mode row must keep physical address equal to virtual address")
    page_walk = by_case["radix4.ld48_page_walk_fill"]
    if page_walk.physical_address != PHYSICAL_ADDRESS_A or page_walk.page_walk_levels != 4:
        issues.append("RADIX4 page-walk row must translate through 4 levels to physical A")
    stale = by_case["tlb.stale_hit_before_va_asid_sfence"]
    if stale.tlb_effect != "dtlb_hit_stale" or stale.physical_address != PHYSICAL_ADDRESS_A:
        issues.append("stale TLB row must preserve the old physical address")
    sfence = by_case["sfence.vm_va_asid_invalidates_stale"]
    if sfence.tlb_entries_after != 0 or sfence.tlb_effect != "invalidate_va_asid":
        issues.append("VA_ASID SFENCE row must invalidate the stale entry")
    for case_id in (
        "radix4.load_after_sfence_page_fault",
        "radix4.permission_page_fault",
        "radix4.reserved_memory_type_page_fault",
    ):
        row = by_case[case_id]
        if row.fault_cause != "PAGE_FAULT" or row.fault_tval != VIRTUAL_ADDRESS:
            issues.append(f"{case_id} must report PAGE_FAULT at the virtual address")

    covered_mnemonics = {row.mnemonic for row in rows}
    for mnemonic in MMU_TLB_MNEMONICS:
        if mnemonic not in covered_mnemonics:
            issues.append(f"missing MMU/TLB projection for {mnemonic}")
        for form in opcodes.opcode_forms_for(mnemonic):
            if form.size.bits != 24:
                issues.append(f"{mnemonic} must stay a 24-bit SFENCE form")
    for mnemonic in DEFERRED_MNEMONICS:
        if mnemonic in covered_mnemonics:
            issues.append(f"{mnemonic} must stay deferred from I21-S02")

    expected_satp = csrs.pack_satp(
        csrs.SATP_MODE_RADIX4,
        FIXTURE_ASID,
        ROOT_TABLE >> csrs.SATP_ROOT_PPN_SHIFT,
    )
    if csrs.satp_mode(expected_satp) != csrs.SATP_MODE_RADIX4:
        issues.append("fixture SATP must encode RADIX4 mode")
    if csrs.satp_asid(expected_satp) != FIXTURE_ASID:
        issues.append("fixture SATP must carry the expected ASID")
    if mmu.MEMORY_TYPE_RESERVED != 0b11:
        issues.append("reserved memory type must remain 0b11")

    for token in (
        "Story: I21-S02",
        "python tools\\rtl_mmu_tlb_slice.py --check",
        "cpu_v01_mmu_tlb_core.sv",
        "RADIX4",
        "SFENCE.VM.VA_ASID",
        "PAGE_FAULT",
    ):
        if token not in doc:
            issues.append(f"{RTL_MMU_TLB_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _required_package_tokens() -> tuple[str, ...]:
    tokens = [
        "OPC_SFENCE_VM_24",
        "OPC_SFENCE_VM_ASID_24",
        "OPC_SFENCE_VM_VA_24",
        "OPC_SFENCE_VM_VA_ASID_24",
        "EXC_PAGE_FAULT",
        "EXC_PRIVILEGE_FAULT",
        "CSR_SATP",
        "CSR_ASID",
        "SATP_MODE_BARE",
        "SATP_MODE_RADIX4",
        "SATP_MODE_SHIFT",
        "SATP_ASID_SHIFT",
        "SATP_ROOT_PPN_SHIFT",
        "PTE_V_BIT",
        "PTE_R_BIT",
        "PTE_W_BIT",
        "PTE_X_BIT",
        "PTE_A_BIT",
        "PTE_MT_SHIFT",
        "PTE_PPN_SHIFT",
        "MEMORY_TYPE_NORMAL_COHERENT",
        "MEMORY_TYPE_DEVICE_ORDERED",
        "MEMORY_TYPE_RESERVED",
        "TLB_INV_ALL",
        "TLB_INV_ASID",
        "TLB_INV_VA",
        "TLB_INV_VA_ASID",
        "translation_valid",
        "effective_address",
        "physical_address",
        "translation_memory_type",
        "translation_tlb_hit",
        "tlb_fill_valid",
        "tlb_invalidate_valid",
        "tlb_invalidate_kind",
        "tlb_invalidate_va",
        "tlb_invalidate_asid",
    ]
    return tuple(tokens)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

"""Integrated cpu_v01_core MMU, TLB, and SFENCE helpers.

Owner stories:
- I22-S06: integrated SATP/ASID, translation, local TLB, and page faults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import rtl_mmu_tlb


JsonValue = Any

RTL_CORE_MMU_TLB_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_mmu_tlb_tb.sv"),
)
RTL_CORE_MMU_TLB_DOC = Path("docs/implementation/rtl-integrated-core-mmu-tlb.md")


@dataclass(frozen=True)
class IntegratedMmuTlbCoverageRow:
    case_id: str
    mnemonic: str
    retire_effects: tuple[str, ...]
    integrated_path: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "mnemonic": self.mnemonic,
            "retire_effects": list(self.retire_effects),
            "integrated_path": self.integrated_path,
        }


def integrated_mmu_tlb_coverage_rows() -> tuple[IntegratedMmuTlbCoverageRow, ...]:
    return tuple(
        IntegratedMmuTlbCoverageRow(
            case_id=row.case_id,
            mnemonic=row.mnemonic,
            retire_effects=_retire_effects(row),
            integrated_path="cpu_v01_core.translate_data_address+memory_states",
        )
        for row in rtl_mmu_tlb.mmu_tlb_coverage_rows()
    )


def integrated_mmu_tlb_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in integrated_mmu_tlb_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_mmu_tlb_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_MMU_TLB_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_core_mmu_tlb_tb {sources}"
    )


def validate_rtl_core_mmu_tlb(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_MMU_TLB_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing integrated core MMU/TLB source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_mmu_tlb_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_MMU_TLB_DOC)

    for token in (
        "MMU_TLB_VIRTUAL_ADDRESS",
        "MMU_TLB_PHYSICAL_ADDRESS_A",
        "MMU_TLB_PHYSICAL_ADDRESS_B",
        "MMU_TLB_PERMISSION_ROOT_PPN",
        "MMU_TLB_MEMTYPE_ROOT_PPN",
        "translation_result_t",
        "satp_mode_value",
        "satp_root_ppn",
        "current_asid",
        "translate_instruction_address",
        "translate_data_address",
        "mark_translation_fault",
        "commit_tlb_invalidate",
        "mem_effective_address_q",
        "dtlb_valid_q",
        "mapping_a_removed_q",
        "retire_packet_q.translation_valid",
        "retire_packet_q.tlb_fill_valid",
        "retire_packet_q.tlb_invalidate_valid",
        "OPC_SFENCE_VM_24",
        "OPC_SFENCE_VM_VA_ASID_24",
        "EXC_PAGE_FAULT",
        "MEMORY_TYPE_RESERVED",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "module cpu_v01_core_mmu_tlb_tb",
        "cpu_v01_core_mmu_tlb_fixture",
        "CCSRRD C1, PCC",
        "CSRWR SATP, D4",
        "SFENCE.VM.VA_ASID D2, D6",
        "SFENCE.VM.ASID D6",
        "bare SATP identity translation result mismatch",
        "RADIX4 page-walk translation result mismatch",
        "stale TLB hit before SFENCE result mismatch",
        "ASID/global TLB scope result mismatch",
        "permission page fault mismatch",
        "reserved memory type page fault mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_mmu_tlb_tb.sv missing {token}")

    rows = integrated_mmu_tlb_coverage_rows()
    covered = {row.mnemonic for row in rows}
    for mnemonic in rtl_mmu_tlb.MMU_TLB_MNEMONICS:
        if mnemonic not in covered:
            issues.append(f"missing integrated MMU/TLB projection for {mnemonic}")

    by_case = {row.case_id: row for row in rows}
    if "translation:bare_identity" not in by_case["bare_mode.ld48_identity"].retire_effects:
        issues.append("bare load row must identify identity translation")
    if "dtlb_fill" not in by_case["radix4.ld48_page_walk_fill"].retire_effects:
        issues.append("RADIX4 page-walk row must identify DTLB fill")
    if "dtlb_hit_stale" not in by_case["tlb.stale_hit_before_va_asid_sfence"].retire_effects:
        issues.append("stale row must identify DTLB stale hit")
    if by_case["sfence.vm_va_asid_invalidates_stale"].retire_effects != (
        "tlb_invalidate:VA_ASID",
    ):
        issues.append("VA_ASID SFENCE row must identify VA_ASID invalidation")
    if by_case["radix4.permission_page_fault"].retire_effects != (
        "fault:PAGE_FAULT",
        "translation_fault:NORMAL_COHERENT",
    ):
        issues.append("permission row must identify PAGE_FAULT at normal memory type")
    if by_case["radix4.reserved_memory_type_page_fault"].retire_effects != (
        "fault:PAGE_FAULT",
        "translation_fault:RESERVED",
    ):
        issues.append("reserved memory-type row must identify PAGE_FAULT at RESERVED")

    for token in (
        "Story: I22-S06",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_mmu_tlb_tb.sv",
        "python tools\\rtl_core_mmu_tlb.py --check",
        "cpu_v01_core_mmu_tlb_tb",
        "SATP",
        "ASID",
        "RADIX4",
        "SFENCE.VM",
        "SFENCE.VM.VA_ASID",
        "PAGE_FAULT",
        "memory-type",
        "stale TLB",
        "I22-S07",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_MMU_TLB_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"integrated MMU/TLB coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _retire_effects(row: rtl_mmu_tlb.RtlMmuTlbCoverageRow) -> tuple[str, ...]:
    effects: list[str] = []
    if row.fault_cause:
        effects.append(f"fault:{row.fault_cause}")
        effects.append(f"translation_fault:{row.memory_type}")
        return tuple(effects)
    if row.satp_mode == "BARE" and row.physical_address == row.virtual_address:
        effects.append("translation:bare_identity")
    if row.page_walk_levels:
        effects.append(f"page_walk:{row.page_walk_levels}")
    if row.tlb_effect == "dtlb_fill":
        effects.append("dtlb_fill")
    elif row.tlb_effect == "dtlb_hit_stale":
        effects.append("dtlb_hit_stale")
    elif row.tlb_effect == "dtlb_fill_asid":
        effects.append("dtlb_fill:asid")
    elif row.tlb_effect == "itlb_global_fill":
        effects.append("itlb_fill:global")
    elif row.tlb_effect.startswith("invalidate_"):
        effects.append(f"tlb_invalidate:{_invalidate_name(row.tlb_effect)}")
    if not effects:
        effects.append("normal_retire:no_write")
    return tuple(effects)


def _invalidate_name(effect: str) -> str:
    return {
        "invalidate_all": "ALL",
        "invalidate_asid": "ASID",
        "invalidate_va": "VA",
        "invalidate_va_asid": "VA_ASID",
    }[effect]


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

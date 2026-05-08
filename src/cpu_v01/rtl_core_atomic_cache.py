"""Integrated cpu_v01_core LL/SC, reservation, fence, and cache helpers.

Owner stories:
- I22-S07: integrated atomic, reservation, fence, and cache-maintenance behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import rtl_atomic_cache


JsonValue = Any

RTL_CORE_ATOMIC_CACHE_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_atomic_cache_tb.sv"),
)
RTL_CORE_ATOMIC_CACHE_DOC = Path(
    "docs/implementation/rtl-integrated-core-atomic-cache.md"
)


@dataclass(frozen=True)
class IntegratedAtomicCacheCoverageRow:
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


def integrated_atomic_cache_coverage_rows() -> tuple[IntegratedAtomicCacheCoverageRow, ...]:
    return tuple(
        IntegratedAtomicCacheCoverageRow(
            case_id=row.case_id,
            mnemonic=row.mnemonic,
            retire_effects=_retire_effects(row),
            integrated_path="cpu_v01_core.execute_decoded_packet+memory_states",
        )
        for row in rtl_atomic_cache.atomic_cache_coverage_rows()
    )


def integrated_atomic_cache_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in integrated_atomic_cache_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_atomic_cache_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_ATOMIC_CACHE_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_core_atomic_cache_tb {sources}"
    )


def validate_rtl_core_atomic_cache(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_ATOMIC_CACHE_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing integrated core atomic/cache source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_atomic_cache_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_ATOMIC_CACHE_DOC)

    for token in (
        "ATOMIC_CACHE_DEVICE_PA",
        "reservation_valid_q",
        "reservation_word_address_q",
        "reservation_memory_type_q",
        "reservation_overlaps",
        "commit_reservation_install",
        "commit_reservation_clear_if_valid",
        "commit_reservation_clear_at",
        "OPC_LL48_24",
        "OPC_SC48_24",
        "OPC_FENCE_24",
        "OPC_FENCE_I_24",
        "OPC_CACHE_CLEAN_24",
        "OPC_CACHE_INVAL_24",
        "OPC_CACHE_CLEANINVAL_24",
        "retire_packet_q.reservation_install_valid",
        "retire_packet_q.reservation_clear_valid",
        "retire_packet_q.sc_success",
        "retire_packet_q.fence_order_valid",
        "retire_packet_q.fence_i_valid",
        "retire_packet_q.cache_maintenance_valid",
        "MEMORY_TYPE_DEVICE_ORDERED",
        "EXC_ACCESS_FAULT",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "module cpu_v01_core_atomic_cache_tb",
        "cpu_v01_core_atomic_cache_fixture",
        "CCSRRD C1, PCC",
        "LL48 D2, C1, D0",
        "SC48 D3, C1, D0, D4",
        "CACHE.CLEAN C1, D0, D7",
        "CSRWR ASID, D7",
        "SFENCE.VM",
        "BRK",
        "integrated atomic/cache LL48/SC48 success result mismatch",
        "integrated atomic/cache SC48 failure result mismatch",
        "integrated atomic/cache LL/SC conflict clear result mismatch",
        "integrated atomic/cache faulting LL48 reservation clear result mismatch",
        "integrated atomic/cache trap CSR fence reservation clear result mismatch",
        "integrated atomic/cache FENCE/FENCE.I ordering result mismatch",
        "integrated atomic/cache CACHE maintenance access result mismatch",
        "integrated atomic/cache CACHE device access fault result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_atomic_cache_tb.sv missing {token}")

    rows = integrated_atomic_cache_coverage_rows()
    covered = {row.mnemonic for row in rows}
    for mnemonic in rtl_atomic_cache.ATOMIC_CACHE_MNEMONICS:
        if mnemonic not in covered:
            issues.append(f"missing integrated atomic/cache projection for {mnemonic}")

    by_case = {row.case_id: row for row in rows}
    if by_case["llsc.ll48_install"].retire_effects != (
        "reservation:install",
        "memory:integer_load",
    ):
        issues.append("LL48 row must identify reservation install and integer load")
    if by_case["llsc.sc48_success_store_clear"].retire_effects != (
        "reservation:clear",
        "memory:store_tag_clear",
        "sc_success",
    ):
        issues.append("SC48 success row must identify store, tag clear, and success")
    if by_case["llsc.sc48_failure_clear"].retire_effects != (
        "reservation:clear",
        "sc_failure",
    ):
        issues.append("SC48 failure row must identify clear and failure result")
    if by_case["reservation.sfence_clear"].retire_effects != (
        "reservation:fence_clear",
        "tlb_invalidate:ALL",
    ):
        issues.append("SFENCE clear row must identify reservation and TLB invalidation")
    if by_case["cache.clean_device_access_fault"].retire_effects != (
        "fault:ACCESS_FAULT",
        "translation_fault:DEVICE_ORDERED",
    ):
        issues.append("device cache row must identify ACCESS_FAULT on DEVICE_ORDERED memory")

    for token in (
        "Story: I22-S07",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_atomic_cache_tb.sv",
        "python tools\\rtl_core_atomic_cache.py --check",
        "cpu_v01_core_atomic_cache_tb",
        "LL48",
        "SC48",
        "reservation",
        "FENCE.I",
        "CACHE.CLEANINVAL",
        "ACCESS_FAULT",
        "DEVICE_ORDERED",
        "I22-S08",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_ATOMIC_CACHE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"integrated atomic/cache coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _retire_effects(row: rtl_atomic_cache.RtlAtomicCacheCoverageRow) -> tuple[str, ...]:
    if row.fault_cause == "ACCESS_FAULT":
        return ("fault:ACCESS_FAULT", "translation_fault:DEVICE_ORDERED")
    if row.fault_cause:
        return (f"fault:{row.fault_cause}", f"reservation:{row.reservation_effect}")

    effects: list[str] = []
    if row.reservation_effect != "none":
        effects.append(f"reservation:{row.reservation_effect}")
    if row.memory_effect != "none":
        effects.append(f"memory:{row.memory_effect}")
    if row.cache_effect == "fence_order":
        effects.append("fence_order")
    elif row.cache_effect == "fence_i":
        effects.append("fence_i")
    elif row.cache_effect != "none":
        effects.append(f"cache:{row.cache_effect}")
    if row.case_id == "llsc.sc48_success_store_clear":
        effects.append("sc_success")
    elif row.case_id == "llsc.sc48_failure_clear":
        effects.append("sc_failure")
    elif row.case_id == "reservation.sfence_clear":
        effects.append("tlb_invalidate:ALL")
    if not effects:
        effects.append("normal_retire:no_write")
    return tuple(effects)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

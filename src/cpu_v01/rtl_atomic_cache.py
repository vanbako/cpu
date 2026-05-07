"""LL/SC, reservation, fence, and cache-maintenance RTL slice helpers.

Owner stories:
- I21-S03: RTL LL/SC, reservation, fence, and cache-maintenance effects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import atomic_ops, cache_ops, fence_ops, mmu, opcodes


JsonValue = Any

WORD_PA = 0xA000
DEVICE_PA = 0xF000

RTL_ATOMIC_CACHE_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_atomic_cache_core.sv"),
    Path("rtl/cpu_v01_atomic_cache_tb.sv"),
)
RTL_ATOMIC_CACHE_DOC = Path("docs/implementation/rtl-atomic-cache-slice.md")

ATOMIC_CACHE_MNEMONICS = (
    "LL48",
    "SC48",
    "FENCE",
    "FENCE.I",
    "CACHE.CLEAN",
    "CACHE.INVAL",
    "CACHE.CLEANINVAL",
)
DEFERRED_MNEMONICS = (
    "CALLC",
    "WFI",
    "CINCADDR",
    "CSETBOUNDS",
    "CSEAL",
    "CUNSEAL",
)


@dataclass(frozen=True)
class RtlAtomicCacheCoverageRow:
    case_id: str
    category: str
    mnemonic: str
    opcode_id: int
    reservation_before: bool
    reservation_after: bool
    reservation_effect: str
    memory_effect: str
    cache_effect: str
    fault_cause: str | None = None
    fault_tval: int | None = None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "mnemonic": self.mnemonic,
            "opcode_id": self.opcode_id,
            "reservation_before": self.reservation_before,
            "reservation_after": self.reservation_after,
            "reservation_effect": self.reservation_effect,
            "memory_effect": self.memory_effect,
            "cache_effect": self.cache_effect,
            "fault_cause": self.fault_cause,
            "fault_tval": self.fault_tval,
        }


def atomic_cache_mnemonics() -> tuple[str, ...]:
    return ATOMIC_CACHE_MNEMONICS


def atomic_cache_coverage_rows() -> tuple[RtlAtomicCacheCoverageRow, ...]:
    return tuple(
        _row(*args)
        for args in (
            (
                "llsc.ll48_install",
                "llsc",
                "LL48",
                False,
                True,
                "install",
                "integer_load",
                "none",
                None,
                None,
            ),
            (
                "llsc.sc48_success_store_clear",
                "llsc",
                "SC48",
                True,
                False,
                "clear",
                "store_tag_clear",
                "none",
                None,
                None,
            ),
            (
                "llsc.sc48_failure_clear",
                "llsc",
                "SC48",
                False,
                False,
                "clear",
                "none",
                "none",
                None,
                None,
            ),
            (
                "llsc.conflicting_store_clear",
                "reservation",
                "ST48",
                True,
                False,
                "conflict_clear",
                "store",
                "none",
                None,
                None,
            ),
            (
                "llsc.faulting_ll48_clear",
                "fault",
                "LL48",
                True,
                False,
                "fault_clear",
                "none",
                "none",
                "ALIGN_FAULT",
                WORD_PA + 1,
            ),
            (
                "reservation.csr_clear",
                "reservation",
                "CSRWR",
                True,
                False,
                "csr_clear",
                "none",
                "none",
                None,
                None,
            ),
            (
                "reservation.trap_clear",
                "reservation",
                "BRK",
                True,
                False,
                "trap_clear",
                "none",
                "none",
                "BREAKPOINT",
                0,
            ),
            (
                "reservation.sfence_clear",
                "reservation",
                "SFENCE.VM",
                True,
                False,
                "fence_clear",
                "none",
                "none",
                None,
                None,
            ),
            (
                "ordering.fence",
                "ordering",
                "FENCE",
                False,
                False,
                "none",
                "none",
                "fence_order",
                None,
                None,
            ),
            (
                "ordering.fence_i",
                "ordering",
                "FENCE.I",
                False,
                False,
                "none",
                "none",
                "fence_i",
                None,
                None,
            ),
            (
                "cache.clean",
                "cache",
                "CACHE.CLEAN",
                False,
                False,
                "none",
                "none",
                "clean",
                None,
                None,
            ),
            (
                "cache.inval_clears_reservation",
                "cache",
                "CACHE.INVAL",
                True,
                False,
                "cache_clear",
                "none",
                "inval",
                None,
                None,
            ),
            (
                "cache.cleaninval_clears_reservation",
                "cache",
                "CACHE.CLEANINVAL",
                True,
                False,
                "cache_clear",
                "none",
                "cleaninval",
                None,
                None,
            ),
            (
                "cache.clean_device_access_fault",
                "fault",
                "CACHE.CLEAN",
                False,
                False,
                "none",
                "none",
                "none",
                "ACCESS_FAULT",
                DEVICE_PA,
            ),
        )
    )


def atomic_cache_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in atomic_cache_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def atomic_cache_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_ATOMIC_CACHE_SOURCE_FILES)
    return f"verilator --binary --timing --top-module cpu_v01_atomic_cache_tb {sources}"


def validate_rtl_atomic_cache_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_ATOMIC_CACHE_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL atomic/cache source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_atomic_cache_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_atomic_cache_tb.sv")
    doc = _read_if_exists(root / RTL_ATOMIC_CACHE_DOC)

    for token in _required_package_tokens():
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_atomic_cache_core",
        "ST_LL48",
        "ST_SC48_SUCCESS",
        "ST_SC48_FAILURE",
        "ST_CONFLICT_STORE_CLEAR",
        "ST_FAULTING_LL48_CLEAR",
        "ST_CSR_CLEAR",
        "ST_TRAP_CLEAR",
        "ST_SFENCE_CLEAR",
        "ST_FENCE",
        "ST_FENCE_I",
        "ST_CACHE_CLEAN",
        "ST_CACHE_INVAL",
        "ST_CACHE_CLEANINVAL",
        "ST_CACHE_DEVICE_FAULT",
        "retire_packet_q.reservation_install_valid <= 1'b1",
        "retire_packet_q.reservation_clear_valid <= 1'b1",
        "retire_packet_q.sc_success <= success",
        "retire_packet_q.fence_order_valid <= 1'b1",
        "retire_packet_q.fence_i_valid <= 1'b1",
        "retire_packet_q.cache_maintenance_valid <= 1'b1",
        "start_fault_packet(OPC_CACHE_CLEAN_24, EXC_ACCESS_FAULT, DEVICE_PA)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_atomic_cache_core.sv missing {token}")

    for token in (
        "module cpu_v01_atomic_cache_tb",
        "LL48/SC48 success result mismatch",
        "SC48 failure result mismatch",
        "LL/SC conflict clear result mismatch",
        "faulting LL48 reservation clear result mismatch",
        "trap CSR fence reservation clear result mismatch",
        "FENCE/FENCE.I ordering result mismatch",
        "CACHE maintenance access result mismatch",
        "CACHE device access fault result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_atomic_cache_tb.sv missing {token}")

    rows = atomic_cache_coverage_rows()
    covered = {row.mnemonic for row in rows}
    for mnemonic in ATOMIC_CACHE_MNEMONICS:
        if mnemonic not in covered:
            issues.append(f"missing atomic/cache projection for {mnemonic}")
    for mnemonic in DEFERRED_MNEMONICS:
        if mnemonic in covered:
            issues.append(f"{mnemonic} must stay deferred from I21-S03")

    by_case = {row.case_id: row for row in rows}
    if by_case["llsc.ll48_install"].reservation_effect != "install":
        issues.append("LL48 row must install a reservation")
    if by_case["llsc.sc48_success_store_clear"].memory_effect != "store_tag_clear":
        issues.append("SC48 success row must store and clear the tag")
    if by_case["llsc.sc48_failure_clear"].memory_effect != "none":
        issues.append("SC48 failure row must not write memory")
    if by_case["llsc.faulting_ll48_clear"].fault_cause != "ALIGN_FAULT":
        issues.append("faulting LL48 row must report ALIGN_FAULT")
    if by_case["cache.clean_device_access_fault"].fault_cause != "ACCESS_FAULT":
        issues.append("device cache-maintenance row must report ACCESS_FAULT")

    if atomic_ops.ATOMIC_MNEMONICS != frozenset({"LL48", "SC48"}):
        issues.append("semantic atomic mnemonic set must remain LL48/SC48")
    if cache_ops.CACHE_MNEMONICS != frozenset(
        {"CACHE.CLEAN", "CACHE.INVAL", "CACHE.CLEANINVAL"}
    ):
        issues.append("semantic cache mnemonic set must remain CACHE.*")
    for mnemonic in ("FENCE", "FENCE.I"):
        if mnemonic not in fence_ops.FENCE_MNEMONICS:
            issues.append(f"semantic fence mnemonic set missing {mnemonic}")
    if mmu.MEMORY_TYPE_NORMAL_COHERENT != 0:
        issues.append("normal coherent memory type must stay 0")

    for token in (
        "Story: I21-S03",
        "python tools\\rtl_atomic_cache_slice.py --check",
        "cpu_v01_atomic_cache_core.sv",
        "LL48",
        "SC48",
        "CACHE.CLEANINVAL",
        "ACCESS_FAULT",
    ):
        if token not in doc:
            issues.append(f"{RTL_ATOMIC_CACHE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _row(
    case_id: str,
    category: str,
    mnemonic: str,
    reservation_before: bool,
    reservation_after: bool,
    reservation_effect: str,
    memory_effect: str,
    cache_effect: str,
    fault_cause: str | None,
    fault_tval: int | None,
) -> RtlAtomicCacheCoverageRow:
    return RtlAtomicCacheCoverageRow(
        case_id=case_id,
        category=category,
        mnemonic=mnemonic,
        opcode_id=opcodes.opcode_forms_for(mnemonic)[0].opcode_id,
        reservation_before=reservation_before,
        reservation_after=reservation_after,
        reservation_effect=reservation_effect,
        memory_effect=memory_effect,
        cache_effect=cache_effect,
        fault_cause=fault_cause,
        fault_tval=fault_tval,
    )


def _required_package_tokens() -> tuple[str, ...]:
    return (
        "OPC_LL48_24",
        "OPC_SC48_24",
        "OPC_FENCE_24",
        "OPC_FENCE_I_24",
        "OPC_CACHE_CLEAN_24",
        "OPC_CACHE_INVAL_24",
        "OPC_CACHE_CLEANINVAL_24",
        "EXC_ACCESS_FAULT",
        "CACHE_MAINT_KIND_BITS",
        "CACHE_MAINT_CLEAN",
        "CACHE_MAINT_INVAL",
        "CACHE_MAINT_CLEANINVAL",
        "reservation_install_valid",
        "reservation_clear_valid",
        "reservation_word_address",
        "reservation_memory_type",
        "sc_success",
        "fence_order_valid",
        "fence_i_valid",
        "cache_maintenance_valid",
        "cache_maintenance_kind",
        "cache_maintenance_address",
        "cache_maintenance_length",
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

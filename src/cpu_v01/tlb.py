"""Private per-core TLB model for CPU v0.1.

Owner stories:
- E09-S03: private ITLB/DTLB state, ASID/global matching, and invalidation.
- E08-S04: `SFENCE.VM` local invalidation effects.
- I06-S02: TLBs and `SFENCE.VM` forms.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import csrs
from .cells import BASE_PAGE_CELLS


class TlbKind(Enum):
    INSTRUCTION = "ITLB"
    DATA = "DTLB"


class TlbInvalidateKind(Enum):
    ALL = "ALL"
    ASID = "ASID"
    VA = "VA"
    VA_ASID = "VA_ASID"


@dataclass(frozen=True)
class TlbEntry:
    kind: TlbKind
    mode: int
    vpn: int
    asid: int
    ppn: int
    user: bool
    readable: bool
    writable: bool
    executable: bool
    memory_type: int
    global_mapping: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", TlbKind(self.kind))
        object.__setattr__(self, "mode", csrs.require_uint(self.mode, csrs.SATP_MODE_BITS, "mode"))
        object.__setattr__(self, "vpn", csrs.require_uint(self.vpn, csrs.SATP_ROOT_PPN_BITS, "vpn"))
        object.__setattr__(self, "asid", csrs.require_uint(self.asid, csrs.SATP_ASID_BITS, "asid"))
        object.__setattr__(self, "ppn", csrs.require_uint(self.ppn, csrs.SATP_ROOT_PPN_BITS, "ppn"))
        object.__setattr__(self, "memory_type", csrs.require_uint(self.memory_type, 2, "memory_type"))

    def matches(self, kind: TlbKind, mode: int, vpn: int, asid: int) -> bool:
        return (
            self.kind is TlbKind(kind)
            and self.mode == mode
            and self.vpn == vpn
            and (self.global_mapping or self.asid == asid)
        )


class LocalTlbs:
    """Private local ITLB and DTLB entries for one simulated core."""

    def __init__(self) -> None:
        self._entries: list[TlbEntry] = []

    def lookup(self, kind: TlbKind, mode: int, vpn: int, asid: int) -> TlbEntry | None:
        kind = TlbKind(kind)
        mode = csrs.require_uint(mode, csrs.SATP_MODE_BITS, "mode")
        vpn = csrs.require_uint(vpn, csrs.SATP_ROOT_PPN_BITS, "vpn")
        asid = csrs.require_uint(asid, csrs.SATP_ASID_BITS, "asid")
        for entry in self._entries:
            if entry.matches(kind, mode, vpn, asid):
                return entry
        return None

    def insert(self, entry: TlbEntry) -> None:
        if not isinstance(entry, TlbEntry):
            raise TypeError("entry must be a TlbEntry")
        self._entries = [
            existing
            for existing in self._entries
            if not (
                existing.kind is entry.kind
                and existing.mode == entry.mode
                and existing.vpn == entry.vpn
                and existing.asid == entry.asid
                and existing.global_mapping == entry.global_mapping
            )
        ]
        self._entries.append(entry)

    def invalidate_all(self) -> None:
        self._entries.clear()

    def invalidate_asid(self, asid: int) -> None:
        asid = csrs.require_uint(asid, csrs.SATP_ASID_BITS, "asid")
        self._entries = [
            entry
            for entry in self._entries
            if entry.global_mapping or entry.asid != asid
        ]

    def invalidate_va(self, virtual_address: int) -> None:
        vpn = vpn_from_address(virtual_address)
        self._entries = [entry for entry in self._entries if entry.vpn != vpn]

    def invalidate_va_asid(self, virtual_address: int, asid: int) -> None:
        vpn = vpn_from_address(virtual_address)
        asid = csrs.require_uint(asid, csrs.SATP_ASID_BITS, "asid")
        self._entries = [
            entry
            for entry in self._entries
            if entry.global_mapping or entry.vpn != vpn or entry.asid != asid
        ]

    def entry_count(self, kind: TlbKind | None = None) -> int:
        if kind is None:
            return len(self._entries)
        kind = TlbKind(kind)
        return sum(1 for entry in self._entries if entry.kind is kind)


@dataclass(frozen=True)
class TlbInvalidateEffect:
    kind: TlbInvalidateKind
    virtual_address: int = 0
    asid: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", TlbInvalidateKind(self.kind))
        object.__setattr__(self, "virtual_address", csrs.require_uint(self.virtual_address, csrs.CSR_BITS, "virtual_address"))
        object.__setattr__(self, "asid", csrs.require_uint(self.asid, csrs.SATP_ASID_BITS, "asid"))

    def apply(self, core: object) -> None:
        local_tlbs = getattr(core, "tlbs", None)
        if not isinstance(local_tlbs, LocalTlbs):
            raise TypeError("core must provide LocalTlbs")
        if self.kind is TlbInvalidateKind.ALL:
            local_tlbs.invalidate_all()
        elif self.kind is TlbInvalidateKind.ASID:
            local_tlbs.invalidate_asid(self.asid)
        elif self.kind is TlbInvalidateKind.VA:
            local_tlbs.invalidate_va(self.virtual_address)
        elif self.kind is TlbInvalidateKind.VA_ASID:
            local_tlbs.invalidate_va_asid(self.virtual_address, self.asid)
        else:
            raise AssertionError(f"unhandled TLB invalidate kind {self.kind}")


def vpn_from_address(virtual_address: int) -> int:
    virtual_address = csrs.require_uint(virtual_address, csrs.CSR_BITS, "virtual_address")
    return virtual_address // BASE_PAGE_CELLS


def page_offset(virtual_address: int) -> int:
    virtual_address = csrs.require_uint(virtual_address, csrs.CSR_BITS, "virtual_address")
    return virtual_address % BASE_PAGE_CELLS

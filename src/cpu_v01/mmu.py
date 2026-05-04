"""SATP, RADIX4 page walking, and page-permission checks for CPU v0.1.

Owner stories:
- E09-S02: SATP layout and translation modes.
- E09-S04: 4-level RADIX4 page-table geometry.
- E09-S05: PTE format and page-walk faults.
- E09-S07: effective-access translation and page checks.
- I06-S01: RADIX4 translation and page permissions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import csrs
from .cells import ADDRESS_SPACE_CELLS, BASE_PAGE_CELLS, INTEGER_OBJECT_CELLS
from .instructions import (
    ExceptionCause,
    FaultPacket,
    InstructionLocation,
)
from .memory import MemoryAccessError, TaggedMemory
from .state import CoreState
from .tlb import TlbEntry, TlbKind, page_offset, vpn_from_address


PTE_SIZE_CELLS = INTEGER_OBJECT_CELLS
PTE_INDEXES_PER_PAGE = BASE_PAGE_CELLS // PTE_SIZE_CELLS
VPN_INDEX_SHIFTS = (41, 31, 21, 11)
VPN_INDEX_MASKS = (0x7F, 0x3FF, 0x3FF, 0x3FF)
PAGE_OFFSET_MASK = BASE_PAGE_CELLS - 1

PTE_V_BIT = 0
PTE_U_BIT = 1
PTE_R_BIT = 2
PTE_W_BIT = 3
PTE_X_BIT = 4
PTE_G_BIT = 5
PTE_A_BIT = 6
PTE_SW_BIT = 7
PTE_MT_SHIFT = 8
PTE_MT_BITS = 2
PTE_RES0_BIT = 10
PTE_PPN_SHIFT = 11
PTE_PPN_BITS = 37
PTE_PPN_MASK = (1 << PTE_PPN_BITS) - 1
PTE_MT_MASK = (1 << PTE_MT_BITS) - 1

MEMORY_TYPE_NORMAL_COHERENT = 0b00
MEMORY_TYPE_NORMAL_UNCACHEABLE = 0b01
MEMORY_TYPE_DEVICE_ORDERED = 0b10
MEMORY_TYPE_RESERVED = 0b11


class AccessType(Enum):
    FETCH = "FETCH"
    LOAD = "LOAD"
    STORE = "STORE"


@dataclass(frozen=True)
class PageTableEntry:
    raw: int

    @property
    def ppn(self) -> int:
        return (self.raw >> PTE_PPN_SHIFT) & PTE_PPN_MASK

    @property
    def memory_type(self) -> int:
        return (self.raw >> PTE_MT_SHIFT) & PTE_MT_MASK

    @property
    def valid(self) -> bool:
        return _bit(self.raw, PTE_V_BIT)

    @property
    def user(self) -> bool:
        return _bit(self.raw, PTE_U_BIT)

    @property
    def readable(self) -> bool:
        return _bit(self.raw, PTE_R_BIT)

    @property
    def writable(self) -> bool:
        return _bit(self.raw, PTE_W_BIT)

    @property
    def executable(self) -> bool:
        return _bit(self.raw, PTE_X_BIT)

    @property
    def global_mapping(self) -> bool:
        return _bit(self.raw, PTE_G_BIT)

    @property
    def accessed(self) -> bool:
        return _bit(self.raw, PTE_A_BIT)

    @property
    def reserved_zero(self) -> bool:
        return _bit(self.raw, PTE_RES0_BIT)

    @property
    def is_leaf(self) -> bool:
        return self.valid and (self.readable or self.writable or self.executable)

    @property
    def is_non_leaf(self) -> bool:
        return self.valid and not (self.readable or self.writable or self.executable)


@dataclass(frozen=True)
class Translation:
    virtual_address: int
    physical_address: int
    memory_type: int = MEMORY_TYPE_NORMAL_COHERENT
    global_mapping: bool = False
    user: bool = True
    readable: bool = True
    writable: bool = True
    executable: bool = True


def pte_value(
    ppn: int,
    *,
    valid: bool = True,
    user: bool = False,
    read: bool = False,
    write: bool = False,
    execute: bool = False,
    global_mapping: bool = False,
    accessed: bool = False,
    software: bool = False,
    memory_type: int = MEMORY_TYPE_NORMAL_COHERENT,
    reserved_zero: bool = False,
) -> int:
    """Pack a 48-bit PTE value for tests and software model setup."""
    ppn = csrs.require_uint(ppn, PTE_PPN_BITS, "ppn")
    memory_type = csrs.require_uint(memory_type, PTE_MT_BITS, "memory_type")
    value = ppn << PTE_PPN_SHIFT
    value |= int(bool(valid)) << PTE_V_BIT
    value |= int(bool(user)) << PTE_U_BIT
    value |= int(bool(read)) << PTE_R_BIT
    value |= int(bool(write)) << PTE_W_BIT
    value |= int(bool(execute)) << PTE_X_BIT
    value |= int(bool(global_mapping)) << PTE_G_BIT
    value |= int(bool(accessed)) << PTE_A_BIT
    value |= int(bool(software)) << PTE_SW_BIT
    value |= memory_type << PTE_MT_SHIFT
    value |= int(bool(reserved_zero)) << PTE_RES0_BIT
    return value


def translate(
    core: CoreState,
    memory: TaggedMemory,
    virtual_address: int,
    access_type: AccessType,
    location: InstructionLocation,
) -> Translation | FaultPacket:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    access_type = AccessType(access_type)
    satp = core.read_csr(csrs.CSR_SATP)
    mode = csrs.satp_mode(satp)
    if mode == csrs.SATP_MODE_BARE:
        return Translation(virtual_address, virtual_address)
    if mode != csrs.SATP_MODE_RADIX4:
        return _page_fault(location, virtual_address)
    tlb_hit = _tlb_lookup(core, satp, virtual_address, access_type, location)
    if tlb_hit is not None:
        return tlb_hit
    return _radix4_translate(core, memory, satp, virtual_address, access_type, location)


def _radix4_translate(
    core: CoreState,
    memory: TaggedMemory,
    satp: int,
    virtual_address: int,
    access_type: AccessType,
    location: InstructionLocation,
) -> Translation | FaultPacket:
    table_base = csrs.satp_root_ppn(satp) << csrs.SATP_ROOT_PPN_SHIFT
    vpn = vpn_from_address(virtual_address)
    asid = csrs.satp_asid(satp)
    tlb_kind = _tlb_kind(access_type)
    for level, index in enumerate(vpn_indexes(virtual_address)):
        pte_address = table_base + (index * PTE_SIZE_CELLS)
        try:
            pte = PageTableEntry(memory.ld48(pte_address))
        except MemoryAccessError:
            return _page_fault(location, virtual_address)

        fault = _validate_pte(core, pte, level, access_type, location, virtual_address)
        if fault is not None:
            return fault
        if pte.is_leaf:
            physical = (pte.ppn << csrs.SATP_ROOT_PPN_SHIFT) | (
                virtual_address & PAGE_OFFSET_MASK
            )
            if physical >= ADDRESS_SPACE_CELLS:
                return _page_fault(location, virtual_address)
            core.tlbs.insert(
                TlbEntry(
                    kind=tlb_kind,
                    mode=csrs.SATP_MODE_RADIX4,
                    vpn=vpn,
                    asid=asid,
                    ppn=pte.ppn,
                    user=pte.user,
                    readable=pte.readable,
                    writable=pte.writable,
                    executable=pte.executable,
                    memory_type=pte.memory_type,
                    global_mapping=pte.global_mapping,
                )
            )
            return Translation(
                virtual_address=virtual_address,
                physical_address=physical,
                memory_type=pte.memory_type,
                global_mapping=pte.global_mapping,
                user=pte.user,
                readable=pte.readable,
                writable=pte.writable,
                executable=pte.executable,
            )
        table_base = pte.ppn << csrs.SATP_ROOT_PPN_SHIFT
    return _page_fault(location, virtual_address)


def _tlb_lookup(
    core: CoreState,
    satp: int,
    virtual_address: int,
    access_type: AccessType,
    location: InstructionLocation,
) -> Translation | FaultPacket | None:
    mode = csrs.satp_mode(satp)
    vpn = vpn_from_address(virtual_address)
    asid = csrs.satp_asid(satp)
    entry = core.tlbs.lookup(_tlb_kind(access_type), mode, vpn, asid)
    if entry is None:
        return None
    if _is_user_mode(core) and not entry.user:
        return _page_fault(location, virtual_address)
    if not _tlb_access_allowed(entry, access_type):
        return _page_fault(location, virtual_address)
    physical = (entry.ppn << csrs.SATP_ROOT_PPN_SHIFT) | page_offset(virtual_address)
    return Translation(
        virtual_address=virtual_address,
        physical_address=physical,
        memory_type=entry.memory_type,
        global_mapping=entry.global_mapping,
        user=entry.user,
        readable=entry.readable,
        writable=entry.writable,
        executable=entry.executable,
    )


def _tlb_kind(access_type: AccessType) -> TlbKind:
    if access_type is AccessType.FETCH:
        return TlbKind.INSTRUCTION
    return TlbKind.DATA


def _tlb_access_allowed(entry: TlbEntry, access_type: AccessType) -> bool:
    if access_type is AccessType.FETCH:
        return entry.executable
    if access_type is AccessType.LOAD:
        return entry.readable
    if access_type is AccessType.STORE:
        return entry.writable
    raise AssertionError(f"unhandled access type {access_type}")


def vpn_indexes(virtual_address: int) -> tuple[int, int, int, int]:
    csrs.require_uint(virtual_address, csrs.CSR_BITS, "virtual_address")
    return tuple(
        (virtual_address >> shift) & mask
        for shift, mask in zip(VPN_INDEX_SHIFTS, VPN_INDEX_MASKS)
    )


def _validate_pte(
    core: CoreState,
    pte: PageTableEntry,
    level: int,
    access_type: AccessType,
    location: InstructionLocation,
    virtual_address: int,
) -> FaultPacket | None:
    if not pte.valid:
        return _page_fault(location, virtual_address)
    if pte.reserved_zero:
        return _page_fault(location, virtual_address)
    if pte.is_non_leaf:
        if level == 3:
            return _page_fault(location, virtual_address)
        if pte.user or pte.global_mapping or pte.accessed or pte.memory_type != 0:
            return _page_fault(location, virtual_address)
        return None
    if not pte.is_leaf:
        return _page_fault(location, virtual_address)
    if level != 3:
        return _page_fault(location, virtual_address)
    if not pte.accessed:
        return _page_fault(location, virtual_address)
    if pte.memory_type == MEMORY_TYPE_RESERVED:
        return _page_fault(location, virtual_address)
    if _is_user_mode(core) and not pte.user:
        return _page_fault(location, virtual_address)
    if not _access_allowed(pte, access_type):
        return _page_fault(location, virtual_address)
    return None


def _access_allowed(pte: PageTableEntry, access_type: AccessType) -> bool:
    if access_type is AccessType.FETCH:
        return pte.executable
    if access_type is AccessType.LOAD:
        return pte.readable
    if access_type is AccessType.STORE:
        return pte.writable
    raise AssertionError(f"unhandled access type {access_type}")


def _is_user_mode(core: CoreState) -> bool:
    return not bool(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_PRIV_BIT))


def _page_fault(location: InstructionLocation, virtual_address: int) -> FaultPacket:
    return FaultPacket(
        ExceptionCause.PAGE_FAULT,
        location,
        tval=virtual_address,
    )


def _bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))

"""Cell-addressed memory and capability-slot tag storage.

Owner stories:
- E01-S01: memory is addressed and sized in 24-bit cells.
- E03-S04: one architectural tag per naturally aligned 4-cell capability slot.
- E04-S03: `LD48`, `ST48`, `CLC`, and `CSC` memory object behavior.
- I02-S03: implementation storage primitives for memory cells and tags.
"""

from __future__ import annotations

from collections.abc import Iterable

from .capabilities import (
    Capability,
    payload_from_cells,
    payload_to_cells,
    require_uint,
)
from .cells import (
    CAPABILITY_OBJECT_CELLS,
    CELL_BITS,
    CELL_MASK,
    INTEGER_OBJECT_CELLS,
    CellRange,
    align_down,
    capability_object_range,
    cell_range,
    integer_object_range,
    is_aligned,
    require_cell_address,
    require_cell_count,
    require_cell_value,
)


INTEGER_BITS = INTEGER_OBJECT_CELLS * CELL_BITS


class MemoryAccessError(ValueError):
    """Base class for architectural memory storage primitive failures."""


class MemoryAlignmentError(MemoryAccessError):
    """Raised when a storage primitive is not naturally aligned."""


class MemoryBoundsError(MemoryAccessError):
    """Raised when a storage primitive cannot fit in the address space."""


class TaggedMemory:
    """Sparse cell memory plus out-of-band capability-slot tags.

    This is a storage model only. It deliberately does not perform capability
    authority, page translation, protected return-stack, or memory-type checks.
    """

    def __init__(self) -> None:
        self._cells: dict[int, int] = {}
        self._tagged_slots: set[int] = set()
        self._protected_ranges: list[CellRange] = []

    @staticmethod
    def capability_slot_base(address: int) -> int:
        return align_down(address, CAPABILITY_OBJECT_CELLS)

    @staticmethod
    def _check_alignment(address: int, alignment: int, opname: str) -> None:
        if not is_aligned(address, alignment):
            raise MemoryAlignmentError(
                f"{opname} address 0x{address:X} is not {alignment}-cell aligned"
            )

    @staticmethod
    def _check_integer_object(address: int, opname: str) -> None:
        try:
            integer_object_range(address)
        except ValueError as exc:
            raise MemoryBoundsError(f"{opname} range exceeds address space") from exc

    @staticmethod
    def _check_capability_object(address: int, opname: str) -> None:
        try:
            capability_object_range(address)
        except ValueError as exc:
            raise MemoryBoundsError(f"{opname} range exceeds address space") from exc

    def read_cell(self, address: int) -> int:
        address = require_cell_address(address)
        return self._cells.get(address, 0)

    def protect_range(self, base: int, length_cells: int) -> None:
        self._protected_ranges.append(cell_range(base, length_cells))

    def overlaps_protected_range(self, address: int, length_cells: int) -> bool:
        access = cell_range(address, length_cells)
        for protected_range in self._protected_ranges:
            if access.base < protected_range.top and protected_range.base < access.top:
                return True
        return False

    def write_cell(self, address: int, value: int) -> None:
        address = require_cell_address(address)
        value = require_cell_value(value)
        self._cells[address] = value
        self.clear_capability_tag(self.capability_slot_base(address))

    def write_cells(self, address: int, values: Iterable[int]) -> None:
        address = require_cell_address(address)
        value_tuple = tuple(values)
        if not value_tuple:
            return
        for offset, value in enumerate(value_tuple):
            require_cell_address(address + offset, f"address[{offset}]")
            require_cell_value(value, f"values[{offset}]")
        for offset, value in enumerate(value_tuple):
            self._cells[address + offset] = value
        self.clear_overlapped_tags(address, len(value_tuple))

    def capability_tag(self, slot_base: int) -> bool:
        slot_base = require_cell_address(slot_base, "slot_base")
        self._check_alignment(slot_base, CAPABILITY_OBJECT_CELLS, "capability tag")
        self._check_capability_object(slot_base, "capability tag")
        return slot_base in self._tagged_slots

    def clear_capability_tag(self, slot_base: int) -> None:
        slot_base = require_cell_address(slot_base, "slot_base")
        self._check_alignment(slot_base, CAPABILITY_OBJECT_CELLS, "capability tag")
        self._tagged_slots.discard(slot_base)

    def clear_overlapped_tags(self, address: int, length_cells: int) -> None:
        address = require_cell_address(address)
        length_cells = require_cell_count(length_cells, "length_cells")
        if length_cells == 0:
            return
        end_address = address + length_cells - 1
        require_cell_address(end_address, "end_address")
        first_slot = self.capability_slot_base(address)
        last_slot = self.capability_slot_base(end_address)
        for slot_base in list(self._tagged_slots):
            if not first_slot <= slot_base <= last_slot:
                continue
            self._tagged_slots.discard(slot_base)

    def ld48(self, address: int) -> int:
        address = require_cell_address(address)
        self._check_integer_object(address, "LD48")
        self._check_alignment(address, INTEGER_OBJECT_CELLS, "LD48")
        low = self.read_cell(address)
        high = self.read_cell(address + 1)
        return low | (high << CELL_BITS)

    def st48(self, address: int, value: int) -> None:
        address = require_cell_address(address)
        value = require_uint(value, INTEGER_BITS, "value")
        self._check_integer_object(address, "ST48")
        self._check_alignment(address, INTEGER_OBJECT_CELLS, "ST48")
        self._cells[address] = value & CELL_MASK
        self._cells[address + 1] = (value >> CELL_BITS) & CELL_MASK
        self.clear_capability_tag(self.capability_slot_base(address))

    def clc(self, address: int) -> Capability:
        address = require_cell_address(address)
        self._check_capability_object(address, "CLC")
        self._check_alignment(address, CAPABILITY_OBJECT_CELLS, "CLC")
        cells = tuple(
            self.read_cell(address + offset)
            for offset in range(CAPABILITY_OBJECT_CELLS)
        )
        return Capability(
            payload=payload_from_cells(cells),
            tag=self.capability_tag(address),
        )

    def csc(self, address: int, capability: Capability) -> None:
        address = require_cell_address(address)
        if not isinstance(capability, Capability):
            raise TypeError("capability must be a Capability")
        self._check_capability_object(address, "CSC")
        self._check_alignment(address, CAPABILITY_OBJECT_CELLS, "CSC")
        cells = payload_to_cells(capability.payload)
        for offset, cell in enumerate(cells):
            self._cells[address + offset] = cell
        if capability.tag:
            self._tagged_slots.add(address)
        else:
            self._tagged_slots.discard(address)

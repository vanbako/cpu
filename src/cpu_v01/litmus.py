"""Executable memory litmus support models for CPU v0.1.

Owner stories:
- E08-S03: TSO-like store-buffer behavior.
- E10-S03: coherent payload/tag visibility through the CPU coherence point.
- E10-S04: noncoherent, tag-unaware DMA behavior.
- E10-S05: cache maintenance effects used by DMA sequences.
- I06-S04: architectural memory-ordering and cache/DMA litmus model.

These helpers are architectural litmus models, not a cycle-accurate cache
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .capabilities import Capability, payload_from_cells, payload_to_cells
from .cells import (
    CACHE_LINE_CELLS,
    CAPABILITY_OBJECT_CELLS,
    CELL_BITS,
    CELL_MASK,
    INTEGER_OBJECT_CELLS,
)


INTEGER_MASK = (1 << (INTEGER_OBJECT_CELLS * CELL_BITS)) - 1


@dataclass(frozen=True)
class StoreBufferEntry:
    address: int
    value: int


class TsoMemoryModel:
    """Small FIFO store-buffer model for scalar TSO litmus tests."""

    def __init__(self, core_count: int = 2) -> None:
        if type(core_count) is not int:
            raise TypeError("core_count must be an int")
        if core_count <= 0:
            raise ValueError("core_count must be positive")
        self._memory: dict[int, int] = {}
        self._store_buffers: list[list[StoreBufferEntry]] = [
            [] for _ in range(core_count)
        ]

    def st48(self, core: int, address: int, value: int) -> None:
        core = self._core_index(core)
        self._store_buffers[core].append(
            StoreBufferEntry(address, value & INTEGER_MASK)
        )

    def ld48(self, core: int, address: int) -> int:
        core = self._core_index(core)
        for entry in reversed(self._store_buffers[core]):
            if entry.address == address:
                return entry.value
        return self._memory.get(address, 0)

    def drain_one(self, core: int) -> bool:
        core = self._core_index(core)
        if not self._store_buffers[core]:
            return False
        entry = self._store_buffers[core].pop(0)
        self._memory[entry.address] = entry.value
        return True

    def fence(self, core: int) -> None:
        core = self._core_index(core)
        while self.drain_one(core):
            pass

    def visible_value(self, address: int) -> int:
        return self._memory.get(address, 0)

    def pending_count(self, core: int) -> int:
        return len(self._store_buffers[self._core_index(core)])

    def _core_index(self, core: int) -> int:
        if type(core) is not int:
            raise TypeError("core must be an int")
        if not 0 <= core < len(self._store_buffers):
            raise IndexError("core index out of range")
        return core


@dataclass
class CacheLine:
    base: int
    cells: list[int] = field(default_factory=lambda: [0] * CACHE_LINE_CELLS)
    tags: list[bool] = field(
        default_factory=lambda: [False]
        * (CACHE_LINE_CELLS // CAPABILITY_OBJECT_CELLS)
    )
    dirty: bool = False

    def clone(self) -> "CacheLine":
        return CacheLine(
            base=self.base,
            cells=list(self.cells),
            tags=list(self.tags),
            dirty=self.dirty,
        )


class CacheDmaModel:
    """Line-granular tag/cache model for cache and DMA litmus tests."""

    def __init__(self, core_count: int = 2) -> None:
        if type(core_count) is not int:
            raise TypeError("core_count must be an int")
        if core_count <= 0:
            raise ValueError("core_count must be positive")
        self.memory: dict[int, CacheLine] = {}
        self.l2: dict[int, CacheLine] = {}
        self.l1d: list[dict[int, CacheLine]] = [dict() for _ in range(core_count)]

    @staticmethod
    def line_base(address: int) -> int:
        return address - (address % CACHE_LINE_CELLS)

    @staticmethod
    def line_offset(address: int) -> int:
        return address % CACHE_LINE_CELLS

    @staticmethod
    def cap_slot_index(address: int) -> int:
        return (address % CACHE_LINE_CELLS) // CAPABILITY_OBJECT_CELLS

    def clc(self, core: int, address: int) -> Capability:
        self._require_aligned(address, CAPABILITY_OBJECT_CELLS, "CLC")
        line = self._l1_line(core, address)
        offset = self.line_offset(address)
        cells = tuple(
            line.cells[offset + index]
            for index in range(CAPABILITY_OBJECT_CELLS)
        )
        return Capability(
            payload_from_cells(cells),
            line.tags[self.cap_slot_index(address)],
        )

    def csc(self, core: int, address: int, capability: Capability) -> None:
        self._require_aligned(address, CAPABILITY_OBJECT_CELLS, "CSC")
        if not isinstance(capability, Capability):
            raise TypeError("capability must be a Capability")
        line = self._exclusive_line(core, address)
        offset = self.line_offset(address)
        for index, cell in enumerate(payload_to_cells(capability.payload)):
            line.cells[offset + index] = cell
        line.tags[self.cap_slot_index(address)] = bool(capability.tag)
        line.dirty = True
        self._publish_l1_to_l2(line)

    def ld48(self, core: int, address: int) -> int:
        self._require_aligned(address, INTEGER_OBJECT_CELLS, "LD48")
        line = self._l1_line(core, address)
        offset = self.line_offset(address)
        return line.cells[offset] | (line.cells[offset + 1] << CELL_BITS)

    def st48(self, core: int, address: int, value: int) -> None:
        self._require_aligned(address, INTEGER_OBJECT_CELLS, "ST48")
        line = self._exclusive_line(core, address)
        offset = self.line_offset(address)
        line.cells[offset] = value & CELL_MASK
        line.cells[offset + 1] = (value >> CELL_BITS) & CELL_MASK
        for cell_address in range(address, address + INTEGER_OBJECT_CELLS):
            line.tags[self.cap_slot_index(cell_address)] = False
        line.dirty = True
        self._publish_l1_to_l2(line)

    def cache_clean(self, address: int) -> None:
        base = self.line_base(address)
        if base in self.l2:
            self.memory[base] = self.l2[base].clone()
            self.memory[base].dirty = False
            self.l2[base].dirty = False

    def cache_inval(self, address: int) -> None:
        base = self.line_base(address)
        for cache in self.l1d:
            cache.pop(base, None)
        self.l2.pop(base, None)

    def cache_cleaninval(self, address: int) -> None:
        self.cache_clean(address)
        self.cache_inval(address)

    def dma_read_cells(self, address: int, length_cells: int) -> tuple[int, ...]:
        return tuple(
            self._memory_cell(address + offset)
            for offset in range(length_cells)
        )

    def dma_write_cells(self, address: int, values: tuple[int, ...]) -> None:
        for offset, value in enumerate(values):
            cell_address = address + offset
            line = self._memory_line(self.line_base(cell_address))
            line.cells[self.line_offset(cell_address)] = value & CELL_MASK
            line.tags[self.cap_slot_index(cell_address)] = False

    def memory_capability_tag(self, address: int) -> bool:
        self._require_aligned(address, CAPABILITY_OBJECT_CELLS, "tag query")
        line = self._memory_line(self.line_base(address))
        return line.tags[self.cap_slot_index(address)]

    def _exclusive_line(self, core: int, address: int) -> CacheLine:
        core = self._core_index(core)
        base = self.line_base(address)
        for other_core, cache in enumerate(self.l1d):
            if other_core != core:
                cache.pop(base, None)
        return self._l1_line(core, address)

    def _l1_line(self, core: int, address: int) -> CacheLine:
        core = self._core_index(core)
        base = self.line_base(address)
        if base not in self.l1d[core]:
            self.l1d[core][base] = self._l2_line(base).clone()
        return self.l1d[core][base]

    def _l2_line(self, base: int) -> CacheLine:
        if base not in self.l2:
            self.l2[base] = self._memory_line(base).clone()
        return self.l2[base]

    def _memory_line(self, base: int) -> CacheLine:
        if base not in self.memory:
            self.memory[base] = CacheLine(base)
        return self.memory[base]

    def _memory_cell(self, address: int) -> int:
        return self._memory_line(self.line_base(address)).cells[self.line_offset(address)]

    def _publish_l1_to_l2(self, line: CacheLine) -> None:
        self.l2[line.base] = line.clone()
        self.l2[line.base].dirty = True

    def _core_index(self, core: int) -> int:
        if type(core) is not int:
            raise TypeError("core must be an int")
        if not 0 <= core < len(self.l1d):
            raise IndexError("core index out of range")
        return core

    @staticmethod
    def _require_aligned(address: int, alignment: int, opname: str) -> None:
        if address % alignment != 0:
            raise ValueError(f"{opname} address is not aligned")

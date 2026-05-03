#!/usr/bin/env python3
"""Prototype capability tag movement through L1, L2, and memory.

This is a spike prototype for E14-S04, not a cycle-accurate cache model.
It models the architectural tag rules that matter for v0.1:

- 16-cell cache lines.
- 4-cell naturally aligned capability slots.
- Tag granularity is one tag per 4-cell capability slot.
- `CLC` and `CSC` move a whole capability slot and tag atomically.
- `ST48` writes two cells and clears any overlapped capability-slot tag.
- CPU writes are visible through the shared L2 coherence point.
- Noncoherent DMA writes memory behind the CPU caches and clear memory tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field


LINE_CELLS = 16
CAP_CELLS = 4
WORD_CELLS = 2
SLOTS_PER_LINE = LINE_CELLS // CAP_CELLS
CELL_MASK = (1 << 24) - 1


class ModelError(ValueError):
    """Raised when the prototype is used with invalid alignment or addresses."""


@dataclass
class CacheLine:
    base: int
    cells: list[int] = field(default_factory=lambda: [0] * LINE_CELLS)
    tags: list[bool] = field(default_factory=lambda: [False] * SLOTS_PER_LINE)
    dirty: bool = False

    def clone(self) -> "CacheLine":
        return CacheLine(
            base=self.base,
            cells=list(self.cells),
            tags=list(self.tags),
            dirty=self.dirty,
        )

    def tag_string(self) -> str:
        return "".join("T" if tag else "." for tag in self.tags)


class TagCacheModel:
    def __init__(self, cores: int = 2) -> None:
        self.memory: dict[int, CacheLine] = {}
        self.l2: dict[int, CacheLine] = {}
        self.l1d: list[dict[int, CacheLine]] = [dict() for _ in range(cores)]
        self.events: list[str] = []

    @staticmethod
    def line_base(address: int) -> int:
        return address & ~(LINE_CELLS - 1)

    @staticmethod
    def line_offset(address: int) -> int:
        return address & (LINE_CELLS - 1)

    @staticmethod
    def cap_slot_base(address: int) -> int:
        return address & ~(CAP_CELLS - 1)

    @staticmethod
    def cap_slot_index(address: int) -> int:
        return (address & (LINE_CELLS - 1)) // CAP_CELLS

    @staticmethod
    def _check_aligned(address: int, alignment: int, opname: str) -> None:
        if address % alignment:
            raise ModelError(f"{opname} address 0x{address:X} is not {alignment}-cell aligned")

    def _memory_line(self, base: int) -> CacheLine:
        if base not in self.memory:
            self.memory[base] = CacheLine(base=base)
        return self.memory[base]

    def _l2_line(self, base: int) -> CacheLine:
        if base not in self.l2:
            self.l2[base] = self._memory_line(base).clone()
            self.events.append(f"L2 fill line 0x{base:X} from memory")
        return self.l2[base]

    def _l1_line(self, core: int, address: int) -> CacheLine:
        base = self.line_base(address)
        if base not in self.l1d[core]:
            self.l1d[core][base] = self._l2_line(base).clone()
            self.events.append(f"core{core} L1D fill line 0x{base:X} from L2")
        return self.l1d[core][base]

    def _invalidate_other_l1s(self, writer_core: int, base: int) -> None:
        for core, cache in enumerate(self.l1d):
            if core == writer_core:
                continue
            if base in cache:
                del cache[base]
                self.events.append(f"core{writer_core} invalidates core{core} L1D line 0x{base:X}")

    def _publish_l1_to_l2(self, core: int, line: CacheLine) -> None:
        self.l2[line.base] = line.clone()
        self.l2[line.base].dirty = True
        self.events.append(f"core{core} publishes line 0x{line.base:X} to L2")

    def clean_line_to_memory(self, address: int) -> None:
        base = self.line_base(address)
        if base in self.l2:
            self.memory[base] = self.l2[base].clone()
            self.memory[base].dirty = False
            self.l2[base].dirty = False
            self.events.append(f"clean line 0x{base:X} from L2 to memory")

    def invalidate_cpu_line(self, address: int) -> None:
        base = self.line_base(address)
        for core, cache in enumerate(self.l1d):
            if base in cache:
                del cache[base]
                self.events.append(f"invalidate core{core} L1D line 0x{base:X}")
        if base in self.l2:
            del self.l2[base]
            self.events.append(f"invalidate L2 line 0x{base:X}")

    def csc(self, core: int, address: int, payload: tuple[int, int, int, int], tag: bool) -> None:
        self._check_aligned(address, CAP_CELLS, "CSC")
        base = self.line_base(address)
        offset = self.line_offset(address)
        slot = self.cap_slot_index(address)
        self._invalidate_other_l1s(core, base)
        line = self._l1_line(core, address)
        for index, value in enumerate(payload):
            line.cells[offset + index] = value & CELL_MASK
        line.tags[slot] = tag
        line.dirty = True
        self._publish_l1_to_l2(core, line)
        self.events.append(f"core{core} CSC slot 0x{address:X} tag={tag}")

    def clc(self, core: int, address: int) -> tuple[tuple[int, int, int, int], bool]:
        self._check_aligned(address, CAP_CELLS, "CLC")
        offset = self.line_offset(address)
        slot = self.cap_slot_index(address)
        line = self._l1_line(core, address)
        payload = tuple(line.cells[offset + index] for index in range(CAP_CELLS))
        tag = line.tags[slot]
        self.events.append(f"core{core} CLC slot 0x{address:X} tag={tag}")
        return payload, tag

    def st48(self, core: int, address: int, payload: tuple[int, int]) -> None:
        self._check_aligned(address, WORD_CELLS, "ST48")
        base = self.line_base(address)
        offset = self.line_offset(address)
        if offset + WORD_CELLS > LINE_CELLS:
            raise ModelError("ST48 crossing a cache line is impossible when 2-cell aligned")
        self._invalidate_other_l1s(core, base)
        line = self._l1_line(core, address)
        for index, value in enumerate(payload):
            line.cells[offset + index] = value & CELL_MASK
        for cell_address in range(address, address + WORD_CELLS):
            slot = self.cap_slot_index(cell_address)
            line.tags[slot] = False
        line.dirty = True
        self._publish_l1_to_l2(core, line)
        self.events.append(f"core{core} ST48 0x{address:X} clears overlapped capability tag")

    def dma_overwrite(self, address: int, payload: list[int]) -> None:
        for index, value in enumerate(payload):
            cell_address = address + index
            base = self.line_base(cell_address)
            offset = self.line_offset(cell_address)
            line = self._memory_line(base)
            line.cells[offset] = value & CELL_MASK
            line.tags[self.cap_slot_index(cell_address)] = False
        self.events.append(
            f"DMA overwrite [{address:#x}, {address + len(payload):#x}) in memory and clear overlapped tags"
        )

    def line_tags(self, level: str, address: int, core: int | None = None) -> str:
        base = self.line_base(address)
        if level == "memory":
            return self._memory_line(base).tag_string()
        if level == "l2":
            return self._l2_line(base).tag_string()
        if level == "l1":
            if core is None:
                raise ModelError("core is required for l1 tag query")
            return self._l1_line(core, address).tag_string()
        raise ModelError(f"unknown level: {level}")


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def run_scenarios() -> list[tuple[str, str]]:
    model = TagCacheModel(cores=2)
    results: list[tuple[str, str]] = []
    cap_a = (0xCA0001, 0xCA0002, 0xCA0003, 0xCA0004)
    cap_b = (0xCB0001, 0xCB0002, 0xCB0003, 0xCB0004)

    payload, tag = model.clc(1, 0x1000)
    assert_equal(tag, False, "cold CLC tag")
    results.append(("cold CLC", "untagged slot observed before CSC"))

    model.csc(0, 0x1000, cap_a, True)
    payload, tag = model.clc(1, 0x1000)
    assert_equal(payload, cap_a, "CSC payload visibility")
    assert_equal(tag, True, "CSC tag visibility")
    results.append(("CSC atomic visibility", "core1 sees full payload and tag from core0 through L2"))

    model.csc(0, 0x1004, cap_b, True)
    model.st48(0, 0x1002, (0xDD0001, 0xDD0002))
    _, tag0 = model.clc(1, 0x1000)
    _, tag1 = model.clc(1, 0x1004)
    assert_equal(tag0, False, "ST48 clears overlapped slot")
    assert_equal(tag1, True, "ST48 does not clear adjacent slot")
    results.append(("ST48 tag clear", "partial overwrite clears only the overlapped 4-cell slot tag"))

    model.clean_line_to_memory(0x1000)
    model.dma_overwrite(0x1004, [0xE0, 0xE1, 0xE2, 0xE3])
    cached_payload, cached_tag = model.clc(1, 0x1004)
    assert_equal(cached_payload, cap_b, "stale cache before DMA invalidation")
    assert_equal(cached_tag, True, "stale tag before DMA invalidation")
    model.invalidate_cpu_line(0x1004)
    dma_payload, dma_tag = model.clc(1, 0x1004)
    assert_equal(dma_payload, (0xE0, 0xE1, 0xE2, 0xE3), "DMA payload after invalidation")
    assert_equal(dma_tag, False, "DMA clears memory tag")
    results.append(("noncoherent DMA", "CPU sees DMA-cleared tag only after cache invalidation"))

    assert_equal(model.line_tags("memory", 0x1000), "....", "final memory tags")
    results.append(("tag granularity", "one tag per naturally aligned 4-cell capability slot"))
    return results


def main() -> None:
    results = run_scenarios()
    print("Capability tag cache hierarchy prototype")
    print(f"line size: {LINE_CELLS} cells")
    print(f"capability slot: {CAP_CELLS} cells")
    print()
    print("| scenario | result |")
    print("| --- | --- |")
    for name, result in results:
        print(f"| {name} | {result} |")


if __name__ == "__main__":
    main()

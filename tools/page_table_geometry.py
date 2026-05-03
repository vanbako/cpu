#!/usr/bin/env python3
"""Prototype page-table geometry for CPU v0.1.

This is a spike prototype for E14-S03. It validates the base-page
radix geometry implied by:

- 48-bit cell virtual addresses.
- 2^11 cell base pages.
- 48-bit PTEs occupying 2 cells.
- Page-table pages of 2^11 cells.
"""

from __future__ import annotations

from dataclasses import dataclass


VA_BITS = 48
PAGE_OFFSET_BITS = 11
PTE_CELLS = 2
PAGE_CELLS = 1 << PAGE_OFFSET_BITS
PTE_PER_PAGE = PAGE_CELLS // PTE_CELLS
PTE_INDEX_BITS = PTE_PER_PAGE.bit_length() - 1
VPN_BITS = VA_BITS - PAGE_OFFSET_BITS
VPN_SPLIT = [7, 10, 10, 10]


@dataclass(frozen=True)
class Translation:
    va: int
    vpn: int
    offset: int
    indexes: tuple[int, int, int, int]


def translate_indexes(va: int) -> Translation:
    if not 0 <= va < (1 << VA_BITS):
        raise ValueError(f"VA out of range: 0x{va:X}")

    offset = va & ((1 << PAGE_OFFSET_BITS) - 1)
    vpn = va >> PAGE_OFFSET_BITS
    remaining = vpn
    indexes_reversed = []
    for bits in reversed(VPN_SPLIT):
        indexes_reversed.append(remaining & ((1 << bits) - 1))
        remaining >>= bits
    indexes = tuple(reversed(indexes_reversed))
    assert remaining == 0
    return Translation(va=va, vpn=vpn, offset=offset, indexes=indexes)


def level_leaf_page_bits() -> list[tuple[str, int]]:
    """Return natural leaf sizes if each level allowed leaf PTEs."""
    levels = []
    for level in range(len(VPN_SPLIT)):
        lower_index_bits = sum(VPN_SPLIT[level + 1 :])
        page_bits = PAGE_OFFSET_BITS + lower_index_bits
        levels.append((f"L{level}", page_bits))
    return levels


def run_checks() -> dict[str, object]:
    assert PTE_PER_PAGE == 1024
    assert PTE_INDEX_BITS == 10
    assert VPN_BITS == sum(VPN_SPLIT)

    samples = [
        0x0,
        0x7FF,
        0x800,
        0x1234_5678_9ABC,
        (1 << VA_BITS) - 1,
    ]
    translations = [translate_indexes(va) for va in samples]

    natural_large_pages = level_leaf_page_bits()
    reserved = [15, 19]
    natural_bits = {bits for _, bits in natural_large_pages}
    reserved_analysis = {
        bits: "natural" if bits in natural_bits else "not natural"
        for bits in reserved
    }

    return {
        "pte_per_page": PTE_PER_PAGE,
        "pte_index_bits": PTE_INDEX_BITS,
        "vpn_bits": VPN_BITS,
        "vpn_split": VPN_SPLIT,
        "translations": translations,
        "natural_large_pages": natural_large_pages,
        "reserved_analysis": reserved_analysis,
    }


def main() -> None:
    result = run_checks()

    print("Page-table geometry prototype")
    print(f"VA bits: {VA_BITS}")
    print(f"base page: 2^{PAGE_OFFSET_BITS} cells")
    print(f"PTE size: {PTE_CELLS} cells")
    print(f"PTEs per page-table page: {result['pte_per_page']}")
    print(f"VPN bits: {result['vpn_bits']}")
    print(f"VPN split: {' + '.join(str(bits) for bits in result['vpn_split'])}")
    print()

    print("| VA | L0 | L1 | L2 | L3 | offset |")
    print("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for t in result["translations"]:
        l0, l1, l2, l3 = t.indexes
        print(f"| 0x{t.va:X} | {l0} | {l1} | {l2} | {l3} | 0x{t.offset:X} |")

    print()
    print("| potential leaf level | natural page size |")
    print("| --- | ---: |")
    for level, bits in result["natural_large_pages"]:
        print(f"| {level} | 2^{bits} cells |")

    print()
    print("| reserved future page size | fit with simple radix leaf? |")
    print("| ---: | --- |")
    for bits, status in result["reserved_analysis"].items():
        print(f"| 2^{bits} cells | {status} |")


if __name__ == "__main__":
    main()

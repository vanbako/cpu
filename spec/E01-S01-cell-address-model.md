# E01-S01: 24-bit Cell Address Model

Story: E01-S01

Status: Complete

Normative source: `design.md`, section 2

## Decision

The CPU v0.1 architecture is cell-addressed.

A **cell** is exactly 24 bits. Every architectural memory address names a cell, not a byte. All architectural memory ranges, page sizes, cache lines, object sizes, and pointer arithmetic are counted in cells.

## Address Rules

| Rule | Definition |
| --- | --- |
| Cell size | 1 cell = 24 bits |
| Address unit | 1 architectural address step = 1 cell |
| Address space | 48-bit cell addresses, giving `2^48` addressable cells |
| Memory range | `[base, top)` contains `top - base` cells |
| Alignment | Address `A` is `N`-cell aligned when `A mod N = 0` |
| Byte addressing | No architectural byte addresses exist in v0.1 |

## Object Sizes

| Object | Size in cells | Size in bits | Alignment |
| --- | ---: | ---: | ---: |
| Cell | 1 | 24 | 1 cell |
| 48-bit integer memory object | 2 | 48 | 2 cells |
| 96-bit capability memory object | 4 | 96 plus tag | 4 cells |
| Fetch group | 2 | 48 | 2 cells |
| Base page | `2^11` | 49152 | `2^11` cells |
| Initial cache line | 16 | 384 | 16 cells |

## Address Arithmetic Examples

| Expression | Meaning |
| --- | --- |
| `A + 1` | Next 24-bit cell |
| `A + 2` | Next aligned 48-bit integer slot when `A` is 2-cell aligned |
| `A + 4` | Next aligned 96-bit capability slot when `A` is 4-cell aligned |
| `[0x1000, 0x1800)` | One base page, because the range is `0x800` cells |
| Cache line containing `A` | Starts at `floor(A / 16) * 16` for a 16-cell line |

## Alignment Examples

| Address | 2-cell aligned | 4-cell aligned | 16-cell aligned |
| ---: | --- | --- | --- |
| `0x1000` | yes | yes | yes |
| `0x1001` | no | no | no |
| `0x1002` | yes | no | no |
| `0x1004` | yes | yes | no |
| `0x1010` | yes | yes | yes |

## Toolchain and ABI Implications

This choice is intentionally nonstandard. A normal byte-addressed ABI cannot be reused unchanged.

Required custom handling:

- Assembler and disassembler address labels are cell addresses.
- Linker layout must allocate sections in cell units.
- Debug information must describe program counters and memory locations in cell units.
- The ABI must define stack layout, argument spill areas, and object alignment in cells.
- Loader and kernel page-table code must use cell counts for virtual and physical ranges.
- Any external binary container that stores bytes must define how 24-bit cells are serialized.

Sub-cell values can exist in registers and instruction encodings, but v0.1 memory addressing does not expose byte or sub-cell locations. A future byte or sub-cell memory extension would need separate rules for packing, extension, tag clearing, alignment, and page permission interaction.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Address increment by 1 advances one 24-bit cell.
- `LD48` and `ST48` reject odd cell addresses.
- `CLC` and `CSC` reject addresses that are not 4-cell aligned.
- Fetch groups start on 2-cell boundaries.
- Base page translation uses `2^11` cells per page.
- Cache-line indexing uses cell address bits, not byte address bits.
- Capability bounds checks compare cell addresses against cell-counted ranges.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `cell` is defined as exactly 24 bits. | Met in `design.md` section 2 and this artifact. |
| All architectural addresses are defined as cell addresses, not byte addresses. | Met. |
| 48-bit integer objects are defined as 2 aligned cells. | Met. |
| 96-bit capability objects are defined as 4 aligned cells. | Met. |
| Fetch groups, pages, and cache lines are described in cells. | Met. |
| The spec explicitly states that this implies a custom toolchain and ABI. | Met. |


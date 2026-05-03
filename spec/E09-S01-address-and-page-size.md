# E09-S01: Address Sizes and Page Size

Story: E09-S01

Status: Complete

Normative source: `design.md`, sections 12.1 and 12.2

Prerequisite: `spec/E01-S01-cell-address-model.md`

## Decision

CPU v0.1 uses 48-bit virtual and physical cell addresses.

The mandatory v0.1 page size is `2^11` cells.

## Address Sizes

| Address type | Width | Unit | Addressable range |
| --- | ---: | --- | --- |
| Virtual address | 48 bits | Cell | `2^48` virtual cells |
| Physical address | 48 bits | Cell | `2^48` physical cells |

Address translation maps virtual page numbers to physical page numbers and preserves the page offset.

## Base Page Size

| Property | Value |
| --- | ---: |
| Base page size | `2^11` cells |
| Base page cells | 2048 |
| Page offset width | 11 cell-address bits |
| VPN width | 37 bits |
| PPN width | 37 bits |
| Serialized page storage | 49152 bits = 6144 octets |

The 6144-octet serialization size does not introduce byte-addressed memory. It only describes how many octets are needed to store a page image in a conventional external file or host tool.

## Future Page Sizes

Reserved but not implemented in v0.1:

- `2^15` cells
- `2^19` cells

These sizes are reserved for encoding and software planning only. They are not valid v0.1 leaf page sizes until the page-table walker behavior is defined in E09-S04 or a later architecture revision.

## Address Breakdown

For a 48-bit cell virtual address and `2^11` cell base page:

```text
VA[47:11] = VPN[36:0]
VA[10:0]  = page offset in cells
```

For a 48-bit cell physical address:

```text
PA[47:11] = PPN[36:0]
PA[10:0]  = page offset in cells
```

## Examples

| Address | VPN/PPN | Page offset |
| ---: | ---: | ---: |
| `0x0000_0000_0000` | `0x0` | `0x000` |
| `0x0000_0000_07FF` | `0x0` | `0x7FF` |
| `0x0000_0000_0800` | `0x1` | `0x000` |
| `0x0000_0000_1001` | `0x2` | `0x001` |

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Virtual addresses are interpreted as 48-bit cell addresses.
- Physical addresses are interpreted as 48-bit cell addresses.
- Page offset is the low 11 cell-address bits.
- VPN extraction uses bits `[47:11]`.
- PPN insertion preserves the low 11-bit page offset.
- `2^15` and `2^19` cell pages are rejected or reserved in v0.1 walker tests.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Virtual addresses are 48-bit cell addresses. | Met. |
| Physical addresses are 48-bit cell addresses. | Met. |
| MVP page size is `2^11` cells. | Met. |
| Future page sizes `2^15` and `2^19` cells are reserved but not implemented in v0.1. | Met. |


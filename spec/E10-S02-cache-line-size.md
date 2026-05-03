# E10-S02: Cache Line Unit and Size

Story: E10-S02

Status: Complete

Normative source: `design.md`, section 13

Prerequisite: `spec/E01-S01-cell-address-model.md`

## Decision

CPU v0.1 cache lines are counted in cells, not bytes.

The MVP cache line size is 16 cells.

```text
16 cells = 384 bits = 48 octets when serialized externally
```

The 48-octet equivalence does not introduce byte addressing. Architectural addresses remain cell addresses.

## Address Breakdown

For a 16-cell line:

| Field | Cell-address bits |
| --- | --- |
| Line offset | Low 4 bits |
| Line base | `address & ~0xF` |
| Line index | Implementation-defined bits above offset |
| Tag | Implementation-defined high address bits |

## Alignment Examples

| Cell address | Line base | Cell offset |
| ---: | ---: | ---: |
| `0x1000` | `0x1000` | `0x0` |
| `0x1001` | `0x1000` | `0x1` |
| `0x100F` | `0x1000` | `0xF` |
| `0x1010` | `0x1010` | `0x0` |

## Object Capacity

One 16-cell cache line can hold:

| Object | Object size | Naturally aligned objects per line |
| --- | ---: | ---: |
| 24-bit cell | 1 cell | 16 |
| 48-bit integer slot | 2 cells | 8 |
| 96-bit capability slot | 4 cells plus tag | 4 |
| 48-bit fetch group | 2 cells | 8 |

Capability tags are associated with capability slots, not with byte lanes.

## Boundary Rules

- A naturally aligned 48-bit integer slot cannot cross a 16-cell line boundary.
- A naturally aligned 96-bit capability slot cannot cross a 16-cell line boundary.
- A 48-bit fetch group cannot cross a 16-cell line boundary when fetch-group alignment is respected.
- Cache maintenance ranges are expressed in cell addresses.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Line base is `address & ~0xF`.
- Offset for `0x100F` is `0xF`.
- Offset for `0x1010` is `0x0`.
- A line contains four 4-cell capability slots.
- A line contains eight 2-cell integer slots.
- Cache indexing uses cell address bits, not byte address bits.
- Cache-line serialization as 48 octets does not permit byte-addressed loads or stores.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Cache lines are counted in cells, not bytes. | Met. |
| MVP cache line size is 16 cells. | Met. |
| 16 cells are identified as 48 bytes. | Met as 48 octets of storage when serialized externally. |
| Alignment and index implications are documented. | Met. |


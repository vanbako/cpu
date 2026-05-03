# E09-S04: Page-table Geometry

Story: E09-S04

Status: Complete

Normative source: `design.md`, section 12.5

Prerequisite: `spec/E09-S01-address-and-page-size.md`

Supporting spike: `spikes/E14-S03-page-table-geometry.md`

## Decision

CPU v0.1 uses a 4-level radix page table for 48-bit cell virtual addresses.

Only `2^11` cell base pages are valid v0.1 leaf mappings. Large page sizes are reserved for future architecture revisions, but are not implemented in v0.1.

## Page-table Page Geometry

| Property | Value |
| --- | ---: |
| Page-table page size | `2^11` cells |
| Page-table page cells | 2048 |
| PTE size | 48 bits = 2 cells |
| PTEs per page-table page | 1024 |
| Full-level index width | 10 bits |
| VPN width | 37 bits |
| Page offset width | 11 bits |

Page-table pages are addressed by physical cell addresses and must be aligned to `2^11` cells.

A PTE slot in a page-table page is selected by index:

```text
PTE cell address = table_base + index * 2
```

Because PTEs occupy 2 cells and page-table pages are `2^11` cell aligned, every PTE slot is naturally 2-cell aligned.

PTEs are scalar MMU data. Capability tags in page-table memory are not interpreted by the page-table walker.

## VPN Split

The 37-bit VPN is split across four levels as:

```text
VPN split = 7 + 10 + 10 + 10
```

| Field | VA bits | Width | Index range |
| --- | --- | ---: | ---: |
| L0 index | `VA[47:41]` | 7 bits | `0-127` |
| L1 index | `VA[40:31]` | 10 bits | `0-1023` |
| L2 index | `VA[30:21]` | 10 bits | `0-1023` |
| L3 index | `VA[20:11]` | 10 bits | `0-1023` |
| Page offset | `VA[10:0]` | 11 bits | `0-2047` |

The root L0 page table is still one full page-table page with 1024 PTE slots. Only indexes `0-127` are reachable by a valid 48-bit virtual address in v0.1. L0 entries `128-1023` are architecturally unreachable and should be treated as reserved software storage; a conforming walker never indexes them.

## Walk Structure

A valid v0.1 base-page translation uses one PTE from each level:

1. L0 PTE selected by `VA[47:41]`.
2. L1 PTE selected by `VA[40:31]`.
3. L2 PTE selected by `VA[30:21]`.
4. L3 PTE selected by `VA[20:11]`.

L0, L1, and L2 PTEs are non-leaf table pointers.

L3 is the only valid leaf level in v0.1. A successful L3 leaf maps one `2^11` cell base page and preserves the page offset:

```text
PA[47:11] = leaf PPN[36:0]
PA[10:0]  = VA[10:0]
```

The exact PTE bit layout, valid/non-leaf/leaf encoding, permission bits, accessed-bit behavior, and reserved-bit fault behavior are defined by E09-S05.

## Large-page Reservation

The future page sizes reserved by E09-S01 are:

- `2^15` cells
- `2^19` cells

These sizes do not match the simple higher-level leaf geometry of this 4-level radix table.

If higher-level leaf PTEs were allowed without extra mechanisms, the natural page sizes would be:

| Leaf level | Natural page size |
| --- | ---: |
| L0 | `2^41` cells |
| L1 | `2^31` cells |
| L2 | `2^21` cells |
| L3 | `2^11` cells |

For v0.1:

- L0, L1, and L2 leaf mappings are invalid.
- `2^15` and `2^19` cell large-page encodings are reserved and invalid.
- No contiguous-PTE large-page mechanism is defined.
- No alternate walker mode for non-natural large pages is defined.

Future revisions may define natural radix large pages, contiguous-PTE large pages, or another walker mode. Those mechanisms must remain compatible with the v0.1 rule that reserved large-page encodings fault rather than silently mapping memory.

## Examples

| VA | L0 | L1 | L2 | L3 | Page offset |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `0x0000_0000_0000` | 0 | 0 | 0 | 0 | `0x000` |
| `0x0000_0000_07FF` | 0 | 0 | 0 | 0 | `0x7FF` |
| `0x0000_0000_0800` | 0 | 0 | 0 | 1 | `0x000` |
| `0x1234_5678_9ABC` | 9 | 104 | 691 | 787 | `0x2BC` |
| `0xFFFF_FFFF_FFFF` | 127 | 1023 | 1023 | 1023 | `0x7FF` |

## Out of Scope for This Story

- `SATP` layout and root selection: E09-S02.
- TLB fill, ASID matching, invalidation, and shootdown: E09-S03.
- PTE field layout and permission semantics: E09-S05.
- Page memory-type behavior: E09-S06.
- Fault priority across capability, translation, privilege, and alignment checks: E09-S07.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Page-table pages contain 1024 PTE slots.
- PTE slot address is `table_base + index * 2` cells.
- A valid base-page walk indexes L0, L1, L2, and L3 in that order.
- L0 index extraction uses `VA[47:41]`.
- L1 index extraction uses `VA[40:31]`.
- L2 index extraction uses `VA[30:21]`.
- L3 index extraction uses `VA[20:11]`.
- Page offset extraction uses `VA[10:0]`.
- L0 reachable indexes are `0-127`.
- A valid v0.1 leaf appears only at L3.
- L0, L1, and L2 leaf encodings raise a page-walk fault.
- Reserved `2^15` and `2^19` cell page encodings raise a page-walk fault.
- Physical address construction preserves the 11-bit page offset.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| v0.1 uses a 4-level radix page table. | Met. |
| PTEs are 48 bits. | Met. |
| Base pages hold 1024 PTEs. | Met. |
| VPN split is `7 + 10 + 10 + 10`. | Met. |
| Large pages are reserved but not implemented. | Met. |

# E14-S03: Page-table Geometry and Future Page Sizes Spike

Story: E14-S03

Status: Spike complete

Prototype: `tools/page_table_geometry.py`

Related story: `spec/E09-S01-address-and-page-size.md`

## Question

Does the proposed v0.1 MMU geometry work for 48-bit cell virtual addresses, `2^11` cell base pages, 48-bit PTEs, and a 4-level radix page table? Do the reserved `2^15` and `2^19` cell page sizes fit naturally?

## Prototype Inputs

| Property | Value |
| --- | ---: |
| Virtual address width | 48 cell-address bits |
| Base page size | `2^11` cells |
| PTE size | 2 cells |
| Page-table page size | `2^11` cells |
| PTEs per page-table page | 1024 |
| PTE index bits per full page-table level | 10 |
| VPN bits | 37 |

## Prototype Results

Command:

```text
python .\tools\page_table_geometry.py
```

Output:

| Property | Result |
| --- | --- |
| PTEs per page-table page | 1024 |
| VPN bits | 37 |
| VPN split | `7 + 10 + 10 + 10` |

Sample translations:

| VA | L0 | L1 | L2 | L3 | offset |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `0x0` | 0 | 0 | 0 | 0 | `0x0` |
| `0x7FF` | 0 | 0 | 0 | 0 | `0x7FF` |
| `0x800` | 0 | 0 | 0 | 1 | `0x0` |
| `0x123456789ABC` | 9 | 104 | 691 | 787 | `0x2BC` |
| `0xFFFFFFFFFFFF` | 127 | 1023 | 1023 | 1023 | `0x7FF` |

Natural leaf sizes if higher-level leaf PTEs are later allowed:

| Leaf level | Natural page size |
| --- | ---: |
| L0 | `2^41` cells |
| L1 | `2^31` cells |
| L2 | `2^21` cells |
| L3 | `2^11` cells |

Reserved future page size fit:

| Reserved size | Fit with simple radix leaf? |
| ---: | --- |
| `2^15` cells | No |
| `2^19` cells | No |

## Findings

The base-page geometry is coherent:

- A base page has 2048 cells.
- A 48-bit PTE occupies 2 cells.
- A page-table page holds 1024 PTEs.
- Full page-table levels naturally consume 10 VPN bits.
- 37 VPN bits split cleanly as `7 + 10 + 10 + 10`.

The reserved future page sizes do not naturally match the simple radix geometry:

- `2^15` cells would require 4 lower VPN bits beyond the base page offset.
- `2^19` cells would require 8 lower VPN bits beyond the base page offset.
- Natural higher-level leaf sizes are `2^21`, `2^31`, and `2^41` cells.

## Recommendation

For v0.1:

- Keep the 4-level radix page table.
- Implement only `2^11` cell base pages.
- Use VPN split `7 + 10 + 10 + 10`.
- Reserve `2^15` and `2^19` page-size encodings, but do not implement them as valid leaf sizes.

For a later revision, choose one of:

- Change future large-page sizes to natural radix sizes such as `2^21` cells.
- Add a separate contiguous-PTE large-page mechanism.
- Add a more complex walker mode for non-natural page sizes.

Do not add the non-natural large-page behavior to v0.1.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| 4-level base-page walk is modeled. | Met. |
| `2^11` cell base pages are validated. | Met. |
| `2^15` and `2^19` cell future page sizes are analyzed against the radix geometry. | Met. |
| Large-page support is either revised, deferred, or given a compatible encoding plan. | Deferred; reserve encodings only for v0.1. |


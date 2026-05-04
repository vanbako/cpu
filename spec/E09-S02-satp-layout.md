# E09-S02: SATP Layout

Story: E09-S02

Status: Complete

Normative source: `design.md`, section 12.3

Prerequisites:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E09-S01-address-and-page-size.md`

Related sources:

- `spec/E02-S04-csr-instructions.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E09-S04-page-table-geometry.md`
- `spec/E11-S01-cold-reset-state.md`

## Decision

`SATP` is the per-core scalar CSR that selects address-translation mode, the active address-space identifier, and the root physical page number for the v0.1 page-table walker.

CPU v0.1 implements two `SATP.MODE` values:

- `BARE`: translation disabled.
- `RADIX4`: 4-level radix translation using the E09-S04 page-table geometry.

The mandatory `ASID` CSR is a separate access path to the same active 8-bit ASID carried in `SATP.ASID`. Reading `ASID` returns `SATP.ASID`. Writing `ASID` updates `SATP.ASID` without changing `SATP.MODE` or `SATP.ROOT_PPN`.

## `SATP` Field Layout

`SATP` is a 48-bit CSR.

| Bits | Field | Meaning |
| ---: | --- | --- |
| `47:45` | `MODE` | Address-translation mode. |
| `44:37` | `ASID` | Active address-space identifier. |
| `36:0` | `ROOT_PPN` | Physical page number of the root L0 page table. |

Packing:

```text
SATP[47:45] = MODE[2:0]
SATP[44:37] = ASID[7:0]
SATP[36:0]  = ROOT_PPN[36:0]
```

This exactly fills the 48-bit scalar CSR width.

## Mode Values

| `MODE` value | Name | Meaning |
| ---: | --- | --- |
| `0b000` | `BARE` | Address translation disabled. |
| `0b001` | `RADIX4` | E09-S04 4-level radix page table with `2^11` cell base pages. |
| `0b010-0b111` | Reserved | Illegal in v0.1. |

`SATP=0` after reset means:

```text
MODE     = BARE
ASID     = 0
ROOT_PPN = 0
```

`MODE=BARE` disables translation even if the active `ASID` is nonzero. In `BARE` mode, `ROOT_PPN` must be zero.

## `BARE` Mode

When `SATP.MODE=BARE`, address translation is disabled.

Rules:

- Instruction fetch uses the effective cell address authorized by `PCC` as the physical cell address.
- Data and capability memory accesses use the effective cell address authorized by the relevant capability as the physical cell address.
- No page-table walk is performed.
- No TLB entry is allocated or used for the access.
- Page faults are not generated solely from translation metadata, because translation metadata is not consulted.
- Capability, privilege, alignment, physical memory, and memory-type checks still apply according to their owning stories.

`SATP.ASID` remains architectural state in `BARE` mode, but it has no translation effect until a translating mode is enabled.

## `RADIX4` Mode

When `SATP.MODE=RADIX4`, address translation uses the E09-S04 page-table geometry.

Rules:

- `SATP.ROOT_PPN` names the physical page number of the L0 root page-table page.
- The root table base cell address is:

```text
root_base = SATP.ROOT_PPN << 11
```

- `root_base[10:0]` is always zero by construction.
- The L0 root table must be aligned to `2^11` cells.
- The page-table walker uses the E09-S04 VPN split: `7 + 10 + 10 + 10`.
- Only L3 leaf PTEs are valid v0.1 leaf mappings.
- PTE format, valid/leaf encodings, permission bits, accessed bits, memory type, and reserved-bit faults are defined by E09-S05.

`ROOT_PPN=0` is architecturally legal in `RADIX4` mode. A platform may reserve physical page zero by platform convention, but the CPU architecture does not hard-code that reservation.

## Active ASID

CPU v0.1 implements an 8-bit active ASID.

| State | Width | Reset value |
| --- | ---: | ---: |
| Active ASID | 8 bits | `0` |

The active ASID is visible through both:

- `SATP.ASID`, bits `44:37`.
- `ASID[7:0]`, the mandatory scalar CSR named by E02-S02.

`ASID[47:8]` are reserved-zero. Reads return zero. Writes must provide zero.

Rules:

- A committed `SATP` write updates `MODE`, active ASID, and `ROOT_PPN` atomically.
- A committed `ASID` write updates only the active ASID and therefore updates the value later read through `SATP.ASID`.
- `CSRRD ASID` returns `zero_extend_48(active_asid)`.
- `CSRWR ASID, Ds` writes `Ds[7:0]` to the active ASID if `Ds[47:8]=0`.
- `CSRSET` and `CSRCLR` on `ASID` operate on the zero-extended 8-bit active ASID and must write zero to reserved bits.

Changing the active ASID affects subsequent translation-context selection. TLB matching, retained entries, local invalidation, and remote shootdown are defined by E09-S03.

## Legal Write Rules

`SATP` and `ASID` are kernel-only CSRs. User-mode reads or writes fault according to E07-S01 and E02-S04.

A `SATP` write is legal only when all of these are true:

- `MODE` is `BARE` or `RADIX4`.
- If `MODE=BARE`, `ROOT_PPN=0`.
- If `MODE=RADIX4`, `ROOT_PPN` is a 37-bit physical page number.
- `ASID` is an 8-bit value.

A `SATP` write with reserved `MODE` values raises `ILLEGAL_CSR_WRITE` and leaves `SATP` and `ASID` unchanged.

A `SATP` write with `MODE=BARE` and nonzero `ROOT_PPN` raises `ILLEGAL_CSR_WRITE` and leaves `SATP` and `ASID` unchanged.

An `ASID` write with any nonzero bit in `ASID[47:8]` raises `ILLEGAL_CSR_WRITE` and leaves the active ASID unchanged.

Faulting writes have no translation-context side effect and do not invalidate or populate TLB entries.

## Translation Context Change

A committed write to `SATP` or `ASID` changes the active translation context before any younger instruction fetch, data access, or capability memory access is architecturally performed.

Required ordering:

- Older instructions retire before the CSR write commits.
- The CSR write commits atomically with any integer destination writeback required by the CSR instruction form.
- Younger translation lookups use the new active translation context.
- In `BARE` mode, younger accesses bypass translation.

Writing `SATP` or `ASID` does not by itself guarantee that previous stores to page tables have become visible to the page-table walker on other cores. Software must use the translation-maintenance sequence defined by E09-S03 and E08-S04 when installing, modifying, or reusing page tables and ASIDs.

An implementation may flush local TLB state on any committed `SATP` or `ASID` write. The architecture does not require an automatic flush if the E09-S03 TLB matching and invalidation rules are still obeyed.

## Examples

| Desired state | `SATP` value |
| --- | ---: |
| Translation off, ASID 0 | `0x0000_0000_0000` |
| Translation off, ASID 7 | `0x000E_0000_0000` |
| `RADIX4`, ASID 0, root PPN 0 | `0x2000_0000_0000` |
| `RADIX4`, ASID 1, root PPN `0x12345` | `0x2002_0001_2345` |
| `RADIX4`, ASID 255, root PPN all ones | `0x3FFF_FFFF_FFFF` |

Encoding formula:

```text
satp = (MODE << 45) | (ASID << 37) | ROOT_PPN
```

## Out of Scope for This Story

- TLB entry format, lookup, replacement, local invalidation, and remote shootdown: E09-S03.
- Page-table PTE bit layout and page-walk fault behavior: E09-S05.
- Memory-type semantics for translated pages: E09-S06.
- Fault priority across capability, translation, privilege, and alignment checks: E09-S07.
- Fence and `SFENCE.VM` instruction semantics: E08-S04.
- Virtualization or guest address-space control.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Reset reads `SATP=0` and `ASID=0`.
- `SATP=0` disables translation.
- `MODE=BARE` with nonzero `ASID` still disables translation.
- `MODE=BARE` with nonzero `ROOT_PPN` raises `ILLEGAL_CSR_WRITE`.
- `MODE=RADIX4` selects E09-S04 4-level page-table geometry.
- `ROOT_PPN` forms an aligned root table base by shifting left 11 cell-address bits.
- Reserved `MODE` values raise `ILLEGAL_CSR_WRITE` and leave `SATP` unchanged.
- `CSRWR ASID` with high bits zero updates `SATP.ASID` and leaves `MODE` and `ROOT_PPN` unchanged.
- `CSRWR ASID` with high bits set raises `ILLEGAL_CSR_WRITE`.
- User-mode reads and writes of `SATP` and `ASID` fault.
- A committed `SATP` write affects younger translation lookups.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `SATP` includes `MODE`, `ASID`, and `ROOT_PPN`. | Met. |
| Recommended packing is `MODE[2:0]`, `ASID[7:0]`, and `ROOT_PPN[36:0]`. | Met: bits `47:45`, `44:37`, and `36:0`. |
| Supported `MODE` values are specified. | Met: `BARE` and `RADIX4`; all other values are reserved. |
| Illegal `SATP` writes are handled predictably. | Met: illegal writes raise `ILLEGAL_CSR_WRITE` and leave `SATP`/`ASID` unchanged. |

# E09-S05: PTE Format

Story: E09-S05

Status: Complete

Normative source: `design.md`, section 12.5

Prerequisite:

- `spec/E09-S04-page-table-geometry.md`

Related sources:

- `spec/E07-S02-exception-classes.md`
- `spec/E09-S02-satp-layout.md`
- `spec/E09-S03-tlb-model.md`

## Decision

CPU v0.1 page-table entries are 48-bit scalar values stored as two naturally aligned cells.

PTEs are not capabilities. The page-table walker does not consume memory capability tags and cannot create capability authority from PTE payload bits.

The PTE format supports:

- 37-bit physical page numbers.
- Invalid, non-leaf, and leaf encodings.
- User/kernel page privilege.
- Read, write, and execute page permissions.
- Global TLB mappings.
- Software-managed accessed-bit behavior.
- Page memory-type selection.
- One hardware-reserved bit.
- One software-owned bit so the 48-bit PTE is fully named.

## Bit Layout

| Bits | Field | Meaning |
| ---: | --- | --- |
| `47:11` | `PPN[36:0]` | Physical page number or next-level table physical page number. |
| `10` | `RES0` | Reserved-zero hardware bit. |
| `9:8` | `MT[1:0]` | Page memory type. |
| `7` | `SW` | Software-owned bit ignored by hardware. |
| `6` | `A` | Accessed bit. |
| `5` | `G` | Global translation bit. |
| `4` | `X` | Execute permission. |
| `3` | `W` | Write permission. |
| `2` | `R` | Read permission. |
| `1` | `U` | User-accessible page. |
| `0` | `V` | Valid PTE bit. |

Encoding formula:

```text
pte = (PPN << 11)
    | (RES0 << 10)
    | (MT << 8)
    | (SW << 7)
    | (A << 6)
    | (G << 5)
    | (X << 4)
    | (W << 3)
    | (R << 2)
    | (U << 1)
    | V
```

The `SW` bit is available to privileged software for page-table metadata. Hardware must preserve it in memory and ignore it during translation. `SW` does not affect validity, permissions, memory type, TLB matching, or fault behavior.

## PTE Classes

PTE class is determined by `V`, `R`, `W`, and `X`.

| Encoding | Class | Meaning |
| --- | --- | --- |
| `V=0` | Invalid | No translation through this PTE. |
| `V=1` and `R=W=X=0` | Non-leaf | `PPN` points to the next page-table level. |
| `V=1` and any of `R`, `W`, or `X` is `1` | Leaf | `PPN` maps a physical base page. |

Invalid PTEs may contain any payload bits. Hardware ignores every field except `V=0` and raises `PAGE_FAULT` for the original faulting virtual address.

Non-leaf PTEs are valid only at L0, L1, and L2. A non-leaf PTE at L3 raises `PAGE_FAULT`.

Leaf PTEs are valid only at L3 in v0.1. A leaf PTE at L0, L1, or L2 raises `PAGE_FAULT` because large pages are reserved but not implemented.

## Valid Non-leaf PTEs

A valid non-leaf PTE:

- Has `V=1`.
- Has `R=W=X=0`.
- Uses `PPN` as the physical page number of the next page-table page.
- Requires the next page-table base address to be aligned to `2^11` cells by construction.

Required non-leaf field values:

| Field | Required value |
| --- | --- |
| `RES0` | `0` |
| `MT` | `0b00` |
| `A` | `0` |
| `U` | `0` |

`G` in a non-leaf PTE is reserved in v0.1 and must be `0`. Global mappings are expressed only by the L3 leaf PTE's `G` bit.

`SW` is ignored for non-leaf PTEs.

Any violation of the required non-leaf field values raises `PAGE_FAULT`.

## Valid Leaf PTEs

A valid v0.1 leaf PTE:

- Appears at L3.
- Has `V=1`.
- Has at least one of `R`, `W`, or `X` set.
- Has `RES0=0`.
- Has `A=1`.
- Has `MT` set to a supported memory-type encoding.
- Maps one `2^11` cell base page.

Physical address construction:

```text
PA[47:11] = PTE.PPN[36:0]
PA[10:0]  = VA[10:0]
```

`R`, `W`, and `X` are independent page permissions:

| Access type | Required leaf permission |
| --- | --- |
| Instruction fetch | `X=1` |
| Integer data load | `R=1` |
| Capability load | `R=1` |
| `LL48` | `R=1` |
| Integer data store | `W=1` |
| Capability store | `W=1` |
| Successful `SC48` | `W=1` |

Capability load/store instructions still require their capability-authority checks from the capability and effective-access stories. Page permissions do not replace capability permissions.

`U=1` means user mode may access the page if the access type and all other checks permit it. `U=0` means the page is kernel-only. The exact combined user/kernel, capability, and page-permission priority is finalized by E09-S07.

`G=1` marks the resulting TLB entry as global. A global TLB entry may match any active ASID according to E09-S03. Software must use global-aware invalidation when changing a global mapping.

## Accessed-bit Policy

CPU v0.1 uses a software-managed accessed bit.

Hardware does not set `A` as a side effect of translation.

Rules:

- A valid leaf PTE with `A=0` raises `PAGE_FAULT` before the access commits.
- The faulting access does not update `A`.
- Kernel software may set `A=1` in the PTE and retry the faulting access.
- After changing `A`, software must perform the TLB maintenance required by E09-S03 and E08-S04 before relying on the updated translation on any core that may have cached the old result.

Non-leaf PTEs must have `A=0`.

No dirty bit exists in the v0.1 PTE. Software that needs dirty tracking must use page permissions, traps, and its own metadata.

## Memory Type Field

`MT[1:0]` selects the page memory type.

Architectural encodings:

| `MT` | Name | E09-S05 behavior |
| ---: | --- | --- |
| `0b00` | `NORMAL_COHERENT` | Valid leaf memory type. |
| `0b01` | `NORMAL_UNCACHEABLE` | Valid leaf memory type. |
| `0b10` | `DEVICE_ORDERED` | Valid leaf memory type. |
| `0b11` | Reserved | Raises `PAGE_FAULT` for valid leaf PTEs. |

E09-S06 defines the detailed behavior of the valid memory types, including cacheability, ordering, device side effects, and fence requirements.

Non-leaf PTEs must use `MT=0b00`.

## Page-walk Faults

The page-table walker raises `PAGE_FAULT` for:

- Invalid PTE (`V=0`) at any walk level.
- Non-leaf PTE at L3.
- Leaf PTE at L0, L1, or L2.
- `RES0=1` in any valid PTE.
- Reserved or illegal field values in a valid non-leaf PTE.
- Leaf PTE with `A=0`.
- Leaf PTE with `MT=0b11`.
- Permission failure for the attempted access.
- User-mode access to `U=0` page.
- Page-table memory access failure during a page walk, unless a later platform story classifies the failure as `ACCESS_FAULT`.

For page faults:

```text
CAUSE       = PAGE_FAULT
TVAL        = faulting virtual cell address
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

E09-S07 finalizes the precise priority between page faults, capability faults, alignment faults, memory-type access faults, and physical access faults.

## PTE Reads, Writes, and Atomicity

A PTE occupies two cells and is naturally 2-cell aligned by E09-S04.

The page-table walker reads each PTE as one aligned 48-bit scalar value. It must not observe a torn mixture of old and new halves for a PTE update that software performs with one aligned `ST48`.

Software page-table updates should use aligned `ST48` stores for PTE writes. Updating one PTE with multiple ordinary operations or racing a walker against a PTE update without required synchronization is invalid software behavior.

Changing a valid PTE that may already be cached in a TLB requires the invalidation and shootdown rules from E09-S03.

## Examples

For these examples, `ppn = 0x12345`.

| Meaning | PTE value |
| --- | ---: |
| Invalid | `0x0000_0000_0000` |
| Non-leaf table pointer | `0x0000_091A_2801` |
| Kernel read/write normal coherent leaf, accessed | `0x0000_091A_284D` |
| User read/execute normal coherent leaf, accessed | `0x0000_091A_2857` |
| Global kernel execute leaf, accessed | `0x0000_091A_2871` |
| Device ordered kernel read/write leaf, accessed | `0x0000_091A_2A4D` |

## Out of Scope for This Story

- TLB lookup, invalidation, ASID matching, and shootdown: E09-S03.
- Detailed page memory-type semantics: E09-S06.
- Final effective-access fault priority: E09-S07.
- Final `SFENCE.VM` and fence sequencing: E08-S04.
- Virtualization, nested page tables, and superpages.
- Hardware dirty-bit tracking.

## Verification Notes

Minimum conformance checks for later simulator, firmware, OS, and RTL work:

- PTEs are read as 48-bit scalar values from 2-cell aligned addresses.
- `V=0` PTEs fault and ignore all other fields.
- `V=1, R=W=X=0` is a non-leaf PTE at L0-L2.
- A non-leaf PTE at L3 raises `PAGE_FAULT`.
- A leaf PTE at L0-L2 raises `PAGE_FAULT`.
- `RES0=1` in any valid PTE raises `PAGE_FAULT`.
- Valid non-leaf PTEs require `U=0`, `G=0`, `A=0`, and `MT=0`.
- Leaf PTEs with `A=0` raise `PAGE_FAULT`.
- Leaf PTEs with `MT=0b11` raise `PAGE_FAULT`.
- User-mode access to a `U=0` leaf raises `PAGE_FAULT`.
- Fetch requires `X=1`; load requires `R=1`; store requires `W=1`.
- `G=1` on an L3 leaf creates a global TLB mapping.
- `SW` does not affect translation, fault behavior, or TLB matching.
- Page faults write `TVAL` with the faulting virtual cell address.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| PTE includes `PPN[36:0]`, `V`, `U`, `R`, `W`, `X`, `G`, `A`, `MT[1:0]`, and one reserved bit. | Met. |
| Invalid, non-leaf, and leaf PTE rules are specified. | Met. |
| Accessed-bit update behavior is defined or delegated to software. | Met: `A` is software-managed and `A=0` faults. |
| Reserved-bit violations raise page fault. | Met. |

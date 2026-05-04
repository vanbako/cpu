# E09-S07: Effective Access Rule

Story: E09-S07

Status: Complete

Normative source: `design.md`, section 12.6

Prerequisites:

- `spec/E03-S02-capability-permissions.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E09-S05-pte-format.md`

Related sources:

- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E09-S02-satp-layout.md`
- `spec/E09-S03-tlb-model.md`

## Decision

Every instruction fetch, data memory access, capability memory access, stack access, and atomic memory access must pass both capability authority and memory-management authority.

The effective access rule composes:

- Authorizing capability tag, seal-state, bounds, and permissions.
- Object alignment and representable address range.
- Address translation through `SATP`, page tables, and TLBs.
- Page privilege and page permissions.
- Page memory type and physical access checks.

Kernel mode bypasses only user/kernel page privilege restrictions. It does not bypass capability checks, page permissions, alignment, memory type, or physical access checks.

## Access Classes

This story defines these architectural access classes:

| Access class | Authorizing capability | Object size | Object alignment | Capability permissions | Page permission |
| --- | --- | ---: | ---: | --- | --- |
| Instruction fetch | `PCC` | Instruction-dependent | E04-S01/E06-S01 placement | `EX` | `X` |
| Integer load (`LD48`) | Instruction-selected data capability | 2 cells | 2 cells | `LD` | `R` |
| Integer store (`ST48`) | Instruction-selected data capability | 2 cells | 2 cells | `ST` | `W` |
| Capability load (`CLC`) | Instruction-selected data capability | 4 cells | 4 cells | `LD`, `LC` | `R` |
| Capability store (`CSC`) | Instruction-selected data capability | 4 cells | 4 cells | `ST`, `SC`, plus `SL` when storing a valid local capability | `W` |
| `LL48` | Instruction-selected data capability | 2 cells | 2 cells | `LD` | `R` |
| Successful `SC48` | Instruction-selected data capability | 2 cells | 2 cells | `ST` | `W` |

The instruction story selects the authorizing capability. For example, instruction fetch always uses `PCC`; stack operations use `DSC`; explicit default-data forms use `DDC`; ordinary data and capability memory forms use their instruction-selected capability operand.

Failed `SC48` has no memory store, but the address, capability, alignment, translation, privilege, page, and memory-type checks still apply before the instruction can report architectural failure.

## Common Data-access Check Order

For data, capability, stack, and atomic memory accesses, the selected fault is determined by this order:

1. Authorizing capability tag.
2. Authorizing capability seal-state.
3. Effective address arithmetic representability.
4. Object alignment.
5. Authorizing capability bounds for the complete object.
6. Protected return-stack storage classification, when the platform has protected return-stack storage enabled.
7. Authorizing capability permissions, including `SL` for local capability stores.
8. Address translation and page-walk validity.
9. Page privilege and page permission.
10. Memory-type legality for the access class.
11. Physical or platform access.

The first failing check in this order determines the reported exception.

No memory payload, memory tag, reservation state, TLB state visible to software, destination register, or store-buffer entry is updated when any check fails.

## Capability Checks

The authorizing capability must satisfy:

- Tag is valid.
- Capability is unsealed.
- The effective object range is inside bounds.
- Required capability permissions for the access class are present.

Capability failures report:

| Failed check | Exception | Reporting |
| --- | --- | --- |
| Invalid tag | `CAPABILITY_TAG_FAULT` | `FAULTCAPIDX` names the authorizing capability. |
| Sealed authorizing capability | `CAPABILITY_SEAL_TYPE_FAULT` | `FAULTCAPIDX` names the authorizing capability. |
| Effective address underflow or overflow | `CAPABILITY_BOUNDS_FAULT` | `TVAL=0` unless the instruction story defines a more precise value. |
| Object outside capability bounds | `CAPABILITY_BOUNDS_FAULT` | `TVAL` is the effective cell address or first out-of-bounds cell. |
| Missing `LD`, `ST`, `EX`, `LC`, or `SC` | `CAPABILITY_PERMISSION_FAULT` | `CAPCAUSE=PERMISSION`. |
| Missing `SL` for storing a valid local capability | `CAPABILITY_LOCAL_STORE_FAULT` | `CAPCAUSE=LOCAL_STORE`. |

Instruction-specific capability source ordering remains owned by the instruction story. Once an instruction has selected the authorizing capability for a memory access, this story owns the ordering between that capability's memory authority checks and MMU checks.

## Protected Return-stack Storage

If a data or capability memory access overlaps protected return-stack storage defined by E06-S04, ordinary access fails with `RETURN_STACK_PERMISSION_FAULT`.

This classification occurs after the effective range is representable, aligned, and known to be inside the authorizing capability bounds. It occurs before ordinary load/store capability permission checks, translation, page permission checks, memory-type checks, or physical access.

The faulting access does not read memory, write memory, clear a capability tag, allocate a store-buffer entry, or update `RSC`.

## Effective Address and Alignment

Data and capability memory effective addresses are computed in mathematical integers. The result must name a representable v0.1 virtual cell range:

```text
0 <= effective
effective + object_size <= 2^48
```

Representability failure raises `CAPABILITY_BOUNDS_FAULT` before translation.

Alignment requirements:

| Object | Alignment failure |
| --- | --- |
| 48-bit integer load/store or `LL48`/`SC48` target not 2-cell aligned | `ALIGN_FAULT` |
| 96-bit capability load/store target not 4-cell aligned | `ALIGN_FAULT` |
| Instruction placement violates E04-S01/E06-S01 slot or fetch-group rules | `ALIGN_FAULT` |

Alignment is checked before capability bounds and before translation for data and capability memory accesses. For instruction fetch, slot and placement alignment follows the fetch-specific order below.

Because base pages are `2^11` cells and v0.1 data objects are naturally aligned power-of-two sizes no larger than 4 cells, an aligned v0.1 data or capability memory object cannot cross a base-page boundary.

## Translation and Page Checks

When `SATP.MODE=BARE`, address translation is disabled:

- The effective cell address is used as the physical cell address.
- No page-table walk occurs.
- No TLB lookup is used.
- Page privilege and page permissions are not checked.
- Memory-type behavior comes from the platform's bare-mode physical memory attributes, where defined.

When `SATP.MODE=RADIX4`, translation uses E09-S02, E09-S03, E09-S04, and E09-S05.

Translation and page checks fail with `PAGE_FAULT` for:

- Page walk invalidity or malformed PTEs.
- Leaf PTE with `A=0`.
- Leaf PTE with reserved `MT`.
- User-mode access to a `U=0` page.
- Missing page permission for the access class.

Page faults report:

```text
CAUSE       = PAGE_FAULT
TVAL        = faulting virtual cell address
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

For a multi-cell object, `TVAL` reports the first virtual cell of the object unless a page-walk story defines a more precise faulting cell. In v0.1 aligned memory objects do not cross page boundaries, so the first cell identifies the faulting page.

## Page Privilege

Page privilege is controlled by `PTE.U`.

| Current `SR.PRIV` | `PTE.U=0` | `PTE.U=1` |
| --- | --- | --- |
| `U` | Page privilege failure, `PAGE_FAULT` | Allowed if all other checks pass. |
| `K` | Allowed if all other checks pass. | Allowed if all other checks pass. |

v0.1 has no supervisor-execute-never, supervisor-access-user, or user-execute-only page policy beyond `PTE.U`.

Kernel accesses to user pages are therefore allowed by page privilege, but still require capability authority and page `R`, `W`, or `X` permission.

## Page Permissions

Page permissions are checked after page privilege.

| Access | Required PTE bit |
| --- | --- |
| Instruction fetch | `X=1` |
| Integer load, capability load, `LL48` | `R=1` |
| Integer store, capability store, successful `SC48` | `W=1` |

Missing page permission raises `PAGE_FAULT`, not a capability permission fault.

Page permissions and capability permissions are both required. For example, `CLC` requires `LD` and `LC` in the authorizing capability and `R=1` in the page leaf PTE.

## Memory Type and Physical Access

After capability, alignment, translation, page privilege, and page permission checks pass, the access must be legal for the selected memory type and physical target.

Memory-type behavior is finalized by E09-S06. Until E09-S06 defines the detailed contract, E09-S07 fixes this priority:

- Reserved `MT=0b11` in a leaf PTE raises `PAGE_FAULT` during translation.
- A valid memory type that does not support the requested access class raises `ACCESS_FAULT`.
- A physical bus, device, or platform protection failure raises `ACCESS_FAULT`.

Access faults report:

```text
CAUSE       = ACCESS_FAULT
TVAL        = faulting physical cell address when known, otherwise the effective cell address or 0
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

## Instruction Fetch Rule

Instruction fetch uses the same effective access model with fetch-specific details.

Fetch fault priority:

1. `PCC.tag` validity.
2. `PCC` seal-state.
3. `PCC` has `EX`.
4. `PCC.cursor` is inside `PCC.bounds`.
5. Slot and instruction-placement alignment defined by E04-S01 and E06-S01.
6. All architecturally consumed instruction cells are inside `PCC.bounds`.
7. Translation and page-walk validity for the fetched instruction cells.
8. Page privilege and `X` permission.
9. Memory-type legality and physical access.
10. Illegal instruction decoding.

The current `PCC.cursor` is the faulting virtual cell address for fetch page faults. For capability bounds faults involving a later consumed instruction cell, `TVAL` reports the first consumed out-of-bounds cell according to E06-S01.

An invalid instruction encoding is reported only after the access to the instruction cells is authorized and succeeds.

## Data and Capability Access Rule

For an aligned data or capability memory access in `RADIX4` mode:

```text
effective = instruction-defined capability cursor + instruction-defined offset
vpn       = effective[47:11]
offset    = effective[10:0]
```

The access succeeds only when:

- The authorizing capability passes tag, seal-state, bounds, and permission checks.
- The object alignment is valid.
- Translation finds a valid L3 leaf PTE.
- `A=1`.
- `MT` is not reserved.
- Current privilege is allowed by `U`.
- The PTE has the required `R`, `W`, or `X` page permission.
- The memory type and physical target allow the access.

On success, memory payload and capability tag behavior follows the instruction story and E03-S04.

## Page-table Walker Accesses

Page-table walker memory accesses are internal translation accesses.

Rules:

- Page-table walker accesses are authorized by `SATP.ROOT_PPN` and valid non-leaf PTEs, not by `PCC`, `DSC`, `DDC`, or a general capability.
- Page-table walker accesses read 48-bit PTEs as scalar MMU data.
- Capability tags in page-table memory are ignored.
- A page-table memory access failure during a walk is reported as `PAGE_FAULT` unless a later platform story classifies that failure as `ACCESS_FAULT`.
- Page-table walker accesses do not recursively translate through the virtual memory system.

## Fault Atomicity

Faulting effective accesses are precise.

On any selected fault:

- The faulting instruction does not retire.
- Destination integer and capability registers are unchanged.
- Memory payload and memory tags are unchanged.
- No store-buffer entry is allocated for the faulting store.
- `LL48` does not create a valid reservation.
- `SC48` does not store and does not report success.
- The selected exception's trap reporting follows E07-S02, E07-S03, and E07-S04.

If multiple fault conditions are true, the priority in this story selects exactly one architectural exception.

## Examples

| Situation | Selected fault |
| --- | --- |
| `LD48` through invalid authorizing capability to an unmapped page | `CAPABILITY_TAG_FAULT` |
| `ST48` through sealed authorizing capability to read-only page | `CAPABILITY_SEAL_TYPE_FAULT` |
| Misaligned `CLC` target outside the page table | `ALIGN_FAULT` |
| Aligned `CLC` target outside capability bounds but mapped in the page table | `CAPABILITY_BOUNDS_FAULT` |
| `LD48` overlapping protected return-stack storage through `DSC` | `RETURN_STACK_PERMISSION_FAULT` |
| `CSC` through capability lacking `SC` to a writable page | `CAPABILITY_PERMISSION_FAULT` |
| `CSC` storing valid local capability through destination lacking `SL` | `CAPABILITY_LOCAL_STORE_FAULT` |
| User-mode `LD48` through valid capability to `U=0, R=1` page | `PAGE_FAULT` |
| User-mode `ST48` through valid capability to `U=1, W=0` page | `PAGE_FAULT` |
| Fetch through valid `PCC` from `U=1, X=0` page | `PAGE_FAULT` |
| `LL48` to valid device-ordered page if E09-S06 marks it noncoherent for atomics | `ACCESS_FAULT` |

## Out of Scope for This Story

- Final load/store opcode semantics and addressing forms: E04-S03.
- Detailed page memory-type behavior and fence requirements: E09-S06.
- Cache maintenance and noncoherent DMA sequences: E10-S04 and E10-S05.
- Final `SFENCE.VM`, `FENCE`, and `FENCE.I` instruction semantics: E08-S04.
- Platform physical memory protection beyond page tables and capabilities.
- Virtualization or nested translation.

## Verification Notes

Minimum conformance checks for later simulator, OS, and RTL work:

- Capability tag fault wins over page fault for the same data access.
- Capability seal/type fault wins over page fault for the same data access.
- Effective address underflow or overflow wins over page fault.
- Misaligned data or capability memory access raises `ALIGN_FAULT` before translation.
- Out-of-bounds aligned memory access raises capability bounds fault before translation.
- Ordinary access overlapping protected return-stack storage raises `RETURN_STACK_PERMISSION_FAULT` before ordinary load/store permission or translation checks.
- Missing capability permission raises capability permission fault before page permission is checked.
- Missing `SL` for valid local capability store raises capability local-store fault.
- Valid capability access to invalid PTE raises `PAGE_FAULT`.
- User-mode access to a `U=0` page raises `PAGE_FAULT`.
- Missing page `R`, `W`, or `X` raises `PAGE_FAULT`.
- Reserved leaf `MT` raises `PAGE_FAULT`.
- Unsupported valid memory type for an access class raises `ACCESS_FAULT`.
- Kernel mode can access `U=1` and `U=0` pages when all other checks pass.
- Page-table walker ignores capability tags in page-table memory.
- Faulting stores do not change memory payload or tags.
- Faulting `LL48` does not create a valid reservation.
- Faulting `SC48` does not store or report success.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Access succeeds only if the capability is valid, unsealed, in bounds, and has the needed permission. | Met. |
| The translated page must be valid and have the needed page permission. | Met. |
| Current privilege mode must allow the access. | Met. |
| Alignment rules must be satisfied. | Met. |
| Fault priority between capability, translation, privilege, and alignment faults is specified. | Met. |

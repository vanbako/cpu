# E04-S03: Memory Operation Set

Story: E04-S03

Status: Complete

Normative source: `design.md`, sections 7.1, 7.2, and 12.6

Prerequisites:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E09-S07-effective-access-rule.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S03-general-capability-registers.md`
- `spec/E03-S02-capability-permissions.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S05-pte-format.md`

## Decision

CPU v0.1 defines four mandatory memory operations:

- `LD48`
- `ST48`
- `CLC`
- `CSC`

`LD48` and `ST48` move ordinary 48-bit integer data. They do not carry capability tags.

`CLC` and `CSC` move 96-bit capability payloads plus the out-of-band memory tag for one naturally aligned capability slot.

All four operations are ordinary user-mode instructions, subject to capability authority, alignment, translation, page privilege, page permissions, memory type, protected return-stack restrictions, and precise-fault rules.

## Instruction Forms

Mandatory architectural forms:

| Instruction | Assembly form | Source registers | Destination registers | Summary |
| --- | --- | --- | --- | --- |
| `LD48` | `LD48 Dd, Ca, Di` | `Ca`, `Di` | `Dd` | Load two cells as one 48-bit integer. |
| `ST48` | `ST48 Ca, Di, Ds` | `Ca`, `Di`, `Ds` | memory | Store one 48-bit integer to two cells. |
| `CLC` | `CLC Cd, Ca, Di` | `Ca`, `Di` | `Cd` | Load one capability slot payload and tag. |
| `CSC` | `CSC Ca, Di, Cs` | `Ca`, `Di`, `Cs` | memory | Store one capability slot payload and tag. |

`Ca` is the memory-authorizing capability register. `Di` is a signed 48-bit cell offset. `Ds` is a 48-bit integer source register. `Dd` receives a 48-bit integer result. `Cs` is the capability source register to store. `Cd` receives a capability result.

All source operands are read before any destination register or memory effect commits.

If final ISA encoding defines explicit default-data-capability forms, those forms use `DDC` as the authorizing capability and otherwise follow the same operation semantics. The baseline forms in this story always use the explicitly named `Ca` operand.

Opcode bit assignments, compact encodings, and default-data aliases are owned by E04-S06.

## Effective Address

All four operations compute the effective cell address as:

```text
effective = Ca.cursor + signed(Di[47:0])
```

The calculation is performed in mathematical integers, not modulo `2^48`.

The effective address must name the complete memory object:

| Instruction | Object range | Representability |
| --- | --- | --- |
| `LD48` | `[effective, effective + 2)` | `0 <= effective <= 2^48 - 2` |
| `ST48` | `[effective, effective + 2)` | `0 <= effective <= 2^48 - 2` |
| `CLC` | `[effective, effective + 4)` | `0 <= effective <= 2^48 - 4` |
| `CSC` | `[effective, effective + 4)` | `0 <= effective <= 2^48 - 4` |

Effective address underflow or overflow raises `CAPABILITY_BOUNDS_FAULT` before translation.

## Alignment

Alignment is mandatory:

| Instruction | Required alignment | Fault |
| --- | ---: | --- |
| `LD48` | `effective mod 2 = 0` | `ALIGN_FAULT` |
| `ST48` | `effective mod 2 = 0` | `ALIGN_FAULT` |
| `CLC` | `effective mod 4 = 0` | `ALIGN_FAULT` |
| `CSC` | `effective mod 4 = 0` | `ALIGN_FAULT` |

An unaligned access does not read memory, write memory, clear a tag, update a destination register, or allocate a store-buffer entry.

## Access Checks

Each instruction uses the E09-S07 common data-access check order.

Required checks:

| Instruction | Capability permissions | Page permission |
| --- | --- | --- |
| `LD48` | `LD` | `R` |
| `ST48` | `ST` | `W` |
| `CLC` | `LD`, `LC` | `R` |
| `CSC` storing invalid or global capability | `ST`, `SC` | `W` |
| `CSC` storing valid local capability | `ST`, `SC`, `SL` | `W` |

The authorizing capability `Ca` must be valid, unsealed, in bounds for the complete object, and carry the required permissions.

If the effective range overlaps protected return-stack storage and the access is not one of the protected return-stack operations defined by E06-S04, the access raises `RETURN_STACK_PERMISSION_FAULT` before ordinary load/store permission, translation, or memory effects.

Address translation, page privilege, page permissions, memory-type legality, and physical access checks follow E09-S07.

## `LD48`

`LD48` loads one aligned 48-bit integer object:

```text
Dd = memory_cells[effective, effective + 2)
```

On success:

- `Dd` receives the 48-bit payload from the two addressed cells.
- No capability tag is loaded into `Dd`.
- Memory payload and memory tags are unchanged.
- `PCC` advances normally.

If the loaded cells overlap a tagged capability slot, `LD48` returns only payload bits. It never returns or creates a capability tag.

On failure:

- `Dd` is unchanged.
- Memory payload and memory tags are unchanged.

## `ST48`

`ST48` stores one aligned 48-bit integer object:

```text
memory_cells[effective, effective + 2) = Ds[47:0]
```

On success:

- The two addressed cells receive `Ds[47:0]`.
- If either written cell overlaps a naturally aligned 4-cell capability slot, that slot's memory tag is cleared according to E03-S04.
- Because `ST48` is 2-cell aligned, it may clear at most one capability slot tag.
- `PCC` advances normally.

`ST48` cannot store a capability tag. It writes integer payload bits only.

On failure:

- Memory payload is unchanged.
- Memory capability tags are unchanged.
- No store-buffer entry is allocated.

## `CLC`

`CLC` loads one aligned capability slot:

```text
Cd.payload = memory_payload[effective, effective + 4)
Cd.tag     = memory_tag[effective]
```

The tag is the tag for the naturally aligned 4-cell capability slot beginning at `effective`.

On success:

- `Cd` receives the 96-bit payload and the slot tag as one architectural operation.
- If the memory slot tag is clear, `Cd.tag` is clear.
- Loading an invalid capability payload is not a fault by itself.
- Memory payload and memory tags are unchanged.
- `PCC` advances normally.

On failure:

- `Cd` is unchanged.
- Memory payload and memory tags are unchanged.

E04-S05 defines additional capability-instruction reporting details for `CLC`. E04-S03 defines the shared memory access, alignment, page, and tag behavior.

## `CSC`

`CSC` stores one aligned capability slot:

```text
memory_payload[effective, effective + 4) = Cs.payload
memory_tag[effective] = Cs.tag
```

On success:

- Memory receives the source capability payload and tag as one architectural operation.
- Storing an invalid-tag source writes the payload and clears the memory slot tag.
- Storing a sealed capability is allowed when destination authority permits capability store.
- Storing a valid local capability requires `SL` in the authorizing capability.
- `PCC` advances normally.

`CSC` does not require the stored source capability `Cs` to be unsealed, in bounds, or permission-bearing. `Cs` is the stored value, not the authority for the store.

On failure:

- Memory payload is unchanged.
- Memory capability tags are unchanged.
- No store-buffer entry is allocated.

E04-S05 defines additional capability-instruction reporting details for `CSC`. E04-S03 defines the shared memory access, alignment, page, and tag behavior.

## Memory Ordering and Atomicity

Aligned `LD48`, `ST48`, `CLC`, and `CSC` are not torn.

Architectural visibility follows E08-S03:

- `LD48` observes one 48-bit payload value.
- `ST48` publishes its two-cell payload write and any required capability-tag clear at one global visibility point.
- `CLC` observes one capability payload and tag from one coherent visibility point, after older same-core buffered stores are considered.
- `CSC` publishes payload and tag together at one global visibility point.

No other core may observe a `CSC` payload without the matching `CSC` tag, or a matching tag without the payload.

## Fault Reporting

Fault reporting follows E07-S02, E07-S03, E07-S04, E04-S05, and E09-S07.

Baseline reporting:

| Fault | `TVAL` |
| --- | --- |
| Effective address underflow or overflow | `0` |
| Alignment fault | Effective cell address |
| Capability bounds fault for `LD48` or `ST48` | Effective cell address |
| Capability bounds fault for `CLC` or `CSC` | Effective capability slot base |
| Page fault | Faulting virtual cell address |
| Access fault | Faulting physical cell address when known, otherwise effective cell address or `0` |
| Protected return-stack ordinary access | Effective cell address or capability slot base |

For capability faults, `FAULTCAPIDX` names the authorizing capability `Ca` unless the instruction-specific capability story defines a more precise source. `CAPCAUSE` follows the selected capability fault reason.

For non-capability faults, trap entry sets `CAPCAUSE=NONE` and `FAULTCAPIDX=NONE` unless a more specific story defines otherwise.

## Out of Scope for This Story

- Exact opcode bit assignments, compact encodings, and default-data aliases: E04-S06.
- Stack push/pop pseudo-instructions and ABI frame layout: E05-S03.
- LL/SC reservation behavior: E08-S01 and E08-S02.
- Page memory-type details: E09-S06.
- Final fence, instruction-fetch synchronization, and TLB maintenance encodings: E08-S04.
- Cache maintenance and noncoherent DMA policy: E10-S04 and E10-S05.

## Verification Notes

Minimum conformance checks for later assembler, simulator, OS, and RTL work:

- `LD48` from a 2-cell aligned address loads the expected 48-bit payload.
- `ST48` to a 2-cell aligned address stores the expected 48-bit payload.
- `LD48` and `ST48` at odd cell addresses raise `ALIGN_FAULT`.
- `CLC` from a 4-cell aligned tagged slot loads payload and tag into `Cd`.
- `CLC` from an untagged slot loads payload with `Cd.tag=0`.
- `CSC` to a 4-cell aligned slot stores payload and tag together.
- Misaligned `CLC` and `CSC` raise `ALIGN_FAULT`.
- `ST48` overlapping either half of a capability slot clears that slot's tag.
- `LD48` from capability payload cells never creates a valid capability tag.
- `CSC` storing a valid local capability without `SL` raises `CAPABILITY_LOCAL_STORE_FAULT`.
- User-mode `LD48` to a kernel-only page raises `PAGE_FAULT`.
- Faulting stores do not update payload, clear tags, or allocate store-buffer entries.
- Ordinary `LD48`, `ST48`, `CLC`, and `CSC` overlapping protected return-stack storage raise `RETURN_STACK_PERMISSION_FAULT`.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `LD48` and `ST48` are defined. | Met. |
| `CLC` and `CSC` are defined. | Met. |
| `LD48/ST48` require even-cell alignment. | Met. |
| `CLC/CSC` require 4-cell alignment. | Met. |
| Unaligned access raises `ALIGN_FAULT`. | Met. |
| Load/store capability permission checks are tied to the effective access rule. | Met. |

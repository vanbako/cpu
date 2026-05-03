# E03-S01: Capability Representation

Story: E03-S01

Status: Complete

Normative source: `design.md`, section 5.1

Supporting spike: `spikes/E14-S01-capability-bounds-compression.md`

## Decision

CPU v0.1 uses a 96-bit architectural capability payload plus one out-of-band validity tag.

| Field | Bits | Meaning |
| --- | ---: | --- |
| `cursor/address` | 48 | Current cell address. |
| `bounds metadata` | 30 | Compressed representation of half-open bounds `[base, top)`. |
| `permissions` | 8 | Access and authority bits. |
| `object type` | 8 | Sealing type. |
| `flags` | 2 | Global/local and reserved flag state. |

The out-of-band tag is architectural metadata. It is not stored in the 96-bit payload and is not addressable as ordinary memory.

## Bounds Model

Capability bounds are cell-addressed and half-open:

```text
[base, top)
```

A tagged v0.1 capability must have an in-bounds cursor:

```text
base <= cursor < top
```

This strict in-bounds cursor invariant is a v0.1 simplification. It keeps compressed-bounds decode small and avoids depending on a richer correction algorithm for temporarily out-of-bounds cursors.

Implication: C-like one-past tagged capability pointers are not supported in v0.1. Software should keep tentative offsets in integer registers, then update the capability only after proving the resulting cursor is in bounds.

## Bounds Compression Budget

The 30-bit bounds metadata budget is retained for v0.1.

The E14-S01 prototype tested this candidate layout:

| Field | Bits |
| --- | ---: |
| Exponent | 6 |
| Base mantissa | 12 |
| Top mantissa | 12 |

The prototype represented:

- 1-cell objects
- 2-cell 48-bit integer objects
- 4-cell 96-bit capability objects
- `2^11` cell base pages
- Reserved future page sizes `2^15` and `2^19` cells
- Large aligned regions
- Near-top memory regions
- The full 48-bit cell address space

The exact compression algorithm is not frozen by E03-S01. The architectural contract is the 30-bit metadata budget, decoded half-open bounds, monotonic representability, and the strict in-bounds cursor invariant.

## Cursor Update Rules

| Instruction | In-bounds result | Out-of-bounds result |
| --- | --- | --- |
| `CSETADDR` | Destination receives updated tagged capability. | Capability bounds fault; destination unchanged. |
| `CINCADDR` | Destination receives updated tagged capability. | Capability bounds fault; destination unchanged. |

This rule is intentionally trap-based instead of tag-clearing. It avoids silently losing authority and makes out-of-bounds pointer creation visible during early software bring-up.

## Bounds Update Rules

For `CSETBOUNDS`:

- Requested bounds must be within parent bounds.
- Bounds may be rounded outward only if the rounded result stays within parent bounds.
- If no representable rounded-in-parent result exists, the instruction raises a capability bounds fault.
- On fault, the destination register is unchanged.

This preserves monotonic authority: a derived capability never gains range outside the parent capability.

## Object Type Rules

| `otype` value | Meaning |
| ---: | --- |
| `0` | Unsealed capability |
| Nonzero | Sealed capability |

Sealed capabilities cannot be dereferenced or modified except through defined seal/unseal or call-entry operations.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Confirm a 96-bit payload plus separate tag is represented in register state.
- Confirm tag is not visible through `LD48`.
- Confirm `otype = 0` behaves as unsealed.
- Confirm `otype != 0` behaves as sealed.
- Confirm `CSETADDR` and `CINCADDR` preserve tag for in-bounds results.
- Confirm `CSETADDR` and `CINCADDR` fault and leave destination unchanged for out-of-bounds results.
- Confirm `CSETBOUNDS` never creates bounds outside parent authority.
- Confirm unrepresentable rounded-in-parent bounds fault and leave destination unchanged.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The 96-bit layout includes 48-bit cursor/address, 30-bit bounds metadata, 8-bit permissions, 8-bit object type, and 2-bit flags. | Met. |
| The tag is out-of-band and not stored in addressable memory. | Met. |
| `otype = 0` means unsealed. | Met. |
| `otype != 0` means sealed. | Met. |
| The 30-bit bounds compressor is identified as a prototype risk. | Met by E14-S01; budget retained and exact codec remains implementation-facing. |


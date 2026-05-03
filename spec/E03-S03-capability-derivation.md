# E03-S03: Capability Derivation Rules

Story: E03-S03

Status: Complete

Normative sources:

- `design.md`, section 5.2
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S02-capability-permissions.md`

## Decision

Capability derivation in CPU v0.1 is monotonic. A derived capability may keep or reduce authority, but it may not gain bounds, permissions, validity, or sealing authority that was not present in its valid capability operands.

## Core Rules

| Rule | Meaning |
| --- | --- |
| Unforgeability | Integer data cannot create a valid capability tag. |
| Monotonic bounds | Bounds may be narrowed, not widened. |
| Monotonic permissions | Permissions may be cleared, not added. |
| Sealed isolation | Sealed capabilities cannot be dereferenced or modified except by defined unseal or call-entry operations. |
| Invalid-tag isolation | Invalid-tag capabilities cannot be dereferenced or used as derivation sources. |
| Fault atomicity | Faulting capability instructions leave destination architectural state unchanged. |

## Instruction Effects

| Instruction | Capability effect |
| --- | --- |
| `CMOVE` | Copies capability payload and tag unchanged. |
| `CGETADDR` | Copies cursor/address into an integer register; does not copy a tag. |
| `CSETADDR` | Changes only the cursor when the result remains in bounds. |
| `CINCADDR` | Adds an integer offset to the cursor when the result remains in bounds. |
| `CSETBOUNDS` | Narrows bounds when the requested or rounded bounds remain within parent bounds. |
| `CANDPERM` | Clears permission bits. |
| `CSEAL` | Converts an unsealed capability into a sealed capability with an authorized object type. |
| `CUNSEAL` | Converts a sealed capability into an unsealed capability when authorized by matching unseal authority. |

No integer ALU instruction can operate on capability registers. No integer move or load can create a valid capability tag.

## Cursor Modification

`CSETADDR` and `CINCADDR` are the only v0.1 instructions that directly change a capability cursor.

Allowed:

```text
valid capability [0x1000, 0x1800), cursor 0x1000
CINCADDR +0x20
result [0x1000, 0x1800), cursor 0x1020, tag valid
```

Faulting:

```text
valid capability [0x1000, 0x1800), cursor 0x1000
CINCADDR +0x900
capability bounds fault, destination unchanged
```

This follows the E03-S01 strict in-bounds cursor invariant.

## Bounds Modification

`CSETBOUNDS` may narrow authority.

Allowed:

```text
parent bounds [0x1000, 0x2000)
requested child bounds [0x1400, 0x1800)
result bounds [0x1400, 0x1800), if representable
```

Not allowed:

```text
parent bounds [0x1000, 0x2000)
requested child bounds [0x0800, 0x1800)
capability bounds fault, destination unchanged
```

If the encoded bounds must round outward, the rounded result must still remain inside parent bounds.

## Permission Modification

`CANDPERM` may only clear bits.

Allowed:

```text
source permissions: LD ST LC SC
mask: LD LC
result permissions: LD LC
```

Not possible through derivation:

```text
source permissions: LD
requested permissions: LD ST
```

No derivation instruction may add `ST` when the source did not already have `ST`.

## Sealing Modification

`CSEAL` requires:

- An unsealed source capability to seal.
- Valid sealing authority with `SEAL`.
- An authorized object type.

`CUNSEAL` requires:

- A sealed source capability to unseal.
- Valid unsealing authority with `UNSEAL`.
- Matching object type authority.

Sealed capabilities cannot be dereferenced, bounds-adjusted, permission-adjusted, or cursor-adjusted while sealed.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CMOVE` preserves payload and tag.
- `CGETADDR` returns cursor bits but no tag.
- `CSETADDR` and `CINCADDR` only change cursor.
- `CSETADDR` and `CINCADDR` fault out of bounds and leave destination unchanged.
- `CSETBOUNDS` never widens bounds.
- `CSETBOUNDS` rejects rounded bounds outside parent bounds.
- `CANDPERM` clears permissions and never adds them.
- Sealed capabilities cannot be dereferenced.
- Sealed capabilities cannot be address-adjusted or bounds-adjusted.
- Invalid-tag capabilities cannot be derivation sources.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Bounds may be narrowed but not widened. | Met. |
| Permissions may be reduced but not increased. | Met. |
| Sealed capabilities cannot be dereferenced or modified. | Met, except through defined unseal or call-entry operations. |
| Invalid-tag capabilities cannot be dereferenced. | Met; also cannot be derivation sources. |
| Capability-address modification is allowed only through explicit capability instructions. | Met: `CSETADDR` and `CINCADDR`. |


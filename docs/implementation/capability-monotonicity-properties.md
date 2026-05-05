# Capability Monotonicity Properties

Story: I15-S01

The I15-S01 conformance fixture adds deterministic property-style coverage for
register-only capability derivation. It exercises representative bounds,
cursors, permission masks, object types, and invalid-tag inputs without adding a
randomized test dependency.

The checked invariant is that derivation can only preserve or reduce authority:

- `CSETADDR` and `CINCADDR` may change the cursor only when the resulting cursor
  remains inside the source bounds.
- `CSETBOUNDS` may only produce a child range contained by the source range,
  rooted at the source cursor.
- `CANDPERM` may only keep permission bits already present on the source.
- `CSEAL` and `CUNSEAL` may only change object-type state when the authority
  capability grants a matching seal or unseal operation.
- Faulting derivations leave the destination register unchanged.
- Invalid source tags fault for authority-bearing derivation operations and
  cannot synthesize a valid destination tag; `CMOVE` may copy the invalid
  capability exactly but does not validate it.

The fixture is intentionally simulator-level: it checks the architectural result
packets and committed register state rather than implementation internals.

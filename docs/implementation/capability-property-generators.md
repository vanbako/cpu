# Capability Property Generators

Story: I16-S02

The capability property generators provide deterministic sample sets for
authority-preserving and authority-reducing capability derivation checks. They
are deliberately small and stable: future invariant runners can select these
case IDs directly, and failures can report a readable case name without relying
on random shrinking.

The generator module is `src/cpu_v01/invariant_cases.py`. It defines:

- `CapabilityDerivationCase`: valid unsealed parent capability plus cursor,
  offset, bounds-length, permission-mask, and seal-object-type samples.
- `InvalidCapabilityCase`: invalid source capabilities used to prove that
  derivation paths cannot promote tags.
- `capability_derivation_cases()`: stable valid-source cases covering full
  authority, limited permission authority, and local store authority.
- `invalid_capability_cases()`: stable invalid-source cases covering unsealed,
  sealed, and local payload shapes.

The I16-S02 conformance fixture consumes the generated cases through the public
capability instruction executor. This keeps the generator honest: every emitted
sample must be executable for its intended path and must preserve the same
non-widening invariants as the I15-S01 property-style tests.

# Invariant Registry

Story: I16-S01

The invariant registry is the implementation-facing matrix that names the
security and correctness properties already covered by executable conformance
tests. It does not replace the story backlog; it gives later property generators
and RTL handoff work a stable set of invariant keys, owner stories, artifacts,
and checked surfaces.

The initial registry lives in `src/cpu_v01/invariants.py` and covers:

- `capability_monotonicity`: capability derivation cannot widen authority.
- `tag_non_forgery`: payload movement cannot synthesize valid capability tags.
- `precise_fault_effects`: faults do not commit partial architectural effects.
- `commit_boundary_atomicity`: normal retire packets capture one atomic commit.
- `software_visible_capability_contracts`: ABI and debug views preserve payload,
  tag, slot, and protected-stack contracts.

Each registry row names:

- one implementation story;
- architecture owner stories;
- E15 audit coverage;
- executable and documentation artifacts;
- architectural surfaces covered by the invariant.

The `validate_invariant_registry()` helper checks key uniqueness, required I15
coverage, required invariant areas, and the presence of conformance/doc
artifacts. The I16-S01 test also checks that conformance artifacts are present in
the story-derived test index.

# Debug Metadata Fixtures

Story: I17-S03

Status: Draft executable fixtures

## Scope

This story adds a deterministic debug metadata layer for CPU v0.1 toolchain
fixtures. It is not a DWARF profile and does not define an external object-file
container. It records the information needed by conformance fixtures and later
toolchain regression artifacts.

The debug metadata emitter owns:

- source line records keyed by `PCC cell plus slot`;
- symbol records resolved from linked object metadata;
- function ranges for source-level lookup and symbolic disassembly;
- ABI register metadata with capability tag and hidden-slot visibility;
- protected return-stack unwind hints derived from the debugger ABI supplement.

## Location Model

Debug locations use the same architectural coordinate as execution and traps:

```text
cell_address + PCC.slot
```

Slot 1 line records are only valid for `TEXT` sections. Data and capability-data
debug records remain cell-addressed and slot 0 unless a later debug format
introduces a separate field for sub-cell metadata.

## Register Metadata

The emitted register table mirrors the halted-core debug view:

- integer registers expose scalar payload state and ABI roles;
- general capability registers expose payload, tag visibility, and ABI roles;
- special capability registers expose payload and tags;
- `PCC` and `EPCC` also expose hidden slot state;
- protected return-stack unwind hints name the supported `PEEK`, `DROP`, and
  `REPLACE` operations and their atomic payload/tag requirements.

## Symbolic Disassembly

The fixture disassembler annotates each decoded instruction with its resolved
location. Exact symbols print as `<symbol>`. Instructions inside a known
function range print as `<function+offset>` when no exact symbol is present.
Source line labels are printed from the same `PCC cell plus slot` lookup table.

## Failure Boundary

Validation is deterministic and side-effect free. Invalid debug metadata is
rejected when a line targets an unknown or out-of-range section, when slot 1 is
used outside text, when a function range references a missing or non-function
symbol, or when a range exceeds its linked section.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Debug metadata maps `PCC` cell plus slot to source lines. | Met. |
| Debug metadata maps locations to functions and symbols. | Met. |
| ABI registers include tag visibility and hidden slot visibility. | Met. |
| Protected return-stack unwind hints are emitted. | Met. |
| Symbolic disassembly prints matching locations. | Met. |

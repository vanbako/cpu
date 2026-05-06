# Relocatable Object Metadata

Story: I17-S01

Status: Draft implementation profile

## Scope

This profile defines the metadata boundary for CPU v0.1 relocatable object
fixtures. It is not a final object-file binary format and does not implement
linking. I17-S02 owns relocation application and section placement. I17-S03 owns
debug line and symbol metadata expansion.

The profile keeps the existing cell-addressed model from I07-S03:

- section sizes and alignments are expressed in 24-bit architectural cells;
- symbol offsets are section-relative cell offsets;
- instruction entry symbols include the hidden `PCC` slot;
- ordinary payload cells do not carry valid capability tags;
- trusted capability initialization is represented through explicit sidecar
  provenance, not fabricated from serialized payload bits.

## Section Metadata

Relocatable sections use one of these kinds:

| Kind | Purpose |
| --- | --- |
| `TEXT` | Packed 12/24/48-bit instruction cells and executable labels. |
| `RODATA` | Ordinary immutable cell payloads. |
| `DATA` | Ordinary mutable cell payloads. |
| `CAPDATA` | Trusted loader capability slots with explicit sidecar provenance. |

`CAPDATA` sections must be aligned to 4-cell capability slots and cover a whole
number of capability slots. Non-`CAPDATA` sections cannot request capability
sidecar provenance.

## Symbols

Relocatable objects carry slot-aware symbols:

- every symbol names a section;
- every symbol has a cell offset inside that section;
- every symbol carries `slot=0` or `slot=1`;
- slot 1 is only valid for `TEXT` symbols;
- `ENTRY` and `FUNCTION` symbols target `TEXT`;
- `OBJECT` symbols target `DATA` or `RODATA`;
- `CAPABILITY_OBJECT` symbols target `CAPDATA`.

This keeps source-level locations, branch/call targets, and debug entry points
aligned with the architectural `PCC.cursor` plus hidden slot state.

## ABI Attributes

Every object must declare the mandatory ABI attributes:

- `CELL_ADDRESSED`;
- `SLOT_AWARE_PCC`;
- `PURE_CAPABILITY`.

Additional attributes such as `PROTECTED_RETURN_STACK` and
`CAPABILITY_TAG_SIDECARS` document which ABI surfaces the fixture expects. Later
linker stories can reject incompatible object mixtures before binary placement.

## Validation Boundary

The I17-S01 implementation is intentionally side-effect free. It validates
metadata shape, section/symbol consistency, ABI attributes, and explicit
capability sidecar provenance. It does not allocate final addresses, patch
instructions, resolve undefined references, or write a program image.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Object metadata distinguishes text, data, and capability-data sections. | Met. |
| Slot-aware symbols are represented. | Met. |
| Capability sidecar provenance is explicit. | Met. |
| ABI attributes are represented and validated. | Met. |
| Validation errors are deterministic and side-effect free. | Met. |

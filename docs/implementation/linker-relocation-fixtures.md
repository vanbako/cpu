# Linker Relocation Fixtures

Story: I17-S02

Status: Draft executable fixtures

## Scope

This story adds a small deterministic linker fixture layer over the I17-S01
relocatable object metadata. It is not a final object-file format, not a static
library model, and not a full linker script implementation.

The fixture linker owns:

- section placement with cell-count alignment;
- payload size checks against object metadata;
- local and exported symbol resolution;
- duplicate exported symbol rejection;
- undefined symbol rejection;
- relocation overflow checks;
- patching a bounded set of relocation kinds used by conformance fixtures.

## Relocation Kinds

| Kind | Patch site | Meaning |
| --- | --- | --- |
| `ABSOLUTE_CELL48` | Two ordinary payload cells | Write a 48-bit absolute cell address as low/high 24-bit cells. |
| `DIRECT_TARGET16` | One 24-bit `BRA` or `CALL` instruction | Patch the 16-bit direct target operand. |
| `CONDITIONAL_TARGET12` | One 24-bit `Bcc` instruction | Patch the 12-bit conditional branch target while preserving the condition field. |

Direct instruction target relocations require a slot-0 target because the
fixture encodings do not carry an explicit target slot. Slot-1 text labels are
still valid metadata and debug labels, but they cannot be used by these direct
relocation forms.

## Placement

Sections are placed in object order and metadata section order. Each section
base is rounded up to its `alignment_cells`; all addresses remain architectural
cell addresses. The fixture linker emits placed payload cells and resolved
symbol addresses. Program-image conversion remains owned by I17-S04 and I11
loader stories.

## Failure Boundary

Validation is deterministic and side-effect free. A failed link reports all
detected metadata, payload, placement, symbol, relocation, and overflow issues
as text. `link_objects` raises a single `LinkerError` containing those issues;
`validate_linker_inputs` returns the same issues without producing an image.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Section placement honors alignment constraints. | Met. |
| Cell and slot labels resolve through symbols. | Met. |
| Branch, call, and data relocations are represented. | Met. |
| Duplicate and undefined symbols are rejected. | Met. |
| Relocation overflow failures are checked. | Met. |

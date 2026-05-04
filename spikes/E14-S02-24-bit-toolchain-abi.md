# E14-S02: 24-bit Cell-addressed Toolchain and ABI Spike

Story: E14-S02

Status: Spike complete

Prototype: `tools/toolchain_abi_model.py`

Related stories:

- E01-S01: 24-bit cell address model
- E04-S01: Instruction size and fetch-group rules
- E05-S03: Data stack model

## Question

Can a minimal toolchain-facing model represent 24-bit cells, 48-bit fetch groups, variable-width instruction placement, cell-addressed labels, and ABI stack-frame alignment without falling back to byte-address assumptions?

## Prototype Scope

The prototype is deliberately small. It is not a final opcode map, assembler grammar, object format, or ABI document.

It models:

- 24-bit cells serialized as exactly 3 host bytes per cell.
- 48-bit fetch groups as 2 cells.
- 12-bit instructions packed into cell slot 0 and slot 1.
- 24-bit instructions at slot 0.
- 48-bit instructions aligned to slot 0 of an even fetch-group cell.
- Direct branch labels and displacements counted in cells.
- 4-cell stack-frame alignment with 2-cell integer slots and 4-cell capability slots.

## Toy Encoding Classes

The prototype uses a non-normative encoding map only to exercise layout and relocation behavior.

| Instruction | Class | Prototype purpose |
| --- | ---: | --- |
| `ADD12 Dd, Ds` | 12-bit | Simple integer instruction packed into a cell subslot. |
| `BRA24 label` | 24-bit | Direct branch with cell-counted PC-relative relocation. |
| `LD48 Dd, Ca, imm` | 24-bit | Integer load using a capability source and cell offset. |
| `ST48 Ds, Ca, imm` | 24-bit | Integer store using a capability source and cell offset. |
| `CLC Cd, Ca, imm` | 48-bit | Capability load requiring fetch-group placement. |

The final ISA story can choose different opcodes and field positions. The spike result is about representability, not opcode assignment.

## Prototype Results

Command:

```text
python .\tools\toolchain_abi_model.py
```

Output summary:

| Property | Result |
| --- | ---: |
| Encoded cells | 8 |
| Serialized host bytes | 24 |
| Fetch groups | 4 |

Encoded sample:

| cell | encoded cell | contents |
| ---: | ---: | --- |
| `0x0` | `0x121110` | `ADD12 D1, D0`; `ADD12 D2, D1` |
| `0x1` | `0xB00004` | `BRA24 done` |
| `0x2` | `0x230004` | `LD48 D3, C0, 4` |
| `0x3` | `0x330006` | `ST48 D3, C0, 6` |
| `0x4` | `0x000010` | low cell of `CLC C1, C2, 16` |
| `0x5` | `0xC11200` | high cell of `CLC C1, C2, 16` |
| `0x6` | `0x000100` | `ADD12 D0, D0`; `PAD12` |
| `0x7` | `0x000000` | section tail padding |

Fetch-group view:

| Fetch-group base | Cell 0 | Cell 1 |
| ---: | ---: | ---: |
| `0x0` | `0x121110` | `0xB00004` |
| `0x2` | `0x230004` | `0x330006` |
| `0x4` | `0x000010` | `0xC11200` |
| `0x6` | `0x000100` | `0x000000` |

Relocation example:

| Relocation | At cell | Target cell | Displacement cells | Encoded cell |
| --- | ---: | ---: | ---: | ---: |
| `BRA24 done` | `0x1` | `0x6` | 4 | `0xB00004` |

Findings:

- Labels are naturally represented as cell addresses.
- Branch displacement uses cell distance from the next cell, not byte distance.
- 48-bit instructions can be emitted safely by aligning to slot 0 of an even cell.
- The section can be serialized as a byte stream only by explicitly writing 3 bytes per cell.

## ABI Stack-frame Checks

The prototype lays out stack frames from a 4-cell aligned `DSC.cursor = 0x1800`.

| Stack frame | New `DSC.cursor` | Raw cells | Aligned cells | Objects |
| --- | ---: | ---: | ---: | --- |
| `e05_example` | `0x17F0` | 16 | 16 | two capability spills, two integer spills, one outgoing capability arg |
| `mixed_spills` | `0x17F0` | 14 | 16 | one capability spill, three integer spills, two outgoing integer args |

Findings:

- 4-cell public ABI alignment handles both 2-cell integer slots and 4-cell capability slots.
- Frame sizes must be rounded in cells, not bytes.
- Capability spill slots remain 4-cell aligned when the frame base is 4-cell aligned.
- Integer spill slots remain 2-cell aligned.
- Padding is normal and should be represented explicitly in compiler frame layout.

## Byte-oriented Host-tool Assumptions

The spike found these assumptions that a v0.1 toolchain must avoid:

- A program counter is not a byte offset. It is a cell address plus hidden slot state.
- Label arithmetic and relocation addends must count cells.
- A 24-bit cell is not a native C integer object size. Host tools must mask to 24 bits and serialize exactly 3 bytes per cell.
- A 48-bit fetch group is 6 host bytes but 2 architectural cells.
- A 48-bit integer memory object is 2 cells, not a host `uint64_t`.
- A 96-bit capability payload is 4 cells plus an out-of-band tag, not just 12 ordinary bytes.
- Section alignment must be expressed in cells: 2-cell fetch groups, 4-cell capability slots, and 16-cell cache lines.
- Debug locations need cell addresses and instruction slot information for packed 12-bit instructions.
- A byte-oriented object container can be used only with explicit CPU v0.1 relocation types and section metadata that define cell serialization.
- Capability tags cannot be recovered from an ordinary byte stream. Tagged capability data in files needs a loader-created capability path or a tag sidecar mechanism defined by a later loader/object-format story.

## Required Custom Toolchain Scope

The architecture needs a custom toolchain layer for v0.1.

Minimum practical scope:

- A cell-aware assembler and disassembler.
- A simulator loader that reads 3-byte serialized cells and rejects implicit byte-addressed relocations.
- A linker layout model whose section addresses, alignments, and relocation addends are in cells.
- Custom relocation types for direct branches, calls, trap vectors, and capability-aware references.
- A compiler backend data layout where the addressable unit is a 24-bit cell and stack slots are cell-counted.
- ABI tests for frame size, spill-slot alignment, call-boundary alignment, and packed instruction placement.
- Debug metadata conventions for cell PC values and slot-1 instructions.

Reusable host infrastructure:

- A conventional file container may be reused if every CPU v0.1 section declares cell serialization and uses CPU v0.1 relocation records.
- Generic host byte arrays may be used inside tools only as containers for serialized cells, never as architectural addresses.
- Existing compiler infrastructure may be reused behind a target backend, but the backend cannot inherit a normal byte-addressed data layout.

## Recommendation

Proceed with the 24-bit cell-addressed model, but treat toolchain work as a first-class custom target.

Do not rely on an ordinary byte-addressed ABI, ordinary ELF relocation semantics, or native host integer object sizes. Build the first assembler, disassembler, simulator loader, and ABI tests around cell addresses from the start.

The v0.1 MVP should define a compact object-container convention before serious compiler work begins:

- section payloads serialized as 3-byte cells,
- section virtual addresses in cells,
- relocation addends in cells,
- explicit fetch-group and capability-slot alignment records,
- no implicit representation of capability tags in ordinary code/data bytes.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Prototype can represent 24-bit cells and 48-bit fetch groups. | Met by `tools/toolchain_abi_model.py`. |
| Prototype can encode at least simple integer, branch, load/store, and capability instructions. | Met: `ADD12`, `BRA24`, `LD48`, `ST48`, and `CLC`. |
| ABI alignment rules are tested with example stack frames. | Met with two frame layouts and alignment assertions. |
| Byte-oriented host-tool assumptions are listed. | Met. |
| Recommendation is made on required custom toolchain scope. | Met: build a custom cell-aware toolchain layer for v0.1. |

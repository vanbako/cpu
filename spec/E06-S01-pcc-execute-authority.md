# E06-S01: Execute Authority Through `PCC`

Story: E06-S01

Status: Complete

Normative source: `design.md`, sections 3.3, 3.4, 5.1, 5.5, 6, and 9

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E03-S02-capability-permissions.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S03-capability-derivation.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E06-S03-sealed-return-capabilities.md`

## Decision

`PCC` is the only normal architectural authority for instruction fetch in CPU v0.1.

Every instruction fetch is authorized by the current `PCC` payload, `PCC` tag, and `PCC` hidden slot bit. Integer registers, data capabilities, `DDC`, and data-stack capabilities cannot authorize instruction fetch.

A valid instruction fetch requires:

- `PCC.tag` is valid.
- `PCC.otype = 0`, meaning `PCC` is unsealed.
- `PCC.permissions` contains `EX`.
- `PCC.cursor` names the current instruction cell and is inside `PCC.bounds`.
- Any additional cell architecturally consumed by the instruction is inside `PCC.bounds`.
- The current hidden slot and decoded instruction size obey E01-S05 and E04-S01.

If any check fails, the instruction does not commit architectural side effects other than precise trap reporting.

## Fetch Address and Slot State

`PCC.cursor` is a cell address. `PCC.slot` is the hidden slot bit defined by E01-S05.

The current architectural fetch location is:

```text
fetch_cell = PCC.cursor
fetch_slot = PCC.slot
```

The front end obtains the 48-bit fetch group containing `fetch_cell`:

```text
fetch_group_base = fetch_cell & ~1
```

The fetch group supplies instruction bits for decode. Architectural execute authority is checked against the instruction cells that are consumed, not against integer addresses or data capabilities.

Implementations may internally read or cache a whole 48-bit fetch group, but that mechanism is not an authority bypass. The architectural fault model is based on the cells consumed by the current instruction and the `PCC` checks in this story. Any internal overfetch must not expose executable authority outside the current `PCC`.

## Fetch Authorization Checks

Before an instruction can be decoded and retired, `PCC` must pass the common execute checks.

| Check | Failure |
| --- | --- |
| `PCC.tag` is valid | Capability tag fault |
| `PCC` is unsealed (`otype = 0`) | Capability seal/type fault |
| `PCC` has `EX` | Capability permission fault |
| `PCC.cursor` is inside `PCC.bounds` | Capability bounds fault |
| All consumed instruction cells are inside `PCC.bounds` | Capability bounds fault |

For fetch capability faults:

- `FAULTCAPIDX = PCC`.
- `TVAL` reports the attempted fetch cell address, or the first consumed instruction cell outside bounds.
- `CAPCAUSE` is `TAG`, `SEAL_TYPE`, `PERMISSION`, or `BOUNDS` according to E03-S06.

E07-S02 assigns final global exception priority. Within this story, each named failure is architecturally visible when it is the first prioritized failing fetch check.

## Consumed Instruction Cells

Instruction size and placement are defined by E01-S05 and E04-S01. E06-S01 adds the `PCC` bounds requirement for the cells consumed by a legal placement.

| Current placement | Consumed cell range | Additional `PCC` bounds requirement |
| --- | --- | --- |
| 12-bit instruction at slot 0 | `[PCC.cursor, PCC.cursor + 1)` | Current cell in bounds |
| 12-bit instruction at slot 1 | `[PCC.cursor, PCC.cursor + 1)` | Current cell in bounds |
| 24-bit instruction at slot 0 | `[PCC.cursor, PCC.cursor + 1)` | Current cell in bounds |
| 48-bit instruction at slot 0 of first fetch-group cell | `[PCC.cursor, PCC.cursor + 2)` | Current cell and next cell in bounds |

Invalid placements raise `ALIGN_FAULT`, not a capability fault:

- 24-bit instruction at slot 1.
- 48-bit instruction at slot 1.
- 48-bit instruction at slot 0 of the second fetch-group cell.
- Explicit control-transfer target that enters slot 1.

Invalid opcode contents still raise the ordinary illegal-instruction exception. `EX` does not authorize executing an invalid encoding.

## Sequential `PCC` Advancement

For ordinary fall-through, `PCC` advances according to the slot and fetch-group rules.

| Retired instruction | Next `PCC.cursor` | Next `PCC.slot` |
| --- | ---: | ---: |
| 12-bit at slot 0 | Same cell | 1 |
| 12-bit at slot 1 | `PCC.cursor + 1` | 0 |
| 24-bit at slot 0 | `PCC.cursor + 1` | 0 |
| 48-bit at slot 0 of first fetch-group cell | `PCC.cursor + 2` | 0 |

Sequential advancement is a `PCC` cursor update. The resulting `PCC.cursor` must preserve the E03-S01 strict in-bounds cursor invariant unless the instruction redirects control to a different valid execution capability.

If a fall-through instruction would advance `PCC.cursor` outside `PCC.bounds`, the instruction raises capability bounds fault before retirement. Its non-`PCC` architectural side effects do not commit.

This rule means executable regions must end with an explicit control transfer, trap, halt, or other non-fall-through terminal instruction if the next sequential cell would be outside `PCC.bounds`.

## Explicit `PCC` Installation and Control Transfers

Instruction-specific control-transfer semantics are defined by later stories, but all operations that install or redirect `PCC` must preserve the shared execute-authority contract.

Any new `PCC` installed for normal execution must be:

- Tagged valid.
- Unsealed, unless the instruction atomically unseals a permitted entry capability before installation.
- In bounds at the target cursor.
- `EX`-authorized.
- Entered at slot 0 except for `IRET`, which restores a previously captured architectural slot from `EPCC`.

Direct branches, direct calls, trap entry, interrupt entry, indirect jumps, and returns enter slot 0. A target that attempts to enter slot 1 raises `ALIGN_FAULT`.

`CALL` and `RET` additionally interact with sealed return capabilities and `RSC`; those rules are defined by E05-S04 and E06-S03. E06-S01 only defines the execute checks that the resulting `PCC` must satisfy.

## Interaction With Capability Derivation

`PCC` authority is monotonic.

Software and hardware may narrow executable authority by deriving a capability with smaller bounds or fewer permissions, then installing that capability into `PCC` through a permitted control-transfer or privileged context-management path.

No operation may create executable authority by:

- Setting `EX` on a capability that did not already have `EX`.
- Widening executable bounds beyond the source capability.
- Creating a valid capability tag from integer data.
- Fetching through `DDC`, `DSC`, `RSC`, or a general data capability as a substitute for `PCC`.

## Fault Atomicity

Fetch and `PCC` advancement faults are precise.

On an E06-S01 capability or alignment fault:

- The faulting instruction does not retire.
- Destination registers are unchanged.
- Memory payload and memory tags are unchanged.
- `PCC` remains the faulting instruction location until trap entry captures it in `EPCC`.
- `SR.SLOT` continues to mirror the faulting `PCC.slot` until trap entry changes execution state.

Trap entry, `EPCC` capture, `TVC` authorization, and exception priority are defined by E07 stories.

## Out of Scope for This Story

- Complete branch, jump, call, return, syscall, breakpoint, `IRET`, `WFI`, and `PAUSE` instruction semantics: E04-S04.
- Sealed entry capability object type and `CALLC` behavior: E06-S02.
- Sealed return capability creation and consumption: E06-S03.
- Trap entry, interrupt entry, and trap return sequencing: E07 stories.
- Reset-time `PCC` contents: E11-S02.
- Instruction-cache coherence and self-modifying-code synchronization: E08-S04.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Fetch through invalid-tag `PCC` raises capability tag fault with `FAULTCAPIDX = PCC`.
- Fetch through sealed `PCC` raises capability seal/type fault.
- Fetch through `PCC` without `EX` raises capability permission fault.
- Fetch at a `PCC.cursor` below `PCC.base` or at-or-above `PCC.top` raises capability bounds fault.
- Fetch of a legal 48-bit instruction whose second cell is outside `PCC.bounds` raises capability bounds fault.
- A legal 12-bit instruction at slot 0 advances to the same cell at slot 1.
- A legal 12-bit instruction at slot 1 advances to the next cell at slot 0.
- A legal 24-bit instruction advances to the next cell at slot 0.
- A legal 48-bit instruction advances to the next fetch group at slot 0.
- A fall-through instruction whose next `PCC.cursor` would be outside bounds raises capability bounds fault without retiring.
- A 24-bit or 48-bit instruction at slot 1 raises `ALIGN_FAULT`.
- A 48-bit instruction at the second cell of a fetch group raises `ALIGN_FAULT`.
- Direct branches, calls, returns, and trap entry install slot 0 targets.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Instruction fetch requires a valid, unsealed, execute-authorized `PCC`. | Met. |
| Fetch outside `PCC` bounds raises capability bounds fault. | Met. |
| Fetch without `EX` raises capability permission fault. | Met. |
| `PCC` cursor advancement respects slot and fetch-group rules. | Met. |

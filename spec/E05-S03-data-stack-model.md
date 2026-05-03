# E05-S03: Data Stack Model

Story: E05-S03

Status: Complete

Normative source: `design.md`, section 8

Prerequisites:

- `spec/E01-S01-cell-address-model.md`
- `spec/E03-S05-local-capabilities.md`

## Decision

`DSC` is the data-stack capability for CPU v0.1.

The data stack grows downward in cell addresses. Stack storage is used for local variables, spills, outgoing stack arguments, and temporary capability storage. Return state is not stored on the data stack; `CALL` and `RET` use `RSC`, defined by E05-S04.

## Stack Capability

`DSC` authorizes data-stack memory accesses.

The runtime or kernel initializes `DSC` as a valid, unsealed capability whose bounds cover the thread's data-stack region.

Recommended `DSC` permissions:

| Use | Required permissions |
| --- | --- |
| Integer stack load | `LD` |
| Integer stack store | `ST` |
| Capability stack load | `LD`, `LC` |
| Global capability stack store | `ST`, `SC` |
| Local capability stack store | `ST`, `SC`, `SL` |

`DSC` should normally be a local capability with `G=0`. Capabilities derived from stack authority should also normally be local so stack-derived authority cannot be stored into heap or global memory unless the destination explicitly allows local stores.

## Stack Cursor Rule

`DSC.cursor` is the current data-stack pointer.

Because v0.1 capabilities require the cursor to remain inside bounds, `DSC.cursor` must always be an in-bounds cell address. It is not allowed to represent an empty stack by pointing one past the top bound.

Software that creates a stack must initialize `DSC.cursor` to a valid aligned address inside the stack bounds. A normal thread starts with an initial aligned frame or anchor slot below the top of the stack region.

## Growth Direction

The data stack grows downward:

- Allocating stack space subtracts a cell count from `DSC.cursor`.
- Releasing stack space adds a cell count to `DSC.cursor`.
- A lower cell address is deeper in the stack.
- A higher cell address is closer to the stack top.

Stack allocation must not move `DSC.cursor` below `DSC.base`. Stack release must not move `DSC.cursor` outside `DSC.bounds`.

Stack overflow from downward allocation is reported as the capability fault produced by the failing cursor update or store authorization. E07-S02/E09-S07 define final fault priority.

## Alignment

The ABI stack alignment is 4 cells.

Rules:

- `DSC.cursor` is 4-cell aligned at public call boundaries.
- Function frame sizes are multiples of 4 cells.
- 48-bit integer slots are 2-cell aligned.
- 96-bit capability slots are 4-cell aligned.
- Capability spill slots must not overlap integer spill slots.
- Outgoing stack argument areas preserve 4-cell alignment.

This alignment supports both 2-cell integer memory objects and 4-cell capability memory objects without dynamic realignment for ordinary frames.

Raw 2-cell integer pushes may temporarily leave `DSC.cursor` 2-cell aligned but not 4-cell aligned. Code must restore 4-cell alignment before a public call boundary, before capability stack operations, and before any frame state that requires capability-slot alignment.

## Stack Objects

| Object | Size | Required alignment | Access operation |
| --- | ---: | ---: | --- |
| 48-bit integer spill | 2 cells | 2 cells | `LD48` / `ST48` through `DSC` |
| 96-bit capability spill | 4 cells plus tag | 4 cells | `CLC` / `CSC` through `DSC` |
| Outgoing integer stack argument | 2 cells | 2 cells | `LD48` / `ST48` through `DSC` |
| Outgoing capability stack argument | 4 cells plus tag | 4 cells | `CLC` / `CSC` through `DSC` |

Sub-cell values stored in stack memory are still contained in whole cells or larger ABI slots. v0.1 does not define byte-addressed stack slots.

## `PUSH` and `POP`

`PUSH` and `POP` operate on `DSC`.

They are ABI stack operations; the final ISA encoding may expose them as real instructions, macro-ops, or assembler pseudoinstructions. Their architectural effect is defined in cells.

### Integer Push and Pop

Integer push of a 48-bit value:

```text
target = DSC.cursor - 2
check target is 2-cell aligned
check [target, target + 2) is in DSC bounds
store 48-bit value through DSC at target
DSC.cursor = target
```

Integer pop of a 48-bit value:

```text
target = DSC.cursor
result = DSC.cursor + 2
check target is 2-cell aligned
check [target, target + 2) is in DSC bounds
check result is in DSC bounds
load 48-bit value through DSC at target
DSC.cursor = result
```

The resulting `DSC.cursor` after pop must remain in bounds. Software must not pop past the initialized stack anchor or caller-owned frame state.

### Capability Push and Pop

Capability push:

```text
target = DSC.cursor - 4
check target is 4-cell aligned
check [target, target + 4) is in DSC bounds
store capability payload and tag through DSC at target
DSC.cursor = target
```

Capability pop:

```text
target = DSC.cursor
result = DSC.cursor + 4
check target is 4-cell aligned
check [target, target + 4) is in DSC bounds
check result is in DSC bounds
load capability payload and tag through DSC at target
DSC.cursor = result
```

Capability push uses `CSC` semantics. Storing a local capability requires `DSC` to have `ST`, `SC`, and `SL`.

## Fault Atomicity

A faulting stack operation leaves architectural state unchanged:

- Faulting push leaves `DSC`, memory payload, and memory tags unchanged.
- Faulting pop leaves `DSC` and the destination register unchanged.
- Misaligned stack object access raises `ALIGN_FAULT`.
- Missing stack capability permissions raise the corresponding capability fault.
- Storing a local capability through `DSC` without `SL` raises capability local-store fault.

## Example Frame

For a 16-cell frame allocated from entry `DSC.cursor = 0x1800`:

```text
new DSC.cursor = 0x17F0

0x17F0-0x17F3  capability spill slot 0
0x17F4-0x17F7  capability spill slot 1
0x17F8-0x17F9  integer spill slot 0
0x17FA-0x17FB  integer spill slot 1
0x17FC-0x17FF  outgoing capability argument slot
```

All capability slots are 4-cell aligned. All integer slots are 2-cell aligned. The total frame size preserves 4-cell alignment at the next call boundary.

## Local Capability Storage

The data stack is the normal place to spill local capabilities.

Rules:

- A stack capability used for capability spills must have `ST`, `SC`, and `SL`.
- `CSC` of a local capability through `DSC` succeeds only when `DSC` has `SL`.
- `CSC` of a local capability through a heap or global capability without `SL` raises capability local-store fault.
- Loading a spilled capability with `CLC` preserves its tag and `G` flag.
- `ST48` into a capability spill slot clears that slot's tag according to E03-S04.

This is compatible with E03-S05: stack memory may explicitly permit local stores, while ordinary long-lived memory normally omits `SL`.

## Out of Scope for This Story

- Integer and capability argument register assignment: E05-S01 and E05-S02.
- Protected return stack layout and access: E05-S04.
- Control-transfer behavior for calls and returns: E04-S04 and E06-S03.
- Trap stack behavior: E07-S04 and E11-S02.
- Exact instruction encodings for stack operations: E04-S06.

## Verification Notes

Minimum conformance checks for later simulator and toolchain work:

- Public call-boundary `DSC.cursor` values are 4-cell aligned.
- Frame sizes emitted by the toolchain are multiples of 4 cells.
- Integer spill slots are 2-cell aligned.
- Capability spill slots are 4-cell aligned.
- Integer push subtracts 2 cells and stores through `DSC`.
- Integer pop loads through `DSC` and adds 2 cells.
- Capability push subtracts 4 cells and stores payload plus tag through `DSC`.
- Capability pop loads payload plus tag through `DSC` and adds 4 cells.
- Push below `DSC.base` faults and leaves `DSC` unchanged.
- Pop outside `DSC.bounds` faults and leaves `DSC` unchanged.
- Local capability push without `SL` raises capability local-store fault.
- `ST48` overlapping a capability spill slot clears that slot's tag.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `DSC` is the data-stack capability. | Met. |
| Data stack grows downward in cells. | Met. |
| `PUSH` and `POP` operate on `DSC`. | Met. |
| Stack alignment is specified. | Met: 4-cell ABI alignment, with 2-cell integer and 4-cell capability slots. |
| Local capability storage rules are compatible with `SL`. | Met. |

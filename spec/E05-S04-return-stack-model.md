# E05-S04: Return Stack Model

Story: E05-S04

Status: Complete

Normative source: `design.md`, sections 8 and 9

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E03-S03-capability-derivation.md`
- `spec/E06-S03-sealed-return-capabilities.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E03-S05-local-capabilities.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E05-S03-data-stack-model.md`

## Decision

`RSC` is the protected return-stack capability for CPU v0.1.

The protected return stack stores sealed return capabilities used by `CALL` and `RET`. It is separate from the data stack governed by `DSC`.

Return-stack storage is not ordinary spill storage. Normal program data, integer stores, and explicit capability stores do not use `RSC`; only `CALL`, `RET`, and later privileged unwind/debug operations may access protected return-stack slots.

## Stack Direction and Slot Format

The protected return stack grows downward in cell addresses, matching the data-stack growth direction.

Each return-stack entry is one naturally aligned 4-cell capability slot:

| Property | Value |
| --- | ---: |
| Entry size | 4 cells |
| Entry alignment | 4 cells |
| Entry payload | 96-bit capability payload |
| Entry tag | One out-of-band capability tag |
| Required stored type | Valid sealed return capability with `otype = OTYPE_RETURN` |

The memory tag rules for 4-cell capability slots still apply. A valid return-stack entry is represented by the 96-bit sealed return-capability payload and a valid memory tag.

## `RSC` Capability Requirements

The runtime or kernel initializes `RSC` as a valid, unsealed capability whose bounds cover the thread's protected return-stack region.

Recommended `RSC` properties:

| Field or permission | Required value |
| --- | --- |
| Tag | Valid |
| Seal state | Unsealed |
| Bounds | Covers only the protected return-stack region for the current thread or activation context |
| Cursor | Current protected return-stack pointer |
| `ST` | Required for `CALL` push |
| `SC` | Required for `CALL` push |
| `SL` | Required for `CALL` push because sealed return capabilities are local |
| `LD` | Required for `RET` pop |
| `LC` | Required for `RET` pop |
| `G` | Should normally be local (`G=0`) |

`RSC.cursor` must always be a 4-cell aligned in-bounds cell address while a thread is runnable.

Because v0.1 capabilities require in-bounds cursors, an empty protected return stack is represented by an in-bounds anchor slot at the top of the region. Software must initialize the return-stack region with at least one unused anchor slot above the first pushed return entry.

## Protected Access Rule

Protected return-stack memory is reachable by:

- The implicit `CALL` protected push operation.
- The implicit `RET` protected pop operation.
- Privileged unwind/debug operations defined by later stories.
- Firmware or kernel initialization before the thread is entered.

Protected return-stack memory is not reachable by ordinary data operations:

- `LD48` and `ST48` through general capability registers, `DSC`, or `DDC` must not access protected return-stack storage.
- `CLC` and `CSC` through general capability registers, `DSC`, or `DDC` must not access protected return-stack storage.
- Ordinary software cannot use `RSC` as an explicit source operand for load/store instructions.
- User mode cannot read or write `RSC` through CCSR access.

If an ordinary load or store attempts to access protected return-stack storage through any non-`RSC` authority, the access raises `RETURN_STACK_PERMISSION_FAULT` and leaves architectural state unchanged.

This rule is stronger than relying only on capability distribution. It preserves backward-edge integrity even if a malformed or compromised context obtains a general data capability whose numeric bounds overlap the protected return-stack memory region.

## Protected Push on `CALL`

`CALL` pushes the sealed return capability created by E06-S03.

Architectural effect:

```text
target = RSC.cursor - 4
check target is 4-cell aligned
check [target, target + 4) is in RSC bounds
check RSC has ST, SC, and SL
store return_cap payload and tag at target
RSC.cursor = target
```

Additional checks:

- `RSC.tag` must be valid.
- `RSC` must be unsealed.
- `return_cap.tag` must be valid.
- `return_cap.otype` must be `OTYPE_RETURN`.
- `return_cap.G` must be `0`.

On success, the memory payload, memory tag, `RSC.cursor`, and `PCC` control transfer commit atomically as part of the `CALL` instruction.

On failure, no return capability is stored, `RSC` is unchanged, and `PCC` is unchanged.

## Protected Pop on `RET`

`RET` pops one sealed return capability.

Architectural effect:

```text
target = RSC.cursor
result = RSC.cursor + 4
check target is 4-cell aligned
check [target, target + 4) is in RSC bounds
check result is in RSC bounds
check RSC has LD and LC
load return_cap payload and tag from target
validate return_cap according to E06-S03
RSC.cursor = result
install unsealed return_cap into PCC with slot 0
```

Additional checks:

- `RSC.tag` must be valid.
- `RSC` must be unsealed.
- The loaded memory tag must be valid.
- The loaded capability must be sealed with `OTYPE_RETURN`.
- The loaded capability must satisfy the return-target checks defined by E06-S03.

On success, the `RSC.cursor` update and `PCC` installation commit atomically as part of the `RET` instruction.

On failure, `RSC`, `PCC`, memory payload, and memory tags are unchanged.

## Underflow, Overflow, and Permission Faults

Return-stack failures are named so tests and later exception encoding can distinguish them.

| Case | Named fault | Baseline architectural class |
| --- | --- | --- |
| `CALL` push target is below `RSC.base` or outside `RSC` bounds | `RETURN_STACK_OVERFLOW` | Capability bounds fault |
| `RET` pop target does not name a valid pushed entry | `RETURN_STACK_UNDERFLOW` | Capability bounds fault or capability tag fault |
| `RSC.tag` is invalid | `RETURN_STACK_PERMISSION_FAULT` | Capability tag fault |
| `RSC` is sealed | `RETURN_STACK_PERMISSION_FAULT` | Capability seal/type fault |
| `CALL` push lacks `ST`, `SC`, or `SL` in `RSC` | `RETURN_STACK_PERMISSION_FAULT` | Capability permission fault or capability local-store fault |
| `RET` pop lacks `LD` or `LC` in `RSC` | `RETURN_STACK_PERMISSION_FAULT` | Capability permission fault |
| Ordinary load/store accesses protected return-stack storage | `RETURN_STACK_PERMISSION_FAULT` | Capability permission fault |
| Protected return-stack slot is not 4-cell aligned | `ALIGN_FAULT` | Alignment fault |

`RETURN_STACK_UNDERFLOW`, `RETURN_STACK_OVERFLOW`, and `RETURN_STACK_PERMISSION_FAULT` are architectural fault names. E07-S02 assigns final exception encodings and priority.

For capability-fault reporting:

- `FAULTCAPIDX = RSC` for faults caused by `RSC` authorization or bounds.
- `TVAL` reports the attempted return-stack slot address when one exists.
- `CAPCAUSE` reports `TAG`, `BOUNDS`, `PERMISSION`, `LOCAL_STORE`, or `SEAL_TYPE` according to the baseline architectural class.

## Empty and Full Conditions

The protected return-stack region is described by `RSC.bounds = [base, top)`.

The region must contain at least one 4-cell anchor slot so `RSC.cursor` remains in bounds when no return entries are present.

With a downward-growing return stack:

- The empty state is `RSC.cursor = empty_anchor`, where `empty_anchor` is a 4-cell aligned in-bounds address selected by runtime or kernel setup.
- `RET` at the empty state raises `RETURN_STACK_UNDERFLOW`.
- A non-empty state has `RSC.cursor` naming the lowest-addressed active return entry.
- `CALL` overflow occurs when `RSC.cursor - 4` is outside `RSC.bounds`.

The architecture does not reserve a scalar CSR for the empty anchor in v0.1. The ABI, runtime, or kernel tracks the bottom-of-live-stack convention for each thread and initializes guard memory so underflow is detected by tag, bounds, or protected-stack metadata checks.

## Ordinary-store Interaction

Ordinary stores cannot forge a valid return capability.

If a privileged debugger or firmware intentionally overwrites a protected return-stack slot with integer stores, the memory tag is cleared according to E03-S04. A later `RET` from that slot raises capability tag fault and the named `RETURN_STACK_UNDERFLOW` or return-slot tag failure according to the final exception story.

If a privileged unwind/debug operation writes a replacement return entry, it must write the full 96-bit payload and tag as one capability-slot update and must install a valid sealed `OTYPE_RETURN` capability. E06-S04 and E12 debug stories define those controlled operations.

## Context Switching

`RSC` is per-core architectural state, but the authority it carries belongs to the currently running thread or privileged context.

Kernel context-switch code must save and restore `RSC` along with other special capability state. User mode cannot directly inspect or replace `RSC`.

A context switch must not expose one thread's protected return-stack authority to another thread.

## Out of Scope for This Story

- Full `CALL`, `CALLC`, `RET`, branch, trap, and `IRET` instruction semantics: E04-S04, E06-S02, E06-S03, and E07-S04.
- Trap/debug interaction while return-stack state is partially updated: E06-S04 and E14-S05.
- Privileged unwind/debug operation encodings: E12 stories.
- Reset-time initialization of `RSC`: E11-S02.
- Final exception cause encodings and priority: E07-S02 and E07-S03.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `RSC` is the only normal architectural authority used by `CALL` and `RET` for protected return-stack storage.
- `CALL` subtracts 4 cells from `RSC.cursor` for the protected push.
- `CALL` stores a valid sealed `OTYPE_RETURN` capability and tag at the pushed slot.
- `CALL` requires `RSC` to have `ST`, `SC`, and `SL`.
- `CALL` below `RSC.bounds` raises `RETURN_STACK_OVERFLOW`.
- Faulting `CALL` leaves `RSC`, `PCC`, memory payload, and memory tags unchanged.
- `RET` loads the capability and tag from the slot named by `RSC.cursor`.
- `RET` adds 4 cells to `RSC.cursor` after a successful pop.
- `RET` from the empty state raises `RETURN_STACK_UNDERFLOW`.
- `RET` requires `RSC` to have `LD` and `LC`.
- Faulting `RET` leaves `RSC`, `PCC`, memory payload, and memory tags unchanged.
- `ST48` through non-`RSC` authority cannot write protected return-stack memory.
- `CSC` through non-`RSC` authority cannot write protected return-stack memory.
- User-mode `CCSRRD` or `CCSRWR` of `RSC` raises privilege fault according to E02-S05.
- Integer overwrite by a privileged/debug path clears the return slot tag.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `RSC` is the protected return-stack capability. | Met. |
| `CALL` and `RET` operate on `RSC`. | Met. |
| Ordinary data stores cannot write protected return-stack memory unless explicitly allowed by the architecture. | Met. |
| Return stack underflow, overflow, and permission faults are named. | Met. |

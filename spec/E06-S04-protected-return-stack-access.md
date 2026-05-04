# E06-S04: Protected Return Stack Access

Story: E06-S04

Status: Complete

Normative source: `design.md`, sections 8, 9, 10.2, and 16.3

Supporting spike: `spikes/E14-S05-protected-return-stack-traps.md`

Prerequisites:

- `spec/E05-S04-return-stack-model.md`
- `spec/E07-S03-precise-exception-model.md`
- `spikes/E14-S05-protected-return-stack-traps.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E07-S02-exception-classes.md`

## Decision

Protected return-stack memory is an architectural protected storage class.

It is reachable only through:

- The implicit `CALL` protected push path.
- The implicit `RET` protected pop path.
- Privileged protected-return-stack maintenance operations defined by this story.
- Firmware or kernel setup before a region is made runnable as protected return-stack storage.

Ordinary memory instructions do not access protected return-stack storage, even in kernel mode and even when their authorizing capability numerically covers the same cell addresses.

This rule is independent of capability distribution. A data capability, `DSC`, or `DDC` that overlaps protected return-stack addresses does not become return-stack authority.

## Protected Storage Classification

Hardware must classify whether an effective memory access overlaps protected return-stack storage before the access can read payload, write payload, write a capability tag, clear a capability tag, or allocate a store-buffer entry.

The exact implementation mechanism is platform-defined until the virtual-memory protection stories assign page-table attributes. Valid implementation choices include:

- A memory-region attribute for protected return-stack pages or physical ranges.
- A per-thread protected return-stack region descriptor associated with context state.
- A TLB or cache-line attribute derived from privileged memory-management metadata.

Architectural requirements:

- `RSC.bounds` for a runnable thread must be contained within protected return-stack storage for that thread or activation context.
- The protected classification must be changed only by kernel, firmware, or debug authority.
- User mode cannot classify ordinary memory as protected return-stack storage.
- User mode cannot remove protected classification from return-stack storage.
- A context switch must install both the correct `RSC` authority and the matching protected storage classification for the selected thread.

If a region is being initialized before it is runnable, firmware or the kernel may write it before setting the protected classification. Once classified as protected return-stack storage, ordinary stores are blocked by this story.

## Ordinary Access Restrictions

The restriction applies to every ordinary data-memory instruction, including:

- Integer loads and stores such as `LD48` and `ST48`.
- Capability loads and stores such as `CLC` and `CSC`.
- Stack operations through `DSC`.
- Default-data operations through `DDC`.
- General capability-register addressing.
- Future ordinary block, vector, or cacheable data-memory operations unless their owning story explicitly routes through the protected return-stack path.

When an ordinary data-memory instruction's effective access range overlaps protected return-stack storage:

- The instruction raises `RETURN_STACK_PERMISSION_FAULT`.
- The faulting instruction does not retire.
- Destination integer or capability registers are unchanged.
- Memory payload is unchanged.
- Memory capability tags are unchanged.
- `ST48` does not clear an overlapped return-slot tag.
- `CSC` does not write payload or tag.
- No store-buffer entry is allocated.
- `RSC` is unchanged.

The ordinary access restriction applies in both `U` and `K` privilege. Kernel mode must use CCSR context management and the privileged maintenance operations below; it must not repair return-stack storage through ordinary loads or stores after the region is protected.

## Ordinary Fault Priority

For ordinary data-memory instructions, the access restriction is checked after enough instruction-local checks have completed to know the effective access range.

Baseline order:

1. Decode, operand, and privilege checks for the instruction form.
2. Authorizing capability tag and seal-state checks.
3. Address generation, representability, alignment, and authorizing-capability bounds checks.
4. Protected return-stack storage classification.
5. Ordinary load/store permission, translation, memory-type, cache, and access-fault checks owned by later stories.

If step 4 finds an overlap, the selected cause is `RETURN_STACK_PERMISSION_FAULT`.

E09-S07 may refine the relative priority between protected-return-stack classification and page-table faults once page attributes are defined. It must preserve deterministic selection and the no-side-effect rule above.

## Protected Push Transaction

`CALL` uses the protected push transaction.

The transaction prepares:

```text
continuation = slot-0 call continuation
return_cap = derive sealed local OTYPE_RETURN from current PCC
target_slot = RSC.cursor - 4
next_rsc_cursor = target_slot
next_pcc = call target, slot 0
```

Required checks:

- Current `PCC` checks and call-continuation checks from E06-S03.
- Target control-transfer checks from E06-S01 and the later control-transfer story.
- `RSC.tag` is valid.
- `RSC` is unsealed.
- `target_slot` is 4-cell aligned.
- `[target_slot, target_slot + 4)` is within `RSC.bounds`.
- `target_slot` overlaps protected return-stack storage for the current context.
- `RSC` has `ST`, `SC`, and `SL`.
- `return_cap.tag` is valid.
- `return_cap` is sealed with `OTYPE_RETURN`.
- `return_cap.G = 0`.

At normal retire, hardware commits these effects as one architectural action:

- Store the 96-bit return-capability payload at `target_slot`.
- Set the memory tag for `target_slot`.
- Set `RSC.cursor = next_rsc_cursor`.
- Set `PCC = next_pcc`.
- Set `PCC.slot = 0`.

If any check fails, none of those effects commit.

`CALL` overflow reports `RETURN_STACK_OVERFLOW`, `CAPCAUSE=BOUNDS`, `FAULTCAPIDX=RSC`, and `TVAL=target_slot` when `target_slot` can be represented.

Other `RSC` authorization failures report `RETURN_STACK_PERMISSION_FAULT` with `CAPCAUSE` set to `TAG`, `SEAL_TYPE`, `PERMISSION`, or `LOCAL_STORE` according to the failing check.

## Protected Pop Transaction

`RET` uses the protected pop transaction.

The transaction prepares:

```text
target_slot = RSC.cursor
next_rsc_cursor = RSC.cursor + 4
return_cap = memory capability at target_slot
next_pcc = unsealed return_cap, slot 0
```

Required checks:

- `RSC.tag` is valid.
- `RSC` is unsealed.
- `target_slot` is 4-cell aligned.
- `[target_slot, target_slot + 4)` is within `RSC.bounds`.
- `next_rsc_cursor` is in `RSC.bounds`.
- `target_slot` overlaps protected return-stack storage for the current context.
- `RSC` has `LD` and `LC`.
- The loaded memory tag is valid.
- The loaded capability is sealed with `OTYPE_RETURN`.
- The loaded capability has `G=0`.
- The loaded return target is in bounds, execute-authorized, and slot 0 according to E06-S03.

At normal retire, hardware commits these effects as one architectural action:

- Set `RSC.cursor = next_rsc_cursor`.
- Install the unsealed return capability into `PCC`.
- Set `PCC.slot = 0`.

`RET` does not clear the popped memory slot. After `RSC.cursor` advances, that slot is inactive and must be overwritten by a later `CALL` before it becomes active again.

If any check fails, none of the normal effects commit. `RSC`, `PCC`, return-stack memory payload, and return-stack memory tags are unchanged.

`RET` underflow reports `RETURN_STACK_UNDERFLOW`, `FAULTCAPIDX=RSC`, and `TVAL=target_slot` when:

- `target_slot` does not name a valid active return slot.
- `next_rsc_cursor` would leave `RSC.bounds`.
- The slot is the runtime empty-anchor convention, as detected by tag, bounds, or protected-stack metadata.
- The slot tag or return-capability type proves there is no valid pushed return entry.

`CAPCAUSE` is `BOUNDS`, `TAG`, or `SEAL_TYPE` according to the failing condition.

## Transaction Visibility

`CALL`, `RET`, and protected maintenance writes use a protected return-stack transaction latch.

Before retire, the transaction latch is not architectural state. It must not be visible through:

- Trap entry.
- Interrupt entry.
- Debug halt entry.
- Single-step completion.
- `CCSRRD RSC`.
- `CLC` or `LD48`.
- Any privileged protected-return-stack maintenance operation.

At retire, the transaction either commits all of its effects or discards all of them.

No architectural observer may see:

- Return-slot payload without the matching tag.
- Return-slot tag without the matching payload.
- Updated `RSC.cursor` without the matching return-slot update for `CALL`.
- Updated `PCC` without the matching `RSC.cursor` update for `CALL` or `RET`.
- A debug halt boundary inside a protected return-stack transaction.

## Trap, Interrupt, and Debug Timing

Trap, interrupt, and debug paths observe only precise instruction boundaries.

| Event timing | Required observation |
| --- | --- |
| Trap, interrupt, or debug entry before `CALL` starts | Pre-`CALL` `RSC`, return-stack memory, tags, and `PCC`. |
| `CALL` faults | No return capability is stored, `RSC` is unchanged, `PCC` is unchanged, and `EPCC` identifies the faulting `CALL`. |
| `CALL` retires then a trap, interrupt, or debug entry occurs | The pushed return slot, return tag, new `RSC.cursor`, and new `PCC` are all visible. |
| Trap, interrupt, or debug entry before `RET` starts | Pre-`RET` `RSC`, return-stack memory, tags, and `PCC`. |
| `RET` faults | `RSC` is unchanged, `PCC` is unchanged, return-stack memory and tags are unchanged, and `EPCC` identifies the faulting `RET`. |
| `RET` retires then a trap, interrupt, or debug entry occurs | The advanced `RSC.cursor` and restored `PCC` are both visible. |
| Maskable interrupt pending during `CALL` or `RET` execution | Delivered before the instruction starts or after it retires; it does not split the instruction. |
| Debug halt request during `CALL` or `RET` execution | Delivered before the instruction starts or after commit or rollback; it does not expose partial protected state. |
| Single-step completion for `CALL` or `RET` | Observes the post-retire state of the whole instruction. |

Trap entry itself does not push to or pop from the protected return stack in v0.1. It preserves `RSC` as interrupted architectural context unless the later trap-entry story explicitly defines a software convention that changes `RSC` after trap entry has completed.

## Privileged Maintenance Operations

E06-S04 defines the architectural semantics of protected return-stack maintenance operations. Exact instruction encodings, debug transport, and optional raw debug inspection are deferred to E12 and later opcode stories.

Required operations:

| Operation | Required authority | Normal effect |
| --- | --- | --- |
| Protected peek | `K` privilege or debug mode at a precise boundary | Validate and read a sealed return capability and tag from an active return slot. |
| Protected drop | `K` privilege or debug mode at a precise boundary | Validate the top active slot, then advance `RSC.cursor` by 4. |
| Protected replace | `K` privilege or debug mode at a precise boundary | Validate a replacement sealed return capability, then atomically replace one active slot payload and tag. |

All protected maintenance operations:

- Use the current architectural `RSC`.
- Require `RSC.tag` to be valid.
- Require `RSC` to be unsealed.
- Require the addressed slot to be 4-cell aligned and within `RSC.bounds`.
- Require the addressed slot to overlap protected return-stack storage for the current context.
- Are precise, retire-time architectural operations.
- Fault without changing `RSC`, `PCC`, memory payload, or memory tags.

## Active Slot Detection

An active return-stack slot is a slot within `RSC.bounds` that is protected for the current context and contains a valid sealed local `OTYPE_RETURN` capability satisfying the return-target checks.

The architecture does not require a hardware depth counter or scalar empty-anchor CSR. Runtime and kernel software still own the empty-anchor convention from E05-S04. Hardware detects an attempted access outside the active stack through the existing bounds, tag, seal/type, and protected-stack metadata checks.

## Protected Peek

Protected peek computes:

```text
slot = RSC.cursor + depth * 4
```

Rules:

- `depth` is a nonnegative integer selected by the maintenance operation.
- `slot` must name an active return-stack slot.
- `RSC` must have `LD` and `LC`.
- The slot tag must be valid.
- The slot payload must be a sealed local `OTYPE_RETURN` capability.
- The return capability must satisfy the E06-S03 return-target validation checks.

On success, the operation returns the sealed return-capability payload and tag to the privileged or debug destination defined by the owning encoding story. It does not alter `RSC`, `PCC`, memory payload, or memory tags.

Protected peek is not a raw memory read. If the active return slot is corrupt, protected peek faults instead of returning malformed authority.

## Protected Drop

Protected drop removes the top active return entry without changing `PCC`.

Rules:

- It addresses `slot = RSC.cursor`.
- It uses the same slot and return-capability validation as protected peek at depth 0.

At normal retire:

```text
RSC.cursor = RSC.cursor + 4
```

Protected drop does not clear the dropped slot. The slot becomes inactive and is overwritten by a later `CALL` before reuse.

## Protected Replace

Protected replace computes:

```text
slot = RSC.cursor + depth * 4
```

Rules:

- `depth` is a nonnegative integer selected by the maintenance operation.
- `slot` must name an active return-stack slot.
- `RSC` must have `ST`, `SC`, and `SL`.
- The replacement source must already carry a valid capability tag.
- The replacement source must be sealed with `OTYPE_RETURN`.
- The replacement source must have `G=0`.
- The replacement source must satisfy the E06-S03 return-target validation checks.

At normal retire, the full 96-bit replacement payload and the memory tag are written as one capability-slot update.

Protected replace does not change `RSC.cursor` or `PCC`.

## Maintenance Faults

Protected maintenance operations use the E07-S02 return-stack causes where the failure is return-stack specific.

| Failure | Cause | Reporting |
| --- | --- | --- |
| Insufficient privilege or debug authority | `PRIVILEGE_FAULT` or debug-specific cause from E12 | `TVAL=0` unless E12 defines more detail. |
| `RSC.tag` invalid | `RETURN_STACK_PERMISSION_FAULT` | `CAPCAUSE=TAG`, `FAULTCAPIDX=RSC`. |
| `RSC` sealed | `RETURN_STACK_PERMISSION_FAULT` | `CAPCAUSE=SEAL_TYPE`, `FAULTCAPIDX=RSC`. |
| Missing required `RSC` permission | `RETURN_STACK_PERMISSION_FAULT` | `CAPCAUSE=PERMISSION` or `LOCAL_STORE`, `FAULTCAPIDX=RSC`. |
| Slot outside `RSC.bounds` or above active stack | `RETURN_STACK_UNDERFLOW` | `CAPCAUSE=BOUNDS`, `FAULTCAPIDX=RSC`, `TVAL=slot`. |
| Existing slot tag invalid | `RETURN_STACK_UNDERFLOW` | `CAPCAUSE=TAG`, `FAULTCAPIDX=RSC`, `TVAL=slot`. |
| Existing slot has wrong seal/type | `RETURN_STACK_UNDERFLOW` | `CAPCAUSE=SEAL_TYPE`, `FAULTCAPIDX=RSC`, `TVAL=slot`. |
| Replacement source invalid or wrong type | `RETURN_STACK_PERMISSION_FAULT` | `CAPCAUSE=TAG`, `SEAL_TYPE`, `PERMISSION`, or `LOCAL_STORE`; source index is reported if the encoding exposes one, otherwise `FAULTCAPIDX=UNKNOWN`. |

If a maintenance operation has multiple failures, it follows the same deterministic check order as the corresponding protected peek, drop, or replace rule above.

## Hardware Assists

An implementation must provide the following architectural assists, though the microarchitecture may name them differently:

| Assist | Required architectural property |
| --- | --- |
| Protected storage classifier | Identifies protected return-stack storage before ordinary memory side effects. |
| Protected return-stack transaction latch | Holds slot payload, tag, next `RSC.cursor`, and next `PCC` until retire. |
| Retire-time commit gate | Commits or discards all effects of `CALL`, `RET`, and protected maintenance operations atomically. |
| Whole-slot tag/data path | Moves return-capability payload and tag together. |
| Debug/trap boundary arbiter | Delivers trap, interrupt, debug halt, and single-step only at precise protected-transaction boundaries. |
| Return-stack fault packet | Carries selected `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX` for return-stack faults. |

These assists do not require a reorder buffer, a hardware return-stack depth CSR, or a globally drained store buffer.

If an implementation buffers committed protected return-stack writes internally, same-core `RET`, protected maintenance operations, and trap/debug observation must see older committed writes through forwarding or an equivalent ordered path.

## Out of Scope for This Story

- Concrete encodings for protected peek, drop, and replace: E12 and later opcode stories.
- Raw debug memory inspection of corrupt protected return-stack slots: E12 stories.
- Direct trap-entry write sequence and trap-target calculation: E07-S04.
- Full branch, `CALL`, `RET`, `IRET`, `SYS`, `BRK`, `WFI`, and `PAUSE` instruction semantics: E04-S04.
- Page-table attributes used to classify protected return-stack pages: E09 stories.
- Context-switch ABI details beyond preserving `RSC` and protected classification.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CALL` reaches protected return-stack memory only through the protected push path.
- `RET` reaches protected return-stack memory only through the protected pop path.
- Successful `CALL` commits slot payload, slot tag, `RSC.cursor`, and `PCC` together.
- Faulting `CALL` leaves `RSC`, `PCC`, memory payload, and memory tags unchanged.
- Successful `RET` commits `RSC.cursor` and `PCC` together.
- Faulting `RET` leaves `RSC`, `PCC`, memory payload, and memory tags unchanged.
- A trap, interrupt, debug halt, or single-step event cannot observe a partial `CALL` or `RET`.
- `LD48` through a general capability overlapping protected return-stack storage raises `RETURN_STACK_PERMISSION_FAULT`.
- `ST48` through a general capability overlapping protected return-stack storage raises `RETURN_STACK_PERMISSION_FAULT` and does not clear the return-slot tag.
- `CLC` through `DSC`, `DDC`, or a general capability overlapping protected return-stack storage raises `RETURN_STACK_PERMISSION_FAULT`.
- `CSC` through `DSC`, `DDC`, or a general capability overlapping protected return-stack storage raises `RETURN_STACK_PERMISSION_FAULT` and writes no payload or tag.
- Kernel-mode ordinary stores are still blocked from protected return-stack storage.
- Protected peek returns only a valid sealed local `OTYPE_RETURN` capability from an active slot.
- Protected drop advances `RSC.cursor` by 4 and does not change `PCC`.
- Protected replace writes a full 96-bit payload and tag atomically and does not change `RSC.cursor` or `PCC`.
- Protected maintenance operations fault without partial state changes.
- Underflow, overflow, and protected permission failures report `FAULTCAPIDX=RSC` when caused by `RSC`.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Return-stack memory is reachable by `CALL` and `RET`. | Met. |
| Privileged unwind/debug access rules are defined. | Met: protected peek, drop, and replace are specified. |
| Ordinary store access restrictions are specified. | Met: ordinary loads/stores are blocked for protected return-stack storage in both `U` and `K`. |
| Trap behavior while return stack state is partially updated is precise. | Met: protected transactions are visible only before or after retire. |

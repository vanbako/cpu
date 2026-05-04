# E14-S05: Protected Return Stack Trap and Debug Spike

Story: E14-S05

Status: Spike complete

Prototype: `tools/return_stack_trap_model.py`

Related stories:

- E05-S04: Return stack model
- E06-S03: Sealed return capabilities
- E07-S03: Precise exception model
- E12-S01: Debug halt model

## Question

Can `CALL`, `RET`, trap entry, and debug unwind access share a protected return stack without exposing partially updated `RSC`, return-stack memory, memory tags, or `PCC`?

## Prototype Model

The prototype models the protected return stack as a small architectural state machine:

- `RSC.bounds = [base, top)`.
- The stack grows downward in 4-cell capability slots.
- The empty state uses the in-bounds anchor slot at `top - 4`.
- `CALL` creates a sealed local `OTYPE_RETURN` capability and pushes it through `RSC`.
- `RET` loads and validates the sealed return capability at `RSC.cursor`.
- Debug unwind access is allowed only after the core is halted at a precise architectural boundary.

The prototype is not cycle accurate. It treats `CALL`, `RET`, and debug writes as transactions whose internal phases are invisible until retire.

## Proposed Ordering

### `CALL`

`CALL target` should be implemented as one retire-time transaction:

```text
continuation = slot-0 call continuation
return_cap = derive sealed local OTYPE_RETURN from current PCC
target_slot = RSC.cursor - 4
check RSC tag, seal state, bounds, ST, SC, and SL
check target control transfer
at retire:
    store return_cap payload and tag at target_slot
    RSC.cursor = target_slot
    PCC = target, slot 0
```

If any check fails, the transaction is discarded. `RSC`, return-stack memory, memory tags, and `PCC` remain unchanged.

### `RET`

`RET` should be implemented as one retire-time transaction:

```text
target_slot = RSC.cursor
result_cursor = RSC.cursor + 4
check RSC tag, seal state, bounds, LD, and LC
load return_cap payload and tag from target_slot
validate return_cap tag, OTYPE_RETURN, local state, bounds, and EX
at retire:
    RSC.cursor = result_cursor
    PCC = unsealed return_cap, slot 0
```

`RET` does not need to clear the popped slot. The slot is outside the active stack after `RSC.cursor` advances and is overwritten by a later `CALL` before it becomes active again.

If any check fails, the transaction is discarded. `RSC`, return-stack memory, memory tags, and `PCC` remain unchanged.

## Trap and Debug Interaction

The precise exception model already requires `CALL` and `RET` to be all-or-nothing. The spike resolves the remaining trap/debug timing rules this way:

| Event timing | Required architectural observation |
| --- | --- |
| Trap, interrupt, or debug request before a `CALL` or `RET` starts | Pre-instruction `RSC`, return-stack memory, tags, and `PCC`. |
| Synchronous fault inside `CALL` | No return capability stored, `RSC` unchanged, `PCC` unchanged, `EPCC` identifies the faulting `CALL`. |
| Synchronous fault inside `RET` | No cursor update, `PCC` unchanged, return-stack memory and tags unchanged, `EPCC` identifies the faulting `RET`. |
| Maskable interrupt pending while `CALL` or `RET` is executing | Delivered only at an instruction boundary, before the instruction starts or after it retires. |
| Debug halt request while `CALL` or `RET` is executing | Enters debug only at a precise boundary, before the instruction starts or after commit or rollback. |
| Single-step completion for `CALL` or `RET` | Observes the post-retire state after both `RSC` and `PCC` have updated. |

No trap, interrupt, debug entry, breakpoint, or single-step event may observe a slot payload without its tag, a tag without its payload, a changed `RSC.cursor` without the corresponding `PCC`, or a changed `PCC` without the corresponding `RSC.cursor`.

## Debug Unwind Access

Debug unwind access should be a privileged protected-return-stack path, not ordinary memory access through `DSC`, `DDC`, or a general capability register.

Minimum operations for E06-S04 and E12 to specify:

| Operation | Semantics |
| --- | --- |
| Debug peek | Read a sealed return capability and tag at `RSC.cursor + depth * 4` without changing state. |
| Debug drop | Validate the top return slot, then advance `RSC.cursor` by 4 without changing `PCC`. |
| Debug replace | Validate a replacement sealed local `OTYPE_RETURN` capability, then atomically write its payload and tag to an active return slot. |

Rules:

- These operations require kernel/debug authority and a precise halted boundary.
- They must use whole 4-cell capability-slot reads and writes.
- They must preserve the same tag atomicity as `CLC` and `CSC`.
- They must reject unsealed, wrong-type, invalid-tag, non-executable, or global replacement capabilities.
- They must report `RETURN_STACK_UNDERFLOW`, `RETURN_STACK_OVERFLOW`, or `RETURN_STACK_PERMISSION_FAULT` using the E07-S02 return-stack causes when the failing condition is return-stack specific.

Optional debug push or frame-insert operations can be deferred. The minimum unwind contract only needs inspect, drop, and replace.

## Prototype Results

Command:

```text
python .\tools\return_stack_trap_model.py
```

Output:

| scenario | result |
| --- | --- |
| CALL trap windows | no architectural return-stack or PCC update before retire |
| RET trap windows | no architectural pop or PCC update before retire |
| RET underflow | `RETURN_STACK_UNDERFLOW CAPCAUSE=BOUNDS TVAL=0x101C FAULTCAPIDX=RSC` |
| CALL overflow | `RETURN_STACK_OVERFLOW CAPCAUSE=BOUNDS TVAL=0x2FFC FAULTCAPIDX=RSC` |
| Debug unwind | halted debug can peek, replace, and drop whole return slots |

## Findings

The protected return stack is recoverable if `CALL` and `RET` are treated as retire-time transactions.

The highest-risk partial states are:

- return slot payload written before tag,
- return slot tag written before payload,
- `RSC.cursor` changed before the slot is valid,
- `PCC` redirected before `RSC.cursor` changes,
- debug halt entered after a protected slot write but before the matching cursor or `PCC` update.

All of those states disappear if implementations hold protected return-stack updates in a transaction until retire and arbitrate debug entry at the same precise boundary.

Underflow and overflow do not require a new scalar depth CSR for v0.1. A correctly initialized in-bounds empty anchor, normal `RSC` bounds checks, slot tags, and the E07-S02 return-stack causes are enough for deterministic traps. Kernel or runtime code still owns the per-thread convention for where the empty anchor is placed.

Debug unwind should not reuse ordinary loads or stores. It needs a protected slot path so that a debugger can inspect or repair return frames without teaching the general memory ISA how to address protected return-stack storage.

## Required Hardware Assists

E06-S04 should require these assists:

| Assist | Reason |
| --- | --- |
| Return-stack transaction latch | Holds slot payload, tag, next `RSC.cursor`, and next `PCC` until retire. |
| Retire-time commit gate | Commits all `CALL` or `RET` effects together or discards them together. |
| Protected return-stack access classifier | Blocks ordinary loads/stores to protected return-stack storage and routes `CALL`, `RET`, and debug unwind operations through the protected path. |
| Whole-slot tag/data write path | Prevents payload/tag tearing for return capabilities. |
| Debug halt arbiter | Allows debug entry only before a protected transaction starts or after it commits or rolls back. |
| Return-stack fault packet | Carries `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX=RSC` for selected return-stack faults. |

These are small assists. They do not require a reorder buffer, speculative architectural snapshots, or a hardware return-stack depth counter.

## Recommendation

Proceed with the protected return stack as specified by E05-S04 and E06-S03.

E06-S04 should make the transaction rule normative:

- `CALL` commits the return slot payload, return slot tag, `RSC.cursor`, and `PCC` together.
- `RET` commits `RSC.cursor` and `PCC` together after validating the return slot.
- Trap, interrupt, debug halt, and single-step paths can observe only pre-instruction or post-instruction state.
- Debug unwind operations require a precise halted boundary and a protected whole-slot access path.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CALL` and `RET` update ordering is modeled. | Met by retire-time transaction model. |
| Trap entry during call/return sequences is analyzed. | Met by trap/debug timing table. |
| Debug unwind access is specified. | Met by peek, drop, and replace operation rules. |
| Return-stack underflow and overflow behavior is tested. | Met by `tools/return_stack_trap_model.py` scenarios. |
| Recommendation is made on required hardware assists. | Met by hardware assist table and E06-S04 recommendation. |

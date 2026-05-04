# E13-S04: Branch Prediction MVP

Story: E13-S04

Status: Complete

Normative source: `design.md`, section 16.4

Prerequisites:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E13-S01-pipeline-stages.md`

Related sources:

- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E08-S04-fence-instructions.md`
- `spec/E09-S02-satp-layout.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E12-S05-extended-performance-counters.md`
- `spec/E13-S03-hazard-handling.md`

## Decision

CPU v0.1 permits a conservative per-core branch predictor with exactly these mandatory MVP structures:

- A per-core 2-bit branch history table (`BHT`) for direct conditional branches only.
- A small per-core return-address stack (`RAS`) for `CALL` and `RET` prediction.

CPU v0.1 does not include a generic indirect branch target buffer (`BTB`). No predictor structure may provide arbitrary targets for `JMP`, `IRET`, or other indirect control transfers. `RET` prediction is allowed only through the constrained `RAS` defined here.

Prediction is a hint to the front end. It must not create architectural authority, bypass capability or page checks, change the precise exception model, or allow wrong-path work to update architectural state.

## Predictor State

Predictor state is per-core microarchitectural state:

- It is not directly readable or writable by ordinary software.
- It is not part of a software context frame.
- It is cleared or made unreachable for ordinary prediction at cold reset.
- It must not be preserved across reset as architecturally meaningful state.

Predictor state may affect timing and performance counters, but it must not affect the committed architectural result of any instruction stream.

## Direct Conditional Branch BHT

The BHT predicts only `Bcc target` direct conditional branches from E04-S04.

The BHT must not be consulted for:

- `BRA`.
- `CALL`.
- `RET`.
- `JMP`.
- `BRK`.
- `SYS` or `SCALL`.
- `IRET`.
- `WFI` or `PAUSE`.
- Any malformed or illegal encoding.

A conforming v0.1 implementation has a per-core BHT with an implementation-defined power-of-two number of entries. The minimum conforming size is 16 entries.

Each BHT entry is a 2-bit saturating counter:

| State | Name | Prediction | Taken update | Not-taken update |
| ---: | --- | --- | --- | --- |
| `0b00` | Strong not-taken | Not taken | `0b01` | `0b00` |
| `0b01` | Weak not-taken | Not taken | `0b10` | `0b00` |
| `0b10` | Weak taken | Taken | `0b11` | `0b01` |
| `0b11` | Strong taken | Taken | `0b11` | `0b10` |

Reset and predictor flush initialize BHT entries to weak not-taken unless the implementation partitions state and makes older entries unreachable by context-key mismatch.

The BHT index must include bits derived from the branch instruction's virtual cell address and the hidden slot bit. Implementations may include additional hashed bits, privilege bits, ASID bits, or other context tags.

For a predicted taken `Bcc`, the predicted target is the decoded direct target cell with slot 0. The BHT supplies direction only; it does not supply a target address.

For a predicted not-taken `Bcc`, the predicted next location is the E01-S05 sequential fall-through cell and slot.

## BHT Update

The BHT update for a `Bcc` is based on the resolved architectural condition:

- Taken increments the selected 2-bit counter.
- Not taken decrements the selected 2-bit counter.

The update must be equivalent to updating only for a `Bcc` that reaches normal architectural retirement.

An implementation may update earlier in the pipeline only if it can roll back or invalidate that update when the branch is killed, faults, is flushed by an older redirect, or otherwise fails to retire normally.

A taken `Bcc` whose direct target check fails does not update the BHT, because the branch does not retire normally.

Wrong-path conditional branches must not leave persistent BHT updates.

## Return-address Stack

The RAS is a per-core predictor stack for direct `CALL` and protected `RET`.

A conforming v0.1 implementation provides at least 4 RAS entries. Deeper RAS implementations are allowed.

Each RAS entry contains only a predicted return location:

- Virtual cell address.
- Hidden slot bit.
- Optional context tag used by the implementation.

RAS entries do not contain capability tags, bounds, permissions, sealed object types, or memory authority. A RAS prediction is not a return capability and cannot authorize instruction fetch or `RET` completion.

For a normally retiring direct `CALL`, the RAS push value is the E04-S04 slot-0 call continuation:

| Call instruction location | RAS push location |
| --- | --- |
| 12-bit `CALL` at slot 0 | Next cell, slot 0. |
| 12-bit `CALL` at slot 1 | Next cell, slot 0. |
| 24-bit `CALL` at slot 0 | Next cell, slot 0. |
| 48-bit `CALL` at fetch-group slot 0 | Next fetch group, slot 0. |

For a faulting `CALL`, no RAS push may persist.

For a `RET`, the front end may predict the target from the top RAS entry. If no valid RAS entry is available for the current context, the front end must not use an arbitrary indirect target. It must stall target fetch until the `RET` target is resolved, or use another behavior that does not fetch a guessed indirect target.

On a normally retiring `RET`, the RAS consumes the top entry for the current context if one exists, whether or not the front end used it for prediction. If the prediction was wrong, recovery must leave RAS state equivalent to correct sequential execution of normally retired `CALL` and `RET` instructions.

RAS overflow handling is implementation-defined, but it must be deterministic and documented by the implementation. A simple conforming policy is to discard the oldest entry and keep the most recent return continuations.

RAS underflow disables return prediction until a later normally retiring `CALL` pushes a new entry.

Speculative RAS push and pop are allowed only with checkpoint or rollback so killed wrong-path work cannot persistently corrupt the RAS.

## No Generic Indirect BTB

CPU v0.1 forbids a generic indirect BTB.

The front end must not use a table keyed by current `PCC` to supply arbitrary predicted targets for:

- `JMP Cs`.
- `IRET`.
- Future indirect call forms unless a later story explicitly permits them.
- Malformed or undecoded instruction bytes.

`JMP Cs` and `IRET` targets are resolved by their architectural operands and checks. Until resolved, the front end must not fetch from a guessed target.

Direct branch and direct call targets may be computed from decoded instruction immediates. An implementation may cache direct predecode metadata only if it obeys E08-S04 `FENCE.I` and `SFENCE.VM` rules for stale instruction bytes, stale translation-dependent metadata, and permission checks.

The RAS is the only v0.1 predictor that may provide a target for an indirect-looking control transfer, and only for `RET`.

## Capability and Fetch Authority

Prediction must not bypass execute authority.

A predicted direct branch target is still fetched under the ordinary `PCC` execute authority and instruction-fetch permission checks. If the predicted path later proves wrong, any wrong-path fetch, decode, or execution work is killed before it can commit architectural state.

A RAS-predicted `RET` target is only a fetch hint. The eventual `RET` instruction must still:

- Pop through the protected return stack.
- Validate the loaded sealed return capability.
- Check tag, seal/type, locality, permissions, bounds, and slot rules.
- Commit the `RSC` update and `PCC` installation atomically.

If the real `RET` target differs from the RAS prediction, or if `RET` faults, the prediction is discarded and the E07-S03 precise exception and E13-S03 flush rules apply.

If the current speculative `PCC` cannot authorize fetch of a predicted target, the implementation must not use the predictor to fetch through that target. It may stall until the control transfer resolves.

## Context Isolation

Predictor state must be flushed or partitioned on privilege change and ASID switch.

The predictor context key is at least:

```text
context = { SR.PRIV, SATP.MODE, active ASID }
```

When an implementation chooses partitioning, BHT and RAS entries used for prediction must carry or derive a context key so that an entry created in one context is not used to predict in a different context.

When an implementation chooses flushing, it must flush or invalidate BHT and RAS prediction state before younger fetch in the new context can consult the predictor after:

- Trap entry changing `SR.PRIV` to kernel.
- Interrupt entry changing `SR.PRIV` to kernel.
- Debug-monitor entry changing `SR.PRIV` to kernel.
- Successful `IRET` changing `SR.PRIV`.
- Any committed write to `SATP` that changes `SATP.MODE` or `SATP.ASID`.
- Any committed write to `ASID`.

If a committed `SATP` write changes `ROOT_PPN` while leaving `MODE` and `ASID` unchanged, the implementation must either include enough address-space identity in its predictor partitioning to prevent stale cross-address-space use, or conservatively flush predictor state before younger fetch.

Software that reuses an ASID for a different address space must follow the E09-S03 and E08-S04 translation-maintenance rules. Predictor implementations that partition only by ASID must ensure the ASID reuse sequence cannot leave stale predictor entries usable for the reused address space; flushing on the relevant `SATP`, `ASID`, or `SFENCE.VM` sequence is a conforming solution.

`DEBUG_HALTED` does not execute ordinary fetch and does not consult or update predictor state. Debug-monitor software is kernel execution in its own predictor context according to the rules above.

## Mispredict Detection

Each predicted control transfer carries enough prediction metadata forward to compare the predicted next location against the resolved architectural next location.

For `Bcc`, the resolved result is:

- Direct target cell, slot 0, when the condition is true and the target checks pass.
- Sequential fall-through cell and slot when the condition is false.

For `RET`, the resolved result is the validated return capability target with slot 0.

A mispredict occurs when a prediction was actually used and the resolved next location differs in cell address or hidden slot, or when the predicted control transfer resolves as a synchronous exception instead of a normal control transfer.

If no prediction was made because the front end stalled until resolution, no mispredict is counted for that control transfer.

## Mispredict Recovery

On mispredict, hardware must:

1. Select the correct redirect packet for the resolved control transfer or exception.
2. Flush or mark killed all younger wrong-path work in fetch, decode, issue, execute, memory, and writeback stages.
3. Prevent wrong-path work from updating integer registers, capability registers, special capability registers, scalar CSRs, memory payload, memory tags, protected return-stack state, counters, debug state, or persistent predictor state.
4. Restore or repair speculative RAS and BHT updates so predictor state is equivalent to correct sequential execution.
5. Restart fetch at the correct `PCC` and hidden slot, or enter the selected trap/debug path.

The mispredicted instruction itself may retire normally if all of its architectural checks pass. Younger wrong-path instructions must not retire.

The E12-S05 `BRANCH_MISPREDICT` event increments only for a used prediction that is corrected by a control-transfer redirect associated with a normally retiring control instruction. A control instruction that faults is recovered through the exception path and does not count as a branch mispredict event unless a later counter story deliberately adds an exception-correction event.

## Reset, Fences, and Maintenance

Cold reset makes BHT and RAS entries unavailable for ordinary prediction. The recommended reset state is:

- BHT entries weak not-taken.
- RAS empty.

`FENCE.I` does not need to clear BHT direction counters or RAS entries that contain only virtual control-flow hints. If an implementation's predictor or predecode structures contain instruction bytes, decoded instruction metadata, target metadata, or translation-dependent fetch authority, E08-S04 requires `FENCE.I` to invalidate or retag that state so stale instruction fetch cannot bypass fresh instruction bytes and checks.

`SFENCE.VM` does not need to clear predictor entries that are correctly partitioned by the active translation context and do not carry stale translation authority. If predictor, target-cache, or predecode state contains translation-dependent authority or is not partitioned strongly enough for the `SFENCE.VM` operation, it must be invalidated or retagged before younger fetch can use it.

## Out of Scope

E13-S04 does not define:

- A generic indirect BTB.
- Indirect-call target prediction.
- Global history, tournament, perceptron, or neural predictors.
- Cross-core predictor sharing.
- User-visible predictor control CSRs.
- Architectural predictor flush instructions beyond the fence and context rules above.
- Complete Spectre-class mitigation policy beyond the explicit no-BTB, context isolation, authority-check, and wrong-path-kill requirements in this story.

## Verification Notes

E13-S04 tests should cover:

- BHT entries use 2-bit saturating update behavior for direct conditional branches.
- Direct conditional branches at different hidden slots can be distinguished by the predictor index or tag.
- `BRA`, `CALL`, `RET`, `JMP`, `IRET`, `BRK`, `SYS`, and `SCALL` do not use the BHT as a conditional direction predictor.
- A predicted-taken `Bcc` fetches the decoded direct target slot 0.
- A predicted-not-taken `Bcc` fetches the sequential fall-through slot from E01-S05.
- A taken branch predicted not-taken flushes fall-through wrong-path work and restarts at the target.
- A not-taken branch predicted taken flushes target wrong-path work and restarts at fall-through.
- A faulting taken branch does not persist a BHT update.
- A normally retiring `CALL` pushes the slot-0 continuation to the RAS.
- A faulting `CALL` does not persist a RAS push.
- A `RET` may predict from RAS when a valid same-context entry exists.
- A `RET` with an empty RAS does not fetch from a generic guessed target.
- A RAS misprediction flushes wrong-path work and restarts at the validated `RET` target.
- `JMP Cs` and `IRET` do not use a generic indirect BTB.
- Predictor state is flushed or partitioned across privilege changes.
- Predictor state is flushed or partitioned across `SATP` or `ASID` switches.
- Wrong-path instructions do not update counters or persistent predictor state.
- `BRANCH_MISPREDICT` increments for corrected used predictions when the event is supported.

## Story Acceptance Review

| Acceptance criterion | Evidence |
| --- | --- |
| Per-core 2-bit BHT is used for direct conditional branches only. | Met: BHT state, indexing, lookup restrictions, and saturating updates are defined for `Bcc` only. |
| No generic indirect BTB exists in v0.1. | Met: arbitrary target prediction for `JMP`, `IRET`, and future indirect forms is forbidden. |
| Small return-address stack supports `CALL/RET`. | Met: a per-core RAS with at least 4 entries predicts `RET` from normally retiring `CALL` continuations. |
| Predictor state is flushed or partitioned on privilege change and ASID switch. | Met: context key and required flush or partition events are specified. |
| Mispredict recovery behavior is specified. | Met: detection, redirect, flush, wrong-path suppression, predictor repair, and counter interaction are specified. |

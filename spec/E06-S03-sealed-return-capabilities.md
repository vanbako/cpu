# E06-S03: Sealed Return Capabilities

Story: E06-S03

Status: Complete

Normative source: `design.md`, section 9

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E03-S03-capability-derivation.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S01-instruction-fetch-groups.md`

## Decision

CPU v0.1 uses sealed return capabilities for backward-edge control flow.

`CALL` derives a return capability from the current `PCC`, seals it with an architecture-reserved return object type, stores it through the protected return-stack path governed by `RSC`, and transfers to the call target.

`RET` accepts only a valid sealed return capability loaded through the protected return-stack path governed by `RSC`. It validates and internally unseals that capability, then installs the resulting execution capability into `PCC`.

## Return Object Type

The architecture reserves one object type for return capabilities:

| Name | Encoding | Meaning |
| --- | ---: | --- |
| `OTYPE_RETURN` | `0xFF` | Sealed return capability |

`OTYPE_RETURN` is not available to ordinary software sealing operations.

Rules:

- `CALL` is the only normal v0.1 operation that creates a capability sealed with `OTYPE_RETURN`.
- `RET` is the only normal v0.1 operation that consumes and internally unseals `OTYPE_RETURN`.
- `CSEAL` with `OTYPE_RETURN` raises capability seal/type fault.
- `CUNSEAL` of `OTYPE_RETURN` raises capability seal/type fault.
- Future privileged debug or unwind stories may define controlled exceptions, but ordinary software cannot mint or unseal return capabilities.

`CALL` and `RET` use internal architectural seal authority. `CALL` does not require `SEAL` permission in `PCC` or any software-visible capability. `RET` does not require `UNSEAL` permission in any software-visible capability.

E06-S02 must not reuse `OTYPE_RETURN` for sealed entry capabilities.

## Return Capability Payload

The return capability is derived from the current `PCC`.

The derived payload:

- Preserves `PCC` bounds.
- Preserves `PCC` permissions.
- Sets the cursor to the architectural call continuation cell address.
- Sets the object type to `OTYPE_RETURN`.
- Sets `G=0`, making the sealed return capability local.
- Preserves the validity tag.

The derived return capability does not carry a directly addressable slot bit. Return capabilities always return to slot 0.

Because the source is `PCC`, the return capability cannot authorize execution outside the caller's current executable bounds, and it cannot gain permissions absent from `PCC`.

## Call Continuation

`CALL` computes the call continuation as a slot-0 location.

| Call instruction location | Return continuation |
| --- | --- |
| 12-bit `CALL` at slot 0 | Next cell, slot 0 |
| 12-bit `CALL` at slot 1 | Next cell, slot 0 |
| 24-bit `CALL` at slot 0 | Next cell, slot 0 |
| 48-bit `CALL` at fetch-group slot 0 | Next fetch group, slot 0 |

This follows E01-S05: slot 1 is not a general control-flow target. A call placed in slot 0 does not return to slot 1.

The computed continuation cursor must be in bounds for the current `PCC`. If it is not in bounds, `CALL` raises capability bounds fault and leaves architectural state unchanged.

## `CALL` Semantics

For `CALL target`, the architectural effect is:

```text
continuation = slot-0 call continuation
return_cap = derive PCC with cursor = continuation
return_cap.otype = OTYPE_RETURN
return_cap.G = 0
protected_push(RSC, return_cap)
PCC.cursor = target
PCC.slot = 0
```

Architectural checks:

- Current `PCC` must be valid, unsealed, in bounds, and execute-authorized.
- The continuation must be in current `PCC` bounds.
- `RSC` must authorize the protected return-stack push.
- The target transfer must satisfy the control-transfer and `PCC` authority rules defined by E04-S04 and E06-S01.

Commit rule:

- `CALL` commits the return-stack update and `PCC` update together.
- If any `CALL` check fails, no return capability is pushed and `PCC` is unchanged.

The protected return-stack storage format, overflow handling, and exact `RSC` cursor update are defined by E05-S04. Trap interaction with a partially executed call is modeled by E06-S04 and E14-S05.

## `RET` Semantics

For `RET`, the architectural effect is:

```text
return_cap = protected_pop(RSC)
validate return_cap has valid tag
validate return_cap is sealed with OTYPE_RETURN
validate return_cap cursor is in bounds
validate return_cap has EX permission
PCC = unseal_as_execution_capability(return_cap)
PCC.otype = 0
PCC.slot = 0
```

Architectural checks:

- `RSC` must authorize the protected return-stack pop.
- The popped value must have a valid capability tag.
- The popped value must be sealed.
- The popped value must have `otype = OTYPE_RETURN`.
- The popped return cursor must be in bounds.
- The popped return capability must have `EX`.
- The return target must be slot 0.

Commit rule:

- `RET` commits the return-stack pop and `PCC` installation together.
- If any `RET` check fails, `RSC`, `PCC`, and destination architectural state are unchanged.

The unsealed result installed into `PCC` is an execution capability. It is not exposed as an unsealed general capability by `RET`.

## Fault Rules

| Invalid case | Fault |
| --- | --- |
| Return-stack pop finds invalid tag | Capability tag fault |
| Popped capability is unsealed | Capability seal/type fault |
| Popped capability is sealed with non-return object type | Capability seal/type fault |
| Popped return cursor is outside bounds | Capability bounds fault |
| Popped return capability lacks `EX` | Capability permission fault |
| Protected return-stack access is out of bounds | Capability bounds fault |
| Protected return-stack access lacks authority | Capability permission fault |
| Return target implies slot 1 | `ALIGN_FAULT` |

On capability faults, `FAULTCAPIDX` reports `RSC` for protected return-stack access faults and the return capability source where the implementation can distinguish it. `TVAL` reports the return-stack slot address for stack access faults or the attempted return cursor for return-target faults.

## Tamper Resistance

Ordinary integer stores cannot forge a valid return capability. If an ordinary store overwrites a protected return capability slot, the capability tag is cleared by the memory tag rules and `RET` raises capability tag fault.

Replacing the slot with another valid capability does not bypass validation:

- Unsealed capabilities are rejected.
- Sealed capabilities with the wrong object type are rejected.
- Capabilities without `EX` are rejected.
- Capabilities whose cursor is outside their bounds are rejected.

Sealed return capabilities cannot be modified with ordinary capability derivation instructions. `CSETADDR`, `CINCADDR`, `CSETBOUNDS`, and `CANDPERM` cannot operate on a sealed return capability.

This story validates the popped return value. The protected return-stack access model in E05-S04 and E06-S04 defines how ordinary software is prevented from writing arbitrary valid capabilities into return-stack storage.

## Out of Scope for This Story

- Sealed entry capabilities and `CALLC`: E06-S02.
- Detailed protected return-stack memory layout and `RSC` cursor rules: E05-S04.
- Trap and debug interaction with return-stack updates: E06-S04 and E14-S05.
- Full control-transfer instruction semantics: E04-S04.
- Precise exception priority across all control-flow faults: E07-S03.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CALL` derives a return capability from current `PCC`.
- The derived return capability cursor is the slot-0 call continuation.
- A 12-bit `CALL` in slot 0 returns to the next cell, slot 0.
- The derived return capability is sealed with `OTYPE_RETURN`.
- The derived return capability is local (`G=0`).
- `CALL` pushes the sealed return capability through the protected `RSC` path.
- `CALL` faults without changing `PCC` or `RSC` if the continuation is out of bounds.
- `RET` rejects an invalid-tag return-stack entry.
- `RET` rejects an unsealed capability.
- `RET` rejects a sealed non-return capability.
- `RET` rejects a return capability without `EX`.
- `RET` installs an unsealed `PCC` with slot 0 for a valid sealed return capability.
- `CSEAL` cannot create `OTYPE_RETURN`.
- `CUNSEAL` cannot unseal `OTYPE_RETURN`.
- Integer overwrite of a return slot clears the tag and causes `RET` tag fault.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CALL` derives a return capability from current `PCC`. | Met. |
| The return capability is sealed as a return capability. | Met: sealed with `OTYPE_RETURN`. |
| `RET` accepts only a valid sealed return capability from `RSC`. | Met. |
| Invalid or tampered return capabilities raise seal/type or tag fault. | Met. |

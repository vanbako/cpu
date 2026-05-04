# E06-S02: Sealed Entry Capabilities

Story: E06-S02

Status: Complete

Normative source: `design.md`, section 9

Prerequisites:

- `spec/E03-S03-capability-derivation.md`
- `spec/E04-S04-control-transfer-instructions.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S02-capability-permissions.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`

## Decision

CPU v0.1 uses sealed entry capabilities for protected forward-edge control flow.

A sealed entry capability carries executable authority in a sealed form. Ordinary code may hold, pass, load, store, and copy the sealed value, but it cannot fetch through it, modify its cursor or bounds, or expose the unsealed executable capability.

`CALLC Cs` is the only normal v0.1 instruction that consumes a sealed entry capability. It validates `Cs`, internally unseals it as an executable target, pushes a sealed return capability through the protected return stack, and enters the target at slot 0. The unsealed target is never written to a general capability register.

## Entry Object Type

The architecture reserves one object type for sealed entry capabilities:

| Name | Encoding | Meaning |
| --- | ---: | --- |
| `OTYPE_ENTRY` | `0xFE` | Sealed callable entry capability |

`OTYPE_ENTRY` is distinct from `OTYPE_RETURN = 0xFF` from E06-S03.

Rules:

- `CSEAL` may create `OTYPE_ENTRY` when its seal-authority operand authorizes object type `0xFE`.
- `CUNSEAL` cannot unseal `OTYPE_ENTRY`; only `CALLC` consumes it in normal v0.1 execution.
- `CALLC` does not require `UNSEAL` permission in any software-visible capability.
- `CALLC` does not require `SEAL` permission in the entry capability or in `PCC`.
- `OTYPE_ENTRY` must not be reused for return capabilities, ordinary software object sealing protocols, or future sealed object classes.

This makes entry capabilities usable as callable handles without distributing raw executable authority.

## Entry Capability Payload

An entry capability is a sealed capability with:

- A valid capability tag.
- `otype = OTYPE_ENTRY`.
- A cursor naming the callable entry cell address.
- Bounds that contain the cursor.
- `EX` permission.
- Any other permissions intentionally carried by the entry authority.

The sealed payload preserves the source capability's bounds, permissions, cursor, flags, and tag, except for setting `otype = OTYPE_ENTRY` during `CSEAL`.

`CALLC` does not add permissions. The installed `PCC` carries only permissions already present in the sealed entry capability. Software should normally clear unnecessary permissions before sealing an entry capability.

Entry capabilities do not carry a directly addressable slot bit. `CALLC` always enters slot 0.

## Creating Entry Capabilities

Software creates an entry capability by first deriving an unsealed executable capability for the intended entry point, then sealing it with `OTYPE_ENTRY`.

Example architectural sequence:

```text
CSETADDR Ctmp, Ccode, entry_cell
CANDPERM Ctmp, Ctmp, entry_permissions
CSEAL Centry, Ctmp, Cseal_entry
```

where:

```text
Cseal_entry.cursor[7:0] = OTYPE_ENTRY
Cseal_entry has SEAL
```

`CSEAL` validation still follows E04-S05:

- The source must be valid and unsealed.
- The sealing authority must be valid and unsealed.
- The sealing authority must have `SEAL`.
- The selected object type must be nonzero.
- The selected object type must be available to `CSEAL`.

`OTYPE_ENTRY` is available to `CSEAL`. `OTYPE_RETURN` is not.

`CSEAL` does not require the source to have `EX`. A sealed non-executable entry-shaped object can be created, but `CALLC` rejects it with a capability permission fault.

## `CUNSEAL` Restriction

Ordinary `CUNSEAL` cannot unseal `OTYPE_ENTRY`, even when the authorizer names object type `0xFE` and has `UNSEAL`.

Attempting to `CUNSEAL` an `OTYPE_ENTRY` capability raises capability seal/type fault and leaves the destination unchanged.

This restriction is what prevents a holder of an entry capability from converting it into raw executable authority. Entering the target is possible only through `CALLC`.

## `CALLC`

`CALLC Cs` is an indirect call through a sealed entry capability.

It computes the same slot-0 call continuation as direct `CALL` from E06-S03 and E04-S04:

| `CALLC` instruction location | Return continuation |
| --- | --- |
| 12-bit `CALLC` at slot 0 | Next cell, slot 0 |
| 12-bit `CALLC` at slot 1 | Next cell, slot 0 |
| 24-bit `CALLC` at slot 0 | Next cell, slot 0 |
| 48-bit `CALLC` at fetch-group slot 0 | Next fetch group, slot 0 |

It prepares:

```text
continuation = slot-0 call continuation
return_cap = derive current PCC with cursor = continuation
return_cap.otype = OTYPE_RETURN
return_cap.G = 0

entry_pcc.payload = Cs.payload with otype = 0
entry_pcc.tag     = Cs.tag
entry_pcc.slot    = 0
```

It then uses the protected push transaction from E05-S04 and E06-S04:

```text
target_slot = RSC.cursor - 4
next_rsc_cursor = target_slot
```

## `CALLC` Checks

`CALLC` performs these instruction-specific checks after fetch/decode and ordinary instruction placement checks:

1. Current `PCC` must be valid, unsealed, in bounds, and execute-authorized.
2. The slot-0 continuation must be representable and inside current `PCC.bounds`.
3. `Cs.tag` must be valid.
4. `Cs` must be sealed.
5. `Cs.otype` must equal `OTYPE_ENTRY`.
6. `Cs` must have `EX`.
7. `Cs.cursor` must be inside `Cs.bounds`.
8. `RSC` must authorize the protected return-stack push.
9. The derived return capability must be a valid sealed local `OTYPE_RETURN` capability.

At normal retire, successful `CALLC` commits as one architectural action:

- Store the 96-bit return-capability payload to the protected return-stack slot.
- Set the memory tag for that slot.
- Set `RSC.cursor = next_rsc_cursor`.
- Install `entry_pcc` into `PCC`.
- Set `PCC.slot = 0`.
- Set `SR.SLOT = 0`.

`CALLC` leaves `Cs` unchanged. The unsealed `entry_pcc` is visible only as the installed `PCC` after successful commit.

If any check fails, no return capability is stored, no return-stack tag is written, `RSC` is unchanged, `PCC` is unchanged, and `Cs` is unchanged.

## Fault Reporting

`CALLC` uses ordinary precise exception reporting.

| Failure | Cause | Capability reporting |
| --- | --- | --- |
| Current `PCC` invalid, sealed, missing `EX`, or out of bounds | Capability fault | `FAULTCAPIDX=PCC`; `CAPCAUSE` selects the failing reason. |
| Continuation outside current `PCC.bounds` | Capability bounds fault | `FAULTCAPIDX=PCC`, `CAPCAUSE=BOUNDS`, `TVAL=continuation`. |
| `Cs.tag` invalid | Capability tag fault | `FAULTCAPIDX=Cs`, `CAPCAUSE=TAG`, `TVAL=0`. |
| `Cs` unsealed | Capability seal/type fault | `FAULTCAPIDX=Cs`, `CAPCAUSE=SEAL_TYPE`, `TVAL=0`. |
| `Cs.otype != OTYPE_ENTRY` | Capability seal/type fault | `FAULTCAPIDX=Cs`, `CAPCAUSE=SEAL_TYPE`, `TVAL=0`. |
| `Cs` lacks `EX` | Capability permission fault | `FAULTCAPIDX=Cs`, `CAPCAUSE=PERMISSION`, `TVAL=0`. |
| `Cs.cursor` outside `Cs.bounds` | Capability bounds fault | `FAULTCAPIDX=Cs`, `CAPCAUSE=BOUNDS`, `TVAL=Cs.cursor`. |
| Protected return-stack push failure | Return-stack fault | E05-S04, E06-S04, and E07-S02 reporting. |

If several `CALLC` checks fail, the check order above selects the reported failure.

Wrong seal state or wrong object type is the invalid-entry-capability case required by this story's acceptance criteria and reports as capability seal/type fault.

## Atomicity and Visibility

`CALLC` is a multi-effect instruction with all-or-nothing commit.

No architectural observer may see:

- The entry capability unsealed in a general capability register.
- A return-stack payload without its matching tag.
- A return-stack tag without its matching payload.
- Updated `RSC.cursor` without the matching return-stack entry.
- Updated `PCC` without the matching protected return-stack push.
- A trap, interrupt, debug halt, or single-step boundary inside the `CALLC` protected transaction.

Maskable interrupt delivery during `CALLC` follows E07-S03 and E07-S05: it may occur before the instruction starts or after the whole instruction commits, but not between the internal unseal, protected push, and `PCC` installation.

## Tamper Resistance

Sealed entry capabilities are still capabilities and rely on the normal tag and sealing rules.

Rules:

- Integer stores cannot forge a valid entry capability tag.
- Ordinary stores over an entry capability memory slot clear the tag according to E03-S04.
- Capability copies and capability stores preserve the sealed payload and tag when authorized.
- `CSETADDR`, `CINCADDR`, `CSETBOUNDS`, and `CANDPERM` cannot modify a sealed entry capability.
- `JMP Cs` rejects a sealed entry capability because `JMP` requires an unsealed executable capability.
- `CGETADDR` may expose the cursor as integer data, but that does not expose executable authority.

Replacing one valid entry capability with another valid entry capability can redirect a later `CALLC` only to authority already represented by the replacement capability. It does not forge authority.

## Entry and Return Interaction

`CALLC` creates a normal sealed return capability for the caller's continuation and pushes it through `RSC`.

The callee returns with ordinary `RET`.

The return capability is derived from the caller's current `PCC`, not from the entry capability. Therefore the callee receives return authority only to the caller continuation selected by the `CALLC` instruction, and that return authority remains protected by `OTYPE_RETURN` and the protected return stack.

## Out of Scope for This Story

- Exact `CALLC` opcode encoding and compact forms: E04-S06 and the final opcode story.
- Cross-compartment ABI details, argument registers, and data-capability handoff conventions: E05 stories.
- Paired code/data entry objects or capability tables.
- Dynamic loader policy for distributing sealing authority.
- Debug-mode raw inspection or controlled unsealing of entry capabilities: E12 stories.
- Branch prediction behavior for `CALLC`: E13-S04.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- `OTYPE_ENTRY = 0xFE`.
- `OTYPE_ENTRY` and `OTYPE_RETURN` are distinct.
- `CSEAL` can create `OTYPE_ENTRY` when authorized.
- `CSEAL` cannot create `OTYPE_RETURN`.
- `CUNSEAL` cannot unseal `OTYPE_ENTRY`.
- `CALLC` rejects invalid-tag `Cs`.
- `CALLC` rejects unsealed `Cs`.
- `CALLC` rejects sealed non-entry `Cs`.
- `CALLC` rejects an entry capability without `EX`.
- `CALLC` rejects an entry capability whose cursor is outside bounds.
- `CALLC` enters slot 0 for a valid entry capability.
- `CALLC` installs an unsealed `PCC` only as the committed target.
- `CALLC` leaves the source general capability register sealed and unchanged.
- `CALLC` pushes a sealed local `OTYPE_RETURN` capability through the protected `RSC` path.
- `CALLC` commits return-stack payload, return-stack tag, `RSC.cursor`, and `PCC` together.
- Faulting `CALLC` leaves return-stack memory, tags, `RSC`, `PCC`, and `Cs` unchanged.
- A maskable interrupt cannot observe a partially completed `CALLC`.
- `RET` from a `CALLC` target returns through the ordinary protected return-stack path.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Entry capability object type is reserved or defined. | Met: `OTYPE_ENTRY = 0xFE`. |
| `CALLC Cs` checks for a sealed entry capability. | Met: `CALLC` requires a valid sealed `Cs` with `otype = OTYPE_ENTRY`. |
| Unseal-and-enter behavior is atomic from the architectural point of view. | Met: the unsealed target is only visible as committed `PCC`, together with the protected return-stack push. |
| Invalid entry capabilities raise seal/type fault. | Met: unsealed or wrong-object-type `Cs` raises capability seal/type fault. |

# E05-S02: Capability Calling Convention

Story: E05-S02

Status: Complete

Normative source: `design.md`, section 8

Prerequisites:

- `spec/E01-S03-general-capability-registers.md`
- `spec/E03-S03-capability-derivation.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E03-S05-local-capabilities.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E05-S01-integer-calling-convention.md`
- `spec/E05-S03-data-stack-model.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S02-sealed-entry-capabilities.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spikes/E14-S02-24-bit-toolchain-abi.md`

## Decision

CPU v0.1 uses a register-first capability calling convention.

The capability ABI assigns:

| Role | Registers |
| --- | --- |
| Capability argument registers | `C0-C3` |
| Capability return register | `C0` |
| Caller-saved capability registers | `C0-C5` |
| Callee-saved capability registers | `C6-C7` |

All `C0-C7` registers remain ordinary general capability registers. The ABI roles are software contracts at public call boundaries.

## ABI Capability Value

An ABI capability value consists of:

- A 96-bit capability payload.
- Its out-of-band architectural validity tag.

Passing or returning a capability preserves both payload and tag unless the register or stack slot is explicitly caller-saved and clobbered by the callee.

Rules:

- A valid-tag capability argument transfers authority to the callee according to its payload.
- An invalid-tag capability argument transfers no authority, but its payload and clear tag are still part of the ABI value.
- Sealed capabilities, including sealed entry capabilities, may be passed as capability values.
- Local capabilities may be passed in registers.
- Local capabilities may be passed on the stack only through a destination stack capability that permits local stores.

Integer registers cannot carry capability tags. Splitting a capability payload into integer registers is not a capability argument and does not transfer authority.

## Capability Arguments

Capability arguments are assigned in source order after language-level classification.

The capability argument index in this story counts capability-class arguments only. Integer-class arguments use the independent integer stream from E05-S01.

The first four capability arguments use registers:

| Capability argument index | Location |
| ---: | --- |
| 0 | `C0` |
| 1 | `C1` |
| 2 | `C2` |
| 3 | `C3` |

Capability argument 4 and later are overflow stack arguments unless the language ABI passes the object indirectly through an earlier capability argument.

At the call boundary, the callee observes exactly the payload and tag placed in `C0-C3` by the caller, except for effects explicitly performed by the call instruction itself. `CALL` does not modify general capability argument registers. `CALLC` leaves its source general capability register unchanged according to E06-S02.

## Capability Stack Arguments

Overflow capability arguments are placed in the caller-allocated outgoing argument area on the data stack.

Each stack capability argument occupies one capability slot:

| Property | Value |
| --- | ---: |
| Slot size | 4 cells |
| Slot alignment | 4 cells |
| Store operation | `CSC` through `DSC` |
| Load operation | `CLC` through `DSC` |

The caller stores the capability payload and tag with `CSC`. The callee loads the payload and tag with `CLC` if it needs the argument.

Stack argument capability stores follow E03-S05 and E04-S05:

- Storing a valid global capability requires `DSC` to have `ST` and `SC`.
- Storing a valid local capability requires `DSC` to have `ST`, `SC`, and `SL`.
- Storing an invalid-tag capability writes the payload and clears the stack slot tag.
- Faulting stack argument stores leave the stack payload and tag unchanged.

A conforming public ABI stack intended to support capability spills or stack-passed capability arguments must provide `DSC` authority with `ST`, `SC`, and `SL` for the caller's outgoing area.

## Mixed Outgoing Argument Area

Integer and capability register assignment uses independent streams:

- Integer-class arguments use `D0-D5`, then integer stack slots from E05-S01.
- Capability-class arguments use `C0-C3`, then capability stack slots from this story.

When either class overflows its register stream, the caller lays out all overflow arguments in one outgoing stack argument area in original source order.

At the public call boundary:

```text
arg_base = entry DSC.cursor
offset = 0
```

For each source-order argument not assigned to a register:

```text
if argument is integer-class:
    offset = align_up(offset, 2)
    place 2-cell integer slot at [arg_base + offset, arg_base + offset + 2)
    offset = offset + 2

if argument is capability-class:
    offset = align_up(offset, 4)
    place 4-cell capability slot at [arg_base + offset, arg_base + offset + 4)
    offset = offset + 4
```

After the last overflow argument:

```text
outgoing_area_size = align_up(offset, 4)
```

Rules:

- `DSC.cursor` is 4-cell aligned at the call boundary.
- Integer overflow slots remain 2-cell aligned.
- Capability overflow slots remain 4-cell aligned.
- Padding cells introduced by alignment are not arguments and have unspecified contents.
- The caller owns allocation and release of the outgoing area.
- The callee may address overflow arguments relative to its entry `DSC.cursor`.
- If the callee moves `DSC.cursor`, it must preserve the entry argument base by its own frame convention before relying on overflow arguments.

For integer-only calls, this layout reduces to the E05-S01 integer overflow layout.

## Capability Return Values

Capability return values use:

| Return value | Location |
| --- | --- |
| Primary capability return | `C0` |

Rules:

- A function returning one capability writes its payload and tag in `C0`.
- Returning an invalid-tag capability is valid and means no authority is returned.
- A function returning no capability leaves `C0` unspecified unless a language ABI defines a narrower rule.
- Multiple capability returns, large aggregates, and mixed integer/capability aggregate returns use caller-provided result storage or a later language ABI convention.

If a function returns both integer and capability values under a language-specific multi-return convention, the first integer returns still use `D0-D1` and the first capability return uses `C0`, unless that language ABI defines an indirect return convention.

## Caller-saved Capability Registers

`C0-C5` are caller-saved.

Rules:

- A callee may freely clobber `C0-C5`, including payload and tag.
- `C0-C3` are both capability argument registers and caller-saved registers.
- `C0` is both the capability return register and a caller-saved register.
- `C4-C5` are volatile temporary capability registers.
- A caller that needs a `C0-C5` capability value after a call must save it before the call and restore it after the call.

Saving a valid local capability to the stack requires `DSC` to have `ST`, `SC`, and `SL`.

## Callee-saved Capability Registers

`C6-C7` are callee-saved.

Rules:

- A callee that writes `C6` or `C7` must restore both the 96-bit payload and the validity tag to their exact entry values before returning normally.
- The restore obligation applies to every normal return path from the function.
- Preserving an invalid-tag entry value means restoring the invalid tag and the 96-bit payload exactly.
- A callee may use `C6-C7` for long-lived authority only if it preserves them.

If a call does not return normally because it traps, unwinds through a runtime mechanism, or terminates the thread, the preservation contract is handled by the trap, unwind, or runtime ABI rather than by this normal function-call rule.

## Tag Preservation Across Calls

The ABI treats capability tags as part of register and stack state.

Rules:

- Capability argument registers `C0-C3` arrive at the callee with the caller-provided payload and tag.
- Capability stack arguments arrive in memory with the caller-stored payload and tag.
- Capability return register `C0` carries the callee-provided payload and tag.
- Callee-saved registers `C6-C7` must preserve payload and tag across normal calls.
- Caller-saved registers `C0-C5` have no preservation guarantee across calls.
- `CMOVE`, `CLC`, and `CSC` are the normal operations for preserving capability tags in registers and stack slots.
- `LD48` cannot load a capability tag.
- `ST48` overlapping a capability slot clears that slot's tag and is not a valid way to spill a capability value.

This rule applies equally to valid, invalid, sealed, unsealed, global, and local capabilities.

## Variadic Capability Calls

Capability arguments to variadic functions use the same initial assignment as non-variadic calls:

- The first four capability arguments use `C0-C3`.
- Later capability arguments use overflow stack capability slots.

A variadic callee that evaluates capability variable arguments is responsible for creating its own capability register save area in its frame if it needs stable memory addresses for register-passed capability arguments.

The abstract capability `va_list` state for this story contains:

| Field | Meaning |
| --- | --- |
| `next_cap_reg` | Next capability argument register index, from 0 through 4. |
| `next_stack_offset` | Next stack argument search offset relative to the entry stack argument base. |

For a capability vararg:

- If `next_cap_reg < 4`, the next capability vararg is read from `C[next_cap_reg]` or from the callee's saved copy of that register.
- If `next_cap_reg == 4`, the next capability vararg is read from the next 4-cell aligned capability slot in the mixed outgoing argument area.

Mixed integer/capability variadic traversal uses the mixed outgoing argument layout above plus the independent register save areas for `D0-D5` and `C0-C3`.

Concrete in-memory `va_list` layout, language default promotions, aggregate variadic arguments, and ABI helper routines are deferred to language ABI documents.

## Calls, Returns, and Stack State

At a public function call boundary:

- `D0-D5` contain the first integer-class arguments from E05-S01.
- `C0-C3` contain the first capability-class arguments.
- Overflow integer and capability arguments are in the mixed outgoing argument area starting at entry `DSC.cursor`.
- `DSC.cursor` is 4-cell aligned.
- `RSC` contains the protected return-stack state used by `CALL`, `CALLC`, and `RET`.
- `C6-C7` carry capability values the callee must preserve if it writes them.

At normal return:

- `C0` contains the capability return value, if any.
- `C6-C7` match their entry payload and tag values.
- `DSC.cursor` is restored to the callee's entry value.
- The caller's outgoing argument area remains caller-owned and may be released by the caller.

A tail call is permitted when the current function has restored `C6-C7`, restored any callee-saved integer state required by E05-S01, and adjusted `DSC.cursor` so the tail-called function observes a valid public call boundary.

## Syscall Capability Convention

The baseline syscall convention uses capability argument registers when a syscall transfers authority:

| Role | Location |
| --- | --- |
| Capability syscall arguments | `C0-C3`, then mixed overflow stack convention if a platform allows more |
| Capability syscall return | `C0` |

User code must treat `C0-C5` as volatile across a syscall unless its operating-system ABI states otherwise. Kernel software must not treat integer payload copies as capability authority; authority transfer through syscalls requires capability registers or capability stack slots with valid tags.

## Out of Scope for This Story

- Exact language ABI layout for `va_list`, aggregate arguments, and aggregate returns.
- Capability table, dynamic loader, and relocation models for constructing argument capabilities.
- Exception unwinding and signal-frame capability preservation.
- Kernel context-switch save area layout for general capability registers.
- Debugger presentation of invalid-tag capability payloads.
- Future floating-point, vector, or wider capability-register classes.

## Verification Notes

Minimum conformance checks for later compiler, assembler, simulator, and ABI tests:

- A function with four capability arguments receives them in `C0-C3`.
- A fifth capability argument is stored in a 4-cell aligned stack capability slot.
- `CSC` of a valid stack-passed capability preserves payload and tag.
- `CLC` of a stack-passed capability restores payload and tag.
- Stack-passed local capabilities require `DSC` with `SL`.
- Mixed overflow arguments preserve source order and natural 2-cell or 4-cell alignment.
- Integer-only overflow layout matches E05-S01.
- A capability return is placed in `C0` with payload and tag.
- Caller-saved `C0-C5` may be clobbered by a call.
- A callee that writes `C6-C7` restores the exact entry payload and tag before `RET`.
- `ST48` is not used to spill capability values because it clears capability tags.
- A variadic callee can access register-passed capability varargs through a callee-created capability register save area.
- A valid capability tag passed in `C0-C3` or through a stack capability slot is visible at callee entry, and a valid tag returned in `C0` is visible to the caller at return.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Capability arguments use `C0-C3`. | Met. |
| Capability return uses `C0`. | Met. |
| Caller-saved capability registers are `C0-C5`. | Met. |
| Callee-saved capability registers are `C6-C7`. | Met. |
| Tag preservation across call boundaries is specified. | Met: payload and tag are preserved for arguments, returns, stack capability slots, and callee-saved registers; caller-saved registers are explicitly volatile. |

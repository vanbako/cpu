# E05-S01: Integer Calling Convention

Story: E05-S01

Status: Complete

Normative source: `design.md`, section 8

Prerequisite:

- `spec/E01-S02-integer-register-semantics.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E04-S02-integer-operation-set.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E05-S03-data-stack-model.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S02-sealed-entry-capabilities.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spikes/E14-S02-24-bit-toolchain-abi.md`

## Decision

CPU v0.1 uses a register-first integer calling convention.

The integer ABI assigns:

| Role | Registers |
| --- | --- |
| Integer argument registers | `D0-D5` |
| Integer return registers | `D0-D1` |
| Caller-saved integer registers | `D0-D11` |
| Callee-saved integer registers | `D12-D15` |

All `D0-D15` registers remain ordinary writable 48-bit architectural registers. The ABI roles are software contracts at call boundaries, not hardware privilege or protection rules.

## ABI Integer Value

An ABI integer value occupies one 48-bit integer register or one 2-cell stack slot.

Rules:

- A full-width scalar is passed as its 48-bit value.
- An unsigned narrow scalar is zero-extended to 48 bits by the caller.
- A signed narrow scalar is sign-extended to 48 bits by the caller.
- A boolean value is passed as `0` for false and `1` for true.
- Sub-cell language objects still occupy whole ABI integer values when passed as arguments or returns.

The callee may rely on these canonical extensions for ordinary prototyped calls. Language ABIs may define additional promotions, but they must produce the same 48-bit ABI integer values before the call boundary.

Integer registers do not carry capability tags and do not authorize memory access. Passing a cell address as an integer passes only a numeric value.

## Integer Arguments

Integer arguments are assigned in source order after any language-level scalar promotion.

The integer argument index in this story counts integer-class arguments only. Mixed integer/capability argument ordering, and the way mixed classes share an outgoing stack argument area, are finalized by E05-S02.

The first six integer arguments use registers:

| Argument index | Location |
| ---: | --- |
| 0 | `D0` |
| 1 | `D1` |
| 2 | `D2` |
| 3 | `D3` |
| 4 | `D4` |
| 5 | `D5` |

Argument indexes are zero-based in this story.

Integer argument 6 and later are overflow stack arguments.

## Overflow Integer Stack Arguments

Overflow integer arguments are placed in a caller-allocated outgoing argument area on the data stack.

At the public call boundary:

```text
arg_base = entry DSC.cursor
```

For integer argument `arg_index >= 6`:

```text
slot_index = arg_index - 6
slot_base  = arg_base + 2 * slot_index
slot_range = [slot_base, slot_base + 2)
```

The caller stores the 48-bit ABI integer value in that 2-cell slot using ordinary integer stack storage through `DSC`.

Rules:

- Every overflow integer slot is 2-cell aligned.
- The outgoing integer argument area size is rounded up to a multiple of 4 cells.
- If there is an odd number of overflow integer slots, the final 2-cell pad follows the last slot at the higher address.
- `DSC.cursor` is 4-cell aligned at the call boundary.
- The callee may read overflow arguments relative to its entry `DSC.cursor`.
- If the callee allocates a frame by moving `DSC.cursor`, it must preserve the entry argument base by its own frame convention before relying on stack arguments.

The caller owns allocation and release of the outgoing argument area. After the callee returns, the caller releases any call-specific outgoing argument area it allocated.

Mixed integer and capability stack argument layout is finalized by E05-S02. This story defines integer-only overflow slots and the rule that integer stack slots are 2 cells.

## Integer Return Values

Integer return values use:

| Return value | Location |
| --- | --- |
| Primary integer return | `D0` |
| Secondary integer return | `D1` |

Rules:

- A single ABI integer return is written in `D0`.
- Two ABI integer returns are written in `D0` and `D1`.
- Narrow integer returns use the same zero-extension or sign-extension rule as narrow integer arguments.
- A function that returns no integer value leaves `D0-D1` unspecified unless a language ABI defines a narrower rule.

Larger integer aggregates, structures, and multiple-return cases beyond two 48-bit integer values are not directly returned by this story. They use a caller-provided return object in memory or a language/runtime convention defined by later ABI stories.

## Caller-saved Integer Registers

`D0-D11` are caller-saved.

Rules:

- A callee may freely clobber `D0-D11`.
- `D0-D5` are both argument registers and caller-saved registers.
- `D0-D1` are both return registers and caller-saved registers.
- `D6-D11` are volatile temporary registers.
- A caller that needs a `D0-D11` value after a call must save it before the call and restore it after the call.

The caller may save volatile integer values in other integer registers that it owns, in stack spill slots, or through a language-specific frame convention.

## Callee-saved Integer Registers

`D12-D15` are callee-saved.

Rules:

- A callee that writes any of `D12-D15` must restore the exact 48-bit entry value before returning normally.
- The restore obligation applies to every normal return path from the function.
- A callee may use `D12-D15` for long-lived locals, loop state, or an optional integer frame cookie if it preserves them.
- No `D12-D15` register is reserved as a mandatory frame pointer in v0.1.

If a call does not return normally because it traps, unwinds through a runtime mechanism, or terminates the thread, the preservation contract is handled by the trap, unwind, or runtime ABI rather than by this normal function-call rule.

## Flags Across Calls

`SR.Z`, `SR.N`, `SR.C`, and `SR.V` are caller-saved.

Rules:

- A callee may execute `CMP`, `CMPU`, `TST`, or privileged/runtime code that changes flags.
- A caller must not rely on condition flags surviving a call.
- If a caller needs a condition after a call, it should materialize the condition into an integer register before the call, for example with `SETcc`.

User-mode code is not required to read `SR` directly to follow this convention.

## Calls, Returns, and Stack State

`CALL`, `CALLC`, and `RET` define control-flow mechanics and protected return-stack behavior. This story defines only integer register and integer stack-argument conventions layered on those instructions.

At a public function call boundary:

- `D0-D5` contain the first integer arguments.
- Overflow integer arguments, if any, are stored in the outgoing argument area starting at entry `DSC.cursor`.
- `DSC.cursor` is 4-cell aligned.
- `RSC` contains the protected return-stack state used by `CALL`, `CALLC`, and `RET`.
- `D12-D15` carry values the callee must preserve if it writes them.

At normal return:

- `D0-D1` contain integer return values, if any.
- `D12-D15` match their entry values.
- `DSC.cursor` is restored to the callee's entry value.
- The caller's outgoing argument area is still caller-owned and may be released by the caller.

A tail call is permitted when the current function has restored its callee-saved integer registers and adjusted `DSC.cursor` so the tail-called function observes a valid public call boundary.

## Variadic Integer Calls

Integer arguments to variadic functions use the same initial assignment as non-variadic calls:

- The first six integer arguments use `D0-D5`.
- Later integer arguments use overflow stack slots.

A variadic callee that evaluates a variable argument list is responsible for creating its own integer register save area in its frame if it needs stable memory addresses for register-passed integer arguments.

The abstract integer `va_list` state for this story contains:

| Field | Meaning |
| --- | --- |
| `next_int_reg` | Next integer argument register index, from 0 through 6. |
| `next_int_stack_slot` | Next overflow integer slot relative to the entry stack argument base. |

When `next_int_reg < 6`, the next integer vararg is read from `D[next_int_reg]` or from the callee's saved copy of that register. When `next_int_reg == 6`, further integer varargs are read from overflow stack slots.

Concrete in-memory `va_list` layout, mixed integer/capability variadic ordering, default language promotions, and ABI details for aggregate variadic arguments are deferred to the language ABI and E05-S02.

## Syscall Integer Convention

The baseline syscall convention follows the integer register ABI unless a platform ABI overrides it:

| Role | Location |
| --- | --- |
| Syscall number | `D0` |
| Integer syscall arguments | `D1-D5`, then overflow stack convention if a platform allows more |
| Integer syscall returns | `D0-D1` |

`SYS` and `SCALL` trap without advancing `PCC`; kernel software owns any policy for preserving or clobbering caller-saved registers during syscall handling. User code must treat `D0-D11` as volatile across a syscall unless its operating-system ABI states otherwise.

## Out of Scope for This Story

- Capability argument and return register assignment: E05-S02.
- Full mixed integer/capability stack argument layout: E05-S02 and E05-S03.
- Data-stack frame layout beyond integer overflow slots and call-boundary alignment: E05-S03.
- Protected return-stack storage layout: E05-S04.
- Aggregate, floating-point, vector, or future wider scalar ABI rules.
- Concrete language ABI documents for C, Rust, or other languages.
- Exception unwinding, signal frames, and trap-frame memory layout.

## Verification Notes

Minimum conformance checks for later compiler, assembler, simulator, and ABI tests:

- A function with six integer arguments receives them in `D0-D5`.
- A seventh integer argument is stored at `[entry DSC.cursor, entry DSC.cursor + 2)`.
- An eighth integer argument is stored at `[entry DSC.cursor + 2, entry DSC.cursor + 4)`.
- An odd count of overflow integer arguments reserves a final 2-cell pad so the outgoing area is 4-cell aligned.
- A single integer return is placed in `D0`.
- Two integer returns are placed in `D0-D1`.
- Caller-saved `D0-D11` may be clobbered by a call.
- A callee that writes `D12-D15` restores the exact 48-bit entry values before `RET`.
- Public call-boundary `DSC.cursor` values are 4-cell aligned.
- The callee restores `DSC.cursor` to its entry value before normal return.
- A caller does not rely on `SR.Z`, `SR.N`, `SR.C`, or `SR.V` surviving a call.
- An integer-only variadic callee can access register-passed varargs through a callee-created register save area and overflow varargs through stack slots.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Integer arguments use `D0-D5`. | Met. |
| Integer returns use `D0-D1`. | Met. |
| Caller-saved integer registers are `D0-D11`. | Met. |
| Callee-saved integer registers are `D12-D15`. | Met. |
| Variadic and overflow argument handling is defined or explicitly deferred. | Met: integer overflow slots and integer varargs are defined; mixed capability variadics and aggregate details are deferred. |

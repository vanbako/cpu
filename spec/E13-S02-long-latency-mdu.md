# E13-S02: Long-latency Multiply/Divide Unit

Story: E13-S02

Status: Complete

Normative source: `design.md`, section 16.2

Prerequisites:

- `spec/E04-S02-integer-operation-set.md`
- `spec/E13-S01-pipeline-stages.md`

Related sources:

- `spec/E01-S02-integer-register-semantics.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E12-S04-mandatory-counters.md`

## Decision

CPU v0.1 uses an independent multiply/divide unit named `MDU` for:

- `MUL`
- `MULU`
- `DIV`
- `DIVU`
- `MOD`
- `MODU`

The `MDU` is not a CSR interface. It returns results and faults through the normal pipeline result path, then architectural state is updated only by `WB` and `RT` according to E13-S01 and E07-S03.

## MDU Scope

The `MDU` executes only integer multiply, divide, and modulo operations from E04-S02.

It does not execute:

- Ordinary add/subtract/logical operations.
- Shifts and rotates.
- Capability operations.
- Memory operations.
- CSR or CCSR operations.
- Branches or control transfers.

All `MDU` instructions are user-mode instructions because their architectural instruction definitions are user-mode integer operations.

## Issue to MDU

An `MDU` instruction reaches the `ISS` stage like any other instruction.

Before issue, `ISS` must know:

- Source register operands are available or can be forwarded.
- Destination register busy state can be allocated.
- The `MDU` can accept the operation now or the pipeline must stall.
- The instruction has an in-order sequence number for precise retire.

On successful issue to the `MDU`:

- Source operands are captured.
- The selected operation width and write form are captured.
- The destination integer register is marked busy.
- The instruction's sequence number is associated with the MDU operation.
- The issuing pipeline may continue with younger independent instructions if E13-S03 hazard rules permit.

If the `MDU` cannot accept a new operation, `ISS` stalls the instruction in order until the unit can accept it or until the instruction is killed by an older redirect, trap, debug entry, interrupt, or reset.

## Multiplier

`MUL` and `MULU` may use a pipelined multiplier.

Required latency policy:

- A conforming v0.1 implementation may choose 2-cycle or 3-cycle multiplier latency.
- The chosen latency must be documented for the implementation.
- A simpler implementation may use a longer iterative multiplier only if it still exposes the same architectural behavior and documents the latency as implementation-defined beyond the recommended 2-3 cycle MVP target.

Required pipeline behavior:

- Pipelined multiplication may accept a new multiply operation before an older multiply has reached `WB`, subject to implementation resource limits.
- Every multiply result carries its original in-order sequence number.
- Results are delivered to the normal `WB` path.
- A multiply result is not architectural until the instruction reaches `RT`.
- Multiply overflow is handled by E04-S02 truncation rules and does not trap.

## Divider and Modulo

`DIV`, `DIVU`, `MOD`, and `MODU` may use an iterative divider.

Required behavior:

- The divider may be single-entry and non-pipelined.
- While the divider is busy, younger divide or modulo instructions wait at `ISS` unless the implementation documents a larger queue.
- Independent non-MDU instructions may continue only if scoreboarding and in-order retire constraints remain satisfied.
- Divide and modulo results are delivered through the normal `WB` path.

Divide-by-zero is the only arithmetic exception produced by the `MDU`.

If the divisor is zero:

- The selected fault is `DIVIDE_BY_ZERO`.
- No destination integer register value is produced.
- The fault packet remains associated with the instruction sequence number.
- The exception is reported only when that instruction reaches `RT`.
- `INSTRET` does not increment for the faulting instruction.

An implementation may detect divide-by-zero before starting the iterative divider. It may also detect it inside the divider. In either case, the architectural exception point is still `RT`.

## Destination Busy Tracking

The pipeline must track destination register busy state for every in-flight `MDU` instruction that writes an integer destination.

Rules:

- `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, and `MODU` mark `Dd` busy when they issue to the `MDU`.
- A younger instruction that reads a busy `Dd` must wait until the value can be forwarded or read according to E13-S03.
- A younger instruction that writes the same `Dd` must not retire before the older `MDU` instruction retires or is killed.
- If the `MDU` instruction faults, the destination busy state is cleared when the fault is handled at `RT`.
- If the `MDU` instruction is killed by an older fault or redirect before retire, its destination busy state is cleared and its result is discarded.

The exact scoreboard or busy-bit structure is owned by E13-S03. E13-S02 requires that such state exists for MDU destinations.

## Writeback and Retire

All MDU completions return through the normal writeback path.

Required flow:

```text
MDU complete -> WB result/fault packet -> RT in-order commit or trap
```

On normal completion:

- `WB` carries the computed integer result, destination register, write form, and sequence number.
- `RT` commits the destination register write when the instruction is oldest.
- `INSTRET` increments once at normal retire according to E12-S04.
- Condition flags are unchanged, as required by E04-S02.

On fault:

- `WB` carries a fault packet instead of a register result.
- `RT` reports the precise exception when the instruction is oldest.
- No destination register write commits.
- `INSTRET` does not increment.

The `MDU` must never write integer registers, flags, CSRs, capability registers, memory, or debug state directly.

## Precise Exception Interaction

MDU operations must preserve precise exceptions.

Rules:

- An older fault kills or suppresses younger in-flight `MDU` operations before they can update architectural state.
- A completed `MDU` result waits for in-order `RT` if an older instruction has not retired.
- A younger instruction cannot observe a completed MDU result as architectural state before the MDU instruction retires.
- Internal MDU state is not visible to trap handlers except through architectural state that has already retired.
- Trap entry does not expose partial MDU progress.

If a divide-by-zero operation is older than a completed younger multiply, the divide-by-zero traps first and the younger multiply result is discarded or replayed.

If a multiply completes internally and then an older load faults, the multiply does not update its destination register.

## CSR and Debug Visibility

MDU completion is not exposed through scalar CSRs, capability CSRs, debug CSRs, interrupt pending bits, or platform event registers in v0.1.

Required exclusions:

- No `MDU_DONE` CSR.
- No `MDU_RESULT` CSR.
- No `MDU_BUSY` mandatory architectural CSR.
- No interrupt on MDU completion.
- No debug halt solely because an MDU operation completed.

Debuggers and performance tools may infer MDU behavior from instruction retirement, counters, implementation trace, or future optional performance events, but not from mandatory MDU CSRs.

## Out of Scope for This Story

- Exact scoreboard, bypass, load-use, and structural hazard policy: E13-S03.
- Branch flush and mispredict recovery details: E13-S03 and E13-S04.
- Numeric multiplier or divider algorithms.
- Precise cycle counts for divide and modulo.
- Optional performance counters for MDU occupancy, stalls, or failures: E12-S05 or later profiles.
- Multi-issue or out-of-order execution.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `MUL` and `MULU` execute through the MDU and write results through normal register writeback.
- `DIV`, `DIVU`, `MOD`, and `MODU` execute through the MDU and write results through normal register writeback.
- A multiply result that completes internally before an older fault does not update its destination.
- A divide-by-zero reports `DIVIDE_BY_ZERO` at `RT` and leaves the destination unchanged.
- A younger dependent instruction waits for an older MDU destination or receives the value only through an allowed forwarding path.
- MDU destination busy state is set at issue and cleared on retire, fault, or kill.
- A second divide waits while a single-entry divider is busy.
- Independent non-MDU instructions can proceed around an in-flight MDU operation when hazards permit.
- `INSTRET` increments once for a normally retired MDU instruction.
- Faulting MDU instructions do not increment `INSTRET`.
- No CSR exposes MDU completion or result state.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Independent `MDU` is defined. | Met. |
| `MUL` may be pipelined with 2-3 cycle latency. | Met: 2-3 cycle pipelined multiplier is the recommended MVP target, with documented implementation latency required. |
| `DIV/MOD` may be iterative. | Met. |
| Destination register busy tracking is required. | Met. |
| Results return through normal register writeback. | Met. |
| MDU completion is not exposed through CSR. | Met. |

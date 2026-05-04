# E12-S03: Single-step

Story: E12-S03

Status: Complete

Normative source: `design.md`, section 15

Prerequisite:

- `spec/E12-S01-debug-halt-behavior.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E07-S06-nested-interrupt-rules.md`
- `spec/E12-S02-hardware-breakpoints-watchpoints.md`
- `spec/E12-S04-mandatory-counters.md`

## Decision

CPU v0.1 single-step is a precise debug facility controlled by `DEBUGCTL`.

When single-step is armed, the core allows exactly one eligible architectural instruction to complete normal retirement, then accepts a debug event with `DCAUSE=SINGLE_STEP` before any younger instruction retires and before an ordinary maskable interrupt is delivered at that post-retire boundary.

Faulting instructions, synchronous trap instructions, breakpoint debug events, watchpoint debug events, and trap or interrupt handler instructions do not complete single-step. They follow their normal exception or debug path first.

## `DEBUGCTL.STEP`

E12-S03 refines the `DEBUGCTL` field reservation from E12-S01 by assigning bit 5:

| Bits | Name | Access | Reset | Meaning |
| ---: | --- | --- | ---: | --- |
| `5` | `STEP` | K/debug `RW` | `0` | Enable one-instruction single-step after debug resume, debug-monitor return, ordinary trap return, or an explicit running-context arm. |
| `7:6` | `RES0` | `RZ/W0` | `0` | Reserved-zero. |

All other `DEBUGCTL` fields keep the E12-S01 definitions. Writes that attempt to set `DEBUGCTL[7:6]` raise `ILLEGAL_CSR_WRITE` and leave `DEBUGCTL` unchanged.

`DEBUGCTL.STEP` is sticky. Hardware does not clear it after a single-step event. A debugger or kernel that wants normal continuous execution must clear `STEP` before resuming or returning to the debugged context.

`DEBUGCTL.STEP` does not by itself request debug entry. It only controls whether a future eligible instruction retirement produces a single-step completion event.

## Hidden Arm State

Each core has hidden single-step arm state, called `STEP_ACTIVE` in this story. `STEP_ACTIVE` is not a CSR field and is not directly readable.

Cold reset clears both `DEBUGCTL.STEP` and `STEP_ACTIVE`.

Writing `DEBUGCTL.STEP=0` clears `STEP_ACTIVE`.

`STEP_ACTIVE` is set when `DEBUGCTL.STEP=1` and one of these events commits:

- Resume from `DEBUG_HALTED`.
- Successful `IRET` out of `DEBUG_MONITOR`.
- Successful `IRET` out of an ordinary trap or interrupt handler.
- A successful `CSRWR`, `CSRSET`, or `CSRCLR` that changes `DEBUGCTL.STEP` from `0` to `1` while the core is already running outside `DEBUG_HALTED`, outside `DEBUG_MONITOR`, and with `SR.EXL=0`.

For the CSR-write case, the CSR instruction that sets `STEP` does not consume the step. `STEP_ACTIVE` becomes eligible only after that CSR instruction has normally retired.

`STEP_ACTIVE` is cleared when:

- A single-step completion debug event is accepted.
- `DEBUGCTL.STEP` is cleared.
- Reset is accepted.
- Trap entry, interrupt entry, debug-monitor entry, or non-monitor debug halt entry begins.
- The selected instruction raises a synchronous exception or enters a non-step debug event before normal retirement.

The sticky `DEBUGCTL.STEP` bit remains unchanged when `STEP_ACTIVE` is cleared by trap, interrupt, or debug entry. If software later returns with `IRET` while `STEP=1`, `STEP_ACTIVE` is armed again for the restored context.

## Eligible Instructions

An instruction is eligible to complete single-step only if all of these are true:

- `STEP_ACTIVE=1` before the instruction is selected for execution.
- The core is not in `DEBUG_HALTED`.
- The core is not executing the E12-S01 `DEBUG_MONITOR`.
- `SR.EXL=0` for the instruction being stepped.
- The instruction reaches normal architectural retire and commits its normal effects.

Instructions executed by ordinary trap handlers, interrupt handlers, and debug-monitor software do not complete single-step while `SR.EXL=1`. Their successful `IRET` return arms the restored context if `DEBUGCTL.STEP=1`.

The stepped instruction is exactly one architectural instruction, independent of encoding size or latency. A multi-cycle instruction, cache-missing load, successful store, successful `SC48`, or taken branch still counts as one instruction if it reaches normal retire.

## Step Completion Event

When an eligible instruction normally retires with `STEP_ACTIVE=1`, hardware first commits the instruction's normal effects as defined by E07-S03. This includes destination registers, memory payload and tag effects, `PCC` updates, `SR` updates, and the `INSTRET` increment defined by E12-S04.

Hardware then accepts a debug event:

```text
CAUSE = DEBUG_HALT
DCAUSE = SINGLE_STEP
TVAL = retired instruction cell address
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

`TVAL` is a cell address and does not encode the hidden slot bit.

For non-monitor `DEBUG_HALTED` entry, the current `PCC` is the next instruction to execute after the stepped instruction. `PCC.slot` is the next slot selected by the retired instruction's normal control-flow behavior.

For `DEBUGCTL.MONITOR=1`, debug-monitor entry saves that same next `PCC` and next slot in `EPCC`, then enters the debug vector according to E12-S01.

If debug-monitor vector entry fails for a single-step event, E12-S01 fallback behavior applies: the core enters `DEBUG_HALTED` with `DCAUSE=ENTRY_FAILURE` and `TVAL` set to the failed vector cell when representable. The stepped instruction has already retired.

## Fault and Event Priority

Single-step completion is lower priority than any fault or debug event that prevents the selected instruction from retiring normally.

The following conditions take priority over single-step completion for the selected instruction:

- Fetch capability, translation, placement, alignment, or decode faults.
- Instruction privilege, CSR, CCSR, operand capability, arithmetic, memory, and effective-access faults.
- `BRK`, `SYS`, and `SCALL` ordinary synchronous traps.
- `BRK` debug entry when `DEBUGCTL.BRKHALT=1`.
- E12-S02 instruction breakpoint and data watchpoint debug events.

If any of those conditions is selected, the instruction does not normally retire, `INSTRET` does not increment for that instruction, and no `DCAUSE=SINGLE_STEP` event is reported for that attempt.

After an otherwise successful instruction retires, single-step completion has the E07-S02 priority-16 position. It is delivered before ordinary maskable interrupts at the same post-retire boundary.

If a maskable interrupt is deliverable before any stepped instruction has executed, interrupt entry may occur first according to E12-S01 and E07-S05. That interrupt entry does not complete single-step. The interrupt handler runs with step completion suppressed while `SR.EXL=1`, and `IRET` rearms the restored context when `DEBUGCTL.STEP=1`.

An externally forced debug entry or platform fatal condition in the E07-S02 priority-1 class may override single-step. If a non-forced `HALTREQ` or external halt request is sampled at the same post-retire boundary as a single-step completion, `DCAUSE=SINGLE_STEP` is reported because the one-instruction step has completed.

## Slot and Control-transfer Behavior

Single-step observes the E01-S05 and E04-S01 hidden-slot model.

For ordinary sequential fall-through:

| Retired instruction | Stop location after step |
| --- | --- |
| 12-bit instruction at slot 0 | Same cell, slot 1. |
| 12-bit instruction at slot 1 | Next cell, slot 0. |
| 24-bit instruction at slot 0 | Next cell, slot 0. |
| 48-bit instruction at fetch-group slot 0 | Next fetch group, slot 0. |

For explicit control transfers, the stop location is the committed control-flow result:

- A taken direct branch, `JMP`, `CALL`, or `RET` stops at the committed target with `PCC.slot=0`.
- A not-taken conditional branch stops at the normal sequential fall-through location.
- A 12-bit not-taken conditional branch in slot 0 stops at slot 1 of the same cell.
- `CALL` stops at the call target, not at the sealed return continuation.
- `RET` stops at the returned target with `PCC.slot=0`.

`IRET` does not itself complete single-step while returning out of `SR.EXL=1` state. Instead, if `DEBUGCTL.STEP=1`, successful `IRET` arms the restored context. If `IRET` restores `PCC.slot=1`, the next instruction attempted is the slot-1 instruction. If that slot-1 location is a legal 12-bit instruction and retires normally, the single-step event stops at that instruction's normal successor.

If an `IRET` restore target is invalid or the restored slot-1 location is not a legal instruction start, the normal `IRET` fault or subsequent fetch/placement fault is reported before any single-step completion.

## Debug State Interaction

Single-step is suppressed in `DEBUG_HALTED`. While halted, no ordinary instruction is fetched or retired, and `STEP_ACTIVE` is clear.

Single-step is also suppressed while executing the E12-S01 `DEBUG_MONITOR`. A monitor can inspect or modify state without being single-stepped by a sticky `DEBUGCTL.STEP` bit. To continue normally, the monitor clears `STEP` before `IRET`. To step another instruction, it leaves `STEP=1` and exits with `IRET`.

If a single-step event enters non-monitor `DEBUG_HALTED`, resuming without clearing `STEP` arms another one-instruction step. This supports repeated debugger step commands through repeated `RESUME` operations.

If a single-step event enters `DEBUG_MONITOR`, the monitor must save any one-level trap state it needs before enabling nesting or performing operations that may trap, as required by E12-S01.

## Counter and Wait Behavior

The stepped instruction increments `INSTRET` exactly as any normally retired instruction does. The single-step debug entry itself does not increment `INSTRET`.

`CYCLE` follows E12-S04:

- It does not increment while the core is in `DEBUG_HALTED`.
- It increments while debug-monitor software executes.
- It increments during ordinary running execution and trap or interrupt handler execution.

A normally retired `WFI` counts as the stepped instruction. When `STEP_ACTIVE=1`, the single-step event is accepted after `WFI` retirement and before the core can remain architecturally parked in the wait state.

If an interrupt is already deliverable at the boundary before `WFI` executes, interrupt entry occurs first and `WFI` does not retire. No single-step completion is reported for `WFI` in that case.

## Out of Scope

E12-S03 does not define:

- Source-level step-over, step-out, or range-step behavior.
- Branch trace, last-branch records, or retired-instruction trace buffers.
- Separate user-only or kernel-only step masks.
- A control bit that forces maskable interrupts to be held off before the first stepped instruction.
- A way to single-step debug-monitor instructions.

## Verification Notes

E12-S03 tests should cover:

- Setting `DEBUGCTL.STEP`, resuming from `DEBUG_HALTED`, retiring one ALU instruction, and re-entering debug with `DCAUSE=SINGLE_STEP`.
- Repeated resume with `STEP=1` stepping one instruction per resume.
- Clearing `STEP` before resume causing continuous execution without step events.
- A faulting instruction reporting its normal exception and not reporting `SINGLE_STEP`.
- `BRK` with `BRKHALT=0` reporting the ordinary `BREAKPOINT` trap instead of `SINGLE_STEP`.
- `BRK` with `BRKHALT=1` reporting `DCAUSE=BRK` instead of `SINGLE_STEP`.
- Instruction breakpoint and data watchpoint events taking priority over step completion.
- A successful load, store, branch, call, return, and `SC48` failure each counting as one stepped instruction when they retire normally.
- A stepped 12-bit slot-0 instruction stopping at slot 1.
- A stepped 12-bit slot-1 instruction stopping at the next cell slot 0.
- Successful `IRET` restoring slot 1 and arming the restored slot-1 instruction.
- Pending maskable interrupt before the first stepped instruction entering the interrupt handler without completing step, then `IRET` rearming the restored context.
- Pending maskable interrupt after the stepped instruction retiring being delayed until after the `SINGLE_STEP` debug event.
- Stepped `WFI` entering debug after retirement instead of remaining parked.

## Story Acceptance Review

| Acceptance criterion | Evidence |
| --- | --- |
| Single-step mode is controlled by debug state. | Met: `DEBUGCTL.STEP` controls sticky step enable and hidden arm state. |
| One architectural instruction retires before debug re-entry. | Met: an eligible instruction commits normal effects and `INSTRET` before `DCAUSE=SINGLE_STEP`. |
| Faulting instructions report their normal fault before or instead of step completion according to a defined priority. | Met: fault, trap, breakpoint, and watchpoint priority is defined ahead of single-step completion. |
| Slot behavior with 12-bit instructions is specified. | Met: slot-0, slot-1, control-transfer, and `IRET` slot cases are specified. |

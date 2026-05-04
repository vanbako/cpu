# E12-S04: Mandatory Counters

Story: E12-S04

Status: Complete

Normative source: `design.md`, section 15

Prerequisite:

- `spec/E02-S02-mandatory-scalar-csrs.md`

Related sources:

- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E12-S01-debug-halt-behavior.md`

## Decision

CPU v0.1 defines two mandatory per-core 48-bit counters:

| CSR | Number | User read | User write | Kernel read | Kernel write | Reset |
| --- | ---: | --- | --- | --- | --- | ---: |
| `CYCLE` | `0x02` | Allowed | Fault | Allowed | Allowed | `0` |
| `INSTRET` | `0x03` | Allowed | Fault | Allowed | Allowed | `0` |

Both counters wrap modulo `2^48`. v0.1 defines no overflow interrupt, sticky overflow bit, saturation mode, or high-half shadow CSR for these mandatory counters.

## Width and Wraparound

`CYCLE` and `INSTRET` are exactly 48-bit unsigned counters.

Increment behavior is modulo `2^48`:

```text
next = (current + 1) mod 2^48
```

Software that needs intervals longer than `2^48 - 1` counts must extend the counters in software by sampling frequently enough to observe wraparound.

Counter reads return the current 48-bit value. Reads have no side effects and do not latch a multi-counter snapshot. If software needs a consistent pair, it must use a retry sequence appropriate for its sampling policy.

## `CYCLE`

`CYCLE` counts architectural core cycles for the local core.

Rules:

- `CYCLE` increments once per architectural core cycle while the core is started and not in `DEBUG_HALTED`.
- The boot core begins with `CYCLE=0` at cold reset.
- A secondary core begins architecturally visible execution with `CYCLE=0` unless the platform startup profile explicitly documents earlier counter activity.
- `CYCLE` does not increment while a core is in cold-reset `STOPPED` state.
- `CYCLE` increments while ordinary instructions execute.
- `CYCLE` increments during trap entry, interrupt entry, debug-monitor entry, and kernel trap/debug-monitor execution.
- `CYCLE` increments while a started core is waiting in a retired `WFI` wait state.
- `CYCLE` does not increment while a core is in `DEBUG_HALTED`.

`CYCLE` is not a wall-clock timer. The `TIMER` CSR remains the architectural timer source for timer interrupts and elapsed-time facilities.

Implementations may vary frequency, stall cycles, and low-power behavior if the visible `CYCLE` rule above is preserved for architecturally started, non-halted execution.

## `INSTRET`

`INSTRET` counts normally retired architectural instructions on the local core.

An instruction increments `INSTRET` exactly once when it reaches normal architectural retire and commits its normal effects.

The following increment `INSTRET` on successful normal retire:

- Integer ALU and compare instructions.
- Capability derivation instructions.
- Loads and stores, including `LD48`, `ST48`, `CLC`, and `CSC`.
- `LL48`.
- `SC48` success and non-trapping `SC48` failure.
- Taken and not-taken branches.
- `CALL`, `CALLC`, `RET`, and `JMP`.
- `IRET` when it successfully returns from trap, interrupt, or debug-monitor state.
- `FENCE`, `FENCE.I`, and `SFENCE.VM` when they complete normally.
- `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` when they complete normally.
- `WFI` when it retires before entering the wait state.
- `PAUSE`.
- CSR and CCSR instructions that complete normally, subject to the explicit counter-write rule below.

The following do not increment `INSTRET`:

- Faulting instructions.
- Instructions killed before retire.
- Instructions suppressed by branch, trap, interrupt, debug, or reset redirection.
- `BRK` on the ordinary breakpoint trap path.
- `BRK` on the debug event path.
- `SYS` and `SCALL`.
- Trap entry and interrupt entry themselves.
- Debug halt entry and debug-monitor entry themselves.
- Cycles spent in `DEBUG_HALTED`.
- Cycles spent waiting after a retired `WFI`.

Trap handlers, interrupt handlers, and debug-monitor software are ordinary kernel instruction streams after entry. Their instructions increment `INSTRET` when they normally retire.

## Explicit Counter Writes

Kernel writes to `CYCLE` or `INSTRET` set the visible counter value.

Rules:

- User-mode writes to `CYCLE` or `INSTRET` raise `CSR_PRIVILEGE_FAULT` and leave the counter unchanged.
- Kernel `CSRWR`, `CSRSET`, and `CSRCLR` follow the E02-S04 read-modify-write rules for CSR atomicity.
- A normal retiring instruction that explicitly writes `INSTRET` does not also apply the implicit `INSTRET` increment for itself. The explicit write result is the final visible `INSTRET` value after the instruction retires.
- A normal retiring instruction that explicitly writes `CYCLE` sets the visible `CYCLE` value at retire. Later architectural core cycles increment from that written value.
- If a counter write and a natural counter increment would otherwise target the same visible counter update point, the explicit CSR write wins.

These rules let kernel software set an exact counter value for tests, context setup, or profiling policy.

## Read Visibility and Ordering

Counter reads are ordinary CSR reads.

Rules:

- `CSRRD CYCLE` returns the current local `CYCLE` value.
- `CSRRD INSTRET` returns the current local `INSTRET` value.
- Counter reads do not serialize data memory, instruction fetch, TLBs, or cache maintenance.
- Counter reads do not imply `FENCE`, `FENCE.I`, or `SFENCE.VM`.
- Counter writes are ordered as ordinary CSR writes. They do not order data memory beyond the CSR instruction's normal program-order execution.

Because `CYCLE` can advance between instructions, two consecutive reads may return different values even without intervening memory operations.

Because `INSTRET` increments on ordinary retired instructions, a `CSRRD INSTRET` followed by another normally retired instruction and a second `CSRRD INSTRET` observes the intervening retirements unless kernel software writes the counter.

## Debug and Wait Interaction

`DEBUG_HALTED` stops both mandatory counters for the halted core:

- `CYCLE` does not increment.
- `INSTRET` does not increment because no ordinary instructions retire.

Debug-monitor software is not halted. Once debug-monitor entry succeeds, monitor instructions increment `CYCLE` and `INSTRET` like ordinary kernel instructions.

`WFI` accounting:

- If `WFI` faults because it is executed outside kernel mode, it does not increment `INSTRET`.
- If a deliverable interrupt is accepted before `WFI` retires, `WFI` does not increment `INSTRET`.
- If `WFI` retires and enters wait, `INSTRET` increments once for the retired `WFI`.
- While the core remains in the `WFI` wait state, `CYCLE` increments and `INSTRET` does not.
- On wakeup, any interrupt handler or resumed instruction stream increments `INSTRET` according to ordinary retire rules.

## Overflow Behavior

Overflow is ordinary modulo wraparound.

When `CYCLE = 0xFFFF_FFFF_FFFF` and one counted cycle occurs:

```text
CYCLE = 0
```

When `INSTRET = 0xFFFF_FFFF_FFFF` and one counted instruction retires:

```text
INSTRET = 0
```

No exception, interrupt, debug event, CSR bit, or `IPENDING` state is generated solely by mandatory counter overflow.

Extended performance counter overflow behavior is deferred to E12-S05.

## Out of Scope for This Story

- `TIMER` frequency, wrap, and wall-clock behavior beyond E02-S02 and E07-S05.
- `PMC0-PMC7` extended performance counters: E12-S05.
- `PERFSEL` selector semantics: E12-S05.
- Per-process virtualized counters, counter filtering, and counter inhibit controls.
- Counter overflow interrupts or sticky overflow reporting.
- Multi-counter atomic snapshot instructions.

## Verification Notes

Minimum conformance checks for later simulator, firmware, OS, and RTL work:

- `CYCLE` and `INSTRET` reset to `0`.
- User-mode reads of `CYCLE` and `INSTRET` succeed.
- User-mode writes to `CYCLE` and `INSTRET` fault and leave the counter unchanged.
- Kernel writes to `CYCLE` and `INSTRET` set exact visible values.
- `CYCLE` wraps from `0xFFFF_FFFF_FFFF` to `0`.
- `INSTRET` wraps from `0xFFFF_FFFF_FFFF` to `0`.
- A normally retired integer instruction increments `INSTRET` once.
- A faulting instruction does not increment `INSTRET`.
- `BRK`, `SYS`, and `SCALL` do not increment `INSTRET` on trap entry.
- A successful `IRET` increments `INSTRET` once.
- Successful and failed non-trapping `SC48` both increment `INSTRET`.
- A retired `WFI` increments `INSTRET` once before wait.
- Waiting after `WFI` increments `CYCLE` but not `INSTRET`.
- `DEBUG_HALTED` increments neither `CYCLE` nor `INSTRET`.
- Debug-monitor instructions increment both counters according to ordinary rules.
- A kernel write to `INSTRET` does not also add an implicit retire increment for that CSR-writing instruction.
- Mandatory counter overflow does not set interrupt pending state.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CYCLE` is defined. | Met. |
| `INSTRET` is defined. | Met. |
| Counter width and overflow behavior are specified. | Met: both counters are 48-bit modulo counters with no mandatory overflow trap or interrupt. |
| Privilege access policy is specified. | Met: user reads are allowed, user writes fault, and kernel reads/writes are allowed. |

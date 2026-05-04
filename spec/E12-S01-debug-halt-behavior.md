# E12-S01: Breakpoint and Debug Halt Behavior

Story: E12-S01

Status: Complete

Normative source: `design.md`, section 15

Prerequisites:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E07-S02-exception-classes.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E07-S06-nested-interrupt-rules.md`
- `spec/E08-S02-ll-sc-progress-guarantee.md`
- `spec/E11-S01-cold-reset-state.md`

## Decision

CPU v0.1 defines a minimal architectural debug model with:

- Precise `BRK` behavior.
- A debug halt event class using `CAUSE=DEBUG_HALT`.
- A non-executing `DEBUG_HALTED` core state for external debugger control.
- An optional software debug-monitor entry path through a separate vector-table index.
- Halt and resume control through the mandatory per-core `DEBUGCTL` CSR.

The transport used by an external debugger to read or write halted core state is platform-defined. This story defines the architectural state transitions that such a debugger observes.

## Debug Control CSR

`DEBUGCTL` is the mandatory fast CSR assigned by E02-S02 at CSR number `0x0E`.

`DEBUGCTL` is per-core, kernel-readable, kernel-writable, and `WARL`. User-mode access follows the E02-S02 CSR privilege rules and raises `CSR_PRIVILEGE_FAULT` or the applicable CSR access fault.

v0.1 assigns these fields:

| Bits | Name | Access | Reset | Meaning |
| ---: | --- | --- | ---: | --- |
| `0` | `BRKHALT` | K `RW` | `0` | Route `BRK` to the debug event path instead of the ordinary `BREAKPOINT` trap. |
| `1` | `MONITOR` | K `RW` | `0` | Route debug events to the software debug-monitor vector instead of `DEBUG_HALTED` when vector entry is possible. |
| `2` | `HALTREQ` | K/debug `W1S`, reads pending request | `0` | Request debug entry at the next precise boundary. |
| `3` | `RESUME` | K/debug `W1`, reads `0` | `0` | Resume a core from `DEBUG_HALTED` when written by a debugger or platform debug controller. |
| `4` | `HALTED` | `RO` | `0` | Core is in `DEBUG_HALTED` and is not retiring ordinary instructions. |
| `7:5` | `RES0` | `RZ/W0` | `0` | Reserved for E12-S02 and E12-S03. |
| `11:8` | `DCAUSE` | `RO` | `0` | Last debug event source. |
| `47:12` | `RES0` | `RZ/W0` | `0` | Reserved. |

Writes that set reserved-zero bits to one raise `ILLEGAL_CSR_WRITE` and leave `DEBUGCTL` unchanged.

`DCAUSE` values:

| Value | Name | Meaning |
| ---: | --- | --- |
| `0x0` | `NONE` | No debug event has been recorded since reset. |
| `0x1` | `EXTERNAL_HALT` | Platform debug controller requested halt. |
| `0x2` | `HALTREQ` | `DEBUGCTL.HALTREQ` requested halt. |
| `0x3` | `BRK` | `BRK` entered the debug event path because `DEBUGCTL.BRKHALT=1`. |
| `0x4` | `ENTRY_FAILURE` | Trap, interrupt, or debug-monitor vector entry failed and the core fell back to debug halt. |
| `0x5` | `HW_BREAKPOINT` | Reserved for E12-S02 hardware instruction breakpoints. |
| `0x6` | `WATCHPOINT` | Reserved for E12-S02 data watchpoints. |
| `0x7` | `SINGLE_STEP` | Reserved for E12-S03 single-step completion. |
| `0x8-0xF` | reserved | Reserved for future debug event sources. |

`DCAUSE` is updated by hardware on debug entry and reset to `NONE` on cold reset. Software writes to `DEBUGCTL` do not directly change `DCAUSE`.

## Debug States

Each core is in one of these debug-related architectural states:

| State | Meaning |
| --- | --- |
| `RUNNING` | The core fetches, executes, and retires ordinary architectural instructions. |
| `DEBUG_HALTED` | The core is stopped for debugger control and retires no ordinary instructions. |
| `DEBUG_MONITOR` | The core is executing privileged debug-monitor software entered through the debug vector. |

`DEBUG_MONITOR` is ordinary kernel execution with `SR.PRIV=K` and `SR.EXL=1`. It is named separately only to describe how the core reached that code.

`DEBUG_HALTED` is not kernel mode, user mode, an interrupt handler, or a low-power `WFI` wait. While halted:

- No ordinary instruction is fetched, decoded, executed, or retired.
- `INSTRET` does not increment.
- Ordinary maskable interrupts are not delivered.
- `WFI` wake conditions are not evaluated as instruction retirement.
- The core may still respond to reset and platform fatal events.
- The platform debug controller may inspect or modify architecturally visible state according to platform debug-access rules.

## Debug Event Sources

v0.1 defines these mandatory debug event sources:

| Source | When recognized | `DCAUSE` |
| --- | --- | --- |
| External halt request | At a precise boundary selected by the platform debug controller. | `EXTERNAL_HALT` |
| `DEBUGCTL.HALTREQ` | After the CSR write requesting halt has committed, at the next precise boundary. | `HALTREQ` |
| `BRK` with `DEBUGCTL.BRKHALT=1` | At the precise point where the `BRK` instruction would otherwise take its ordinary trap. | `BRK` |
| Entry failure fallback | When trap, interrupt, or debug-monitor entry cannot fetch a valid vector. | `ENTRY_FAILURE` |

E12-S02 adds hardware instruction breakpoint and watchpoint sources. E12-S03 adds single-step.

Debug events have higher priority than ordinary maskable interrupts at the same precise boundary. A synchronous exception from the current instruction has priority over an external halt request unless the event is an externally forced halt classified by E07-S02 priority 1.

`BRK` with `DEBUGCTL.BRKHALT=0` remains the E04-S04 ordinary precise breakpoint trap:

```text
CAUSE = BREAKPOINT
TVAL = faulting PCC.cursor
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

`BRK` with `DEBUGCTL.BRKHALT=1` does not take the ordinary `BREAKPOINT` trap. It enters the debug event path with `DCAUSE=BRK` and `CAUSE=DEBUG_HALT`.

## Debug Event Reporting

When a debug event is accepted, hardware records:

```text
CAUSE       = DEBUG_HALT
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
DEBUGCTL.DCAUSE = selected debug event source
```

`TVAL` is:

| Source | `TVAL` |
| --- | --- |
| External halt request | `0` unless the platform reports a more specific cell address. |
| `DEBUGCTL.HALTREQ` | `0`. |
| `BRK` debug event | Faulting `BRK` instruction cell address. |
| Entry failure fallback | Failed vector cell address when representable, otherwise `0`. |

All `TVAL` addresses are cell addresses.

Debug event reporting does not write `CAPCAUSE` or `FAULTCAPIDX` with stale capability-fault information. If a debug event is accepted, the capability-fault reporting state is set to `NONE`.

## Debug Halt Entry

When `DEBUGCTL.MONITOR=0`, an accepted debug event enters `DEBUG_HALTED`.

Required entry effects:

```text
DEBUGCTL.HALTED = 1
DEBUGCTL.HALTREQ = 0
DEBUGCTL.DCAUSE = selected debug event source
CAUSE = DEBUG_HALT
TVAL = source-specific debug value
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

The core preserves the current execution state for debugger inspection:

- `PCC` remains the next instruction to execute, or the faulting `BRK` instruction for `BRK` debug entry.
- `PCC.slot` is preserved.
- `SR.PRIV`, `SR.IE`, `SR.EXL`, `SR.PIE`, and `SR.PPRIV` are preserved.
- `EPCC` is not modified by non-monitor debug halt entry.
- General integer registers, general capability registers, special capability registers, memory payload, and memory tags are not modified by halt entry.

Debug halt entry is not an ordinary retired instruction and does not increment `INSTRET`.

If `BRK` enters `DEBUG_HALTED`, resuming without changing `PCC` re-executes the same `BRK`. A debugger that wants to continue after the breakpoint must advance `PCC` according to the decoded instruction size or patch/disable the breakpoint before resume.

## Debug Monitor Vector

When `DEBUGCTL.MONITOR=1`, an accepted debug event attempts to enter privileged software at a separate debug vector.

The debug vector uses the same vector table base and stride model as E07-S05 interrupts, but a reserved debug index:

```text
debug_vector_index = 4
stride_cells = 4 << TVEC.VSHIFT
debug_vector_cell = TVC.cursor + debug_vector_index * stride_cells
debug_pcc = TVC with cursor = debug_vector_cell
debug_slot = 0
```

With reset `TVEC=0`, the debug vector target is `TVC.cursor + 16` cells. Interrupt vector indexes `1-3` remain timer, software IPI, and external interrupt. Index `0` remains the direct synchronous exception entry.

Before debug-monitor entry can commit, `TVC` and `debug_vector_cell` must pass the same authorization checks as interrupt vector entry:

| Check | Failure |
| --- | --- |
| `TVC.tag` is valid | Debug monitor entry failure. |
| `TVC` is unsealed | Debug monitor entry failure. |
| `TVC` has `EX` | Debug monitor entry failure. |
| `debug_vector_cell` is representable as a 48-bit cell address | Debug monitor entry failure. |
| `debug_vector_cell` is inside `TVC.bounds` | Debug monitor entry failure. |

On successful debug-monitor entry, hardware performs a trap-like save into the one hardware saved level:

```text
EPCC.payload = interrupted_or_faulting_PCC.payload
EPCC.tag     = interrupted_or_faulting_PCC.tag
EPCC.slot    = interrupted_or_faulting_PCC.slot

CAUSE        = DEBUG_HALT
TVAL         = source-specific debug value
CAPCAUSE     = NONE
FAULTCAPIDX  = NONE

SR.PIE       = old SR.IE
SR.IE        = 0
SR.PPRIV     = old SR.PRIV
SR.PRIV      = K
SR.EXL       = 1

PCC.payload  = debug_pcc.payload
PCC.tag      = debug_pcc.tag
PCC.slot     = 0
SR.SLOT      = 0

DEBUGCTL.HALTREQ = 0
DEBUGCTL.HALTED  = 0
DEBUGCTL.DCAUSE  = selected debug event source
```

Debug-monitor entry does not increment `INSTRET`.

Because debug-monitor entry uses `EPCC`, `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, `SR.PIE`, and `SR.PPRIV`, it overwrites the one hardware saved level just like trap or interrupt entry. Debug-monitor software must save a software frame before enabling nesting or before calling code that may trap.

If debug-monitor entry fails, the core must not fetch through the invalid vector. It falls back to `DEBUG_HALTED` with `DCAUSE=ENTRY_FAILURE`, `CAUSE=DEBUG_HALT`, and `TVAL` set to the failed vector cell when representable.

## Resume and Exit

There are two debug exits.

### Resume From `DEBUG_HALTED`

A core leaves `DEBUG_HALTED` when the platform debug controller writes `DEBUGCTL.RESUME=1` or performs an equivalent documented resume action.

Resume effects:

```text
DEBUGCTL.HALTED = 0
DEBUGCTL.HALTREQ = 0
DEBUGCTL.RESUME read value remains 0
```

The core resumes at the current `PCC` and current `PCC.slot`. If the debugger modified `PCC`, `SR`, registers, memory, or capability state while halted, execution resumes from the modified state and the normal architectural checks apply.

If a maskable interrupt is pending and enabled after resume, interrupt delivery may occur at the next precise boundary before the resumed instruction executes.

### Exit From `DEBUG_MONITOR`

Debug-monitor software exits with the normal `IRET` path defined by E04-S04 and E07-S06.

`IRET` restores `PCC`, `PCC.slot`, `SR.IE`, `SR.PRIV`, and `SR.EXL` from `EPCC`, `SR.PIE`, and `SR.PPRIV`. A monitor may modify `EPCC` before `IRET` to skip a `BRK`, redirect execution, or resume after a patched instruction.

`DEBUGCTL.HALTED` remains `0` during debug-monitor execution and after `IRET`.

## External Debug Access

The external debugger interface is platform-defined, but it must preserve these architectural rules:

- It must not create a valid capability tag from integer data or untagged memory payload.
- It must preserve capability payload and tag atomicity when reading or writing capability registers or capability memory slots.
- It must not report a core as `RUNNING` while `DEBUGCTL.HALTED=1`.
- It must not let a halted core retire ordinary instructions before resume.
- If it modifies memory that may be fetched as code, it must use the same instruction-cache synchronization requirements as privileged software before relying on execution of the modified code.

External debug memory access authority, authentication, physical transport, and host protocol are platform security policy, not architectural ISA behavior.

## Interaction With Other State

Debug entry clears any active `LL48` reservation on the affected core, as required by E08-S02.

Debug halt entry does not drain the store buffer. Older retired stores may still become globally visible according to E08-S03 unless the platform debug controller chooses to quiesce the memory system before reporting the core halted.

Cold reset clears `DEBUGCTL`, leaves `HALTED=0`, and does not enter debug halt by default. Halt-on-reset is a platform debug option outside mandatory v0.1 reset behavior.

`WFI` must wake for a debug event. If a debug event is accepted while the core is waiting in `WFI`, the core enters `DEBUG_HALTED` or `DEBUG_MONITOR` instead of continuing ordinary fall-through execution.

## Out of Scope for This Story

- Hardware instruction breakpoint and data watchpoint match registers: E12-S02.
- Single-step behavior and priority: E12-S03.
- Mandatory counter halt behavior: E12-S04.
- Extended performance counters and debug event counters: E12-S05.
- External debugger authentication, transport, packet format, and memory-access privilege policy.
- Debug access to protected return-stack internals beyond the architectural register and memory integrity rules above.

## Verification Notes

Minimum conformance checks for later simulator, debugger, and RTL work:

- `DEBUGCTL=0` after reset leaves `BRK` on the ordinary `BREAKPOINT` trap path.
- User-mode access to `DEBUGCTL` faults.
- Kernel writes to reserved `DEBUGCTL` bits fault and leave `DEBUGCTL` unchanged.
- `BRK` with `BRKHALT=0` raises `CAUSE=BREAKPOINT` and enters the normal synchronous trap path.
- `BRK` with `BRKHALT=1` reports `CAUSE=DEBUG_HALT` and `DCAUSE=BRK`.
- Debug halt entry preserves `PCC` and `PCC.slot`.
- Debug halt entry does not modify `EPCC`.
- Debug halt entry sets `DEBUGCTL.HALTED=1`.
- A halted core retires no ordinary instructions and does not increment `INSTRET`.
- Resume clears `HALTED` and resumes at the current `PCC`.
- Resuming from a halted `BRK` without advancing `PCC` re-executes `BRK`.
- With `MONITOR=1`, a debug event enters vector index 4 using `TVC` and `TVEC.VSHIFT`.
- Debug-monitor entry saves the interrupted or faulting `PCC` and slot in `EPCC`.
- Debug-monitor entry sets `SR.PRIV=K`, `SR.EXL=1`, and `SR.IE=0`.
- Debug-monitor entry failure falls back to `DEBUG_HALTED` instead of fetching through an invalid vector.
- Debug entry clears active LL/SC reservation state.
- `WFI` wakes for a debug event.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `BRK` instruction behavior is defined. | Met: ordinary breakpoint trap by default, debug event path when `DEBUGCTL.BRKHALT=1`. |
| Debug halt exception class is defined. | Met: accepted debug events report `CAUSE=DEBUG_HALT`. |
| Debug mode entry and exit are specified. | Met: `DEBUG_HALTED`, debug-monitor entry, resume, and `IRET` exit are specified. |
| A separate debug vector is defined. | Met: debug-monitor vector index 4 is separate from direct exception and mandatory interrupt vectors. |
| Halt/resume control is exposed through debug state. | Met: `DEBUGCTL.HALTREQ`, `HALTED`, `RESUME`, and `DCAUSE` are defined. |

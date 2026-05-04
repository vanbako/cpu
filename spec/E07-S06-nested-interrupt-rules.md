# E07-S06: Nested Interrupt Rules

Story: E07-S06

Status: Complete

Normative source: `design.md`, section 10.5

Prerequisites:

- `spec/E07-S04-trap-entry.md`
- `spec/E07-S05-vectored-interrupts.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`

## Decision

CPU v0.1 has one hardware saved trap level.

The hardware saved level consists of:

- `EPCC` payload, tag, and hidden slot.
- `CAUSE`.
- `TVAL`.
- `CAPCAUSE`.
- `FAULTCAPIDX`.
- `SR.PIE`.
- `SR.PPRIV`.

Every successful synchronous trap entry and every successful interrupt entry overwrites that one saved level.

There is no hardware trap-state stack, no automatic memory trap frame, and no automatic nested-interrupt frame push.

## Entry State

After either E07-S04 synchronous trap entry or E07-S05 interrupt entry:

```text
SR.PRIV = K
SR.EXL  = 1
SR.IE   = 0
```

`SR.PIE` contains the interrupted `SR.IE` value.

`SR.PPRIV` contains the interrupted `SR.PRIV` value.

`EPCC` contains the interrupted or faulting execution capability and hidden slot.

While this entry state remains unchanged, ordinary maskable interrupt delivery is disabled. Pending interrupt sources may remain pending in `IPENDING`, but they are not deliverable until software explicitly reopens delivery.

## One-level Overwrite Rule

The following state is not preserved by hardware across a second trap or interrupt:

- Previous `EPCC`.
- Previous `CAUSE`.
- Previous `TVAL`.
- Previous `CAPCAUSE`.
- Previous `FAULTCAPIDX`.
- Previous `SR.PIE`.
- Previous `SR.PPRIV`.

If software permits another trap or interrupt before saving this state, the earlier trap context is lost from architectural hardware state.

Synchronous exceptions are not maskable by `SR.IE`. A synchronous exception taken while `SR.EXL=1` still uses the E07-S04 direct trap-entry update unless a later double-fault story defines a fatal policy for a narrower case. It overwrites the one hardware saved level.

Ordinary maskable interrupts follow E07-S05 and are deliverable only when:

```text
SR.IE = 1
SR.EXL = 0
(IPENDING & IENABLE & 0x7) != 0
```

## Software Trap Frame Requirement

Software must save a trap frame before enabling deeper nesting if it needs to resume the interrupted context.

The minimum software frame for a nestable handler contains:

| Field | Why it is required |
| --- | --- |
| `EPCC` payload and tag | Restores interrupted execution authority. |
| `EPCC.slot` | Restores slot-0 or slot-1 interrupted execution. |
| `SR.PIE` | Restores previous interrupt-enable state for `IRET`. |
| `SR.PPRIV` | Restores previous privilege for `IRET`. |
| `CAUSE` | Preserves the trap or interrupt cause. |
| `TVAL` | Preserves address or scalar trap value. |
| `CAPCAUSE` | Preserves capability-specific fault reason. |
| `FAULTCAPIDX` | Preserves capability operand reporting. |

The handler must also save any general integer registers, general capability registers, special capability registers, stack state, or platform interrupt-controller state required by its ABI and policy.

Plain `CCSRWR EPCC, Cs` is not sufficient to restore a general software trap frame because E02-S05 sets `EPCC.slot=0` for that instruction. A fully general v0.1 nested-trap implementation must preserve and restore `EPCC.slot` as architectural state.

E07-S06 therefore requires E04-S04 or the trap-return instruction story to provide a slot-aware trap-state restore path before nested trap return is considered complete. Until that concrete encoding is assigned, architectural models may represent it as:

```text
restore_epcc(payload, tag, slot)
```

where `slot` is the saved `EPCC.slot` value and must be either 0 or 1.

## Re-enable Protocol

Trap and interrupt entry never re-enable interrupts automatically.

After saving a software frame, a handler may explicitly reopen ordinary maskable interrupt delivery by a privileged `SR` write that sets:

```text
SR.PRIV = K
SR.EXL  = 0
SR.IE   = 1
```

The handler may also update `IENABLE`, `IPENDING`, `TIMECMP`, or platform interrupt-controller state before reopening delivery.

Setting only `SR.IE=1` is not enough while `SR.EXL=1`; E07-S05 still blocks ordinary maskable interrupt delivery when `SR.EXL=1`.

Clearing only `SR.EXL` is not enough when `SR.IE=0`.

This makes interrupt nesting an explicit software decision. Hardware does not infer nesting from pending sources, priority, privilege mode, or handler PC.

## Closing a Nested Window

Before restoring an outer software frame, software must close the nested interrupt window.

The normal sequence is:

1. Clear `SR.IE`, set `SR.EXL=1`, or both, with a privileged `SR` write.
2. Restore the saved `EPCC` payload, tag, and slot through the required slot-aware restore path.
3. Restore saved reporting CSRs if handler policy requires exact diagnostic state.
4. Restore saved `SR.PIE` and `SR.PPRIV`.
5. Execute `IRET`.

If software restores `EPCC` or saved reporting state while `SR.IE=1` and `SR.EXL=0`, a new interrupt may overwrite the hardware saved level before `IRET` executes.

## `IRET` State Restore Contract

E04-S04 owns the final instruction encoding, but v0.1 `IRET` must implement this architectural state restore.

`IRET` is privileged. If executed when `SR.PRIV != K`, it raises `PRIVILEGE_FAULT` and changes no architectural state.

Before committing, `IRET` checks that `EPCC` is a valid execution capability for the captured slot:

| Check | Failure |
| --- | --- |
| `EPCC.tag` is valid | Capability tag fault with `FAULTCAPIDX=EPCC`. |
| `EPCC` is unsealed | Capability seal/type fault with `FAULTCAPIDX=EPCC`. |
| `EPCC` has `EX` | Capability permission fault with `FAULTCAPIDX=EPCC`. |
| `EPCC.cursor` is inside `EPCC.bounds` | Capability bounds fault with `FAULTCAPIDX=EPCC`. |
| `EPCC.slot` is a valid captured architectural slot | `ALIGN_FAULT`. |

On success, `IRET` commits atomically:

```text
PCC.payload = EPCC.payload
PCC.tag     = EPCC.tag
PCC.slot    = EPCC.slot
SR.SLOT     = EPCC.slot

SR.IE       = SR.PIE
SR.PRIV     = SR.PPRIV
SR.EXL      = 0
```

`IRET` leaves `SR.PIE`, `SR.PPRIV`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX` unchanged unless E04-S04 later assigns narrower diagnostic cleanup behavior.

On fault, `IRET` commits none of the restore effects. The `IRET` fault is a synchronous exception and follows E07-S04. If it occurs while software has not saved the previous hardware trap level, it may overwrite that level like any other synchronous exception.

## Return Scenarios

### Return Without Nesting

A handler that does not enable nested interrupts can return by:

1. Clearing or acknowledging the interrupt source if needed.
2. Adjusting `EPCC` for resumable synchronous traps if policy requires it.
3. Executing `IRET`.

The `IRET` restores:

- `PCC` from `EPCC`.
- `SR.IE` from `SR.PIE`.
- `SR.PRIV` from `SR.PPRIV`.
- `SR.EXL=0`.

### Return From a Nested Handler

A nested interrupt handler returns to the interrupted outer handler by executing `IRET` using the nested hardware saved level.

For a normal nested interrupt delivered while the outer handler ran with `SR.PRIV=K`, `SR.IE=1`, and `SR.EXL=0`, nested `IRET` restores:

```text
SR.PRIV = K
SR.IE   = 1
SR.EXL  = 0
PCC     = outer handler continuation from EPCC
```

The outer handler then continues inside its explicitly opened nested window.

### Return From the Outer Handler

Before returning to the original interrupted context, the outer handler must restore the saved outer frame into the one hardware saved level, including `EPCC.slot`, then execute `IRET`.

If the original context was user mode with interrupts enabled, final `IRET` restores:

```text
SR.PRIV = U
SR.IE   = 1
SR.EXL  = 0
PCC     = original user continuation from restored EPCC
```

## Pending-source Interaction

Nested interrupt control is separate from source masking and acknowledgement.

Rules:

- `SR.IE=0` blocks ordinary maskable interrupt delivery regardless of `IENABLE` and `IPENDING`.
- `SR.EXL=1` blocks ordinary maskable interrupt delivery regardless of `IENABLE` and `IPENDING`.
- `IENABLE` masks individual interrupt sources but does not save trap state.
- `IPENDING` records pending source state but does not force nesting.
- `IRET` does not clear interrupt pending bits.

If a handler re-enables interrupts before clearing or masking the current source, the same source may be delivered again according to E07-S05 priority.

## Fault and Debug Interaction

Debug halt priority and debug-mode nesting are deferred to E12.

Synchronous faults inside handlers are precise. They use direct trap entry, update `EPCC`, reporting CSRs, `SR.PIE`, and `SR.PPRIV`, and may overwrite an unsaved hardware trap level.

Fatal trap-entry or interrupt-entry failure behavior remains defined by E07-S04 and E07-S05.

## Out of Scope for This Story

- Concrete `IRET` opcode and any slot-aware trap-state restore encoding: E04-S04.
- Debug halt, breakpoint, and single-step nesting policy: E12 stories.
- Platform interrupt-controller threshold and priority CSRs.
- Full trap-frame memory ABI layout.
- LL/SC reservation behavior across interrupts and context switches: E08-S02.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Trap entry copies exactly one level of `SR.IE` to `SR.PIE`.
- Trap entry copies exactly one level of `SR.PRIV` to `SR.PPRIV`.
- A second trap entry overwrites `EPCC`.
- A second trap entry overwrites `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX`.
- A second trap entry overwrites `SR.PIE` and `SR.PPRIV`.
- No ordinary maskable interrupt is delivered while `SR.EXL=1`.
- Setting `SR.IE=1` while leaving `SR.EXL=1` does not allow ordinary maskable interrupt delivery.
- Clearing `SR.EXL` while leaving `SR.IE=0` does not allow ordinary maskable interrupt delivery.
- Setting `SR.IE=1` and `SR.EXL=0` in kernel mode allows enabled pending maskable interrupts at the next precise boundary.
- `IRET` is privileged.
- `IRET` restores `SR.IE` from `SR.PIE`.
- `IRET` restores `SR.PRIV` from `SR.PPRIV`.
- `IRET` clears `SR.EXL`.
- `IRET` restores `PCC` payload, tag, and slot from `EPCC`.
- `IRET` restores `SR.SLOT` from `EPCC.slot`.
- Faulting `IRET` leaves `PCC`, `SR.IE`, `SR.PRIV`, and `SR.EXL` unchanged before the resulting synchronous trap entry.
- A nested interrupt handler can return to an outer handler with `SR.PRIV=K`, `SR.IE=1`, and `SR.EXL=0`.
- A fully general nested-trap software frame preserves and restores `EPCC.slot`.
- Re-enabling interrupts before clearing a level-sensitive source can redeliver the same source.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Hardware saves one level of `IE`, `PIE`, and previous privilege. | Met: the one hardware level is `SR.PIE` and `SR.PPRIV`, overwritten on each entry. |
| Deeper nesting requires software to save a trap frame. | Met. |
| Interrupts are re-enabled only by explicit software action. | Met: software must explicitly set `SR.IE=1` and `SR.EXL=0`. |
| `IRET` restores privilege and interrupt enable state. | Met: `IRET` restores `SR.PRIV` from `SR.PPRIV` and `SR.IE` from `SR.PIE`. |

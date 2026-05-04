# E07-S04: Direct Exception Trap Entry

Story: E07-S04

Status: Complete

Normative source: `design.md`, sections 10.2, 10.3, and 10.5

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E07-S03-precise-exception-model.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S03-extended-csr-space.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E11-S02-reset-capability-state.md`

## Decision

CPU v0.1 uses direct trap entry for synchronous exceptions.

Every synchronous exception enters one common exception target. The selected exception cause is reported through `CAUSE`, not by selecting a per-cause exception vector.

Maskable interrupts are not defined by this story. E07-S05 defines vectored interrupt target selection.

## Trap Entry Inputs

The precise exception model supplies a pending exception packet at exception retire.

The packet contains:

- Faulting `PCC` payload and tag.
- Faulting `PCC` hidden slot.
- Selected `CAUSE`.
- Selected `TVAL`.
- Selected `CAPCAUSE`.
- Selected `FAULTCAPIDX`.

For traps that do not have a relevant address or scalar value, the packet carries `TVAL=0`.

For non-capability traps, the packet carries:

```text
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

For capability-related traps, `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL` follow E03-S06, E04-S05, E05-S04, E06-S01, E06-S03, E06-S04, and E07-S02.

## Direct Exception Target

The direct exception target is:

```text
trap_pcc = TVC
trap_slot = 0
```

`TVC.cursor` is the cell address of the common synchronous exception entry point.

`TVEC` does not add an offset for synchronous exceptions in v0.1. Kernel software selects the direct exception entry by installing an appropriate `TVC.cursor`. E07-S05 owns the scalar `TVEC` fields used for vectored interrupts.

Direct exception entry does not depend on the exception `CAUSE` value for target selection.

## `TVC` Authorization

Trap entry installs `TVC` into `PCC` only if `TVC` is valid for executing the direct exception target.

Required `TVC` checks:

| Check | Diagnostic reason if delivery failure reporting is exposed |
| --- | --- |
| `TVC.tag` is valid | `FAULTCAPIDX=TVC`, `CAPCAUSE=TAG`. |
| `TVC` is unsealed | `FAULTCAPIDX=TVC`, `CAPCAUSE=SEAL_TYPE`. |
| `TVC` has `EX` | `FAULTCAPIDX=TVC`, `CAPCAUSE=PERMISSION`. |
| `TVC.cursor` is inside `TVC.bounds` | `FAULTCAPIDX=TVC`, `CAPCAUSE=BOUNDS`. |

On successful trap entry, the first handler fetch still uses the normal `PCC` execute-authority rules. For example, if the first handler instruction is a 48-bit instruction whose second cell is outside `TVC.bounds`, that later handler fetch raises a precise exception in kernel mode.

Trap entry always installs slot 0. There is no v0.1 direct exception path to a slot-1 handler target.

## Trap Entry State Update

Trap entry is one atomic architectural update.

Using the pre-trap values:

```text
old_ie   = SR.IE
old_priv = SR.PRIV
```

Successful synchronous exception trap entry commits:

```text
EPCC.payload    = pending.faulting_pcc_payload
EPCC.tag        = pending.faulting_pcc_tag
EPCC.slot       = pending.faulting_pcc_slot

CAUSE           = pending.CAUSE
TVAL            = pending.TVAL
CAPCAUSE        = pending.CAPCAUSE
FAULTCAPIDX     = pending.FAULTCAPIDX

SR.PIE          = old_ie
SR.IE           = 0
SR.PPRIV        = old_priv
SR.PRIV         = K
SR.EXL          = 1

PCC.payload     = TVC.payload
PCC.tag         = TVC.tag
PCC.slot        = 0
SR.SLOT         = 0
```

`SR.SLOT` is still a read-only mirror. It changes because trap entry installs a slot-0 `PCC`, not because software writes the `SR.SLOT` field.

Trap entry leaves `SR.Z`, `SR.N`, `SR.C`, and `SR.V` unchanged.

## Reporting CSR Values

`CAUSE` receives the selected E07-S02 cause value.

Synchronous exception `CAUSE` values use:

```text
CAUSE[47]    = 0
CAUSE[46:16] = 0
CAUSE[15:0]  = exception cause code
```

`TVAL` receives the selected trap value from the pending exception packet. All address values in `TVAL` are cell addresses.

`CAPCAUSE` and `FAULTCAPIDX` receive capability-specific values only for capability-related traps.

Required non-capability trap reporting:

```text
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

Required capability trap reporting examples:

| Trap source | `CAPCAUSE` | `FAULTCAPIDX` | `TVAL` |
| --- | --- | --- | --- |
| Fetch through invalid `PCC` | `TAG` | `PCC` | Attempted fetch cell. |
| Fetch outside `PCC.bounds` | `BOUNDS` | `PCC` | First out-of-bounds consumed cell. |
| `CLC` through an out-of-bounds source | `BOUNDS` | Authorizing capability source | Effective capability slot base. |
| `CSC` local-store failure | `LOCAL_STORE` | Destination authority | Effective capability slot base. |
| `CALL` return-stack overflow | `BOUNDS` | `RSC` | Attempted return-stack slot. |
| `RET` return-stack underflow from invalid slot tag | `TAG` | `RSC` | Return-stack slot. |

If the implementation cannot report a precise capability operand for a capability-related trap, it writes `FAULTCAPIDX=UNKNOWN`. It must not write an unassigned `FAULTCAPIDX` encoding.

## State Not Saved by Hardware

Trap entry does not create a memory trap frame.

Hardware does not automatically save:

- General integer registers.
- General capability registers.
- `DSC`.
- `RSC`.
- `DDC`.
- `KSC`.
- `KRC`.
- `SCRATCH`.
- Memory payload.
- Memory capability tags.

Hardware does not push to `DSC`, `KSC`, or `RSC`. It does not allocate store-buffer entries for trap entry.

`KSC` is preserved as kernel trap-stack authority. The trap handler may explicitly read or use `KSC` according to later ABI and instruction stories, but E07-S04 does not define an automatic stack switch.

Software owns the full trap frame. A handler that needs registers, stack state, nested-trap state, or user context must save it explicitly after entry.

## Atomicity and Visibility

Trap entry is not a normal retired instruction and does not increment `INSTRET`.

No observer may see a partially completed trap entry. In particular, hardware must not expose:

- `EPCC` updated without matching `CAUSE`.
- `CAUSE` updated without matching `EPCC`.
- `SR.PRIV=K` without the trap-target `PCC`.
- `PCC=TVC` without `SR.EXL=1`.
- Capability reporting CSRs from a different exception packet than `CAUSE`.

Younger instructions suppressed by the precise exception model must not commit before trap entry becomes visible.

Older retired stores may remain in the same-core store buffer at trap entry according to E07-S03 and E08-S03. Trap entry does not drain the store buffer.

## Trap Entry Failure

If `TVC` cannot authorize the direct exception target, the original synchronous exception cannot be delivered through the normal trap path.

This is a fatal trap-entry failure, not a second ordinary synchronous exception recursively delivered through the same invalid `TVC`.

Required behavior:

- The core must not continue executing the faulting context as if the trap had been delivered.
- The core must not fetch handler instructions through invalid or unauthorized `TVC`.
- The failure must be visible to platform debug, reset, or fatal-error machinery once those stories define the mechanism.

If an implementation exposes diagnostic reporting for the failed delivery, it should report the `TVC` delivery failure using:

```text
FAULTCAPIDX = TVC
TVAL        = TVC.cursor when representable, otherwise 0
CAPCAUSE    = TAG, SEAL_TYPE, PERMISSION, or BOUNDS
```

E12 debug stories may define whether a trap-entry failure enters debug halt. E11 stories define reset recovery behavior.

## Nested Trap Interaction

E07-S04 provides one hardware saved level.

Every successful trap entry overwrites:

- `EPCC`.
- `CAUSE`.
- `TVAL`.
- `CAPCAUSE`.
- `FAULTCAPIDX`.
- `SR.PIE`.
- `SR.PPRIV`.

If a synchronous exception occurs while `SR.EXL=1`, trap entry still follows the same update rule unless E07-S06 later defines a narrower double-fault or nested-trap policy. Software that wants to preserve the earlier trap context must save a software trap frame before executing code that can take another trap.

Ordinary maskable interrupt delivery while `SR.EXL=1` is disabled by E01-S06 unless E07-S05 and E07-S06 define an explicit software-managed re-enable sequence.

## Software Trap Frame Convention

The minimum hardware-provided trap frame consists only of:

- `EPCC`.
- `SR.PIE`.
- `SR.PPRIV`.
- `CAUSE`.
- `TVAL`.
- `CAPCAUSE`.
- `FAULTCAPIDX`.

The kernel trap handler is responsible for:

- Saving any live integer registers it needs.
- Saving any live general capability registers it needs.
- Saving `DSC`, `RSC`, `DDC`, `KSC`, `KRC`, or `TVC` if its policy requires it.
- Preserving the previous `EPCC` and reporting CSRs before enabling nested traps or interrupts.
- Advancing `EPCC` for recoverable traps such as `SYS`, `SCALL`, or `BRK` when policy chooses to resume after the trapping instruction.

E04-S04 defines `IRET` behavior. This story only defines entry state.

## Out of Scope for This Story

- Vectored interrupt target calculation and interrupt cause values: E07-S05.
- Nested interrupt software protocol beyond one hardware saved level: E07-S06.
- `IRET`, `SYS`, `SCALL`, `BRK`, `WFI`, and `PAUSE` instruction semantics: E04-S04.
- Debug halt entry, debug vectors, and trap-entry failure debug behavior: E12 stories.
- Full effective access priority with MMU/page faults: E09-S07.
- Concrete trap-frame ABI layout in memory.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- A synchronous exception enters the same `TVC.cursor` target regardless of `CAUSE`.
- Trap entry installs `PCC` from `TVC` and sets `PCC.slot=0`.
- Trap entry captures faulting `PCC.payload`, `PCC.tag`, and `PCC.slot` in `EPCC`.
- A faulting slot-1 instruction is captured with `EPCC.slot=1`.
- Trap entry writes `CAUSE` with the selected synchronous exception value.
- Trap entry writes `TVAL=0` when the selected trap has no trap value.
- Trap entry writes `CAPCAUSE=NONE` and `FAULTCAPIDX=NONE` for non-capability traps.
- Capability traps write the selected `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL`.
- Trap entry copies `SR.IE` to `SR.PIE`.
- Trap entry clears `SR.IE`.
- Trap entry copies `SR.PRIV` to `SR.PPRIV`.
- Trap entry sets `SR.PRIV=K`.
- Trap entry sets `SR.EXL=1`.
- Trap entry leaves condition flags unchanged.
- Trap entry does not modify general integer registers.
- Trap entry does not modify general capability registers.
- Trap entry does not push to memory, `DSC`, `KSC`, or `RSC`.
- Trap entry through invalid, sealed, non-executable, or out-of-bounds `TVC` does not fetch handler code and enters fatal trap-entry failure.
- Repeated trap entry while `SR.EXL=1` overwrites the one hardware saved level unless software saved it first.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Exceptions use direct trap entry. | Met. |
| Hardware saves `EPCC`. | Met. |
| `SR.IE` is copied to `SR.PIE`. | Met. |
| Current privilege is copied to previous privilege state. | Met: `SR.PRIV` is copied to `SR.PPRIV`. |
| `CAUSE`, `TVAL`, and `CAPCAUSE` are populated where applicable. | Met. |
| Hardware does not auto-save all GPRs. | Met: no general integer or capability register save is performed. |

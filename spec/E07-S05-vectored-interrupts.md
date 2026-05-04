# E07-S05: Vectored Interrupts

Story: E07-S05

Status: Complete

Normative source: `design.md`, sections 10.3, 10.4, and 10.5

Prerequisites:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E07-S04-trap-entry.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S03-extended-csr-space.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`

## Decision

CPU v0.1 uses vectored entry for ordinary maskable interrupts.

Synchronous exceptions remain direct and use E07-S04. Interrupts use the same trap-entry save state as synchronous exceptions, but select a per-source vector target.

The mandatory v0.1 interrupt sources are:

- Per-core timer interrupt.
- Per-core software IPI interrupt.
- Per-core external interrupt line from a platform interrupt controller.

## Interrupt Cause Encoding

Interrupt `CAUSE` values use bit 47 to distinguish interrupts from synchronous exceptions:

```text
CAUSE[47]    = 1
CAUSE[46:16] = 0
CAUSE[15:0]  = interrupt cause code
```

Mandatory interrupt causes:

| Interrupt source | Cause code | `CAUSE` value | `IPENDING` bit | Vector index |
| --- | ---: | ---: | ---: | ---: |
| `TIMER_INTERRUPT` | `0x0001` | `0x800000000001` | 0 | 1 |
| `SOFTWARE_IPI_INTERRUPT` | `0x0002` | `0x800000000002` | 1 | 2 |
| `EXTERNAL_INTERRUPT` | `0x0003` | `0x800000000003` | 2 | 3 |

Interrupt cause codes `0x0004-0x00FF` are reserved for future mandatory architectural interrupt sources.

Interrupt entry always writes:

```text
TVAL        = 0
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

An interrupt is not a capability-related trap, even if interrupt delivery later fails because `TVC` is invalid. Trap-entry delivery failures are fatal platform/debug conditions, not normally delivered interrupt causes.

## Interrupt Source CSRs

`IENABLE` and `IPENDING` use the same low-bit source layout.

| Bit | Name | `IENABLE` access | `IPENDING` access | Meaning |
| ---: | --- | --- | --- | --- |
| 0 | `TIMER` | RW | RO, level-derived | Per-core timer comparison source. |
| 1 | `SOFTWARE_IPI` | RW | RW, latched | Per-core software IPI source. |
| 2 | `EXTERNAL` | RW | RO, platform-derived | Per-core external interrupt source. |
| 47:3 | `RES0` | RZ/W0 | RZ/W0 | Reserved for future sources. |

`IENABLE` reset value is zero, so no maskable interrupt source is enabled after reset.

`IPENDING` reset value is zero except for sources that become pending immediately because of their level condition. With the mandatory reset values `TIMER=0` and `TIMECMP=0xFFFFFFFFFFFF`, the timer source is not pending at reset.

Kernel writes to `IENABLE` may set or clear bits 0-2. Writes that set reserved bits 47:3 to one raise `ILLEGAL_CSR_WRITE`.

Kernel writes to `IPENDING`:

- May set or clear bit 1, the software IPI pending latch.
- Must not attempt to change read-only timer or external pending bits.
- Must write zero to reserved bits 47:3.

CSR read-modify-write instructions follow E02-S04. Hardware source updates and CSR writes to `IPENDING` must serialize so software observes one complete order.

## Timer Interrupt Source

The timer interrupt is pending when:

```text
unsigned(TIMER) >= unsigned(TIMECMP)
```

Both operands are the current 48-bit CSR values interpreted as unsigned integers.

The timer pending bit is level-derived. It remains pending while the comparison is true. Software clears the timer interrupt condition by writing `TIMECMP` to a value that makes the comparison false or by clearing `IENABLE.TIMER`.

Writing `IPENDING.TIMER` does not clear the timer source.

`TIMER` wrap behavior is the modulo-`2^48` counter behavior from E02-S02. The comparison above is evaluated on the current wrapped 48-bit values. Portable timer software should program `TIMECMP` before the intended deadline crosses a wrap boundary.

## Software IPI Source

The software IPI interrupt is a per-core latched pending bit.

The latch can be set by:

- A kernel write to `IPENDING.SOFTWARE_IPI` on the local core.
- A platform IPI or start-event mechanism targeting this core, defined by E11-S03 or platform interrupt-controller stories.

The latch is cleared by a kernel write that clears `IPENDING.SOFTWARE_IPI`.

Software IPI delivery does not automatically clear the latch. The handler must clear it or mask the source before returning if it does not want immediate redelivery.

## External Interrupt Source

The external interrupt source is provided by a platform interrupt controller.

In the mandatory CPU-core architecture, `IPENDING.EXTERNAL` is a read-only per-core input. It is pending when the platform interrupt controller asserts external interrupt delivery for this core.

External interrupt claim, completion, subpriority, device identity, and controller-specific thresholding are not part of the mandatory fast CSR set. They are reserved for platform interrupt-controller CSRs in the `0x80-0xBF` extended range and platform profiles.

Writing `IPENDING.EXTERNAL` does not clear the external source. Software clears or acknowledges external interrupts through the platform interrupt controller or by clearing the underlying device condition.

## Delivery Eligibility

At an instruction boundary, a maskable interrupt is deliverable when all of these are true:

```text
SR.IE = 1
SR.EXL = 0
(IPENDING & IENABLE & 0x7) != 0
```

`SR.PRIV` does not suppress delivery. Both user and kernel code may be interrupted when `SR.IE=1` and `SR.EXL=0`.

Synchronous exceptions take priority over ordinary maskable interrupts. If the oldest instruction at the retirement point has a synchronous exception, hardware delivers the synchronous exception through E07-S04 instead of delivering a maskable interrupt.

Interrupt delivery occurs only at a precise instruction boundary:

- Older instructions have committed.
- The interrupted instruction has not committed.
- Multi-effect instructions such as `CALL`, `RET`, `CSRSET`, `CSRCLR`, `CLC`, `CSC`, and `ST48` are not split.
- Younger fetched, decoded, or internally completed work is killed or replayed as required by E07-S03.

## Source Priority

If multiple enabled sources are pending at the same delivery point, hardware selects one source using this fixed priority:

| Priority | Source | Cause | Vector index |
| ---: | --- | --- | ---: |
| 1 | External interrupt | `EXTERNAL_INTERRUPT` | 3 |
| 2 | Software IPI | `SOFTWARE_IPI_INTERRUPT` | 2 |
| 3 | Timer interrupt | `TIMER_INTERRUPT` | 1 |

Lower priority number means higher priority.

This fixed priority applies after any platform interrupt-controller logic has reduced device-specific external interrupt state to the core's single external pending input.

## Priority Thresholds

There is no mandatory architectural priority-threshold CSR in the v0.1 fast CSR set.

The mandatory core-level threshold is therefore effectively disabled: any enabled pending mandatory source is eligible for delivery according to the fixed priority table.

Fine-grained thresholding is explicitly deferred to platform interrupt-controller CSRs and future interrupt profiles. A platform controller may filter which external interrupt reaches `IPENDING.EXTERNAL`, but it must not change the mandatory ordering between the three core-level sources once they are pending and enabled.

## `TVEC` Layout

`TVEC` controls interrupt vector spacing. It does not affect direct synchronous exception target selection.

| Bits | Name | Access | Meaning |
| ---: | --- | --- | --- |
| 3:0 | `VSHIFT` | WARL | Interrupt vector stride is `4 << VSHIFT` cells. |
| 47:4 | `RES0` | RZ/W0 | Reserved. |

`TVEC=0` after reset means `VSHIFT=0` and a 4-cell interrupt vector stride.

Implementations must support `VSHIFT=0`. They may support larger legal strides. Unsupported `VSHIFT` values are legalized according to WARL behavior or fault according to the CSR write rules selected by the implementation profile.

The vector stride is always a multiple of 4 cells, so every mandatory vector target enters at slot 0 and is naturally aligned for 48-bit handler prologues if software chooses to place them there.

## Interrupt Vector Target

The per-core vector base is `TVC.cursor`.

For a selected interrupt source:

```text
stride_cells = 4 << TVEC.VSHIFT
vector_cell  = TVC.cursor + vector_index * stride_cells
interrupt_pcc = TVC with cursor = vector_cell
interrupt_slot = 0
```

Vector index 0 is reserved for the direct synchronous exception entry at `TVC.cursor` from E07-S04. Mandatory interrupt vector indexes begin at 1.

Required `TVC` and target checks before interrupt entry commits:

| Check | Diagnostic reason if delivery failure reporting is exposed |
| --- | --- |
| `TVC.tag` is valid | `FAULTCAPIDX=TVC`, `CAPCAUSE=TAG`. |
| `TVC` is unsealed | `FAULTCAPIDX=TVC`, `CAPCAUSE=SEAL_TYPE`. |
| `TVC` has `EX` | `FAULTCAPIDX=TVC`, `CAPCAUSE=PERMISSION`. |
| `vector_cell` is representable as a 48-bit cell address | `FAULTCAPIDX=TVC`, `CAPCAUSE=BOUNDS`. |
| `vector_cell` is inside `TVC.bounds` | `FAULTCAPIDX=TVC`, `CAPCAUSE=BOUNDS`. |

The first instruction fetch at the vector target still follows E06-S01. If the handler instruction consumes additional cells outside `TVC.bounds`, that later handler fetch raises a precise exception in kernel mode.

Interrupt vectoring does not modify `TVC`.

## Interrupt Entry State Update

Interrupt entry is one atomic architectural update.

Using the pre-interrupt boundary values:

```text
old_ie   = SR.IE
old_priv = SR.PRIV
```

Successful interrupt entry commits:

```text
EPCC.payload    = interrupted_pcc_payload
EPCC.tag        = interrupted_pcc_tag
EPCC.slot       = interrupted_pcc_slot

CAUSE           = selected_interrupt_cause
TVAL            = 0
CAPCAUSE        = NONE
FAULTCAPIDX     = NONE

SR.PIE          = old_ie
SR.IE           = 0
SR.PPRIV        = old_priv
SR.PRIV         = K
SR.EXL          = 1

PCC.payload     = interrupt_pcc.payload
PCC.tag         = interrupt_pcc.tag
PCC.slot        = 0
SR.SLOT         = 0
```

The interrupted `PCC` is the architectural next instruction location at the delivery boundary. For example, if an interrupt is delivered after a 12-bit slot-0 instruction normally retires, `EPCC.slot=1` because slot 1 is the next instruction location.

Interrupt entry leaves `SR.Z`, `SR.N`, `SR.C`, and `SR.V` unchanged.

Interrupt entry does not increment `INSTRET`.

Interrupt entry does not clear the selected source pending bit. The handler is responsible for clearing or masking the source through `TIMECMP`, `IPENDING.SOFTWARE_IPI`, or the platform interrupt controller.

## State Not Saved by Hardware

Interrupt entry uses the same minimal hardware save model as E07-S04.

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

Hardware does not push to `DSC`, `KSC`, or `RSC`. It does not allocate store-buffer entries for interrupt entry.

Software owns the full interrupt frame.

## Interrupt Entry Failure

If `TVC`, `TVEC`, or the selected vector target cannot authorize interrupt entry, the interrupt cannot be delivered through the normal vector path.

This is a fatal interrupt-entry failure. It is not converted into a normal synchronous exception through the same invalid vector state.

Required behavior:

- The core must not fetch handler instructions through invalid or unauthorized `TVC`.
- The core must not silently resume the interrupted context as if the interrupt had been handled.
- The selected pending interrupt source is not automatically cleared by the failed delivery.
- The failure must be visible to platform debug, reset, or fatal-error machinery once those stories define the mechanism.

If an implementation exposes diagnostic reporting for the failed delivery, it should report:

```text
FAULTCAPIDX = TVC
TVAL        = vector_cell when representable, otherwise 0
CAPCAUSE    = TAG, SEAL_TYPE, PERMISSION, or BOUNDS
```

## Out of Scope for This Story

- Full nested interrupt software protocol and re-enable rules: E07-S06.
- `IRET`, `WFI`, and interrupt-aware control-transfer instruction semantics: E04-S04.
- Remote IPI send mailbox and secondary-core startup protocol: E11-S03.
- Platform interrupt-controller claim, complete, threshold, MSI, and device-priority interfaces.
- Debug halt priority relative to interrupt delivery: E12 stories.
- Counter behavior while halted or in handlers: E12-S04 and E12-S05.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CAUSE[47]=1` for timer, software IPI, and external interrupt entry.
- Timer interrupt writes `CAUSE=0x800000000001`.
- Software IPI writes `CAUSE=0x800000000002`.
- External interrupt writes `CAUSE=0x800000000003`.
- Interrupt entry writes `TVAL=0`, `CAPCAUSE=NONE`, and `FAULTCAPIDX=NONE`.
- `IPENDING.TIMER` reads pending when `TIMER >= TIMECMP`.
- Writing `TIMECMP` to a future value clears timer pending.
- `IPENDING.SOFTWARE_IPI` can be set and cleared by kernel software.
- `IPENDING.EXTERNAL` reflects the platform external pending input.
- `IENABLE` masks each mandatory interrupt source.
- No interrupt is delivered when `SR.IE=0`.
- No ordinary maskable interrupt is delivered when `SR.EXL=1`.
- A synchronous exception at the same retirement point takes priority over an interrupt.
- With all three sources pending and enabled, external interrupt is selected first.
- With timer and software IPI pending and enabled, software IPI is selected first.
- `TVEC=0` produces a 4-cell vector stride.
- Timer vector target is `TVC.cursor + 4` when `TVEC=0`.
- Software IPI vector target is `TVC.cursor + 8` when `TVEC=0`.
- External vector target is `TVC.cursor + 12` when `TVEC=0`.
- Interrupt entry captures the interrupted next `PCC` and slot in `EPCC`.
- Interrupt entry installs slot-0 `PCC` at the selected vector target.
- Interrupt entry copies `SR.IE` to `SR.PIE`, clears `SR.IE`, copies `SR.PRIV` to `SR.PPRIV`, sets `SR.PRIV=K`, and sets `SR.EXL=1`.
- Interrupt entry leaves condition flags and general registers unchanged.
- Invalid or out-of-bounds interrupt vector state enters fatal interrupt-entry failure rather than fetching handler code.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Interrupts use a vectored trap model. | Met. |
| Per-core trap vector base is defined. | Met: `TVC.cursor` is the per-core vector base. |
| Timer, software IPI, and external interrupt causes are defined. | Met. |
| Interrupt priority and threshold behavior is specified or explicitly deferred. | Met: fixed core-source priority is specified; threshold CSRs are deferred to platform interrupt-controller stories. |

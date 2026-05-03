# E01-S05: PC Subslot Behavior

Story: E01-S05

Status: Complete

Normative source: `design.md`, section 3.4

## Decision

`PCC` and `EPCC` carry a hidden slot bit because the architecture is cell-addressed but allows 12-bit instructions inside a 24-bit cell.

Slot meanings:

- Slot 0: first 12-bit half of a 24-bit cell.
- Slot 1: second 12-bit half of a 24-bit cell.

Slot 1 is not a general branch target. It is reachable only by sequential fall-through from a 12-bit instruction in slot 0.

## Instruction Start Rules

| Instruction size | Legal start slot | Notes |
| ---: | --- | --- |
| 12-bit | Slot 0 or slot 1 | Two 12-bit instructions may share one cell. |
| 24-bit | Slot 0 only | Occupies one full cell. |
| 48-bit | Slot 0 only | Must begin at the first cell of a 48-bit fetch group. |

No instruction may cross a 48-bit fetch-group boundary.

## Sequential Fall-through

| Current instruction | Next sequential PC |
| --- | --- |
| 12-bit at slot 0 | Same cell, slot 1 |
| 12-bit at slot 1 | Next cell, slot 0 |
| 24-bit at slot 0 | Next cell, slot 0 |
| 48-bit at fetch-group slot 0 | Next fetch group, slot 0 |

## Explicit Control Transfers

Explicit control transfers enter only at slot 0:

- Direct branches
- Indirect jumps
- Calls
- Returns
- Trap entry
- Interrupt entry

`IRET` restores the slot captured in `EPCC`. That slot must have been produced by a valid retired or faulting instruction stream.

## Fault Rules

| Invalid case | Exception |
| --- | --- |
| Start 24-bit instruction at slot 1 | `ALIGN_FAULT` |
| Start 48-bit instruction at slot 1 | `ALIGN_FAULT` |
| Start 48-bit instruction at the second cell of a fetch group | `ALIGN_FAULT` |
| Explicit branch/call/jump/return target has slot 1 | `ALIGN_FAULT` |
| Trap vector target has slot 1 | `ALIGN_FAULT` |

The exception is named as `ALIGN_FAULT` because the invalid slot is a control-flow alignment violation in a cell-addressed architecture.

## Encoding Implications

Assemblers and encoders should treat slot 1 as a packing location for sequential 12-bit instructions only.

Practical rules:

- A 12-bit branch at slot 0 may fall through to slot 1 when not taken.
- A taken 12-bit branch targets slot 0.
- A 12-bit call at slot 0 returns to a slot-0 continuation, not to slot 1.
- Assemblers should avoid placing unrelated reachable code in slot 1 after unconditional control-transfer instructions.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Decode two packed 12-bit instructions in one cell.
- Fall through from slot 0 to slot 1 after a 12-bit instruction.
- Fall through from slot 1 to the next cell slot 0 after a 12-bit instruction.
- Reject a 24-bit instruction start at slot 1 with `ALIGN_FAULT`.
- Reject a 48-bit instruction start at slot 1 with `ALIGN_FAULT`.
- Reject direct or indirect explicit slot-1 targets with `ALIGN_FAULT`.
- Capture `EPCC` with the correct slot for exceptions raised by a slot-1 instruction.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `PCC` and `EPCC` carry a hidden slot bit. | Met. |
| Slot 0 and slot 1 are defined. | Met. |
| Branches, calls, returns, and trap targets enter at slot 0. | Met. |
| Slot 1 is reachable only by fall-through after a 12-bit instruction. | Met. |
| Illegal slot targets raise a named exception. | Met: `ALIGN_FAULT`. |


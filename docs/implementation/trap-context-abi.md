# Trap Frame and Context-Switch ABI

Story: I09-S01

This supplement fixes the first OS/runtime ABI layout used by conformance tests. It does not change trap hardware: v0.1 still has one hardware saved level, and software must save a frame before enabling deeper nesting.

## Minimum Nested Trap Frame

The minimum nestable software frame is 16 cells and 4-cell aligned.

| Field | Offset | Cells | Purpose |
| --- | ---: | ---: | --- |
| `EPCC` | 0 | 4 | Captured execution capability payload and tag. |
| `EPCC_SLOT` | 4 | 2 | Hidden slot saved by `EPCCRD` and restored by `EPCCWR`. |
| `SR` | 6 | 2 | Saved status word, including `PIE` and `PPRIV`. |
| `CAUSE` | 8 | 2 | Trap or interrupt cause. |
| `TVAL` | 10 | 2 | Trap value. |
| `CAPCAUSE` | 12 | 2 | Capability-specific fault reason. |
| `FAULTCAPIDX` | 14 | 2 | Capability operand index. |

Plain `CCSRWR EPCC, Cs` is not a valid general frame restore because it resets `EPCC.slot` to 0. A nestable restore uses `EPCCWR Cs, Ds`, restores policy-selected reporting CSRs and `SR.PIE`/`SR.PPRIV`, then executes `IRET`.

## Context Switch Save Set

A full kernel context switch saves:

- `D0-D15`.
- `C0-C7`, including payloads and tags.
- Every special capability register: `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC`.

The normal function-call ABI remains unchanged: `D0-D11` and `C0-C5` are caller-saved, while `D12-D15` and `C6-C7` are callee-saved.

## Required Return Scenarios

Conformance and OS bring-up should cover:

- slot-0 `IRET` restore;
- slot-1 `IRET` restore;
- nested frame restore preserving `EPCC.slot`;
- faulting `IRET` with no partial restore.

# Minimal Kernel Handlers

Story: I14-S02

Status: Draft executable fixtures

Owner sources:

- I14-S01 installs the tiny ROM handoff capabilities.
- I09-S01 defines the minimum trap-frame ABI.
- I09-S03 defines syscall arguments and returns.
- E07-S05 defines timer interrupt vectoring.
- E07-S06 defines slot-aware `IRET` return state.

## Scope

The I14-S02 fixtures add the first executable kernel-side examples on top of the
tiny ROM handoff. They are Python-level simulator fixtures, not a final ROM
binary or operating-system kernel.

The fixtures cover:

- saving the minimum software trap frame from `EPCC`, `SR`, `CAUSE`, `TVAL`,
  `CAPCAUSE`, and `FAULTCAPIDX`;
- reading syscall arguments from `D0-D5` and `C0-C3`;
- returning syscall values in `D0-D1`;
- selecting and delivering the timer interrupt vector from `TVC + 4` when
  `TVEC=0`;
- programming the next `TIMECMP` value in the timer handler;
- returning through the existing architectural `IRET` implementation.

## Trap Frames

The software frame mirrors `docs/implementation/trap-context-abi.md`. A handler
may restore the saved frame, including the hidden `EPCC.slot`, before executing
`IRET`. The fixture uses simulator state helpers for the frame restore while the
final control transfer itself runs through `control_ops.execute_control("IRET")`
and the normal retire commit path.

## Interrupts

The interrupt fixture implements the mandatory low interrupt bits:

- timer: bit 0, cause `0x800000000001`, vector index 1;
- software IPI: bit 1, cause `0x800000000002`, vector index 2;
- external: bit 2, cause `0x800000000003`, vector index 3.

Delivery requires `SR.IE=1`, `SR.EXL=0`, and an enabled pending source. The
fixed priority order is external, software IPI, timer. The timer pending bit is
level-derived from `TIMER >= TIMECMP`.

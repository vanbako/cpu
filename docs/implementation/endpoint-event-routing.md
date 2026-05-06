# Endpoint Event Routing

Story: I19-S02

Status: Draft executable fixture

## Scope

This story adds the first CPU-side endpoint event routing fixture above the
external fabric boundary profile. It proves the interrupt-visible behavior that
a future point-to-point fabric adapter must drive, while leaving link training,
packet formats, switch routing, enumeration, and device programming outside
this repository.

The fixture reuses:

- the firmware secondary-core startup demo;
- the existing mandatory interrupt source model;
- `TVC` vector delivery and software trap frames;
- `IRET` return to the interrupted boot or secondary core context.

## Routed Sources

The CPU-visible routing controller can mark an endpoint event pending through
named ingress points: left peer, right peer, fabric 0, and fabric 1. Those names
are logical ingress identifiers, not address windows. A pending endpoint event
drives the existing external interrupt source for the target core.

The executable fixture arms all three mandatory interrupt sources for the boot
core and one firmware-started secondary core:

- external endpoint event;
- software IPI;
- timer level interrupt.

With all three pending and enabled, each core observes the architectural
priority order: external, software IPI, then timer.

## Acknowledgement

Acknowledgement is modeled at the CPU boundary:

- external endpoint acknowledgement removes one pending endpoint event for the
  target core;
- software IPI acknowledgement clears the target core's `IPENDING` IPI bit;
- timer acknowledgement moves `TIMECMP` past the current `TIMER` value.

After each acknowledgement, the fixture restores the saved trap frame and
returns through `IRET`. The final state has no selected interrupt source for
either tested core.

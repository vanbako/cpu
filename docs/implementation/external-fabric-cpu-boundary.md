# External Fabric CPU Boundary

Story: I19-S01

Status: Planned implementation profile

## Scope

This document is the CPU-repository boundary for future external modules. It
does not define the full computer architecture, package topology, link protocol,
switch fabric, discovery format, routing policy, or device programming model.
Those belong in a separate computer-architecture repository.

The CPU implementation only needs stable CPU-visible contracts:

- how external endpoint control/status windows appear to privileged software;
- how endpoint or fabric events become external interrupts or start events;
- how noncoherent external agents read or write memory;
- how cache maintenance, fences, and page memory types compose with those
  external accesses;
- how capability tags are protected when external agents are not tag-aware;
- how link, endpoint, and fabric faults map into existing CPU-visible fault or
  interrupt reporting.

## Current CPU Contract

CPU v0.1 already has abstract device and external-agent concepts:

- `DEVICE_ORDERED` memory for ordered side-effecting accesses;
- external interrupt pending/enable/cause bits;
- software IPI and secondary-core start-event hooks;
- noncoherent, tag-unaware external memory overwrite behavior;
- cache-maintenance and fence sequences for external-agent ownership handoff.

Those rules are intentionally not a bus definition. In this implementation
repo, "external agent" is the generic CPU-side model for a device, accelerator,
storage controller, fabric endpoint, or another module that can interact with
CPU-visible memory or interrupt state.

## CPU-Side Implementation Shape

I19-S01 should keep the simulator model topology-neutral:

- endpoint windows are named platform regions, not physical bus addresses;
- event ingress is modeled as external interrupt or platform start-event state;
- external memory transfers use the existing noncoherent external-agent path;
- capability tags are never accepted from ordinary endpoint payload writes;
- endpoint errors map to `ACCESS_FAULT`, external interrupt state, or a
  documented fatal platform event depending on the operation boundary.

The first fixtures should avoid requiring PCIe, AXI, a shared bus, or a
particular switch. They should only prove that the CPU-visible memory, tag,
cache, fence, interrupt, and startup semantics are ready for a later fabric.

## Separate Computer-Architecture Repo Seed

A separate repo can define a PCIe-like point-to-point module fabric with:

- modules as endpoints: CPU, GPU, NPU, NVMe, memory controllers, and fabric
  switches;
- four physical/logical links per module: left peer, right peer, fabric 0, and
  fabric 1;
- packetized transactions rather than a shared bus;
- link training, credit/flow control, retry, ordering classes, and link reset;
- switch routing, discovery, enumeration, address/window assignment, and
  endpoint identity;
- message delivery for interrupts, IPIs, starts, completions, and errors;
- explicit rules for coherent, noncoherent, and tag-aware future extensions;
- security policy for which endpoints may initiate memory reads/writes.

The CPU repo should consume that future architecture through a small adapter
profile: endpoint windows, event lines/messages, external-agent memory
transfers, and error reporting. It should not own the full fabric design.

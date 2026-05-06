# External-Agent Transfers

Story: I19-S03

Status: Draft executable fixture

## Scope

This story makes the CPU-side noncoherent external-agent transfer rules
executable. It does not define a bus, packet protocol, switch fabric, endpoint
enumeration, or a DMA programming interface. Those belong with the separate
computer architecture and fabric work.

The fixture models a tag-unaware external agent that can read and write
ordinary payload cells in CPU-visible memory. It cannot create capability tags.
The CPU driver owns the cache-line ownership handoff sequence.

## Ownership Handoff

For a `NORMAL_COHERENT` buffer handed from CPU to external agent, the fixture
requires:

- CPU writes the buffer;
- `FENCE`;
- `CACHE.CLEAN` over the whole owned cache line;
- `FENCE`;
- ownership moves to the external agent.

For a `NORMAL_COHERENT` buffer handed from external agent back to CPU, the
fixture requires:

- external agent writes backing memory;
- `FENCE` after completion observation;
- `CACHE.INVAL` over the whole owned cache line;
- `FENCE`;
- ownership moves back to the CPU.

Without the invalidation, a CPU cache can still observe the stale payload and
stale tag. After invalidation, the CPU observes the external-agent payload with
an invalid capability tag.

## Memory Types

`NORMAL_COHERENT` payload buffers require cache maintenance on ownership
handoff. `NORMAL_UNCACHEABLE` payload buffers are observed directly after the
completion fence and do not require cache maintenance. `DEVICE_ORDERED` regions
are endpoint control/status windows, not external-agent payload buffers;
`CACHE.CLEAN` over such a mapping raises the existing access fault.

The fixture keeps ownership at cache-line granularity. Sharing CPU-owned data in
the same cache line as an external-agent-owned subrange is outside the accepted
profile until a later driver protocol adds explicit line sharing rules.

## Tag Rules

External-agent payload writes clear every overlapped capability-slot tag.
Cache maintenance and invalidation do not restore cleared tags. A future
tag-aware fabric extension would need a separate trusted profile; this fixture
only accepts tag-unaware external-agent writes.

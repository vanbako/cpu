# E10-S01: Cache Hierarchy

Story: E10-S01

Status: Complete

Normative source: `design.md`, section 13

## Decision

CPU v0.1 uses private per-core L1 caches and a shared inclusive L2 cache.

| Level | Scope | Role |
| --- | --- | --- |
| L1 I-cache | Private per core | Instruction fetch |
| L1 D-cache | Private per core | Data and capability memory access |
| L2 cache | Shared by all cores | Inclusive CPU coherence point |

## Hierarchy Rules

- Each core has a private L1 instruction cache.
- Each core has a private L1 data cache.
- All cores share one inclusive L2 cache.
- Every valid L1 line has a corresponding L2 line or L2 directory entry.
- L2 owns cross-core ownership, invalidation, and visibility ordering.
- Memory below L2 is not the CPU coherence point.

## L1 Instruction Cache

The L1 instruction cache:

- Is private to one core.
- Is filled through L2.
- Serves instruction fetch only.
- Does not receive data-side stores.
- Is synchronized with data writes through `FENCE.I`.

Instruction fetch is still capability-authorized by `PCC`. The I-cache is a storage and latency optimization, not an authority bypass.

## L1 Data Cache

The L1 data cache:

- Is private to one core.
- Is write-back.
- Is write-allocate.
- Is filled through L2.
- Writes dirty lines back through L2.
- Holds ordinary data, capability payload bits, and associated capability tag state.

Data and capability loads/stores are still capability-authorized before commit. The D-cache is a storage and latency optimization, not an authority bypass.

## Shared Inclusive L2

The L2 cache:

- Is shared by all cores.
- Is inclusive of valid L1 contents.
- Is the CPU coherence point.
- Mediates cross-core visibility.
- Tracks ownership and invalidation for dirty data.
- Carries enough tag state or tag-directory information to preserve capability-tag visibility.

The exact MESI-like state machine is deferred to E10-S03. The tag movement details are prototyped in E14-S04 and finalized in E03-S04/E10-S03.

## Out of Scope for This Story

- Exact cache line size and index fields: E10-S02.
- MESI-like coherence state machine: E10-S03.
- Noncoherent DMA policy: E10-S04.
- Cache maintenance instruction behavior: E10-S05.
- Memory ordering contract: E08-S03.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Each core can independently fill L1 I-cache lines.
- Each core can independently fill L1 D-cache lines.
- L1 D-cache write hit marks line dirty.
- L1 D-cache write miss allocates the line.
- Dirty L1 D-cache eviction writes back through L2.
- L1 instruction fetch fills through L2, not through L1 D-cache.
- L1 data load/store fills through L2, not through L1 I-cache.
- L2 can identify which L1s may hold a line.
- Capability tag state is not lost when data moves through L1 and L2.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Each core has private L1 instruction cache. | Met. |
| Each core has private L1 data cache. | Met. |
| Cores share an inclusive L2 cache. | Met. |
| L1 data cache is write-back and write-allocate. | Met. |
| L2 is the coherence point. | Met. |


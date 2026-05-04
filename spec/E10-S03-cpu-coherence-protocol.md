# E10-S03: CPU Coherence Protocol

Story: E10-S03

Status: Complete

Normative source: `design.md`, section 13

Prerequisites:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E10-S01-cache-hierarchy.md`

Related sources:

- `spec/E10-S02-cache-line-size.md`
- `spikes/E14-S04-capability-tag-cache-model.md`

## Decision

CPU v0.1 uses a MESI-like CPU coherence protocol for normal coherent cacheable memory.

The coherent data hierarchy is:

- Private L1 data caches per core.
- A shared inclusive L2 cache.
- L2 as the CPU coherence point and directory.

The coherence granule is one cache line. In v0.1, one cache line is 16 cells and contains four capability tag bits.

Instruction caches fill through L2 but are not data-side coherent with stores. Instruction-fetch synchronization is handled by `FENCE.I`, defined by E08-S04.

## Coherent Line Contents

A coherent cache line contains:

- 16 architectural cells.
- 4 capability tag bits, one per naturally aligned 4-cell capability slot.
- Coherence state.
- Dirty/owner/sharer metadata as required by the level.

Payload cells and tag bits move together for all coherent line transfers, invalidations, ownership changes, fills, and writebacks.

No coherence path may transfer payload without the associated tag state, or tag state without the associated payload.

## L1 Data Cache States

L1 data caches use MESI-like states:

| State | Meaning |
| --- | --- |
| `I` | Invalid. The L1 has no usable copy. |
| `S` | Shared clean. Other L1s may also hold clean copies. Stores require an upgrade. |
| `E` | Exclusive clean. This L1 is the only data-cache holder and may silently transition to `M` on store. |
| `M` | Modified exclusive. This L1 owns the dirty line. Other data-cache L1s do not hold valid copies. |

An implementation may collapse `E` into `S` for simplicity if it still obtains exclusive ownership before store visibility. Architecturally, the visible behavior must match the rules in this story.

## L2 Directory State

The shared L2 records enough directory state to preserve inclusion and enforce ownership:

| L2 state | Meaning |
| --- | --- |
| `I` | Line not present in L2 and not present in any L1. |
| `S` | Line is clean in L2 and may be shared by one or more L1s. |
| `E` | Line is clean and held exclusively by one L1, or clean in L2 with no L1 sharers. |
| `M` | One L1 data cache owns the dirty line. L2 records the owner and either holds current data or can obtain it from the owner. |

The L2 directory tracks:

- Current L1 data-cache sharers.
- The dirty owner, when a line is in `M`.
- Whether L1 instruction caches may hold instruction copies, if the implementation chooses to track them.

Because L2 is inclusive, every valid L1 data-cache line has a corresponding L2 line or L2 directory entry.

## Read Miss and Shared Access

For `LD48`, `CLC`, `LL48`, or another data read that misses in the L1 data cache:

1. The core sends a shared read request to L2.
2. L2 serializes the request against other requests for the same line.
3. If no L1 owns the line dirty, L2 supplies the line payload and tags.
4. If another L1 owns the line dirty, L2 obtains the current payload and tags from the owner.
5. The owner either downgrades to `S` or supplies data and invalidates, according to the implementation policy.
6. The requester installs the line in `S` or `E`.

The requester must receive payload and tag state from the same coherent line version.

## Write Miss and Upgrade

For `ST48`, `CSC`, successful `SC48`, or another data store:

1. The core must hold the line in `E` or `M` before the store becomes globally visible.
2. If the line is `I`, the core sends a read-exclusive request to L2.
3. If the line is `S`, the core sends an upgrade request to L2.
4. L2 serializes the request against other requests for the same line.
5. L2 invalidates all other L1 data-cache sharers and waits for acknowledgements.
6. If another L1 owns the line dirty, that owner supplies the current payload and tags and loses ownership.
7. L2 grants exclusive ownership to the requester.
8. The requester applies the store and holds the line in `M`.

For a line already in `E`, the core may transition to `M` locally when the store-buffer entry drains, because exclusive ownership has already been established by L2.

## Store Visibility and TSO

Stores become globally visible according to E08-S03.

For this coherence protocol, a store's global visibility point is the point at which:

- Older same-core stores have reached their visibility points.
- The core has exclusive ownership for the target line.
- All required invalidations for the target line have been acknowledged.
- The store's payload and tag effects have been applied to the coherent line version.

After that point, any other core that obtains the line must observe the store or a later globally visible store.

The coherence protocol must preserve TSO behavior:

- Stores from one core reach global visibility in program order.
- A younger store cannot pass an older store from the same core.
- A younger load may execute before an older store reaches global visibility only as allowed by E08-S03.
- `FENCE` drains older stores before younger data-memory operations proceed.

Store-buffer coalescing is allowed only if the resulting global visibility behavior is indistinguishable from the program-order stores required by E08-S03.

## Capability Tag Coherence

Capability tag bits participate in coherent line state.

`CSC` visibility includes:

- The four written payload cells.
- The written tag bit for the capability slot.

`ST48` and successful `SC48` visibility include:

- The two written payload cells.
- Clearing the tag bit for the overlapped 4-cell capability slot.

Coherence rules:

- A line in `S`, `E`, or `M` carries both payload and tag state.
- An invalidation invalidates both payload and tags.
- A downgrade from `M` supplies both payload and tags.
- A writeback from `M` writes both payload and tags.
- L2 responses include both payload and tags.
- No core may observe new payload with old tag or old payload with new tag for a `CSC` visibility point.
- No core may observe an old valid tag after an overlapping `ST48` or successful `SC48` tag clear is globally visible.

The L2 directory and data arrays may store tags directly or may track a dirty owner that has current tags. Either implementation is valid if every read, ownership transfer, and writeback observes the current payload and tags together.

## L1 Data Cache Eviction

L1 data-cache eviction rules:

- Evicting an `I` line has no coherence effect.
- Evicting an `S` line notifies or silently removes the sharer according to the L2 directory policy.
- Evicting an `E` line removes exclusive ownership and leaves a clean L2 copy.
- Evicting an `M` line writes payload and tags back to L2 before the L1 discards the line.

An `M` eviction's writeback is not a new architectural store. It publishes the already-visible coherent line contents to L2 and eventually to memory.

## L2 Eviction and Inclusion

Because L2 is inclusive, L2 eviction must preserve inclusion:

- If L2 evicts a line with L1 sharers, it invalidates those L1 copies first.
- If L2 evicts a line with an `M` owner, it obtains the current payload and tags from the owner.
- Dirty data and tags are written to backing memory before the L2 line is discarded.
- Clean lines may be discarded after invalidating included L1 copies.

Backing memory is below the CPU coherence point. Memory may lag dirty CPU state until L2 writeback or cache maintenance.

## Instruction Cache Coherence

L1 instruction caches are read-only from the data side.

Rules:

- Instruction-cache fills go through L2.
- Instruction-cache lines do not enter `M`.
- Data stores do not automatically update or invalidate L1 instruction-cache lines.
- A core may keep stale instruction-cache contents after data-side code writes.
- Software must use the `FENCE.I` sequence defined by E08-S04 before executing newly written or modified code.

The coherence protocol may optionally track L1 instruction-cache sharers in L2, but architectural correctness cannot depend on automatic instruction-cache invalidation by ordinary data stores.

## Atomic Operations and Coherence

`LL48` and `SC48` use the same coherence protocol as ordinary aligned 48-bit loads and stores.

Minimum rules:

- `LL48` obtains a coherent readable copy of the target line.
- Successful `SC48` requires store authority and exclusive ownership before it becomes globally visible.
- Successful `SC48` is ordered as a store in the TSO model.
- Failed `SC48` performs no coherent store and does not change payload or tags.
- Coherence invalidation or another core's store to the reservation granule may clear a reservation, as defined by E08-S02.

The exact reservation granule and progress rules are not defined by this story.

## Device and DMA Boundary

Device and DMA agents do not participate in this CPU coherence protocol in v0.1.

Consequences:

- DMA writes can update backing memory while CPU caches still hold stale payload and tags.
- Non-tag-aware DMA clears tags in backing memory for overlapped capability slots.
- CPU cores observe DMA updates only after the cache maintenance and fence sequences defined by E10-S04 and E10-S05.

This story defines CPU-cache coherence only.

## Out of Scope for This Story

- Exact finite-state-machine encodings and transient states.
- Store-buffer implementation details beyond the TSO visibility contract.
- `LL48` and `SC48` reservation progress details: E08-S01 and E08-S02.
- Fence instruction encodings and `FENCE.I`: E08-S04.
- Page memory types: E09-S06.
- Noncoherent DMA policy: E10-S04.
- Cache maintenance operations: E10-S05.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Two cores reading the same line can both hold `S`.
- A store to an `S` line invalidates other L1 data-cache sharers before global visibility.
- A store to an `E` line can transition the line to `M` without external invalidations.
- A read by Core 1 after Core 0 holds `M` obtains Core 0's current payload and tags.
- An `M` owner downgrade supplies payload and tags together.
- An `M` eviction writes payload and tags to L2.
- L2 eviction invalidates included L1 data-cache copies.
- Stores from one core become globally visible in program order.
- `CSC` cross-core visibility transfers payload and tag together.
- `ST48` or successful `SC48` cross-core visibility transfers payload and tag clear together.
- Instruction-cache contents can remain stale after data stores until `FENCE.I`.
- DMA writes are not observed through CPU coherence without cache maintenance.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| CPU caches are coherent with each other. | Met for L1 data caches and L2 on normal coherent cacheable memory. |
| A MESI-like protocol is selected for v0.1. | Met. |
| Stores become visible according to the TSO-like memory model. | Met. |
| Capability tags participate in coherent visibility. | Met. |
| Coherence behavior for instruction and data caches is documented. | Met. |

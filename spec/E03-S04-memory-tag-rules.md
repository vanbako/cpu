# E03-S04: Capability Memory Tag Rules

Story: E03-S04

Status: Complete

Normative source: `design.md`, section 5.3

Supporting spike: `spikes/E14-S04-capability-tag-cache-model.md`

## Decision

CPU v0.1 memory has one capability tag bit per naturally aligned 4-cell capability slot.

Tags are architectural metadata. They are not addressable memory bits and cannot be created by ordinary integer data movement.

## Tag Granularity

| Item | Value |
| --- | --- |
| Capability slot size | 4 cells |
| Capability slot alignment | `address mod 4 = 0` |
| Tag granularity | 1 tag per 4-cell slot |
| Tags per 16-cell cache line | 4 |

The tag for slot `[A, A + 4)` describes whether the 96 payload bits in that slot are a valid capability.

## `CLC` and `CSC`

`CLC` rules:

- Requires 4-cell alignment.
- Loads all 96 payload bits and the slot tag as one architectural operation.
- Raises `ALIGN_FAULT` on misalignment.

`CSC` rules:

- Requires 4-cell alignment.
- Stores all 96 payload bits and the slot tag as one architectural operation.
- Raises `ALIGN_FAULT` on misalignment.

Atomicity requirement:

- Another core must not observe new payload with an old tag.
- Another core must not observe old payload with a new tag.
- Cache and memory systems must move payload and tag together for coherent CPU accesses.

## Ordinary Store Tag Clearing

`ST48` writes two cells.

If either written cell overlaps a 4-cell capability slot, that slot's tag is cleared.

Because `ST48` is 2-cell aligned, it may clear at most one capability slot tag.

Examples:

| `ST48` address | Written cells | Cleared capability slot |
| ---: | --- | --- |
| `0x1000` | `0x1000-0x1001` | `0x1000-0x1003` |
| `0x1002` | `0x1002-0x1003` | `0x1000-0x1003` |
| `0x1004` | `0x1004-0x1005` | `0x1004-0x1007` |

`LD48` may read capability payload bits as integer data, but it never returns the tag.

## Cache and Coherence Requirements

The L1 data cache, L2, and memory must carry tag state alongside cache-line data.

For CPU-coherent accesses:

- L2 is the coherence point for payload and tag visibility.
- Tag bits participate in coherent line state.
- A line transfer includes both cell data and associated capability tag bits.
- Cross-core invalidation and ownership must preserve tag/data consistency.

E14-S04 modeled this with a 16-cell line containing four 4-cell capability slots and four tag bits.

## DMA and External Overwrites

Non-tag-aware DMA or external agents clear tags for every overlapped capability slot in memory.

DMA is noncoherent in v0.1:

- DMA writes memory outside CPU cache coherence.
- CPU caches may retain stale data and stale tags.
- Drivers must use cache maintenance and fences before CPU reuse of DMA-written buffers.

This rule prevents external data writes from forging valid capabilities.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CLC` from a 4-cell aligned tagged slot returns payload and tag.
- `CSC` to a 4-cell aligned slot stores payload and tag together.
- Misaligned `CLC` raises `ALIGN_FAULT`.
- Misaligned `CSC` raises `ALIGN_FAULT`.
- `ST48` at the first half of a capability slot clears that slot tag.
- `ST48` at the second half of a capability slot clears that slot tag.
- `ST48` does not clear adjacent capability slot tags.
- `LD48` never returns a valid capability tag.
- Cross-core `CSC` followed by `CLC` observes payload and tag consistently.
- DMA overwrite clears memory tags, and CPU cache invalidation is needed before CPU reuse.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CLC` loads a full capability and tag atomically. | Met. |
| `CSC` stores a full capability and tag atomically. | Met. |
| Any `ST48` into one of the four cells of a capability slot clears that slot's tag. | Met. |
| Capabilities in memory require 4-cell alignment. | Met. |
| Non-tag-aware DMA or external overwrites clear tags. | Met. |
| Tag and data atomicity requirements are stated. | Met. |


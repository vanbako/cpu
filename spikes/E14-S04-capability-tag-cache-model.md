# E14-S04: Capability Tag Storage Through Cache Hierarchy Spike

Story: E14-S04

Status: Spike complete

Prototype: `tools/tag_cache_model.py`

Related stories:

- E03-S01: Capability representation
- E10-S01: Cache hierarchy
- E10-S02: Cache line size

## Question

Can capability tags be modeled cleanly through private L1 data caches, shared inclusive L2, and backing memory while preserving `CLC`/`CSC` atomicity, `ST48` tag clearing, cross-core visibility, and noncoherent DMA behavior?

## Prototype Model

The prototype models:

- 16-cell cache lines.
- 4-cell naturally aligned capability slots.
- One tag bit per capability slot.
- Private per-core L1 data caches.
- Shared inclusive L2 as the CPU coherence point.
- Backing memory below L2.
- Noncoherent DMA that writes memory behind CPU caches.

It is not cycle accurate and does not define the final MESI state machine. Its purpose is to validate tag granularity and movement rules.

## Proposed Tag Granularity

Use one tag bit per naturally aligned 4-cell capability slot.

For the v0.1 16-cell cache line:

| Cache line contents | Count |
| --- | ---: |
| Cells | 16 |
| 96-bit capability slots | 4 |
| Tag bits | 4 |

This keeps tag indexing simple:

```text
line_base = address & ~0xF
capability_slot_base = address & ~0x3
slot_index_in_line = (address & 0xF) / 4
```

## Prototype Results

Command:

```text
python .\tools\tag_cache_model.py
```

Output:

| scenario | result |
| --- | --- |
| cold CLC | untagged slot observed before CSC |
| CSC atomic visibility | core1 sees full payload and tag from core0 through L2 |
| ST48 tag clear | partial overwrite clears only the overlapped 4-cell slot tag |
| noncoherent DMA | CPU sees DMA-cleared tag only after cache invalidation |
| tag granularity | one tag per naturally aligned 4-cell capability slot |

## Findings

`CLC` and `CSC` are cleanest when treated as whole-slot operations:

- `CLC` reads all 4 cells plus the slot tag as one architectural operation.
- `CSC` writes all 4 cells plus the slot tag as one architectural operation.
- The L1 and L2 cache-line representations must move cell data and tag bits together.

`ST48` needs overlap-based tag clearing:

- `ST48` writes 2 cells.
- If either written cell overlaps a 4-cell capability slot, that slot tag is cleared.
- Adjacent capability slot tags are not cleared.

CPU coherence must include tag visibility:

- When one core stores a capability with `CSC`, another core must not observe the new payload with the old tag or the old payload with the new tag.
- L2 must carry enough tag state or directory state to make payload and tag visibility coherent together.

Noncoherent DMA remains manageable:

- DMA/device writes update memory outside CPU coherence.
- Non-tag-aware DMA clears tags for overlapped capability slots in memory.
- CPU caches may still hold stale data and stale tags until software performs cache invalidation.
- Drivers must use cache maintenance and fences around DMA buffers.

## Recommendation

Keep the v0.1 memory tag rule:

- One tag bit per naturally aligned 4-cell capability slot.
- `CLC` and `CSC` move payload and tag atomically.
- Any `ST48` overlapping a capability slot clears that slot tag.
- L1, L2, and memory representations must store tags alongside cache-line data.
- CPU coherence must treat tag bits as part of coherent line state.
- Noncoherent DMA must clear memory tags and requires software cache maintenance before CPU reuse.

This is sufficient to proceed with E03-S04 and E10-S03. The final coherence story still needs to define the MESI-like state machine and the exact tag state carried in L2.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Tag storage granularity is proposed. | Met: one tag per naturally aligned 4-cell capability slot. |
| `CLC` and `CSC` atomicity is modeled. | Met by prototype whole-slot load/store behavior. |
| `ST48` tag-clear behavior is modeled. | Met by overlap-based tag clearing. |
| Coherence visibility of tags is tested. | Met by cross-core `CSC` then `CLC` scenario through L2. |
| Noncoherent DMA tag-clear behavior is documented. | Met by DMA overwrite plus cache invalidation scenario. |


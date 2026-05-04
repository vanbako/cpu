# E15-S05: Memory, Capability, MMU, Cache, and Ordering Composition Audit

Story: E15-S05

Status: Complete

Prerequisites:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S07-effective-access-rule.md`
- `spec/E10-S03-cpu-coherence-protocol.md`
- `spec/E15-S01-terminology-cross-reference-audit.md`

Litmus catalog:

- `tools/memory_consistency_litmus.md`

## Decision

The v0.1 memory, capability, MMU, cache, DMA, and ordering contract is internally consistent after the corrections listed below.

No unresolved blocking inconsistency remains for composed CPU memory accesses, capability tag visibility, page translation, TLB invalidation, LL/SC reservation behavior, cache maintenance, `FENCE`, `FENCE.I`, or noncoherent DMA ownership sequences.

## Corrections Applied

| Finding | Severity | Correction |
| --- | --- | --- |
| E15-S05-F01: E08-S01 said a faulting `LL48` creates no new reservation but did not say whether it clears an older reservation. E08-S02 requires faulting `LL48` to clear any previous reservation. | Blocking LL/SC composition gap | Updated `spec/E08-S01-ll48-sc48.md` to say faulting `LL48` clears any previous reservation and creates none. |
| E15-S05-F02: E09-S07 and E08-S04 said faulting effective accesses or fences do not update reservation state, which conflicted with E08-S02's global rule that synchronous exceptions clear active LL/SC reservations before handler execution. | Blocking reservation-clear wording inconsistency | Updated `spec/E09-S07-effective-access-rule.md` and `spec/E08-S04-fence-instructions.md` to distinguish normal instruction effects from reservation clearing caused by trap entry. Updated `tools/fault_priority_matrix.md` accordingly. |

## Audit Scope

This audit cross-checks:

- Capability payload/tag storage and tag-clearing rules from E03-S04 and E04-S03/E04-S05.
- Local-capability storage restrictions from E03-S05.
- Protected return-stack access restrictions from E06-S04.
- Effective access, page permissions, page memory types, TLB matching, and translation maintenance from E09.
- LL/SC access checks, reservation clearing, progress, and coherent visibility from E08-S01/E08-S02.
- TSO-like ordering, store buffers, `FENCE`, `FENCE.I`, and `SFENCE.VM` from E08-S03/E08-S04.
- Cache hierarchy, line size, coherence, noncoherent DMA, and cache maintenance from E10.
- State and priority findings from E15-S03 and E15-S04 where they affect memory ordering or reservation state.

## Composition Matrix

| Path | Composed rule | Audit result |
| --- | --- | --- |
| Instruction fetch | `PCC` authority, slot/fetch placement, translation, page `X`, memory type, and instruction-cache freshness all apply. Fetch is allowed only from executable normal coherent memory in v0.1. | Pass. `FENCE.I` and `SFENCE.VM` cover stale instruction bytes and stale translations respectively. |
| `LD48` / `ST48` | Effective access uses capability tag/seal/address/alignment/bounds/protected-stack/permission/page/memory-type order. `ST48` clears any overlapped capability-slot tag at one visibility point. | Pass. |
| `CLC` / `CSC` | Capability payload and tag move together. `CLC` never faults on an invalid memory tag; it loads an invalid capability. `CSC` stores payload plus source tag atomically and enforces `SL` only for valid local source capabilities. | Pass. |
| Local capabilities | A valid local capability may be stored only through `ST`, `SC`, and `SL`; integer stores do not carry tags and cannot create local authority. | Pass. |
| Protected return stack | Ordinary data/capability accesses overlapping protected return-stack storage raise `RETURN_STACK_PERMISSION_FAULT` after range/bounds are known and before ordinary permission or translation effects. | Pass. |
| Page translation and privilege | Capability permissions and page permissions are both required. Kernel bypasses only `PTE.U` user/kernel page privilege, not capability, page `R/W/X`, alignment, memory type, or physical checks. | Pass. |
| Page memory types | `NORMAL_COHERENT` supports fetch, data, capability, LL/SC, and cache maintenance. `NORMAL_UNCACHEABLE` supports data/capability accesses but not fetch or LL/SC. `DEVICE_ORDERED` supports only integer `LD48`/`ST48`. | Pass. |
| TLB and stale translations | TLBs are private per core and cannot create capability authority. `SFENCE.VM` invalidates selected local entries and cached failures; remote shootdown is a software protocol with fences and acknowledgments. | Pass. |
| TSO and store buffers | CPU normal coherent stores are multi-copy atomic at L2. Store buffers may delay global visibility, but same-core loads forward older overlapping payload/tag effects. `FENCE` drains older stores before younger data/cache-maintenance operations. | Pass. |
| LL/SC | `LL48` creates a physical-address reservation only after successful access checks. Faulting `LL48`, trap/interrupt/debug entry, `IRET`, `SATP`/ASID/`SR` writes, `SFENCE.VM`, `WFI`, conflicting stores, and invalidating maintenance clear reservations. | Pass after correction. |
| Cache hierarchy and tags | L1 data caches and inclusive L2 carry payload plus tag state. L2 is the CPU coherence point. Coherence transfers, invalidations, downgrades, and writebacks move payload and tags together. | Pass. |
| Cache maintenance | Maintenance is line-granular over 16-cell lines, uses capability-bounded ranges, translates each maintained line, and preserves payload/tag integrity. Fences are required around DMA and ordinary memory ordering boundaries. | Pass. Partial older-line progress on later-line fault remains documented implementation behavior, not a portable recovery contract. |
| Noncoherent DMA | Devices do not snoop CPU caches, update L2, join the CPU global store order, or observe tags. Drivers must use ownership handoff, `FENCE`, and cache maintenance for `NORMAL_COHERENT`; uncacheable buffers require fences but no cache effect. | Pass. |
| DMA and tags | Non-tag-aware DMA clears backing-memory tags for overlapped capability slots. CPU caches may hold stale payload/tag copies until invalidation. Device-created payload bits never create valid architectural tags. | Pass. |

## Stale-state Review

| Stale state risk | Required prevention or disposition |
| --- | --- |
| Stale capability payload/tag in another CPU core | Coherent L1/L2 protocol transfers and invalidates payload/tag together. |
| Same-core stale tag after buffered integer store | Store-buffer forwarding must make `CLC` observe the local tag clear. |
| Stale backing memory after CPU writes before device read | `FENCE; CACHE.CLEAN; FENCE` before device doorbell for `NORMAL_COHERENT`. |
| Stale CPU cache payload/tag after device write | Completion observation, `FENCE; CACHE.INVAL; FENCE` before CPU consumption for `NORMAL_COHERENT`. |
| Stale uncacheable DMA ordering | Completion/doorbell protocol plus `FENCE`; cache maintenance has no cache-line effect. |
| Stale instruction bytes after data stores | Local `FENCE.I` after data stores are globally visible; remote cores execute their own `FENCE.I`. |
| Stale instruction bytes after DMA code load | DMA completion sequence plus `FENCE.I` before fetch. |
| Stale local translation after page-table update | Matching local `SFENCE.VM` form; `SFENCE.VM` also invalidates cached page-walk failures. |
| Stale remote translation or ASID reuse | Software shootdown using request, target local invalidation, acknowledgment, and fences before reuse. |
| Stale reservation after fault or context switch | E08-S02 clears reservations on trap/interrupt/debug entry, `IRET`, `SATP`/ASID/`SR` writes, `SFENCE.VM`, and other clear events. |
| Stale predictor or fetch metadata with translation authority | `FENCE.I` or `SFENCE.VM` must invalidate or retag structures that could bypass fresh fetch or permission checks. |

## Accepted Deferrals and Boundaries

| Area | Disposition |
| --- | --- |
| Coherent I/O and tag-aware I/O | Out of scope for v0.1. Future profiles must define device interaction with CPU coherence, tags, ordering, page tables, and capability authority. |
| IOMMU or device capability authorization | Out of scope for mandatory v0.1. CPU capabilities and CPU page tables do not directly authorize external DMA. |
| Remote instruction-cache synchronization mechanism | Platform/software protocol. The architectural requirement is that each target core executes `FENCE.I` before acknowledging completion. |
| Remote TLB shootdown mechanism | Software/platform protocol using IPI or equivalent signal plus target `SFENCE.VM` and acknowledgment. |
| Cache-maintenance partial progress after multi-line fault | Documented implementation behavior if all-or-nothing maintenance cannot be guaranteed. Portable software must not rely on recovery progress. |
| Page-table walker bus failures | E09-S07 treats walker access failures as `PAGE_FAULT` unless a later platform story classifies the failure as `ACCESS_FAULT`. |

## Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| E15-S05-F01: Faulting `LL48` reservation behavior was incomplete in E08-S01. | Corrected | E08-S01 now matches E08-S02: a faulting `LL48` clears any previous reservation and creates none. |
| E15-S05-F02: Reservation clearing on synchronous exceptions was obscured by no-normal-effect wording in E09-S07 and E08-S04. | Corrected | E09-S07, E08-S04, and the E15-S04 matrix now distinguish normal effects from E08-S02 trap-entry reservation clearing. |
| E15-S05-F03: Effective access rules agree with load, store, capability, atomic, cache-maintenance, TLB, and fetch stories. | Pass | E09-S07 remains the canonical access/fault order. |
| E15-S05-F04: Capability tag clearing and payload/tag visibility agree across `ST48`, `SC48`, `CLC`, `CSC`, coherence, cache maintenance, and DMA. | Pass | No correction required. |
| E15-S05-F05: Permission, local-capability, protected-stack, page-permission, privilege, memory-type, and alignment rules compose without authority gaps. | Pass | No correction required. |
| E15-S05-F06: TSO, fences, `FENCE.I`, `SFENCE.VM`, cache maintenance, LL/SC clearing, shootdown, and DMA ownership sequences form valid software protocols. | Pass | No correction required after reservation wording updates. |
| E15-S05-F07: Cache hierarchy, inclusive L2 coherence point, private L1s, device memory, and uncacheable memory are mutually consistent. | Pass | No correction required. |

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The effective access rule agrees with every load, store, capability, atomic, cache-maintenance, TLB, and fetch story. | Met. |
| Capability tag storage, tag clearing, `CLC`, `CSC`, `ST48`, non-tag-aware DMA, coherence, and memory ordering use compatible visibility and atomicity rules. | Met. |
| Permission bits, local capability rules, protected return-stack storage, page permissions, privilege mode, memory types, and alignment compose without gaps. | Met. |
| TSO, fences, `FENCE.I`, `SFENCE.VM`, cache maintenance, LL/SC reservation clearing, shootdown, and DMA ownership rules form valid software sequences. | Met after reservation wording corrections. |
| Cache hierarchy, coherence point, inclusive L2, private L1s, device memory, and uncacheable memory are consistent. | Met. |
| Any path where an implementation could observe stale data, stale tags, stale translations, or stale instruction bytes is either forbidden, fenced, invalidated, or explicitly out of scope. | Met by the stale-state review. |

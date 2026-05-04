# E10-S05: Cache Maintenance Operations

Story: E10-S05

Status: Complete

Normative source: `design.md`, section 13

Prerequisites:

- `spec/E10-S01-cache-hierarchy.md`
- `spec/E10-S02-cache-line-size.md`

Related sources:

- `spec/E02-S03-extended-csr-space.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E10-S03-cpu-coherence-protocol.md`

## Decision

CPU v0.1 defines three privileged cache maintenance operations:

- `CACHE.CLEAN`
- `CACHE.INVAL`
- `CACHE.CLEANINVAL`

These operations maintain data-cache and L2 coherent cache state for a cell-addressed range. They operate at 16-cell cache-line granularity and preserve capability payload/tag consistency.

They do not replace `FENCE`, `FENCE.I`, or `SFENCE.VM`. Software uses fences around cache maintenance when it needs ordering against ordinary data memory, instruction fetch, DMA, or page-table updates.

## Instruction Forms

Architectural forms:

| Instruction | Assembly form | Source registers | Required privilege | Summary |
| --- | --- | --- | --- | --- |
| `CACHE.CLEAN` | `CACHE.CLEAN Ca, Di, Dn` | `Ca`, `Di`, `Dn` | `K` | Write back dirty CPU data and tags for the range. |
| `CACHE.INVAL` | `CACHE.INVAL Ca, Di, Dn` | `Ca`, `Di`, `Dn` | `K` | Discard CPU cache copies for the range. |
| `CACHE.CLEANINVAL` | `CACHE.CLEANINVAL Ca, Di, Dn` | `Ca`, `Di`, `Dn` | `K` | Clean dirty copies, then discard CPU cache copies for the range. |

`Ca` is a capability bounding the maintenance range. `Di` is a signed 48-bit cell offset. `Dn` is an unsigned 48-bit cell length.

The final opcode encoding is owned by E04-S06. If an implementation also exposes `CACHECTL`, the CSR command encoding must be equivalent to these architectural effects and remain kernel-only.

User-mode execution raises `PRIVILEGE_FAULT` and performs no cache maintenance.

## Range Calculation

The requested range is:

```text
start = Ca.cursor + signed(Di[47:0])
len   = unsigned(Dn[47:0])
end   = start + len
```

The calculation is performed in mathematical integers.

If `len=0`, the operation is a no-op after privilege and source-operand decoding. It does not require a valid capability range and performs no translation.

For nonzero length:

- `Ca.tag` must be valid.
- `Ca` must be unsealed.
- `0 <= start < end <= 2^48`.
- The requested range `[start, end)` must be inside `Ca.bounds`.

Cache maintenance is a privileged maintenance operation, not an architectural load or store. It does not require `LD`, `ST`, `LC`, `SC`, or `SL` permission bits. The capability still bounds the range so maintenance cannot silently target unrelated addresses.

## Line Rounding

Cache maintenance operates on every cache line that overlaps the requested range.

With the v0.1 16-cell line size:

```text
line_start = start & ~0xF
line_end   = (end + 15) & ~0xF
```

The maintained line range is `[line_start, line_end)`.

Because maintenance affects entire lines, the expanded line range must also be inside `Ca.bounds`. If `[line_start, line_end)` is not inside `Ca.bounds`, the instruction raises `CAPABILITY_BOUNDS_FAULT` and performs no maintenance.

Portable drivers should align DMA buffers and code-loading ranges to 16-cell cache-line boundaries. If they cannot, they must use a capability that intentionally covers the full expanded cache-line range and must account for unrelated data sharing those lines.

## Translation

Cache maintenance range addresses are effective cell addresses.

When `SATP.MODE=BARE`, the effective line address is the physical line address.

When `SATP.MODE=RADIX4`, each cache line in the expanded range is translated through the active address space:

- Translation uses the same active `SATP` and ASID as ordinary data accesses.
- Translation requires a valid page mapping for the line address.
- Page-table walker and TLB behavior follow E09-S03 and related MMU stories.
- `PTE.U` does not block a kernel-mode cache maintenance operation.
- Page memory type may restrict whether maintenance is meaningful or legal, as finalized by E09-S06.

If translation or page-table walking fails for any line, the instruction raises `PAGE_FAULT` for that line's virtual cell address and performs no architecturally visible maintenance for younger lines. Implementations should avoid partial maintenance on older lines when a later line faults, but software must not rely on partial progress after a fault.

## Maintenance Scope

The operations apply to the CPU coherent cache hierarchy:

- The executing core's private L1 data cache.
- Other cores' private L1 data caches through the shared L2 directory.
- The shared inclusive L2 cache.
- Associated capability tag state for every maintained line.

The operation does not directly invalidate other cores' L1 instruction caches. Instruction-cache synchronization is handled by `FENCE.I` and any platform-defined remote instruction-cache synchronization protocol.

Because L2 is inclusive, a range operation initiated by one core can locate L1 data-cache sharers or dirty owners through L2 directory state. A conforming implementation must not leave a stale L1 data-cache copy in any core after a completed invalidate or clean-invalidate for the maintained line.

## `CACHE.CLEAN`

`CACHE.CLEAN` writes dirty CPU cache contents for the maintained lines back toward backing memory.

Required behavior for each maintained line:

- If any L1 data cache owns a dirty line, the current payload and tag bits are obtained from the owner.
- Dirty payload and tag state are written through L2 toward backing memory.
- Clean cache copies may remain valid.
- Dirty cache copies become clean after their dirty contents are written back.
- Payload cells and capability tag bits are written back together.

`CACHE.CLEAN` is used before a noncoherent device or DMA engine reads a buffer that the CPU may have modified.

`CACHE.CLEAN` does not discard valid cache copies. CPU cores may continue to hold clean copies after the operation.

## `CACHE.INVAL`

`CACHE.INVAL` invalidates CPU cache copies for the maintained lines.

Required behavior for each maintained line:

- Valid L1 data-cache copies are invalidated.
- The L2 directory no longer reports L1 data-cache sharers or dirty owners for the line.
- L2 may keep or discard a clean copy according to implementation policy, unless the line's memory type or platform maintenance policy requires the L2 copy to be discarded.
- Dirty CPU data and tags may be discarded without writeback.

`CACHE.INVAL` is used after noncoherent DMA/device writes and before the CPU reads the buffer.

Software must not use `CACHE.INVAL` on dirty CPU data that it still needs. If CPU writes must be preserved before invalidation, software must use `CACHE.CLEANINVAL` or `CACHE.CLEAN` followed by `CACHE.INVAL`.

## `CACHE.CLEANINVAL`

`CACHE.CLEANINVAL` performs clean then invalidate for the maintained lines.

Required behavior for each maintained line:

- Dirty CPU payload and tag state are written back through L2 toward backing memory.
- All L1 data-cache copies are invalidated.
- L2 no longer reports L1 data-cache sharers or dirty owners for the line.
- L2 may keep or discard a clean copy according to implementation policy, unless the line's memory type or platform maintenance policy requires discard.

`CACHE.CLEANINVAL` is used for bidirectional DMA setup, page lifecycle transitions where dirty CPU data must be preserved before cache copies are removed, and conservative driver sequences.

## Tag Handling

Cache maintenance must preserve capability tag integrity.

Rules:

- Clean writes back payload cells and their associated tag bits together.
- Invalidation discards payload cells and tag bits together.
- Clean-invalidate writes back dirty payload and tag bits together before discarding cache copies.
- A maintenance operation must not create a valid tag from untagged payload.
- A maintenance operation must not write back payload without its matching tag state or tag state without its matching payload.

This keeps `CSC`, `ST48`, DMA overwrite, and cache-maintenance behavior consistent with E03-S04 and E10-S03.

## Ordering With `FENCE`

Cache maintenance instructions are synchronous with their own cache-maintenance effect before they retire, but they are not a substitute for `FENCE`.

Software must use `FENCE` when it needs ordinary memory operations ordered with maintenance:

| Scenario | Required sequence |
| --- | --- |
| CPU writes buffer, then device reads it | CPU stores; `FENCE`; `CACHE.CLEAN`; `FENCE`; device doorbell. |
| Device writes buffer, then CPU reads it | Observe device completion; `FENCE`; `CACHE.INVAL`; `FENCE`; CPU loads. |
| Bidirectional DMA buffer setup | CPU stores if any; `FENCE`; `CACHE.CLEANINVAL`; `FENCE`; device doorbell. |
| Page reused after CPU writes and before DMA use | `FENCE`; `CACHE.CLEANINVAL`; page ownership update. |

The first `FENCE` ensures older CPU stores have reached the coherent cache hierarchy before maintenance observes the lines. The second `FENCE` ensures the maintenance operation is complete before younger device-control stores or CPU data accesses proceed.

E08-S04 finalizes exact fence instruction encodings and any stronger platform sequence for device memory.

## Interaction With `FENCE.I`

Data stores do not automatically invalidate L1 instruction-cache contents.

For code written through data stores and then executed by the same core, software must use the instruction-fetch synchronization sequence finalized by E08-S04. The conservative v0.1 sequence is:

```text
store new code
FENCE
CACHE.CLEAN code_range
FENCE.I
```

`CACHE.CLEAN` ensures dirty data-cache contents and tags for the code range are visible through the coherent hierarchy or backing memory as required by the implementation. `FENCE.I` makes stale instruction-cache contents unusable for subsequent instruction fetch on the executing core.

For code that may execute on other cores, software must also cause those cores to perform their required instruction-cache synchronization, typically through an IPI-based protocol. Remote instruction-cache synchronization details are finalized by E08-S04.

## Faults and Atomicity

Faulting cache maintenance instructions do not retire.

Fault behavior:

| Failure | Exception |
| --- | --- |
| User-mode execution | `PRIVILEGE_FAULT` |
| Invalid `Ca.tag` | `CAPABILITY_TAG_FAULT` |
| Sealed `Ca` | `CAPABILITY_SEAL_TYPE_FAULT` |
| Range arithmetic underflow or overflow | `CAPABILITY_BOUNDS_FAULT` |
| Requested or expanded line range outside `Ca.bounds` | `CAPABILITY_BOUNDS_FAULT` |
| Translation failure for a maintained line | `PAGE_FAULT` |
| Memory type or platform rejects maintenance | `ACCESS_FAULT` |

On a fault:

- No integer or capability destination register is written.
- No memory payload or memory tag is architecturally modified by the instruction.
- No required cache maintenance completion is reported.

If an implementation cannot guarantee all-or-nothing cache effects across a multi-line range, it must document that faulting multi-line maintenance may have completed older lines before the fault. Portable software should use page- and line-valid ranges and should not depend on recovering precise partial maintenance progress.

## Out of Scope for This Story

- Noncoherent DMA ownership protocol and driver API policy: E10-S04.
- Detailed page memory-type semantics: E09-S06.
- Final `FENCE`, `FENCE.I`, and `SFENCE.VM` encodings: E08-S04.
- Instruction-cache maintenance operations beyond the `FENCE.I` synchronization contract.
- Cache-enable CSRs and implementation-specific cache-control policy.
- Coherent I/O.

## Verification Notes

Minimum conformance checks for later simulator, firmware, OS, and RTL work:

- User-mode `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` raise `PRIVILEGE_FAULT`.
- Nonzero range with invalid authorizing capability raises capability tag fault.
- Unaligned ranges are rounded to overlapping 16-cell cache lines.
- Expanded line range outside capability bounds raises capability bounds fault.
- `CACHE.CLEAN` writes dirty payload and tag state back together.
- `CACHE.INVAL` removes L1 data-cache copies and directory sharers for the range.
- `CACHE.CLEANINVAL` writes dirty data and tags back before invalidating cache copies.
- DMA-read setup uses `FENCE; CACHE.CLEAN; FENCE`.
- DMA-write completion uses `FENCE; CACHE.INVAL; FENCE`.
- `ST48` tag-clear state is preserved by clean and discarded by invalidation with its payload.
- Code written through data stores is not guaranteed visible to instruction fetch until the required `FENCE.I` sequence.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CACHE.CLEAN` is defined as privileged. | Met. |
| `CACHE.INVAL` is defined as privileged. | Met. |
| `CACHE.CLEANINVAL` is defined as privileged. | Met. |
| Required interaction with `FENCE` and `FENCE.I` is documented. | Met. |
| Address range and alignment behavior are specified. | Met. |

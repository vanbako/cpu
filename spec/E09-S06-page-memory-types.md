# E09-S06: Page Memory Types

Story: E09-S06

Status: Complete

Normative source: `design.md`, sections 12.5, 12.6, and 13

Prerequisites:

- `spec/E09-S05-pte-format.md`
- `spec/E10-S05-cache-maintenance-operations.md`

Related sources:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E08-S01-ll48-sc48.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E09-S07-effective-access-rule.md`
- `spec/E10-S03-cpu-coherence-protocol.md`

## Decision

CPU v0.1 defines three valid page memory types and one reserved PTE memory-type encoding.

The memory type controls cache allocation, CPU coherence participation, capability-tag storage, device side effects, legal access classes, and the fence sequences software must use around device communication.

Memory-type legality is checked after capability authority, alignment, translation, page privilege, and page permission checks. A valid memory type that rejects an otherwise authorized access raises `ACCESS_FAULT`, as specified by E09-S07.

## Memory Type Encodings

For `SATP.MODE=RADIX4`, the page memory type comes from the L3 leaf PTE `MT[1:0]` field.

| `MT` | Name | Summary |
| ---: | --- | --- |
| `0b00` | `NORMAL_COHERENT` | Cacheable normal memory that participates in CPU coherence. |
| `0b01` | `NORMAL_UNCACHEABLE` | Normal memory that bypasses CPU data caches and CPU coherence allocation. |
| `0b10` | `DEVICE_ORDERED` | Device or MMIO memory with ordered side-effecting accesses. |
| `0b11` | Reserved | Invalid for a leaf PTE and raises `PAGE_FAULT`. |

When `SATP.MODE=BARE`, there is no PTE. The platform physical memory attributes must classify each physical range using equivalent memory-type behavior. If a bare-mode physical range is not classified, access to that range raises `ACCESS_FAULT`.

## Access Class Matrix

The table below applies after the access has already passed capability, alignment, translation, page privilege, and page `R`, `W`, or `X` checks.

| Access class | `NORMAL_COHERENT` | `NORMAL_UNCACHEABLE` | `DEVICE_ORDERED` |
| --- | --- | --- | --- |
| Instruction fetch | Allowed | `ACCESS_FAULT` | `ACCESS_FAULT` |
| `LD48` | Allowed | Allowed | Allowed if the device accepts the addressed register. |
| `ST48` | Allowed | Allowed | Allowed if the device accepts the addressed register. |
| `CLC` | Allowed | Allowed | `ACCESS_FAULT` |
| `CSC` | Allowed | Allowed | `ACCESS_FAULT` |
| `LL48` | Allowed | `ACCESS_FAULT` | `ACCESS_FAULT` |
| `SC48` | Allowed | `ACCESS_FAULT` | `ACCESS_FAULT` |
| `CACHE.CLEAN` | Allowed | No cache-line effect | `ACCESS_FAULT` |
| `CACHE.INVAL` | Allowed | No cache-line effect | `ACCESS_FAULT` |
| `CACHE.CLEANINVAL` | Allowed | No cache-line effect | `ACCESS_FAULT` |

`NORMAL_UNCACHEABLE` is not executable in the v0.1 base architecture. This keeps instruction fetch tied to the coherent L1 instruction cache and L2 hierarchy defined by E10-S01 and E10-S03.

`DEVICE_ORDERED` supports only integer data loads and stores. Capability memory operations are rejected because device memory does not preserve architectural capability tags. Atomic `LL48` and `SC48` are rejected because device memory and uncacheable memory do not participate in the CPU coherence protocol required by E08-S01.

## `NORMAL_COHERENT`

`NORMAL_COHERENT` is ordinary cacheable memory.

Properties:

- Data and capability accesses may allocate in the private L1 data cache and shared inclusive L2.
- Instruction fetch may allocate in the private L1 instruction cache and fill through L2.
- CPU accesses participate in the MESI-like CPU coherence protocol from E10-S03.
- CPU data memory ordering follows the TSO-like model from E08-S03.
- Capability payload and tag state move through L1, L2, and backing memory together.
- `LL48` and `SC48` use the normal coherent reservation and ownership rules.

`NORMAL_COHERENT` is the required memory type for normal code, kernel data, user data, page tables, stacks, heap memory, and portable CPU synchronization objects.

`CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` are meaningful for `NORMAL_COHERENT` ranges. They operate on coherent L1 data-cache and L2 state as specified by E10-S05.

## `NORMAL_UNCACHEABLE`

`NORMAL_UNCACHEABLE` is ordinary memory that is not cached by the CPU data hierarchy.

Properties:

- Data and capability accesses do not allocate valid L1 data-cache lines.
- Data and capability accesses do not allocate coherent L2 lines or become CPU coherence events.
- Accesses are performed against the platform backing-memory path.
- Capability payload and tag storage exist for the physical range.
- `LD48`, `ST48`, `CLC`, and `CSC` are legal when the device-independent backing memory accepts the access.
- Aligned 48-bit integer accesses and aligned 96-bit capability accesses are not torn.

CPU implementations may use internal buffering for `NORMAL_UNCACHEABLE` only if the architectural behavior is unchanged:

- Same-core accesses to `NORMAL_UNCACHEABLE` memory become visible in program order.
- Two CPU accesses to the same naturally aligned 48-bit word or 96-bit capability slot observe one serialization order at the backing-memory point.
- `ST48` clears any overlapped capability slot tag at the same serialization point as the payload write.
- `CSC` writes payload and tag together at one serialization point.
- `CLC` observes payload and tag from one serialization point.

`NORMAL_UNCACHEABLE` is intended for noncoherent buffers and memory windows where cache allocation is undesirable. It is not a CPU synchronization memory type. Portable locks, reference counts, and inter-core communication that rely on `LL48` and `SC48` must use `NORMAL_COHERENT`.

Cache maintenance operations over `NORMAL_UNCACHEABLE` lines complete after the usual privilege, range, capability, and translation checks, but have no cache-line effect because the memory type does not allow CPU cache copies. This lets generic driver code use one maintenance path for coherent and uncacheable buffers.

## `DEVICE_ORDERED`

`DEVICE_ORDERED` is for memory-mapped device registers and side-effecting device windows.

Properties:

- CPU data caches and instruction caches must not allocate lines for this memory type.
- CPU accesses are visible device transactions, not normal memory coherence events.
- Implementations must not speculate, merge, duplicate, or reorder visible device transactions in a way that changes the architectural device-observable order.
- Same-core `DEVICE_ORDERED` accesses become visible to the addressed device in program order.
- `LD48` may have device-defined read side effects.
- `ST48` may have device-defined write side effects.

`DEVICE_ORDERED` does not provide architectural capability-tag storage:

- `CLC` raises `ACCESS_FAULT`.
- `CSC` raises `ACCESS_FAULT`.
- `LD48` reads only device payload data and never returns a tag.
- `ST48` writes only device payload data and cannot create a valid tag.

Instruction fetch from `DEVICE_ORDERED` memory raises `ACCESS_FAULT`, even if the PTE has `X=1`.

Cache maintenance operations over `DEVICE_ORDERED` memory raise `ACCESS_FAULT`. Device register windows are not cacheable buffers, and treating maintenance as a silent no-op could hide an invalid driver range.

The platform may reject a specific `LD48` or `ST48` to a device register because the register is absent, unsupported, read-only, write-only, or requires a narrower future access form. Such rejection raises `ACCESS_FAULT`.

## Reserved Memory Type

`MT=0b11` is reserved in a valid leaf PTE.

When the page-table walker encounters `MT=0b11` in an L3 leaf PTE:

- The translation fails before any memory payload, memory tag, cache state, reservation state, or device side effect is updated.
- The exception is `PAGE_FAULT`.
- `TVAL` is the faulting virtual cell address.
- `CAPCAUSE=NONE`.
- `FAULTCAPIDX=NONE`.

This is a page-walk validity failure, not a memory-type `ACCESS_FAULT`. Valid memory types use `ACCESS_FAULT` only when the selected type does not support the already-authorized access class.

## Ordering and Fences

`NORMAL_COHERENT` CPU accesses follow E08-S03. `FENCE` drains older coherent stores to the CPU coherence point before younger data-memory operations proceed.

`NORMAL_UNCACHEABLE` accesses are ordered in program order with respect to other `NORMAL_UNCACHEABLE` accesses from the same core. Software must use `FENCE` when ordering is required between `NORMAL_UNCACHEABLE` accesses and `NORMAL_COHERENT` accesses, cache maintenance, or device control stores.

`DEVICE_ORDERED` accesses are ordered with respect to other `DEVICE_ORDERED` accesses from the same core, but they are not a substitute for a `FENCE` between normal memory and device registers. Device register reads and writes do not automatically drain older coherent stores, perform cache maintenance, or make device DMA writes visible through CPU caches.

Required portable sequences:

| Scenario | Required sequence |
| --- | --- |
| CPU writes a `NORMAL_COHERENT` buffer, then device reads it | CPU stores; `FENCE`; `CACHE.CLEAN`; `FENCE`; `ST48` device doorbell. |
| CPU writes a `NORMAL_UNCACHEABLE` buffer, then device reads it | CPU stores; `FENCE`; `ST48` device doorbell. |
| Device writes a `NORMAL_COHERENT` buffer, then CPU reads it | Observe device completion; `FENCE`; `CACHE.INVAL`; `FENCE`; CPU loads. |
| Device writes a `NORMAL_UNCACHEABLE` buffer, then CPU reads it | Observe device completion; `FENCE`; CPU loads. |
| CPU configures normal memory state, then writes device registers | CPU stores; `FENCE`; device register stores. |
| CPU reads device status, then consumes normal memory affected by the device | Device register load; `FENCE`; CPU loads. |

E08-S04 owns the final `FENCE`, `FENCE.I`, and `SFENCE.VM` instruction encodings and any stronger platform-defined ordering sequences.

## Tag Handling With External Agents

For `NORMAL_COHERENT` and `NORMAL_UNCACHEABLE`, the physical range has architectural capability-tag storage.

CPU tag rules:

- `CLC` loads payload and tag together.
- `CSC` stores payload and tag together.
- `ST48` clears any overlapped capability-slot tag.
- `LD48` returns only payload cells.

External non-tag-aware writes, including DMA writes, clear tags for every overlapped capability slot in backing memory.

For `NORMAL_COHERENT` DMA buffers, CPU caches may still hold stale payload and stale tag state after the external write. Software must use the cache maintenance and fence sequence before CPU reuse.

For `NORMAL_UNCACHEABLE` DMA buffers, the CPU does not hold cache copies for the range, so cache maintenance is not required. Software still needs `FENCE` around device completion and CPU consumption to establish ordering.

`DEVICE_ORDERED` memory has no architectural capability-tag storage, so external tag preservation is not defined for device register windows.

## Fault Reporting

Fault priority follows E09-S07.

Memory-type failures use these exceptions:

| Failure | Exception |
| --- | --- |
| Leaf PTE has `MT=0b11` | `PAGE_FAULT` |
| Valid memory type rejects the access class | `ACCESS_FAULT` |
| Device rejects an otherwise legal `LD48` or `ST48` | `ACCESS_FAULT` |
| Bare-mode physical range has no memory-type classification | `ACCESS_FAULT` |
| Cache maintenance targets `DEVICE_ORDERED` memory | `ACCESS_FAULT` |

For `ACCESS_FAULT`, `TVAL` reports the faulting physical cell address when known; otherwise it reports the effective cell address or `0`.

On any memory-type fault, the instruction does not retire and does not update memory payload, memory tags, cache state, reservation state, device state, destination registers, or architecturally visible maintenance completion.

## Out of Scope for This Story

- PTE bit layout and leaf/non-leaf validity: E09-S05.
- Fault priority before memory-type checks: E09-S07.
- Final opcode encodings for `FENCE` and cache maintenance: E08-S04 and E04-S06.
- Noncoherent DMA ownership policy and driver APIs: E10-S04.
- Cache maintenance operation internals: E10-S05.
- Coherent I/O and device participation in CPU coherence.
- Wider or narrower MMIO access forms beyond `LD48` and `ST48`.

## Verification Notes

Minimum conformance checks for later simulator, OS, and RTL work:

- `MT=0b00` permits fetch, data, capability, LL/SC, and cache maintenance when page and capability checks pass.
- `MT=0b01` permits `LD48`, `ST48`, `CLC`, and `CSC`, but does not allocate CPU cache lines.
- `MT=0b01` rejects instruction fetch with `ACCESS_FAULT`.
- `MT=0b01` rejects `LL48` and `SC48` with `ACCESS_FAULT`.
- `MT=0b01` cache maintenance completes with no cache-line effect after ordinary maintenance checks pass.
- `MT=0b10` permits only accepted `LD48` and `ST48` device transactions.
- `MT=0b10` rejects instruction fetch, `CLC`, `CSC`, `LL48`, `SC48`, and cache maintenance with `ACCESS_FAULT`.
- `MT=0b11` in a leaf PTE raises `PAGE_FAULT`, not `ACCESS_FAULT`.
- Device doorbell after coherent descriptor stores uses `FENCE; CACHE.CLEAN; FENCE`.
- Device completion before coherent DMA-buffer reads uses `FENCE; CACHE.INVAL; FENCE`.
- Uncacheable DMA buffers require ordering fences but not cache maintenance.
- Non-tag-aware DMA overwrite clears backing-memory tags for normal memory ranges.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Normal coherent cacheable memory is defined. | Met. |
| Normal uncacheable memory is defined. | Met. |
| Device ordered memory is defined. | Met. |
| Reserved memory type behavior is specified. | Met. |
| Fence requirements for device memory are documented. | Met. |

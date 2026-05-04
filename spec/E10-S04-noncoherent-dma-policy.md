# E10-S04: Noncoherent DMA Policy

Story: E10-S04

Status: Complete

Normative source: `design.md`, sections 5.3, 11.2, and 13

Prerequisites:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E10-S05-cache-maintenance-operations.md`

Related sources:

- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S06-page-memory-types.md`
- `spec/E10-S02-cache-line-size.md`
- `spec/E10-S03-cpu-coherence-protocol.md`

## Decision

CPU v0.1 uses noncoherent I/O.

Device and DMA agents do not participate in the CPU cache-coherence protocol, do not snoop private L1 data caches, do not update the shared L2 directory, and do not participate in the CPU global store order.

Drivers must use explicit ownership handoff, `FENCE`, and cache maintenance when sharing memory between CPUs and devices.

Coherent I/O is explicitly deferred beyond v0.1.

## I/O Coherence Boundary

The CPU coherent domain contains:

- CPU cores.
- Private L1 data caches.
- The shared inclusive L2.
- Capability tag state carried by coherent cache lines.

The v0.1 I/O domain is outside that coherent domain.

Consequences:

- Device reads observe backing memory, not dirty CPU cache state that has not been cleaned.
- Device writes update backing memory, not CPU L1 or L2 cache copies.
- CPU caches may contain stale payload and stale tag state after device writes.
- DMA/device transactions are not multi-copy atomic with respect to CPU cores.
- DMA/device transactions are not ordered by the CPU TSO model except through explicit driver sequences.

The L2 cache is the CPU coherence point only for CPU-originated coherent accesses. It is not a coherent I/O home agent in v0.1.

## DMA Address and Authority

Devices operate on platform-defined bus addresses or physical addresses supplied by privileged software.

CPU capabilities and CPU page tables authorize CPU instructions. They do not directly authorize an external device DMA transaction unless a later platform profile defines an IOMMU or device capability mechanism.

The kernel or driver is responsible for:

- Selecting memory that the device is allowed to access.
- Translating or allocating a device-visible address for that memory.
- Programming the device registers with that address.
- Preventing user software from using device authority as a bypass around capability or page-table isolation.
- Revoking or quiescing device access before reusing pages for unrelated authority domains.

If a device reports a DMA error, completion status, or bus fault, that report is platform and device specific. It is not delivered as a precise CPU exception for the instruction that originally programmed the device.

## DMA Buffer Memory Types

Portable v0.1 drivers use these memory types:

| Buffer or register role | Memory type | Driver consequence |
| --- | --- | --- |
| Cacheable data buffer or descriptor ring | `NORMAL_COHERENT` | Requires cache maintenance and fences around DMA handoff. |
| Uncacheable data buffer or descriptor ring | `NORMAL_UNCACHEABLE` | Requires fences around handoff, but cache maintenance has no cache-line effect. |
| Device register or doorbell page | `DEVICE_ORDERED` | Accessed with `LD48` or `ST48`; not a DMA buffer. |

`NORMAL_COHERENT` buffers are preferred for CPU-intensive data. `NORMAL_UNCACHEABLE` buffers are preferred for small rings, polling areas, or device-visible memory that is frequently shared with hardware and rarely reused by the CPU.

`DEVICE_ORDERED` pages are for MMIO registers. Drivers must not treat device register windows as ordinary DMA buffers, capability storage, or executable memory.

## Ownership Model

Each DMA buffer region is in one of these software ownership states:

| State | CPU rule | Device rule |
| --- | --- | --- |
| CPU-owned | CPU may read or write according to capabilities and pages. | Device must not read or write the region. |
| Device-read | CPU must not modify the region until completion. | Device may read the region. |
| Device-write | CPU must not read or write the region until completion. | Device may write the region. |
| Bidirectional-device | CPU must not read or write the region until completion. | Device may read and write the region. |

The architecture does not enforce these states. They are mandatory driver policy for portable software.

CPU access while the device owns a coherent buffer is invalid software behavior unless the device-specific protocol explicitly defines a race-free shared status field and the driver uses the required fences and memory types for that field.

## Cache-line Discipline

Cache maintenance operates on 16-cell lines.

Portable drivers should allocate DMA buffers and descriptor rings so that:

- The buffer start is 16-cell aligned.
- The buffer size is a multiple of 16 cells.
- No unrelated CPU-owned object shares a cache line with a DMA-owned region.
- Capability slots that must retain valid tags do not share a DMA-overwritten line or slot.

If a driver cannot satisfy this alignment, it must use maintenance capabilities that intentionally cover the expanded cache-line range and must account for all objects in those lines. Device writes to a subrange may still clear capability tags for any overlapped 4-cell capability slot.

## CPU to Device DMA

For a device read from a `NORMAL_COHERENT` buffer, such as transmit data or CPU-written descriptors:

```text
CPU writes buffer or descriptors
FENCE
CACHE.CLEAN buffer_or_descriptor_range
FENCE
ST48 device doorbell or tail register
```

Required effects:

- The first `FENCE` makes older CPU stores available to cache maintenance.
- `CACHE.CLEAN` writes dirty payload and tag state back toward backing memory.
- The second `FENCE` orders the clean before the device-visible doorbell.
- The `DEVICE_ORDERED` doorbell tells the device it may read the buffer.

For a device read from a `NORMAL_UNCACHEABLE` buffer:

```text
CPU writes buffer or descriptors
FENCE
ST48 device doorbell or tail register
```

No cache maintenance is required because CPU cache copies are not allocated for the buffer. The `FENCE` is still required to order normal memory writes before the device doorbell.

After the doorbell, the region is device-owned until the device-specific completion rule returns ownership to the CPU.

## Device to CPU DMA

For a device write into a `NORMAL_COHERENT` buffer, such as receive data or completion records, the driver must first prevent dirty CPU cache state from later overwriting device output.

Before giving the buffer to the device:

```text
CPU stops using the buffer
FENCE
CACHE.INVAL buffer_range
FENCE
ST48 device doorbell or queue register
```

`CACHE.INVAL` is valid here only when the old CPU contents are disposable and the device will overwrite the region the driver intends to consume. If old CPU contents must be preserved for unwritten cells, the driver must use `CACHE.CLEANINVAL` instead or must split the buffer so preserved data is not in the DMA-owned line range.

After observing device completion:

```text
LD48 or interrupt observes device completion
FENCE
CACHE.INVAL buffer_range
FENCE
CPU reads buffer
```

Required effects:

- The first completion-side `FENCE` orders the observed completion before cache invalidation.
- `CACHE.INVAL` discards stale CPU cache copies and stale CPU tag state.
- The final `FENCE` orders the invalidation before CPU loads from the buffer.

For a device write into a `NORMAL_UNCACHEABLE` buffer:

```text
CPU stops using the buffer
FENCE
ST48 device doorbell or queue register
LD48 or interrupt observes device completion
FENCE
CPU reads buffer
```

No cache maintenance is required for uncacheable buffers. The fences still define ownership and ordering around device-visible state.

## Bidirectional DMA

For a `NORMAL_COHERENT` buffer that the device may both read and write during one ownership interval:

```text
CPU writes initial contents if any
FENCE
CACHE.CLEANINVAL buffer_range
FENCE
ST48 device doorbell or queue register
LD48 or interrupt observes device completion
FENCE
CACHE.INVAL buffer_range
FENCE
CPU reads final contents
```

`CACHE.CLEANINVAL` preserves CPU-written initial contents for the device and removes CPU cache copies before the device writes. The post-completion `CACHE.INVAL` removes any stale CPU copies before CPU consumption.

For `NORMAL_UNCACHEABLE` bidirectional buffers, the driver uses the same ownership boundaries but omits cache maintenance:

```text
CPU writes initial contents if any
FENCE
ST48 device doorbell or queue register
LD48 or interrupt observes device completion
FENCE
CPU reads final contents
```

## Capability Tags and DMA

Non-tag-aware DMA or external writes clear tags for every overlapped naturally aligned 4-cell capability slot in backing memory.

Rules:

- DMA reads observe payload cells only.
- DMA reads do not observe architectural capability tags.
- DMA writes cannot create valid capability tags.
- DMA writes clear backing-memory tags for every capability slot they overlap.
- A device that copies capability payload bits through DMA copies only integer data unless a future tag-aware I/O extension says otherwise.

For `NORMAL_COHERENT` buffers, stale CPU cache copies may still contain old valid tags after a device write. The CPU must invalidate the range before it can reliably observe the device-written payload and the cleared backing-memory tags.

For `NORMAL_UNCACHEABLE` buffers, the CPU does not hold cache copies, so a `CLC` after the required completion fence observes the backing-memory tag state directly.

Portable drivers should not place live capabilities in DMA-write buffers. If a device must receive pointer-like values, the driver should pass device-defined integer addresses or handles, not architectural capabilities.

## Descriptor Rings and Doorbells

A typical noncoherent queue uses:

- A normal memory descriptor ring.
- A normal memory data buffer set.
- `DEVICE_ORDERED` device registers for head, tail, status, and doorbells.

CPU-produced descriptors use the CPU-to-device sequence before updating the device tail or doorbell.

Device-produced completion descriptors use the device-to-CPU completion sequence before the CPU reads the completion entry.

Drivers should keep CPU-produced and device-produced descriptors on separate 16-cell lines when possible. Mixed ownership within one cache line forces conservative `CACHE.CLEANINVAL`/`CACHE.INVAL` use and can discard or expose unrelated state.

## Page Reuse and Revocation

Before a page or buffer previously used for DMA is returned to a general allocator, mapped into another protection domain, or reused for capability-bearing data, privileged software must ensure:

- The device can no longer write the range.
- Any outstanding DMA using the range has completed or has been cancelled.
- Any required `NORMAL_COHERENT` invalidation has completed.
- Backing-memory capability tags reflect any non-tag-aware device writes.
- The new owner receives authority only through normal capability and page-table mechanisms.

For conservative page lifecycle transitions after coherent DMA:

```text
quiesce device access
FENCE
CACHE.INVAL page_range
FENCE
scrub or initialize page if required by the new owner
reuse or remap page
```

`CACHE.INVAL` is used after device writes so stale CPU cache contents are not written back over device output or over backing-memory tag clears. If CPU-owned dirty contents must be preserved before a later device read, the driver must use the CPU-to-device or bidirectional handoff sequence before giving the range to the device.

If a page-table entry or memory type for the page changes during reuse, the TLB and page-table update rules from E09-S03 and the fence rules from E08-S04 also apply.

## Coherent I/O Deferred

v0.1 does not define:

- Device snooping of CPU L1 or L2 caches.
- DMA writes that update or invalidate CPU cache lines automatically.
- Device participation in MESI ownership or the CPU global store order.
- I/O page-table walkers or an architectural IOMMU.
- Address-translation services for devices.
- Tag-aware coherent DMA.
- Devices that create, preserve, or transfer valid architectural capability tags.

A future coherent-I/O profile must define how device transactions interact with CPU cache state, tag state, memory ordering, page tables, and capability authority. Until then, portable v0.1 software must assume all DMA is noncoherent.

## Faults and Error Reporting

CPU faults from cache maintenance, ordinary MMIO loads/stores, translation, page memory type, and capability checks are defined by E09-S06, E09-S07, and E10-S05.

Device DMA errors are not precise CPU instruction faults. A platform may report them through:

- Device status registers.
- External interrupts.
- Platform error CSRs.
- Firmware-defined error logs.

A DMA error does not retroactively fault the CPU store that programmed the device. Drivers must check the relevant device or platform completion status before trusting DMA results.

## Out of Scope for This Story

- Cache maintenance instruction internals: E10-S05.
- Final `FENCE`, `FENCE.I`, and `SFENCE.VM` encodings: E08-S04.
- MMIO register layout for any concrete device.
- Platform interrupt-controller behavior.
- IOMMU, device page tables, and device-side capability enforcement.
- Coherent I/O and tag-aware I/O extensions.

## Verification Notes

Minimum conformance checks for later simulator, firmware, OS, and RTL work:

- Device reads do not observe dirty CPU cache data until `CACHE.CLEAN` has completed.
- Device writes do not invalidate stale CPU cache copies automatically.
- CPU reads after device writes require completion observation, `FENCE`, `CACHE.INVAL`, and `FENCE` for `NORMAL_COHERENT` buffers.
- CPU writes before device reads require `FENCE`, `CACHE.CLEAN`, and `FENCE` for `NORMAL_COHERENT` buffers.
- `NORMAL_UNCACHEABLE` DMA buffers require fences but no cache maintenance effect.
- `DEVICE_ORDERED` register accesses are used for device doorbells and status.
- Non-tag-aware DMA writes clear backing-memory tags for every overlapped capability slot.
- Invalidating a coherent DMA-written buffer makes stale CPU tags unusable.
- Cache-line sharing between CPU-owned and DMA-owned objects is rejected by driver conformance tests or handled with expanded-range maintenance.
- Coherent I/O behavior is not assumed by any v0.1 driver sequence.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| I/O is outside CPU cache coherence for v0.1. | Met. |
| DMA/device accesses are noncoherent. | Met. |
| Drivers must use cache maintenance and fences around DMA. | Met. |
| Non-tag-aware DMA clears capability tags on overwrite. | Met. |
| Coherent I/O is explicitly deferred. | Met. |

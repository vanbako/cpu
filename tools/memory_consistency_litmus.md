# Memory Consistency Litmus Catalog

Story: E15-S05

Status: Complete

This catalog lists verification scenarios for the v0.1 composed memory, capability, translation, cache, DMA, and ordering contract.

## Effective Access

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-001 | `LD48` through invalid authorizing capability to an unmapped page. | `CAPABILITY_TAG_FAULT`; no page walk result is architecturally selected. |
| MEM-LIT-002 | `CLC` to an odd or 2-cell-only aligned capability slot. | `ALIGN_FAULT`; no memory read, destination update, or reservation effect. |
| MEM-LIT-003 | Aligned `CSC` through capability lacking `SC` to a writable page. | `CAPABILITY_PERMISSION_FAULT`; memory payload and tag unchanged. |
| MEM-LIT-004 | `CSC` stores valid local capability through destination lacking `SL`. | `CAPABILITY_LOCAL_STORE_FAULT`; memory payload and tag unchanged. |
| MEM-LIT-005 | Ordinary `LD48` overlaps protected return-stack storage through `DDC`. | `RETURN_STACK_PERMISSION_FAULT`; no data read is visible. |
| MEM-LIT-006 | User-mode `LD48` through valid authority to `U=0, R=1` page. | `PAGE_FAULT`; `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`. |
| MEM-LIT-007 | `LL48` to `DEVICE_ORDERED` memory. | `ACCESS_FAULT`; no reservation is created. |
| MEM-LIT-008 | `CACHE.CLEAN` over `DEVICE_ORDERED` range. | `ACCESS_FAULT`; no required maintenance completion. |

## Tags and Coherence

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-020 | Core 0 `CSC` stores a valid capability; Core 1 later `CLC`s after visibility. | Core 1 observes payload and tag from the same coherent visibility point. |
| MEM-LIT-021 | Core 0 `ST48` writes either half of a capability slot; Core 1 later `CLC`s after visibility. | Core 1 observes the tag clear with the corresponding payload state. |
| MEM-LIT-022 | Same-core buffered `ST48` overlaps a later `CLC` to the same slot. | `CLC` observes the local tag clear through store-buffer forwarding. |
| MEM-LIT-023 | Same-core buffered `CSC` is followed by `CLC` to the same slot. | `CLC` observes the local payload and tag together. |
| MEM-LIT-024 | `SC48` succeeds on cells overlapping a capability slot. | Payload write and tag clear become visible at one coherent visibility point. |
| MEM-LIT-025 | `SC48` fails after access checks pass. | Destination result is `1`; memory payload and tags unchanged; no global store visibility point. |

## TSO and Fences

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-040 | Store buffering: Core 0 `ST48 X=1; LD48 Y`, Core 1 `ST48 Y=1; LD48 X`. | Both loads may read old values under TSO. |
| MEM-LIT-041 | Store buffering with `FENCE` between each store and load. | Both loads reading old values is forbidden. |
| MEM-LIT-042 | Core 0 `ST48 A; ST48 B`; Core 1 observes `B`. | If Core 1 observes `B`, it must also be able to observe the earlier `A` under the global store order. |
| MEM-LIT-043 | `FENCE` before `CACHE.CLEAN` in CPU-to-device DMA sequence. | Older CPU stores are globally visible to maintenance before device doorbell. |
| MEM-LIT-044 | `FENCE` after `CACHE.INVAL` in device-to-CPU DMA sequence. | Younger CPU loads occur after invalidation completes. |

## LL/SC Reservations

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-060 | Successful `LL48`, then faulting `LL48` to another address, then `SC48` to original word. | `SC48` fails after access checks; faulting `LL48` cleared the original reservation. |
| MEM-LIT-061 | Successful `LL48`, then same-core `ST48` overlaps reservation granule, then `SC48`. | `SC48` fails. |
| MEM-LIT-062 | Successful `LL48`, then other-core store overlaps reservation granule before `SC48`. | Later `SC48` fails unless a new successful `LL48` occurs. |
| MEM-LIT-063 | Successful `LL48`, then `CACHE.INVAL` covering the line, then `SC48`. | `SC48` fails; invalidation clears affected reservations. |
| MEM-LIT-064 | Successful `LL48`, then user-mode `SFENCE.VM` faults, then handler tests reservation. | Trap entry clears the reservation. |
| MEM-LIT-065 | Constrained loop with no conflicts, no clear events, and normal coherent memory. | Eventually one `SC48` succeeds within the implementation-documented bound. |

## Translation and Instruction Visibility

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-080 | Update PTE, execute matching local `SFENCE.VM`, then access through updated mapping. | Younger local access cannot use stale local TLB entry or stale cached page-walk failure. |
| MEM-LIT-081 | Reuse ASID on another core without remote shootdown. | Invalid software behavior; stale translations may be observed until shootdown completes. |
| MEM-LIT-082 | Change global mapping, invalidate with `SFENCE.VM.ASID` only. | Invalid software sequence; global entries are not invalidated by ASID-only form. |
| MEM-LIT-083 | Store new code in normal coherent memory, execute `FENCE; FENCE.I`, then fetch locally. | Younger local fetch cannot use stale instruction bytes. |
| MEM-LIT-084 | DMA writes code into `NORMAL_COHERENT`; CPU executes without DMA completion invalidation and `FENCE.I`. | Invalid software sequence; stale payload, tags, or instruction bytes may be observed. |

## DMA and Memory Types

| ID | Scenario | Expected result |
| --- | --- | --- |
| MEM-LIT-100 | Device reads `NORMAL_COHERENT` buffer without prior `FENCE; CACHE.CLEAN; FENCE`. | Invalid driver sequence; device may observe stale backing memory. |
| MEM-LIT-101 | Device writes `NORMAL_COHERENT` buffer, CPU reads without `FENCE; CACHE.INVAL; FENCE`. | Invalid driver sequence; CPU may observe stale payload or stale tags. |
| MEM-LIT-102 | Device writes `NORMAL_UNCACHEABLE` buffer, CPU observes completion then `FENCE`, then reads. | CPU observes backing-memory payload and tag state without cache maintenance. |
| MEM-LIT-103 | Non-tag-aware DMA overwrites cells in a capability slot. | Backing-memory tag for every overlapped 4-cell capability slot is cleared. |
| MEM-LIT-104 | Driver shares CPU-owned object in the same 16-cell cache line as DMA-owned subrange. | Invalid or requires expanded-range maintenance and ownership accounting for the whole line. |
| MEM-LIT-105 | CPU uses `LL48`/`SC48` lock in DMA-owned or uncacheable/device memory. | Invalid portable synchronization; access raises `ACCESS_FAULT` for unsupported memory types. |

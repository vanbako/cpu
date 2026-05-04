# E08-S03: TSO-like Memory Model

Story: E08-S03

Status: Complete

Normative source: `design.md`, section 11.2

Prerequisites:

- `spec/E01-S01-cell-address-model.md`
- `spec/E10-S01-cache-hierarchy.md`

Related sources:

- `spec/E03-S04-memory-tag-rules.md`
- `spec/E10-S02-cache-line-size.md`
- `spikes/E14-S04-capability-tag-cache-model.md`

## Decision

CPU v0.1 uses a TSO-like coherent, multi-copy-atomic memory model for CPU accesses to normal coherent cacheable memory.

The model is defined over cell-addressed memory. There are no byte lanes in the architectural memory model.

The shared L2 is the CPU coherence point. The exact cache-coherence state machine is defined by E10-S03, but it must implement the architectural visibility and ordering rules in this story.

## Scope

This story covers CPU memory ordering for:

- `LD48`
- `ST48`
- `CLC`
- `CSC`
- `LL48`
- `SC48`
- Future v0.1-compatible atomic read-modify-write operations, if added
- `FENCE` as a data-memory ordering operation

This story does not define:

- Exact `LL48` and `SC48` reservation behavior: E08-S01 and E08-S02.
- Detailed fence encodings and maintenance interactions: E08-S04.
- Page memory-type encodings: E09-S06.
- The MESI-like coherence state machine: E10-S03.
- Noncoherent DMA maintenance sequences: E10-S04 and E10-S05.

## Memory Operation Granularity

| Operation | Access granularity | Visibility unit |
| --- | ---: | --- |
| `LD48` | 2 aligned cells | One atomic 48-bit load |
| `ST48` | 2 aligned cells | One atomic 48-bit store plus any required tag clear |
| `CLC` | 4 aligned cells plus tag | One atomic capability-slot load |
| `CSC` | 4 aligned cells plus tag | One atomic capability-slot store |
| `LL48` | 2 aligned cells | One atomic 48-bit load with reservation side effect |
| Successful `SC48` | 2 aligned cells | One atomic 48-bit store plus reservation result |
| Failed `SC48` | 2 aligned cells | No memory store |

Aligned memory operations are not torn. Another core cannot observe half of one `ST48`, half of one `CSC`, or a capability payload and tag from different `CSC` visibility points.

## Coherence and Multi-copy Atomicity

For normal coherent cacheable memory:

- All stores become visible through one global CPU store order.
- The global CPU store order is consistent with each core's program order for stores.
- Once a store becomes globally visible, it is visible to all cores at the same architectural point.
- Two cores cannot permanently disagree about the order in which two stores became visible.
- A load that reads from coherent memory observes the latest globally visible store to the accessed cells, except when it forwards from an older store in the same core's store buffer.

This is multi-copy atomic from the CPU's point of view. Devices and DMA agents are not participants in this global CPU store order.

## Store-buffer Model

Each core may implement a FIFO store buffer.

Architectural rules:

- A store may retire before it has become globally visible.
- Stores from one core become globally visible in program order.
- A younger store from the same core cannot pass an older store in the global CPU store order.
- A younger load from the same core may execute before an older store has become globally visible.
- A load must observe older same-core buffered stores to the same accessed cells or capability slot before it observes global memory.
- `FENCE` drains older stores to global visibility before younger data-memory operations proceed.

Store-buffer entries carry all architectural effects of the store:

- `ST48` buffered state includes the two written cells and any capability-slot tag clear.
- `CSC` buffered state includes the four payload cells and the capability tag.
- Successful `SC48` buffered state includes the two written cells and any capability-slot tag clear.

For a same-core load after older buffered stores, the result must be as if those older same-core stores occur before the load. If a same-core buffered `ST48` overlaps a later `CLC` to the same capability slot, the `CLC` must observe the local tag clear. If a same-core buffered `CSC` is followed by a `CLC` to the same slot, the `CLC` must observe the local payload and tag.

## Load Ordering

For normal coherent cacheable memory:

- Loads are not reordered with older loads.
- Loads are not reordered with older fences.
- Loads may be satisfied from older same-core buffered stores.
- Loads that do not forward from the store buffer read from the globally visible coherent state.
- A load cannot read from a younger store in program order.

`LD48` returns only cell data. It never returns a capability tag.

`CLC` returns the capability payload and tag from one coherent visibility point, plus any applicable older same-core buffered store effects.

## Store Ordering

For normal coherent cacheable memory:

- Stores are not reordered with older stores.
- Stores are not reordered with older fences.
- Stores may be buffered before global visibility.
- Stores become globally visible only through the CPU coherence point.
- The visibility point of a store includes all payload and tag effects of that store.

`ST48` and successful `SC48` visibility include:

- The two written cells.
- Clearing the tag for the overlapped 4-cell capability slot, if any.

`CSC` visibility includes:

- The four written payload cells.
- The written capability tag.

Another core must not observe a `CSC` payload without the matching `CSC` tag, nor the matching `CSC` tag without the payload.

## Atomic Operation Ordering

Atomic operations participate in the same coherent memory order as ordinary loads and stores.

Baseline rules:

- `LL48` is ordered as a load.
- Failed `SC48` performs no memory store and has no global store visibility point.
- Successful `SC48` is ordered as a store.
- A successful `SC48` is atomic with respect to other stores to the same aligned 48-bit word.
- Future single-instruction atomic read-modify-write operations must appear as one indivisible global memory-order event.

The reservation granule, success/failure result, progress guarantee, and reservation-clear events are defined by E08-S01 and E08-S02.

## Fence Ordering

`FENCE` is the data-memory ordering primitive for this model.

Minimum architectural rule:

- All older data-memory operations become complete before any younger data-memory operation after the `FENCE` is allowed to execute.

For a core with a store buffer, `FENCE` drains older stores to global visibility before younger loads, stores, or atomics proceed.

In TSO, `FENCE` is primarily needed for:

- Ordering an older store before a younger load.
- Creating explicit synchronization boundaries for device, DMA, and cache-maintenance sequences.
- Making algorithms that require a full memory barrier portable across implementation details.

`FENCE.I` and `SFENCE.VM` are not defined by this story. They are specified by E08-S04.

## Capability Tag Visibility

Capability tag visibility follows the same ordering rules as the payload cells associated with the tag.

Rules:

- Tag bits participate in coherent visibility.
- A `CSC` publishes payload and tag together at one global visibility point.
- A `CLC` observes payload and tag from one coherent visibility point, after applying older same-core buffered store effects.
- A `ST48` or successful `SC48` publishes its payload write and required tag clear together at one global visibility point.
- The tag clear from `ST48` or successful `SC48` is ordered like the store itself.
- A `FENCE` that orders data stores also orders capability payload writes and tag updates.

Consequences:

- Core 1 cannot observe a valid tag for stale capability payload after Core 0's `CSC` is globally visible.
- Core 1 cannot observe new capability payload with an old tag after Core 0's `CSC` is globally visible.
- Core 1 cannot observe an old valid tag for a capability slot after Core 0's overlapping `ST48` or successful `SC48` tag clear is globally visible.

## Device, DMA, and Noncoherent Exceptions

The TSO-like model applies to CPU accesses to normal coherent cacheable memory. It does not make devices coherent participants in the CPU store order.

Device and DMA exceptions:

- DMA/device writes are not multi-copy atomic with respect to CPU cores.
- DMA/device writes do not participate in the global CPU store order.
- Non-tag-aware DMA or external writes clear tags in backing memory for every overlapped capability slot.
- CPU caches may retain stale payload and stale tags after noncoherent DMA writes.
- Drivers must use cache maintenance and fences around DMA buffers before CPU reuse.
- Device memory may have side effects and ordering requirements that are stronger or different from normal coherent memory.

E09-S06 defines normal uncacheable and device-ordered page types. E08-S04, E10-S04, and E10-S05 define the required fence and cache-maintenance sequences.

Instruction fetch is also outside the data TSO model. Code written through data stores becomes reliably visible to instruction fetch only after the `FENCE.I` sequence defined by E08-S04.

## Litmus Expectations

For normal coherent cacheable memory, with initial `X=0` and `Y=0`:

### Store Buffering

```text
Core 0: ST48 X = 1; LD48 r0 = Y
Core 1: ST48 Y = 1; LD48 r1 = X
```

Allowed outcome:

```text
r0 = 0, r1 = 0
```

Rationale: each core's younger load may execute before its older store becomes globally visible.

With `FENCE` between each store and load:

```text
Core 0: ST48 X = 1; FENCE; LD48 r0 = Y
Core 1: ST48 Y = 1; FENCE; LD48 r1 = X
```

Forbidden outcome:

```text
r0 = 0, r1 = 0
```

### Message Passing

```text
Core 0: ST48 X = 1; ST48 Y = 1
Core 1: LD48 r0 = Y; LD48 r1 = X
```

Forbidden outcome:

```text
r0 = 1, r1 = 0
```

Rationale: stores from Core 0 become globally visible in program order.

### Capability Publication

```text
Core 0: CSC CAP = valid_cap
Core 1: CLC c0 = CAP
```

If Core 1 observes the new payload from `CSC`, it must observe the matching tag from that same `CSC`. If Core 1 observes the valid tag from `CSC`, it must observe the matching payload from that same `CSC`.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Stores from one core become globally visible in program order.
- The store-buffering litmus without fences allows both loads to read zero.
- The store-buffering litmus with `FENCE` forbids both loads reading zero.
- The message-passing litmus forbids observing `Y=1` and then `X=0`.
- Same-core load after same-address store can forward from the local store buffer.
- Same-core `CLC` after buffered `CSC` observes the buffered payload and tag.
- Same-core `CLC` after buffered overlapping `ST48` observes the local tag clear.
- Cross-core `CSC` visibility publishes payload and tag together.
- Cross-core overlapping `ST48` or successful `SC48` visibility publishes payload and tag clear together.
- Failed `SC48` has no global store visibility point.
- Successful `SC48` is globally ordered as a store.
- DMA overwrite requires cache invalidation before CPU reuse to observe memory payload and tag clear.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The memory model is coherent and multi-copy atomic. | Met for normal coherent cacheable CPU memory. |
| Store-buffer ordering behavior is described. | Met. |
| Load, store, atomic, and fence ordering rules are specified. | Met. |
| Capability tag visibility follows memory ordering rules. | Met. |
| Device memory exceptions are called out. | Met. |

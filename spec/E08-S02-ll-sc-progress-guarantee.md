# E08-S02: LL/SC Progress Guarantee

Story: E08-S02

Status: Complete

Normative source: `design.md`, section 11.1

Prerequisite:

- `spec/E08-S01-ll48-sc48.md`

Related sources:

- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E07-S06-nested-interrupt-rules.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E08-S04-fence-instructions.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E10-S03-cpu-coherence-protocol.md`
- `spec/E10-S05-cache-maintenance-operations.md`

## Decision

CPU v0.1 requires forward progress for constrained `LL48`/`SC48` retry loops on normal coherent cacheable memory.

An implementation may fail `SC48` spuriously, but it must not fail every `SC48` forever when the executing core repeatedly retries a constrained loop without conflicting stores, repeated interruptions, context switches, cache invalidations, or reservation-tracking loss.

The progress bound is implementation-defined, finite, and mandatory to document. Portable software may rely on eventual success under the constrained-loop rules in this story, but it must not rely on a numeric bound unless the platform profile publishes one.

## Reservation Identity

Each core has at most one active reservation.

A reservation records at least:

| Field | Meaning |
| --- | --- |
| `valid` | Whether the core has an active reservation. |
| `word_pa` | The aligned physical 48-bit word reserved by the successful `LL48`. |
| `granule` | The implementation reservation granule containing `word_pa`. |
| `memory_type` | The page memory type used by the successful `LL48`, which must be normal coherent cacheable memory. |

When translation is enabled, `LL48` creates the reservation after successful translation and access checks. The reserved word is identified by physical cell address, not by virtual address or ASID.

`SC48` performs all access checks before testing the reservation, as required by E08-S01. After those checks, `SC48` matches the reservation if the translated physical aligned word equals `word_pa` and the reservation remains valid.

Consequences:

- A virtual alias that translates to the same physical aligned word may match the reservation if no clear event has occurred and all `SC48` access checks pass.
- A virtual address that translates to a different physical aligned word does not match, even if its virtual cell address equals the original `LL48` effective address.
- `SATP`, active ASID, and local translation-maintenance operations clear reservations as defined below, so ordinary context switches do not carry reservations across address spaces.

## Reservation Granule

The reservation granule is the implementation-defined conflict region described by E08-S01.

Rules:

- The granule must contain the reserved aligned 48-bit word.
- The granule must be at least the reserved word.
- The granule must not exceed the containing 16-cell cache line in v0.1.
- The implementation must document whether it tracks word, sub-line, or full-line reservations.

A conflicting store is any CPU store whose written cells overlap the reservation granule.

If an implementation chooses a cache-line reservation granule, any CPU store to the same 16-cell line conflicts. If it chooses a word reservation granule, only stores overlapping the reserved aligned 48-bit word conflict.

## Creating and Replacing Reservations

A successful `LL48`:

- Clears any previous reservation held by the current core.
- Creates a new valid reservation for the translated physical aligned word.
- Records the implementation granule that contains that word.

A faulting `LL48`:

- Clears any previous reservation held by the current core.
- Creates no new reservation.
- Performs no memory load and writes no destination register, as required by E08-S01.

This rule prevents a failed address probe from preserving an older unrelated reservation.

## Store-conditional Consumption

A retired `SC48` always consumes the current core's reservation.

| `SC48` outcome | Reservation effect |
| --- | --- |
| Success, `Dr=0` | Reservation is cleared. |
| Non-trapping failure, `Dr=1` | Reservation is cleared. |
| Synchronous fault | Reservation is cleared by trap entry before the handler executes. |

Software must execute a new successful `LL48` before retrying after any `SC48` result.

## Required Clear Events

The following events clear an active reservation on the affected core.

| Event | Scope | Required effect |
| --- | --- | --- |
| Cold reset or secondary-core startup | Target core | Reservation state starts invalid. |
| Successful `LL48` | Executing core | Replaces any older reservation with the new one. |
| Faulting `LL48` | Executing core | Clears any older reservation and creates none. |
| Retired `SC48` success or non-trapping failure | Executing core | Consumes the reservation. |
| Faulting `SC48` | Executing core | Clears by synchronous trap entry. |
| Any synchronous exception or software trap | Executing core | Clears before trap-handler execution. |
| Any delivered interrupt | Target core | Clears before interrupt-handler execution. |
| Committed `IRET` | Executing core | Clears before returning to the restored context. |
| Committed explicit write to `SR`, `SATP`, or active ASID state | Executing core | Clears before younger instruction execution. |
| Committed `SFENCE.VM` form | Executing core | Clears before the instruction retires. |
| `WFI` entry | Executing core | Clears before entering the wait state. |
| Same-core store overlapping the granule | Executing core | Clears before any younger `SC48` can test the reservation. |
| Other-core store overlapping the granule | Reserving core | Clears before a later `SC48` on the reserving core can succeed. |
| Coherence invalidation of the reserved granule | Invalidated core | Clears when the local coherent copy or reservation-tracking state is invalidated. |
| L1 data-cache eviction of the reserved granule | Evicting core | Clears when the local line or reservation-tracking state is discarded. |
| Inclusive L2 eviction requiring L1 invalidation | Invalidated cores | Clears reservations for invalidated granules. |
| `CACHE.INVAL` or `CACHE.CLEANINVAL` covering the granule | All affected cores | Clears reservations for invalidated lines before the maintenance operation retires. |

For same-core stores after the successful `LL48`, the reservation is cleared when the store commits into the core's architectural memory path or store buffer, not only when the store later becomes globally visible. A younger `SC48` cannot succeed using a reservation that was invalidated by an older same-core store.

If an older same-core buffered store overlaps the granule and can become globally visible after the `LL48`, the implementation must either delay the `LL48` until the older overlapping store is globally visible, or clear the reservation when that older store drains. A reservation cannot survive an overlapping same-core store visibility point merely because the store entered the store buffer before the `LL48`.

For other-core stores, the coherence protocol may clear the reservation when it sends the invalidation, when it receives the invalidation acknowledgment, or at the store's global visibility point. The required architectural result is that if the other-core store is ordered between the successful `LL48` load and the attempted `SC48`, the `SC48` cannot succeed using the stale reservation.

## Events That Do Not Clear by Themselves

These events do not clear a reservation solely by architectural definition:

| Event | Reservation effect |
| --- | --- |
| Integer or capability register arithmetic | Does not clear. |
| Branches, calls, and returns that do not trap | Do not clear, except for their ordinary protected return-stack side effects if those side effects store to the reservation granule. |
| `PAUSE` | Does not clear. |
| `FENCE` | Does not clear by itself. Older stores ordered by the fence may already have cleared. |
| `FENCE.I` | Does not clear by itself. |
| Same-core loads that do not fault | Do not clear by themselves. |
| Other-core coherent read-only requests | Do not clear by themselves unless they cause eviction or invalidation of the local reservation-tracking state. |
| `CACHE.CLEAN` covering the granule | Does not have to clear unless the implementation invalidates or discards reservation-tracking state while performing the clean. |

An implementation may conservatively clear reservations for additional internal reasons only if it still satisfies the constrained-loop progress guarantee. It must not use unrelated read-only traffic, ordinary branch execution, or `PAUSE` as an unbounded source of spurious failure.

## Interrupt and Context-switch Rules

Reservations are not part of software context.

Trap and interrupt entry clear the interrupted context's reservation before handler execution. If the handler later executes `SC48` without first executing a successful `LL48`, that `SC48` must return failure after passing access checks.

An interrupt handler may use `LL48`/`SC48` for its own synchronization. That handler reservation is cleared by any nested trap or interrupt, by a consumed `SC48`, and by `IRET` before returning to the interrupted context.

A scheduler must never save and restore reservation state as part of a thread context. If a context switch did not include a trap, interrupt, `SATP` or active-ASID write, explicit `SR` write, `SFENCE.VM`, or another required clear event, privileged software must execute one of those reservation-clearing operations before resuming a different software context on the same core.

This rule prevents one thread's successful `LL48` from enabling another thread's `SC48`.

## Cache and Coherence Rules

Reservations participate in the normal coherent cacheable CPU memory system.

Minimum requirements:

- `LL48` obtains a coherent readable copy of the reservation granule.
- `SC48` success requires the core to obtain store authority for the target line before the store becomes globally visible.
- A conflicting store from any CPU core clears reservations for that granule according to the serialized coherence order.
- A failed `SC48` performs no coherent store and creates no invalidation.
- Payload writes and tag clears from a successful `SC48` become visible at the same coherent visibility point required by E08-S03 and E10-S03.

A coherence race between a reserving core's `SC48` and another core's store is resolved by the L2 coherence point:

- If the `SC48` store is serialized first and all `SC48` checks pass, the `SC48` may succeed.
- If the other store is serialized first and overlaps the reservation granule, the `SC48` must fail unless the core executes a new successful `LL48`.
- The two stores must not both appear to have succeeded using the same reservation state.

Read-only sharing does not make a store conflict. Another core may read the reserved line without clearing the reservation unless that read causes the implementation to discard local reservation-tracking state. Such discards are allowed only within the progress constraints below.

Noncoherent DMA and devices do not participate in CPU LL/SC reservations. A noncoherent DMA write is not guaranteed to clear a CPU reservation by itself. Software must not run portable LL/SC synchronization on buffers owned by noncoherent DMA, and DMA ownership transfers must use the cache-maintenance and fence sequences from E10-S04 and E10-S05.

## Constrained-loop Progress

A constrained LL/SC retry loop is a loop that satisfies all of these conditions:

1. Each attempt executes one successful `LL48` followed by one `SC48` to the same physical aligned 48-bit word.
2. The target memory remains normal coherent cacheable for the whole attempt.
3. The `LL48` and `SC48` access checks would pass for every attempt.
4. The instruction sequence between `LL48` and `SC48` is finite and within the implementation's documented constrained-loop limit.
5. The sequence between `LL48` and `SC48` contains only integer register operations, non-memory capability register operations, branches, and `PAUSE`.
6. The sequence contains no additional load, store, cache maintenance, `SFENCE.VM`, `WFI`, CSR/CCSR write, syscall, breakpoint, or instruction that traps.
7. On `SC48` failure, software retries by executing a fresh `LL48` before the next `SC48`.

Under these loop constraints, a conforming implementation must guarantee that at least one retry eventually succeeds if all of these environmental conditions hold:

- No other CPU core performs a conflicting store to the reservation granule.
- No cache maintenance operation invalidates the reservation granule.
- No interrupt, synchronous trap, debug entry, context switch, reset, or low-power wait clears the reservation.
- The core continues to receive fair instruction execution and memory-system service.
- The cache hierarchy does not repeatedly evict or invalidate the reservation granule for reasons unrelated to conflicting stores.

Spurious `SC48` failure is allowed, but only within this progress guarantee. An implementation must not choose a policy that can make a constrained loop fail forever in the absence of the listed clear events.

If a clear event occurs, the progress guarantee restarts after software executes the next successful `LL48` under the constrained-loop and environmental conditions.

## Software Guidance

Portable lock and atomic-update code should keep the active reservation window short.

Recommended shape:

```text
retry:
    LL48  old, Ca, Di
    ... bounded register-only computation ...
    SC48  rc, new, Ca, Di
    TST   rc
    Bcc.NE retry
```

Software should not place ordinary stores, cache maintenance, system calls, `WFI`, or translation-maintenance instructions between `LL48` and `SC48`.

`PAUSE` is safe as a spin-wait hint, but it is normally used after a failed `SC48` and before the next `LL48`, not inside the active reservation window.

If software needs ordering beyond the load-like behavior of `LL48` and store-like behavior of successful `SC48`, it must use the `FENCE` rules from E08-S03 and E08-S04. `FENCE` does not preserve a reservation that was already cleared by an older store or another clear event.

## Out of Scope for This Story

- `LL48` and `SC48` opcode encodings: E04-S06.
- Base access checks, result codes, and tag-clear behavior: E08-S01.
- Full memory-ordering litmus behavior: E08-S03.
- Fence instruction semantics beyond reservation interaction: E08-S04.
- Fairness of lock algorithms under contention.
- LL/SC behavior for noncoherent, uncacheable, or device memory.
- Debug halt details beyond the requirement that future debug entry must not preserve another context's reservation.

## Verification Notes

Minimum conformance checks for later simulator, OS, and RTL work:

- Reset and secondary-core startup leave no active reservation.
- A successful `LL48` creates one reservation and replaces any previous reservation on the same core.
- A faulting `LL48` clears any previous reservation and creates none.
- Successful `SC48` consumes the reservation.
- Failed non-trapping `SC48` consumes the reservation.
- `SC48` after trap or interrupt entry fails unless preceded by a new successful `LL48`.
- `IRET` clears any handler-created reservation before returning.
- A committed `SATP`, active-ASID, or explicit `SR` write clears the current core's reservation.
- A committed `SFENCE.VM` form clears the current core's reservation.
- `FENCE`, `FENCE.I`, and `PAUSE` do not clear reservations by themselves.
- A same-core store overlapping the reservation granule makes a younger `SC48` fail.
- Another core's store overlapping the reservation granule makes a later `SC48` fail.
- Another core's read-only access does not by itself force `SC48` failure.
- `CACHE.INVAL` and `CACHE.CLEANINVAL` covering the reserved line clear reservations on affected cores.
- L1 eviction or inclusive L2 invalidation of the reserved granule clears the reservation.
- A constrained retry loop eventually observes one `SC48` success when no clear event or conflicting store occurs.
- Spurious failures are finite under the constrained-loop progress test.
- Noncoherent DMA writes are not modeled as reservation-clearing coherent events.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Progress is guaranteed absent conflicting stores and repeated interruptions. | Met: constrained loops must eventually succeed without conflicting stores, repeated traps/interrupts, context switches, cache invalidations, or reservation loss. |
| Events that clear reservations are listed. | Met. |
| Context switch and interrupt effects on reservations are specified. | Met: trap/interrupt entry, `IRET`, context switches, and relevant privileged state changes clear reservations. |
| Cache eviction and coherence invalidation behavior is defined. | Met. |

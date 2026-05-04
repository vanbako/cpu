# E12-S05: Extended Performance Counters

Story: E12-S05

Status: Complete

Normative source: `design.md`, section 15

Prerequisites:

- `spec/E02-S03-extended-csr-space.md`
- `spec/E12-S04-mandatory-counters.md`

Related sources:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E08-S01-ll48-sc48.md`
- `spec/E08-S02-ll-sc-progress-guarantee.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E10-S01-cache-hierarchy.md`
- `spec/E12-S01-debug-halt-behavior.md`
- `spec/E13-S03-hazard-handling.md`

## Decision

CPU v0.1 assigns eight per-core extended performance monitor counters, `PMC0-PMC7`, and defines `PERFSEL` as the kernel-only selector and configuration window for those counters.

`PMC0-PMC7` are generic 48-bit event counters. They are not permanently tied to one event each. `PERFSEL` binds each `PMC` slot to a reserved event selector, so more architectural event names can be reserved than there are simultaneous counters.

The architectural event selector namespace reserves stable names for:

- I-cache misses.
- D-cache misses.
- L2 misses.
- ITLB misses.
- DTLB misses.
- Branch mispredicts.
- Traps taken.
- Non-trapping `SC48` failures.
- Capability faults.

An implementation may support any subset of the reserved events. Unsupported event selectors are handled by `WARL` readback and never silently count a different named event.

## Counter CSRs

E12-S05 assigns the `PMC0-PMC7` CSRs reserved by E02-S03:

| CSR number | Name | Access | Reset | Meaning |
| ---: | --- | --- | ---: | --- |
| `0x40` | `PMC0` | K `RW` | `0` | Performance monitor counter 0. |
| `0x41` | `PMC1` | K `RW` | `0` | Performance monitor counter 1. |
| `0x42` | `PMC2` | K `RW` | `0` | Performance monitor counter 2. |
| `0x43` | `PMC3` | K `RW` | `0` | Performance monitor counter 3. |
| `0x44` | `PMC4` | K `RW` | `0` | Performance monitor counter 4. |
| `0x45` | `PMC5` | K `RW` | `0` | Performance monitor counter 5. |
| `0x46` | `PMC6` | K `RW` | `0` | Performance monitor counter 6. |
| `0x47` | `PMC7` | K `RW` | `0` | Performance monitor counter 7. |

User-mode reads or writes of `PMC0-PMC7` raise `CSR_PRIVILEGE_FAULT`.

Kernel writes set the exact visible 48-bit counter value. If a natural event increment and an explicit CSR write would update the same `PMC` at the same retire point, the explicit CSR write wins.

All `PMC` counters wrap modulo `2^48`. E12-S05 defines no overflow interrupt, sticky overflow bit, saturation mode, high-half shadow CSR, or overflow reporting CSR.

## `PERFSEL` Layout

`PERFSEL` is the mandatory fast CSR at `0x0F`. E12-S05 defines it as a selector/configuration window over the eight `PMC` rows.

| Bits | Name | Access | Reset | Meaning |
| ---: | --- | --- | ---: | --- |
| `2:0` | `IDX` | K `RW` | `0` | Selects one `PMC` row, `0-7`. |
| `7:3` | `RES0` | `RZ/W0` | `0` | Reserved-zero. |
| `15:8` | `EVENT` | K `WARL` | `0` | Event selector for the selected `PMC` row. |
| `16` | `EN` | K `WARL` | `0` | Enable counting for the selected `PMC` row. |
| `17` | `CLR` | K `W1`, reads `0` | `0` | Clear the selected `PMC` counter to zero. |
| `18` | `CFGW` | K `W1`, reads `0` | `0` | Write `EVENT` and `EN` into the selected `PMC` row. |
| `47:19` | `RES0` | `RZ/W0` | `0` | Reserved-zero. |

User-mode reads or writes of `PERFSEL` raise `CSR_PRIVILEGE_FAULT`.

Writes that set reserved-zero bits raise `ILLEGAL_CSR_WRITE` and leave `PERFSEL`, all `PMC` configuration rows, and all `PMC` counter values unchanged.

`PERFSEL.IDX` selects the current row for reads and side effects. A `PERFSEL` read returns:

- The current `IDX`.
- The readback `EVENT` and `EN` for that row.
- `CLR=0`.
- `CFGW=0`.
- Reserved bits as zero.

`PERFSEL` write behavior:

| Write field state | Effect |
| --- | --- |
| `CFGW=0`, `CLR=0` | Select `IDX` for later reads. Counter configuration and counter values are unchanged. |
| `CFGW=1`, `CLR=0` | Select `IDX` and write `EVENT` and `EN` to that row. Counter value is unchanged. |
| `CFGW=0`, `CLR=1` | Select `IDX` and clear `PMC[IDX]` to zero. Counter configuration is unchanged. |
| `CFGW=1`, `CLR=1` | Select `IDX`, write `EVENT` and `EN` to that row, and clear `PMC[IDX]` to zero. |

`CFGW` and `CLR` are side-effect controls. They do not remain set after the CSR instruction retires.

## Event Selectors

The mandatory v0.1 architectural event selector namespace is:

| Selector | Name | Event counted |
| ---: | --- | --- |
| `0x00` | `NONE` | No event. Counter does not increment. |
| `0x01` | `ICACHE_MISS` | Demand instruction-cache miss attributable to the local core. |
| `0x02` | `DCACHE_MISS` | Demand data-cache miss attributable to the local core. |
| `0x03` | `L2_MISS` | Local-core request that misses the shared L2 and must be satisfied below L2. |
| `0x04` | `ITLB_MISS` | Instruction translation lookup miss in `RADIX4` mode. |
| `0x05` | `DTLB_MISS` | Data, capability, atomic, or stack translation lookup miss in `RADIX4` mode. |
| `0x06` | `BRANCH_MISPREDICT` | Branch or control prediction later corrected by an architectural redirect. |
| `0x07` | `TRAP_TAKEN` | Successful synchronous trap, interrupt, or debug-monitor entry. |
| `0x08` | `LLSC_FAILURE` | Non-trapping `SC48` failure that writes `Dr=1`. |
| `0x09` | `CAPABILITY_FAULT` | Selected capability-related exception packet. |
| `0x0A-0x7F` | reserved architectural | Reserved for later architectural events. |
| `0x80-0xBF` | platform | Platform-defined events when documented by the platform profile. |
| `0xC0-0xFE` | implementation-specific | Implementation-defined events when documented by the implementation. |
| `0xFF` | reserved | Reserved. |

Selectors `0x01-0x09` have stable architectural names even on implementations that do not support counting them.

## Unsupported Event Behavior

`PERFSEL.EVENT` and `PERFSEL.EN` are `WARL`.

When software writes an unsupported architectural, platform, implementation-specific, or reserved selector with `CFGW=1`, the selected row must read back as:

```text
EVENT = NONE
EN = 0
```

The write does not fault solely because the event selector is unsupported.

This readback rule is the architectural discovery mechanism:

1. Kernel software writes `PERFSEL` with `IDX`, the desired `EVENT`, `EN=1`, and `CFGW=1`.
2. Kernel software reads `PERFSEL`.
3. If the row reads back with the requested `EVENT` and `EN=1`, the event is supported for that `PMC`.
4. If the row reads back as `EVENT=NONE` or `EN=0`, the event is unsupported or disabled for that row.

An implementation must not alias an unsupported selector to a different event. For example, writing `BRANCH_MISPREDICT` must not read back as `BRANCH_MISPREDICT` while actually counting taken branches or all branch instructions.

Platform and implementation-specific selectors may be supported only when platform or implementation documentation names the selector and event semantics.

## Counting Rules

Each `PMC` row counts independently.

When an event occurs, every enabled `PMC` row whose readback `EVENT` matches that event increments by the number of occurrences attributed to the local core:

```text
PMC = (PMC + event_count) mod 2^48
```

Multiple `PMC` rows may count the same event. A single `PMC` row counts only one selected event at a time.

The following never increment architectural `PMC` counters:

- Wrong-path work killed by branch, trap, interrupt, debug, or reset redirect.
- Prefetch-only requests that are not demanded by the architectural instruction stream or an architectural data access.
- Maintenance traffic generated internally by replacement, writeback, coherence probing, or platform debug inspection unless a later event selector explicitly names it.
- Events generated by another core, except when a documented shared event is explicitly attributed to this core.
- Events while this core is in `DEBUG_HALTED`.

Debug-monitor software is ordinary kernel execution after entry. Its cache, TLB, branch, trap, LL/SC, and capability-fault events may increment PMCs according to the selected events.

## Event Definitions

### `ICACHE_MISS`

`ICACHE_MISS` increments for a demand instruction fetch by the local core that misses in the private L1 instruction cache and requires a fill request toward L2 or lower memory.

An instruction-side prefetch that is later unused does not increment `ICACHE_MISS`. A wrong-path fetch killed before it becomes part of the architectural instruction stream does not increment `ICACHE_MISS`.

If the implementation has no enabled instruction cache, this selector may be unsupported and read back as `NONE`.

### `DCACHE_MISS`

`DCACHE_MISS` increments for a demand data-side access by the local core that misses in the private L1 data cache and requires a fill or write-allocate request toward L2 or lower memory.

Data-side accesses include integer loads and stores, capability loads and stores, `LL48`, `SC48`, protected return-stack accesses, and cacheable page-table walker data accesses when the implementation routes them through the local data-cache lookup.

Uncacheable, noncoherent, device, or cache-bypassed accesses do not increment `DCACHE_MISS` unless a later selector explicitly names those accesses.

If the implementation has no enabled data cache, this selector may be unsupported and read back as `NONE`.

### `L2_MISS`

`L2_MISS` increments for a local-core request to the shared L2 that cannot be satisfied by an L2 resident line or directory entry and requires access below L2.

The event is attributed to the core whose instruction, data, atomic, page-walk, or write-allocate request caused the L2 lookup.

Coherence probes, invalidations, and writebacks caused only by other cores do not increment this core's `L2_MISS` counter.

If the implementation has no enabled L2 cache, this selector may be unsupported and read back as `NONE`.

### `ITLB_MISS`

`ITLB_MISS` increments when `SATP.MODE=RADIX4` and an instruction fetch translation lookup misses in the local ITLB and performs or invokes a page-table walk.

No `ITLB_MISS` is counted when `SATP.MODE=BARE`, because TLB lookup is bypassed.

A page-walk fault after an ITLB miss still leaves the ITLB miss event counted once. A stale cached negative translation may count as an ITLB miss only if the implementation performs the same miss/refill path that a positive miss would use.

### `DTLB_MISS`

`DTLB_MISS` increments when `SATP.MODE=RADIX4` and a data-side translation lookup misses in the local DTLB and performs or invokes a page-table walk.

Data-side translation lookups include integer data accesses, capability data accesses, `LL48`, `SC48`, protected return-stack accesses, and explicit cache-maintenance accesses that require data-side address translation.

No `DTLB_MISS` is counted when `SATP.MODE=BARE`.

### `BRANCH_MISPREDICT`

`BRANCH_MISPREDICT` increments when the front end follows a predicted next `PCC` or slot and a later resolved control-flow instruction selects a different architectural next `PCC` or slot, requiring wrong-path work to be flushed.

If an implementation stalls until a control transfer is resolved and does not make a prediction, no mispredict occurs for that control transfer.

E13-S04 owns the final predictor structure and may refine which direct conditional branches, returns, or indirect transfers are predicted. It must preserve this counter event's basic meaning: count corrections of an actually used prediction, not all taken branches.

### `TRAP_TAKEN`

`TRAP_TAKEN` increments when the core successfully commits one of these handler-entry updates:

- E07-S04 direct synchronous exception trap entry.
- E07-S05 vectored maskable interrupt entry.
- E12-S01 debug-monitor entry.

Non-monitor `DEBUG_HALTED` entry does not increment `TRAP_TAKEN` because no handler instruction stream is entered.

A trap-entry failure does not increment `TRAP_TAKEN` for the failed handler entry. If a later debug-monitor fallback succeeds, that debug-monitor entry may increment `TRAP_TAKEN`.

### `LLSC_FAILURE`

`LLSC_FAILURE` increments when an `SC48` instruction passes all access checks, retires normally as a non-trapping failure, writes `Dr=1`, performs no memory store, and consumes the reservation.

The event includes missing reservations, mismatched reservations, reservations cleared by conflicts, and spurious failures.

A faulting `SC48` does not increment `LLSC_FAILURE`, because access faults take priority over reservation failure.

### `CAPABILITY_FAULT`

`CAPABILITY_FAULT` increments when the selected exception packet is capability-related and carries a non-`NONE` `CAPCAUSE`.

This includes baseline capability tag, bounds, permission, seal/type, and local-store faults, plus protected return-stack faults that report a capability cause.

A single selected capability exception increments `CAPABILITY_FAULT` at most once, even if more than one latent capability check could have failed. If that exception also successfully enters a trap handler, `TRAP_TAKEN` may increment separately.

## Reset, Halt, and Startup

Cold reset initializes:

```text
PMC0-PMC7 = 0
PERFSEL.IDX = 0
all PMC row EVENT = NONE
all PMC row EN = 0
```

Secondary cores begin architecturally visible execution with the same reset values unless a platform startup profile explicitly documents earlier firmware writes.

`DEBUG_HALTED` stops performance-counter increments for the halted core. It does not clear `PMC` counter values or configuration rows.

`DEBUGCTL.RESUME` and debug-monitor `IRET` do not clear `PMC` state.

## Out of Scope

E12-S05 does not define:

- User-mode access to performance counters.
- Counter overflow interrupts or sticky overflow flags.
- Atomic multi-counter snapshot reads.
- Per-privilege, per-ASID, per-process, or per-context counter filtering.
- Sampling periods or interrupt-on-overflow profiling.
- Mandatory support for every reserved event on every implementation.
- Precise counting of speculative prefetches or wrong-path microarchitectural activity.

## Verification Notes

E12-S05 tests should cover:

- `PMC0-PMC7` reset to zero.
- `PERFSEL` reset selects `IDX=0`, `EVENT=NONE`, and `EN=0`.
- Kernel writes to a `PMC` set the exact visible value.
- User reads and writes of `PERFSEL` and `PMC0-PMC7` raise `CSR_PRIVILEGE_FAULT`.
- `PERFSEL` writes with reserved-zero bits raise `ILLEGAL_CSR_WRITE` and leave counter state unchanged.
- Writing `PERFSEL` with `CFGW=1` configures only the selected row.
- Writing `PERFSEL` with `CLR=1` clears only the selected `PMC`.
- Unsupported event selectors read back as `EVENT=NONE`, `EN=0`.
- Two `PMC` rows configured for the same supported event both increment on that event.
- Disabled rows do not increment.
- `ICACHE_MISS`, `DCACHE_MISS`, `L2_MISS`, `ITLB_MISS`, and `DTLB_MISS` selectors can be probed through readback even if unsupported.
- A non-trapping failed `SC48` increments `LLSC_FAILURE`; a faulting `SC48` does not.
- A capability fault increments `CAPABILITY_FAULT` once for the selected exception.
- A synchronous trap or interrupt handler entry increments `TRAP_TAKEN` when supported.
- `DEBUG_HALTED` does not increment PMCs.
- Counter overflow wraps modulo `2^48` without setting interrupt pending state.

## Story Acceptance Review

| Acceptance criterion | Evidence |
| --- | --- |
| Counters are reserved for I-cache misses, D-cache misses, L2 misses, ITLB misses, DTLB misses, branch mispredicts, traps taken, LL/SC failures, and capability faults. | Met: selectors `0x01-0x09` reserve stable event names for each requested category. |
| Counter selection through `PERFSEL` is defined or reserved. | Met: `PERFSEL` is a kernel-only selector/configuration window over `PMC0-PMC7`. |
| Unsupported counter behavior is specified. | Met: unsupported selectors read back as `EVENT=NONE`, `EN=0`, and do not alias to other events. |

# RTL Integrated Core Atomic Cache

Story: I22-S07

Status: Draft integrated RTL atomic, reservation, fence, and cache-maintenance implementation

This story promotes the I21-S03 LL/SC and cache-maintenance slice into the live
`cpu_v01_core` execution and memory path. The integrated core now executes
`LL48`, `SC48`, `FENCE`, `FENCE.I`, and `CACHE.*` through the top-level retire
packet, while using the existing data-memory, tag-memory, translation, CSR,
trap, and `SFENCE.VM` paths.

I22-S08 still owns promotion of observed integrated-core cases into the
Verilator regression gate.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Provides shared opcode, reservation, fence, cache-maintenance, memory-effect, and translation retire fields. |
| `rtl/cpu_v01_core.sv` | Adds integrated reservation state, `LL48`/`SC48` execution, reservation clear events, fence retire effects, cache-maintenance retire effects, and `DEVICE_ORDERED` cache access faults. |
| `rtl/cpu_v01_core_atomic_cache_tb.sv` | Verilator-oriented fixture for LL/SC success and failure, same-core store conflict, faulting `LL48`, CSR/SFENCE/trap clears, `FENCE`, `FENCE.I`, `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL`, and device-memory `ACCESS_FAULT`. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_atomic_cache.py --check
```

Print the integrated atomic/cache coverage projection:

```text
python tools\rtl_core_atomic_cache.py --json
```

The Verilator source check for this story is:

```text
verilator --lint-only --timing --top-module cpu_v01_core_atomic_cache_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_atomic_cache_tb.sv
```

## Implemented Behavior

- `LL48` uses the translated data-memory load path, writes the destination
  integer register, and installs a normal-coherent reservation at retire.
- `SC48` success reuses the store path, clears the memory tag, returns zero,
  marks `sc_success`, and clears the matching reservation.
- `SC48` failure returns one without data-memory or tag-memory writes and
  retires a reservation clear.
- Same-core `ST48`, faulting `LL48`, CSR writes, `BRK` trap entry, and
  `SFENCE.VM` clear active reservations in the integrated retire packet.
- `FENCE` and `FENCE.I` expose ordering retire effects.
- `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` expose maintenance kind,
  physical address, and length. Invalidating forms clear overlapping
  reservations.
- `CACHE.CLEAN` over `DEVICE_ORDERED` memory retires `ACCESS_FAULT` with the
  translated device physical address in `TVAL`.

## Fixture Diagnostics

`cpu_v01_core_atomic_cache_tb` checks data-memory writes, tag clears,
reservation install and clear metadata, `SC48` success/failure results, fence
retire bits, cache-maintenance ranges, and device-memory access faults from the
integrated top-level ports and retire packet.

## Deferred From This Story

- Other-core reservation invalidation remains a fabric/coherence follow-up.
- Full external cache-line implementation is still outside the single-core RTL
  fixture; this story exposes architected maintenance retire effects.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `LL48` installs reservations through the top-level memory path. | Met. |
| `SC48` success and failure retire architected result and reservation effects. | Met. |
| Conflict, fault, CSR, trap, and fence paths clear reservations. | Met for representative integrated cases. |
| `FENCE`, `FENCE.I`, and `CACHE.*` retire observable ordering and maintenance effects. | Met. |
| Device-memory cache maintenance faults precisely. | Met for `CACHE.CLEAN` over `DEVICE_ORDERED`. |

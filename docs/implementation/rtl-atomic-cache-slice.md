# RTL Atomic Cache Slice

Story: I21-S03

Status: Draft RTL coverage implementation

This slice expands the deterministic RTL surface to `LL48`/`SC48`,
reservation lifecycle effects, ordering fences, and cache-maintenance access
checks. It remains a bounded fixture, not an integrated cache hierarchy,
store-buffer implementation, multicore coherency engine, or DMA controller.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds `LL48`, `SC48`, `FENCE`, `FENCE.I`, `CACHE.*`, reservation, ordering, and cache-maintenance retire-packet constants/fields. |
| `rtl/cpu_v01_atomic_cache_core.sv` | Deterministic fixture for LL/SC success/failure, reservation clear events, `FENCE`, `FENCE.I`, `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL`, and device-memory access faults. |
| `rtl/cpu_v01_atomic_cache_tb.sv` | Verilator-oriented smoke testbench for final LL/SC, reservation, fence, cache-maintenance, and `ACCESS_FAULT` observations. |

## Local Commands

Validate the source and coverage projection boundary:

```text
python tools\rtl_atomic_cache_slice.py --check
```

Print the coverage projection:

```text
python tools\rtl_atomic_cache_slice.py --json
```

The Verilator fixture command for this bounded slice is:

```text
verilator --binary --timing --top-module cpu_v01_atomic_cache_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_atomic_cache_core.sv rtl/cpu_v01_atomic_cache_tb.sv
```

## Covered Behavior

- `LL48` installs an aligned normal-coherent reservation and writes the loaded
  48-bit value.
- `SC48` success writes memory, clears the memory tag, returns zero, and clears
  the reservation.
- `SC48` failure returns one without memory or tag updates and clears the
  reservation.
- Same-core store conflict, faulting `LL48`, CSR writes, trap entry, and
  `SFENCE.VM` retire effects clear active reservations.
- `FENCE` and `FENCE.I` expose ordering retire effects.
- `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` expose cache-maintenance
  retire effects; invalidating forms clear matching reservations.
- `CACHE.CLEAN` over device memory reports `ACCESS_FAULT` with the translated
  physical address in `TVAL`.

## Deferred From This Slice

Integrated store-buffer draining, cache-line state machines, remote conflict
notification, DMA ownership, multicore coherence, and performance/progress
timing remain for later stories and integration work.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| RTL covers `LL48` reservation install. | Met. |
| RTL covers `SC48` success and failure. | Met. |
| RTL covers reservation clear events for conflict, fault, trap, CSR, and fence paths. | Met. |
| RTL covers `FENCE` and `FENCE.I` ordering effects. | Met. |
| RTL covers `CACHE.*` access checks and reservation clears. | Met. |
| RTL covers device-memory cache-maintenance `ACCESS_FAULT`. | Met. |

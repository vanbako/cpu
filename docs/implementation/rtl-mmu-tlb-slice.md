# RTL MMU TLB Slice

Story: I21-S02

Status: Draft RTL coverage implementation

This slice expands the deterministic RTL surface to `RADIX4` translation,
local TLB behavior, `SATP`/ASID context, page faults, and `SFENCE.VM*`
invalidation effects. It is still a bounded fixture, not an integrated
`cpu_v01_core`, page-table walker port, cache hierarchy, or multicore
shootdown implementation.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds `SFENCE.VM*`, page-fault, SATP, PTE, memory-type, TLB-invalidate, translation, and TLB retire-packet constants/fields. |
| `rtl/cpu_v01_mmu_tlb_core.sv` | Deterministic fixture for bare translation, RADIX4 page walk, DTLB fill/hit, stale entry behavior, `SFENCE.VM*`, ASID/global scope, and page faults. |
| `rtl/cpu_v01_mmu_tlb_tb.sv` | Verilator-oriented smoke testbench for final translation, TLB, SFENCE, ASID, and fault observations. |

## Local Commands

Validate the source and coverage projection boundary:

```text
python tools\rtl_mmu_tlb_slice.py --check
```

Print the coverage projection:

```text
python tools\rtl_mmu_tlb_slice.py --json
```

The Verilator fixture command for this bounded slice is:

```text
verilator --binary --timing --top-module cpu_v01_mmu_tlb_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_mmu_tlb_core.sv rtl/cpu_v01_mmu_tlb_tb.sv
```

## Covered Behavior

- Bare `SATP` identity translation.
- `RADIX4` page walk through four levels with DTLB fill metadata.
- DTLB stale hit behavior before `SFENCE.VM.VA_ASID` retires.
- Local `SFENCE.VM`, `SFENCE.VM.ASID`, `SFENCE.VM.VA`, and
  `SFENCE.VM.VA_ASID` invalidation retire effects.
- ASID-specific and global TLB entry scope.
- `PAGE_FAULT` reporting for unmapped, permission, and reserved memory-type PTE
  cases, with the original virtual address in `TVAL`.

## Deferred From This Slice

`FENCE`, `FENCE.I`, `LL48`, `SC48`, reservation behavior, cache-maintenance
instructions, cache hierarchy behavior, remote TLB shootdown, and a real
page-table-walker memory port remain for later I21 stories.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| RTL covers bare-mode translation. | Met. |
| RTL covers RADIX4 page-walk translation and DTLB fill metadata. | Met. |
| RTL covers permission, mapping, and reserved memory-type page faults. | Met. |
| RTL covers stale TLB behavior before local invalidation. | Met. |
| RTL covers `SFENCE.VM*` invalidation effects. | Met. |
| RTL covers ASID/global TLB scope. | Met. |

# RTL Integrated Core MMU TLB

Story: I22-S06

Status: Draft integrated RTL translation implementation

This story promotes the I21-S02 MMU/TLB slice into the live `cpu_v01_core`
memory path. The integrated core now tracks `SATP`/`ASID`, translates data
accesses before driving the data-memory port, reports translation and TLB retire
metadata, handles representative `PAGE_FAULT` outcomes, and retires local
`SFENCE.VM*` invalidation effects.

I22-S07 still owns LL/SC, reservation, fence, and cache-maintenance integration.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Provides shared `SATP`, PTE, memory-type, TLB invalidation, translation, and page-fault retire fields. |
| `rtl/cpu_v01_core.sv` | Adds integrated translation helpers, local DTLB state, data-memory physical-address issue, `SATP`/`ASID` coupling, page-fault retire metadata, and `SFENCE.VM*` invalidation effects. |
| `rtl/cpu_v01_core_mmu_tlb_tb.sv` | Verilator-oriented fixture for bare identity translation, `RADIX4` fills, stale TLB behavior, `SFENCE.VM.VA_ASID`, ASID/global scope, and memory-type faults. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_mmu_tlb.py --check
```

Print the integrated MMU/TLB coverage projection:

```text
python tools\rtl_core_mmu_tlb.py --json
```

The Verilator source check for this story is:

```text
verilator --lint-only --timing --top-module cpu_v01_core_mmu_tlb_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_mmu_tlb_tb.sv
```

## Implemented Behavior

- Bare `SATP` data loads retire identity translation metadata and drive the
  data-memory port with the effective address.
- `RADIX4` data loads through the deterministic fixture mapping retire a
  translation, final page-walk level, physical address, and DTLB fill.
- A stale TLB entry can satisfy a second load after the fixture mapping is
  removed, until `SFENCE.VM.VA_ASID` invalidates the local entry.
- The post-invalidation load retires `PAGE_FAULT` with the original virtual
  address in `TVAL`.
- `SATP` writes update the exposed `ASID` CSR field used by translation and
  SFENCE operand checks.
- `SFENCE.VM`, `SFENCE.VM.ASID`, `SFENCE.VM.VA`, and `SFENCE.VM.VA_ASID` retire
  local TLB invalidation metadata.
- ASID-specific fills and a global mapping preserve the I21-S02 scope
  distinction in integrated retire packets.
- Permission and reserved memory-type fixture roots retire precise
  `PAGE_FAULT` packets without issuing the data-memory access.

## Fixture Diagnostics

`cpu_v01_core_mmu_tlb_tb` checks that the address sent to the data-memory port
is the translated physical address, that retire packets include effective and
physical addresses, and that stale TLB, invalidation, ASID/global, and
memory-type fault paths are observable from the integrated top level.

## Deferred From This Story

- A general-purpose external page-table-walker port; this story keeps the
  deterministic fixture mapping used by the bounded RTL slice.
- Instruction-side page-fault fixtures beyond the shared translation helper
  boundary.
- LL/SC, reservation, fence, and cache-maintenance behavior: I22-S07.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Data accesses translate before using the top-level data port. | Met for bare and RADIX4 representative cases. |
| Retire packets expose translation, TLB fill, and stale-hit metadata. | Met. |
| `SATP`/`ASID` state drives translation and invalidation scope. | Met. |
| `SFENCE.VM*` forms retire local invalidation effects. | Met. |
| Permission and memory-type translation faults are precise. | Met for representative `PAGE_FAULT` cases. |

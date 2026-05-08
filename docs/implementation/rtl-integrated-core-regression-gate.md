# RTL Integrated Core Regression Gate

Story: I22-S08

Status: Implemented integrated-core regression gate profile

This story promotes `cpu_v01_core` fixtures into the Verilator regression gate.
The gate keeps the existing golden and toolchain cases, and adds integrated
top-level cases that name their `cpu_v01_core` testbench, source files, suite,
and golden retire trace when the fixture is directly comparable.

## Commands

Fast integrated and legacy gate:

```text
python tools\verilator_diff_harness.py --suite fast
```

List all integrated cases:

```text
python tools\verilator_diff_harness.py --suite all --list-cases
```

Select one integrated top-level case by ID:

```text
python tools\verilator_diff_harness.py --case-id core.scalar.integer_ops_add_mul
```

Compare an observed integrated retire trace:

```text
python tools\verilator_diff_harness.py --case-id core.scalar.integer_ops_add_mul --observed-trace build\verilator\retire_trace.json
```

## Integrated Cases

| Case ID | Suite | Top module | Golden trace |
| --- | --- | --- | --- |
| `core.shell.reset_idle` | fast | `cpu_v01_core_shell_tb` | none |
| `core.fetch_decode.slot1_48bit_placement` | fast | `cpu_v01_core_fetch_decode_tb` | `fault_cases.slot1_48bit_placement` |
| `core.scalar.integer_ops_add_mul` | fast | `cpu_v01_core_scalar_control_tb` | `integer_ops.add_mul` |
| `core.cap_mem.memory_tag_ops` | slow | `cpu_v01_core_cap_mem_tb` | `memory_tag_ops.csc_clc_st48_ld48` |
| `core.control_trap.sys_iret` | slow | `cpu_v01_core_control_trap_tb` | `traps.sys_iret_return` |
| `core.mmu_tlb.translation_sfence` | slow | `cpu_v01_core_mmu_tlb_tb` | none |
| `core.atomic_cache.llsc_cache` | slow | `cpu_v01_core_atomic_cache_tb` | none |

## Verilator Boundaries

Each integrated case has a lint command of this shape:

```text
verilator --lint-only --timing --top-module cpu_v01_core_scalar_control_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_scalar_control_tb.sv
```

The harness still accepts observed `retire_trace.json` input and reports the
first mismatch by selected case ID, packet sequence, and field. Integrated cases
with a golden trace compare against the same golden corpus as the legacy gate,
but diagnostics use the `core.*` case ID.

## Explicit Deferrals

- `core.shell.reset_idle` has no retire trace because it is a no-program shell
  smoke.
- `core.mmu_tlb.translation_sfence` remains an assertion fixture until trace
  capture covers translation and TLB metadata.
- `core.atomic_cache.llsc_cache` remains an assertion fixture until trace
  capture covers reservation, `SC48`, fence, and cache-maintenance metadata.
- Binary execution is delegated to the external Verilator/make runner; dry-run
  selection and observed-trace comparison remain local gate behavior.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Fast and slow suites can select `cpu_v01_core` cases. | Met. |
| Integrated cases name their top module and source files. | Met. |
| Golden-backed integrated cases compare observed retire traces. | Met. |
| Mismatches report the selected integrated case ID. | Met. |
| Remaining deferrals are reported separately from slice-only coverage. | Met. |

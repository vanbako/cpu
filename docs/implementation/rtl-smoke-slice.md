# RTL Smoke Slice

Story: I20-S05

Status: Draft RTL smoke implementation

The first SystemVerilog slice lives under `rtl/` and implements the smallest
single-core retire boundary from I20-S01. It is intentionally limited to a
single slot-0 reset smoke instruction plus a placement-fault variant. Capability
register behavior, data-memory/tag behavior, traps, calls, returns, atomics,
TLBs, caches, interrupts, debug, MMIO, DMA, and secondary cores remain deferred
to later I20 stories.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | First package constants and packed packet types. |
| `rtl/cpu_v01_smoke_core.sv` | Tiny single-core smoke slice with reset, slot-0 ADD retire, and slot placement fault handling. |
| `rtl/cpu_v01_smoke_tb.sv` | Verilator-oriented smoke testbench for the normal and placement-fault cores. |

The smoke core initializes `D0 = 0x10`, `D1 = 0x20`, starts from the reset
vector, retires one 24-bit `ADD` from slot 0, writes `D2 = 0x30`, and emits a
retire packet with the first-slice integer write fields. A second parameterized
instance forces slot 1 and emits a precise `ALIGN_FAULT` packet before normal
effects are selected.

## Local Commands

Validate the source/golden projection boundary:

```text
python tools\rtl_smoke_slice.py --check
```

Print the first-slice packet projection:

```text
python tools\rtl_smoke_slice.py --json
```

The projection is derived from the golden corpus cases:

- `reset_smoke.add_slot0`;
- `fault_cases.slot1_48bit_placement`.

When Verilator is installed, `rtl/cpu_v01_smoke_tb.sv` is the first testbench
target to wire into the differential harness.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| RTL retires a tiny straight-line reset program. | Met. |
| RTL emits integer register writes. | Met. |
| RTL preserves slot-0 sequencing for the smoke path. | Met. |
| RTL checks legal placement and emits a precise placement fault. | Met. |
| Retire packets are compared against the golden corpus projection. | Met. |

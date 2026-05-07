# Verilator Regression Gate

Story: I21-S05

Status: Implemented harness gate profile

## Scope

The Verilator differential harness now exposes a regression-suite gate over
generated semantic and toolchain cases. It can:

- list fast and slow regression partitions;
- select one or more cases with `--case-id`;
- compare observed retire traces against selected golden/toolchain-backed
  expected cases;
- report the first mismatch by selected case ID, packet sequence, and field;
- skip cleanly when Verilator is unavailable unless `--require-verilator` is
  requested.

## Commands

Fast gate for local use:

```text
python tools\verilator_diff_harness.py --suite fast
```

Specific case comparison:

```text
python tools\verilator_diff_harness.py --case-id syscall_trap.sys_pause_iret_binary --observed-trace build\verilator\retire_trace.json
```

Case inventory:

```text
python tools\verilator_diff_harness.py --suite all --list-cases
```

## Case Sources

Golden cases come from `cpu_v01.golden_traces`. Toolchain cases come from
`cpu_v01.toolchain_corpus`; cases that name a `golden_trace_case_id` are
projected under their toolchain case ID so diagnostics point to the binary
fixture that failed.

Slow cases are retained for linker, debug metadata, bad-object, and broader
semantic corpus checks. Fast cases are the default CLI gate.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Harness runs generated golden cases by case ID. | Met. |
| Harness runs generated toolchain cases by case ID. | Met. |
| Fast and slow suites are partitioned. | Met. |
| First-mismatch diagnostics name the selected case ID. | Met. |
| Missing Verilator still skips cleanly unless required. | Met. |

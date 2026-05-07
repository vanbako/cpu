# Verilator Differential Harness

Story: I20-S04

Status: Draft harness skeleton

The I20-S04 harness is the boundary between the semantic golden retire corpus
and future RTL simulations. It does not require RTL to exist yet. It validates
the generated golden corpus and SystemVerilog interface contract, compares
observed retire JSON when provided, and skips cleanly when Verilator is not
available.

## Command

Dry-run the harness boundary:

```text
python tools\verilator_diff_harness.py
```

Run the fast regression partition explicitly:

```text
python tools\verilator_diff_harness.py --suite fast
```

Select a single generated case ID:

```text
python tools\verilator_diff_harness.py --case-id integer_ops.add_mul
```

Compare an observed trace JSON file:

```text
python tools\verilator_diff_harness.py --observed-trace build\verilator\retire_trace.json
```

Require Verilator to be present:

```text
python tools\verilator_diff_harness.py --require-verilator
```

Attempt the future non-dry-run RTL boundary:

```text
python tools\verilator_diff_harness.py --run
```

Until an integrated `cpu_v01_core` top-level exists, `--run` only validates
that Verilator is available and then reports that the build/run command is
deferred. The current I20 RTL artifacts are fixture slices consumed through the
readiness report.

## Inputs

- Golden expected packets come from `cpu_v01.golden_traces`.
- Toolchain-backed case IDs come from `cpu_v01.toolchain_corpus` when a case
  names a golden retire trace.
- Package and interface prerequisites come from `cpu_v01.sv_contract`.
- Observed packets are read from `retire_trace.json` using the same case and
  packet shape as `python tools\golden_trace_corpus.py`.

## Result Rules

- `PASSED`: dry-run prerequisites are valid, or an observed trace exactly
  matches the golden corpus.
- `FAILED`: prerequisites fail, Verilator is required but unavailable, or the
  first observed packet mismatch is found.
- `SKIPPED`: Verilator or RTL execution is unavailable and was not required.

Mismatches report the case ID first, then the packet sequence and field path.
This keeps future CI output actionable for a failing RTL retire packet.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Harness dry-runs the RTL/testbench boundary. | Met. |
| Harness feeds the golden fixtures. | Met. |
| Harness compares captured/observed retire traces. | Met. |
| Harness reports the first mismatch by case ID. | Met. |
| Harness skips cleanly when Verilator is unavailable. | Met. |

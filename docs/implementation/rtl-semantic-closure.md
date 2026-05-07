# RTL Semantic Closure Report

Story: I21-S06

Status: single-core fixture-slice semantic closure published

This report is the single-core RTL semantic closure boundary for CPU v0.1. It
does not claim an integrated `cpu_v01_core`; it records which deterministic RTL
slices, golden cases, invariants, deferrals, and local gates are sufficient to
start the next multicore/fabric RTL phase.

## Command

```text
python tools\rtl_semantic_closure.py --check
```

## Local Gates

- `python tools\local_checks.py`
- `python tools\verilator_diff_harness.py --suite fast`
- `python tools\rtl_readiness_gap.py --check`
- `python tools\story_coverage.py --check-drift`

## Instruction Families

| Family | Covered RTL stories | Deferred mandatory mnemonics |
| --- | --- | --- |
| Integer scalar and condition results | `I21-S01` | - |
| Memory/tag and LL/SC | `I20-S06`, `I21-S03` | - |
| Capability derivation | `I20-S06` | `CINCADDR`, `CSETBOUNDS`, `CSEAL`, `CUNSEAL` |
| Control, trap, syscall, and protected stack | `I20-S07`, `I21-S01`, `I21-S04` | `WFI` |
| CSR, CCSR, ordering, MMU/TLB, and cache maintenance | `I21-S01`, `I21-S02`, `I21-S03` | - |

The generated report expands these rows to every mandatory v0.1 mnemonic and
checks that the unsupported set mirrors the RTL readiness inventory.

## Golden Cases

Golden retire cases are mapped through `src/cpu_v01/rtl_readiness.py`. The
closure check requires every `cpu_v01.golden_traces` case to appear with an RTL
status or an explicit semantic-only status.

## Invariants

The closure report imports the invariant registry and lists the stable keys for
capability monotonicity, tag non-forgery, precise fault effects, commit-boundary
atomicity, and software-visible capability contracts.

## Unsupported Deferrals

The final single-core semantic-closure deferrals are:

- `CINCADDR`
- `CSETBOUNDS`
- `CSEAL`
- `CUNSEAL`
- `WFI`

Broader deferred surfaces remain explicit: integrated `cpu_v01_core`, debug
monitor RTL entry, interrupt-controller sleep/wakeup timing, multicore
execution, fabric links, coherence, and external memory integration.

## Readiness Criteria

- `python tools\local_checks.py` passes, including the fast Verilator regression gate.
- Mandatory unsupported mnemonics are limited to documented deferrals.
- Golden retire cases have RTL status or explicit semantic-only status.
- Security and precision invariants are mapped to conformance artifacts.
- Integrated multicore/fabric RTL starts only after `cpu_v01_core` exists and
  deferred external interfaces are modeled.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Mandatory instruction families are mapped. | Met. |
| Golden cases are mapped. | Met. |
| Invariants are mapped. | Met. |
| Unsupported deferrals are explicit. | Met. |
| Local gate commands and multicore/fabric readiness criteria are listed. | Met. |

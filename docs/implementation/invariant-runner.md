# Invariant Runner

Story: I16-S03

The invariant runner executes deterministic invariant case families and reports
the seed, case IDs, and pass/fail status for every selected case. It is meant to
be a small reproduction layer between the hand-written conformance fixtures and
future broader property generation.

Library entry points live in `src/cpu_v01/invariant_runner.py`:

- `available_families()` returns supported family names.
- `invariant_case_ids()` lists stable replay IDs.
- `run_invariants(seed=..., families=..., case_ids=...)` executes selected cases.
- `render_report(report)` produces a command-line friendly report.

The command-line wrapper is:

```text
python tools\invariant_runner.py --seed 7
```

Useful selection forms:

```text
python tools\invariant_runner.py --family capability_derivation
python tools\invariant_runner.py --family invalid_tag_derivation --list
python tools\invariant_runner.py --seed 7 --case-id capability_derivation/full_permissions_low_cursor/CSETADDR/address=0x1000
```

The runner currently executes the deterministic I16-S02 capability cases through
the public capability instruction semantics. A failing report includes the exact
case ID needed for reproduction.

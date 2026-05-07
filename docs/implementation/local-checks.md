# Local Checks

Story: I01-S02

Use these commands before implementation commits.

## Spec Checks

```text
python tools\spec_reference_check.py
python tools\spec_constants_model.py
python tools\story_coverage.py --check-drift
python tools\toolchain_corpus.py --check
python tools\verilator_diff_harness.py --suite fast
python tools\rtl_semantic_closure.py --check
git diff --check
```

## Implementation Tests

```text
python -m unittest discover -s tests/conformance -p "test_*.py"
python -m unittest discover -s tests/litmus -p "test_*.py"
```

## Full Local Check

Run all commands above before committing implementation code.

I12-S01 adds a one-command runner for the full local check:

```text
python tools\local_checks.py
```

To inspect the command plan without running it:

```text
python tools\local_checks.py --list
```

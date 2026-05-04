# Local Checks

Story: I01-S02

Use these commands before implementation commits.

## Spec Checks

```text
python tools\spec_reference_check.py
python tools\spec_constants_model.py
git diff --check
```

## Implementation Tests

```text
python -m unittest discover -s tests/conformance -p "test_*.py"
```

## Full Local Check

Run all commands above before committing implementation code.

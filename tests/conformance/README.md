# Conformance Tests

This directory will hold story-derived CPU v0.1 conformance tests.

Tests should reference the owning architecture story or E15 matrix in their names, comments, or test metadata once the harness exists.

Current command:

```text
python -m unittest discover -s tests/conformance -p "test_*.py"
```

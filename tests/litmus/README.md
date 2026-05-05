# Litmus Tests

This directory will hold executable litmus tests for memory ordering, capability tag visibility, trap/debug priority, LL/SC reservation behavior, cache maintenance, and DMA ownership protocols.

Initial scenarios should be derived from `tools/memory_consistency_litmus.md` and `tools/fault_priority_matrix.md`.

The story-derived test ownership index is `docs/implementation/conformance-test-index.md`.

Current command:

```text
python -m unittest discover -s tests/litmus -p "test_*.py"
```

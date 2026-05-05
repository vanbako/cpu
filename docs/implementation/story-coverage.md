# Story Coverage Report

Story: I12-S02

Status: Draft implementation profile

## Purpose

The story coverage report compares the implementation backlog story table with
the conformance test index. It identifies which stories have indexed tests,
which have documentation or tool-only evidence, and which stories are still
missing indexed artifacts.

This is a reporting tool, not a gate. Future story I12-S03 owns turning drift
or missing ownership into failing checks.

## Command

```text
python tools\story_coverage.py
```

To print only missing stories:

```text
python tools\story_coverage.py --missing-only
```

## Drift Check

I12-S03 adds a check mode for local automation:

```text
python tools\story_coverage.py --check-drift
```

The drift check fails when:

- a `tests\conformance\test_*.py` or `tests\litmus\test_*.py` file is missing
  from the conformance index;
- the conformance index names a stale artifact path;
- an implementation document other than `docs\implementation\README.md` has no
  `Story: Ixx-Syy` owner line.

## Status Meaning

- `tested`: at least one indexed artifact is under `tests\`.
- `docs/tool`: indexed evidence exists, but no test artifact is listed.
- `missing`: the story appears in `agile-impl-v0.1.md` but has no indexed
  artifact yet.

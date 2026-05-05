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

## Status Meaning

- `tested`: at least one indexed artifact is under `tests\`.
- `docs/tool`: indexed evidence exists, but no test artifact is listed.
- `missing`: the story appears in `agile-impl-v0.1.md` but has no indexed
  artifact yet.

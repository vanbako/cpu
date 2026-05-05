# Pipeline Semantic Comparison

Story: I13-S02

Status: Draft executable model

Owner sources:

- I13-S01 defines the single-issue trace wrapper.
- E13-S01 defines `RT` as the precise commit point.
- E07-S03 defines precise result packet behavior.

## Scope

The I13-S02 comparator checks that the pipeline trace model and the semantic
decoded-program executor produce the same architectural results for the same
program.

It is not yet a hazard, MDU latency, branch-predictor, or scoreboard model.
Those are owned by I13-S03 and later implementation stories.

## Method

The comparator:

1. deep-copies the initial core state and optional `TaggedMemory`;
2. builds one executor for the pipeline copy and one executor for the semantic
   copy;
3. runs the same number of decoded-program steps through both paths;
4. compares each step's result packet;
5. compares final architectural snapshots.

Snapshots include integer registers, general capability registers, `PCC`,
`EPCC`, assigned scalar CSRs, and caller-selected memory cell/tag observations.

## Expected Uses

The first comparison tests cover:

- straight-line integer programs;
- load/store programs with observed memory cells;
- branch redirect packets;
- precise fault and trap-entry behavior.

The comparator is intentionally reusable by later I13 stories when hazards,
MDU latency, and predictor behavior are introduced.

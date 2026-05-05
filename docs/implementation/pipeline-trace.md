# Pipeline Trace Model

Story: I13-S01

Status: Draft executable model

Owner sources:

- E13-S01 defines the single-issue pipeline stage order.
- I10-S01 defines the RTL handoff trace and commit vocabulary.

## Scope

The I13-S01 model is an architectural trace wrapper around the existing decoded
instruction executor. It is not a cycle-accurate RTL implementation and does
not model hazards, MDU busy state, bypassing, or branch prediction. Those belong
to later I13 stories.

## Stage Order

Every traced instruction emits the E13-S01 stage sequence:

```text
FE0 -> FE1 -> PD -> XLT -> ISS -> EX -> MEM -> WB -> RT
```

Instructions receive monotonically increasing in-order sequence numbers. The
baseline model advances one instruction through the full sequence per step,
which preserves single-issue and in-order retirement.

## Result Detection

Result packets are marked as pending from the stage where the model detects
them onward:

- placement faults are detected at `PD`;
- missing or malformed decoded entries are detected at `XLT`;
- integer, capability, control, branch, and syscall-style results are detected
  at `EX`;
- load/store, atomic, cache-maintenance, call, and return-stack results are
  detected at `MEM`.

All result packets are carried to `RT`. Architectural state changes happen only
at `RT`.

## Retire Behavior

At `RT` the model can:

- commit normal retire packets with the existing semantic commit helper;
- install redirect targets for branch-like redirect packets;
- optionally enter the direct trap path for fault packets;
- leave fault packets uncommitted when trap entry is not requested.

This makes the trace useful for straight-line, branch, trap, and memory tests
without reimplementing instruction semantics.

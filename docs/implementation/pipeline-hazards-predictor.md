# Pipeline Hazards And Predictor

Story: I13-S03

Status: Draft executable model

Owner sources:

- E13-S02 defines the independent MDU and busy destination contract.
- E13-S03 defines hazard, interlock, flush, and kill behavior.
- E13-S04 defines the conservative BHT and return-address stack predictor.

## Scope

The I13-S03 model adds cycle-prototype annotations to the existing single-issue
pipeline trace. It does not replace the semantic executor and it does not claim
RTL-accurate cache, TLB, divider, or replay timing.

The model records:

- load-use interlocks for adjacent unavailable load results;
- scoreboard busy events for MDU destinations;
- BHT predictions for direct conditional `BCC` instructions;
- branch flush and wrong-path kill events on prediction mismatch;
- return-address stack push, prediction, and consume events for `CALL`/`RET`;
- predictor context flushes after privilege, `SATP`, or `ASID` changes.

## Semantic Contract

The hazard-aware comparator deep-copies the initial architectural state and runs
the same decoded program through two paths:

1. a hazard-annotated pipeline trace path;
2. the semantic decoded-program execution path.

Each retire packet and final architectural snapshot must match. Hazard stalls,
busy marks, predictions, and killed wrong-path work are microarchitectural trace
events only; they must not change integer registers, capability registers, CSRs,
memory payload, memory tags, protected return-stack state, or committed `PCC`.

## Predictor Profile

The draft implementation uses the minimum conforming predictor shape:

- 16-entry 2-bit BHT initialized to weak not-taken;
- BHT lookup only for `BCC`;
- 4-entry return-address stack;
- no generic indirect BTB;
- flush-on-context-change rather than partitioned predictor entries.

This keeps I13-S03 useful for RTL handoff tests while leaving exact queue,
forwarding mux, cache miss, TLB miss, and divider finite-state-machine details
to later implementation work.

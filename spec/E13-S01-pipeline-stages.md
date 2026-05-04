# E13-S01: Pipeline Stages

Story: E13-S01

Status: Complete

Normative source: `design.md`, section 16.1

Prerequisites:

- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E07-S03-precise-exception-model.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E09-S07-effective-access-rule.md`
- `spec/E10-S03-cpu-coherence-protocol.md`

## Decision

CPU v0.1 uses a single-issue, in-order pipeline model with named stages:

```text
FE0 -> FE1 -> PD -> XLT -> ISS -> EX -> MEM -> WB -> RT
```

The pipeline may contain implementation-specific buffers or sub-stages, but architectural behavior must be equivalent to this ordered stage model.

Only one architectural instruction may enter issue per cycle in the baseline v0.1 pipeline. Instructions retire in program order. `RT` is the architectural retire point and the precise-exception point.

## Stage Responsibilities

| Stage | Name | Required responsibility |
| --- | --- | --- |
| `FE0` | Next-PC generation | Select the next fetch PC, slot, predicted branch path, trap/interrupt/debug redirect, or sequential fall-through. |
| `FE1` | Instruction fetch | Check fetch authority, translate instruction address when MMU is enabled, and fetch the 48-bit fetch group from the instruction side. |
| `PD` | Predecode | Split the fetched group into legal 12/24/48-bit instruction starts, detect placement faults, and identify instruction length. |
| `XLT` | ISA translation | Decode the architectural instruction into the internal operation fields needed by later stages. |
| `ISS` | Issue | Check operand readiness, structural availability, and in-order issue conditions. |
| `EX` | Execute | Perform integer ALU, branch resolution, condition evaluation, address generation, and non-memory capability derivation work. |
| `MEM` | Memory and access | Perform data translation, effective-access checks, cache access, capability memory access, atomics, and memory-side fault detection. |
| `WB` | Writeback preparation | Prepare integer, capability, CSR, special-register, and memory-result writeback values for retire. |
| `RT` | Retire | Commit the oldest instruction's architectural effects, take precise exceptions, or perform redirects in program order. |

The stage names are architectural implementation vocabulary for v0.1 RTL, simulator, tracing, and verification. They do not require a fixed number of flip-flop boundaries or mandate that every instruction performs useful work in every stage.

## Single-issue and In-order Rules

The baseline pipeline is single-issue:

- At most one architectural instruction is accepted from `ISS` into execution for each core cycle.
- Instructions are assigned an in-order sequence as they pass through the pipeline.
- `RT` considers instructions in that sequence order.
- A younger instruction cannot retire before an older instruction.
- A younger instruction cannot make an architectural state update if an older instruction has not retired or been killed.

Implementations may allow limited internal overlap, such as instruction fetch continuing while an older instruction is in memory or a long-latency unit. That overlap is permitted only if the retire order and precise-exception rules remain identical to the in-order model.

## Fetch and Predecode Flow

`FE0`, `FE1`, and `PD` implement the fetch-group rules from E04-S01.

Required behavior:

- `FE0` tracks `PCC.cursor` and `PCC.slot`.
- Explicit redirects target slot 0 unless the owning story defines a slot-aware restore path such as `IRET`.
- `FE1` fetches a 48-bit fetch group aligned to an even cell address.
- `FE1` performs or initiates instruction-side translation and fetch permission checks.
- `PD` selects the current instruction from the fetched group using the hidden slot state.
- `PD` detects illegal 24-bit or 48-bit starts at slot 1.
- `PD` detects illegal 48-bit starts in the second cell of a fetch group.
- `PD` supplies the decoded instruction length to later stages for sequential fall-through and trap/debug resume policy.

Fetch, predecode, and translation may run ahead of retire, but younger fetched or decoded instructions must be killable on branch redirect, trap, interrupt, debug entry, or reset.

## Translation and Decode Flow

`XLT` performs architectural decode into the implementation operation representation.

Required behavior:

- Unsupported, malformed, or reserved encodings are identified no later than `XLT`.
- Operand register indexes, immediate fields, CSR indexes, capability register indexes, condition codes, and instruction class are available to `ISS`.
- The internal operation must retain enough original architectural information for precise reporting, including faulting PC, slot, instruction length, and selected cause data.

An implementation may fuse, split, or annotate internal operations only if the externally visible instruction still retires as one architectural instruction with the atomic effects required by E07-S03.

## Execute and Memory Flow

`EX` handles non-memory execution and address generation.

Typical `EX` work:

- Integer arithmetic and logical operations.
- Flag result calculation.
- Branch condition evaluation and target calculation.
- Capability cursor, bounds, permission, seal, and unseal operations that do not access memory.
- Effective address generation for loads, stores, atomics, stack operations, and cache maintenance.

`MEM` handles operations that need data-side translation, cache/coherence state, or memory tag state.

Typical `MEM` work:

- DTLB lookup or page-table-walk initiation.
- Data and capability effective-access checks.
- L1D/L2 data access.
- `LD48`, `ST48`, `CLC`, `CSC`, `LL48`, and `SC48` memory-side effects.
- Capability tag load, store, or clear behavior.
- Cache-maintenance range access checks and maintenance requests.

The final access check priority remains owned by E09-S07 and the instruction-specific stories. E13-S01 fixes where this work belongs in the pipeline model, not a new fault priority.

## Writeback and Retire Flow

`WB` gathers completed results and makes them available to `RT`.

`WB` may prepare:

- Integer register write values.
- Condition flag write values.
- General capability payload and tag write values.
- Scalar CSR write values.
- Special capability register payload, tag, and hidden slot write values.
- Memory store payload and tag effects that are ready to become architectural.
- Trap, interrupt, debug, or redirect packets.

`RT` commits exactly one oldest architectural instruction or entry event at a time.

At `RT`, exactly one outcome is selected:

| Outcome | Effect |
| --- | --- |
| Normal retire | Commit all normal effects of the oldest instruction and increment `INSTRET` according to E12-S04. |
| Exception retire | Commit no normal effects of the faulting instruction and enter the E07-S04 trap path. |
| Redirect retire | Commit the redirecting instruction's normal control-flow effects and kill younger wrong-path work. |
| Interrupt/debug entry | Enter at a precise boundary after older instructions retire and before a younger instruction commits. |

No architectural observer may see a partial `RT` commit.

## Precise Exceptions

`RT` is the precise-exception point for the v0.1 pipeline.

Rules:

- A fault detected in any earlier stage is carried with the instruction until `RT`.
- If an older instruction is still pending, a younger detected fault waits and cannot trap first.
- When a faulting instruction reaches `RT`, it commits none of its normal effects.
- Younger work in `FE0` through `WB` is killed or made architecturally irrelevant before trap entry becomes visible.
- Older retired stores may remain in the store buffer according to E07-S03 and E08-S03.
- Trap entry itself is an atomic architectural update after the selected exception reaches `RT`.

This story does not change the fault priority defined by E07-S02, E07-S03, E09-S07, or instruction-specific stories.

## Redirects and Front-end Recovery

Control-flow redirects are resolved in order.

Rules:

- Direct branch, conditional branch, call, return, `IRET`, trap, interrupt, debug, and reset redirects update `FE0` only through an architecturally selected redirect packet.
- A redirect kills younger fetched, decoded, issued, or completed wrong-path work.
- The pipeline must restore `PCC.cursor`, `PCC.slot`, and `SR.SLOT` according to the redirecting instruction or entry path.
- A wrong-path instruction must not update registers, CSRs, memory, capability tags, return-stack state, counters, or debug state.

Branch prediction details are deferred to E13-S04. Until then, an implementation may predict not-taken, stall until branch resolution, or use a conservative local predictor if it preserves these recovery rules.

## Trace and Verification Model

For simulator, RTL, and verification traces, each in-flight instruction should be representable with:

| Field | Purpose |
| --- | --- |
| Sequence number | Establishes in-order retirement and kill behavior. |
| `PCC` payload/tag and slot | Identifies the architectural instruction location and authority. |
| Instruction length | Supports fall-through, trap resume, and slot tests. |
| Stage | One of `FE0`, `FE1`, `PD`, `XLT`, `ISS`, `EX`, `MEM`, `WB`, `RT`, or implementation sub-state. |
| Pending result packet | Captures normal effects waiting for `RT`. |
| Pending fault packet | Captures selected precise exception information. |
| Redirect packet | Captures branch, trap, interrupt, debug, or reset redirect information. |

This trace vocabulary is recommended for conformance tests, pipeline traces, and simulator logging. Implementations may use different internal names if their architectural trace can be mapped back to these stages.

## Out of Scope for This Story

- Independent multiply/divide unit timing and busy tracking: E13-S02.
- Detailed bypass, scoreboard, interlock, branch flush, and replay rules: E13-S03.
- Branch predictor structure, return prediction, and predictor flushing or partitioning: E13-S04.
- Exact finite-state-machine encodings for cache, TLB, page walker, or store buffer.
- Physical timing, cycle count per stage, and silicon implementation constraints.
- Multi-issue, out-of-order, or speculative commit designs.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Pipeline traces expose or map to `FE0`, `FE1`, `PD`, `XLT`, `ISS`, `EX`, `MEM`, `WB`, and `RT`.
- Only one architectural instruction issues per cycle in the baseline model.
- Instructions retire in program order.
- A younger completed instruction cannot retire before an older stalled instruction.
- A 24-bit instruction at slot 1 is detected before retire and traps precisely at `RT`.
- A 48-bit instruction at the second cell of a fetch group traps precisely at `RT`.
- A branch redirect kills younger wrong-path work before any younger state update.
- A load/store fault detected in `MEM` is reported only when that instruction reaches `RT`.
- A faulting store creates no store-buffer entry at `RT`.
- A trap entry after a fault captures the faulting `PCC` and slot.
- A successful multi-effect instruction commits all effects at `RT` or none on fault.
- Interrupt and debug entry occur only at precise boundaries between retired instructions.
- `INSTRET` increments only for normal retire outcomes.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Pipeline is single-issue and in-order. | Met. |
| Stages are named `FE0`, `FE1`, `PD`, `XLT`, `ISS`, `EX`, `MEM`, `WB`, and `RT`. | Met. |
| Each stage has a short responsibility. | Met. |
| Retire is the precise-exception point. | Met. |

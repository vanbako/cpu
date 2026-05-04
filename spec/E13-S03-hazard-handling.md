# E13-S03: Hazard Handling

Story: E13-S03

Status: Complete

Normative source: `design.md`, section 16.3

Prerequisites:

- `spec/E13-S01-pipeline-stages.md`
- `spec/E13-S02-long-latency-mdu.md`

Related sources:

- `spec/E04-S02-integer-operation-set.md`
- `spec/E04-S03-memory-operation-set.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S07-effective-access-rule.md`

## Decision

CPU v0.1 requires explicit hazard handling for the single-issue in-order pipeline:

- Bypass or forward results from `EX`, `MEM`, and `WB` where the value is available early enough.
- Track busy architectural destinations with a scoreboard or equivalent busy-bit mechanism.
- Stall on load-use and other unavailable-result dependencies.
- Flush younger wrong-path work on branch, trap, interrupt, debug, and reset redirects.
- Kill or replay in-flight work without violating precise exceptions.

The implementation may choose exact mux placement, scoreboard encoding, and replay buffering, but the externally visible behavior must match this story.

## Hazard Classes

The pipeline must handle these hazard classes:

| Hazard class | Meaning | Required response |
| --- | --- | --- |
| RAW | Younger instruction reads a value produced by an older instruction. | Forward if available; otherwise stall until available. |
| WAW | Younger instruction writes the same architectural destination as an older in-flight instruction. | Preserve in-order retire and final program-order value. |
| Structural | Required pipeline, cache, TLB, MDU, writeback, or retire resource is unavailable. | Stall at or before `ISS` until resource is available. |
| Control | Younger fetched work is on the wrong path after a redirect. | Flush or mark killed before any architectural update. |
| Exception | Older instruction faults while younger work is in flight. | Kill or replay younger work and take the older precise exception. |
| Memory ordering | Load/store interaction with same-core store buffer or fences. | Preserve E08-S03 and E08-S04 ordering. |

Because the pipeline retires in order, WAR hazards are avoided by construction: a younger read cannot retire before an older write, and if it needs the older value it must use forwarding or stall under RAW rules.

## Scoreboard and Busy State

The pipeline must track pending writes to architectural destinations.

At minimum, busy tracking must cover:

- Integer registers `D0-D15`.
- General capability registers `C0-C7`.
- Special capability registers when written by explicit instructions or trap/interrupt/debug entry.
- Scalar CSRs targeted by CSR instructions.
- Hidden `PCC.slot` and `EPCC.slot` when a slot-aware operation is in flight.
- Memory-side store or capability-store effects that have not reached their architecturally allowed commit point.

Rules:

- An instruction marks its destination busy when it issues or when the pipeline otherwise commits to producing that destination.
- A busy mark records enough age information to distinguish the oldest producer from younger producers.
- A consumer may issue only if every required source is available from the register file, a bypass path, or a documented forwarding path.
- If a source is busy and no valid forwarding path can supply the value for the consuming stage, the consumer stalls.
- Busy state is cleared on normal retire, precise fault handling, redirect kill, debug entry kill, interrupt entry kill, or reset kill as applicable.

An implementation may use a centralized scoreboard, per-register busy bits plus sequence tags, reservation metadata, or another equivalent structure.

## Bypass and Forwarding

The implementation must provide bypassing where the producing value is available soon enough to avoid a needless stall.

Required forwarding classes:

| Producer | Consumer | Requirement |
| --- | --- | --- |
| `EX` integer ALU result | Younger `EX` integer or address-generation operand | Forward when adjacent ALU dependencies would otherwise stall. |
| `EX` capability derivation result | Younger capability or memory-address operand | Forward when the derived capability is available before the consumer needs it. |
| `MEM` load result | Younger `EX` or `MEM` consumer | Forward when the load data has returned early enough for the consumer cycle; otherwise use load-use interlock. |
| `MEM` capability load result | Younger capability consumer | Forward payload and tag together or stall. |
| `WB` result packet | Any younger source read | Forward instead of requiring a register-file write/read timing assumption. |
| MDU `WB` result | Younger integer consumer | Forward through normal `WB` result forwarding or stall until register write. |

Forwarded capability values must include payload and tag together. A forwarded capability tag must not be separated from its matching payload.

Forwarding must not bypass privilege, capability, page, alignment, or memory-type checks. A value from a faulting instruction is never forwarded as a valid architectural result.

## Load-use Interlock

Loads and capability loads may produce results later than adjacent consumers need them.

Required behavior:

- If a younger instruction needs a value from an older `LD48`, `LL48`, `CLC`, or other load before that value is available, the younger instruction stalls.
- If a load faults, no dependent younger instruction may consume a speculative value.
- A `CLC` dependency includes both payload and tag readiness.
- A failed non-trapping `SC48` produces its result code through the normal integer result path and must obey the same dependency rules as other integer-producing operations.
- A successful `SC48` has both a result-code destination and memory effects. Consumers of the result code follow integer dependency rules; memory ordering follows E08-S03.

A one-cycle load-use stall is permitted but not required. The actual stall length is implementation-dependent and may be longer for TLB misses, cache misses, page walks, or cache-maintenance interactions.

## Store-buffer and Memory Hazards

Stores retire in order but may remain in the same-core store buffer according to E08-S03.

Required behavior:

- A store cannot allocate an architectural store-buffer entry until it is allowed to retire normally.
- A faulting or killed store must not allocate a store-buffer entry.
- A younger same-core load must observe older same-core buffered stores to overlapping cells or capability slots according to E08-S03 forwarding rules.
- A younger `CLC` after an older buffered overlapping `ST48` or successful `SC48` must observe the local tag clear required by E08-S03.
- A younger `CLC` after an older buffered `CSC` to the same slot must observe the buffered payload and tag together.
- `FENCE` stalls younger data-memory operations until older data-memory and cache-maintenance operations meet the completion rule from E08-S04.

Memory disambiguation may be conservative. A simple implementation may stall younger loads behind older unresolved stores until the store address and overlap are known.

## Structural Hazards

The pipeline must stall rather than dropping or corrupting work when a required resource is unavailable.

Structural resources include:

- Instruction fetch interface.
- DTLB, ITLB, or page-walker path.
- L1D or L1I access port.
- L2 or coherence request path.
- Store buffer entry.
- MDU entry or divider slot.
- Writeback result path.
- Retire commit path.
- Trap, interrupt, or debug entry update path.

When a structural stall occurs, older instructions continue if possible and younger instructions remain in their current stage or are prevented from entering the blocked stage. The stall must not reorder retirement or create duplicate architectural effects.

## Control Hazards and Flush

Control redirects are resolved through the ordered redirect rules from E13-S01.

Redirect sources include:

- Taken `BRA`.
- Taken `Bcc`.
- `CALL` and `CALLC`.
- `RET`.
- `JMP`.
- `IRET`.
- `BRK`, `SYS`, `SCALL`, and other synchronous traps.
- Interrupt entry.
- Debug entry.
- Reset and fatal platform redirection.

When a redirect is selected:

- `FE0` receives the selected redirect target, slot, and authority.
- Younger fetched, decoded, issued, executing, memory, and writeback-stage wrong-path work is flushed or marked killed.
- Killed wrong-path work must not update registers, CSRs, special capability registers, memory, capability tags, return-stack state, counters, debug state, or predictor state in a way that changes architectural behavior.
- Any busy marks allocated for killed younger instructions are cleared.
- Any MDU operation belonging to a killed younger instruction is canceled, ignored at completion, or tagged invalid.

Branch predictor details are owned by E13-S04. This story requires only that any wrong-path prediction is recoverable before architectural state is changed by the wrong-path instructions.

## Exception Kill and Replay

Precise exceptions require kill or replay support for in-flight younger work.

Rules:

- A fault packet detected before `RT` stays attached to that instruction's sequence number.
- The oldest pending fault reaches `RT` before younger faults or younger normal results.
- When the oldest instruction faults at `RT`, younger work is killed or made replayable before trap entry becomes visible.
- A replayed instruction must reperform all checks whose result could have changed.
- A replayed memory instruction must not duplicate a retired memory payload write or tag update.
- A replayed `LL48`/`SC48` must preserve the E08-S01 and E08-S02 reservation and failure rules.
- A replayed CSR, CCSR, or special-register operation must not duplicate side effects from a prior non-retired attempt.

Replay is an implementation technique, not an architectural event. Software observes only the final precise retire, fault, or redirect behavior.

## Counter and Debug Interaction

Hazard stalls do not by themselves increment `INSTRET`.

Rules:

- `INSTRET` increments only when `RT` performs a normal retire, according to E12-S04.
- Killed or replayed internal attempts do not increment `INSTRET`.
- A debug halt request is accepted at a precise boundary. Younger work is killed before `DEBUG_HALTED` becomes visible.
- Debug-monitor entry uses the same precise kill rule as trap and interrupt entry.
- `CYCLE` may continue to increment during stalls according to E12-S04.

## Out of Scope for This Story

- Exact branch predictor structure and update policy: E13-S04.
- Exact MDU algorithms and latencies beyond E13-S02.
- Cache, TLB, and page-walker finite-state-machine details.
- Store-buffer depth, coalescing policy, and coherence transient states beyond architectural ordering.
- Speculative side-channel mitigation beyond the explicit predictor and context rules in E13-S04.
- Multi-issue, out-of-order scheduling, or speculative architectural commit.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Adjacent integer ALU dependencies use EX/MEM/WB forwarding or stall until correct.
- A capability derivation followed by a capability memory access observes the derived capability payload and tag together.
- A load-use dependency stalls until the loaded value is available.
- A `CLC` use dependency stalls or forwards payload and tag together.
- A failed non-trapping `SC48` result code is available through the normal integer dependency path.
- A dependent instruction cannot consume a value from a faulting producer.
- MDU destination busy state blocks or forwards dependent consumers.
- A second divide stalls behind a busy single-entry divider.
- A store that faults does not allocate a store-buffer entry.
- A same-core load after an older buffered same-address store observes store-buffer forwarding.
- `FENCE` prevents younger data-memory operations until older required operations complete.
- A taken branch flushes younger fall-through work before it updates architectural state.
- A branch misprediction increments no architectural counter except through normally retired instructions.
- An older exception kills a younger completed instruction before the younger instruction retires.
- A replayed load does not duplicate a store or tag update.
- A killed MDU result is ignored when it later completes.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| EX, MEM, and WB bypassing is required where possible. | Met. |
| Scoreboard or busy-bit tracking is required. | Met. |
| Load-use interlock is required. | Met. |
| Branch mispredict flush is required. | Met: all control redirects, including wrong-path branch predictions, flush younger work. |
| Precise exception replay or kill behavior is required. | Met. |

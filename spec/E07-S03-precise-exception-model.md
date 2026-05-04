# E07-S03: Precise Exception Model

Story: E07-S03

Status: Complete

Normative source: `design.md`, sections 10.2, 10.3, 16.1, 16.2, and 16.3

Prerequisite:

- `spec/E07-S02-exception-classes.md`

Related sources:

- `spec/E01-S02-integer-register-semantics.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spec/E08-S03-tso-memory-model.md`

## Decision

All CPU v0.1 exceptions are precise.

For any synchronous exception, the architectural state observed by the trap handler is equivalent to sequential execution in which:

1. Every older instruction has completed and committed its architectural effects.
2. The faulting instruction has committed no normal architectural effects.
3. Every younger instruction has committed no architectural effects.
4. Trap-entry state identifies the faulting instruction and the selected exception cause.

This is the architectural contract. Implementations may use predecode queues, scoreboards, bypass paths, store buffers, or long-latency units, but those structures must produce the same precise state at trap entry.

## Architectural Retire Point

An instruction reaches the architectural retire point after all checks needed for its normal architectural effects are known.

At retire, exactly one of these outcomes occurs:

| Outcome | Architectural effect |
| --- | --- |
| Normal retire | All normal effects of the instruction become committed atomically for architectural state. |
| Exception retire | No normal effects of the instruction commit; trap-entry state is produced for the exception. |
| Redirect retire | The instruction commits its normal redirect effects, such as a branch or call target, and younger wrong-path work is discarded. |

Normal committed effects include:

- Integer register writes.
- Condition-code updates.
- General capability register payload and tag writes.
- Special capability register payload, tag, and hidden slot writes.
- Scalar CSR writes.
- Memory payload writes.
- Memory capability-tag writes or tag clears.
- `PCC` cursor and slot updates.
- Stack and protected return-stack cursor updates.

An instruction with multiple normal effects commits them as one architectural action. No trap, interrupt, debug entry, or younger instruction can observe a partially committed instruction.

## Faulting Instruction State

For a precise synchronous exception, hardware captures a pending exception packet containing:

- Faulting `PCC` payload and tag.
- Faulting `PCC` hidden slot.
- Selected `CAUSE`.
- Selected `TVAL`.
- Selected `CAPCAUSE`.
- Selected `FAULTCAPIDX`.

`EPCC` is the architectural destination for the faulting `PCC` and hidden slot during trap entry. E07-S04 defines the exact trap-entry write sequence and direct trap target calculation.

Until trap entry updates `PCC`, the faulting `PCC` remains the architectural current instruction location. Trap entry then installs the trap handler execution state.

## Fault Atomicity

A faulting instruction leaves normal architectural state unchanged.

On exception retire:

- Integer destination registers are unchanged.
- General capability destination registers are unchanged.
- Scalar CSRs targeted by the faulting instruction are unchanged.
- Special capability registers targeted by the faulting instruction are unchanged.
- `PCC` remains the faulting instruction location until trap entry redirects execution.
- `DSC`, `RSC`, `DDC`, `KSC`, `KRC`, `TVC`, and `EPCC` are unchanged except for trap-entry updates defined by E07-S04.
- Memory payload is unchanged.
- Memory capability tags are unchanged.
- Store-buffer entries for the faulting instruction are not created.
- `INSTRET` does not increment for the faulting instruction.

Reporting state written by trap entry is not considered a normal effect of the faulting instruction. `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, `EPCC`, and `SR` trap fields are updated by the trap-entry mechanism, not by the faulting instruction's normal commit path.

## Younger Instruction Suppression

Younger instructions must not commit state after an older instruction is selected for exception.

If younger work has been fetched, decoded, issued, partially executed, or completed internally, the implementation must kill or replay it before trap entry becomes architecturally visible.

Younger work must not:

- Write integer or capability registers.
- Write scalar CSRs or special capability registers.
- Update `PCC` or `SR.SLOT`.
- Enqueue memory writes into the architectural store buffer.
- Write memory payload or memory tags.
- Clear capability tags through `ST48`.
- Update `DSC` or `RSC`.
- Update return-stack memory.
- Increment `INSTRET`.

The only permitted younger effects are microarchitectural effects that are not architecturally visible and are either flushed or harmless under the v0.1 memory and security model. Cache fills and predictor updates are refined by E08, E10, E12, and E13 stories.

## Older Store-buffer State

The TSO memory model allows a store to retire before it becomes globally visible.

For precise exceptions:

- Older retired stores may still reside in the same core's store buffer at trap entry.
- Those stores are part of the architectural state because the older store instructions have retired.
- Same-core trap-handler loads observe older buffered stores according to E08-S03 forwarding rules.
- Trap entry does not implicitly drain the store buffer unless a later trap or fence story defines a stronger rule.
- Younger or faulting stores must not allocate store-buffer entries.

This preserves precise exceptions without weakening the TSO store-buffer contract.

## Long-latency Operations

Long-latency operations, including multiply, divide, modulo, and future multi-cycle operations, must report completion and exceptions in program order at retire.

Required behavior:

- Issue marks the destination register or architectural destination busy.
- Independent younger instructions may execute only if the implementation can still prevent them from committing before the long-latency instruction retires.
- Dependent younger instructions wait until the value is available through bypass or writeback according to the pipeline story.
- The long-latency result is not architectural until the instruction retires.
- A long-latency exception is retained with the instruction until it reaches retire.
- If an older instruction faults, any younger in-flight long-latency operation is killed or made architecturally irrelevant.

Examples:

- `DIV` or `MOD` by zero reports `DIVIDE_BY_ZERO` when that instruction reaches retire.
- A multi-cycle `MUL` that has produced a result internally does not update its destination register if an older instruction faults first.
- MDU completion is not exposed through a CSR and cannot be observed as a partial architectural side effect.

## Atomic Multi-effect Instructions

Instructions with multiple architectural effects must be all-or-nothing.

Required atomic commit examples:

| Instruction family | Atomic effects |
| --- | --- |
| `CSRSET` / `CSRCLR` | Destination integer write and scalar CSR update. |
| `CCSRWR PCC, Cs` | Special capability payload/tag copy and `PCC.slot = 0`. |
| `CLC` | Destination capability payload and tag load. |
| `CSC` | Memory capability payload and tag store. |
| `ST48` | Two-cell payload write and any overlapped capability-tag clear. |
| `CALL` | Sealed return capability store, return-stack tag update, `RSC.cursor`, and `PCC` target update. |
| `RET` | Protected return-stack pop, `RSC.cursor`, and `PCC` installation. |
| Trap entry | `EPCC`, `SR`, `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, and trap-target `PCC` updates. |

If any check for a multi-effect instruction fails, none of its normal effects commit.

E06-S04 refines trap/debug interactions with protected return-stack state, but it must preserve this all-or-nothing contract.

## Deterministic Fault Selection

If more than one fault condition is possible for the same instruction, hardware must select one deterministic exception.

Selection rules:

1. Use the default priority table in E07-S02.
2. Within an instruction family, use the check order defined by the owning instruction story.
3. If the instruction story does not define an order, use the earliest architecturally required check that can determine the fault without committing state.
4. If capability and MMU/effective-access faults interact, use E09-S07 once that story is defined.
5. Report the selected fault consistently for the same architectural input state.

Capability reporting follows the selected fault. `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL` identify the selected capability fault, not every latent fault that might also have been true.

## Capability and MMU Fault Priority

Until E09-S07 finalizes the full effective-access matrix, E07-S03 fixes these constraints:

- Instruction fetch must first pass `PCC` authority checks before an instruction can retire.
- Decode and instruction-placement faults are reported before any data-memory side effect.
- Capability operand tag, seal/type, and instruction-local permission checks defined by an instruction story occur before memory payload or tag updates.
- Address-generation overflow or underflow is reported before translation or cache access.
- Alignment faults are reported before memory payload or tag updates.
- No page fault, access fault, or capability fault may expose a partial data or tag update.
- The same architectural state must not sometimes report a capability fault and sometimes a page fault because of timing.

E09-S07 may choose the final order between capability bounds, page validity, page permissions, privilege page bits, memory type, and access fault checks for effective data and instruction accesses. It must keep the result deterministic and precise.

## Interrupt Interaction

Synchronous exceptions take priority over ordinary maskable interrupts for the same retirement point.

Rules:

- If the oldest retiring instruction has a synchronous exception, trap that exception before delivering a maskable interrupt.
- If no synchronous exception is pending and interrupts are enabled and deliverable, interrupt delivery may occur at an instruction boundary.
- Interrupt delivery observes a precise boundary after older instructions have retired and before the next instruction commits.
- Interrupt entry must not split the commit of a multi-effect instruction.

E07-S05 defines interrupt cause values, priority, threshold behavior, and vectored interrupt target calculation.

## Commit and Counter Rules

`INSTRET` increments once for each instruction that normally retires.

Rules:

- Faulting instructions do not increment `INSTRET`.
- Instructions killed before retirement do not increment `INSTRET`.
- `SYS`, `SCALL`, and `BRK` are synchronous traps and do not increment `INSTRET` unless a later counter story explicitly changes this accounting.
- Interrupt entry does not by itself increment `INSTRET`.
- Trap-handler instructions increment `INSTRET` when they normally retire.

`CYCLE` and `TIMER` behavior is independent of precise exception retirement and is refined by E12-S04.

## Out of Scope for This Story

- Direct trap-entry write sequence and trap target calculation: E07-S04.
- Interrupt cause values, priority, thresholds, and vectoring: E07-S05.
- Full effective access priority across capability, translation, page privilege, memory type, and access faults: E09-S07.
- Debug halt, breakpoint policy, and single-step completion priority: E12 stories.
- Concrete pipeline stages, bypassing, scoreboards, and replay machinery: E13 stories.
- Exact integer instruction table and divide/modulo semantics: E04-S02.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- A faulting instruction leaves integer destination registers unchanged.
- A faulting instruction leaves general capability destination registers unchanged.
- A faulting instruction leaves scalar CSRs and special capability registers unchanged except for trap-entry reporting updates.
- A faulting store does not write memory payload, enqueue a store-buffer entry, or clear memory tags.
- A faulting `CSC` does not write payload or tag.
- A faulting `CSRSET` does not update either destination register or target CSR.
- A faulting `CCSRWR` does not update the target special capability register.
- `EPCC` captures the faulting `PCC` payload and hidden slot.
- Younger instructions that completed internally before an older fault do not update architectural state.
- A divide-by-zero in a long-latency divider reports `DIVIDE_BY_ZERO` at retire and does not update the destination register.
- An older exception kills or suppresses a younger in-flight MDU result.
- A retired older store may remain buffered across trap entry and is observed by same-core trap-handler loads according to TSO forwarding.
- `CALL` either commits the return-stack update and `PCC` update together or commits neither.
- `RET` either commits the return-stack pop and `PCC` installation together or commits neither.
- A synchronous exception takes priority over an ordinary maskable interrupt at the same instruction boundary.
- Repeating the same architectural state produces the same selected capability/MMU fault.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| All exceptions are precise. | Met. |
| Faulting instruction state is captured in `EPCC`. | Met. |
| Younger instructions are prevented from committing state. | Met. |
| Long-latency operations report exceptions at retire. | Met. |
| Capability and MMU faults have deterministic priority. | Met. |

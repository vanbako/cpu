# E15-S03: Architectural State-transition Audit

Story: E15-S03

Status: Complete

Prerequisite:

- `spec/E15-S01-terminology-cross-reference-audit.md`

## Decision

The v0.1 architectural state-transition contract is internally consistent for reset, secondary startup, trap and interrupt entry, debug entry and exit, `IRET`, `CALL`, `CALLC`, `RET`, protected return-stack maintenance, `WFI`, `PAUSE`, and single-step interactions after the correction listed below.

No unresolved blocking state-transition inconsistency remains in this audit scope.

The full same-cycle event-priority matrix remains owned by E15-S04. This audit checks that each transition has compatible committed, preserved, restored, killed, and invalidated state once the winning event is selected.

## Corrections Applied

| Finding | Severity | Correction |
| --- | --- | --- |
| E15-S03-F01: E11-S02 said trap entry through invalid `TVC` followed ordinary capability tag-fault behavior, while E07-S04 and E07-S05 define invalid `TVC` or vector state as fatal trap-entry or interrupt-entry failure rather than recursive normal trap delivery. | Blocking wording inconsistency | Updated `spec/E11-S02-reset-capability-state.md` to distinguish ordinary invalid-capability uses from invalid `TVC` entry failure and to point diagnostic reporting at `FAULTCAPIDX=TVC` and `CAPCAUSE=TAG`. |

## Audit Scope

This audit cross-checks state transitions in:

- `spec/E11-S01-cold-reset-state.md`
- `spec/E11-S02-reset-capability-state.md`
- `spec/E11-S03-secondary-core-startup.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S04-trap-entry.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E07-S06-nested-interrupt-rules.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E06-S02-sealed-entry-capabilities.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E12-S01-debug-halt-behavior.md`
- `spec/E12-S02-hardware-breakpoints-watchpoints.md`
- `spec/E12-S03-single-step.md`
- `spec/E13-S01-pipeline-stages.md`
- `spec/E13-S03-hazard-handling.md`

## State-transition Ledger

| Transition | Owner specs | Commits | Preserves or restores | Kills or invalidates | Audit result |
| --- | --- | --- | --- | --- | --- |
| Cold reset, boot core | E11-S01, E11-S02 | `COREID=0`, lifecycle `RUNNING`, reset `PCC` at `RESET_VECTOR`, `PCC.slot=0`, reset scalar CSRs, `SATP=0`, `ASID=0`, no valid LL reservation, cache state disabled or invalid. | Reset `PCC` is valid ROM execute authority. Broader `KRC`, `KSC`, `DSC`, `RSC`, and `TVC` may be installed by reset logic or firmware before use. | No partial retire; stale cache, TLB, interrupt latch, and LL state cannot survive as architecturally valid state. Reset does not write trap-reporting state. | Pass. Reset is not modeled as trap entry and therefore cannot collide with `EPCC` or `CAUSE` ownership. |
| Cold reset, secondary cores | E11-S01, E11-S03 | `COREID=1-3`, lifecycle `STOPPED` or reset-time `WFI_PARKED`. | Existing platform-reset lifecycle choice is documented by the implementation. | Secondary cores do not fetch, retire, mutate memory, update counters, or expose partial capability state before startup. | Pass. Reset parking and secondary startup use the same lifecycle names. |
| Secondary startup success | E11-S03, E11-S02, E07-S05 | Lifecycle `STARTED`, valid `PCC=entry_pcc`, `PCC.slot=0`, `SR.PRIV=K`, `SR.IE=0`, `SR.EXL=0`, `SR.SLOT=0`, `SATP=0` unless profiled, `ASID=0`, `DSC` and `RSC` valid before use, `IENABLE=0`, startup argument registers. | Optional `KSC`, `KRC`, `TVC`, `DDC`, and `arg_cap0` are preserved with valid tags only through trusted authority paths. | Failed validation consumes the start attempt and does not expose partial startup state. A start signal sent to an already `STARTED` core does not replace live execution state. | Pass. Startup is a lifecycle transition, not ordinary interrupt entry. |
| Secondary startup failure | E11-S03 | Lifecycle `START_FAILED` or documented parked state, mailbox `FAILED`, `failure_code` where exposed. | Previous parked core cannot execute the requested entry point. | Invalid `PCC`, stack, root, vector, mailbox generation, or target-core state does not partly install architectural state. | Pass. Failure does not require a valid `TVC`, matching reset-capability rules. |
| Synchronous trap entry | E07-S03, E07-S04, E13-S01 | `EPCC` payload/tag/slot from faulting `PCC`, `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, `SR.PIE`, `SR.IE=0`, `SR.PPRIV`, `SR.PRIV=K`, `SR.EXL=1`, `PCC=TVC`, `PCC.slot=0`, `SR.SLOT=0`. | Faulting instruction normal effects do not commit; older retired state remains architectural. `DSC`, `RSC`, `DDC`, `KSC`, `KRC`, and `TVC` are not automatically pushed or modified by entry. | Younger work is killed. Trap entry does not increment `INSTRET`. Invalid `TVC` causes fatal trap-entry failure rather than recursive normal trap entry. | Pass. One hardware saved level is consistently defined. |
| Maskable interrupt entry | E07-S05, E07-S06, E13-S01 | `EPCC` from interrupted next `PCC`, interrupt `CAUSE`, `TVAL=0`, `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`, `SR.PIE`, `SR.IE=0`, `SR.PPRIV`, `SR.PRIV=K`, `SR.EXL=1`, vector `PCC`, `PCC.slot=0`, `SR.SLOT=0`. | Pending source is not cleared automatically. General registers, capability registers, stacks, `TVC`, and platform controller state are software responsibilities. | Younger work is killed. Entry does not increment `INSTRET`. Invalid vector state causes fatal interrupt-entry failure, not a synchronous trap through the same invalid vector. | Pass. Interrupt entry shape matches trap entry while preserving interrupt-specific reporting. |
| Nested trap or interrupt | E07-S04, E07-S05, E07-S06 | A second successful entry overwrites the one hardware saved level. | Software-preserved frames must include `EPCC.slot`, `SR.PIE`, `SR.PPRIV`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX` when needed. | Hardware does not infer or allocate nested trap frames. Ordinary maskable interrupts remain blocked while `SR.EXL=1` unless software explicitly restores a deliverable state. | Pass. The one-level hardware rule is consistent across entry and return. |
| `IRET` success | E04-S04, E07-S06, E12-S01, E12-S03 | `PCC.payload/tag/slot = EPCC`, `SR.SLOT=EPCC.slot`, `SR.IE=SR.PIE`, `SR.PRIV=SR.PPRIV`, `SR.EXL=0`. If `DEBUGCTL.STEP=1`, successful return arms `STEP_ACTIVE` for the restored context. | `EPCC`, `SR.PIE`, `SR.PPRIV`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX` remain unchanged. Pending interrupts are not cleared. | No partial restore is visible. If interrupts are deliverable after restore, delivery may occur at the next precise boundary. | Pass. Slot-aware restore is consistent with `EPCCRD`/`EPCCWR` and pipeline redirect rules. |
| `IRET` fault | E04-S04, E07-S04, E07-S06 | No normal `IRET` restore effects commit; the fault follows synchronous trap entry. | Pre-fault `PCC`, `SR.IE`, `SR.PRIV`, and `SR.EXL` remain until trap entry commits. | Current one-level saved state may be overwritten by the `IRET` fault if software did not save it. | Pass. Fault behavior follows the precise exception model. |
| Non-monitor debug halt entry | E12-S01, E12-S02, E12-S03, E13-S03 | `DEBUGCTL.HALTED=1`, `HALTREQ=0`, selected `DCAUSE`, `CAUSE=DEBUG_HALT`, source `TVAL`, `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`; debug entry clears LL reservation. | Current `PCC` and `PCC.slot` are preserved; `SR.PRIV`, `SR.IE`, `SR.EXL`, `SR.PIE`, `SR.PPRIV`, registers, memory, and `EPCC` are preserved. | No ordinary instruction retires while halted. Younger work is killed before `DEBUG_HALTED` is visible. `STEP_ACTIVE` is clear. | Pass. Non-monitor halt is not trap entry and therefore does not consume the one hardware saved level. |
| Debug-monitor entry | E12-S01, E12-S02, E12-S03, E07-S06 | `EPCC` from interrupted or faulting `PCC`, `CAUSE=DEBUG_HALT`, source `TVAL`, `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`, `SR.PIE`, `SR.IE=0`, `SR.PPRIV`, `SR.PRIV=K`, `SR.EXL=1`, debug vector `PCC`, `PCC.slot=0`, `SR.SLOT=0`, `HALTREQ=0`, `HALTED=0`, selected `DCAUSE`; debug entry clears LL reservation. | Debug-monitor code exits with ordinary `IRET` and may edit `EPCC` first. Comparators and single-step are suppressed during monitor execution. | Debug-monitor entry overwrites the one hardware saved level. Entry failure falls back to `DEBUG_HALTED` instead of fetching through an invalid vector. | Pass. Debug-monitor state intentionally matches trap/interrupt saved-state shape. |
| Resume from `DEBUG_HALTED` | E12-S01, E12-S03 | `DEBUGCTL.HALTED=0`, `HALTREQ=0`; if `DEBUGCTL.STEP=1`, resume arms `STEP_ACTIVE`. | Execution resumes at current `PCC` and current `PCC.slot`, including any debugger modifications. | No pending interrupt is cleared; a deliverable interrupt may enter before the resumed instruction executes. | Pass. Resume is compatible with both debug and interrupt boundary rules. |
| `CALL` and `CALLC` success | E04-S04, E06-S02, E06-S03, E06-S04, E07-S03 | Sealed local `OTYPE_RETURN` return capability payload and tag are stored through protected `RSC`; `RSC.cursor` is updated; target `PCC` is installed with `PCC.slot=0`. `CALLC` also installs the unsealed entry target only as committed `PCC`. | Caller return authority is derived from current `PCC` and slot-0 continuation. `CALLC` leaves source `Cs` sealed and unchanged. | No trap, interrupt, debug halt, or single-step boundary can observe partial return-stack payload, tag, `RSC.cursor`, or `PCC`. | Pass. Multi-effect call entry matches precise-retire and protected-stack transaction rules. |
| `CALL`, `CALLC`, or `RET` fault | E06-S02, E06-S03, E06-S04, E07-S03 | No normal call or return effects commit; trap entry captures the faulting instruction in `EPCC`. | `RSC`, `PCC`, return-stack memory payload, memory tags, and relevant source/destination registers remain unchanged until trap entry state is produced. | No partial protected return-stack state is visible. | Pass. Fault behavior is all-or-nothing across direct calls, sealed entry calls, and returns. |
| `RET` success | E04-S04, E06-S03, E06-S04 | Protected pop validates a sealed local `OTYPE_RETURN`, advances `RSC.cursor`, and installs the unsealed return target into `PCC` with `PCC.slot=0`. | Popped memory slot is not cleared but becomes inactive after `RSC.cursor` advances. | No partial pop, unsealed return capability, or mismatched `PCC`/`RSC.cursor` state is visible. | Pass. Return state matches the protected return-stack and slot-target rules. |
| Protected return-stack maintenance | E06-S04, E12-S01 | Privileged or debug peek/drop/replace operates only at a precise boundary; drop updates `RSC.cursor`; replace writes one full payload plus tag atomically; peek returns a validated sealed return capability. | Maintenance uses current architectural `RSC` and does not expose raw corrupt authority. Faults leave `RSC`, `PCC`, memory payload, and tags unchanged. | Partial payload/tag replacement, partial drop, and mid-transaction debug boundaries are forbidden. | Pass. Debug unwind authority is compatible with protected-stack atomicity. |
| `WFI` | E04-S04, E07-S05, E11-S03, E12-S01, E12-S03 | If no interrupt is deliverable before execution, `WFI` retires, advances `PCC` to fall-through, may wait, and increments `INSTRET` as a normal retired instruction. | `WFI` does not modify `IPENDING`, `IENABLE`, `SR.IE`, or `SR.EXL`. | If an interrupt is deliverable before `WFI`, interrupt entry occurs and `WFI` does not retire. Debug wakes a waiting core. A stepped `WFI` enters debug after retirement before remaining parked. | Pass. Ordinary `WFI` wait state is distinct from reset-time `WFI_PARKED` lifecycle state. |
| `PAUSE` | E04-S04 | Normal fall-through retirement only. | Flags, CSRs, capability state, memory, interrupt state, and privilege state are unchanged. | None beyond ordinary precise retirement. | Pass. `PAUSE` cannot conflict with trap, debug, or startup state. |
| Single-step completion | E12-S03, E12-S01, E07-S05, E13-S01 | Normal instruction effects and `INSTRET` commit first; then debug event with `DCAUSE=SINGLE_STEP` is accepted before younger instruction retirement and before ordinary maskable interrupt delivery at that post-retire boundary. | Sticky `DEBUGCTL.STEP` remains set unless software clears it. Monitor or halted state suppresses stepping. | `STEP_ACTIVE` clears on step completion, trap entry, interrupt entry, debug entry, or a selected fault/debug event before retire. | Pass. Single-step is a post-retire debug event and does not split multi-effect instructions. |
| Pipeline redirect and kill | E13-S01, E13-S03, E07-S03 | Selected branch, `CALL`, `RET`, `IRET`, trap, interrupt, debug, or reset redirect updates fetch from one architecturally selected packet. | Older retired state remains committed; stores already retired may remain buffered under the memory model. | Younger wrong-path work cannot update registers, CSRs, CCSRs, memory, tags, return-stack state, counters, debug state, or predictor state in an architecturally visible way. | Pass. Pipeline model supplies the common atomic boundary for all audited transitions. |

## Conformance Scenarios

| Scenario | Expected state observation | Result |
| --- | --- | --- |
| Boot core takes cold reset then immediately fetches ROM. | First fetch uses valid reset `PCC.cursor=RESET_VECTOR`, `PCC.slot=0`, `SR.PRIV=K`, `SR.IE=0`, `SR.EXL=0`, `SATP=0`; `EPCC`, `CAUSE`, `TVAL`, and `CAPCAUSE` are not written as reset side effects. | Pass. |
| Secondary core is `WFI_PARKED` and receives a valid start event while `SR.IE=0` and `IENABLE=0`. | Startup validation may proceed because the start event is a lifecycle release, not ordinary maskable interrupt entry. The core enters `STARTED` only after full state installation. | Pass. |
| Secondary core startup has an invalid `entry_pcc` tag. | The core reports startup failure through mailbox or platform lifecycle state and does not fetch through the invalid target or enter normal trap entry through `TVC`. | Pass. |
| Slot-1 instruction faults. | Trap entry captures the faulting `PCC` and `EPCC.slot=1`; handler starts at `TVC.cursor` with slot 0. | Pass. |
| Interrupt is delivered after a 12-bit slot-0 instruction normally retires. | `EPCC` captures the architectural next instruction, so `EPCC.slot=1`; vector handler starts at slot 0. | Pass. |
| Handler preserves a nested trap frame and returns with `IRET`. | Software must restore `EPCC.payload`, `EPCC.tag`, and `EPCC.slot`; `IRET` restores `PCC.slot` and `SR.SLOT` from `EPCC.slot`. | Pass. |
| `IRET` restores `SR.IE=1` with an enabled pending interrupt. | `IRET` completes its restore atomically; interrupt delivery may occur at the next precise boundary before the restored context executes. | Pass. |
| `BRK` with `DEBUGCTL.BRKHALT=1` enters non-monitor debug. | `PCC` remains at the `BRK` instruction, `PCC.slot` is preserved, `EPCC` is unchanged, and resume without adjustment re-executes `BRK`. | Pass. |
| Hardware watchpoint matches a store-like instruction. | Debug event is accepted before the access commits; no store-buffer entry, memory payload, memory tag, or return-stack update from the matched instruction is visible. | Pass. |
| Debug-monitor entry is selected for a single-step completion. | The stepped instruction has already retired; monitor entry saves the next `PCC` and slot in `EPCC`; if monitor vectoring fails, fallback is `DEBUG_HALTED` with the stepped effects preserved. | Pass. |
| `CALLC` succeeds and an interrupt is pending during the internal unseal and protected push. | The interrupt observes either pre-`CALLC` state or full post-commit state; it cannot see an unsealed entry target outside committed `PCC` or a partial return-stack push. | Pass. |
| `RET` finds a corrupt protected return-stack slot. | `RET` faults; `RSC.cursor`, `PCC`, return-stack payload, and tags remain unchanged until trap entry state is produced. | Pass. |
| `WFI` executes while single-step is active and no interrupt is deliverable first. | `WFI` retires, advances `PCC` to fall-through, increments `INSTRET`, then accepts the single-step debug event before remaining parked. | Pass. |
| Reset or branch redirect kills younger fetched work. | Killed wrong-path work cannot update architectural registers, CSRs, capability state, memory, tags, return-stack state, counters, debug state, or predictor state in a visible way. | Pass. |

## Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| E15-S03-F01: E11-S02 treated invalid `TVC` trap entry as an ordinary capability tag fault, while E07-S04 and E07-S05 require fatal entry failure. | Corrected | E11-S02 now distinguishes invalid `TVC` delivery failure from ordinary invalid-capability instruction/data uses. |
| E15-S03-F02: Reset and reset-capability stories agree that reset is not trap entry and does not write `EPCC`, `CAUSE`, `TVAL`, `CAPCAUSE`, or `FAULTCAPIDX`. | Pass | No further correction required. |
| E15-S03-F03: Secondary startup consistently treats start release as a lifecycle event before `STARTED`, while software IPI delivery follows ordinary interrupt rules only after a core is already `STARTED`. | Pass | No correction required. |
| E15-S03-F04: Trap entry, interrupt entry, debug-monitor entry, and `IRET` consistently use one hardware saved level with explicit `EPCC.slot` preservation for fully general software frames. | Pass | No correction required. |
| E15-S03-F05: Non-monitor `DEBUG_HALTED` entry deliberately preserves `PCC`, `PCC.slot`, `SR` trap fields, and `EPCC`, while debug-monitor entry deliberately consumes the one saved level. | Pass | No correction required. |
| E15-S03-F06: `CALL`, `CALLC`, `RET`, and protected return-stack maintenance all use all-or-nothing commit rules, and trap/debug/single-step cannot observe partial protected state. | Pass | No correction required. |
| E15-S03-F07: `WFI`, reset-time `WFI_PARKED`, interrupts, debug wake, and single-step retirement have compatible state boundaries. | Pass | No correction required. |
| E15-S03-F08: The pipeline and hazard stories provide a common precise retire and redirect-kill contract for all audited transitions. | Pass | No correction required. |

## Handoff to Later Consistency Stories

E15-S03 intentionally does not replace the full event-priority audit. E15-S04 must still check the single selected event when faults, debug events, single-step, interrupts, fatal events, and instruction-specific checks are simultaneously eligible.

E15-S05 must still audit composed memory, tag, cache, TLB, DMA, and ordering paths. This story relied on those owner stories only for state-transition boundaries, not for full memory-system litmus coverage.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Cold reset and reset capability state agree on initial scalar state, capability state, core parking, MMU state, interrupt state, cache state, and ROM entry authority. | Met. |
| Trap entry, nested interrupt entry, `IRET`, debug entry, debug exit, single-step, breakpoint/watchpoint events, and forced halt agree on saved state and priority. | Met for saved-state and transition composition; full same-cycle priority matrix continues in E15-S04. |
| `CALL`, `CALLC`, `RET`, protected return-stack updates, exceptions during call/return, and debug unwind rules agree on atomicity and precise state. | Met. |
| Secondary-core startup agrees with reset, interrupt, mailbox, cache, fence, and capability setup rules. | Met. |
| `WFI`, `PAUSE`, interrupt masking, pending interrupts, and start events have compatible wake and ordering rules. | Met. |
| Every transition names which state is committed, killed, preserved, restored, or invalidated. | Met by the state-transition ledger and conformance scenarios above. |

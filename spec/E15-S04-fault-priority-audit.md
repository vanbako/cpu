# E15-S04: Fault, Exception, Interrupt, and Debug Priority Audit

Story: E15-S04

Status: Complete

Prerequisites:

- `spec/E07-S02-exception-classes.md`
- `spec/E09-S07-effective-access-rule.md`
- `spec/E15-S01-terminology-cross-reference-audit.md`

Verification matrix:

- `tools/fault_priority_matrix.md`

## Decision

The v0.1 fault, exception, interrupt, and debug priority contract is internally consistent after the corrections listed below.

No unresolved blocking priority, reporting-register, recoverability, or precision inconsistency remains in this audit scope.

## Corrections Applied

| Finding | Severity | Correction |
| --- | --- | --- |
| E15-S04-F01: E07-S02 and the E15-S01 glossary implied that a debug breakpoint path could report `BREAKPOINT`, while E12-S02 hardware breakpoints report `CAUSE=DEBUG_HALT` with `DCAUSE=HW_BREAKPOINT`. | Blocking reporting inconsistency | Updated E07-S02 and E15-S01 so `BREAKPOINT` means the ordinary `BRK` trap when `DEBUGCTL.BRKHALT=0`, and debug breakpoint/watchpoint/single-step paths report `DEBUG_HALT` with E12 `DCAUSE`. |
| E15-S04-F02: E07-S04 and E07-S05 `TVC` authorization tables still used normal capability-fault wording for entry-vector delivery failures, which could be read as recursive trap delivery. | Blocking wording inconsistency | Updated the tables to describe diagnostic `FAULTCAPIDX=TVC` and `CAPCAUSE` values when delivery-failure reporting is exposed. The fatal entry-failure rule remains authoritative. |
| E15-S04-F03: E04-S05 left open whether `CAPCAUSE` is cleared or preserved for `ALIGN_FAULT`, but E07-S04 requires non-capability faults to write `CAPCAUSE=NONE` and `FAULTCAPIDX=NONE`. | Non-blocking wording inconsistency | Updated E04-S05 to point directly at the E07-S04 non-capability reporting rule. |

## Audit Scope

This audit cross-checks:

- Cause names, classes, and recoverability in E07-S02.
- Precise exception selection and trap-entry reporting in E07-S03 and E07-S04.
- Interrupt eligibility, source priority, and interrupt reporting in E07-S05.
- CSR and CCSR selector, access, privilege, and atomicity rules in E02-S04 and E02-S05.
- Effective-access priority in E09-S07, with page-memory-type refinements from E09-S06.
- Memory, capability, atomic, return-stack, cache-maintenance, fence, and TLB-invalidation fault rules in E04, E06, E08, E09, and E10 stories.
- Debug halt, hardware breakpoint/watchpoint, and single-step priority in E12 stories.

## Priority Model

The canonical verification matrix is `tools/fault_priority_matrix.md`.

The composed priority model is:

1. Reset, fatal platform conditions, and externally forced debug can override ordinary retirement.
2. The oldest current instruction's fetch, placement, decode, privilege, CSR/CCSR, operand, effective-access, return-stack, cache-maintenance, TLB/fence, arithmetic, or explicit synchronous trap condition is selected before ordinary maskable interrupt delivery.
3. Hardware instruction breakpoints are debug events after successful fetch and before illegal-instruction decode.
4. Data watchpoints are debug events after effective-access checks succeed and before memory/register effects commit.
5. Single-step completion is a post-retire debug event after normal instruction effects and `INSTRET`, before same-boundary ordinary maskable interrupt delivery.
6. Non-forced debug halt requests at a precise boundary beat ordinary maskable interrupts, but lose to current-instruction synchronous exceptions and to same-boundary single-step completion.
7. Ordinary maskable interrupts are delivered only when no higher-priority current-instruction or debug event has been selected, `SR.IE=1`, `SR.EXL=0`, and an enabled source is pending.

## Reporting Register Consistency

| Event | `CAUSE` | `TVAL` | `CAPCAUSE` / `FAULTCAPIDX` | Debug state | Audit result |
| --- | --- | --- | --- | --- | --- |
| Non-capability synchronous exception | E07-S02 synchronous cause, bit 47 clear | Owner-defined scalar or cell address, otherwise `0` | `NONE` / `NONE` | Unchanged except trap entry state | Pass. |
| Capability fault | E07-S02 capability cause or specific return-stack cause | E03/E04/E06/E09 selected cell address or `0` | Selected reason and operand | Unchanged except trap entry state | Pass. |
| Page fault | `PAGE_FAULT` | Faulting virtual cell address | `NONE` / `NONE` | Unchanged except trap entry state | Pass. |
| Access fault | `ACCESS_FAULT` | Physical cell address when known, otherwise effective address or `0` | `NONE` / `NONE` | Unchanged except trap entry state | Pass. |
| Ordinary `BRK` | `BREAKPOINT` | Faulting instruction cell address | `NONE` / `NONE` | No `DCAUSE` update required | Pass after correction. |
| Debug event | `DEBUG_HALT` | E12 source-specific value | `NONE` / `NONE` | `DEBUGCTL.DCAUSE` selects source | Pass after correction. |
| Interrupt entry | Interrupt cause with bit 47 set | `0` | `NONE` / `NONE` | No `DCAUSE` update | Pass. |
| Entry-vector failure | Fatal entry failure or E12 debug fallback | Diagnostic value if exposed | Diagnostic `CAPCAUSE` / `FAULTCAPIDX=TVC` if exposed | `DCAUSE=ENTRY_FAILURE` on debug fallback | Pass after correction. |

Trap entry and debug-monitor entry both overwrite the one hardware saved level as audited in E15-S03. Non-monitor debug halt preserves `EPCC` while updating `CAUSE`, `TVAL`, capability reporting fields, and `DCAUSE` through the E12 debug path.

## Instruction-family Coverage

| Area | Priority disposition |
| --- | --- |
| Instruction fetch and decode | E09-S07 fetch order wins over decode; E12-S02 instruction breakpoints fit after successful fetch and before malformed decode. |
| Integer arithmetic | Divide/modulo by zero is the only arithmetic trap; overflow is non-trapping. Arithmetic faults are precise and lose to earlier decode/privilege/operand faults. |
| CSR/CCSR access | Selector existence and access-class faults are selected before CSR/CCSR privilege faults; no partial CSR/CCSR update commits on fault. |
| Capability derivation | Instruction-owned operand order selects `FAULTCAPIDX`; selected capability faults populate `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL`. |
| Memory and capability load/store | E09-S07 common order selects capability tag/seal/address/alignment/bounds/protected-stack/permission/page/access faults deterministically. |
| Atomics | `LL48`/`SC48` use E09-S07 access checks before reservation effects; `SC48` access faults trap instead of returning failure; watchpoints beat reservation success/failure after access checks. |
| Control transfer | E04-S04 instruction privilege and capability checks are deterministic; `BRK`, `SYS`, and `SCALL` beat ordinary interrupts. |
| `CALL`, `CALLC`, and `RET` | Current `PCC` and entry capability checks precede protected return-stack effects; return-stack faults use E07-S02 specific causes. |
| Cache maintenance | User-mode privilege fault wins before capability checks; nonzero-range capability/range checks precede translation and memory-type/access failures. Partial older-line maintenance is explicitly documented as implementation behavior, not recoverable architectural rollback. |
| Fences and TLB invalidation | Valid `FENCE` has no addressed access faults; user-mode `FENCE.I`/`SFENCE.VM*` raise privilege faults; malformed encodings raise illegal instruction. |
| Debug comparators | Instruction fetch/access faults beat instruction breakpoints; effective-access faults beat watchpoints; comparators are suppressed in `DEBUG_HALTED` and debug-monitor execution. |
| Single-step | Any fault, explicit trap, breakpoint/watchpoint, or `BRK` debug event for the selected instruction beats single-step; otherwise step is reported after normal retire and before ordinary interrupts. |

## Accepted Deferrals and Profile Areas

| Area | Disposition |
| --- | --- |
| Platform fatal/reset/debug escalation after trap-entry or interrupt-entry failure | Accepted deferral. Owner stories require no recursive normal trap and require visibility to platform debug, reset, or fatal machinery. |
| Platform interrupt controller claim, completion, threshold, subpriority, and external-device identity | Accepted platform profile area. Core-level mandatory priority remains external, software IPI, timer once sources are pending and enabled. |
| Physical bus/device/PMP-like access rejection details | Accepted platform profile area. Selected architectural cause is `ACCESS_FAULT`. |
| Page-table walker memory access failure classification | Accepted narrow deferral: E09-S07 reports page-walk access failure as `PAGE_FAULT` unless a later platform story classifies it as `ACCESS_FAULT`. |
| Cache-maintenance partial older-line progress on a later-line fault | Accepted documented implementation behavior. Portable software must use valid page- and line-range maintenance and cannot rely on recovery progress. |
| Final opcode bit assignments and malformed-instruction bit reporting in `TVAL` | Accepted final-opcode-story area. The selected cause remains `ILLEGAL_INSTRUCTION` unless a final opcode story narrows reporting. |

## Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| E15-S04-F01: Debug breakpoint reporting was aliased to ordinary `BREAKPOINT` in older prose. | Corrected | Hardware/debug breakpoint, watchpoint, single-step, `BRKHALT=1`, and entry-failure fallback now consistently report `DEBUG_HALT` with E12 `DCAUSE`. |
| E15-S04-F02: Entry-vector capability failure wording could imply recursive normal capability traps. | Corrected | E07-S04 and E07-S05 now describe diagnostic reasons while preserving fatal entry failure. |
| E15-S04-F03: E04-S05 left non-capability `CAPCAUSE` cleanup ambiguous for `ALIGN_FAULT`. | Corrected | E04-S05 now points to E07-S04 `NONE` reporting. |
| E15-S04-F04: Effective-access priority is deterministic across capability, alignment, protected return-stack, page, memory-type, and physical access checks. | Pass | E09-S07 is the canonical order. |
| E15-S04-F05: CSR and CCSR fault names, privilege faults, and side-effect atomicity agree with E07-S02 and E07-S03. | Pass | No correction required. |
| E15-S04-F06: `LL48`/`SC48` access faults, reservation failure, watchpoints, and tag effects have a coherent order. | Pass | Access faults and watchpoints precede reservation result; faulting/failing `SC48` does not alter memory tags. |
| E15-S04-F07: Cache maintenance has a deterministic fault order with an explicit partial-progress caveat for multi-line faults. | Pass with accepted caveat | No correction required. |
| E15-S04-F08: Single-step, non-forced debug halt, and maskable interrupts have compatible post-retire priority. | Pass | Single-step wins at the same post-retire boundary; debug halt wins over ordinary interrupts. |

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Exception classes, cause codes, capability-fault details, page faults, alignment faults, illegal instructions, CSR faults, CCSR faults, breakpoints, watchpoints, single-step, interrupts, and fatal conditions have one priority model. | Met by `tools/fault_priority_matrix.md`. |
| `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, `EPCC`, `SR.EXL`, debug cause state, and relevant CCSR/CSR side effects agree across producer stories. | Met after the reporting cleanups above. |
| Fault priority is checked for instruction fetch, data load/store, capability load/store, capability derivation, atomics, CSR/CCSR access, cache maintenance, TLB invalidation, return-stack operations, and control transfer. | Met by instruction-family coverage and the verification matrix. |
| Recoverability and precision rules agree with the retire model. | Met, with cache-maintenance partial progress explicitly treated as documented implementation behavior rather than normal recoverable rollback. |
| User/kernel privilege faults and debug-mode behavior are not contradictory. | Met. |
| Cases deliberately left to implementation or platform policy are explicitly marked and do not affect mandatory conformance. | Met by accepted deferrals and profile areas. |

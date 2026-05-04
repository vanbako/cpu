# Fault Priority Matrix

Story: E15-S04

Status: Complete

This matrix is the verification checklist for the E15-S04 audit. It summarizes the selected architectural event for common overlapping fault, exception, interrupt, and debug conditions.

Lower order numbers win when more than one condition is eligible at the same architectural point.

## Global Event Order

| Order | Event family | Selected report | Notes |
| ---: | --- | --- | --- |
| 1 | Reset, implementation fatal platform condition, externally forced debug | Reset/fatal/debug mechanism | These can override ordinary retirement. Fatal trap/interrupt-entry failure is not recursive normal trap delivery. |
| 2 | Current-instruction fetch or instruction access fault | Synchronous `CAUSE` from E07-S02/E09-S07 | Includes `PCC` tag/seal/permission/bounds, fetch translation/page, fetch memory-type/access, and placement faults. |
| 3 | Instruction breakpoint comparator after successful fetch | `CAUSE=DEBUG_HALT`, `DCAUSE=HW_BREAKPOINT` | E12-S02 places this before malformed or unsupported decode. |
| 4 | Malformed, unsupported, reserved, or illegal instruction encoding | `ILLEGAL_INSTRUCTION` or specific owner cause | Includes malformed fence/CSR/CCSR/control-transfer encodings. |
| 5 | Decoded instruction privilege or CSR/CCSR selector/access fault | `PRIVILEGE_FAULT`, `CSR_*`, or `CCSR_*` | CSR/CCSR selector and access-class faults are selected before CSR/CCSR privilege faults. |
| 6 | Explicit synchronous trap instruction | `BREAKPOINT`, `SYSCALL_TRAP`, or `DEBUG_HALT` for `BRKHALT=1` | Ordinary `BRK` reports `BREAKPOINT`; debug-routed `BRK` reports `DEBUG_HALT`, `DCAUSE=BRK`. |
| 7 | Instruction-defined capability, control-transfer, return-stack, arithmetic, effective-access, cache-maintenance, or TLB/fence fault | Selected owner-story synchronous cause | Uses the detailed owner order below. |
| 8 | Data watchpoint after effective-access checks pass and before access commits | `CAUSE=DEBUG_HALT`, `DCAUSE=WATCHPOINT` | Effective-access faults win over watchpoints. Matching watchpoints prevent memory/register effects. |
| 9 | Normal instruction retire | Normal effects and `INSTRET` | For `SC48`, reservation failure is a normal non-trapping retire with `Dr=1`. |
| 10 | Single-step completion after normal retire | `CAUSE=DEBUG_HALT`, `DCAUSE=SINGLE_STEP` | The stepped instruction has already committed normal effects and `INSTRET`. |
| 11 | Non-forced external halt or `HALTREQ` sampled at a precise boundary | `CAUSE=DEBUG_HALT`, selected E12 `DCAUSE` | Loses to current-instruction synchronous exceptions and to same-boundary single-step completion, but wins over maskable interrupts. |
| 12 | Ordinary maskable interrupt | Interrupt `CAUSE` with bit 47 set | Eligible only when `SR.IE=1`, `SR.EXL=0`, and a source is enabled and pending. |

## Instruction Fetch and Decode

| Overlap | Winner | Reporting |
| --- | --- | --- |
| Invalid `PCC.tag` and unmapped fetch page | Fetch capability tag fault | `CAPCAUSE=TAG`, `FAULTCAPIDX=PCC`, `TVAL=attempted fetch cell`. |
| Sealed or non-executable `PCC` and page fault | Fetch capability fault | `CAPCAUSE=SEAL_TYPE` or `PERMISSION`, `FAULTCAPIDX=PCC`. |
| `PCC.cursor` out of bounds and illegal opcode bits | Fetch capability bounds fault | Illegal decode is reached only after fetch access succeeds. |
| Illegal slot or 48-bit placement and legal opcode bits | `ALIGN_FAULT` | `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`. |
| Successful fetch, instruction breakpoint match, and malformed opcode | Debug event | `CAUSE=DEBUG_HALT`, `DCAUSE=HW_BREAKPOINT`; malformed decode is suppressed. |
| Successful fetch with no breakpoint and malformed opcode | `ILLEGAL_INSTRUCTION` | `TVAL=0` unless an opcode story defines instruction-bit reporting. |

## CSR and CCSR Instructions

| Overlap | Winner | Reporting |
| --- | --- | --- |
| Malformed CSR/CCSR encoding and reserved selector | `ILLEGAL_INSTRUCTION` | Decode fails before selector semantics. |
| Reserved CSR number and user mode | `RESERVED_CSR_FAULT` | Selector existence is checked before privilege. |
| Existing CSR disallows required read/write and user mode | `ILLEGAL_CSR_READ` or `ILLEGAL_CSR_WRITE` | Access-class legality is checked before privilege. |
| Existing CSR allows operation but current privilege is too low | `CSR_PRIVILEGE_FAULT` | `TVAL` carries selector bits when decoded. |
| Reserved CCSR index and user mode | `RESERVED_CCSR_FAULT` | CCSR index existence is checked before privilege. |
| Implemented CCSR does not support operation and user mode | `ILLEGAL_CCSR_ACCESS` | Operation support is checked before privilege. |
| Implemented CCSR supports operation but current privilege is too low | `CCSR_PRIVILEGE_FAULT` | No CCSR payload/tag update commits. |

## Data, Capability, Stack, and Atomic Access

| Check order | Failed check | Selected report |
| ---: | --- | --- |
| 1 | Authorizing capability tag invalid | `CAPABILITY_TAG_FAULT`, failing capability in `FAULTCAPIDX`. |
| 2 | Authorizing capability sealed | `CAPABILITY_SEAL_TYPE_FAULT`. |
| 3 | Effective address underflow or overflow | `CAPABILITY_BOUNDS_FAULT`, `TVAL=0` unless owner is more precise. |
| 4 | Object alignment failure | `ALIGN_FAULT`, no capability reporting. |
| 5 | Object outside authorizing capability bounds | `CAPABILITY_BOUNDS_FAULT`, `TVAL` effective cell or slot base. |
| 6 | Ordinary access overlaps protected return-stack storage | `RETURN_STACK_PERMISSION_FAULT`. |
| 7 | Missing capability permission or `SL` | `CAPABILITY_PERMISSION_FAULT` or `CAPABILITY_LOCAL_STORE_FAULT`. |
| 8 | Translation/page-walk/PTE validity failure, reserved `MT`, page privilege, or page permission | `PAGE_FAULT`, `CAPCAUSE=NONE`, `FAULTCAPIDX=NONE`. |
| 9 | Valid memory type rejects access class | `ACCESS_FAULT`. |
| 10 | Physical, device, bus, or platform access rejection | `ACCESS_FAULT`. |

Access faults beat normal memory effects, LL reservation creation, `SC48` success/failure result, cache-maintenance completion, and data watchpoint delivery only when the access fault is selected before the watchpoint match point.

## Control Transfer and Return Stack

| Overlap | Winner | Reporting |
| --- | --- | --- |
| User-mode `IRET`, `EPCCRD`, `EPCCWR`, or `WFI` with invalid operands | `PRIVILEGE_FAULT` | Instruction privilege is checked before operand capability checks. |
| `Bcc` condition false and target out of bounds | Normal fall-through | Untaken conditional branch does not check target bounds. |
| Direct target out of current `PCC.bounds` | `CAPABILITY_BOUNDS_FAULT` | `FAULTCAPIDX=PCC`. |
| `CALL` continuation out of bounds and `RSC` push would overflow | Current `PCC` continuation bounds fault | `CALL` current-PC checks precede protected push checks. |
| `CALL` protected push target outside `RSC.bounds` | `RETURN_STACK_OVERFLOW` | `CAPCAUSE=BOUNDS`, `FAULTCAPIDX=RSC`. |
| `RET` active slot invalid or empty | `RETURN_STACK_UNDERFLOW` | `CAPCAUSE` selects `TAG`, `BOUNDS`, or `SEAL_TYPE`. |
| `RET` return target lacks execute authority | Return-target capability fault | Reporting follows E06-S03/E06-S04 selected check. |
| `BRK` with `BRKHALT=0` and pending interrupt | `BREAKPOINT` | Synchronous trap beats maskable interrupt. |
| `BRK` with `BRKHALT=1` and pending interrupt | `DEBUG_HALT`, `DCAUSE=BRK` | Debug event beats maskable interrupt. |
| `SYS`/`SCALL` and pending interrupt | `SYSCALL_TRAP` | Synchronous trap beats maskable interrupt. |

## Debug, Single-step, and Interrupt Boundaries

| Overlap | Winner | Reporting |
| --- | --- | --- |
| Current instruction faults and non-forced external halt request is pending | Current instruction fault | External halt waits unless externally forced. |
| Current instruction faults while single-step is active | Current instruction fault | No `DCAUSE=SINGLE_STEP`; `STEP_ACTIVE` clears on entry. |
| Hardware breakpoint/watchpoint and single-step active | Breakpoint/watchpoint debug event | `DCAUSE=HW_BREAKPOINT` or `WATCHPOINT`; no step completion. |
| `BRKHALT=1` and single-step active | `BRK` debug event | `DCAUSE=BRK`; no step completion. |
| Normal instruction retires with single-step active and interrupt pending | Single-step debug event | `DCAUSE=SINGLE_STEP`; interrupt may be delivered after debug resume/return. |
| Normal boundary has non-forced debug halt and maskable interrupt pending | Debug halt | E12 debug events beat ordinary maskable interrupts. |
| Multiple mandatory interrupt sources pending and enabled | External, then software IPI, then timer | E07-S05 fixed priority. |
| Interrupt vector target invalid | Fatal interrupt-entry failure or debug fallback | Pending interrupt source is not automatically cleared. |
| Trap or debug-monitor vector target invalid | Fatal entry failure or debug fallback | No recursive normal trap through the invalid vector. |

## Cache, Fence, and TLB Maintenance

| Overlap | Winner | Reporting |
| --- | --- | --- |
| User-mode `CACHE.*` with invalid capability operand | `PRIVILEGE_FAULT` | Privilege is checked before range authority. |
| Kernel `CACHE.*` nonzero range with invalid `Ca.tag` | `CAPABILITY_TAG_FAULT` | No required maintenance completion is reported. |
| Kernel `CACHE.*` range outside rounded line bounds and unmapped later line | Capability bounds fault | Capability/range checks precede translation. |
| Kernel `CACHE.*` translation failure for maintained line | `PAGE_FAULT` | Implementations may document partial older-line maintenance; software must not depend on recovery progress. |
| Kernel `CACHE.*` valid translation but memory type rejects maintenance | `ACCESS_FAULT` | Memory-type legality is after translation and page checks. |
| User-mode `FENCE.I` or `SFENCE.VM*` | `PRIVILEGE_FAULT` | No normal cache, TLB, predictor, or register effect; any active LL/SC reservation is cleared by trap entry. |
| Malformed fence encoding | `ILLEGAL_INSTRUCTION` | `FENCE` itself performs no addressed access and raises no page/capability/access faults. |
| Valid kernel `SFENCE.VM*` | Normal retire | Invalidates selected local TLB entries and orders local translation use. |

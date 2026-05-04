# E15-S06: Software-facing ABI, Firmware, Debug, and Toolchain Contract Audit

Story: E15-S06

Status: Complete

Prerequisites:

- `spec/E04-S06-mandatory-mvp-additions.md`
- `spec/E05-S01-integer-calling-convention.md`
- `spec/E05-S02-capability-calling-convention.md`
- `spec/E11-S03-secondary-core-startup.md`
- `spec/E12-S01-debug-halt-behavior.md`
- `spec/E15-S01-terminology-cross-reference-audit.md`

Contract matrix:

- `tools/software_contract_matrix.md`

## Decision

The v0.1 software-facing contract is internally consistent across the mandatory instruction baseline, ABI register roles, data-stack and protected-return-stack layout, reset and secondary-core startup handoff, debug halt and monitor behavior, mandatory counters, extended performance events, and toolchain assumptions.

No unresolved blocking inconsistency remains for a first assembler, simulator, firmware ROM, kernel trap path, debugger, or ABI test suite.

## Audit Scope

This audit cross-checks:

- Mandatory integer, memory, capability, control-flow, CSR, CCSR, atomic, fence, cache-maintenance, and debug-adjacent instructions.
- Integer and capability ABI register streams, caller/callee preservation, return values, overflow stack arguments, variadic deferrals, and syscall conventions.
- Data-stack and protected-return-stack alignment, locality, protected storage, and unwind/debug maintenance rules.
- Cold reset, reset capability authority, boot-core entry, secondary-core mailbox startup, and public startup handoff state.
- Breakpoints, hardware breakpoints, watchpoints, single-step, debug halt, debug-monitor entry, counters, and performance event discovery.
- Cell-addressed toolchain requirements for labels, debug information, instruction placement, stack layout, object alignment, page geometry, and binary serialization.

## Contract Matrix Summary

| Area | Owner stories | Audit result |
| --- | --- | --- |
| Mandatory instruction coverage | E04-S02 through E04-S06, E06-S02, E08-S01, E08-S04, E10-S05 | Pass. E04-S06 is the mandatory additions checklist; the complete baseline is the union of earlier instruction owner stories plus the E04-S06 additions. |
| Opcode coverage contract | E04-S01, E04-S06, E02-S04, E02-S05 | Pass. Every mandatory mnemonic has an owner and at least one required assembly spelling or synonym rule; final numeric opcode allocation remains explicitly deferred. |
| CSR and CCSR software access | E02-S02 through E02-S05, E04-S04, E12-S01 through E12-S05 | Pass. Scalar CSRs use integer registers and CSR-number access; special capability registers use CCSR indices and preserve tags. `EPCCRD`/`EPCCWR` cover slot-aware trap frames. |
| Integer ABI | E01-S02, E05-S01 | Pass. `D0-D5` arguments, `D0-D1` returns, `D0-D11` caller-saved, and `D12-D15` callee-saved are compatible with all mandatory instruction side effects. |
| Capability ABI | E01-S03, E05-S02 | Pass. `C0-C3` arguments, `C0` return, `C0-C5` caller-saved, and `C6-C7` callee-saved preserve payload and tag where required. |
| Mixed overflow arguments | E05-S01, E05-S02, E05-S03 | Pass. Integer-only layout reduces to E05-S01, while mixed overflow uses source order with 2-cell and 4-cell natural alignment. |
| Data stack | E05-S03, E03-S05, E11-S02, E11-S03 | Pass. `DSC` alignment, local-capability store permission, and startup stack requirements agree. |
| Protected return stack | E05-S04, E06-S03, E06-S04, E12-S01 | Pass. `CALL`, `CALLC`, `RET`, protected maintenance, trap/debug boundaries, and ABI preservation all keep return authority off the data stack. |
| Boot-core reset | E11-S01, E11-S02, E02-S02, E01-S06 | Pass. The boot core enters ROM with valid slot-0 `PCC`, masked interrupts, `SATP=0`, invalid non-handoff capability tags, and reset scalar CSRs. |
| Secondary-core startup | E11-S03, E08-S03, E11-S02, E05-S03, E05-S04 | Pass. The mailbox publication sequence, capability tag paths, startup arguments in `D0`/`C0`, and stack setup form a coherent firmware ABI. |
| Debug halt and monitor | E12-S01, E12-S02, E12-S03, E07-S04, E07-S06 | Pass. Non-monitor halt preserves inspected state, monitor entry consumes the one hardware saved level, and single-step uses precise post-retire state. |
| Counters and performance events | E12-S04, E12-S05, E02-S02, E02-S03 | Pass. Mandatory counters and optional PMCs have compatible reset, privilege, halt, wrap, and discovery behavior. |
| Toolchain cell model | E01-S01, E01-S05, E04-S01, E05-S03, E09-S01 | Pass. Labels, PC values, memory ranges, stack slots, pages, cache lines, and debug locations are cell-addressed. |

## Example Walkthroughs

| Walkthrough | Expected contract |
| --- | --- |
| User integer/capability call | Caller places integer-class arguments in `D0-D5`, capability-class arguments in `C0-C3`, lays out overflow arguments in source order at entry `DSC.cursor`, and invokes `CALL` or `CALLC`. Callee may clobber `D0-D11` and `C0-C5`, must restore `D12-D15` and `C6-C7`, and returns via `D0-D1` and `C0`. |
| Capability stack spill | A compiler spills a live valid local capability with `CSC` through a `DSC` that has `ST`, `SC`, and `SL`; reload uses `CLC` and preserves payload and tag. `ST48` is not a capability spill because it clears tags. |
| Trap frame save with slot-1 fault | Trap entry captures `EPCC.payload`, `EPCC.tag`, and `EPCC.slot`. A nestable handler uses `EPCCRD` to copy payload and slot to a software frame and `EPCCWR` to restore both before `IRET`. Plain `CCSRWR EPCC` is payload/tag-only and resets the hidden slot to 0. |
| Boot-core ROM handoff | Reset hardware installs a valid ROM `PCC` at `RESET_VECTOR`, slot 0. Firmware derives `KRC`, `KSC`, `DSC`, `RSC`, and `TVC` through trusted tagged authority before enabling traps, interrupts, stack use, or later kernel handoff. |
| Secondary startup | Boot code writes a tagged mailbox, executes the storage-class ordering operation, signals the target, and the secondary reaches `STARTED` only after installing valid `PCC`, `DSC`, `RSC`, and documented startup arguments in `D0` and `C0`. |
| Debug step over a 12-bit slot-0 instruction | Resume arms `STEP_ACTIVE`, the slot-0 instruction retires and increments `INSTRET`, then debug entry reports `DCAUSE=SINGLE_STEP` with `PCC` at slot 1 of the same cell. |
| Breakpoint source compatibility | Source may use `BRK` for the breakpoint instruction. With `DEBUGCTL.BRKHALT=0`, it is an ordinary `BREAKPOINT` trap; with `BRKHALT=1`, it is a `DEBUG_HALT` event with `DCAUSE=BRK`. |

## Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| E15-S06-F01: Mandatory instruction ownership is partitioned rather than held in one table. | Pass | E04-S06 explicitly owns the additions checklist and points to earlier owner stories for baseline integer, memory, capability, and control-transfer instructions. |
| E15-S06-F02: `SYS` and `SCALL` source compatibility could be confused with two required opcodes. | Pass | `SYS` is canonical and `SCALL` is a required assembler synonym; one binary encoding may implement both. |
| E15-S06-F03: Slot-aware trap frames require a path beyond ordinary CCSR access. | Pass | E04-S04 defines `EPCCRD` and `EPCCWR`; E07-S06 explicitly warns that plain `CCSRWR EPCC` is not sufficient for general nested-trap restore. |
| E15-S06-F04: ABI register preservation agrees with trap/debug state ownership. | Pass | Function-call preservation is a normal-return software contract; trap, syscall, debug, unwind, and context-switch save areas are intentionally OS/runtime policy. |
| E15-S06-F05: Startup use of `D0` and `C0` agrees with the public ABI. | Pass | Startup handoff intentionally uses the primary argument registers, and other registers are zero or invalid unless the platform ABI documents more arguments. |
| E15-S06-F06: Protected return-stack unwind/debug access does not violate capability integrity. | Pass | E06-S04 protected peek/drop/replace validate sealed return entries and operate only at precise privileged/debug boundaries. |
| E15-S06-F07: Debug observability and counters expose enough bring-up state without breaking authority rules. | Pass | Debug transport cannot forge tags; mandatory counters and PMCs are per-core, privilege-checked, and halted-state behavior is defined. |
| E15-S06-F08: Toolchain assumptions for 24-bit cells and mixed instruction sizes are documented as custom behavior. | Pass | E01-S01, E01-S05, and E04-S01 consistently use cell addresses, hidden slots, and 12/24/48-bit placement rules. |

## Accepted Deferrals and Boundaries

| Area | Disposition |
| --- | --- |
| Final numeric opcode bit assignments | Deferred to the final opcode story or generated opcode table. E15-S06 requires coverage, not bit positions. |
| Exact binary container serialization of 24-bit cells | Deferred to toolchain/container work. The architecture requires the container to document cell serialization. |
| Concrete C/Rust language ABI details | Deferred. E05 defines the architectural ABI substrate, including register classes, overflow layout, and variadic state abstractions. |
| Trap-frame memory layout and context-switch save area | OS/runtime policy. The architecture names the minimum hardware saved state and slot-aware helpers. |
| Platform debug transport and authentication | Platform security policy, with architectural tag-integrity and halted-state constraints. |
| Platform start-event CSR numbers and mailbox addresses | Platform profile detail, constrained by the E11-S03 logical mailbox and ordering rules. |
| Mandatory support for every extended performance event | Not required. E12-S05 defines selector names and `WARL` discovery for unsupported events. |

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Mandatory instruction lists agree with the instruction semantics, privilege rules, CSR/CCSR access rules, fences, atomics, debug behavior, and return-stack operations. | Met. |
| Integer and capability calling conventions agree on register use, preserved state, return values, overflow arguments, variadic deferrals, and stack alignment. | Met. |
| Data-stack and return-stack models agree with local capabilities, protected storage, trap handling, debug unwind, and boot setup. | Met. |
| Firmware reset, ROM entry, reset capability authority, secondary-core startup, cache/TLB state, and interrupt setup form one boot sequence. | Met. |
| Debug halt, breakpoints, watchpoints, single-step, counters, and performance events expose enough state for simulation and bring-up without violating capability integrity. | Met. |
| Toolchain assumptions for 24-bit cells, fetch groups, instruction sizes, alignment, and ABI layout are documented as required custom behavior. | Met. |

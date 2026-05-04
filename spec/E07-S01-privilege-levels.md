# E07-S01: Privilege Levels

Story: E07-S01

Status: Complete

Normative source: `design.md`, section 10.1

Prerequisite:

- `spec/E01-S06-status-register-behavior.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E02-S01-scalar-csr-namespace.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S03-extended-csr-space.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E11-S02-reset-capability-state.md`

## Decision

CPU v0.1 has exactly two architectural privilege levels:

| Encoded value | Name | Meaning |
| ---: | --- | --- |
| `0` | `U` | User mode. Runs applications and untrusted runtime code. |
| `1` | `K` | Kernel mode. Runs the kernel, firmware after reset handoff, trap handlers, interrupt handlers, and privileged runtime code. |

Privilege is ordered:

```text
U < K
```

An operation with required privilege `K` may execute only when `SR.PRIV = K`. An operation with required privilege `U` may execute in either mode unless its owning story defines a narrower rule.

`SR.PRIV` is the current privilege field. `SR.PPRIV` is the one-level previous-privilege field used by trap entry and `IRET`.

## No Virtualization Level

v0.1 has no virtualization privilege level.

Specifically, v0.1 has no:

- Hypervisor mode.
- Guest mode.
- Machine-versus-supervisor split.
- Virtualized copy of privileged CSRs.
- Guest-visible trap-vector, interrupt, or page-table root state.

Address spaces selected by `SATP` and `ASID` are memory-management context, not privilege levels. A later architecture revision may add virtualization only with a new explicit compatibility story.

## Privilege Is Not Authority Bypass

Kernel mode bypasses user/kernel privilege checks only. It does not bypass capability or memory-system authorization.

Even in `K` mode:

- Instruction fetch must pass `PCC` tag, bounds, seal-state, and `EX` checks.
- Data access must pass the effective capability, alignment, translation, and memory-type checks assigned by later stories.
- Capability loads and stores still require the appropriate `LD`, `ST`, `LC`, `SC`, and `SL` permissions.
- Capability derivation remains monotonic.
- Integer data cannot create valid capability tags.

This keeps pure-capability authority intact while still giving kernel software access to privileged control state.

## Privilege Transitions

Normal user code cannot directly raise its privilege.

Privilege changes occur only through defined architectural paths:

| Path | Effect |
| --- | --- |
| Cold reset entry | Starts core 0 in `K` mode according to E01-S06 and E11 stories. |
| Trap or interrupt entry | Sets `SR.PRIV = K`, saves old privilege in `SR.PPRIV`, and sets `SR.EXL = 1`. |
| `IRET` | Restores `SR.PRIV = SR.PPRIV` and clears `SR.EXL`, subject to `IRET` privilege checks. |
| Privileged `SR` write | Kernel-only context-management path governed by CSR access rules. |

`SYS` or `SCALL` from user mode is an explicit request for kernel service. It raises a syscall/software-trap exception; it is not a privilege violation.

`BRK` from user mode is an explicit breakpoint/debug trap. It is not a privilege violation unless the debug story later adds a policy that rejects a specific breakpoint use.

## Privileged Instructions

The baseline v0.1 privilege classification is:

| Instruction or instruction class | Required privilege | Notes |
| --- | --- | --- |
| Integer ALU, moves, compares, and ordinary branches | `U` | May execute in `U` or `K`. |
| Ordinary capability derivation and movement instructions | `U` | Subject to capability tag, bounds, permission, and seal/type checks. |
| `LD48`, `ST48`, `CLC`, `CSC` | `U` | Subject to capability, alignment, translation, and memory-type checks. |
| `CALL`, `CALLC`, `RET`, `JMP`, direct branches | `U` | Subject to control-flow and capability rules. |
| `SYS` or `SCALL` | `U` | Enters the syscall/software-trap path. |
| `BRK` | `U` | Enters the breakpoint/debug path. |
| `PAUSE` | `U` | Execution hint only. |
| `FENCE` | `U` | Data-ordering fence; detailed scope is defined by E08-S04. |
| `FENCE.I` | `K` | Conservative v0.1 baseline; E08-S04 may define a narrower user-visible synchronization ABI. |
| `SFENCE.VM` | `K` | Translation/TLB maintenance. |
| `IRET` | `K` | Returns from trap state using `EPCC`, `SR.PIE`, and `SR.PPRIV`. |
| `WFI` | `K` | Wait/idle operation; user-mode wait should use scheduler ABI, not hardware idle. |
| `CCSRRD`, `CCSRWR` | `K` | All implemented v0.1 special capability registers are kernel-only. |
| `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR` | CSR-specific | Required privilege is determined by the selected scalar CSR and operation. |
| `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL` | `K` | Cache maintenance operations are privileged. |
| Privileged return-stack unwind/debug operations | `K` or debug mode | Deferred to E06-S04 and E12 stories. |

If an owning instruction story later assigns a more specific privilege rule, it must preserve user/kernel isolation and update this table's dependency chain.

## Scalar CSR Privilege Summary

Scalar CSR privilege is defined per CSR and per operation by E02-S01, E02-S02, and E02-S03.

Mandatory fast-window summary:

| CSR | User read | User write | Kernel read | Kernel write |
| --- | --- | --- | --- | --- |
| `SR` | no | no | yes | yes, subject to field rules |
| `COREID` | yes | no | yes | no |
| `CYCLE` | yes | no | yes | yes |
| `INSTRET` | yes | no | yes | yes |
| `TVEC` | no | no | yes | yes |
| `CAUSE` | no | no | yes | yes |
| `TVAL` | no | no | yes | yes |
| `SCRATCH` | no | no | yes | yes |
| `IENABLE` | no | no | yes | yes |
| `IPENDING` | no | no | yes | yes, subject to field rules |
| `TIMER` | yes | no | yes | no |
| `TIMECMP` | no | no | yes | yes |
| `SATP` | no | no | yes | yes |
| `ASID` | no | no | yes | yes |
| `DEBUGCTL` | no | no | yes | yes |
| `PERFSEL` | no | no | yes | yes |

Extended CSR baseline:

- `FAULTCAPIDX` and `CAPCAUSE` are kernel read/write reporting CSRs.
- `CACHECTL`, `TLBCTL`, cache-maintenance CSRs, TLB-maintenance CSRs, platform interrupt-controller CSRs, and implementation-specific privileged control CSRs are kernel-only unless their owning story explicitly defines a user-readable non-authority field.
- Reserved, future, unimplemented, or undocumented CSR numbers fault before returning any value.

The CSR access-check order from E02-S04 still applies. For example, a write to a read-only CSR raises `ILLEGAL_CSR_WRITE`; an otherwise legal access attempted from insufficient privilege raises `CSR_PRIVILEGE_FAULT`.

## Capability CSR Privilege Summary

All implemented v0.1 capability CSR indices are kernel-only:

| CCSR index | Register | User access | Kernel access |
| ---: | --- | --- | --- |
| `0` | `PCC` | no | read/write |
| `1` | `DSC` | no | read/write |
| `2` | `RSC` | no | read/write |
| `3` | `DDC` | no | read/write |
| `4` | `EPCC` | no | read/write |
| `5` | `TVC` | no | read/write |
| `6` | `KSC` | no | read/write |
| `7` | `KRC` | no | read/write |

User-mode `CCSRRD` or `CCSRWR` to an implemented CCSR raises `CCSR_PRIVILEGE_FAULT`.

Reserved CCSR indices raise `RESERVED_CCSR_FAULT` according to E02-S05.

## Privilege Violation Faults

`PRIVILEGE_FAULT` is the architectural privilege-violation exception class for v0.1.

Existing instruction-specific names remain valid and map into the privilege-violation class until E07-S02 assigns final cause encodings:

| Name | Use |
| --- | --- |
| `PRIVILEGE_FAULT` | Generic privileged instruction or privileged operation executed from insufficient privilege. |
| `CSR_PRIVILEGE_FAULT` | Scalar CSR access where the CSR exists and the operation is allowed, but `SR.PRIV` is too low. |
| `CCSR_PRIVILEGE_FAULT` | Capability CSR access to an implemented CCSR while `SR.PRIV` is too low. |

On a privilege violation:

- The faulting instruction does not retire.
- Destination integer and capability registers are unchanged.
- Memory payload and memory tags are unchanged.
- The target CSR or CCSR is unchanged.
- Trap reporting uses the precise exception path defined by E07-S03 and E07-S04.

`TVAL` for a privilege violation is `0` unless the owning instruction story defines a more specific reporting value.

## User-mode Invariants

When `SR.PRIV = U`, software cannot directly:

- Write `SR.PRIV` or any other `SR` field.
- Read or write special capability registers.
- Install a new `PCC`, `EPCC`, `TVC`, `KSC`, `KRC`, `DSC`, `RSC`, or `DDC` through CCSR access.
- Change `SATP`, `ASID`, interrupt enables, trap vectors, debug controls, cache controls, or TLB controls.
- Execute `IRET`, `WFI`, `SFENCE.VM`, cache-maintenance operations, or other kernel-only operations.

User mode can still:

- Use capabilities it legitimately holds.
- Execute ordinary arithmetic, memory, capability, and control-flow instructions subject to their non-privilege checks.
- Read user-readable observation CSRs such as `COREID`, `CYCLE`, `INSTRET`, and `TIMER`.
- Request kernel service through `SYS` or `SCALL`.
- Trigger a breakpoint trap through `BRK`.

## Out of Scope for This Story

- Numeric `CAUSE` values and full exception priority: E07-S02.
- Precise exception retirement and rollback contract: E07-S03.
- Direct trap entry and `IRET` sequencing details: E07-S04.
- Vectored interrupt source model: E07-S05.
- Page-table user/supervisor access bits and effective access priority: E09-S05 and E09-S07.
- Final cache, TLB, and instruction-fetch fence semantics: E08-S04 and E10-S05.
- Debug-mode privilege and halt/resume policy: E12 stories.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Reset starts core 0 with `SR.PRIV = K`.
- `SR.PRIV = 0` means `U`; `SR.PRIV = 1` means `K`.
- No encoding or CSR state exposes a third v0.1 privilege mode.
- User-mode `CSRWR SR, Ds` raises `CSR_PRIVILEGE_FAULT` and leaves `SR` unchanged.
- User-mode `CSRRD COREID` succeeds.
- User-mode `CSRRD CYCLE`, `CSRRD INSTRET`, and `CSRRD TIMER` succeed.
- User-mode `CSRWR CYCLE, Ds` raises `CSR_PRIVILEGE_FAULT`.
- User-mode `CSRRD SATP` raises `CSR_PRIVILEGE_FAULT`.
- User-mode `CCSRRD C0, PCC` raises `CCSR_PRIVILEGE_FAULT`.
- User-mode `CCSRWR PCC, C0` raises `CCSR_PRIVILEGE_FAULT`.
- User-mode `IRET`, `WFI`, `SFENCE.VM`, and cache-maintenance operations raise `PRIVILEGE_FAULT`.
- User-mode `SYS` or `SCALL` raises syscall/software trap rather than privilege fault.
- User-mode `BRK` raises breakpoint/debug trap rather than privilege fault.
- Kernel-mode access to privileged CSRs and CCSRs succeeds when the selected CSR/CCSR access class permits the operation.
- Kernel mode still faults on capability tag, bounds, permission, seal/type, and local-store violations.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `U` and `K` privilege levels are defined. | Met. |
| No virtualization level exists in v0.1. | Met. |
| Privileged instructions and CSRs are identified. | Met. |
| Privilege violations raise a named exception. | Met: `PRIVILEGE_FAULT`, with CSR-specific `CSR_PRIVILEGE_FAULT` and `CCSR_PRIVILEGE_FAULT`. |

# E07-S02: Exception Classes

Story: E07-S02

Status: Complete

Normative source: `design.md`, sections 10.2 and 10.3

Prerequisite:

- `spec/E07-S01-privilege-levels.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S03-extended-csr-space.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S01-pcc-execute-authority.md`

## Decision

CPU v0.1 has a fixed architectural exception cause namespace for synchronous traps and debug halt entry.

`CAUSE` is the scalar trap-class CSR assigned by E02-S02. Hardware-generated synchronous exception causes use this format:

```text
CAUSE[47]    = 0
CAUSE[46:16] = 0
CAUSE[15:0]  = exception cause code
```

Interrupt causes are not assigned by E07-S02. E07-S05 owns the interrupt cause namespace and may use `CAUSE[47] = 1` for interrupt causes.

Kernel software may still write `CAUSE` for diagnostic replay as allowed by E02-S02. Portable software should use only assigned hardware-generated values when interpreting traps.

## Mandatory Exception Cause Table

| `CAUSE` value | Name | Class | Typical source |
| ---: | --- | --- | --- |
| `0x0000` | `NONE` | No exception | Reset value or software-cleared reporting state. |
| `0x0001` | `ILLEGAL_INSTRUCTION` | Illegal instruction | Malformed encoding, unsupported opcode, malformed operand class, or illegal reserved instruction form. |
| `0x0002` | `BREAKPOINT` | Breakpoint | `BRK` instruction or debug breakpoint path. |
| `0x0003` | `PRIVILEGE_FAULT` | Privilege violation | Kernel-only instruction, operation, CSR, or CCSR attempted from insufficient privilege. |
| `0x0004` | `DIVIDE_BY_ZERO` | Arithmetic exception | Integer divide or modulo with zero divisor. |
| `0x0005` | `ALIGN_FAULT` | Alignment exception | Misaligned memory object, illegal instruction slot, illegal fetch-group placement, or explicit slot-1 target. |
| `0x0006` | `ACCESS_FAULT` | Physical or memory access exception | Bus, device, memory-type, PMP-like, or platform access rejection not represented as a page fault. |
| `0x0007` | `PAGE_FAULT` | Translation exception | Invalid translation, page permission failure, or page-walk failure. |
| `0x0008` | `SYSCALL_TRAP` | Software trap | `SYS` or `SCALL`. |
| `0x0009` | `CAPABILITY_TAG_FAULT` | Capability fault | Required authorizing or derivation-source capability has invalid tag. |
| `0x000A` | `CAPABILITY_BOUNDS_FAULT` | Capability fault | Cursor, fetch, load/store, or bounds derivation exceeds capability bounds. |
| `0x000B` | `CAPABILITY_PERMISSION_FAULT` | Capability fault | Required capability permission is missing, except local-store failures. |
| `0x000C` | `CAPABILITY_SEAL_TYPE_FAULT` | Capability fault | Sealed capability used incorrectly or object type authority mismatch. |
| `0x000D` | `CAPABILITY_LOCAL_STORE_FAULT` | Capability fault | Local capability stored through destination authority without `SL`. |
| `0x000E` | `DEBUG_HALT` | Debug halt | External debug halt request or debug-mode entry condition. |

Values `0x000F-0x001F` are reserved for future mandatory synchronous exception classes.

## Assigned Specific Fault Causes

Some earlier stories define more specific named faults. E07-S02 assigns these names values in the same `CAUSE` namespace.

| `CAUSE` value | Name | Broader class | Notes |
| ---: | --- | --- | --- |
| `0x0020` | `RESERVED_CSR_FAULT` | Illegal instruction | Scalar CSR number is reserved, future, unimplemented, or undocumented. |
| `0x0021` | `ILLEGAL_CSR_READ` | Illegal instruction | CSR exists but does not permit the requested read. |
| `0x0022` | `ILLEGAL_CSR_WRITE` | Illegal instruction | CSR exists but does not permit the requested write or field value. |
| `0x0023` | `CSR_PRIVILEGE_FAULT` | Privilege violation | Scalar CSR access is otherwise legal but current privilege is too low. |
| `0x0024` | `RESERVED_CCSR_FAULT` | Illegal instruction | Capability CSR index is reserved or unimplemented. |
| `0x0025` | `ILLEGAL_CCSR_ACCESS` | Illegal instruction | CCSR exists but does not support the requested operation. |
| `0x0026` | `CCSR_PRIVILEGE_FAULT` | Privilege violation | CCSR access is otherwise legal but current privilege is too low. |
| `0x0030` | `RETURN_STACK_UNDERFLOW` | Capability fault | `RET` pop has no valid pushed return entry. `CAPCAUSE` gives the underlying tag, bounds, or seal/type reason when applicable. |
| `0x0031` | `RETURN_STACK_OVERFLOW` | Capability fault | `CALL` protected push target is outside `RSC` bounds. `CAPCAUSE = BOUNDS`. |
| `0x0032` | `RETURN_STACK_PERMISSION_FAULT` | Capability fault | Protected return-stack access lacks authority or ordinary access targets protected return storage. `CAPCAUSE` gives the underlying reason. |

Values `0x0033-0x00FF` are reserved for future architecture-defined specific synchronous causes.

A handler that does not care about the specific CSR, CCSR, or return-stack cause may classify the value by the broader class column.

## Capability Fault Reporting

For capability-related causes, hardware also populates capability-fault reporting state:

- `CAPCAUSE`
- `FAULTCAPIDX`
- `TVAL`

Mapping to `CAPCAUSE`:

| `CAUSE` value | `CAPCAUSE` |
| ---: | --- |
| `CAPABILITY_TAG_FAULT` | `TAG` |
| `CAPABILITY_BOUNDS_FAULT` | `BOUNDS` |
| `CAPABILITY_PERMISSION_FAULT` | `PERMISSION` |
| `CAPABILITY_SEAL_TYPE_FAULT` | `SEAL_TYPE` |
| `CAPABILITY_LOCAL_STORE_FAULT` | `LOCAL_STORE` |
| `RETURN_STACK_UNDERFLOW` | `TAG`, `BOUNDS`, or `SEAL_TYPE`, according to the failing return slot check |
| `RETURN_STACK_OVERFLOW` | `BOUNDS` |
| `RETURN_STACK_PERMISSION_FAULT` | `TAG`, `PERMISSION`, `LOCAL_STORE`, or `SEAL_TYPE`, according to the failing protected-stack check |

`FAULTCAPIDX` and `TVAL` follow E03-S06, E04-S05, E05-S04, and E06-S01.

For non-capability exceptions, trap entry must set:

```text
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

E07-S04 defines the exact trap-entry write sequence.

## Baseline `TVAL` Rules

`TVAL` records a relevant cell address or scalar value when one exists.

| Exception source | Baseline `TVAL` |
| --- | --- |
| Instruction fetch capability fault | Attempted fetch cell address or first consumed out-of-bounds cell. |
| Instruction placement `ALIGN_FAULT` | Faulting instruction cell address. |
| Explicit slot-1 control-transfer target | Target cell address. |
| Data load/store or capability load/store fault | Effective cell address or capability slot base. |
| Capability derivation bounds fault | Attempted cursor, requested base, or requested top as defined by the owning instruction story. |
| Page fault | Faulting virtual cell address. |
| Access fault | Faulting physical or effective cell address when known, otherwise `0`. |
| CSR or CCSR fault | CSR number or CCSR index in bits `[7:0]` when the selector decoded, otherwise `0`. |
| Illegal instruction from malformed encoding | `0`, unless the opcode story later chooses to report instruction bits. |
| Divide by zero | `0`. |
| Breakpoint | Faulting instruction cell address. |
| Syscall/software trap | Syscall instruction cell address. |
| Debug halt | `0` unless the debug story defines a more specific value. |

All `TVAL` addresses are cell addresses, not byte addresses.

## Recoverability

Recoverability is a contract between hardware and privileged software, not a promise that the original user program can continue unchanged.

| Cause family | Recoverability |
| --- | --- |
| `ILLEGAL_INSTRUCTION`, CSR illegal/reserved faults | Recoverable by trap handler emulation, signal delivery, or process termination. |
| `BREAKPOINT` | Recoverable through debugger or kernel policy. |
| `PRIVILEGE_FAULT`, `CSR_PRIVILEGE_FAULT`, `CCSR_PRIVILEGE_FAULT` | Recoverable by kernel policy; normally delivered as a user fault or kernel bug. |
| `DIVIDE_BY_ZERO` | Recoverable by language/runtime policy or process termination. |
| `ALIGN_FAULT` | Recoverable by emulation or process termination. |
| `ACCESS_FAULT` | Platform-defined; recoverable for some device or memory-type cases, fatal for unrecoverable hardware errors. |
| `PAGE_FAULT` | Recoverable if the kernel can install or repair a translation; otherwise process or kernel fatal by policy. |
| `SYSCALL_TRAP` | Recoverable and expected; it is the normal user-to-kernel service path. |
| Capability faults | Recoverable by kernel policy; normally indicate invalid authority and are delivered as user faults or kernel bugs. |
| Return-stack faults | Recoverable only by privileged unwind/debug/runtime policy; normally security-critical. |
| `DEBUG_HALT` | Recoverable by debug resume policy. |

If trap entry itself cannot be delivered because the kernel trap state is invalid, the core is in a fatal platform state. E07-S04 and E12 stories define trap-entry and debug escalation behavior.

## Default Exception Priority

E07-S02 defines the default priority for simultaneous faults on one instruction. Lower number means higher priority.

| Priority | Fault source |
| ---: | --- |
| 1 | Reset, externally forced debug entry, or implementation fatal platform condition. Final debug priority is refined by E12. |
| 2 | Synchronous exception from the current instruction. A synchronous exception prevents delivery of ordinary maskable interrupts for that instruction. |
| 3 | Fetch authorization faults through `PCC`: tag, seal/type, `EX`, or bounds. |
| 4 | Instruction placement faults discovered by fetch/decode: illegal slot, illegal 48-bit fetch-group placement, explicit slot-1 target known before execution. |
| 5 | Malformed or unsupported instruction encoding, malformed operand class, reserved instruction form. |
| 6 | CSR/CCSR selector, access-class, and privilege faults for CSR/CCSR instructions. |
| 7 | Generic privilege faults for decoded non-CSR privileged instructions. |
| 8 | Explicit synchronous traps: `BRK`, `SYS` or `SCALL`. |
| 9 | Instruction-defined source operand capability checks in the order defined by the owning instruction story. |
| 10 | Address-generation overflow or underflow. |
| 11 | Alignment faults for data, capability, stack, or control-target accesses. |
| 12 | Capability bounds, permission, local-store, and seal/type faults for the effective access, when not already covered by instruction-specific priority. |
| 13 | Translation and page faults. |
| 14 | Physical, device, memory-type, or bus access faults. |
| 15 | Arithmetic execution faults such as divide by zero. |
| 16 | Debug single-step completion after an otherwise successful instruction. E12-S03 refines this. |
| 17 | Maskable interrupts. E07-S05 refines interrupt priority and threshold behavior. |

Instruction-specific check ordering already defined by an owning story is authoritative within that instruction. For example, E04-S05 defines detailed capability operand check order for `CLC`, `CSC`, `CSEAL`, and `CUNSEAL`.

E09-S07 owns the final effective-access priority between capability, translation, privilege, and alignment faults for memory accesses. It must preserve:

- Fetch/decode faults occur before memory-side effects.
- Faulting instructions do not partially update destination registers, memory payload, or memory tags.
- The selected fault is deterministic for a fixed architectural state.

## Out of Scope for This Story

- Precise retire, rollback, and commit-point requirements: E07-S03.
- Trap-entry state updates to `EPCC`, `SR`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX`: E07-S04.
- Vectored interrupt causes and interrupt priority: E07-S05.
- Effective access priority across capability, translation, privilege, and memory-type checks: E09-S07.
- Debug-mode halt/resume, breakpoint policy, and single-step priority refinements: E12 stories.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CAUSE=0x0001` for malformed instruction encoding.
- `CAUSE=0x0002` for `BRK`.
- `CAUSE=0x0003` or the specific CSR/CCSR privilege cause for insufficient privilege.
- `CAUSE=0x0004` for divide or modulo by zero.
- `CAUSE=0x0005` for slot-1 24-bit or 48-bit instruction placement.
- `CAUSE=0x0007` for page faults once E09 page-table behavior is implemented.
- `CAUSE=0x0008` for `SYS` or `SCALL`.
- `CAUSE=0x0009-0x000D` for baseline capability faults.
- `CAUSE=0x0020-0x0026` for assigned CSR and CCSR specific faults.
- `CAUSE=0x0030-0x0032` for assigned protected return-stack faults.
- Non-capability faults write `CAPCAUSE=NONE` and `FAULTCAPIDX=NONE`.
- Capability faults write the matching `CAPCAUSE` value.
- `TVAL` reports cell addresses, not byte addresses.
- A synchronous exception from the current instruction takes priority over an ordinary maskable interrupt.
- A malformed instruction does not also report divide by zero, page fault, or access fault.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Illegal instruction, breakpoint, privilege violation, divide by zero, alignment fault, access fault, page fault, syscall/software trap, capability tag fault, capability bounds fault, capability permission fault, capability seal/type fault, capability local-store fault, and debug halt are defined. | Met. |
| Each exception has a `CAUSE` value. | Met. |
| Exception priority for simultaneous faults is specified. | Met. |
| Recoverable versus fatal behavior is documented where applicable. | Met. |

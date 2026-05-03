# E01-S04: Special Capability Registers

Story: E01-S04

Status: Complete

Normative source: `design.md`, sections 3.3, 4, 10, and 14

Prerequisite: `spec/E01-S03-general-capability-registers.md`

Related sources:

- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E05-S03-data-stack-model.md`

## Decision

CPU v0.1 has 8 per-core special capability registers:

- `PCC`
- `DSC`
- `RSC`
- `DDC`
- `EPCC`
- `TVC`
- `KSC`
- `KRC`

Each special capability register contains a 96-bit capability payload plus one out-of-band validity tag, using the same capability representation as general capability registers.

`PCC` and `EPCC` also carry the hidden instruction slot bit defined by E01-S05. The slot bit is architectural state associated with the register, but it is not part of the 96-bit capability payload.

## Register Map

| Register | Purpose | Implicit use | Explicit access privilege |
| --- | --- | --- | --- |
| `PCC` | Program-counter capability. Authorizes instruction fetch and carries the current execution cursor. | Fetch, branches, calls, returns, traps, `IRET` | Kernel only |
| `DSC` | Data-stack capability. Authorizes data-stack loads, stores, pushes, pops, spills, and stack arguments. | Stack ABI operations | Kernel only |
| `RSC` | Return-stack capability. Authorizes protected return-stack operations. | `CALL` and `RET` return-state handling | Kernel only |
| `DDC` | Default data capability. Authorizes memory access only for instruction forms that explicitly use the default data capability. | Explicit DDC-form loads/stores | Kernel only |
| `EPCC` | Exception program-counter capability. Captures the interrupted or faulting execution capability and slot. | Trap entry and `IRET` | Kernel only |
| `TVC` | Trap-vector capability. Authorizes fetch of trap and interrupt entry code. | Trap and interrupt entry | Kernel only |
| `KSC` | Kernel trap-stack capability. Provides kernel stack authority during trap handling and privileged runtime code. | Trap/software convention, finalized by E07-S04 | Kernel only |
| `KRC` | Kernel root capability. Holds privileged root authority used by firmware and kernel to derive controlled authority. | Kernel derivation and setup | Kernel only |

The explicit access privilege column refers to capability CSR instructions. Ordinary architectural operations may use a special capability implicitly according to their own instruction semantics.

## Privilege Rules

Special capability registers are per-core architectural state.

Explicit reads and writes of special capability registers through capability CSR instructions are privileged in v0.1. User mode cannot execute `CCSRRD` or `CCSRWR` for these registers.

User mode may still use special capability state implicitly:

- Instruction fetch uses `PCC`.
- Stack operations use `DSC`.
- Calls and returns use `PCC` and `RSC`.
- Explicit default-data-capability instruction forms use `DDC` when such forms are defined.

User mode cannot directly read, write, widen, reseal, or replace special capability registers through CCSR access. The kernel installs user context authority before entering user mode and regains control through the trap path.

Kernel mode may read and write special capability registers through CCSR access, subject to the detailed CCSR semantics defined by E02-S05. Kernel writes must not create capability tags from integer data; they copy existing capability payload and tag state from a capability source.

## Capability CSR Index Reservation

The v0.1 special capability CCSR index space reserves these indices:

| CCSR index | Register |
| ---: | --- |
| 0 | `PCC` |
| 1 | `DSC` |
| 2 | `RSC` |
| 3 | `DDC` |
| 4 | `EPCC` |
| 5 | `TVC` |
| 6 | `KSC` |
| 7 | `KRC` |

Indices `8-255` are reserved unless later architecture stories assign them.

Reserved baseline access forms:

```text
CCSRRD Cd, idx
CCSRWR idx, Cs
```

Baseline rules:

- `CCSRRD` copies the selected special capability payload and tag into a general capability destination register.
- `CCSRWR` copies a general capability payload and tag into the selected special capability register.
- Both instructions are privileged for the v0.1 special capability register map.
- Invalid or reserved indices fault according to the CCSR story.
- Detailed fault codes, read-only cases, atomicity, and side effects are finalized by E02-S05.

For `PCC` and `EPCC`, the hidden slot bit is not part of the capability payload copied by `CCSRRD` or `CCSRWR`. Unless a later story defines a slot-aware CCSR form, explicit CCSR writes to `PCC` or `EPCC` set the associated hidden slot to 0. Hardware trap entry and sequential fetch still update slot state according to E01-S05.

## Reset-time Responsibility

Reset-time special capability initialization is split between hardware and ROM/firmware.

### Hardware Reset

On cold reset, hardware is responsible for:

- Starting core 0 in kernel privilege.
- Installing a valid `PCC` on core 0 that authorizes execution of the fixed ROM reset vector.
- Setting the core 0 `PCC` hidden slot to 0.
- Keeping interrupts disabled until firmware configures trap state.
- Initializing other special capability tags to invalid unless the platform reset story defines a stronger initial value.

Non-boot cores do not begin normal instruction execution after cold reset. Their special capability state is invalid or implementation-reset state until ROM/firmware brings them up through the secondary-core startup protocol.

### ROM/Firmware Initialization

ROM or firmware is responsible for installing usable early privileged authority:

- `KRC` for kernel or firmware root authority.
- `KSC` for early kernel/trap stack authority.
- `DSC` for initial data-stack authority.
- `RSC` for protected return-stack authority.
- `TVC` before enabling traps or interrupts.
- `DDC` if default-data-capability forms will be used.

`EPCC` is invalid until the first trap or until firmware explicitly initializes it for a controlled transfer path.

E11-S01 and E11-S02 refine the complete reset-state table and reset capability contents.

## Register-specific Notes

### `PCC`

`PCC` authorizes instruction fetch. A valid fetch requires `PCC` to be tagged, unsealed, in bounds for the attempted fetch cell address, and execute-authorized.

Normal sequential execution updates `PCC.cursor` and the hidden slot bit. Explicit branches, calls, returns, traps, and interrupt entry target slot 0.

### `DSC`

`DSC` is the data-stack capability defined by E05-S03. It should normally carry local stack authority and include `SL` when local capability spills are required.

### `RSC`

`RSC` is the protected return-stack capability. Ordinary data stack operations do not use it. `CALL` and `RET` use `RSC` for protected return state; the detailed return-stack ABI is defined by E05-S04.

### `DDC`

`DDC` is not a general ambient pointer. It authorizes memory access only when an instruction form explicitly selects default-data-capability addressing. Instructions that name a general capability source do not use `DDC`.

### `EPCC`

`EPCC` captures the faulting or interrupted execution capability and hidden slot for precise trap return. `IRET` restores execution state from `EPCC` according to the trap-return story.

### `TVC`

`TVC` authorizes trap and interrupt vector fetch. Trap entry targets slot 0. A missing tag, missing execute permission, sealed state, out-of-bounds vector target, or invalid slot raises the appropriate fault defined by the trap and capability fault stories.

### `KSC`

`KSC` provides kernel stack authority for trap handlers and privileged runtime code. The exact trap-frame convention and any hardware use of `KSC` are deferred to E07-S04.

### `KRC`

`KRC` holds kernel root authority. It is kernel-only and should not be installed into user context. Kernel software derives narrower capabilities from `KRC` for address spaces, stacks, devices, and other controlled resources.

## Out of Scope for This Story

- Scalar CSR namespace and mandatory CSR table: E02-S01 and E02-S02.
- Full `CCSRRD` and `CCSRWR` instruction semantics: E02-S05.
- Execute authority and `PCC` cursor advancement details: E06-S01.
- Return capability and return-stack semantics: E05-S04 and E06-S03.
- Trap entry and trap return sequencing: E07-S04.
- Complete reset capability contents: E11-S02.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Each core has independent `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC` state.
- Each special capability register carries payload plus tag.
- `PCC` and `EPCC` carry hidden slot state.
- Core 0 reset installs a valid ROM `PCC` with slot 0.
- Other special capabilities are invalid after hardware reset until ROM/firmware initializes them.
- User-mode `CCSRRD` and `CCSRWR` to special capability indices fault.
- Kernel-mode `CCSRRD` preserves payload and tag when copying to `C0-C7`.
- Kernel-mode `CCSRWR` copies payload and tag from `C0-C7`.
- CCSR indices `0-7` select the named special capability registers.
- CCSR writes to `PCC` or `EPCC` set the hidden slot to 0 unless a later slot-aware form is defined.
- Fetch through `PCC` cannot bypass capability tag, bounds, seal, or execute-permission checks.
- Trap vector fetch through `TVC` cannot bypass capability tag, bounds, seal, or execute-permission checks.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC` are defined. | Met. |
| Each special capability register has a purpose and privilege rule. | Met. |
| Reset-time initialization responsibility is assigned to hardware, ROM, or firmware. | Met. |
| Access paths through capability CSR instructions are specified or reserved. | Met. |

# CPU v0.1 Agile Backlog

Source architecture document: `design.md`

## Product Goal

Build a coherent v0.1 architecture definition for a 4-core, in-order, server-style, pure-capability CPU with a 24-bit cell-addressed memory model, 48-bit architectural addresses, virtual memory, coherent CPU caches, user/kernel privilege, precise traps, and CHERI-inspired capability integrity.

This backlog is written for architecture, RTL, simulator, firmware, toolchain, OS, and verification work. The intent of v0.1 is not a complete production processor. The intent is to make the architecture precise enough that a first simulator, formal model, assembler subset, and RTL prototype can be built without inventing missing rules.

## Roles

- CPU architect: owns the architectural contract and design decisions.
- RTL engineer: implements the core, caches, MMU, and interrupt-facing hardware.
- Verification engineer: proves and tests architectural behavior.
- Toolchain engineer: builds assembler, disassembler, ABI, and compiler-facing rules.
- Firmware engineer: owns reset, boot, secondary-core bring-up, and platform setup.
- Kernel engineer: owns privilege, traps, virtual memory, atomics, and scheduling assumptions.
- Security engineer: validates capability integrity and control-flow protection.

## Definition of Done for v0.1 Stories

A story is done when:

- The behavior is specified in architectural terms.
- Required state, instructions, exceptions, and alignment rules are named.
- Edge cases are documented.
- At least one verification strategy exists.
- Dependencies on firmware, OS, toolchain, or RTL are identified.
- Any open design choice is explicitly marked as deferred, reserved, or blocked by a spike.

## Epic Summary

| Epic | Name | Primary Outcome |
| --- | --- | --- |
| E01 | Architectural Foundation | Cell addressing, registers, status, and PC slot behavior are defined. |
| E02 | CSR and Control State | Scalar and capability control state can scale past short encodings. |
| E03 | Capability Model | Capabilities are unforgeable, bounded, permissioned, tagged, and sealable. |
| E04 | ISA and Encoding | The base instruction set and instruction-size rules are usable by tools and RTL. |
| E05 | ABI and Calling Convention | Calls, returns, stacks, arguments, and saved registers are stable enough for tools. |
| E06 | Control-Flow Protection | Forward and backward control flow use sealed capabilities and protected return state. |
| E07 | Privilege, Exceptions, and Interrupts | User/kernel execution, precise traps, and vectored interrupts are specified. |
| E08 | Atomics and Memory Ordering | LL/SC and a TSO-like memory model are defined for 4-core software. |
| E09 | MMU and Virtual Memory | Page tables, TLBs, ASIDs, and effective access checks are specified. |
| E10 | Cache and Coherence | Private L1s, shared inclusive L2, CPU coherence, and cache maintenance are defined. |
| E11 | Boot, Reset, and Multicore Bring-up | Cold reset and secondary-core startup have a deterministic platform contract. |
| E12 | Debug and Observability | Breakpoints, watchpoints, single-step, counters, and debug mode are defined. |
| E13 | Microarchitecture MVP | The first in-order pipeline, hazards, long-latency units, and predictor are bounded. |
| E14 | Prototype Risk Spikes | The riskiest design choices are prototyped before the rest of the backlog hardens. |

## Story Refinement Matrix

Priority:

- P0: unblocks the architecture contract or can change many later stories.
- P1: required for a usable v0.1 simulator, RTL model, firmware path, or kernel contract.
- P2: needed for a complete v0.1 document, but can follow the first executable model.

Size:

- S: small, mostly one focused spec update and targeted tests.
- M: medium, one bounded design area with edge cases.
- L: large, cross-functional design requiring simulator or RTL implications.
- XL: too large for one sprint; split into spec, model, RTL, and verification tasks before implementation.
- Spike: time-boxed research or prototype with a written recommendation.

### E01 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E01-S01 | P0 | M | None | Normative address-unit section defining cell, object sizes, fetch groups, pages, and cache-line units. | Address arithmetic examples, alignment examples, and ABI/toolchain review. |
| E01-S02 | P0 | M | E01-S01 | Integer register table with width forms, narrow-write behavior, and flag side effects. | ALU writeback tests for zero/sign/full-width forms and non-flag-setting arithmetic. |
| E01-S03 | P0 | M | E01-S01 | General capability register definition with tag, authorization, and non-dereferenceable integer-address rule. | Capability register move, load/store authorization, and invalid-tag tests. |
| E01-S04 | P0 | L | E01-S03 | Special capability register map with reset, privilege, trap, and access rules. | Reset-state tests, privileged access tests, and trap entry capability-state tests. |
| E01-S05 | P0 | M | E01-S01 | PC slot state rules for branch, call, return, trap, and fall-through behavior. | Fetch/decode tests for slot 0 entry, slot 1 fall-through, and illegal slot targets. |
| E01-S06 | P0 | M | E01-S02 | `SR` bitfield definition with privilege, interrupt, slot, and condition-code update rules. | Flag tests, trap-state save/restore tests, and reserved-bit behavior tests. |

### E02 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E02-S01 | P1 | M | E01-S06 | CSR namespace map with 256 architectural numbers, 16 fast entries, and reserved behavior. | CSR decode tests, reserved CSR tests, and privilege matrix review. |
| E02-S02 | P1 | L | E02-S01 | Mandatory CSR register table with access mode, scope, reset value, and side effects. | CSR read/write tests and per-core versus global CSR tests. |
| E02-S03 | P2 | M | E02-S01 | Extended CSR reservation map for performance, cache, TLB, capability fault, and platform interrupt state. | Unsupported-access tests and forward-compatibility review. |
| E02-S04 | P1 | M | E02-S01 | Semantics for `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR`, including read-modify-write atomicity. | Instruction tests for CSR read/write/set/clear and privilege faults. |
| E02-S05 | P1 | M | E01-S04, E03-S01 | Semantics for `CCSRRD` and `CCSRWR`, including tag preservation and privileged capability-state access. | CCSR read/write tests, tag tests, invalid index tests, and privilege tests. |

### E03 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E03-S01 | P0 | L | E01-S03, E14-S01 | Final capability layout decision for 96-bit format plus out-of-band tag. | Bounds-codec results reviewed, encode/decode tests passing, and precision report accepted. |
| E03-S02 | P0 | M | E03-S01 | Permission-bit table with architectural effect, fault cause, and monotonic reduction rule. | Permission matrix tests for load, store, execute, capability load/store, seal, and unseal. |
| E03-S03 | P0 | L | E03-S02 | Capability derivation rules for bounds, permissions, sealing, invalid tags, and address modification. | Monotonicity tests, invalid operation tests, and formal invariants where practical. |
| E03-S04 | P0 | XL | E03-S01, E14-S04 | Memory tag storage and update rules for `CLC`, `CSC`, `ST48`, alignment, atomicity, and DMA overwrite. | Tag atomicity tests, partial-store tag-clear tests, coherence tests, and DMA overwrite model. |
| E03-S05 | P1 | M | E03-S02 | Local capability rules for `G`, `SL`, stack use, and temporary delegated authority. | Local-store permission tests and stack leak-prevention tests. |
| E03-S06 | P1 | M | E03-S02, E07-S02 | Capability fault reporting contract using `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL`. | Fault injection tests for tag, bounds, permission, seal/type, and local-store faults. |

### E04 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E04-S01 | P0 | L | E01-S01, E01-S05 | Instruction-size, fetch-group, boundary, and target-alignment rules for 12/24/48-bit instructions. | Assembler boundary tests, fetch-group tests, and illegal-crossing tests. |
| E04-S02 | P1 | L | E01-S02, E04-S01 | Integer ISA table with operands, signedness, flags, overflow, divide faults, and encoding class. | ALU conformance tests, divide-by-zero tests, and encoding/decoding round trips. |
| E04-S03 | P0 | L | E03-S04, E09-S07 | Data and capability load/store semantics with alignment, authorization, page checks, and tag behavior. | Load/store tests covering alignment, permission, tag, page, and privilege faults. |
| E04-S04 | P1 | L | E04-S01, E06-S03, E07-S04 | Control-transfer ISA semantics for branches, calls, returns, breakpoints, syscalls, `IRET`, `WFI`, and `PAUSE`. | Branch/call/return tests, syscall/trap tests, and privilege tests. |
| E04-S05 | P0 | L | E03-S03, E04-S01 | Capability instruction semantics with tag propagation, bounds, permissions, sealing, and faults. | Capability instruction conformance tests and derivation monotonicity tests. |
| E04-S06 | P1 | M | E02-S04, E08-S01, E08-S04 | Final mandatory v0.1 instruction checklist with privilege class and optional-future exclusions. | ISA completeness review and assembler opcode coverage report. |

### E05 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E05-S01 | P1 | M | E01-S02 | Integer calling convention table with args, returns, caller-saved, callee-saved, and deferred variadic rules. | Assembly function-call examples and register-preservation tests. |
| E05-S02 | P1 | M | E01-S03, E03-S03 | Capability calling convention table with args, return, saved registers, and tag-preservation expectations. | Capability argument/return examples and saved-register tag tests. |
| E05-S03 | P0 | L | E03-S05 | Data-stack ABI defining `DSC`, growth direction, alignment, `PUSH/POP`, and local capability storage. | Stack-frame examples, alignment tests, and local capability store tests. |
| E05-S04 | P0 | L | E01-S04, E03-S03, E06-S03 | Return-stack ABI defining `RSC`, protected return storage, underflow/overflow, and access restrictions. | Nested call/return tests, underflow/overflow tests, and ordinary-store rejection tests. |

### E06 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E06-S01 | P0 | M | E01-S04, E03-S02 | `PCC` execute-authority rule for instruction fetch, bounds, permissions, and cursor advancement. | Fetch permission tests, bounds tests, and slot advancement tests. |
| E06-S02 | P1 | L | E03-S03, E04-S04 | Sealed entry capability model and `CALLC` atomic unseal-and-enter semantics. | Valid entry-call tests and invalid seal/type tests. |
| E06-S03 | P0 | L | E01-S04, E03-S03 | Sealed return capability model for `CALL`, `RET`, return object type, and tamper resistance. | Nested return tests, tampered return tests, and tag/seal fault tests. |
| E06-S04 | P0 | XL | E05-S04, E07-S03, E14-S05 | Protected return-stack access model across calls, returns, traps, unwind, and debug access. | Trap-during-call tests, debug unwind tests, and precise-state tests. |

### E07 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E07-S01 | P1 | M | E01-S06 | User/kernel privilege model with no v0.1 virtualization and a privileged operation list. | Privileged instruction tests and user-mode violation tests. |
| E07-S02 | P1 | L | E07-S01 | Exception cause table with priority, recoverability, and mandatory exception classes. | Fault-priority tests and cause-code conformance tests. |
| E07-S03 | P0 | L | E07-S02 | Precise exception contract for retire, state commit, long-latency operations, and fault priority. | Pipeline replay/kill tests and architectural-state comparison tests. |
| E07-S04 | P1 | L | E01-S04, E02-S02, E07-S03 | Direct exception trap-entry semantics with `EPCC`, `SR`, `CAUSE`, `TVAL`, and `CAPCAUSE`. | Trap-entry tests and software trap-frame examples. |
| E07-S05 | P1 | L | E02-S02, E07-S04 | Vectored interrupt model for timer, software IPI, external interrupt, threshold, and priority. | Timer/IPI/external interrupt tests and vector address tests. |
| E07-S06 | P1 | M | E07-S04, E07-S05 | Nested interrupt rule with one hardware-saved level and software-managed deeper nesting. | Nested interrupt tests, `IRET` restore tests, and re-enable tests. |

### E08 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E08-S01 | P1 | M | E04-S03, E10-S03 | `LL48` and `SC48` semantics with alignment, reservation granule, success/failure result, and spurious failure. | Atomic instruction tests and alignment/failure tests. |
| E08-S02 | P1 | M | E08-S01 | LL/SC progress and reservation-clear rules for interrupts, context switches, stores, and coherence events. | Contended/uncontended retry tests and reservation-clear tests. |
| E08-S03 | P0 | XL | E01-S01, E10-S01 | TSO-like coherent, multi-copy-atomic memory model including tag visibility and device-memory exceptions. | Litmus tests, store-buffer tests, and cross-core tag visibility tests. |
| E08-S04 | P1 | L | E08-S03, E09-S03, E10-S05 | Fence instruction semantics for data memory, instruction fetch, TLB invalidation, DMA, and privilege. | Fence litmus tests, self-modifying-code tests, and TLB/cache maintenance tests. |

### E09 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E09-S01 | P0 | M | E01-S01 | Virtual/physical address and base-page-size definition with future large-page reservation. | Page-size math review and address-range tests. |
| E09-S02 | P1 | M | E02-S02, E09-S01 | `SATP` layout, mode values, ASID field, root PPN field, and illegal-write behavior. | `SATP` write/read tests and mode-switch tests. |
| E09-S03 | P1 | L | E09-S02 | TLB model with private ITLB/DTLB, ASIDs, local invalidation, and IPI-based shootdown. | ASID tests, invalidate tests, and remote shootdown simulations. |
| E09-S04 | P0 | L | E09-S01, E14-S03 | Page-table geometry decision for 4-level radix base pages and reserved large-page path. | Page-walk model, VPN split tests, and large-page compatibility analysis. |
| E09-S05 | P1 | L | E09-S04 | 48-bit PTE format with valid, leaf, non-leaf, accessed, memory-type, and reserved-bit behavior. | Page-walk tests, reserved-bit fault tests, and PTE permission tests. |
| E09-S06 | P1 | M | E09-S05, E10-S05 | Memory-type semantics for cacheable, uncacheable, device ordered, and reserved pages. | Cacheability tests and device-ordering fence tests. |
| E09-S07 | P0 | L | E03-S02, E07-S01, E09-S05 | Effective access rule combining capability, translation, privilege, and alignment checks with fault priority. | Fault-priority matrix tests and representative load/store/fetch tests. |

### E10 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E10-S01 | P1 | M | E01-S01 | Cache hierarchy contract for private L1I/L1D, shared inclusive L2, write-back, and write-allocate. | Cache-configuration review and basic hit/miss model tests. |
| E10-S02 | P1 | S | E10-S01 | Cache line definition in cells with 16-cell, 48-byte MVP size and alignment implications. | Address-index examples and cache-line boundary tests. |
| E10-S03 | P0 | XL | E03-S04, E08-S03, E10-S01 | CPU coherence model with MESI-like states, L2 coherence point, TSO visibility, and tag participation. | Cross-core coherence tests and tag visibility tests. |
| E10-S04 | P1 | L | E03-S04, E10-S05 | Noncoherent DMA policy with driver responsibilities, cache maintenance, fences, and tag clearing. | DMA model tests and cache-maintenance sequence review. |
| E10-S05 | P1 | L | E10-S01, E10-S02 | Privileged cache maintenance operations with range, alignment, and fence interaction rules. | Clean/invalidate operation tests and self-modifying-code sequence tests. |

### E11 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E11-S01 | P1 | M | E01-S04, E02-S02 | Cold reset-state table for core startup, MMU, interrupts, caches, and ROM vector. | Reset-state simulation tests and firmware entry checklist. |
| E11-S02 | P0 | M | E01-S04, E03-S01 | Reset capability-state rules for `PCC`, `KRC`, `KSC`, `DSC`, `RSC`, and invalid initial registers. | Reset capability tests and invalid-tag exposure tests. |
| E11-S03 | P1 | L | E07-S05, E11-S01 | Secondary-core startup protocol using mailbox, IPI/start event, `STARTED` transition, and stack/capability setup. | Multicore boot simulation and invalid-mailbox tests. |

### E12 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E12-S01 | P1 | L | E02-S02, E07-S02 | Debug halt model with `BRK`, debug vector, debug mode entry/exit, and halt/resume control. | Breakpoint/debug-entry tests and halt/resume tests. |
| E12-S02 | P2 | M | E12-S01 | Hardware breakpoint/watchpoint model with match granularity, privilege behavior, and fault interaction. | Breakpoint/watchpoint tests and fault-priority tests. |
| E12-S03 | P2 | M | E12-S01, E01-S05 | Single-step semantics for one architectural instruction, fault priority, and slot behavior. | Single-step tests for 12/24/48-bit instructions and faulting instructions. |
| E12-S04 | P1 | S | E02-S02 | Mandatory `CYCLE` and `INSTRET` counter behavior with width, overflow, and privilege access. | Counter increment and overflow tests. |
| E12-S05 | P2 | M | E02-S03, E12-S04 | Extended counter reservation and `PERFSEL` behavior for misses, traps, LL/SC failures, and capability faults. | Counter-selection tests and unsupported-counter tests. |

### E13 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E13-S01 | P1 | L | E04-S01, E07-S03 | Single-issue in-order pipeline model with named stages and retire as precise-exception point. | Pipeline trace tests and state-commit tests. |
| E13-S02 | P1 | M | E04-S02, E13-S01 | Independent MDU design with busy tracking, normal writeback, and no CSR completion path. | Multiply/divide dependency tests and long-latency writeback tests. |
| E13-S03 | P1 | L | E13-S01, E13-S02 | Hazard-handling requirements for bypassing, scoreboard, load-use interlock, branch flush, and exception kill. | Dependency tests, load-use tests, branch-mispredict tests, and exception replay tests. |
| E13-S04 | P2 | M | E01-S05, E04-S04, E13-S01 | Conservative branch predictor model with direct-branch BHT, return stack, and context flush/partitioning. | Predictor update tests, mispredict recovery tests, and context-switch predictor tests. |

### E14 Refined Stories

| Story | Priority | Size | Depends on | Refined deliverable | Verification path |
| --- | --- | --- | --- | --- | --- |
| E14-S01 | P0 | Spike | E01-S03 | Bounds-compression prototype and decision record for keeping, revising, or expanding 96-bit capabilities. | Encode/decode corpus, rounding analysis, and monotonicity tests. |
| E14-S02 | P0 | Spike | E01-S01, E04-S01, E05-S03 | Toolchain/ABI prototype covering 24-bit cells, fetch groups, instruction encoding, and stack frames. | Assembler examples, encoded binaries, and host byte-assumption report. |
| E14-S03 | P0 | Spike | E09-S01 | Page-table geometry prototype and large-page compatibility recommendation. | Page-walk model and analysis of `2^15` and `2^19` cell pages. |
| E14-S04 | P0 | Spike | E03-S01, E10-S01 | Tag-through-cache prototype covering L1, L2, memory, `CLC`, `CSC`, `ST48`, coherence, and DMA. | Tag atomicity tests, partial-store tests, and cross-core visibility tests. |
| E14-S05 | P0 | Spike | E05-S04, E06-S03, E07-S03 | Protected return-stack model for call, return, trap, debug unwind, underflow, and overflow behavior. | Trap-during-return scenarios, debug unwind scenarios, and precise-state checks. |

## E01: Architectural Foundation

### Goal

Define the core architectural vocabulary and programmer-visible state so all later work uses the same units, alignment rules, and register semantics.

### Stories

#### E01-S01: Define the 24-bit cell memory model

As a CPU architect, I want the smallest addressable unit to be named as a 24-bit cell so that memory, MMU, cache, ABI, and toolchain rules are unambiguous.

Acceptance criteria:

- `cell` is defined as exactly 24 bits.
- All architectural addresses are defined as cell addresses, not byte addresses.
- 48-bit integer objects are defined as 2 aligned cells.
- 96-bit capability objects are defined as 4 aligned cells.
- Fetch groups, pages, and cache lines are described in cells.
- The spec explicitly states that this implies a custom toolchain and ABI.

Artifacts:

- Normative spec section: `design.md` section 2
- Story artifact: `spec/E01-S01-cell-address-model.md`

#### E01-S02: Define integer register semantics

As a toolchain engineer, I want the 16 48-bit integer registers and narrow write rules specified so that code generation and simulation agree.

Acceptance criteria:

- Registers `D0-D15` are defined as 48-bit architectural registers.
- Supported operation widths are listed as 8, 12, 16, 24, 32, and 48 bits.
- Zero-extending, sign-extending, and full-width write forms are specified.
- Flag-setting behavior is not implicit for ordinary arithmetic.
- Illegal or reserved width encodings are documented.

#### E01-S03: Define general capability registers

As a compiler and OS engineer, I want the general capability register file specified so that pointer-carrying values are represented consistently.

Acceptance criteria:

- Registers `C0-C7` are defined.
- Each architectural capability is defined as 96 bits plus an out-of-band tag.
- Integer addresses are not directly dereferenceable in pure-capability mode.
- All instruction fetch, load, and store operations are capability-authorized.

#### E01-S04: Define special capability registers

As a kernel engineer, I want named special capability registers so that execution, data, trap, and root authority are separated.

Acceptance criteria:

- `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC` are defined.
- Each special capability register has a purpose and privilege rule.
- Reset-time initialization responsibility is assigned to hardware, ROM, or firmware.
- Access paths through capability CSR instructions are specified or reserved.

#### E01-S05: Define PC subslot behavior

As an RTL engineer, I want variable-length instruction slot rules specified so that fetch and decode remain deterministic.

Acceptance criteria:

- `PCC` and `EPCC` carry a hidden slot bit.
- Slot 0 and slot 1 are defined.
- Branches, calls, returns, and trap targets enter at slot 0.
- Slot 1 is reachable only by fall-through after a 12-bit instruction.
- Illegal slot targets raise a named exception.

Artifacts:

- Normative spec section: `design.md` section 3.4
- Story artifact: `spec/E01-S05-pc-subslot-behavior.md`

#### E01-S06: Define status register behavior

As a kernel engineer, I want `SR` fields and update rules specified so that traps, privilege, and condition codes are predictable.

Acceptance criteria:

- `Z`, `N`, `C`, `V`, `IE`, `PIE`, `PRIV`, `EXL`, and `SLOT` are defined.
- Current and previous privilege state are represented.
- Arithmetic does not update flags by default.
- `CMP`, `TST`, or explicit flag-setting forms are defined as the source of condition flags.
- Reserved bits have read and write behavior specified.

## E02: CSR and Control State

### Goal

Define a scalable control/status register architecture that supports compact instruction encodings without limiting the architectural namespace.

### Stories

#### E02-S01: Define scalar CSR namespace

As a CPU architect, I want a 256-entry scalar CSR namespace so that future control state can be added without changing the ISA model.

Acceptance criteria:

- 256 scalar CSR numbers are reserved architecturally.
- 16 fast CSRs are identified for short encodings.
- Extended CSR access through long-form instructions is defined.
- Reserved CSR behavior is documented.
- Privilege checks for CSR reads and writes are specified.

#### E02-S02: Define mandatory scalar CSRs

As a kernel engineer, I want mandatory CSRs defined so that traps, timers, page tables, debug, and counters have stable software names.

Acceptance criteria:

- `SR`, `COREID`, `CYCLE`, `INSTRET`, `TVEC`, `CAUSE`, `TVAL`, `SCRATCH`, `IENABLE`, `IPENDING`, `TIMER`, `TIMECMP`, `SATP`, `ASID`, `DEBUGCTL`, and `PERFSEL` are assigned.
- Read-only, write-only, and read-write behavior is specified.
- Reset values are specified or delegated to firmware.
- Per-core versus global scope is specified.

#### E02-S03: Define extended CSR space

As a platform engineer, I want extended CSR locations reserved for performance, cache, TLB, capability faults, and interrupt controller state so that v0.1 can grow without incompatible changes.

Acceptance criteria:

- `PMC0-PMC7`, `CACHECTL`, `TLBCTL`, `FAULTCAPIDX`, and `CAPCAUSE` are reserved.
- Platform-specific interrupt controller CSR space is reserved.
- Unsupported CSR access behavior is specified.
- Counter overflow behavior is defined or explicitly deferred.

#### E02-S04: Define CSR instructions

As an assembler engineer, I want CSR instruction forms specified so that control-state access can be encoded and tested.

Acceptance criteria:

- `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR` are defined.
- Source and destination register behavior is specified.
- Atomicity of read-modify-write forms is specified.
- Privileged access violations raise a named exception.
- Short-form and long-form encodings are distinguished.

#### E02-S05: Define capability CSR access

As a security engineer, I want special capability registers accessed through explicit capability CSR instructions so that capability authority is not confused with scalar control state.

Acceptance criteria:

- `CCSRRD` and `CCSRWR` are defined or reserved for v0.1.
- Valid special capability register indices are listed.
- Privilege requirements are documented.
- Tag preservation rules for CCSR reads and writes are defined.
- Invalid writes cannot forge capability tags.

## E03: Capability Model

### Goal

Specify the CHERI-inspired pure-capability model, including representation, derivation, sealing, local capabilities, memory tags, and fault behavior.

### Stories

#### E03-S01: Define capability representation

As a CPU architect, I want a 96-bit capability format plus tag so that capability state is compact and implementable.

Acceptance criteria:

- The 96-bit layout includes 48-bit cursor/address, 30-bit bounds metadata, 8-bit permissions, 8-bit object type, and 2-bit flags.
- The tag is out-of-band and not stored in addressable memory.
- `otype = 0` means unsealed.
- `otype != 0` means sealed.
- The 30-bit bounds compressor is identified as a prototype risk.

#### E03-S02: Define permission bits

As a security engineer, I want capability permission bits named so that access checks are clear and testable.

Acceptance criteria:

- `LD`, `ST`, `EX`, `LC`, `SC`, `SL`, `SEAL`, and `UNSEAL` are defined.
- Each permission has an architectural effect.
- Missing permissions raise named capability permission faults.
- Permission reduction is monotonic.

#### E03-S03: Define capability derivation rules

As a verification engineer, I want monotonic derivation rules so that capabilities cannot gain authority through legal instructions.

Acceptance criteria:

- Bounds may be narrowed but not widened.
- Permissions may be reduced but not increased.
- Sealed capabilities cannot be dereferenced or modified.
- Invalid-tag capabilities cannot be dereferenced.
- Capability-address modification is allowed only through explicit capability instructions.

#### E03-S04: Define capability memory tag rules

As an RTL engineer, I want memory tag update rules so that capability forging is impossible through ordinary stores.

Acceptance criteria:

- `CLC` loads a full capability and tag atomically.
- `CSC` stores a full capability and tag atomically.
- Any `ST48` into one of the four cells of a capability slot clears that slot's tag.
- Capabilities in memory require 4-cell alignment.
- Non-tag-aware DMA or external overwrites clear tags.
- Tag and data atomicity requirements are stated.

#### E03-S05: Define local capability semantics

As a security engineer, I want local capabilities to be constrained so that stack-derived authority cannot leak into global memory.

Acceptance criteria:

- `G=1` means global capability.
- `G=0` means local capability.
- Local capabilities may be stored only through a capability with `SL=1`.
- Violations raise capability local-store fault.
- Stack and temporary delegation examples are documented.

#### E03-S06: Define capability fault reporting

As a kernel engineer, I want capability fault information exposed so that the OS can diagnose and handle faults.

Acceptance criteria:

- Capability tag, bounds, permission, seal/type, and local-store faults are named.
- `CAPCAUSE` is populated for capability-related traps.
- `FAULTCAPIDX` identifies the relevant source capability where possible.
- Faulting virtual address or cell address behavior is defined through `TVAL`.

## E04: ISA and Encoding

### Goal

Define the v0.1 instruction set and encoding constraints well enough for assembler, disassembler, simulator, and RTL work.

### Stories

#### E04-S01: Define instruction-size and fetch-group rules

As an RTL engineer, I want instruction boundary rules so that fetch, predecode, and trap recovery are simple.

Acceptance criteria:

- Instructions may be 12, 24, or 48 bits.
- Fetch always operates on a 48-bit fetch group.
- No instruction may cross a 48-bit fetch-group boundary.
- 24-bit cell boundaries are the only legal direct branch, call, and trap targets.
- 48-bit instructions must begin at slot 0 of the first cell in a fetch group.

#### E04-S02: Define integer operation set

As a compiler engineer, I want the mandatory integer operations specified so that code generation has a stable target.

Acceptance criteria:

- `CPY`, `NEG`, `ADD`, `ADDU`, `SUB`, `SUBU`, `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, `MODU`, `NOT`, `AND`, `OR`, `XOR`, `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR`, `CMP`, `CMPU`, `TST`, `SETcc`, `CMOVcc`, `BSET`, and `BCLR` are listed.
- Signed and unsigned behavior is defined.
- Divide-by-zero behavior is defined.
- Overflow and flag behavior are defined.
- Encoding category is assigned as 12-bit, 24-bit, or 48-bit where applicable.

#### E04-S03: Define memory operation set

As an RTL engineer, I want data and capability load/store behavior specified so that alignment, checks, and faults are deterministic.

Acceptance criteria:

- `LD48` and `ST48` are defined.
- `CLC` and `CSC` are defined.
- `LD48/ST48` require even-cell alignment.
- `CLC/CSC` require 4-cell alignment.
- Unaligned access raises `ALIGN_FAULT`.
- Load/store capability permission checks are tied to the effective access rule.

#### E04-S04: Define control transfer instructions

As a compiler and kernel engineer, I want branch, call, syscall, trap return, and wait instructions specified so that programs and traps can execute correctly.

Acceptance criteria:

- `BRA`, `Bcc`, `CALL`, `RET`, `JMP`, `BRK`, `SYS` or `SCALL`, `IRET`, `WFI`, and `PAUSE` are defined.
- Direct target slot rules are enforced.
- Conditional branch conditions map to status flags.
- `CALL` and `RET` semantics are compatible with the protected return stack.
- `IRET`, `WFI`, and privileged forms enforce privilege rules.

#### E04-S05: Define capability instruction set

As a compiler engineer, I want capability instructions specified so that pure-capability code can manipulate authority without integer-pointer aliases.

Acceptance criteria:

- `CMOVE`, `CGETADDR`, `CSETADDR`, `CINCADDR`, `CSETBOUNDS`, `CANDPERM`, `CSEAL`, `CUNSEAL`, `CLC`, and `CSC` are defined.
- Tag propagation behavior is specified.
- Bounds, permission, and sealing checks are specified.
- Invalid operations produce named capability faults.

#### E04-S06: Define mandatory MVP additions

As a product owner for the architecture, I want the required missing instructions tracked so that v0.1 is complete enough to execute system software.

Acceptance criteria:

- `LL48`, `SC48`, `FENCE`, `FENCE.I`, `SFENCE.VM`, `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR`, `CCSRRD`, `CCSRWR`, `BRK`, `SYS` or `SCALL`, `WFI`, and `PAUSE` are in the v0.1 ISA list.
- Each instruction has a short description and privilege rule.
- Optional future instructions such as `CAS48` and `CAS96` are excluded from required v0.1.

## E05: ABI and Calling Convention

### Goal

Define a recommended v0.1 ABI early enough to avoid churn in assembler, compiler, simulator tests, firmware, and kernel code.

### Stories

#### E05-S01: Define integer argument and return registers

As a compiler engineer, I want integer calling convention registers specified so that functions can exchange scalar values consistently.

Acceptance criteria:

- Integer arguments use `D0-D5`.
- Integer returns use `D0-D1`.
- Caller-saved integer registers are `D0-D11`.
- Callee-saved integer registers are `D12-D15`.
- Variadic and overflow argument handling is defined or explicitly deferred.

#### E05-S02: Define capability argument and return registers

As a compiler engineer, I want capability calling convention registers specified so that pure-capability pointers and authority pass through calls safely.

Acceptance criteria:

- Capability arguments use `C0-C3`.
- Capability return uses `C0`.
- Caller-saved capability registers are `C0-C5`.
- Callee-saved capability registers are `C6-C7`.
- Tag preservation across call boundaries is specified.

#### E05-S03: Define data stack model

As a toolchain engineer, I want data stack rules specified so that stack frames are generated consistently.

Acceptance criteria:

- `DSC` is the data-stack capability.
- Data stack grows downward in cells.
- `PUSH` and `POP` operate on `DSC`.
- Stack alignment is specified.
- Local capability storage rules are compatible with `SL`.

#### E05-S04: Define return stack model

As a security engineer, I want return addresses separated from data stack writes so that backward-edge control flow is protected.

Acceptance criteria:

- `RSC` is the protected return-stack capability.
- `CALL` and `RET` operate on `RSC`.
- Ordinary data stores cannot write protected return-stack memory unless explicitly allowed by the architecture.
- Return stack underflow, overflow, and permission faults are named.

## E06: Control-Flow Protection

### Goal

Use capability semantics to protect forward and backward control flow without relying on integer return addresses.

### Stories

#### E06-S01: Define execute authority through `PCC`

As a security engineer, I want instruction fetch governed by `PCC` so that code execution is bounded and permissioned.

Acceptance criteria:

- Instruction fetch requires a valid, unsealed, execute-authorized `PCC`.
- Fetch outside `PCC` bounds raises capability bounds fault.
- Fetch without `EX` raises capability permission fault.
- `PCC` cursor advancement respects slot and fetch-group rules.

#### E06-S02: Define sealed entry capabilities

As a kernel and runtime engineer, I want sealed entry capabilities so that protected entry points can be called without exposing raw authority.

Acceptance criteria:

- Entry capability object type is reserved or defined.
- `CALLC Cs` checks for a sealed entry capability.
- Unseal-and-enter behavior is atomic from the architectural point of view.
- Invalid entry capabilities raise seal/type fault.

#### E06-S03: Define sealed return capabilities

As a security engineer, I want return capabilities sealed so that return addresses cannot be forged or modified as data.

Acceptance criteria:

- `CALL` derives a return capability from current `PCC`.
- The return capability is sealed as a return capability.
- `RET` accepts only a valid sealed return capability from `RSC`.
- Invalid or tampered return capabilities raise seal/type or tag fault.

#### E06-S04: Define protected return stack access

As an RTL and kernel engineer, I want return-stack memory protected so that ordinary stores cannot corrupt return state.

Acceptance criteria:

- Return-stack memory is reachable by `CALL` and `RET`.
- Privileged unwind/debug access rules are defined.
- Ordinary store access restrictions are specified.
- Trap behavior while return stack state is partially updated is precise.

## E07: Privilege, Exceptions, and Interrupts

### Goal

Define the minimal privileged architecture needed for user/kernel isolation, precise exceptions, syscall handling, timer/IPI/external interrupts, and nested interrupt control.

### Stories

#### E07-S01: Define privilege levels

As a kernel engineer, I want user and kernel privilege modes defined so that isolation and privileged operations are enforceable.

Acceptance criteria:

- `U` and `K` privilege levels are defined.
- No virtualization level exists in v0.1.
- Privileged instructions and CSRs are identified.
- Privilege violations raise a named exception.

#### E07-S02: Define exception classes

As a verification engineer, I want all mandatory exception classes named so that tests can cover fault behavior.

Acceptance criteria:

- Illegal instruction, breakpoint, privilege violation, divide by zero, alignment fault, access fault, page fault, syscall/software trap, capability tag fault, capability bounds fault, capability permission fault, capability seal/type fault, capability local-store fault, and debug halt are defined.
- Each exception has a `CAUSE` value.
- Exception priority for simultaneous faults is specified.
- Recoverable versus fatal behavior is documented where applicable.

#### E07-S03: Define precise exception model

As an RTL engineer, I want precise exception requirements so that retire and rollback behavior are testable.

Acceptance criteria:

- All exceptions are precise.
- Faulting instruction state is captured in `EPCC`.
- Younger instructions are prevented from committing state.
- Long-latency operations report exceptions at retire.
- Capability and MMU faults have deterministic priority.

#### E07-S04: Define trap entry

As a kernel engineer, I want direct exception trap entry so that the kernel receives enough state to build a software trap frame.

Acceptance criteria:

- Exceptions use direct trap entry.
- Hardware saves `EPCC`.
- `SR.IE` is copied to `SR.PIE`.
- Current privilege is copied to previous privilege state.
- `CAUSE`, `TVAL`, and `CAPCAUSE` are populated where applicable.
- Hardware does not auto-save all GPRs.

#### E07-S05: Define vectored interrupts

As a kernel engineer, I want vectored interrupts so that common timer, IPI, and external interrupt paths can enter quickly.

Acceptance criteria:

- Interrupts use a vectored trap model.
- Per-core trap vector base is defined.
- Timer, software IPI, and external interrupt causes are defined.
- Interrupt priority and threshold behavior are specified or explicitly deferred.

#### E07-S06: Define nested interrupt rules

As a kernel engineer, I want one hardware level of saved trap state so that interrupt nesting is simple and explicit.

Acceptance criteria:

- Hardware saves one level of `IE`, `PIE`, and previous privilege.
- Deeper nesting requires software to save a trap frame.
- Interrupts are re-enabled only by explicit software action.
- `IRET` restores privilege and interrupt enable state.

## E08: Atomics and Memory Ordering

### Goal

Define a practical 4-core synchronization model using LL/SC and a strong memory-ordering contract.

### Stories

#### E08-S01: Define `LL48` and `SC48`

As a kernel engineer, I want aligned 48-bit LL/SC primitives so that locks and atomic updates can be implemented.

Acceptance criteria:

- `LL48` and `SC48` operate on aligned 48-bit words.
- Alignment requires a 2-cell boundary.
- Reservation granule is at least the accessed word and may be the cache line.
- `SC48` success and failure return behavior is defined.
- `SC48` may fail spuriously.

#### E08-S02: Define LL/SC progress guarantee

As a kernel engineer, I want a progress rule so that lock algorithms can rely on bounded retry under non-contention conditions.

Acceptance criteria:

- Progress is guaranteed absent conflicting stores and repeated interruptions.
- Events that clear reservations are listed.
- Context switch and interrupt effects on reservations are specified.
- Cache eviction and coherence invalidation behavior is defined.

#### E08-S03: Define TSO-like memory model

As an OS and compiler engineer, I want a TSO-like coherent memory model so that shared-memory software has a strong and understandable contract.

Acceptance criteria:

- The memory model is coherent and multi-copy atomic.
- Store-buffer ordering behavior is described.
- Load, store, atomic, and fence ordering rules are specified.
- Capability tag visibility follows memory ordering rules.
- Device memory exceptions are called out.

#### E08-S04: Define fence instructions

As a kernel and driver engineer, I want fence instructions specified so that instruction fetch, data memory, MMU, and DMA boundaries are manageable.

Acceptance criteria:

- `FENCE` orders data memory operations.
- `FENCE.I` synchronizes instruction fetch with prior code writes.
- `SFENCE.VM` or equivalent TLB invalidate instruction is defined.
- Privilege rules are specified.
- Fence effects on caches, TLBs, and predictors are documented where applicable.

## E09: MMU and Virtual Memory

### Goal

Define virtual memory, page tables, TLB behavior, and access checks for a pure-capability 48-bit cell-addressed system.

### Stories

#### E09-S01: Define address sizes and page size

As a kernel engineer, I want virtual and physical address sizes and base page size fixed so that page tables and memory maps can be implemented.

Acceptance criteria:

- Virtual addresses are 48-bit cell addresses.
- Physical addresses are 48-bit cell addresses.
- MVP page size is `2^11` cells.
- Future page sizes `2^15` and `2^19` cells are reserved but not implemented in v0.1.

#### E09-S02: Define `SATP`

As a kernel engineer, I want `SATP` layout specified so that address translation can be enabled and switched.

Acceptance criteria:

- `SATP` includes `MODE`, `ASID`, and `ROOT_PPN`.
- Recommended packing is `MODE[2:0]`, `ASID[7:0]`, and `ROOT_PPN[36:0]`.
- Supported `MODE` values are specified.
- Illegal `SATP` writes are handled predictably.

#### E09-S03: Define TLB model

As an RTL and OS engineer, I want TLB behavior specified so that address-space switching and shootdown are correct.

Acceptance criteria:

- Each core has private ITLB and DTLB.
- ASID support is mandatory.
- Local TLB invalidate instructions are mandatory.
- Remote shootdown is performed through IPI.
- TLB behavior on privilege and ASID changes is specified.

#### E09-S04: Define page-table geometry

As an RTL engineer, I want page-table geometry specified so that the hardware walker can be implemented.

Acceptance criteria:

- v0.1 uses a 4-level radix page table.
- PTEs are 48 bits.
- Base pages hold 1024 PTEs.
- VPN split is `7 + 10 + 10 + 10`.
- Large pages are reserved but not implemented.

#### E09-S05: Define PTE format

As a kernel engineer, I want the 48-bit PTE format specified so that page-table memory is unambiguous.

Acceptance criteria:

- PTE includes `PPN[36:0]`, `V`, `U`, `R`, `W`, `X`, `G`, `A`, `MT[1:0]`, and one reserved bit.
- Invalid, non-leaf, and leaf PTE rules are specified.
- Accessed-bit update behavior is defined or delegated to software.
- Reserved-bit violations raise page fault.

#### E09-S06: Define page memory types

As a driver and kernel engineer, I want page memory types specified so that cacheable, uncacheable, and device memory are handled correctly.

Acceptance criteria:

- Normal coherent cacheable memory is defined.
- Normal uncacheable memory is defined.
- Device ordered memory is defined.
- Reserved memory type behavior is specified.
- Fence requirements for device memory are documented.

#### E09-S07: Define effective access rule

As a security and verification engineer, I want the complete access rule specified so that capability, page, privilege, and alignment checks compose correctly.

Acceptance criteria:

- Access succeeds only if the capability is valid, unsealed, in bounds, and has the needed permission.
- The translated page must be valid and have the needed page permission.
- Current privilege mode must allow the access.
- Alignment rules must be satisfied.
- Fault priority between capability, translation, privilege, and alignment faults is specified.

## E10: Cache and Coherence

### Goal

Define the v0.1 cache hierarchy, CPU coherence contract, maintenance operations, and noncoherent DMA policy.

### Stories

#### E10-S01: Define cache hierarchy

As an RTL engineer, I want the cache hierarchy specified so that the first multicore memory system has a clear shape.

Acceptance criteria:

- Each core has private L1 instruction cache.
- Each core has private L1 data cache.
- Cores share an inclusive L2 cache.
- L1 data cache is write-back and write-allocate.
- L2 is the coherence point.

#### E10-S02: Define cache line unit and size

As an RTL engineer, I want cache lines defined in cells so that cache behavior matches the architectural address unit.

Acceptance criteria:

- Cache lines are counted in cells, not bytes.
- MVP cache line size is 16 cells.
- 16 cells are identified as 48 bytes.
- Alignment and index implications are documented.

#### E10-S03: Define CPU coherence protocol

As a verification engineer, I want the CPU coherence behavior specified so that cross-core memory tests can be written.

Acceptance criteria:

- CPU caches are coherent with each other.
- A MESI-like protocol is selected for v0.1.
- Stores become visible according to the TSO-like memory model.
- Capability tags participate in coherent visibility.
- Coherence behavior for instruction and data caches is documented.

#### E10-S04: Define noncoherent DMA policy

As a driver engineer, I want I/O coherence boundaries specified so that device drivers use the right cache maintenance pattern.

Acceptance criteria:

- I/O is outside CPU cache coherence for v0.1.
- DMA/device accesses are noncoherent.
- Drivers must use cache maintenance and fences around DMA.
- Non-tag-aware DMA clears capability tags on overwrite.
- Coherent I/O is explicitly deferred.

#### E10-S05: Define cache maintenance operations

As a kernel and driver engineer, I want cache maintenance operations specified so that DMA, code loading, and page lifecycle operations are safe.

Acceptance criteria:

- `CACHE.CLEAN` is defined as privileged.
- `CACHE.INVAL` is defined as privileged.
- `CACHE.CLEANINVAL` is defined as privileged.
- Required interaction with `FENCE` and `FENCE.I` is documented.
- Address range and alignment behavior are specified.

## E11: Boot, Reset, and Multicore Bring-up

### Goal

Define deterministic cold reset, firmware setup, and secondary-core startup behavior.

### Stories

#### E11-S01: Define cold reset state

As a firmware engineer, I want reset state specified so that ROM code can bring the platform up predictably.

Acceptance criteria:

- Reset starts at a fixed ROM reset vector.
- Only core 0 starts executing after cold reset.
- Other cores enter `STOPPED` or `WFI` parked state.
- MMU is off.
- Interrupts are masked.
- Caches are off or invalid.

#### E11-S02: Define reset capability state

As a security engineer, I want reset capabilities initialized safely so that firmware starts with defined authority.

Acceptance criteria:

- `PCC` is initialized to a ROM code capability.
- `KRC`, `KSC`, `DSC`, and `RSC` are initialized by ROM or firmware.
- Undefined capability registers have defined invalid-tag behavior.
- Reset cannot expose forgeable capability state.

#### E11-S03: Define secondary-core startup

As a firmware and kernel engineer, I want secondary-core bring-up specified so that multicore boot is reliable.

Acceptance criteria:

- Kernel or firmware writes a per-core start mailbox.
- Kernel or firmware sends an IPI or start event.
- Target core transitions to `STARTED`.
- Startup capability and stack state requirements are documented.
- Failed startup or invalid mailbox behavior is specified.

## E12: Debug and Observability

### Goal

Define the minimum debug, inspection, and performance-counter features needed to build and verify the platform.

### Stories

#### E12-S01: Define breakpoint and debug halt behavior

As a verification and tools engineer, I want breakpoint and debug halt behavior specified so that interactive debugging and simulator tests are possible.

Acceptance criteria:

- `BRK` instruction behavior is defined.
- Debug halt exception class is defined.
- Debug mode entry and exit are specified.
- A separate debug vector is defined.
- Halt/resume control is exposed through debug state.

#### E12-S02: Define hardware breakpoints and watchpoints

As a debug tool engineer, I want instruction breakpoints and data watchpoints so that hardware and simulator debugging can observe execution.

Acceptance criteria:

- Hardware instruction breakpoint capability is defined.
- Hardware data watchpoint capability is defined.
- Match granularity and privilege behavior are specified.
- Watchpoint interaction with capability and page faults is specified.

#### E12-S03: Define single-step

As a debug tool engineer, I want single-step behavior specified so that debuggers can advance one architectural instruction at a time.

Acceptance criteria:

- Single-step mode is controlled by debug state.
- One architectural instruction retires before debug re-entry.
- Faulting instructions report their normal fault before or instead of step completion according to a defined priority.
- Slot behavior with 12-bit instructions is specified.

#### E12-S04: Define mandatory counters

As a performance engineer, I want mandatory counters so that basic performance and progress can be measured.

Acceptance criteria:

- `CYCLE` is defined.
- `INSTRET` is defined.
- Counter width and overflow behavior are specified.
- Privilege access policy is specified.

#### E12-S05: Define extended performance counters

As a performance engineer, I want common miss, trap, branch, atomic, and capability-fault counters reserved so that later tuning can use stable names.

Acceptance criteria:

- Counters are reserved for I-cache misses, D-cache misses, L2 misses, ITLB misses, DTLB misses, branch mispredicts, traps taken, LL/SC failures, and capability faults.
- Counter selection through `PERFSEL` is defined or reserved.
- Unsupported counter behavior is specified.

## E13: Microarchitecture MVP

### Goal

Bound the first implementation around a simple single-issue, in-order pipeline while preserving enough structure for capability checks, virtual memory, precise exceptions, and multicore operation.

### Stories

#### E13-S01: Define pipeline stages

As an RTL engineer, I want named pipeline stages so that implementation and verification share a common model.

Acceptance criteria:

- Pipeline is single-issue and in-order.
- Stages are named `FE0`, `FE1`, `PD`, `XLT`, `ISS`, `EX`, `MEM`, `WB`, and `RT`.
- Each stage has a short responsibility.
- Retire is the precise-exception point.

#### E13-S02: Define long-latency multiply/divide unit

As an RTL engineer, I want `MUL`, `DIV`, and `MOD` handled by an independent execution unit so that the pipeline can continue around long operations.

Acceptance criteria:

- Independent `MDU` is defined.
- `MUL` may be pipelined with 2-3 cycle latency.
- `DIV/MOD` may be iterative.
- Destination register busy tracking is required.
- Results return through normal register writeback.
- MDU completion is not exposed through CSR.

#### E13-S03: Define hazard handling

As a verification engineer, I want hazard handling requirements specified so that instruction interaction tests are meaningful.

Acceptance criteria:

- EX, MEM, and WB bypassing is required where possible.
- Scoreboard or busy-bit tracking is required.
- Load-use interlock is required.
- Branch mispredict flush is required.
- Precise exception replay or kill behavior is required.

#### E13-S04: Define branch prediction MVP

As a security and RTL engineer, I want a conservative branch predictor so that performance improves without opening unnecessary indirect prediction surface.

Acceptance criteria:

- Per-core 2-bit BHT is used for direct conditional branches only.
- No generic indirect BTB exists in v0.1.
- Small return-address stack supports `CALL/RET`.
- Predictor state is flushed or partitioned on privilege change and ASID switch.
- Mispredict recovery behavior is specified.

## E14: Prototype Risk Spikes

### Goal

Reduce uncertainty around the design choices most likely to affect the rest of the architecture.

### Stories

#### E14-S01: Spike 96-bit capability bounds compression

As a CPU architect, I want a prototype bounds compressor so that the 96-bit capability format can be validated before the ISA freezes.

Acceptance criteria:

- Prototype can encode and decode representative bounds.
- Precision and rounding behavior are measured.
- Monotonic narrowing behavior is tested.
- Failure cases are documented.
- Recommendation is made to keep, revise, or expand the 96-bit format.

Artifacts:

- Prototype: `tools/cap_bounds_codec.py`
- Decision record: `spikes/E14-S01-capability-bounds-compression.md`

#### E14-S02: Spike 24-bit cell-addressed toolchain and ABI

As a toolchain engineer, I want a small assembler or compiler-facing prototype so that the software impact of cell addressing is understood.

Acceptance criteria:

- Prototype can represent 24-bit cells and 48-bit fetch groups.
- Prototype can encode at least simple integer, branch, load/store, and capability instructions.
- ABI alignment rules are tested with example stack frames.
- Byte-oriented host-tool assumptions are listed.
- Recommendation is made on required custom toolchain scope.

#### E14-S03: Spike page-table geometry and future page sizes

As a kernel and RTL engineer, I want the page-table geometry tested against future large-page goals so that v0.1 does not block later evolution.

Acceptance criteria:

- 4-level base-page walk is modeled.
- `2^11` cell base pages are validated.
- `2^15` and `2^19` cell future page sizes are analyzed against the radix geometry.
- Large-page support is either revised, deferred, or given a compatible encoding plan.

#### E14-S04: Spike capability tag storage through cache hierarchy

As an RTL and verification engineer, I want a model for capability tags moving through L1, L2, and memory so that tag atomicity is implementable.

Acceptance criteria:

- Tag storage granularity is proposed.
- `CLC` and `CSC` atomicity is modeled.
- `ST48` tag-clear behavior is modeled.
- Coherence visibility of tags is tested.
- Noncoherent DMA tag-clear behavior is documented.

#### E14-S05: Spike protected return stack traps

As a security and RTL engineer, I want call, return, trap, and debug interactions modeled so that the protected return stack remains precise and recoverable.

Acceptance criteria:

- `CALL` and `RET` update ordering is modeled.
- Trap entry during call/return sequences is analyzed.
- Debug unwind access is specified.
- Return-stack underflow and overflow behavior is tested.
- Recommendation is made on required hardware assists.

## Suggested MVP Milestones

### Milestone M1: Architecture Contract

Includes:

- E01 Architectural Foundation
- E02 CSR and Control State
- E03 Capability Model
- E04 ISA and Encoding

Exit criteria:

- A simulator author can implement architectural state and execute simple programs.
- An assembler author can begin encoding the mandatory instruction subset.
- A verification engineer can write basic state, trap, and capability tests.

### Milestone M2: System Software Contract

Includes:

- E05 ABI and Calling Convention
- E06 Control-Flow Protection
- E07 Privilege, Exceptions, and Interrupts
- E08 Atomics and Memory Ordering
- E09 MMU and Virtual Memory

Exit criteria:

- A toy kernel can boot in simulation.
- User/kernel transitions, syscalls, traps, and page faults are architecturally defined.
- Locks and basic multicore synchronization have a defined contract.

### Milestone M3: Platform Contract

Includes:

- E10 Cache and Coherence
- E11 Boot, Reset, and Multicore Bring-up
- E12 Debug and Observability
- E13 Microarchitecture MVP

Exit criteria:

- A first RTL or cycle-level model has enough detail to implement multicore execution.
- Debug and counters are sufficient for bring-up.
- Cache, coherence, and DMA boundaries are defined.

### Milestone M0: Risk Spikes

Includes:

- E14 Prototype Risk Spikes

Exit criteria:

- Capability compression, 24-bit tooling, page geometry, tag storage, and protected return stack risks have evidence-backed recommendations.
- Any resulting architecture changes are folded back into `design.md` before v0.1 is frozen.

## Initial Backlog Priority

| Priority | Story | Reason |
| --- | --- | --- |
| 1 | E14-S01 | Capability bounds compression can change the core capability format. |
| 2 | E01-S01 | The cell model affects every other architecture area. |
| 3 | E04-S01 | Fetch and instruction boundary rules affect ISA, RTL, and tools. |
| 4 | E03-S04 | Tag rules are central to capability integrity and memory design. |
| 5 | E09-S04 | Page-table geometry affects the MMU and future large-page path. |
| 6 | E05-S03 | Stack layout interacts with local capabilities and return protection. |
| 7 | E06-S03 | Return capabilities shape calls, traps, debug, and ABI behavior. |
| 8 | E08-S03 | The memory model defines the multicore software contract. |
| 9 | E10-S03 | Coherence must preserve data and capability tag visibility. |
| 10 | E11-S01 | Reset behavior is required before firmware and simulation boot. |

## Out of Scope for v0.1

- Virtualization privilege level.
- Coherent I/O.
- Generic indirect branch target buffer.
- Required CAS instructions.
- Production compiler backend.
- Full operating system port.
- Large-page implementation beyond reserved encodings.
- Rich lock-free atomics beyond `LL48` and `SC48`.
- Final physical layout, timing closure, or silicon implementation plan.

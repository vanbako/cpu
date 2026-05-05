# CPU v0.1 Implementation Backlog

This backlog tracks implementation work for the frozen CPU v0.1 architecture contract.

The architecture backlog remains `agile-v0.1.md`. Implementation work should not reopen architecture decisions unless an implementation story finds a real contradiction or missing rule. In that case, the fix must be recorded as an erratum or a new architecture story before code depends on it.

Primary handoff artifact:

- `spec/v0.1-implementation-checklist.md`

Related freeze artifact:

- `spec/E15-S07-v0.1-freeze-report.md`

## Implementation Strategy

Build the implementation in small executable slices, starting with a semantic simulator and conformance tests.

The first simulator should use an internal decoded-instruction representation. Final binary opcode allocation, object-file serialization, and platform binding can proceed in parallel without blocking architectural behavior tests.

Implementation principles:

- Keep architecture semantics separate from platform policy.
- Keep decoding separate from instruction execution.
- Keep capability payload/tag handling centralized and hard to bypass.
- Add tests with each slice before expanding the surface area.
- Prefer story-derived conformance tests over ad hoc examples.
- Treat RTL as a consumer of the semantic model and conformance suite, not the first executable truth source.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `docs/implementation/` | Mutable implementation notes, platform profiles, opcode plans, and design decisions that are not normative architecture spec. |
| `src/cpu_v01/` | Semantic simulator and implementation libraries. |
| `tests/conformance/` | Story-derived architectural conformance tests. |
| `tests/litmus/` | Memory, ordering, LL/SC, cache, DMA, trap, and debug litmus tests. |
| `tools/` | Existing audit/prototype tools and future generated tables. |

## Epic Roadmap

| Epic | Priority | Goal | First output |
| --- | --- | --- | --- |
| I01 | P0 | Project skeleton and executable test harness. | Importable package, test runner, CI-local commands, and first empty conformance suite. |
| I02 | P0 | Architectural data model. | Cells, addresses, integer registers, capabilities, tags, CSRs, CCSRs, memory objects, and reset state. |
| I03 | P0 | Decoded instruction executor. | Internal instruction enum and semantic execution for the first integer/capability/memory subset. |
| I04 | P0 | Fault, trap, slot, and debug baseline. | Precise exception packets, direct trap entry, `IRET`, `EPCC.slot`, and non-monitor debug halt tests. |
| I05 | P0 | Calls and protected return stack. | `CALL`, `CALLC`, `RET`, sealed entry/return capabilities, and protected stack transactions. |
| I06 | P1 | MMU, atomics, ordering, cache, and DMA model. | `RADIX4`, TLBs, memory types, LL/SC, fences, cache maintenance, and E15-S05 litmus tests. |
| I07 | P0 | Opcode, assembler, and disassembler binding. | Final opcode table, source mnemonics, synonyms, illegal encodings, and binary fixtures. |
| I08 | P0 | Minimal platform profile and boot path. | Test platform memory map, reset vector, ROM hook, interrupt bindings, secondary mailbox, and debug transport model. |
| I09 | P1 | Firmware, kernel, and debugger ABI supplements. | Trap-frame layout, context-switch save set, syscall policy, debug register access, and unwind notes. |
| I10 | P1 | RTL/cycle-level handoff. | Simulator-backed conformance suite, decode tables, commit-point checklist, and RTL interface notes. |
| I11 | P0 | Program image execution. | Serialized cell-image loader, ROM/RAM placement, and reset-to-program execution smoke tests. |
| I12 | P0 | CI and story coverage. | One-command local check runner, story coverage report, and drift checks for tests/docs. |
| I13 | P1 | Cycle-level prototype. | Pipeline trace model checked against semantic retire packets. |
| I14 | P1 | Firmware and kernel bring-up path. | Tiny ROM, trap/syscall/timer handlers, and secondary-core boot demo in simulation. |
| I15 | P1 | Formal and security invariants. | Property-style tests for capability monotonicity, tag integrity, and precise fault effects. |
| I16 | P1 | Formal invariant expansion. | Registry, reusable generators, and seeded invariant runner for security/correctness properties. |
| I17 | P1 | Toolchain and binary pipeline. | Richer assembler/linker fixtures, relocations, object metadata, and debug symbols. |
| I18 | P1 | Kernel/userland bring-up. | User process image, VM allocation, syscall demo, and minimal scheduler fixtures. |
| I19 | P2 | Devices and multicore platform. | MMIO devices, IPI/interrupt controller model, DMA driver protocol, and multicore integration tests. |
| I20 | P1 | RTL readiness and golden corpus. | Golden trace corpus, differential harness, CI artifacts, and RTL handoff gap report. |

## First Vertical Slice

The first vertical slice is a single-core semantic simulator that can reset into a ROM-like state, execute a hand-authored decoded program, take a trap, and return with `IRET`.

Minimum included stories:

- I01-S01 through I01-S03.
- I02-S01 through I02-S05.
- I03-S01 through I03-S03.
- I04-S01 through I04-S03.

Explicitly excluded from the first slice:

- Final binary opcode decoding.
- Page translation.
- Caches and DMA.
- Multicore execution.
- Protected return-stack calls beyond enough state to avoid accidental conflicts.
- Real firmware image loading.

## Story Table

| Story | Priority | Size | Dependencies | Summary | Acceptance evidence |
| --- | --- | --- | --- | --- | --- |
| I01-S01 | P0 | S | E15-S07 | Create the implementation repository skeleton and package/test layout. | Package imports, test runner executes, README files identify ownership. |
| I01-S02 | P0 | S | I01-S01 | Establish local test commands and baseline CI-style checks. | Commands for unit tests, spec checks, and lint/format check are documented and runnable locally. |
| I01-S03 | P0 | M | I01-S01 | Build a story-derived conformance test index. | Test index maps first implementation tests to owning spec stories and E15 matrices. |
| I02-S01 | P0 | M | I01-S01, E01-S01 | Implement 24-bit cell and 48-bit address helpers. | Cell value masking, address bounds, alignment, range, and object-size tests pass. |
| I02-S02 | P0 | M | I02-S01, E03-S01 | Implement capability payload, tag, and permission data types. | Capability field width, tag copy, invalid-tag, permission mask, and object-type tests pass. |
| I02-S03 | P0 | M | I02-S01, E03-S04 | Implement memory cells and capability-slot tag storage. | `LD48`/`ST48` object access, `CLC`/`CSC` slot access, and integer-store tag-clear tests pass. |
| I02-S04 | P0 | M | I02-S02, E01-S02, E01-S03, E01-S04 | Implement architectural core state. | `D0-D15`, `C0-C7`, special capabilities, `PCC.slot`, `EPCC.slot`, and per-core fields are represented. |
| I02-S05 | P0 | M | I02-S04, E02-S02, E02-S05, E11-S01, E11-S02 | Implement reset state and CSR/CCSR storage. | Boot-core reset, invalid capability tags, fast CSR reset values, and CCSR copy tests pass. |
| I03-S01 | P0 | M | I02-S05, E04-S01 | Define decoded instruction representation and execution result protocol. | Decoded instruction objects can report normal retire, fault packet, debug event, or control redirect. |
| I03-S02 | P0 | M | I03-S01, E04-S02 | Implement baseline integer operations. | Arithmetic, compare/test, condition-code, width, sign/zero extension, and divide-by-zero tests pass. |
| I03-S03 | P0 | M | I03-S01, I02-S02, E04-S05 | Implement first capability derivation operations. | `CMOVE`, `CGETADDR`, `CSETADDR`, `CINCADDR`, `CANDPERM`, invalid-tag, sealed-source, and bounds tests pass. |
| I03-S04 | P0 | M | I02-S03, I03-S01, E04-S03, E09-S07 | Implement `LD48`, `ST48`, `CLC`, and `CSC` without translation. | Alignment, bounds, permission, tag propagation, local-store, protected-storage, and no-side-effect tests pass. |
| I04-S01 | P0 | M | I03-S01, E01-S05, E04-S01 | Implement fetch placement and hidden slot sequencing for decoded programs. | 12-bit slot fall-through, 24/48-bit placement, explicit slot-0 target, and slot fault tests pass. |
| I04-S02 | P0 | M | I02-S05, I03-S01, E07-S02, E07-S04 | Implement fault packets and direct trap entry. | `CAUSE`, `TVAL`, `CAPCAUSE`, `FAULTCAPIDX`, `EPCC`, `SR`, `PCC=TVC`, and invalid-`TVC` failure tests pass. |
| I04-S03 | P0 | M | I04-S02, E04-S04, E07-S06 | Implement `IRET`, `EPCCRD`, and `EPCCWR`. | Slot-aware trap-frame save/restore, `IRET` privilege, `EPCC` capability checks, and post-`IRET` interrupt boundary tests pass. |
| I04-S04 | P0 | M | I04-S02, E12-S01, E12-S03 | Implement non-monitor debug halt and single-step baseline. | `BRKHALT`, halt/resume, `DCAUSE`, counter suppression, and one-instruction step tests pass. |
| I05-S01 | P0 | M | I03-S04, I04-S01, E06-S03, E06-S04 | Implement direct `CALL` and protected return-stack push. | Sealed local return capability, protected slot tag write, `RSC.cursor`, and atomic commit tests pass. |
| I05-S02 | P0 | M | I05-S01, E06-S02 | Implement `CALLC`. | Sealed entry validation, source preservation, protected push, slot-0 target, and invalid-entry tests pass. |
| I05-S03 | P0 | M | I05-S01, E06-S03, E06-S04 | Implement `RET` and protected pop. | Return-slot validation, underflow, wrong type, invalid tag, `RSC.cursor`, `PCC`, and no-partial-state tests pass. |
| I06-S01 | P1 | L | I03-S04, E09-S02, E09-S05, E09-S07 | Implement `RADIX4` translation and page permissions. | PTE walk, page fault, privilege, permission, memory type, and bare-mode tests pass. |
| I06-S02 | P1 | M | I06-S01, E09-S03, E08-S04 | Implement TLBs and `SFENCE.VM` forms. | Local TLB hit/miss, cached failure invalidation, ASID/global behavior, and fence tests pass. |
| I06-S03 | P1 | M | I03-S04, E08-S01, E08-S02 | Implement `LL48`/`SC48` reservations. | Success, failure, faulting `LL48` clear, trap-entry clear, conflict clear, and spurious failure tests pass. |
| I06-S04 | P1 | L | I06-S01, I06-S03, E08-S03, E10-S03, E10-S05 | Implement architectural memory ordering and cache/DMA litmus model. | `tools/memory_consistency_litmus.md` scenarios are executable and passing where in scope. |
| I07-S01 | P0 | L | I03-S01, E04-S06 | Allocate final opcode table for mandatory v0.1 instructions. | Every mandatory mnemonic has a canonical encoding or synonym; excluded instructions are absent. |
| I07-S02 | P0 | M | I07-S01 | Implement assembler and disassembler for binary fixtures. | Round-trip source/binary/source tests and illegal-encoding tests pass. |
| I07-S03 | P0 | M | I07-S02, E01-S01, E14-S02 | Define byte-oriented 24-bit cell serialization and section payload profile. | Little-endian 3-octet cells, page/cache-line byte sizes, cell-addressed section metadata, and assembler fixture serialization tests pass. |
| I08-S01 | P0 | M | I02-S05, E11-S01, E11-S02 | Define minimal test platform profile. | Reset vector, memory map, ROM/RAM/device regions, fatal entry behavior, and debug policy are documented. |
| I08-S02 | P0 | M | I08-S01, E11-S03 | Implement secondary-core startup platform binding. | Mailbox publish, start signal, valid startup, invalid startup, and already-started cases pass. |
| I09-S01 | P1 | M | I04-S03, E07-S06, E15-S06 | Define trap-frame and context-switch ABI supplement. | Nested trap frame, `EPCC.slot`, general register save set, special capability save set, and return tests are specified. |
| I09-S02 | P1 | M | I09-S01, E05-S01, E05-S02, E15-S06 | Define language ABI argument, return, overflow, and spill profile. | Register windows, mixed overflow stack layout, public stack alignment, and capability spill rules have executable tests. |
| I09-S03 | P1 | M | I09-S02, E04-S04, E05-S01, E05-S02 | Define baseline syscall ABI policy. | `SYS`/`SCALL` spelling, service number, syscall argument windows, overflow layout, returns, and volatility have executable tests. |
| I09-S04 | P1 | M | I09-S01, I09-S03, E05-S04, E12-S01, E12-S03 | Define debugger register access and protected unwind profile. | Halted-core register inventory, tag/slot visibility, direct-access lifecycle rule, and return-stack unwind operations have executable tests. |
| I10-S01 | P1 | L | I01-I07 | Produce RTL handoff checklist from simulator results. | RTL commit points, decoder table, fault packet interface, tag path, and conformance hooks are documented. |
| I11-S01 | P0 | M | I07-S03, I08-S01 | Define simulator program-image manifest and loader boundaries. | Image sections, entry capability source, RAM/ROM placement, tag-bearing data policy, and invalid-image failures are documented and tested. |
| I11-S02 | P0 | M | I11-S01, I02-S03 | Implement serialized 24-bit cell image loading into simulator memory. | Little-endian cells load into ROM/RAM regions, capability tags remain explicit, protected regions reject ordinary image writes, and bad alignment fails. |
| I11-S03 | P0 | L | I11-S02, I04-S03, I07-S02 | Execute a serialized reset-to-trap smoke program. | A binary fixture resets through the test platform, executes integer/load/store/control flow, takes a trap, and returns with `IRET`. |
| I12-S01 | P0 | S | I01-S02, I01-S03 | Add one-command full local check runner. | Spec checks, conformance tests, litmus tests, and whitespace checks run through one documented command. |
| I12-S02 | P0 | M | I01-S03 | Generate a story coverage report from tests and docs. | Current implementation story rows report indexed tests, missing tests, and intentionally documentation-only stories. |
| I12-S03 | P1 | M | I12-S02 | Add drift checks for story IDs, test names, and implementation docs. | New test files without index rows, stale index rows, and unowned implementation docs fail the local check. |
| I13-S01 | P1 | L | I10-S01, E13-S01 | Implement a single-issue pipeline trace model. | FE0 through RT stages emit deterministic traces for straight-line, branch, trap, and load/store programs. |
| I13-S02 | P1 | L | I13-S01, I03-S01 | Compare cycle-level retire packets against semantic execution. | Matching programs produce identical committed architectural state, fault packets, debug events, and redirects. |
| I13-S03 | P1 | M | I13-S02, E13-S02, E13-S03, E13-S04 | Model first hazard, MDU, and predictor cases. | Load-use interlock, busy destination, branch flush, return-stack prediction, and context flush cases match the semantic contract. |
| I14-S01 | P1 | M | I11-S03, I08-S01 | Build a tiny ROM initialization sequence. | ROM sets initial capabilities, validates platform profile assumptions, and reaches a kernel handoff point in simulation. |
| I14-S02 | P1 | L | I14-S01, I09-S01, I09-S03 | Add minimal trap, syscall, and timer handler fixtures. | Trap frames, syscall arguments, timer interrupt dispatch, and `IRET` paths run as executable firmware/kernel examples. |
| I14-S03 | P1 | L | I14-S02, I08-S02 | Demonstrate secondary-core startup under firmware control. | Core 0 publishes a mailbox, starts a secondary core, observes `STARTED`, and rejects invalid or repeated startup attempts. |
| I15-S01 | P1 | M | I03-S03, E03-S03 | Add property-style capability monotonicity tests. | Derivation, bounds, permissions, sealing, and unsealing cannot widen authority or synthesize valid tags. |
| I15-S02 | P1 | M | I02-S03, I03-S04, E03-S04 | Add property-style tag integrity tests. | Integer stores, serialization, DMA, cache movement, CCSR copies, and debug observation cannot forge capability tags. |
| I15-S03 | P1 | L | I04-S02, I06-S01, E15-S04 | Add precise-fault and no-side-effect property tests. | Fault-priority cases suppress partial register, memory, tag, reservation, TLB, and protected-stack effects. |
| I16-S01 | P1 | M | I15-S01, I15-S02, I15-S03, E15-S01 | Define the invariant registry and coverage matrix. | Registry entries map invariant keys to implementation stories, architecture owners, E15 coverage, artifacts, and checked surfaces. |
| I16-S02 | P1 | M | I16-S01, I03-S03, E03-S03 | Add reusable deterministic capability property generators. | Shared generators cover authority-preserving and authority-reducing capability cases without broadening tags, bounds, or permissions. |
| I16-S03 | P1 | L | I16-S01, I06-S01, I15-S03, E15-S04 | Add a seed-stable invariant runner. | A repeatable runner executes selected invariant families, records seed/case IDs, and reproduces failures from the command line. |

## Near-term Sprint Plan

### Sprint A: Skeleton and data model

Target stories:

- I01-S01
- I01-S02
- I02-S01
- I02-S02
- I02-S03

Outcome:

- Importable simulator package.
- Cell/address helpers.
- Capability data type.
- Memory plus capability tags.
- First tests for tag integrity and alignment.

### Sprint B: Core state and basic execution

Target stories:

- I02-S04
- I02-S05
- I03-S01
- I03-S02
- I03-S03

Outcome:

- Resettable core model.
- CSR/CCSR storage.
- Decoded instruction executor.
- Integer and first capability operations.

### Sprint C: Memory, traps, and first runnable program

Target stories:

- I03-S04
- I04-S01
- I04-S02
- I04-S03

Outcome:

- Load/store capability behavior.
- Slot-aware execution.
- Direct trap entry and `IRET`.
- First decoded program that resets, executes, traps, and returns.

## Definition of Ready for Starting Code

Code can start when:

- `spec/v0.1-implementation-checklist.md` is committed.
- This implementation backlog is committed.
- The first implementation story has an explicit test target.
- The worktree is clean.

For I01-S01, that condition is met once this backlog is committed.

## Definition of Done for Implementation Stories

Every implementation story should leave:

- Focused code changes in the owned module or package.
- Tests tied to the owning architecture story or E15 matrix.
- A short note in the story status or commit message when behavior is intentionally partial.
- No silent architecture changes.
- Passing local checks relevant to the touched layer.

Minimum local checks before each implementation commit:

```text
python tools\spec_reference_check.py
python tools\spec_constants_model.py
python -m unittest discover -s tests/conformance -p "test_*.py"
python -m unittest discover -s tests/litmus -p "test_*.py"
git diff --check
```

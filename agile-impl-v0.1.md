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
| I19 | P2 | External endpoints and multicore platform boundary. | CPU endpoint/fabric attachment profile, event/IPI routing, external-agent transfer protocol, and point-to-point fabric litmus tests. |
| I20 | P1 | RTL readiness and first SystemVerilog slice. | First-slice contract, golden retire corpus, SV package/interface plan, Verilator harness, and first single-core RTL gates. |
| I21 | P1 | Single-core RTL semantic closure. | Expand the first RTL slice to mandatory single-core instruction, trap, MMU, atomic, and differential-gate coverage. |
| I22 | P1 | Integrated single-core RTL core. | Replace fixture-only RTL slices with a real `cpu_v01_core` top level that runs golden programs through fetch, decode, execute, memory, trap, and retire paths. |
| I23 | P1 | FPGA first-test bring-up. | Wrap the integrated single-core RTL for a first FPGA smoke test with BRAM-backed memories, a tiny visible pass/fail program, synthesis constraints, and board bring-up evidence. |
| I24 | P1 | Tang Mega 138K physical build bring-up. | Verified device/package, CST/SDC overlay, Gowin reports, bitstream, SRAM programming log, and first board pass/fail/heartbeat evidence. |
| I25 | P1 | FPGA debug and observability. | UART or GAO/ILA status path for retire count, fault code, PC/slot, reset state, and replayable failure evidence. |
| I26 | P1 | Loadable FPGA program images. | Repeatable FPGA ROM/RAM/tag image generation and a board-safe path to run more than one smoke program. |
| I27 | P1 | Minimal FPGA SoC shell. | UART, timer, GPIO/status, simple MMIO map, interrupt path, and firmware-visible platform profile around the CPU. |
| I28 | P1 | FPGA timing and reset hardening. | Clock/PLL profiles, reset/CDC audit, automated timing-report parser, and conservative debug/release build gates. |
| I29 | P2 | External memory bring-up. | DDR/external-memory boundary, calibration visibility, memory-test firmware, and cache/tag policy evidence for off-BRAM execution. |

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
| I17-S01 | P1 | M | I07-S02, I07-S03, I11-S01, E14-S02, E15-S06 | Define relocatable object and symbol metadata profile. | Object metadata distinguishes cell-addressed text, data, and capability-data sections, slot-aware symbols, capability sidecar provenance, ABI attributes, and deterministic validation errors. |
| I17-S02 | P1 | L | I17-S01, I07-S02, I11-S02, E04-S01, E04-S06 | Implement linker relocation fixtures. | Assembler/linker fixtures resolve cell and slot labels, section placement, branch/call/data relocations, alignment constraints, duplicate or undefined symbols, and relocation overflow failures. |
| I17-S03 | P1 | M | I17-S01, I09-S04, I12-S01, E12-S01, E15-S06 | Emit debug line, symbol, and register metadata. | Debug metadata maps `PCC` cell plus slot to source lines, functions, ABI registers, capability tag visibility, and protected return-stack unwind hints; disassembly prints matching symbolic locations. |
| I17-S04 | P1 | L | I17-S02, I17-S03, I11-S03, I14-S02 | Publish executable toolchain regression corpus. | Golden object and binary fixtures cover reset smoke, call/return, syscall/trap, capability memory, relocation, debug metadata, and bad-object cases through the local check command. |
| I18-S01 | P1 | L | I11-S03, I14-S02, I09-S03, I06-S01, E07-S01 | Build user process image and entry-context fixture. | Kernel fixture installs user `PCC`, `DSC`, `RSC`, `SATP`, ABI arguments, and privilege state, enters user mode, and rejects invalid image or context setup without partial state. |
| I18-S02 | P1 | L | I18-S01, I06-S01, I06-S02, E09-S07 | Add VM allocation and page-mapping fixtures. | Map, unmap, permission, ASID/TLB invalidation, memory-type, and capability/page fault-priority cases run as executable kernel fixtures. |
| I18-S03 | P1 | M | I18-S01, I09-S03, I14-S02, E04-S04 | Implement syscall demo across the user/kernel boundary. | User `SYS` preserves trap-frame state, validates service numbers and arguments, returns scalar and capability results, and rejects bad user pointers or invalid tags. |
| I18-S04 | P1 | L | I18-S02, I18-S03, I06-S03, E07-S05, E07-S06 | Add minimal scheduler and context-switch fixtures. | Timer preemption switches two runnable tasks, saves and restores ABI and trap context including capabilities, tags, `SATP`, and `ASID`, clears LL/SC reservations, and resumes with `IRET`. |
| I19-S01 | P2 | M | I08-S01, I06-S04, E09-S06, E10-S05 | Define CPU external endpoint and fabric attachment boundary. | CPU-side profile separates abstract endpoint windows, link events, external interrupt ingress, noncoherent external-agent memory effects, and tag-clearing rules from the out-of-repo computer architecture topology. |
| I19-S02 | P2 | L | I14-S03, I18-S04, I19-S01, E07-S05, E11-S03 | Implement endpoint event, IPI, and interrupt routing fixtures. | Timer, software IPI, fabric-delivered external events, pending/enable/priority, delivery, and acknowledgement paths run across boot and secondary cores without assuming a shared bus. |
| I19-S03 | P2 | L | I19-S01, I18-S02, I06-S04, I15-S02, E10-S04 | Add noncoherent external-agent transfer and cache-maintenance fixtures. | External-agent read/write fixtures enforce ownership handoff, fences, cache clean/invalidate ordering, memory-type policy, and capability tag clear/non-forgery behavior. |
| I19-S04 | P2 | XL | I19-S02, I19-S03, I06-S04, E08-S03, E10-S03 | Add point-to-point fabric integration litmus suite. | Four-core startup, fabric event delivery, shared-memory, LL/SC contention, coherence/tag visibility, and external-agent ordering litmus cases run deterministically. |
| I20-S01 | P1 | M | I10-S01, I13-S01, I13-S03, E13-S01 | Define the first RTL slice and microarchitecture contract. | A document fixes first-slice inclusions/exclusions, pipeline boundaries, stall/flush rules, commit packet timing, memory/tag assumptions, and unsupported-feature behavior. |
| I20-S02 | P1 | L | I13-S02, I16-S03, E07-S03, E13-S01 | Generate a semantic golden retire trace corpus. | Deterministic fixtures cover reset smoke, integer ops, capability derivation, memory/tag ops, traps, calls/returns, and selected fault cases with machine-readable expected retire packets. |
| I20-S03 | P1 | L | I07-S01, I10-S01, I20-S01, E04-S06 | Define SystemVerilog package, constants, and top-level interfaces. | SV package/type artifacts or generated specs cover cells, capabilities, tags, CSRs, decoded opcodes, fault packets, retire packets, instruction memory, data memory, and tag-memory ports. |
| I20-S04 | P1 | L | I20-S02, I20-S03 | Add a Verilator differential harness skeleton. | A harness builds or dry-runs the RTL/testbench boundary, feeds golden fixtures, captures retire traces, reports first mismatch by case ID, and skips cleanly when Verilator is unavailable. |
| I20-S05 | P1 | L | I20-S01, I20-S03, I20-S04 | Implement the first single-core SystemVerilog smoke slice. | The RTL retires a tiny straight-line reset program with integer register writes, slot-0 sequencing, legal placement checks, and retire-trace comparison against the golden corpus. |
| I20-S06 | P1 | XL | I20-S05, I02-S02, I02-S03, I03-S03, I03-S04 | Add capability register and memory/tag RTL behavior. | RTL passes golden cases for capability payload/tag registers, `CMOVE`, `CGETADDR`, `CSETADDR`, `CANDPERM`, `LD48`, `ST48`, `CLC`, `CSC`, tag clears, and invalid-tag faults. |
| I20-S07 | P1 | L | I20-S06, I04-S02, I04-S03, I05-S01 | Add precise fault, trap, and protected-stack RTL gates. | RTL passes golden cases for fault packets, no-normal-effect faults, direct trap entry, `IRET`, direct `CALL`, protected return-stack push, and all-or-nothing commit behavior. |
| I20-S08 | P1 | M | I20-S04, I20-S07, E15-S07 | Publish RTL readiness gap report and CI command. | A report lists implemented RTL surface, known deferrals, unsupported instructions/interfaces, golden corpus coverage, and the local command that gates future RTL commits. |
| I21-S01 | P1 | L | I20-S07, I20-S08, I07-S01, I20-S02 | Expand RTL scalar, branch, CSR, and CCSR instruction coverage. | Verilator/golden cases pass for remaining mandatory integer, branch, CSR, CCSR, `EPCCRD`, `EPCCWR`, `PAUSE`, and `BRK` forms that do not require MMU, atomics, or cache maintenance. |
| I21-S02 | P1 | XL | I21-S01, I06-S01, I06-S02, I18-S02, E09-S02, E09-S07 | Add RTL `RADIX4` page walk, TLB, `SATP`, ASID, and page-fault behavior. | RTL passes golden VM fixtures for bare mode, page walks, permission faults, memory-type faults, stale TLB behavior, and `SFENCE.VM*` invalidation effects. |
| I21-S03 | P1 | L | I21-S02, I06-S03, I06-S04, E08-S01, E08-S02 | Add RTL `LL48`/`SC48`, reservation, fence, and cache-maintenance architectural effects. | RTL passes golden and litmus-derived cases for LL/SC success/failure, conflict clears, trap/CSR/fence reservation clears, `FENCE`, `FENCE.I`, and `CACHE.*` access checks. |
| I21-S04 | P1 | XL | I21-S01, I21-S02, I20-S07, I14-S02, I18-S03 | Expand RTL control-transfer and trap coverage to syscall and protected call/return paths. | RTL passes golden cases for `CALLC`, `RET`, protected return-stack pop faults, `SYS`/`SCALL`, syscall trap-frame save/restore, and `IRET` back to user mode. |
| I21-S05 | P1 | L | I21-S01, I21-S02, I21-S03, I21-S04, I20-S04, I17-S04 | Promote the Verilator differential harness to a regression-suite gate. | The harness runs generated golden/toolchain cases by case ID, partitions slow and fast suites, emits first-mismatch diagnostics, and preserves clean skip behavior when Verilator is unavailable. |
| I21-S06 | P1 | M | I21-S05, I16-S01, I20-S08, E15-S07 | Publish single-core RTL semantic closure report. | A report maps mandatory v0.1 instruction families, golden cases, invariants, unsupported deferrals, and local gate commands, with explicit readiness criteria for starting multicore/fabric RTL. |
| I22-S01 | P1 | L | I21-S06, I20-S03, I20-S04, E13-S01 | Define and instantiate the integrated `cpu_v01_core` top-level shell. | `cpu_v01_core` exposes stable clock/reset, instruction memory, data memory, tag-memory, interrupt/event, retire, and debug-observation ports; reset state, stall/flush, and unsupported external-interface behavior are documented and lint/build clean. |
| I22-S02 | P1 | L | I22-S01, I07-S01, I20-S02, I21-S01, E01-S05, E04-S01 | Integrate instruction fetch, slot sequencing, and 12/24/48-bit decode. | The core fetches from instruction memory, enforces slot placement and explicit slot-0 targets, decodes mandatory scalar/control encodings used by the golden corpus, and reports precise placement or illegal-instruction faults. |
| I22-S03 | P1 | XL | I22-S02, I21-S01, E02-S04, E02-S05, E04-S02, E04-S04 | Integrate scalar, branch, CSR, CCSR, and retire execution. | Golden scalar/control programs retire through the top-level pipeline with correct register/CSR/CCSR writes, condition codes, branches, redirects, `EPCCRD`/`EPCCWR`, `BRK`, `PAUSE`, no-effect faults, and first-mismatch diagnostics. |
| I22-S04 | P1 | XL | I22-S03, I20-S06, I03-S04, I21-S06, E03-S04, E04-S03, E04-S05 | Integrate capability registers plus data and tag-memory operations. | Top-level golden cases pass for capability derivation, capability payload/tag registers, `LD48`, `ST48`, `CLC`, `CSC`, tag clears, local/protected-storage checks, and invalid-tag or bounds faults without partial architectural effects. |
| I22-S05 | P1 | XL | I22-S04, I21-S04, I14-S02, I18-S03, E06-S02, E06-S04, E07-S04, E07-S06 | Integrate trap, syscall, protected call, and return paths. | The core passes top-level cases for direct trap entry, `IRET`, `CALL`, `CALLC`, protected return-stack push/pop, `RET` faults, `SYS`/`SCALL`, syscall frame save/restore, privilege transitions, and trap-priority ordering. |
| I22-S06 | P1 | XL | I22-S05, I21-S02, I18-S02, E09-S02, E09-S03, E09-S07 | Integrate MMU, TLB, SATP/ASID, page-walk, and translation faults. | Instruction and data accesses use the integrated translation path; golden VM fixtures cover bare mode, page walks, permission and memory-type faults, stale TLB behavior, ASID/global matching, and all `SFENCE.VM*` invalidation forms. |
| I22-S07 | P1 | L | I22-S06, I21-S03, I06-S04, E08-S01, E08-S02, E08-S04, E10-S05 | Integrate LL/SC, reservation, fence, and cache-maintenance effects. | Top-level cases and litmus projections pass for `LL48`/`SC48`, conflict and trap clears, spurious failure allowance, `FENCE`, `FENCE.I`, `CACHE.*` access checks, and ordering-visible retire boundaries. |
| I22-S08 | P1 | L | I22-S01, I22-S02, I22-S03, I22-S04, I22-S05, I22-S06, I22-S07, I21-S05, I17-S04 | Promote integrated `cpu_v01_core` simulation to the RTL regression gate. | Fast and slow Verilator suites run against `cpu_v01_core`, selected golden/toolchain cases move from slice projection to observed top-level retire traces, remaining deferrals are explicit, and the local gate fails on integrated-core mismatches. |
| I23-S01 | P1 | M | I22-S08, I20-S03, I08-S01, I14-S01 | Define the FPGA first-test boundary and target profile. | A bring-up profile names target board assumptions, clock/reset, ROM/RAM/tag BRAM map, image format, debug/status outputs, synthesis flow, and explicit non-goals. |
| I23-S02 | P1 | L | I23-S01, I22-S01, I22-S08, I20-S03 | Add a board-neutral `cpu_v01_fpga_top` wrapper. | An FPGA top wrapper instantiates `cpu_v01_core`, synchronizes reset, exposes clock/reset/status/debug pins, drives idle interrupts/events, and elaborates without black-box CPU-owned ports. |
| I23-S03 | P1 | L | I23-S02, I11-S02, I14-S01, I22-S04 | Implement FPGA ROM, RAM, and tag-memory adapters. | BRAM-friendly instruction ROM, data RAM, and tag RAM adapters satisfy core handshakes, load a tiny initialized image, and clear tag state on integer stores. |
| I23-S04 | P1 | M | I23-S03, I14-S01, I17-S04, I22-S03 | Build first FPGA smoke firmware and observation signals. | A tiny firmware case retires deterministic instructions, reaches a pass/fail status visible on LED/UART/ILA probes, and exposes retire/fault heartbeat signals. |
| I23-S05 | P1 | L | I23-S04, I20-S04, I22-S08, E13-S01 | Add synthesis, implementation, and timing gates for the first-test design. | A scripted FPGA synth/place/route flow builds the first-test design, reports utilization/timing, and fails on unconstrained clocks/resets or black boxes. |
| I23-S06 | P1 | M | I23-S05, E11-S01, E12-S01, E15-S07 | Document and execute the first board bring-up procedure. | The bring-up runbook covers programming, reset, expected observations, triage steps, and captured first-pass evidence from the board or documented blocker. |
| I24-S01 | P1 | M | I23-S06, E15-S07 | Verify the physical Tang Mega 138K device, package, and toolchain target. | Board marking or programmer/JTAG scan records the actual FPGA device, package, and device version; target docs and build settings are updated if the board is not the assumed `GW5AST-LV138PG484A`/`PBG484A`. |
| I24-S02 | P1 | L | I24-S01, I23-S05 | Create the verified Tang Mega 138K first-test CST/SDC overlay. | Constraints map `board_clk_i`, `board_reset_n_i`, `pass_led_o`, `fail_led_o`, `heartbeat_led_o`, IO standards, LED polarity, and clock period from verified board data. |
| I24-S03 | P1 | L | I24-S02, I23-S05 | Run Gowin synthesis, place-route, bitstream, and report audit for the first-test design. | Timing, utilization, port assignment, synthesis, and `.fs` bitstream artifacts are captured; the audit fails on black boxes, unconstrained paths, negative slack, or missing status pins. |
| I24-S04 | P1 | M | I24-S03, I23-S06 | Program SRAM and capture first pass/fail/heartbeat board evidence. | Programming log, reset observation, LED or probe capture, and pass/fail/heartbeat result are recorded with the exact bitstream and board identity. |
| I24-S05 | P1 | M | I24-S04 | Archive first-board evidence and close or file bring-up blockers. | A first-board evidence note links the scan, reports, bitstream, programming log, observation capture, and any residual defects or retest steps. |
| I25-S01 | P1 | M | I23-S04, I24-S04, E12-S01 | Define a compact FPGA debug/status packet. | Status fields cover reset state, PC/slot, retire count, fault code, trap cause, pass/fail state, and build identity without changing architectural retire behavior. |
| I25-S02 | P1 | L | I25-S01, I24-S04, I23-S02 | Add a UART status streamer for board bring-up. | The FPGA top can stream status packets over UART at a documented baud rate; simulation and board procedures show expected idle, pass, and fault packets. |
| I25-S03 | P1 | M | I25-S01, I24-S02 | Add optional GAO/ILA probe bundles for first-failure capture. | Probe definitions expose clock/reset, PC/slot, retire count, fault code, pass/fail/heartbeat, and key memory handshakes without perturbing the release build. |
| I25-S04 | P1 | M | I25-S02, I22-S08, I23-S06 | Map board failure captures back to Verilator replay cases. | A captured fault/status record can select the nearest `core.*` or golden case, print replay commands, and preserve first-mismatch diagnostics. |
| I25-S05 | P1 | M | I25-S02, I25-S03, I24-S05 | Add a debug-evidence gate to the FPGA bring-up runbook. | The runbook requires UART or ILA evidence for nontrivial failures and distinguishes clock/reset failures from firmware, memory, trap, and translation failures. |
| I26-S01 | P1 | M | I17-S04, I23-S03 | Define the FPGA program-image manifest. | Manifest entries bind assembler/linker fixtures to instruction ROM, data RAM, tag RAM, entry capability, image hash, and expected board observations. |
| I26-S02 | P1 | L | I26-S01, I23-S04 | Generate FPGA BRAM initialization images from toolchain fixtures. | ROM/RAM/tag `.mem` artifacts are produced deterministically from selected fixtures and checked against simulator-visible expected cells and tags. |
| I26-S03 | P1 | M | I26-S02, I24-S03 | Document and automate the bitstream rebuild or memory-update path for changed programs. | The flow names which artifacts require Gowin rebuild, which can be updated in-place if supported, and how image identity is recorded in reports and board evidence. |
| I26-S04 | P1 | L | I25-S02, I27-S02 | Add a board-safe UART or JTAG-assisted program load path. | A loader can install a bounded RAM image, reject malformed images, preserve tag policy, and report success/failure over the debug/status path. |
| I26-S05 | P1 | M | I26-S02, I25-S04 | Publish an FPGA smoke-program corpus. | Multiple small programs cover reset pass, scalar/control, capability memory, trap/syscall, translation fault, and failure-path observations with expected UART/LED/probe signatures. |
| I27-S01 | P1 | M | I23-S01, I24-S05, E11-S01 | Define the minimal FPGA SoC platform profile and MMIO map. | The platform profile assigns UART, timer, GPIO/status, interrupt pending/enable, reset cause, and image identity registers without conflicting with existing memory regions. |
| I27-S02 | P1 | L | I27-S01, I25-S01 | Integrate a simple UART TX/RX MMIO peripheral. | Firmware can transmit status text/packets and optionally receive bounded commands through documented MMIO registers with simulation and FPGA wrapper checks. |
| I27-S03 | P1 | L | I27-S01, I14-S02, I22-S05 | Add a timer and interrupt source for FPGA firmware. | The timer can raise an interrupt, be acknowledged by firmware, and produce visible or UART-confirmed handler progress without breaking first-test pass/fail behavior. |
| I27-S04 | P1 | M | I27-S01, I23-S04 | Add GPIO/status MMIO registers for LEDs, reset cause, and board diagnostics. | Firmware-visible registers drive pass/fail/heartbeat/status outputs and expose reset/build diagnostics for the bring-up runbook. |
| I27-S05 | P1 | L | I27-S02, I27-S03, I27-S04, I18-S03 | Run a minimal firmware/kernel smoke on the FPGA SoC shell. | A board or documented-blocker run shows UART output, timer interrupt handling, syscall/trap path progress, and GPIO pass/fail evidence. |
| I28-S01 | P1 | M | I24-S03 | Define clock, PLL, and build-frequency profiles for the FPGA target. | Debug and release clock profiles name source clocks, PLL settings, generated clocks, SDC constraints, and expected timing margins. |
| I28-S02 | P1 | L | I28-S01, I23-S02 | Audit reset and clock-domain crossings in the FPGA wrapper and debug paths. | Async inputs, reset synchronizers, UART/debug crossings, and generated-clock domains are documented and checked by focused RTL or lint assertions. |
| I28-S03 | P1 | L | I24-S03, I28-S01 | Implement an automated Gowin timing/report parser. | The parser extracts slack, utilization, unconstrained paths, ports, warnings, bitstream identity, and clock summary; CI-style checks fail on policy violations. |
| I28-S04 | P1 | M | I28-S03 | Track maximum passing first-test clock and select conservative board defaults. | Frequency sweep results or documented blockers identify the highest passing build and the lower default clock used for bring-up and debug. |
| I28-S05 | P1 | M | I28-S02, I28-S03 | Publish a reproducible FPGA build profile. | Tool version, device/package, constraints, Tcl, reports, bitstream hash, and board evidence are captured so another machine can reproduce the build. |
| I29-S01 | P2 | M | I27-S01, E10-S03, E10-S05 | Define the external-memory attachment and DDR bring-up boundary. | The profile separates DDR controller signals, calibration status, memory window, cacheability, tag policy, and CPU-owned fault behavior from board-specific IP details. |
| I29-S02 | P2 | XL | I29-S01, I28-S02 | Integrate the DDR controller wrapper and calibration visibility. | The FPGA shell exposes calibration done/error state, gates CPU access until ready, and fails visibly or through UART when calibration does not complete. |
| I29-S03 | P2 | L | I29-S02, I26-S05 | Add external-memory test firmware. | Walking pattern, address-line, burst, alignment, and fault-injection tests run from BRAM while exercising DDR as data memory and reporting progress over debug/status output. |
| I29-S04 | P2 | L | I29-S02, I06-S04, I15-S02 | Define cache, ordering, and capability-tag policy for external memory. | Litmus and firmware fixtures prove the selected memory type, cache-maintenance requirements, and tag-clearing/non-forgery behavior for off-BRAM accesses. |
| I29-S05 | P2 | XL | I29-S03, I29-S04, I28-S05 | Capture first external-memory FPGA evidence. | Board evidence shows DDR calibration, memory-test pass/fail, timing reports, debug/status output, and any remaining external-memory blockers. |

## RTL Readiness Slice

The first SystemVerilog implementation should not start by attempting the full CPU. The intended I20 sequence is:

1. Define a narrow single-core RTL slice and interfaces.
2. Generate semantic golden retire traces.
3. Create SV package/interface contracts and a differential harness.
4. Implement a tiny straight-line RTL smoke slice.
5. Expand into capability, memory/tag, fault, trap, and protected-stack behavior.

Initial RTL exclusions:

- Multicore execution.
- L1/L2 caches and noncoherent DMA.
- Full `RADIX4` page walking and TLBs.
- Interrupt controller/MMIO device model.
- Branch predictor performance behavior.
- Firmware/kernel boot beyond fixtures needed by the golden corpus.

These exclusions must remain visible in the I20-S08 gap report until implemented by later stories.

## Post-I20 Story Refinement

I17 turns the current assembler, serialization, and program-image pieces into a
toolchain pipeline. The order is object metadata, relocation/linking, debug
metadata, then a regression corpus that can be used by firmware and kernel
stories.

I18 uses the existing ROM, trap, syscall, MMU, and ABI fixtures to model a
minimal user process. The order is user entry context, VM mapping, syscall
round-trip, then timer-driven scheduling and context switching.

I19 extends the platform beyond single-core fixtures without freezing the
computer interconnect in this CPU repository. The order is CPU endpoint/fabric
attachment boundary, event/IPI routing, external-agent cache-maintenance
protocol, then point-to-point fabric litmus integration.

I21 should follow I20 by closing the single-core RTL semantic gap before moving
to multicore RTL. The order is scalar/control coverage, MMU/TLB behavior,
atomics and maintenance effects, syscall/protected-control paths, differential
suite promotion, then a closure report that decides whether multicore/fabric
RTL is ready to start.

I22 should follow I21 by turning the proven fixture slices into one integrated
single-core `cpu_v01_core`. The order is top-level shell and interfaces, real
fetch/decode, scalar/control retire, capability and tag-memory integration,
trap/syscall/protected control flow, MMU/TLB integration, atomic and maintenance
effects, then promotion of the integrated core into the Verilator regression
gate. Multicore execution, fabric links, coherence, and external module
topology remain outside I22.

I23 should follow I22 by proving that the integrated single-core RTL can become
a physical FPGA smoke target. The order is target profile, board-neutral top
wrapper, BRAM-backed ROM/RAM/tag adapters, tiny firmware and visible
observation signals, synthesis/timing gate, then a board bring-up runbook with
captured evidence. Full SoC peripherals, multicore execution, fabric links,
cache hierarchy tuning, and long-running software workloads remain outside
I23.

I24 should follow I23 by removing the documented board blocker. The order is
physical device/package confirmation, verified CST/SDC overlay, Gowin
synthesis/place-route/report capture, SRAM programming with pass/fail evidence,
then an archived evidence bundle that closes or files every residual blocker.
It should avoid adding new peripherals; the goal is a trustworthy first board
pass of the existing I23 smoke design.

I25 should add observability before the FPGA target becomes more complex. The
order is compact status-packet definition, UART status streaming, optional
GAO/ILA probes, replay mapping back to Verilator cases, then a bring-up
evidence gate that makes board failures diagnosable. It should not depend on
DDR, a full SoC, or long-running firmware.

I26 should make FPGA software iteration repeatable. The order is an FPGA image
manifest, deterministic BRAM image generation from toolchain fixtures,
documented bitstream rebuild or memory-update flow, optional UART/JTAG-assisted
loading, then a small corpus of board smoke programs with expected
observations. It should preserve the existing architectural tag rules instead
of inventing a separate FPGA-only image format.

I27 should wrap the CPU in the smallest useful FPGA SoC shell after the first
board pass and debug path exist. The order is MMIO/platform profile, UART,
timer interrupt, GPIO/status registers, then a minimal firmware/kernel smoke.
It remains a single-core board platform; fabric links, DDR, and cache hierarchy
work stay outside I27.

I28 should harden the board build so later FPGA stories are repeatable. The
order is clock/PLL profiles, reset and CDC audit, automated Gowin report
parsing, frequency-margin tracking, then a reproducible build profile. It
should fail loudly on unconstrained paths, unsafe reset crossings, negative
slack, or mismatched bitstream/report evidence.

I29 should only start after BRAM execution, debug, and timing gates are stable.
The order is external-memory boundary definition, DDR controller/calibration
wrapper, memory-test firmware, cache/order/tag policy, then first external
memory board evidence. It is intentionally P2 because DDR failures are expensive
to debug without I24-I28 in place.

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

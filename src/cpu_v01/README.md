# cpu_v01 Source Package

This directory will hold the CPU v0.1 semantic simulator and implementation libraries.

The first implementation target is an internal decoded-instruction semantic model. Binary opcode decoding and assembler integration should be added after the semantic model has conformance coverage.

Current implementation story:

- I01-S01: package skeleton and import smoke test.
- I01-S02: local test commands and baseline CI-style checks.
- I01-S03: story-derived conformance and litmus test ownership index.
- I02-S01: 24-bit cell and 48-bit address helpers.
- I02-S02: capability payload, tag, permission, flag, and object-type data types.
- I02-S03: cell-addressed memory and capability-slot tag storage.
- I02-S04: architectural core-state containers for integer, general capability, and special capability registers.
- I02-S05: mandatory scalar CSR storage and cold-reset state helpers.
- I03-S01: decoded instruction representation and execution-result packets.
- I03-S02: baseline integer operation semantics and normal-result commit helper.
- I03-S03: first register-only capability derivation semantics.
- I03-S04: `LD48`, `ST48`, `CLC`, and `CSC` memory operation semantics without translation.
- I04-S01: decoded-program fetch placement and hidden slot fall-through sequencing.
- I04-S02: direct synchronous trap entry from precise fault packets.
- I04-S03: `IRET`, `EPCCRD`, and `EPCCWR` trap-return semantics.
- I04-S04: non-monitor debug halt, resume, and single-step baseline.
- I05-S01: direct `CALL` with protected return-stack push.
- I05-S02: `CALLC` sealed entry-capability calls.
- I05-S03: `RET` with protected return-stack pop.
- I06-S01: `RADIX4` translation and page-permission checks for memory operations.
- I06-S02: private TLBs and `SFENCE.VM` local invalidation forms.
- I06-S03: `LL48`/`SC48` reservations and store-conditional result semantics.
- I06-S04: executable TSO, cache-maintenance, and noncoherent-DMA litmus support.
- I07-S01: final mandatory opcode table with canonical mnemonics, synonyms, and exclusions.
- I07-S02: assembler/disassembler helpers for mandatory binary fixtures.
- I07-S03: little-endian 24-bit cell serialization helpers and section payload rules for byte-oriented host containers.
- I08-S01: minimal test-platform profile for reset, memory map, fatal-entry, and debug policy.
- I08-S02: secondary-core start mailbox and platform start-event binding.
- I09-S01: trap-frame layout and context-switch ABI supplement.
- I09-S02: language ABI register windows, mixed overflow stack layout, and spill rules.
- I09-S03: baseline syscall ABI register, overflow, return, and volatility policy.
- I09-S04: debugger register view and protected return-stack unwind profile.
- I10-S01: RTL handoff decoder, commit-point, fault-packet, tag-path, and conformance checklist.
- I11-S01: program-image manifest and loader boundary validation.
- I11-S02: serialized cell image loading with explicit capability sidecars.
- I11-S03: serialized reset-to-trap smoke program execution.
- I12-S01: one-command local check runner.
- I12-S02: implementation story coverage report.
- I12-S03: story index and implementation documentation drift checks.
- I13-S01: single-issue in-order pipeline trace model.
- I13-S02: pipeline versus semantic execution comparison.
- I13-S03: first hazard, MDU busy, and predictor trace cases.
- I14-S01: trusted tiny ROM initialization and kernel handoff fixture.
- I14-S02: minimal trap-frame, syscall, timer, and IRET handler fixtures.

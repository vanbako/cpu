# Implementation Notes

This directory holds mutable implementation documents for CPU v0.1.

Use this directory for:

- Minimal platform profiles.
- Opcode allocation plans.
- Object-file and cell-serialization notes.
- Trap-frame and context-switch ABI supplements.
- Implementation decisions that do not change the frozen architecture contract.

Normative architecture stories remain in `spec/`.

Start with `docs/implementation/local-checks.md` for the local commands expected before implementation commits.

Current platform binding:

- `docs/implementation/test-platform-profile.md`: minimal simulator/test platform for reset, memory map, fatal-entry, and debug policy.
- `docs/implementation/secondary-startup.md`: per-core start mailbox and platform start-event binding.
- `docs/implementation/trap-context-abi.md`: trap-frame layout and context-switch save-set supplement.
- `docs/implementation/rtl-handoff.md`: decoder, commit-point, fault-packet, tag-path, and conformance checklist for RTL.
- `docs/implementation/cell-serialization-profile.md`: little-endian 24-bit cell serialization and section payload rules for byte-oriented host containers.
- `docs/implementation/relocatable-object-metadata.md`: relocatable object sections, slot-aware symbols, capability sidecar provenance, and ABI attributes.
- `docs/implementation/linker-relocation-fixtures.md`: section placement, symbol resolution, and first relocation fixture profile.
- `docs/implementation/debug-metadata.md`: source-line, symbol, ABI register, unwind, and symbolic disassembly metadata fixtures.
- `docs/implementation/toolchain-regression-corpus.md`: executable assembler/linker/debug/bad-object regression corpus.
- `docs/implementation/user-process-entry.md`: user process image and kernel-installed entry-context fixture.
- `docs/implementation/vm-page-mapping.md`: deterministic user VM page-table allocation and mapping fixtures.
- `docs/implementation/user-syscall-demo.md`: user-to-kernel syscall round-trip fixture with validation and returns.
- `docs/implementation/minimal-scheduler.md`: timer preemption and two-task context-switch fixture.
- `docs/implementation/endpoint-event-routing.md`: topology-neutral endpoint event, IPI, and interrupt routing fixture.
- `docs/implementation/external-agent-transfers.md`: noncoherent external-agent ownership and cache-maintenance fixture.
- `docs/implementation/point-to-point-fabric-litmus.md`: four-core point-to-point fabric integration litmus suite.
- `docs/implementation/language-abi.md`: public call-boundary register windows, mixed overflow layout, and spill rules.
- `docs/implementation/syscall-abi.md`: baseline syscall service register, argument registers, overflow layout, returns, and volatility.
- `docs/implementation/debugger-abi.md`: direct halted-core register view and protected return-stack unwind rules.
- `docs/implementation/conformance-test-index.md`: story-derived conformance and litmus test ownership index.
- `docs/implementation/program-image-manifest.md`: simulator program-image manifest and loader boundary profile.
- `docs/implementation/program-image-loader.md`: serialized cell image loading and explicit capability sidecar profile.
- `docs/implementation/reset-to-trap-smoke.md`: serialized reset-to-trap smoke fixture for the semantic simulator.
- `docs/implementation/story-coverage.md`: implementation story coverage report profile.
- `docs/implementation/pipeline-trace.md`: single-issue in-order pipeline trace model.
- `docs/implementation/pipeline-semantic-comparison.md`: pipeline versus semantic execution comparison profile.
- `docs/implementation/pipeline-hazards-predictor.md`: first hazard, MDU busy, and predictor trace profile.
- `docs/implementation/tiny-rom.md`: trusted tiny ROM initialization and kernel handoff fixture.
- `docs/implementation/minimal-kernel-handlers.md`: trap-frame, syscall, timer, and `IRET` handler fixtures.
- `docs/implementation/secondary-core-boot-demo.md`: firmware-controlled secondary-core startup demo.
- `docs/implementation/external-fabric-cpu-boundary.md`: CPU-side external endpoint and future fabric attachment boundary.
- `docs/implementation/capability-monotonicity-properties.md`: deterministic property-style capability monotonicity checks.
- `docs/implementation/tag-integrity-properties.md`: deterministic property-style capability tag non-forgery checks.
- `docs/implementation/precise-fault-properties.md`: deterministic property-style precise-fault side-effect checks.
- `docs/implementation/invariant-registry.md`: invariant coverage registry for property and RTL follow-up work.
- `docs/implementation/capability-property-generators.md`: deterministic capability derivation property case generators.
- `docs/implementation/invariant-runner.md`: seed-stable invariant case runner and replay CLI.
- `docs/implementation/rtl-first-slice-contract.md`: first SystemVerilog slice boundary, pipeline, retire-packet, memory/tag, and unsupported-feature contract.
- `docs/implementation/golden-retire-trace-corpus.md`: deterministic semantic retire packet corpus for future RTL differential testing.
- `docs/implementation/systemverilog-interface-spec.md`: generated SystemVerilog package/type/interface contract for the first RTL boundary.
- `docs/implementation/verilator-differential-harness.md`: dry-run and observed-trace comparator boundary for future Verilator RTL tests.
- `docs/implementation/verilator-regression-gate.md`: fast/slow Verilator regression-suite gate over golden and toolchain case IDs.
- `docs/implementation/rtl-smoke-slice.md`: first SystemVerilog reset/ADD/placement-fault smoke slice and golden projection.
- `docs/implementation/rtl-capability-memory-slice.md`: SystemVerilog capability register and memory/tag smoke slice with golden projection.
- `docs/implementation/rtl-fault-trap-slice.md`: SystemVerilog precise fault, trap, `IRET`, and protected return-stack smoke slice with golden projection.
- `docs/implementation/rtl-readiness-gap-report.md`: RTL readiness gap report, unsupported surface inventory, and local gate command for future RTL commits.
- `docs/implementation/rtl-scalar-control-slice.md`: SystemVerilog scalar integer, branch/control, CSR, and CCSR coverage slice for I21 semantic closure.
- `docs/implementation/rtl-mmu-tlb-slice.md`: SystemVerilog RADIX4, TLB, SATP, ASID, page-fault, and `SFENCE.VM*` coverage slice for I21 semantic closure.
- `docs/implementation/rtl-atomic-cache-slice.md`: SystemVerilog LL/SC, reservation, fence, and cache-maintenance coverage slice for I21 semantic closure.
- `docs/implementation/rtl-control-trap-slice.md`: SystemVerilog `CALLC`, protected `RET`, `SYS`/`SCALL`, syscall frame, and `IRET` coverage slice for I21 semantic closure.
- `docs/implementation/rtl-semantic-closure.md`: single-core RTL semantic closure report with mandatory family, invariant, deferral, and gate mapping.
- `docs/implementation/rtl-integrated-core-plan.md`: I22 plan for replacing fixture-only RTL slices with an integrated `cpu_v01_core` top level and regression gate.
- `docs/implementation/rtl-integrated-core-shell.md`: I22-S01 `cpu_v01_core` top-level shell, no-program smoke boundary, and port projection.
- `docs/implementation/rtl-integrated-core-fetch-decode.md`: I22-S02 integrated instruction fetch, slot sequencing, 12/24/48-bit decode, and front-end fault projection.
- `docs/implementation/rtl-integrated-core-scalar-control.md`: I22-S03 integrated scalar, branch, CSR, CCSR, EPCC, PAUSE, and BRK retire effects in `cpu_v01_core`.
- `docs/implementation/rtl-integrated-core-cap-mem.md`: I22-S04 integrated capability derivation, data-memory, and tag-memory retire effects in `cpu_v01_core`.
- `docs/implementation/rtl-integrated-core-control-trap.md`: I22-S05 integrated call, protected return-stack, syscall trap, trap-frame, and `IRET` retire effects in `cpu_v01_core`.
- `docs/implementation/rtl-integrated-core-mmu-tlb.md`: I22-S06 integrated `SATP`/`ASID`, data translation, local TLB, `SFENCE.VM*`, and page-fault retire effects in `cpu_v01_core`.
- `docs/implementation/rtl-integrated-core-atomic-cache.md`: I22-S07 integrated `LL48`/`SC48`, reservation, fence, and cache-maintenance retire effects in `cpu_v01_core`.
- `docs/implementation/rtl-integrated-core-regression-gate.md`: I22-S08 integrated `cpu_v01_core` Verilator regression-gate case registry, trace comparison, and deferral profile.
- `docs/implementation/fpga-first-test-plan.md`: I23-S01 through I23-S06 first FPGA smoke bring-up profile, story refinement, memory map, synthesis gate, and board evidence plan.
- `docs/implementation/fpga-top-wrapper.md`: I23-S02 board-neutral `cpu_v01_fpga_top` wrapper, reset synchronization, status/debug outputs, and fetch-disabled smoke attachment.
- `docs/implementation/fpga-memory-adapters.md`: I23-S03 FPGA instruction ROM, data RAM, and tag RAM adapters plus initialization and tag-clear checks.
- `docs/implementation/fpga-smoke-firmware.md`: I23-S04 built-in PAUSE smoke firmware, pass/fail LED contract, heartbeat, retire count, and fault observation.
- `docs/implementation/fpga-synthesis-gate.md`: I23-S05 Tang Mega 138K synthesis, place-route, timing, bitstream, and board-constraint gate profile.
- `docs/implementation/fpga-board-bringup.md`: I23-S06 Tang Mega 138K programming, reset, observation, evidence, and documented-blocker runbook.
- `docs/implementation/fpga-board-identity.md`: I24-S01 Tang Mega 138K physical device/package identity evidence gate and blocker profile.
- `docs/implementation/fpga-constraints-overlay.md`: I24-S02 Tang Mega 138K first-test CST template, SDC timing file, pin evidence audit, and blocker profile.
- `docs/implementation/fpga-gowin-build.md`: I24-S03 Gowin build command plan, report-bundle audit, bitstream handoff, and blocker profile.
- `docs/implementation/fpga-board-programming.md`: I24-S04 SRAM programming evidence parser, first pass/fail/heartbeat audit, and physical-run blocker profile.
- `docs/implementation/fpga-first-board-evidence.md`: I24-S05 first-board evidence archive, blocker disposition audit, and downstream handoff profile.

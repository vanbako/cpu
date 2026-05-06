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
- `docs/implementation/rtl-smoke-slice.md`: first SystemVerilog reset/ADD/placement-fault smoke slice and golden projection.
- `docs/implementation/rtl-capability-memory-slice.md`: SystemVerilog capability register and memory/tag smoke slice with golden projection.
- `docs/implementation/rtl-fault-trap-slice.md`: SystemVerilog precise fault, trap, `IRET`, and protected return-stack smoke slice with golden projection.
- `docs/implementation/rtl-readiness-gap-report.md`: RTL readiness gap report, unsupported surface inventory, and local gate command for future RTL commits.

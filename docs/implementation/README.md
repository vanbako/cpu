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

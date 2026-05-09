# AGENTS.md

## Scope

These instructions apply to the whole repository. If a narrower `AGENTS.md`
is added later, follow the more specific file for that subtree.

## Repository Map

- `agile-impl-v0.1.md`: implementation epic and story backlog. Start here
  before changing behavior.
- `spec/`: frozen or normative architecture stories.
- `docs/implementation/`: mutable implementation notes. Most story-owned
  documents use a single `Story: Ixx-Syy` owner line near the top.
- `docs/implementation/conformance-test-index.md`: ownership index for tests,
  tools, implementation notes, architecture owner stories, and E15 coverage.
- `src/cpu_v01/`: Python semantic models, validators, generated inventories,
  and report helpers.
- `tools/`: command-line validators and local check runners.
- `tests/conformance/` and `tests/litmus/`: unittest coverage. Test filenames
  are story-derived.
- `rtl/`: SystemVerilog RTL, packages, FPGA wrappers, and Verilator testbenches.

## Working Flow

1. Run `git status --short` before editing. The tree may contain user changes;
   do not revert changes you did not make.
2. Read the relevant story in `agile-impl-v0.1.md` and the nearby
   implementation note under `docs/implementation/`.
3. Keep each change story-scoped. A normal story change updates some mix of:
   Python model or validator, RTL, focused unittest, implementation note, and
   conformance index row.
4. When adding a new implementation note under `docs/implementation/`, include
   exactly one `Story: Ixx-Syy` owner line unless the local pattern clearly says
   otherwise.
5. When adding a new `tests/conformance/test_*.py` or
   `tests/litmus/test_*.py`, add a matching row to
   `docs/implementation/conformance-test-index.md` in the same change.
6. Prefer existing local helpers and style over new abstractions. Keep edits
   close to the story surface.
7. Use `apply_patch` for manual edits. Avoid generated churn and unrelated
   formatting changes.

## Verification

For a focused story, run the specific validator and unittest first, for example:

```text
python tools\<story_validator>.py --check
python -m unittest tests.conformance.test_iXX_sYY_<name>
```

Run these drift checks before committing story work:

```text
python tools\spec_reference_check.py
python tools\story_coverage.py --check-drift
git diff --check
```

The full local gate is:

```text
python tools\local_checks.py
```

`tools/local_checks.py --list` prints the exact command plan.

## RTL And FPGA Notes

- Shared RTL types live in `rtl/cpu_v01_pkg.sv`.
- The integrated CPU top is `cpu_v01_core`.
- The board-neutral FPGA first-test top is `cpu_v01_fpga_top`.
- Keep Verilator commands in the Python story helper when a story owns RTL or
  a testbench. Existing helpers expose command strings and self-validation.
- Verilator is installed through MSYS2 in this workspace. Prior runs used
  lint/elaboration successfully; binary Verilator builds may also need MSYS2
  `make` or `mingw32-make` available on `PATH`.

The current FPGA bring-up thread has completed profile, top-wrapper, memory
adapter, smoke-firmware, synthesis-gate, and board-runbook slices for the
Sipeed Tang Mega 138K Dock. Physical board evidence is still blocked on a
verified device/package scan, CST pin overlay, Gowin reports, bitstream, and
LED or probe capture. Use `docs/implementation/fpga-board-identity.md`,
`python tools\fpga_board_identity.py --check`,
`docs/implementation/fpga-constraints-overlay.md`, and
`python tools\fpga_constraints_overlay.py --check` before generating
board-specific constraints. Use `docs/implementation/fpga-gowin-build.md` and
`python tools\fpga_gowin_build.py --check` before handing a bitstream to board
programming. Use `docs/implementation/fpga-board-programming.md` and
`python tools\fpga_board_programming.py --check` to audit SRAM programming,
reset release, heartbeat, pass/fail, retire, and fault evidence. Use
`docs/implementation/fpga-first-board-evidence.md` and
`python tools\fpga_first_board_archive.py --check` to close or file residual
bring-up blockers. Use `docs/implementation/fpga-debug-status-packet.md` and
`python tools\fpga_debug_status_packet.py --check` before changing the packet
layout. Use `docs/implementation/fpga-uart-status-streamer.md` and
`python tools\fpga_uart_status_streamer.py --check` before changing UART debug
transport around the status packet. Use
`docs/implementation/fpga-probe-bundles.md` and
`python tools\fpga_probe_bundles.py --check` before changing optional GAO/ILA
probe definitions. Use `docs/implementation/fpga-replay-mapper.md` and
`python tools\fpga_replay_mapper.py --check` before changing captured-status
to Verilator replay mapping. Use
`docs/implementation/fpga-debug-evidence-gate.md` and
`python tools\fpga_debug_evidence.py --check` before changing failure evidence
closure rules. Use `docs/implementation/fpga-program-image-manifest.md` and
`python tools\fpga_program_manifest.py --check` before adding FPGA `.mem`
generation, bitstream memory updates, or multi-program smoke images. Use
`docs/implementation/fpga-bram-image-generation.md` and
`python tools\fpga_bram_images.py --check` before changing generated BRAM image
formats, write paths, or manifest hash checks. Use
`docs/implementation/fpga-image-update-flow.md` and
`python tools\fpga_image_update_flow.py --check` before changing the Gowin
rebuild, memory-update, image identity, or bitstream hash handoff. Use
`docs/implementation/fpga-smoke-program-corpus.md` and
`python tools\fpga_smoke_corpus.py --check` before changing multi-program
smoke cases or expected LED/UART/probe signatures. Keep the device/package
verification note in
`docs/implementation/fpga-first-test-plan.md` and the evidence contract in
`docs/implementation/fpga-board-bringup.md` in mind before claiming a board
pass.

## Story Coverage Rules

- Every implementation backlog story should have indexed evidence.
- Every test row in `docs/implementation/conformance-test-index.md` needs an
  implementation story, architecture owner story or freeze artifact, and E15
  coverage.
- `python tools\story_coverage.py --check-drift` fails for missing test index
  rows, stale indexed artifact paths, and unowned implementation documents.
- `python tools\spec_reference_check.py` verifies that story-owned
  implementation docs have the expected `Story:` headers.

## Git

When asked to commit:

1. Inspect `git status --short`.
2. Stage only the files intended for the completed change.
3. Run the relevant focused checks, or state clearly why they were not run.
4. Commit with a concise imperative message.

Do not use destructive git commands such as `git reset --hard` or
`git checkout --` unless explicitly requested.

## Skills

Repo-local guidance belongs in this file. Codex skills are useful only when a
workflow should be reused across sessions or repositories. The previously
executed work suggests these optional skills, but they do not need to be
installed for this repo to function:

- `cpu-v01-story-implementation`: use when implementing a backlog story in this
  repo. Workflow: read the story, update the model/RTL/doc/test/index surfaces,
  run the story validator, run focused unittest, then run drift checks.
- `cpu-v01-rtl-verilator-slice`: use when changing SystemVerilog or Verilator
  testbenches for this CPU. Workflow: inspect the existing RTL helper pattern,
  update RTL and Python command inventory together, lint/elaborate with
  Verilator, and record deferrals in the implementation note.
- `cpu-v01-fpga-bringup`: use when continuing the first FPGA test path.
  Workflow: maintain the first-test profile, top wrapper, BRAM adapters, smoke
  firmware, synthesis/timing gate, and board evidence as one coherent bring-up
  thread.

If these workflows should become actual Codex skills, create them under
`%USERPROFILE%\.codex\skills` or the configured `CODEX_HOME\skills` path with a
proper `SKILL.md`, then validate them with the skill validator.

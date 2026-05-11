# FPGA Retro Console Failure Replay

Story: I34-S05

Status: Retro Console 60K failure replay classification gate implemented;
physical classification remains blocked until an I34-S04 `failure_observed`
capture exists.

Structured gate:

```text
python tools\fpga_retro_console_replay.py --check
```

Evidence template:

```text
python tools\fpga_retro_console_replay.py --template
```

Evidence audit:

```text
python tools\fpga_retro_console_replay.py --audit docs\implementation\evidence\i34_s05_retro_console_replay_classification.txt
```

## Purpose

I34-S05 consumes an I34-S04 `failure_observed` Retro Console 60K SRAM
programming capture and turns it into a replayable failure disposition. The
gate requires the captured `uart_status_packet_hex`, an I25-S04 replay mapping,
the selected `replay_case_id`, the exact `replay_command`, an `observed_trace`
or explicit `none`, preserved `first_mismatch` or assertion output, accepted
I25-S05 debug evidence, and `primary_138k_claim=no`.

The gate classifies failures as `board_identity`, `constraints`,
`clock_reset`, `memory`, `firmware`, `loader`, `trap`, or `cpu_rtl`. A
classified failure is handed to I34-S06 for the Retro Console pass/blocker
archive without claiming a Tang Mega Dock with 138K SOM pass.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_retro_console_replay.py` | Structured I34-S05 profile, template, parser, audit rules, status-packet classification, and validator. |
| `tools/fpga_retro_console_replay.py` | CLI wrapper for checking, JSON, template, class list, retest commands, and evidence audit. |
| `tests/conformance/test_i34_s05_fpga_retro_console_replay.py` | Conformance coverage for profile dependencies, packet-to-replay selection, failure classes, CLI output, and docs. |
| `docs/implementation/fpga-retro-console-replay.md` | This implementation note. |

## Evidence Format

The classification record lives at
`docs/implementation/evidence/i34_s05_retro_console_replay_classification.txt`
and uses:

```text
story=I34-S05
classified_at=
repository_commit=
board=Sipeed Tang Retro Console with 60K SOM
retro_console_programming=docs/implementation/evidence/i34_s04_retro_console_programming.txt
programming_board_result=failure_observed
primary_138k_claim=no
capture_source=uart
uart_status_packet_hex=
uart_log=docs/implementation/evidence/i34_s05_uart_failure.log
decoded_status_packet=docs/implementation/evidence/i34_s05_status_packet.json
probe_capture=none
replay_mapping=docs/implementation/evidence/i34_s05_replay_mapping.json
replay_case_id=core.control_trap.sys_iret
replay_command=python tools\verilator_diff_harness.py --case-id core.control_trap.sys_iret
observed_trace=build\fpga\captures\status_sequence_5_retire_trace.json
first_mismatch=core.control_trap.sys_iret packet 5: pc_cell mismatch
failure_class=trap
classification_rationale=syscall trap captured in Retro Console status packet
debug_evidence=docs/implementation/evidence/i25_s05_debug_evidence.txt
debug_evidence_status=accepted
followup_issue=CPU-123
retest_commands=python tools\fpga_retro_console_programming.py --check ; python tools\fpga_replay_mapper.py --check ; python tools\fpga_debug_evidence.py --check ; python tools\verilator_diff_harness.py --case-id core.control_trap.sys_iret
```

## Required Gates

| Gate | Command | Role |
| --- | --- | --- |
| Retro Console programming | `python tools\fpga_retro_console_programming.py --check` | Supplies the I34-S04 `failure_observed` board capture and status packet. |
| Replay mapper | `python tools\fpga_replay_mapper.py --check` | Selects ranked Verilator replay cases from the captured packet. |
| Debug evidence | `python tools\fpga_debug_evidence.py --check` | Requires UART or GAO/ILA evidence and a triage disposition. |
| Verilator replay | `python tools\verilator_diff_harness.py --case-id <case_id>` | Preserves first-mismatch or assertion diagnostics for the selected case. |

## Classification Rules

| Failure class | Status signature | Replay requirement |
| --- | --- | --- |
| `board_identity` | Device/package, board marking, programmer scan, or 60K target mismatch. | Preserve status capture and the I34-S01 identity discrepancy. |
| `constraints` | Pin, IO voltage, clock, reset, LED, UART, or SDC mismatch. | Preserve replay/probe capture plus the suspect CST/SDC evidence. |
| `clock_reset` | Reset asserted, core idle, or no retire progress. | Use `core.shell.reset_idle` or preserve reset/probe assertion evidence. |
| `memory` | Access, align, page, capability, tag, bounds, permission, or local-store fault. | Use cap/mem, fetch/decode, or MMU replay output and keep `first_mismatch`. |
| `firmware` | Failed packet without board, memory, loader, trap, or RTL evidence. | Use scalar/control replay plus ROM/image/pass-condition evidence. |
| `loader` | Image load, entry handoff, or loader data implicated. | Preserve replay plus loader/image evidence. |
| `trap` | Syscall, return-stack, divide, debug, or control-trap cause. | Use control/trap or scalar fault replay and keep `first_mismatch`. |
| `cpu_rtl` | Selected core replay produces a first mismatch or assertion after board evidence is clean. | Preserve the core replay case, observed trace, and first mismatch line. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `classified` | Failure capture has a replay case, first mismatch, accepted debug evidence, class, and issue. | Hand the record to I34-S06. |
| `needs_capture` | Failure observation lacks complete UART or GAO/ILA capture evidence. | Recapture the board packet/probes and rerun I34-S04/I25-S05. |
| `needs_triage` | Packet exists but replay, first mismatch, classification, or issue is incomplete. | Run I25-S04 and Verilator replay, then update the classification. |
| `invalid` | Required fields, links, the 138K non-claim guard, or the 32-byte packet are malformed. | Fix the key/value record and rerun the audit. |
| `blocked` | I34-S04 has not produced a Retro Console board failure capture. | Complete programming evidence or archive the smoke result through I34-S06. |

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Captured status selects a Verilator replay case. | Met by requiring `uart_status_packet_hex`, I25-S04 `replay_mapping`, `replay_case_id`, and `replay_command`. |
| First mismatch is preserved. | Met by requiring `first_mismatch` or assertion diagnostics for closure. |
| Board identity, constraints, clock/reset, memory, firmware, loader, trap, and CPU RTL failures are classified. | Met by the required `failure_class` set and packet/rationale matching rules. |
| I34-S04, I25-S04, and I25-S05 are used directly. | Met by required gate links and validator dependencies. |
| The 138K first-pass board is not claimed. | Met by `primary_138k_claim=no` and the audit guard. |
| I34-S06 receives a pass/blocker disposition. | Met by the `classified` audit action and `followup_issue` requirement. |

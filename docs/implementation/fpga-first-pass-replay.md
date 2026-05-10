# FPGA First-Pass Failure Replay

Story: I31-S04

Status: Failure replay classification gate implemented; physical capture blocked

Structured gate:

```text
python tools\fpga_first_pass_replay.py --check
```

Evidence template:

```text
python tools\fpga_first_pass_replay.py --template
```

Evidence audit:

```text
python tools\fpga_first_pass_replay.py --audit docs\implementation\evidence\i31_s04_failure_replay_classification.txt
```

## Purpose

I31-S04 consumes an I31-S03 `failure_observed` programming capture and makes it
actionable before the first physical pass/blocker archive closes. The gate
requires the captured `uart_status_packet_hex`, an I25-S04 replay mapping,
the selected `replay_case_id`, the exact `replay_command`, an `observed_trace`
or explicit `none`, and preserved `first_mismatch` or assertion output.

The classification is intentionally narrower than a generic debug log. It
classifies first-pass board failures as `clock_reset`, `memory`, `firmware`,
`trap`, `translation`, `loader`, or `board_integration`, then links I25-S05
debug evidence and a filed follow-up before I31-S05 can archive the disposition.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_first_pass_replay.py` | Structured I31-S04 profile, template, parser, audit rules, status-packet classification, and validator. |
| `tools/fpga_first_pass_replay.py` | CLI wrapper for checking, JSON, template, class list, retest commands, and evidence audit. |
| `tests/conformance/test_i31_s04_fpga_first_pass_replay.py` | Conformance coverage for profile dependencies, packet-to-replay selection, classification, CLI output, and docs. |
| `docs/implementation/fpga-first-pass-replay.md` | This implementation note. |

## Evidence Format

The classification record lives at
`docs/implementation/evidence/i31_s04_failure_replay_classification.txt` and
uses:

```text
story=I31-S04
classified_at=
repository_commit=
first_pass_programming=docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt
programming_board_result=failure_observed
capture_source=uart
uart_status_packet_hex=
uart_log=docs/implementation/evidence/i31_s04_uart_failure.log
decoded_status_packet=docs/implementation/evidence/i31_s04_status_packet.json
probe_capture=none
replay_mapping=docs/implementation/evidence/i31_s04_replay_mapping.json
replay_case_id=core.control_trap.sys_iret
replay_command=python tools\verilator_diff_harness.py --case-id core.control_trap.sys_iret
observed_trace=build\fpga\captures\status_sequence_4_retire_trace.json
first_mismatch=core.control_trap.sys_iret packet 4: pc_cell mismatch
failure_class=trap
classification_rationale=syscall trap captured in first-pass status packet
debug_evidence=docs/implementation/evidence/i25_s05_debug_evidence.txt
debug_evidence_status=accepted
followup_issue=CPU-123
retest_commands=python tools\fpga_first_pass_programming.py --check ; python tools\fpga_replay_mapper.py --check ; python tools\fpga_debug_evidence.py --check ; python tools\verilator_diff_harness.py --case-id core.control_trap.sys_iret
```

## Required Gates

| Gate | Command | Role |
| --- | --- | --- |
| First-pass programming | `python tools\fpga_first_pass_programming.py --check` | Supplies the `failure_observed` board capture and status packet. |
| Replay mapper | `python tools\fpga_replay_mapper.py --check` | Selects ranked Verilator replay cases from the captured packet. |
| Debug evidence | `python tools\fpga_debug_evidence.py --check` | Requires UART or GAO/ILA evidence and a triage disposition. |
| Verilator replay | `python tools\verilator_diff_harness.py --case-id <case_id>` | Preserves first-mismatch or assertion diagnostics for the selected case. |

## Classification Rules

| Failure class | Status signature | Replay requirement |
| --- | --- | --- |
| `clock_reset` | Reset asserted, core idle, or no retire progress. | Use `core.shell.reset_idle` or preserve reset/probe assertion evidence. |
| `memory` | Access, align, capability, tag, bounds, permission, or local-store fault. | Use cap/mem or fetch/decode replay output and keep `first_mismatch`. |
| `firmware` | Failed packet without memory, trap, translation, loader, or board evidence. | Use scalar/control replay plus ROM/image/pass-condition evidence. |
| `trap` | Syscall, return-stack, divide, debug, or control-trap cause. | Use control/trap or scalar fault replay and keep `first_mismatch`. |
| `translation` | Page-fault cause or MMU/TLB replay selection. | Use `core.mmu_tlb.translation_sfence`. |
| `loader` | Image load, entry handoff, or loader data implicated. | Preserve replay plus loader/image evidence. |
| `board_integration` | Pins, LEDs, UART/probe wiring, constraints, or board package implicated. | Preserve replay/probe evidence even when core replay is clean. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `classified` | Failure capture has a replay case, first mismatch, accepted debug evidence, class, and issue. | Hand the record to I31-S05. |
| `needs_capture` | Failure observation lacks complete UART or GAO/ILA capture evidence. | Recapture the board packet/probes and rerun I31-S03/I25-S05. |
| `needs_triage` | Packet exists but replay, first mismatch, classification, or issue is incomplete. | Run I25-S04 and Verilator replay, then update the classification. |
| `invalid` | Required fields, links, or the 32-byte packet are malformed. | Fix the key/value record and rerun the audit. |
| `blocked` | I31-S03 has not produced a board failure capture. | Complete programming evidence or archive first pass through I31-S05. |

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Captured status selects a Verilator replay case. | Met by requiring `uart_status_packet_hex`, I25-S04 `replay_mapping`, `replay_case_id`, and `replay_command`. |
| First mismatch is preserved. | Met by requiring `first_mismatch` or assertion diagnostics for closure. |
| Clock/reset, memory, firmware, trap, translation, loader, and board integration failures are classified. | Met by the required `failure_class` set and packet/rationale matching rules. |
| I31-S03, I25-S04, and I25-S05 are used directly. | Met by required gate links and validator dependencies. |
| I31-S05 receives a pass/blocker disposition. | Met by the `classified` audit action and `followup_issue` requirement. |

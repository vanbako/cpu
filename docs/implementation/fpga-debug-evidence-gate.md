# FPGA Debug Evidence Gate

Story: I25-S05

Status: Debug-evidence gate implemented; physical evidence blocked

Structured gate:

```text
python tools\fpga_debug_evidence.py --check
```

Evidence template:

```text
python tools\fpga_debug_evidence.py --template
```

Evidence audit:

```text
python tools\fpga_debug_evidence.py --audit-evidence docs\implementation\evidence\i25_s05_debug_evidence.txt
```

## Purpose

I25-S05 adds a debug-evidence gate to the FPGA bring-up runbook. It makes
nontrivial board failures actionable by requiring `UART or GAO/ILA` evidence,
I25-S04 replay mapping, and a preserved `first_mismatch` or assertion
diagnostic before a failure can be treated as triaged.

Clock/reset failures are handled separately because UART may not be available
when the clock, reset, or pin overlay is wrong. Those cases still need reset or
probe evidence and an explicit `clock_reset` diagnosis.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_debug_evidence.py` | Structured I25-S05 profile, evidence parser, audit rules, and validator. |
| `tools/fpga_debug_evidence.py` | CLI wrapper for checking, JSON, template, and captured-evidence audit output. |
| `tests/conformance/test_i25_s05_fpga_debug_evidence.py` | Conformance tests for profile, audit outcomes, CLI, docs, and dependency gates. |
| `docs/implementation/fpga-debug-evidence-gate.md` | This implementation note. |

## Evidence Format

The debug-evidence record lives at
`docs/implementation/evidence/i25_s05_debug_evidence.txt` and uses:

```text
story=I25-S05
board=Sipeed Tang Mega 138K Dock
captured_at=
first_board_archive=docs/implementation/evidence/i24_s05_first_board_archive.txt
board_result=
symptom_class=
evidence_source=
uart_packet_hex=none
uart_log=none
probe_capture=none
probe_setup=none
replay_mapping=none
replay_command=none
first_mismatch=none
clock_reset_diagnosis=not_applicable
firmware_diagnosis=not_applicable
memory_diagnosis=not_applicable
trap_diagnosis=not_applicable
translation_diagnosis=not_applicable
followup_issue=none
retest_steps=none
```

## Required Gates

| Gate | Command | Role |
| --- | --- | --- |
| First-board archive | `python tools\fpga_first_board_archive.py --check` | Provides the board run and blocker context. |
| UART status stream | `python tools\fpga_uart_status_streamer.py --check` | Provides packet capture path for debug evidence. |
| GAO/ILA probes | `python tools\fpga_probe_bundles.py --check` | Provides probe list and trigger policy. |
| Replay mapping | `python tools\fpga_replay_mapper.py --check` | Selects Verilator replay cases and commands. |

## Triage Classes

| Symptom class | Required capture | Replay requirement | Distinguishes |
| --- | --- | --- | --- |
| `clock_reset` | Reset observation plus LED/probe clock evidence; UART may be unavailable. | Replay optional until clock/reset is alive. | Pin, reset synchronizer, and clocking failures. |
| `firmware` | UART packet or GAO/ILA status capture. | I25-S04 replay mapping and selected Verilator command. | ROM/image/pass-condition failures. |
| `memory` | UART packet plus GAO/ILA `memory_handshake` capture when available. | I25-S04 replay mapping to cap/mem or fetch/decode cases. | Memory adapter stalls versus execution faults. |
| `trap` | UART packet or GAO/ILA `status_packet` capture with fault/trap fields. | I25-S04 replay mapping to control/trap cases. | Trap-frame or return-stack failures. |
| `translation` | UART packet or GAO/ILA `status_packet` capture with page-fault evidence. | I25-S04 replay mapping to MMU/TLB cases. | Address translation versus memory adapter failures. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required debug evidence is complete for the result and symptom class. | Reference the record from downstream FPGA stories. |
| `needs_capture` | A nontrivial failure lacks UART packet hex or GAO/ILA capture evidence. | Capture UART/probe evidence and rerun the audit. |
| `needs_triage` | Evidence exists but classification, replay, or first-mismatch disposition is incomplete. | Record replay mapping, selected command, and diagnostics. |
| `invalid` | Required fields are missing or malformed. | Fix the key/value record and rerun the audit. |
| `blocked` | I24-S05 archive or I25-S05 evidence does not exist yet. | Capture the board archive and debug evidence first. |

## Runbook Impact

- A simple `first_pass` may close with LED/video plus optional UART/probe logs.
- A nontrivial `firmware`, `memory`, `trap`, `translation`, or `unknown`
  failure cannot close from LED state alone.
- `clock_reset` failures must explain why UART or ILA evidence is unavailable
  or insufficient and must preserve reset/clock evidence.
- Any replayable failure must include `replay_command`, `replay_mapping`, and
  `first_mismatch` or assertion diagnostics.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| UART or ILA evidence is required for nontrivial failures. | Met by the `needs_capture` audit path. |
| Clock/reset failures are distinguished from execution failures. | Met by the `clock_reset` class and diagnosis field. |
| Firmware, memory, trap, and translation failures are classified. | Met by required symptom classes and diagnosis fields. |
| Replay mapping is part of failure closure. | Met by required `replay_mapping` and `replay_command`. |
| First-mismatch diagnostics are preserved. | Met by required `first_mismatch` for nontrivial failure classes. |

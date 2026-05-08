# FPGA Probe Bundles

Story: I25-S03

Status: Optional GAO/ILA probe definitions implemented

Structured gate:

```text
python tools\fpga_probe_bundles.py --check
```

Probe list:

```text
python tools\fpga_probe_bundles.py --list
```

## Purpose

I25-S03 defines optional `GAO` or `ILA` probe bundles for first-failure FPGA
capture. The bundles use existing `cpu_v01_fpga_top` signals so the release
build keeps the same ports and does not instantiate analyzer IP by default.

The probe set complements the I25-S01 packet and I25-S02 UART stream. It
captures clock/reset, PC/slot, retire count, fault code, pass/fail/heartbeat,
and key memory handshakes in one view for board triage.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_probe_bundles.py` | Structured I25-S03 probe inventory, triggers, capture rules, and validator. |
| `tools/fpga_probe_bundles.py` | CLI wrapper for checking, JSON, CSV probe-list, and command-plan output. |
| `tests/conformance/test_i25_s03_fpga_probe_bundles.py` | Conformance tests for profile coverage, CLI output, docs, and non-interference rules. |
| `docs/implementation/fpga-probe-bundles.md` | This implementation note. |

## Bundles

| Bundle | Purpose |
| --- | --- |
| `clock_reset` | Confirms board clock, async reset, synchronized reset, and reset-observed state. |
| `status_packet` | Mirrors the I25-S01 status packet sources and first-test LEDs. |
| `memory_handshake` | Captures instruction, data, and tag memory request/response flow. |

## Required Probes

| Probe | Width | Source | Role |
| --- | --- | --- | --- |
| `probe_board_clk` | 1 | `board_clk_i` | Sample clock reference. |
| `probe_board_reset_n` | 1 | `board_reset_n_i` | Async board reset input. |
| `probe_core_rst_n` | 1 | `core_rst_n` | Synchronized core reset. |
| `probe_reset_observed` | 1 | `status_reset_observed_o` | Reset-release observation. |
| `probe_pcc_cursor_low` | 32 | `debug_pcc_cursor_low_o` | Current low PC/PCC cursor bits. |
| `probe_pc_slot` | 1 | `retire_packet.slot` | Retired instruction slot. |
| `probe_retire_valid` | 1 | `retire_valid` | Architectural retire marker. |
| `probe_retire_count` | 32 | `status_retire_count_o` | Retire progress counter. |
| `probe_fault_valid` | 1 | `status_fault_valid_o` | Sticky fault observation. |
| `probe_fault_code` | 16 | `status_fault_code_o` | Sticky first fault cause. |
| `probe_trap_cause` | 16 | `retire_packet.fault.cause` | Trap cause at sampled retire point. |
| `probe_pass_led` | 1 | `pass_led_o` | First-test pass state. |
| `probe_fail_led` | 1 | `fail_led_o` | First-test fail state. |
| `probe_heartbeat` | 1 | `heartbeat_led_o` | Retire-derived heartbeat. |
| `probe_imem_req_valid` | 1 | `imem_req_valid` | Instruction request valid. |
| `probe_imem_req_ready` | 1 | `imem_req_ready` | Instruction request accepted. |
| `probe_imem_rsp_valid` | 1 | `imem_rsp_valid` | Instruction response valid. |
| `probe_dmem_req_valid` | 1 | `dmem_req_valid` | Data request valid. |
| `probe_dmem_req_ready` | 1 | `dmem_req_ready` | Data request accepted. |
| `probe_dmem_req_write` | 1 | `dmem_req_write` | Data request direction. |
| `probe_dmem_rsp_valid` | 1 | `dmem_rsp_valid` | Data response valid. |
| `probe_tagmem_req_valid` | 1 | `tagmem_req_valid` | Tag memory request valid. |
| `probe_tagmem_req_ready` | 1 | `tagmem_req_ready` | Tag memory request accepted. |
| `probe_tagmem_req_write` | 1 | `tagmem_req_write` | Tag memory request direction. |
| `probe_tagmem_rsp_valid` | 1 | `tagmem_rsp_valid` | Tag memory response valid. |

Optional alignment probes include `probe_uart_tx`,
`probe_uart_packet_started`, and `probe_uart_sequence` when the I25-S02 UART
streamer is present in the debug build.

## Triggers

| Trigger | Source | Condition | Purpose |
| --- | --- | --- | --- |
| `reset_release` | `probe_reset_observed` | Rising edge. | Confirm reset synchronizer and first fetch startup. |
| `first_pass` | `probe_pass_led` | Rising edge. | Capture the first successful smoke completion window. |
| `first_fault` | `probe_fault_valid` or `probe_fail_led` | Rising edge. | Capture PC, slot, fault code, and handshakes around the first fault. |
| `memory_stall` | Request valid without ready or response progress. | High for 16 cycles. | Distinguish memory adapter stalls from core decode or trap faults. |
| `uart_packet_start` | `probe_uart_packet_started` | Rising edge. | Align probe samples with UART status packet sequence. |

## Setup

1. Run `python tools\fpga_probe_bundles.py --list` and import or copy the
   signal list into the Gowin GAO or generic ILA setup.
2. Use `board_clk_i` as the analyzer sample clock for the first-test design.
3. Put `clock_reset`, `status_packet`, and `memory_handshake` in the same
   capture group.
4. Trigger on `first_fault` for failure triage, or on `first_pass` for a
   known-good reference capture.
5. Archive the probe setup file, signal list, trigger condition, and capture
   output with the I25-S05 debug-evidence gate.

## Non-Interference

- The release build keeps the same `cpu_v01_fpga_top` ports.
- Probe definitions do not change `retire_ready` or memory ready/valid
  behavior.
- GAO or ILA IP is enabled only in a debug Gowin project variant.
- Captured samples are debug evidence and are not architectural state.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Clock/reset probes are defined. | Met by the `clock_reset` bundle. |
| PC/slot, retire count, fault code, and LEDs are exposed. | Met by the `status_packet` bundle. |
| Key memory handshakes are defined. | Met by the `memory_handshake` bundle. |
| Probe triggers cover pass and failure capture. | Met by `first_pass`, `first_fault`, and `memory_stall`. |
| Release build is not perturbed. | Met by profile-only probe definitions and non-interference rules. |

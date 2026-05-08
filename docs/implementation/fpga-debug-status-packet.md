# FPGA Debug Status Packet

Story: I25-S01

Status: Packet contract implemented

Structured gate:

```text
python tools\fpga_debug_status_packet.py --check
```

Example packet:

```text
python tools\fpga_debug_status_packet.py --example
```

## Purpose

I25-S01 defines the compact debug/status packet that later FPGA bring-up
stories can stream over UART or expose through GAO/ILA probes. The packet
captures reset state, PC/slot, retire count, fault code, trap cause,
pass/fail state, build identity, and packet sequence without changing
architectural retire behavior.

I25-S02 owns the UART status streamer and is checked with
`python tools\fpga_uart_status_streamer.py --check`. I25-S03 owns optional
GAO/ILA probe bundles and is checked with
`python tools\fpga_probe_bundles.py --check`. This story fixes the shared
packet layout those stories must use.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_debug_status.py` | Structured I25-S01 packet profile, flag definitions, encode/decode helpers, and validator. |
| `tools/fpga_debug_status_packet.py` | CLI wrapper for checking, printing JSON, emitting an example packet, and decoding packet hex. |
| `tests/conformance/test_i25_s01_fpga_debug_status_packet.py` | Conformance tests for fields, flags, encode/decode, CLI output, documentation, and non-interference rules. |
| `docs/implementation/fpga-debug-status-packet.md` | This implementation note. |

## Packet Layout

The packet is exactly `32 bytes`, little-endian, with magic `0xC501` and
version `1`.

| Field | Offset | Width | Source | Meaning |
| --- | --- | --- | --- | --- |
| `magic` | 0 | 16 | Constant `0xC501`. | Resynchronization marker. |
| `version` | 2 | 8 | Constant `1`. | Packet format version. |
| `packet_size` | 3 | 8 | Constant `32`. | Packet size in bytes. |
| `flags` | 4 | 16 | Status flags. | Reset, retire, fault, pass/fail, and heartbeat bits. |
| `slot` | 6 | 8 | `retire_packet.slot`. | Slot within the current fetch group. |
| `pass_fail_state` | 7 | 8 | `pass_led_o`/`fail_led_o` state machine. | `idle_or_reset`, `running`, `first_pass`, `failed`, or `blocked`. |
| `pc_cell` | 8 | 64 | `retire_packet.pc` or `debug_pcc.cursor`. | Zero-extended cell PC. |
| `retire_count` | 16 | 32 | `debug_retire_sequence[31:0]`. | Retire progress counter. |
| `fault_code` | 20 | 16 | `status_fault_code_o`. | Sticky first fault code. |
| `trap_cause` | 22 | 16 | `retire_packet.fault.cause`. | Trap cause for the sampled retire point. |
| `build_id` | 24 | 32 | First-test build identity register. | Software-visible build identity. |
| `sequence` | 28 | 32 | Debug packet counter. | Monotonic sequence for drop detection. |

## Flags

| Flag | Bit | Source | Meaning |
| --- | --- | --- | --- |
| `reset_asserted` | 0 | `board_reset_n_i`/`core_rst_n`. | Reset is currently asserted. |
| `reset_observed` | 1 | `status_reset_observed_o`. | Core reset observation has occurred. |
| `core_idle` | 2 | `status_core_idle_o`. | Core reports idle. |
| `retire_valid` | 3 | `status_retire_valid_o`. | Sample includes a retire observation. |
| `fault_valid` | 4 | `status_fault_valid_o`. | Sticky fault observation is set. |
| `pass_led` | 5 | `pass_led_o`. | First-test pass LED is asserted. |
| `fail_led` | 6 | `fail_led_o`. | First-test fail LED is asserted. |
| `heartbeat` | 7 | `heartbeat_led_o`. | Heartbeat observation is high in this sample. |

## Pass/Fail States

| Value | State |
| --- | --- |
| 0 | `idle_or_reset` |
| 1 | `running` |
| 2 | `first_pass` |
| 3 | `failed` |
| 4 | `blocked` |

## Non-Interference

- Packet generation samples existing debug and retire observation signals only.
- Packet generation must not deassert `retire_ready` or backpressure
  architectural retire behavior.
- UART or ILA consumers may drop packets without changing CPU state.
- `build_id` and `sequence` are debug metadata and are not architectural
  registers.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Reset state is covered. | Met by `reset_asserted` and `reset_observed`. |
| PC and slot are covered. | Met by `pc_cell` and `slot`. |
| Retire/fault/trap state is covered. | Met by `retire_count`, `fault_code`, and `trap_cause`. |
| Pass/fail state is covered. | Met by `pass_fail_state` and pass/fail flags. |
| Build identity is covered. | Met by `build_id`. |
| Architectural retire behavior is unchanged. | Met by the non-interference rules and downstream ownership split. |

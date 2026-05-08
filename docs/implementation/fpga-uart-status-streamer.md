# FPGA UART Status Streamer

Story: I25-S02

Status: UART streamer implemented; physical decode evidence blocked

Structured gate:

```text
python tools\fpga_uart_status_streamer.py --check
```

Command plan:

```text
python tools\fpga_uart_status_streamer.py --plan
```

## Purpose

I25-S02 adds a board-neutral UART transmitter to `cpu_v01_fpga_top`. The
streamer serializes the I25-S01 `32-byte` debug/status packet on `uart_tx_o`
at `115200` baud by default, using 8N1 framing. It samples existing status
signals and does not backpressure `retire_ready` or change architectural retire
behavior.

The default build assumes a 25 MHz first-test clock. Testbenches override the
clock and baud parameters to make UART activity observable quickly in
simulation. The board procedure decodes packets with the I25-S01 helper:

```text
python tools\fpga_debug_status_packet.py --check
```

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_top.sv` | Adds `uart_tx_o`, I25-S01 packet assembly, and `cpu_v01_fpga_uart_status_streamer`. |
| `rtl/cpu_v01_fpga_top_tb.sv` | Fetch-disabled idle UART smoke check. |
| `rtl/cpu_v01_fpga_first_test_tb.sv` | First-test pass UART smoke check. |
| `src/cpu_v01/fpga_uart_status.py` | Structured I25-S02 streamer profile and validator. |
| `tools/fpga_uart_status_streamer.py` | CLI wrapper for checking, JSON, and command plan output. |
| `tests/conformance/test_i25_s02_fpga_uart_status_streamer.py` | Conformance tests for profile, RTL tokens, docs, and CLI output. |
| `docs/implementation/fpga-uart-status-streamer.md` | This implementation note. |

## UART Profile

| Field | Value |
| --- | --- |
| Output | `uart_tx_o` |
| Framing | 8N1, idle high, start bit low, LSB-first data, stop bit high |
| Baud | `115200` |
| Clock | 25 MHz first-test clock |
| Packet interval | 25,000 cycles between packet starts after reset release |
| Packet format | I25-S01 magic `0xC501`, version `1`, 32-byte little-endian payload |
| Build identity | `DEBUG_BUILD_ID = 32'h2501_C0DE` |

## Expected Packets

| Scenario | Required state | Required flags | Expected fields |
| --- | --- | --- | --- |
| `idle` | `idle_or_reset` | `reset_observed`, `core_idle` | `pc_cell`, `build_id`, and `sequence` are present. |
| `pass` | `first_pass` | `retire_valid`, `pass_led`, `heartbeat` | `retire_count >= 8`, `fault_code == 0`, and `trap_cause == 0`. |
| `fault` | `failed` | `fault_valid`, `fail_led` | `fault_code != 0`, `trap_cause != 0`, and `sequence` increments. |

## Simulation

Run the Verilator command plan or the focused checks:

```text
python tools\fpga_uart_status_streamer.py --plan
python tools\fpga_uart_status_streamer.py --check
```

The reset wrapper testbench proves the idle packet path by holding fetch
disabled and checking that `uart_tx_o` leaves idle. The first-test smoke
testbench proves the pass packet path while the firmware reaches `first_pass`.
Fault packet decode is a board and future fault-injection procedure: capture
the UART stream when `fail_led_o` or `status_fault_valid_o` asserts, decode the
latest packet, and archive it with the failure evidence.

## Board Procedure

1. Run I24-S04 programming evidence first; this story does not replace the
   board pass/fail evidence gate.
2. Connect the board UART at `115200` baud, 8N1.
3. Reset the board and capture several packets from `uart_tx_o`.
4. Decode packet bytes with the I25-S01 layout and verify `idle_or_reset`,
   `first_pass`, or `failed` as appropriate.
5. Preserve UART logs with the I25-S05 debug-evidence gate.

## Non-Interference

- The streamer samples the I25-S01 packet bus and never changes `retire_ready`.
- UART transmit state is reset/debug sideband state only.
- Missing UART capture does not change CPU architectural state; it only blocks
  debug-evidence closure.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| FPGA top streams packets over UART. | Met by `uart_tx_o` and `cpu_v01_fpga_uart_status_streamer`. |
| Baud rate is documented. | Met by the 115200 baud profile and board procedure. |
| Idle, pass, and fault packets are specified. | Met by the expected-packets table. |
| Simulation proves UART activity. | Met by idle and pass testbench checks. |
| Architectural retire behavior is unchanged. | Met by the `retire_ready` non-interference rule. |

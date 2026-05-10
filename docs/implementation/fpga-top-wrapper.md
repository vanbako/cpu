# FPGA Top Wrapper

Story: I23-S02

Status: Implemented board-neutral wrapper profile

This story adds the first board-neutral FPGA wrapper around the integrated
`cpu_v01_core`. The wrapper started as a reset and observation shell: it
synchronizes board reset, instantiates the integrated core, exposes
status/debug pins, and now defaults to the I23-S04 first-test firmware path.
Later I30 slices add the SoC MMIO decoder and peripheral handoffs while
preserving the reset-smoke mode.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_top.sv` | Board-neutral FPGA top wrapper around `cpu_v01_core` and the FPGA-local memory adapters. |
| `rtl/cpu_v01_fpga_top_tb.sv` | Reset-smoke testbench for synchronized reset, status outputs, and fetch-disabled idle behavior. |
| `src/cpu_v01/fpga_top.py` | Structured port projection and source/documentation validator. |
| `tools/fpga_top_wrapper.py` | CLI wrapper for checking or rendering the FPGA top projection. |
| `tests/conformance/test_i23_s02_fpga_top_wrapper.py` | I23-S02 conformance coverage. |

## Command

```text
python tools\fpga_top_wrapper.py --check
```

Optional Verilator smoke command:

```text
verilator --binary --timing --top-module cpu_v01_fpga_top_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv
```

## Wrapper Boundary

The wrapper exposes only board-neutral signals:

- `board_clk_i`;
- active-low asynchronous `board_reset_n_i`;
- optional `debug_halt_request_i`;
- `uart_rx_i` for firmware UART receive;
- `uart_tx_o` for the shared firmware and I25-S02 debug/status packet stream;
- `pass_led_o`, `fail_led_o`, and `heartbeat_led_o`;
- reset, idle, retire, fault, and memory-port activity status outputs;
- low-width debug projections for reset PCC, PCC permissions, and reset SR.

`cpu_v01_fpga_top` contains a two-stage reset synchronizer. The synchronized
reset drives `cpu_v01_core` as `core_rst_n`.

## Current Idle Attachments

The wrapper keeps a fetch-disabled reset-smoke mode for I23-S02 regression
coverage while the default path runs the I23-S04 first-test firmware:

- `cpu_v01_core` defaults to `.ENABLE_FETCH(1'b1)` through the wrapper
  parameter;
- `cpu_v01_fpga_top_tb` overrides `.ENABLE_FETCH(1'b0)` to preserve the reset
  observation check;
- instruction, data, and tag-memory ports connect through the FPGA BRAM adapters
  and SoC decoder added by I23-S03 and I30-S02;
- software interrupt and event inputs remain tied idle;
- timer and external interrupt inputs are now driven by the I30-S03 timer,
  UART, and GPIO/status handoffs;
- retire is held ready so future firmware smoke status can observe retire
  packets without another wrapper contract change.

I25-S02 adds the optional UART debug/status stream. It serializes the I25-S01
32-byte status packet into the I30-S03 low-dominant UART TX combine and is
checked with `python tools\fpga_uart_status_streamer.py --check`.

The runtime pass status is now `pass_sticky_q && !fault_sticky_q`, set by the
I23-S04 retire threshold. The reset-smoke testbench checks that pass remains
low when fetch is disabled.

## Deferrals

- I23-S05 adds board constraints, synthesis, implementation, and timing gates.
- I23-S06 captures board programming and first-pass evidence.
- I25-S02 owns the UART status streamer baud/packet procedure.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The FPGA top instantiates `cpu_v01_core`. | Met by `rtl/cpu_v01_fpga_top.sv`. |
| Board reset is synchronized before reaching the core. | Met by the two-stage reset synchronizer and reset-smoke testbench. |
| Interrupts/events are deterministic. | Met by constant idle software/event connections plus I30-S03 timer and external interrupt handoffs. |
| Status/debug pins are visible at the wrapper boundary. | Met by LED, fault, retire, reset, PCC, and SR outputs. |
| Memory integration remains explicit future work. | Met for the top boundary; I23-S03 owns the adapter behavior. |

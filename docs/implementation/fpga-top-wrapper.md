# FPGA Top Wrapper

Story: I23-S02

Status: Implemented board-neutral wrapper profile

This story adds the first board-neutral FPGA wrapper around the integrated
`cpu_v01_core`. The wrapper is intentionally a reset and observation shell: it
synchronizes board reset, instantiates the integrated core, ties interrupts and
events to deterministic idle values, exposes status/debug pins, and holds the
memory side idle until I23-S03 adds BRAM adapters.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_top.sv` | Board-neutral FPGA top wrapper around `cpu_v01_core`. |
| `rtl/cpu_v01_fpga_top_tb.sv` | Reset-smoke testbench for synchronized reset, status outputs, and idle memory behavior. |
| `src/cpu_v01/fpga_top.py` | Structured port projection and source/documentation validator. |
| `tools/fpga_top_wrapper.py` | CLI wrapper for checking or rendering the FPGA top projection. |
| `tests/conformance/test_i23_s02_fpga_top_wrapper.py` | I23-S02 conformance coverage. |

## Command

```text
python tools\fpga_top_wrapper.py --check
```

Optional Verilator smoke command:

```text
verilator --binary --timing --top-module cpu_v01_fpga_top_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv
```

## Wrapper Boundary

The wrapper exposes only board-neutral signals:

- `board_clk_i`;
- active-low asynchronous `board_reset_n_i`;
- optional `debug_halt_request_i`;
- `pass_led_o`, `fail_led_o`, and `heartbeat_led_o`;
- reset, idle, retire, fault, and memory-port activity status outputs;
- low-width debug projections for reset PCC, PCC permissions, and reset SR.

`cpu_v01_fpga_top` contains a two-stage reset synchronizer. The synchronized
reset drives `cpu_v01_core` as `core_rst_n`.

## Current Idle Attachments

I23-S02 does not claim a runnable ROM path. To keep the wrapper elaborable
before BRAM integration:

- `cpu_v01_core` is instantiated with `.ENABLE_FETCH(1'b0)`;
- instruction, data, and tag-memory ready inputs are tied ready;
- instruction, data, and tag responses are tied invalid or zero;
- timer, software, external interrupt, and event inputs are tied idle;
- retire is held ready so future firmware smoke status can observe retire
  packets without another wrapper contract change.

The reset-smoke status treats `reset_observed && core_idle && !fault_sticky_q`
as `pass_led_o`. I23-S04 owns replacing that reset-idle pass indication with
the dedicated first FPGA smoke firmware pass/fail contract.

## Deferrals

- I23-S03 adds BRAM instruction ROM, data RAM, and tag RAM adapters.
- I23-S04 adds the tiny smoke firmware and final pass/fail status source.
- I23-S05 adds board constraints, synthesis, implementation, and timing gates.
- I23-S06 captures board programming and first-pass evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The FPGA top instantiates `cpu_v01_core`. | Met by `rtl/cpu_v01_fpga_top.sv`. |
| Board reset is synchronized before reaching the core. | Met by the two-stage reset synchronizer and reset-smoke testbench. |
| Interrupts/events are deterministically idle. | Met by constant idle event and interrupt connections. |
| Status/debug pins are visible at the wrapper boundary. | Met by LED, fault, retire, reset, PCC, and SR outputs. |
| Memory integration remains explicit future work. | Met by idle response ties and I23-S03 deferral. |

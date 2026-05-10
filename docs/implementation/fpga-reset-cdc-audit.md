# FPGA Reset CDC Audit

Story: I28-S02

Structured gate:

```text
python tools\fpga_reset_cdc.py --check
```

Related gates:

```text
python tools\fpga_clock_profiles.py --check
python tools\fpga_top_wrapper.py --check
python tools\fpga_uart_status_streamer.py --check
```

## Scope

I28-S02 audits the reset and clock-domain crossings visible in the FPGA top
wrapper and debug paths. It does not change the current RTL clocking model:
`cpu_v01_fpga_top` still runs in the single `board_clk_i` domain selected by
`debug_direct_25mhz`. The release PLL profile remains blocked until a wrapper,
lock/reset sequencing, generated-clock SDC, and Gowin timing evidence exist.

## Audit Items

| Item | Kind | Domain | Status | Handling |
| --- | --- | --- | --- | --- |
| `board_clk_i` | source clock | `board_clk_i` | `implemented_current_domain` | Single current domain constrained by I24-S02 and named by I28-S01. |
| `board_reset_n_i` | async reset input | `board_clk_i` | `implemented_two_stage_sync_release` | Asynchronous assert and synchronized release through `RESET_SYNC_STAGES`. |
| `core_rst_n` | synchronized reset | `board_clk_i` | `implemented_same_domain_fanout` | Reset fanout to the core, BRAM adapters, UART status streamer, and wrapper status flops. |
| `debug_halt_request_i` | async debug input | `board_clk_i` | `documented_open_issue` | Currently passed through to `cpu_v01_core`; tie low for first board smoke or add a two-flop synchronizer before board use. |
| `uart_tx_o` | shared UART output | `board_clk_i` | `implemented_same_domain_output` | Idle-high firmware/status TX combine in the current clock domain. |
| `uart_rx_i` | async UART input | `board_clk_i` | `implemented_two_stage_sync` | Board UART RX enters the two-flop synchronizer inside `cpu_v01_fpga_uart_mmio` before RX sampling. |
| `status_debug_outputs` | debug/status outputs | `board_clk_i` | `implemented_same_domain_outputs` | LED, fault, retire-count, PCC, and SR projections leave the current domain as outputs only. |
| `release_pll_domain` | generated clock domain | `cpu_clk` | `blocked_until_pll_wrapper` | `release_pll_25mhz` is defined by I28-S01 but no active PLL wrapper or generated-clock SDC is selected. |

## RTL Evidence

The gate checks these current RTL facts:

- `board_reset_n_i` uses `always_ff @(posedge board_clk_i or negedge board_reset_n_i)`;
- `reset_sync_q <= {reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1}` implements the release shift register;
- `core_rst_n` is assigned from `reset_sync_q[RESET_SYNC_STAGES-1]`;
- core, BRAM adapters, UART MMIO, and UART status streamer use `.rst_n(core_rst_n)`;
- the status UART instance uses `.clk(board_clk_i)`;
- `uart_rx_i` reaches `cpu_v01_fpga_uart_mmio`, where `uart_rx_meta_q` and
  `uart_rx_sync_q` synchronize the input before sampling;
- `uart_tx_o`, LED/status outputs, and debug projections are current-domain
  output paths.

## Open Issues

- `debug_halt_request_i` is raw in `cpu_v01_fpga_top` and must be tied low or
  synchronized before it is board-driven.
- `release_pll_25mhz` has no RTL PLL wrapper, lock signal, or active
  `create_generated_clock` SDC yet.
- Any future loader inputs beyond `uart_rx_i` must add explicit synchronizers
  before it enters the SoC clock domain.

## Command Plan

```text
python tools\fpga_clock_profiles.py --check
python tools\fpga_top_wrapper.py --check
python tools\fpga_uart_status_streamer.py --check
verilator --lint-only --timing --top-module cpu_v01_fpga_top_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv
python tools\fpga_reset_cdc.py --check
```

The Verilator line is a lint/elaboration companion to the structured audit.
The default I23-S02 binary smoke command remains owned by
`python tools\fpga_top_wrapper.py --check`.

## Handoffs

- I28-S03 should flag unconstrained generated clocks and missing reset/clock
  report evidence.
- I28-S04 should keep frequency sweeps on `debug_direct_25mhz` until release
  PLL reset handling is implemented.
- I28-S05 should include the selected clock profile and reset/CDC audit in the
  reproducible build profile.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Async inputs are documented. | Met by `board_reset_n_i`, `debug_halt_request_i`, and synchronized `uart_rx_i` evidence. |
| Reset synchronizers are documented and checked. | Met by `RESET_SYNC_STAGES`, `reset_sync_q`, and `core_rst_n` checks. |
| UART/debug crossings are audited. | Met by same-domain `uart_tx_o`, synchronized `uart_rx_i`, and debug/status output items plus the raw halt open issue. |
| Generated-clock domains are documented. | Met by the blocked `release_pll_25mhz` / `cpu_clk` domain. |
| Focused RTL checks are named. | Met by the top-wrapper and lint/elaboration command plan. |

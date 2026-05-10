# FPGA SoC Loader Handoff

Story: I30-S04

Status: Draft RTL integration slice

## Command

Validate the loader handoff contract:

```text
python tools\fpga_soc_loader_handoff.py --check
```

List rules:

```text
python tools\fpga_soc_loader_handoff.py --rules
```

Lint the focused RTL testbench:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_top_loader_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_loader_tb.sv
```

## Scope

I30-S04 integrates the I26-S04 board-safe loader handoff into
`cpu_v01_fpga_top`. The handoff is a synchronous SoC-domain interface for a
UART or future JTAG bridge; raw transport synchronization remains owned by the
transport block. This story wires the bounded memory side, status reporting,
and UART arbitration that the top-level closure matrix assigned to I30-S04.

Required upstream gates:

- `python tools\fpga_program_loader.py --check`
- `python tools\fpga_soc_top_peripherals.py --check`
- `python tools\fpga_uart_status_streamer.py --check`
- `python tools\fpga_debug_status_packet.py --check`

## Loader Interface

The top exposes:

| Signal | Direction | Semantics |
| --- | --- | --- |
| `loader_req_valid_i` / `loader_req_ready_o` | input/output | One-cell synchronous loader request handshake. |
| `loader_req_write_i` | input | Must be high; non-write traffic is `MALFORMED`. |
| `loader_req_addr_i` | input | CPU cell address for the target data RAM cell. |
| `loader_req_wdata_i` | input | 24-bit CPU cell payload to install. |
| `loader_req_tag_i` | input | Must be zero; tag-bearing traffic is rejected as `TAG_POLICY`. |
| `loader_uart_tx_i` | input | Idle-high loader UART status leg. |
| `loader_status_valid_o` / `loader_status_code_o` | output | Latched status visible to debug/status evidence. |

`cpu_v01_fpga_soc_loader_handoff` accepts only writes inside the I26-S04
`data_ram` target:

```text
0x00010000 .. 0x00011000
```

Accepted writes update `cpu_v01_fpga_data_ram` and clear the matching
`cpu_v01_fpga_tag_ram` sidecar bit. The handoff never targets
`instruction_rom`, never installs trusted tags, and never accepts out-of-window
payloads.

## Status And Arbitration

The RTL status codes mirror I26-S04:

| Code | Name | Condition |
| --- | --- | --- |
| `0x0000` | `OK` | Bounded untagged `data_ram` write accepted. |
| `0x2603` | `LOAD_STATUS_BAD_TARGET` | Address is outside the loader `data_ram` window, including `instruction_rom`. |
| `0x2605` | `TAG_POLICY` | `loader_req_tag_i` is asserted. |
| `0x2607` | `MALFORMED` | Request is not a write. |

Failures latch into `loader_status_code_o`, set the debug/status fault flag,
and drive the debug/status packet fault-code field. UART arbitration extends the
I30-S03 policy:

```text
assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;
```

All three UART sources are idle-high and low-dominant, so firmware UART,
debug/status packets, or loader status can pull the shared TX output low.
I32-S01 still owns the interactive monitor command names and host protocol.

## Testbench

`rtl/cpu_v01_fpga_top_loader_tb.sv` checks:

- a bounded `data_ram` loader write succeeds;
- the matching `tag_ram` bit is cleared;
- an `instruction_rom` target returns `LOAD_STATUS_BAD_TARGET`;
- tag-bearing traffic returns `TAG_POLICY` without writing RAM;
- non-write traffic returns `MALFORMED`;
- loader failure status reaches debug/status outputs;
- `loader_uart_tx_i` participates in UART TX arbitration.

## Handoffs

- I30-S05 proves the loader handoff together with firmware UART, timer,
  syscall, and GPIO smoke.
- I32-S01 owns interactive monitor command naming and host protocol expansion.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Loader traffic is bounded. | Met by the `data_ram` window check and `LOAD_STATUS_BAD_TARGET`. |
| Loader traffic cannot overwrite protected/tag state outside its manifest. | Met by no `instruction_rom` mux, data RAM range gating, tag-bearing rejection, and tag sidecar clear-only behavior. |
| Loader status is visible over debug/UART. | Met by `loader_status_code_o`, debug/status packet fault-code selection, and `loader_uart_tx_i` arbitration. |
| Firmware/status UART arbitration remains deterministic. | Met by the idle-high low-dominant three-way UART TX combine. |
| Focused wrapper checks exist. | Met by `cpu_v01_fpga_top_loader_tb` and `python tools\fpga_soc_loader_handoff.py --check`. |

# FPGA SoC Top Data/MMIO Decoder

Story: I30-S02

Status: Draft RTL integration slice

## Command

Validate the decoder contract:

```text
python tools\fpga_soc_top_decoder.py --check
```

List decode windows:

```text
python tools\fpga_soc_top_decoder.py --windows
```

Lint the focused RTL testbench:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_top_soc_decoder_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_soc_decoder_tb.sv
```

## Scope

I30-S02 replaces the direct `cpu_v01_core` data-memory connection to
`cpu_v01_fpga_data_ram` with `cpu_v01_fpga_soc_dmem_decoder`. The decoder
selects the BRAM data window, each I27-S01 MMIO peripheral window, or a
deterministic reserved/fault response.

Required upstream gates:

- `python tools\fpga_soc_top_closure.py --check`
- `python tools\fpga_soc_platform.py --check`
- `python tools\fpga_uart_mmio.py --check`
- `python tools\fpga_timer_mmio.py --check`
- `python tools\fpga_gpio_status.py --check`

## Decode Windows

| Target | Base | End | Routed surface |
| --- | ---: | ---: | --- |
| `data_ram` | `0x00010000` | `0x00011000` | `cpu_v01_fpga_data_ram` and `tag_ram` sidecar |
| `uart` | `0x00F00000` | `0x00F00100` | `cpu_v01_fpga_uart_mmio` |
| `timer` | `0x00F00100` | `0x00F00200` | `cpu_v01_fpga_timer_mmio` |
| `gpio_status` | `0x00F00200` | `0x00F00300` | `cpu_v01_fpga_gpio_status` |
| `interrupt_controller` | `0x00F00300` | `0x00F00400` | `cpu_v01_fpga_irq_mmio` |
| `system_identity` | `0x00F00400` | `0x00F00500` | `cpu_v01_fpga_system_identity_mmio` |
| `video_display` | `0x00F00500` | `0x00F00600` | `cpu_v01_fpga_video_mmio` |

The rest of `platform_devices` and any unmapped top-level cell address decode
as reserved. Reserved reads return `EXC_ACCESS_FAULT`. Reserved writes are
accepted as deterministic no-ops because the current core data-write channel has
no write-response fault phase.

## Tag Sidecar

`tag_ram` remains paired only with `data_ram`. The top gates `tagmem_req_valid`
with `tagmem_req_in_data_ram`; non-RAM tag reads return an invalid tag through a
one-cycle bypass and non-RAM tag writes are suppressed. This prevents MMIO
stores from creating capability sidecar tags while preserving `CLC` reads of
device payloads as invalid-tag capabilities.

## Integrated Peripherals

The decoder now reaches the existing UART, timer, GPIO/status, and
`video_display` RTL blocks.
I30-S02 intentionally leaves their board-facing ownership limited:

- `uart_tx_o` is still driven by the I25-S02 debug/status streamer.
- `timer_interrupt_pending` remains tied off at the core input.
- LEDs remain driven by the first-test sticky pass/fail and retire heartbeat.
- I35-S04 owns video control/status semantics and `video_vblank` interrupt
  routing.

I30-S03 owns those mux, interrupt, and board pin handoffs.

## Testbench

`rtl/cpu_v01_fpga_top_soc_decoder_tb.sv` checks:

- RAM write/read routing through the decoder;
- UART status, timer compare, GPIO/status, video_display,
  interrupt-controller, and system-identity MMIO reads;
- reserved-window and invalid-length `EXC_ACCESS_FAULT` responses;
- selection of one MMIO target without asserting the RAM request.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| CPU data requests no longer connect directly to `cpu_v01_fpga_data_ram`. | Met by `cpu_v01_fpga_soc_dmem_decoder`. |
| RAM accesses and each I27-S01 MMIO peripheral window are decoded. | Met by the original I27 windows plus the I35-S04 `video_display` window and focused testbench. |
| Reserved/fault windows behave deterministically. | Met by reserved read `EXC_ACCESS_FAULT` and no-op write policy. |
| `tag_ram` sidecar updates remain paired with `data_ram`. | Met by `tagmem_req_in_data_ram` gating and invalid-tag bypass. |
| I30-S03/I30-S05 handoffs remain explicit. | Met by the integrated-peripheral handoff notes. |

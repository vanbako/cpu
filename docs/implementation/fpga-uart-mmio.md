# FPGA UART MMIO

Story: I27-S02

Command:

```text
python tools\fpga_uart_mmio.py --check
```

Related gates:

```text
python tools\fpga_soc_platform.py --check
python tools\fpga_debug_status_packet.py --check
python tools\fpga_uart_status_streamer.py --check
```

## Scope

I27-S02 adds the firmware-visible UART TX/RX MMIO contract reserved by the
I27-S01 `uart` peripheral at `0x00F00000`. This is distinct from the I25-S02
debug/status UART streamer: the status streamer continues to emit I25-S01
packets, while this block lets firmware transmit status text or loader packets
and receive bounded commands through explicit registers.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_uart_mmio.py` | Executable register model, state-machine helper, JSON profile, and validator. |
| `tools/fpga_uart_mmio.py` | CLI for `--check`, `--json`, `--registers`, `--plan`, and `--demo`. |
| `rtl/cpu_v01_fpga_uart_mmio.sv` | Cell-addressed UART TX/RX MMIO block with bounded TX/RX FIFOs. |
| `rtl/cpu_v01_fpga_uart_mmio_tb.sv` | Standalone wrapper simulation for TX, RX, IRQ, overrun, and clear-errors behavior. |
| `tests/conformance/test_i27_s02_fpga_uart_mmio.py` | Story conformance tests for model, docs, CLI, and RTL tokens. |

The top-level SoC-shell arbitration is intentionally explicit rather than
hidden here: a later shell must decide whether firmware UART TX, the I25-S02
status streamer, or a board mux owns the physical UART pin at any instant.
Until that shell exists, `cpu_v01_fpga_uart_mmio` is a standalone RTL peripheral
validated against the I27-S01 address map.

## Register Map

All addresses are CPU cell addresses under the I27-S01 `platform_devices`
window. Values are little-endian within the low byte of the 24-bit CPU cell
unless noted.

| Register | Cell | Access | Reset | Semantics |
| --- | --- | --- | --- | --- |
| `UART_TXDATA` | `0x00F00000` | write-only | `0x00` | Write low byte to queue one transmitted byte. |
| `UART_RXDATA` | `0x00F00001` | read-only | `0x00` | Read and pop the oldest received byte, or return zero if empty. |
| `UART_STATUS` | `0x00F00002` | read-only | `TX_READY \| TX_EMPTY` | Poll TX/RX readiness, sticky errors, and interrupt pending state. |
| `UART_CONTROL` | `0x00F00003` | read-write | `0x00` | Enable TX/RX ready interrupts and clear sticky errors. |
| `UART_BAUD_DIV` | `0x00F00004` | read-write | `217` | 24-bit board-clock divisor for 25 MHz / 115200 baud by default. |

## Status Bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | `TX_READY` | TX FIFO can accept at least one byte. |
| 1 | `TX_EMPTY` | TX FIFO is empty and the serializer is idle. |
| 2 | `RX_VALID` | RX FIFO contains at least one byte. |
| 3 | `RX_OVERRUN` | A received byte arrived while the RX FIFO was full. |
| 4 | `FRAME_ERROR` | RX stop-bit validation failed. |
| 5 | `TX_IRQ_PENDING` | `TX_READY` is true and TX ready interrupt is enabled. |
| 6 | `RX_IRQ_PENDING` | `RX_VALID` is true and RX ready interrupt is enabled. |
| 7 | `TX_OVERRUN` | Firmware wrote `UART_TXDATA` while the TX FIFO was full. |

## Control Bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | `TX_IRQ_ENABLE` | Raise `uart_tx_ready` while TX can accept data. |
| 1 | `RX_IRQ_ENABLE` | Raise `uart_rx_ready` while RX data is queued. |
| 2 | `CLEAR_ERRORS` | Write-one action that clears `RX_OVERRUN`, `FRAME_ERROR`, and `TX_OVERRUN`. |

`UART_CONTROL` stores only the interrupt-enable bits; `CLEAR_ERRORS` is a
write action and reads back as zero.

## Bounded Commands

RX command input is deliberately bounded. The RTL and Python model use a
four-byte RX FIFO, preserve existing queued bytes on overflow, and set
`RX_OVERRUN` instead of accepting unbounded command input. I26-S04 can build a
loader protocol on top of this by limiting command frame size, checking the
overrun bit before accepting a frame, and reporting success/failure through
either firmware UART TX or the existing I25-S02 status packet path.

TX output is also bounded. Firmware can poll `TX_READY` or enable
`uart_tx_ready`; writes while the TX FIFO is full set `TX_OVERRUN` and drop the
new byte.

## Wrapper And Simulation Checks

The Verilator command inventory is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_uart_mmio_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_uart_mmio_tb.sv
```

The standalone testbench covers:

- reset status with `TX_READY` and `TX_EMPTY`;
- `UART_TXDATA` causing `uart_tx_o` to leave idle;
- serial RX injection through `uart_rx_i` and readback through `UART_RXDATA`;
- `uart_tx_ready` and `uart_rx_ready` interrupt outputs;
- RX FIFO overrun and `CLEAR_ERRORS`.

The FPGA wrapper follow-up is still a real integration point: the future SoC
shell must arbitrate the single board UART TX path if both firmware UART output
and the I25-S02 debug/status stream are enabled.

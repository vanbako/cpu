# FPGA SoC Platform

Story: I27-S01

Status: Draft platform and MMIO map

## Command

Validate the profile:

```text
python tools\fpga_soc_platform.py --check
```

Print the profile:

```text
python tools\fpga_soc_platform.py --json
```

List peripherals:

```text
python tools\fpga_soc_platform.py --list
```

List registers for one peripheral:

```text
python tools\fpga_soc_platform.py --registers uart
```

## Scope

I27-S01 defines the minimal FPGA SoC shell profile around `cpu_v01_fpga_top`.
It assigns a firmware-visible MMIO map for UART, timer, GPIO/status, interrupt
pending/enable, reset cause, and image identity registers. It does not
implement the peripherals in RTL; I27-S02, I27-S03, and I27-S04 own those
implementations.

Required upstream gates:

- `python tools\fpga_first_test_profile.py --check`
- `python tools\fpga_first_board_archive.py --check`

The physical board pass remains blocked until I24-S05 evidence exists. This
profile is still useful before that because it prevents later UART, timer, and
loader work from inventing conflicting addresses.

## Address Window

The SoC MMIO window is the existing `platform_devices` region:

| Field | Value |
| --- | --- |
| Base | `0x00F00000` |
| End | `0x00F01000` |
| Size | `0x1000` cells |
| Memory type | Device ordered |

The window ends exactly at the existing secondary mailbox base, so the SoC
peripherals do not overlap ROM, RAM, or mailbox regions.

## Peripherals

| Peripheral | Base | Size | Owner | Purpose |
| --- | --- | --- | --- | --- |
| `uart` | `0x00F00000` | `0x100` | I27-S02 | UART TX/RX MMIO and future bounded loader command transport. |
| `timer` | `0x00F00100` | `0x100` | I27-S03 | 48-bit timer, compare register, and timer interrupt. |
| `gpio_status` | `0x00F00200` | `0x100` | I27-S04 | LEDs, board inputs, status override, and debug-status selection. |
| `interrupt_controller` | `0x00F00300` | `0x100` | I27-S01 | Pending, enable, acknowledge, and simulation force registers. |
| `system_identity` | `0x00F00400` | `0x100` | I27-S01 | Reset cause, build identity, and selected image SHA-256. |

## Register Summary

| Peripheral | Registers |
| --- | --- |
| `uart` | `UART_TXDATA`, `UART_RXDATA`, `UART_STATUS`, `UART_CONTROL`, `UART_BAUD_DIV` |
| `timer` | `TIMER_VALUE`, `TIMER_COMPARE`, `TIMER_CONTROL`, `TIMER_STATUS` |
| `gpio_status` | `GPIO_OUT`, `GPIO_IN`, `GPIO_DIR`, `STATUS_LEDS`, `DEBUG_STATUS_SELECT` |
| `interrupt_controller` | `IRQ_PENDING`, `IRQ_ENABLE`, `IRQ_ACK`, `IRQ_FORCE` |
| `system_identity` | `RESET_CAUSE`, `BUILD_ID_LO`, `BUILD_ID_HI`, `IMAGE_SHA256_0` through `IMAGE_SHA256_5` |

## Interrupt Lines

The first SoC shell exposes four local interrupt lines:

| Line | Source | Consumer |
| --- | --- | --- |
| `uart_rx_ready` | UART receive FIFO transitioned non-empty. | I27-S02 and later loader path. |
| `uart_tx_ready` | UART transmit FIFO can accept data. | I27-S02 firmware polling or interrupt mode. |
| `timer_compare` | Timer reached `TIMER_COMPARE` while enabled. | I27-S03 timer interrupt smoke. |
| `gpio_status` | GPIO/status edge or software force. | I27-S04 board diagnostic path. |

The interrupt controller presents `IRQ_PENDING`, `IRQ_ENABLE`, `IRQ_ACK`, and
`IRQ_FORCE` as 16-bit cells. `IRQ_FORCE` is for simulation and board-debug
fixtures; production firmware should use real peripheral sources.

## Identity Registers

`RESET_CAUSE` is a sticky write-one-to-clear register. It records power-on,
button, loader, and watchdog reset causes. The `BUILD_ID_*` registers expose a
96-bit build identity chosen by the bitstream flow.

`IMAGE_SHA256_0` through `IMAGE_SHA256_5` expose the selected I26 program-image
hash as five 48-bit cells plus one 16-bit tail. I26-S03 records the same
`image_sha256` in rebuild or memory-update evidence, and I26-S04 must preserve
that identity when adding a board-safe loader.

## Non-Goals

- External DDR controller or DDR calibration policy.
- Cache-coherent interconnect or fabric links.
- DMA or bus mastering.
- Multicore startup.
- The program loader protocol, which remains with I26-S04 after I27-S02 exists.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| UART, timer, GPIO/status, interrupt, reset cause, and image identity registers are assigned. | Met. |
| MMIO ranges fit inside `platform_devices` and do not overlap existing regions. | Met. |
| Interrupt pending/enable/ack semantics are reserved. | Met. |
| I27-S02, I27-S03, and I27-S04 implementation ownership is explicit. | Met. |
| The profile validates through `python tools\fpga_soc_platform.py --check`. | Met. |

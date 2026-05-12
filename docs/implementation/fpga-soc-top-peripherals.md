# FPGA SoC Top Peripheral Handoffs

Story: I30-S03

Status: Draft RTL integration slice

## Command

Validate the top-level peripheral handoff contract:

```text
python tools\fpga_soc_top_peripherals.py --check
```

List handoffs:

```text
python tools\fpga_soc_top_peripherals.py --handoffs
```

Lint the focused RTL testbench:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_top_soc_peripherals_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv
```

## Scope

I30-S03 wires the I27-S02 UART, I27-S03 timer, I27-S04 GPIO/status block,
interrupt-controller aggregate, and system identity block through
`cpu_v01_fpga_top`. I30-S02 already routes CPU data requests to these MMIO
windows; this story closes the board-visible and core-visible handoff points.
I35-S04 extends the aggregate with `video_vblank`.

Required upstream gates:

- `python tools\fpga_soc_top_decoder.py --check`
- `python tools\fpga_soc_platform.py --check`
- `python tools\fpga_uart_mmio.py --check`
- `python tools\fpga_timer_mmio.py --check`
- `python tools\fpga_gpio_status.py --check`
- `python tools\fpga_reset_cdc.py --check`

## Handoffs

| Handoff | RTL policy |
| --- | --- |
| Firmware UART RX | `uart_rx_i` is a top-level input and connects to `cpu_v01_fpga_uart_mmio.uart_rx_i`, which contains the two-flop RX synchronizer audited by I28-S02. |
| UART TX mux | `assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;` combines idle-high firmware UART, I25-S02 status UART output, and the I30-S04 loader UART leg with low-dominant behavior. |
| Timer interrupt | `timer_compare_irq` directly drives `timer_interrupt_pending`; firmware acknowledges through the I27-S03 `TIMER_STATUS` register. |
| External interrupts | `irq_pending_enabled` bits 0, 1, 3, and 4 aggregate UART RX ready, UART TX ready, GPIO/status, and video_vblank into `external_interrupt_pending` through `16'h001B`. |
| Video vblank interrupt | `video_vblank_irq` from `cpu_v01_fpga_video_mmio` maps to interrupt-controller bit 4. |
| GPIO/status LEDs | Firmware `STATUS_LEDS` requests OR with first-test sticky pass/fail and retire heartbeat status. |
| System identity | `RESET_CAUSE`, `BUILD_ID_*`, and `IMAGE_SHA256_*` remain readable through the `system_identity` MMIO window. |

## Interrupt Lines

The top-level interrupt order starts with I27-S01 and adds the I35-S04 video
line:

| Bit | Source | Core delivery |
| ---: | --- | --- |
| 0 | `uart_rx_ready` | External interrupt aggregate when enabled by IRQ MMIO. |
| 1 | `uart_tx_ready` | External interrupt aggregate when enabled by IRQ MMIO. |
| 2 | `timer_compare` | Direct timer interrupt input. |
| 3 | `gpio_status` | External interrupt aggregate when enabled by IRQ MMIO. |
| 4 | `video_vblank` | External interrupt aggregate when enabled by IRQ MMIO. |

## UART Policy

Both UART transmitters are idle-high. The top uses a low-dominant combine so
either firmware UART output or the debug/status streamer can pull the physical
TX line low. This preserves the first-test status packet path while exposing
firmware UART output. I30-S04 extends this combine with the loader UART leg and
keeps the loader handoff bounded by its own status policy.

## GPIO/status LEDs

`pass_led_o`, `fail_led_o`, and `heartbeat_led_o` remain compatible with the
first-test smoke:

- pass is asserted by first-test pass sticky status or firmware PASS;
- fail is asserted by first fault sticky status or firmware FAIL;
- heartbeat is asserted by retire progress or firmware HEARTBEAT.

The extra `status_leds_o` software bits remain internal until a later board
pin profile assigns additional outputs.

## Testbench

`rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv` checks:

- firmware UART RX reaches the UART MMIO instance;
- UART TX follows the low-dominant firmware/status combine;
- timer compare reaches `timer_interrupt_pending`;
- enabled non-timer interrupt bits, including video_vblank, reach
  `external_interrupt_pending`;
- GPIO/status LEDs combine with first-test sticky status;
- reset-idle status projections remain stable.

## Handoffs

- I30-S04 adds the loader UART leg to the firmware/status arbitration policy.
- I30-S05 proves firmware UART output, timer service, GPIO pass/fail, and
  syscall progress together.
- I35-S04 owns `cpu_v01_fpga_video_mmio` register semantics and vblank
  acknowledgement.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Firmware-visible UART TX/RX reaches the top. | Met by `uart_rx_i`, `uart_mmio_tx`, `status_uart_tx`, and the low-dominant `uart_tx_o` combine. |
| Timer interrupt pending and acknowledgement path are wired. | Met by `timer_compare_irq` to `timer_interrupt_pending`; acknowledgement remains the I27-S03 `TIMER_STATUS` path. |
| Video vblank reaches the existing interrupt path. | Met by `video_vblank` bit 4 and the external interrupt mask `16'h001B`. |
| GPIO/status LEDs are firmware-visible without losing first-test status. | Met by ORing firmware LED requests with first-test pass/fail/heartbeat. |
| Reset/build identity remains top-level readable. | Met by the `system_identity` MMIO handoff. |
| Focused wrapper checks exist. | Met by `cpu_v01_fpga_top_soc_peripherals_tb` and `python tools\fpga_soc_top_peripherals.py --check`. |

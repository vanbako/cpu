# FPGA SoC Smoke

Story: I27-S05

Command:

```text
python tools\fpga_soc_smoke.py --check
```

Related gates:

```text
python tools\fpga_soc_platform.py --check
python tools\fpga_uart_mmio.py --check
python tools\fpga_timer_mmio.py --check
python tools\fpga_gpio_status.py --check
python -m unittest tests.conformance.test_i18_s03_syscall_demo
python tools\fpga_smoke_corpus.py --check
```

## Scope

I27-S05 records the first minimal FPGA SoC shell smoke as a
`documented_blocker_run`. The smoke composes the completed I27 peripheral
contracts and the I18-S03 syscall demo, then preserves the remaining RTL
top-level blockers that prevent claiming an actual board pass.

The selected firmware image handoff is `syscall_trap.sys_pause_iret_fpga` from
the smoke corpus. The smoke evidence has four required observations:

| Observation | Source | Pass condition |
| --- | --- | --- |
| UART output | `UART_TXDATA` through the I27-S02 model. | Output contains `I27-S05`, `timer`, `syscall`, `GPIO`, and `pass`. |
| timer interrupt | `TIMER_COMPARE`, `TIMER_STATUS`, and the I14-S02 timer handler fixture. | Pending asserts before `STATUS_PENDING` acknowledgement and clears afterward; handler programs `TIMECMP=100`. |
| syscall/trap progress | I18-S03 syscall demo. | `SYS` trap enters, service returns `OK`, `IRET` returns to user mode. |
| GPIO pass/fail | `STATUS_LEDS` and `GPIO_IN` through the I27-S04 model. | Pass and heartbeat are set, fail is clear, and input change raises `gpio_status`. |

## Evidence Run

Use:

```text
python tools\fpga_soc_smoke.py --run
```

The JSON output includes:

- `uart_text` and `uart_bytes`;
- `timer_mmio_pending_before_ack` and `timer_mmio_pending_after_ack`;
- `timer_handler_entered`, `timer_handler_source`, and `timer_handler_new_timecmp`;
- `syscall_status`, `syscall_trap_entered`, and `syscall_final_user_mode`;
- `gpio_pass_led`, `gpio_fail_led`, `gpio_heartbeat_led`, and `gpio_interrupt_seen`;
- the blocker list copied into the run artifact.

## Documented Blockers

This is not yet a board pass. I30-S02 and I30-S03 close the data/MMIO decoder,
`timer_interrupt_pending`, UART firmware/status TX combine, UART RX, and
GPIO/status LED handoffs in `cpu_v01_fpga_top`. The remaining blockers are:

- I30-S05 top-level RTL firmware smoke has not yet proven this modeled I27-S05
  run under Verilator.
- I30-S04 bounded loader handoff is still absent from `cpu_v01_fpga_top`.
- Gowin bitstream and physical board evidence remain deferred to I31.

Because of those blockers, the first actual board run still needs the I30-S05
RTL smoke and I31 Gowin/bitstream evidence before it can claim combined UART
output, timer interrupt handling, syscall/trap progress, and GPIO pass/fail on
the Tang Mega 138K.

## Handoffs

- I26-S04 can now build a bounded loader protocol on top of I27-S02 UART RX
  and this smoke evidence contract.
- I30-S03 owns the MMIO peripheral handoffs needed to turn the original
  documented-blocker run into an RTL smoke candidate.
- I24-S05 remains the archive gate for physical board evidence once the shell
  is wired and a bitstream exists.

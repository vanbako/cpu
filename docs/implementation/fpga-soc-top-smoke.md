# FPGA SoC Top Smoke

Story: I30-S05

Status: Draft RTL smoke slice

## Command

Validate the top-level smoke contract:

```text
python tools\fpga_soc_top_smoke.py --check
```

Print the expected smoke run:

```text
python tools\fpga_soc_top_smoke.py --run
```

Build the focused RTL smoke executable:

```text
verilator --binary --timing --Mdir obj_dir\soc_top_smoke --top-module cpu_v01_fpga_top_soc_smoke_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_soc_smoke_tb.sv
```

Run the smoke executable:

```text
obj_dir\soc_top_smoke\Vcpu_v01_fpga_top_soc_smoke_tb.exe
```

## Scope

I30-S05 turns the I27-S05 modeled FPGA SoC smoke into a top-level RTL smoke
for `cpu_v01_fpga_top`. The fixture keeps the I30-S03 UART/timer/GPIO wiring
and the I30-S04 loader arbitration in one integrated run. It is still a
Verilator pre-board smoke, not a Gowin bitstream or physical-board pass.

Required upstream gates:

- `python tools\fpga_soc_smoke.py --check`
- `python tools\fpga_soc_top_peripherals.py --check`
- `python tools\fpga_soc_loader_handoff.py --check`

## Firmware Fixture

`rtl/cpu_v01_fpga_top_soc_smoke_tb.sv` runs the top with fetch enabled and
status UART disabled so the firmware UART leg is observable without packet
traffic. The harness seeds the reset ROM and initial register fixture, then the
core executes:

| Step | Firmware fixture | Checked evidence |
| --- | --- | --- |
| UART output | `ST48 C1, D0, D1` through `ST48 C1, D0, D4` | UART MMIO writes emit `I30S`, and `uart_tx_o` starts a frame. |
| timer interrupt | `ST48 C2, D7, D10`, `ST48 C2, D8, D11`, then `ST48 C2, D9, D12` | `timer_interrupt_pending` asserts before the firmware TIMER_STATUS acknowledgement and clears afterward. |
| syscall/trap | `SYS; PAUSE` with `IRET` at the TVC handler cell | `retire_packet` shows SYS trap entry, IRET trap-frame restore, and return to the post-SYS PAUSE slot. |
| GPIO pass/fail | `ST48 C3, D9, D13` | GPIO/status requests pass and heartbeat. Fail remains asserted from the preserved first-failure status. |
| first-failure status | SYS trap | `status_fault_valid_o` and `status_fault_code_o` preserve `EXC_SYSCALL_TRAP`. |

The seeded capability registers are testbench fixture state, not a new ABI.
They provide the top-level firmware with store authority for the UART, timer,
and GPIO/status MMIO windows while leaving the loader port idle-high and idle.
The integrated core treats the I27-S01 SoC window as device-ordered MMIO and
permits unaligned integer MMIO cells there so `ST48` can reach single-cell
register offsets such as `TIMER_STATUS` and `STATUS_LEDS`; normal RAM still
keeps the architectural integer-object alignment fault.

## Evidence Boundary

This story proves that the integrated top can run the firmware-visible MMIO and
trap paths together under Verilator. It does not claim:

- physical UART bytes on the Tang Mega 138K pins;
- Gowin timing, utilization, or bitstream evidence;
- full architectural interrupt delivery inside `cpu_v01_core`.

The timer check is therefore a top-level timer service/acknowledgement smoke:
the I30-S03 `timer_compare_irq` line reaches `timer_interrupt_pending`, and the
firmware fixture acknowledges through the I27-S03 `TIMER_STATUS` register. Full
core interrupt delivery remains outside this story's RTL scope.

## Handoffs

- I30-S06 archives the RTL sources, Verilator command/logs, decoded UART/status
  or probe traces, replay mapping, remaining blockers, and retest commands.
- I31-S01 can use this as the pre-board top-level evidence handoff before the
  first-pass Gowin build bundle.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Integrated top executes a firmware fixture. | Met by `cpu_v01_fpga_top_soc_smoke_tb` running `cpu_v01_fpga_top` with `ENABLE_FETCH=1`. |
| UART output is emitted. | Met by checked UART MMIO writes for `I30S` and an observed UART TX start bit. |
| Timer service is observed. | Met by timer pending assertion before firmware acknowledgement and clear after acknowledgement. |
| Syscall/trap return progresses. | Met by SYS trap entry, IRET restore, and return to the post-SYS PAUSE slot. |
| GPIO pass/fail evidence is driven. | Met by STATUS_LEDS pass and heartbeat while fail reflects preserved first-failure status. |
| First-failure status is preserved. | Met by `EXC_SYSCALL_TRAP` on `status_fault_code_o`. |
| Focused wrapper checks exist. | Met by `python tools\fpga_soc_top_smoke.py --check` and `rtl/cpu_v01_fpga_top_soc_smoke_tb.sv`. |

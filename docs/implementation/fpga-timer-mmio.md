# FPGA Timer MMIO

Story: I27-S03

Command:

```text
python tools\fpga_timer_mmio.py --check
```

Related gates:

```text
python tools\fpga_soc_platform.py --check
python -m unittest tests.conformance.test_i14_s02_kernel_handlers
python tools\rtl_core_control_trap.py --check
```

## Scope

I27-S03 adds the firmware-visible timer MMIO block reserved by the I27-S01
`timer` peripheral at `0x00F00100`. It provides a 48-bit free-running counter,
a 48-bit compare register, an interrupt-enable bit, one-shot mode, and
write-one-to-clear acknowledgement through `TIMER_STATUS`.

This slice exposes `timer_compare` as a level interrupt source for the later
SoC shell. It does not yet wire `cpu_v01_fpga_top.timer_interrupt_pending`; that
handoff belongs with the minimal SoC shell smoke in I27-S05, where handler
progress can be shown over GPIO or UART without changing the existing
first-test pass/fail behavior.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_timer_mmio.py` | Executable timer model, register profile, JSON output, and validator. |
| `tools/fpga_timer_mmio.py` | CLI for `--check`, `--json`, `--registers`, `--plan`, and `--demo`. |
| `rtl/cpu_v01_fpga_timer_mmio.sv` | Cell-MMIO 48-bit timer with compare, status, and interrupt output. |
| `rtl/cpu_v01_fpga_timer_mmio_tb.sv` | Standalone wrapper testbench for compare, ack, one-shot, and clear behavior. |
| `tests/conformance/test_i27_s03_fpga_timer_mmio.py` | Story conformance tests for model, docs, CLI, and RTL tokens. |

## Register Map

All addresses are CPU cell addresses under the I27-S01 `platform_devices`
window. The 48-bit logical registers use two 24-bit CPU cells on the data path:
cell 0 contains bits 23:0 and cell 1 contains bits 47:24.

| Register | Cell | Access | Width | Semantics |
| --- | --- | --- | --- | --- |
| `TIMER_VALUE` | `0x00F00100` | read-only | 48 | Free-running cycle counter while `ENABLE` is set. |
| `TIMER_COMPARE` | `0x00F00101` | read-write | 48 | Compare deadline that raises `timer_compare` at or after the value. |
| `TIMER_CONTROL` | `0x00F00102` | read-write | 4 | Enable counting, enable interrupt output, one-shot mode, and clear value/status. |
| `TIMER_STATUS` | `0x00F00103` | write-one-to-clear | 4 | Sticky `PENDING` and `OVERFLOW` bits; write `STATUS_PENDING` to acknowledge. |

## Control Bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | `ENABLE` | Increment `TIMER_VALUE` every SoC clock. |
| 1 | `IRQ_ENABLE` | Drive `timer_compare` while `PENDING` is set. |
| 2 | `ONESHOT` | Clear `ENABLE` after the first compare event. |
| 3 | `CLEAR_VALUE` | Write-one action that clears `TIMER_VALUE`, `PENDING`, and `OVERFLOW`. |

## Status Bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | `PENDING` / `STATUS_PENDING` | Timer value reached or passed `TIMER_COMPARE`. |
| 1 | `OVERFLOW` | The 48-bit counter wrapped. |

Firmware acknowledges the timer interrupt by writing `STATUS_PENDING` to
`TIMER_STATUS`. This clears the level interrupt without disturbing the compare
register, UART state, GPIO state, or first-test pass/fail latches.

## Firmware Contract

The intended programming sequence is:

1. Write a two-cell 48-bit `TIMER_COMPARE`.
2. Set `ENABLE` and, if interrupt delivery is desired, `IRQ_ENABLE`.
3. On handler entry, record visible progress through GPIO or UART.
4. Acknowledge by writing `STATUS_PENDING` to `TIMER_STATUS`.
5. Program the next compare value, or use `ONESHOT` for a single interrupt.

The interrupt source is the existing architectural timer source from I14-S02:
`timer_compare` maps to the kernel timer interrupt bit and cause value. I22-S05
already validates the integrated control/trap path that will consume
`timer_interrupt_pending` once the SoC shell wires this output.

## Wrapper And Simulation Checks

The Verilator command inventory is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_timer_mmio_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_timer_mmio_tb.sv
```

The standalone testbench covers:

- compare match raising `timer_interrupt_o`;
- firmware acknowledgement clearing `timer_pending_o`;
- two-cell `TIMER_VALUE` readback;
- `CLEAR_VALUE` resetting value and status;
- one-shot mode setting `PENDING` and clearing `ENABLE`.

I27-S05 must connect this source into `cpu_v01_fpga_top`, preserve the existing
first-test pass/fail behavior, and capture handler progress through UART or
GPIO evidence.

# FPGA SoC Top-Level Closure

Story: I30-S01

Status: Draft closure plan

## Command

Validate the closure plan:

```text
python tools\fpga_soc_top_closure.py --check
```

List the blocker matrix:

```text
python tools\fpga_soc_top_closure.py --matrix
```

Print one shortcut row:

```text
python tools\fpga_soc_top_closure.py --shortcut data_mmio_decoder_bypass
```

## Scope

I30-S01 converts the I27-S05 `documented_blocker_run` into an ordered
top-level closure plan for `cpu_v01_fpga_top`. It does not change RTL behavior.
The output is a checked matrix that maps each top-level shortcut or recently
closed handoff to the owning RTL story, expected testbench, validator, and
board-evidence handoff.

Required upstream gates:

- `python tools\fpga_soc_smoke.py --check`
- `python tools\fpga_program_loader.py --check`
- `python tools\fpga_debug_evidence.py --check`

## Blocker Matrix

| Shortcut ID | Shortcut or handoff | Owner | Testbench | Validator | Board-evidence handoff |
| --- | --- | --- | --- | --- | --- |
| `data_mmio_decoder_bypass` | I30-S02 replaced direct dmem-to-RAM bypass with `cpu_v01_fpga_soc_dmem_decoder`. | `I30-S02` | `rtl/cpu_v01_fpga_top_soc_decoder_tb.sv` | `python tools\fpga_soc_top_decoder.py --check` | I30-S05 integrated firmware smoke and I30-S06 closure archive. |
| `timer_interrupt_tied_off` | I30-S03 routes `timer_compare_irq` into `timer_interrupt_pending`. | `I30-S03` | `rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv` | `python tools\fpga_soc_top_peripherals.py --check` | I30-S05 timer-interrupt smoke and I30-S06 closure archive. |
| `uart_pin_mux_missing` | I30-S03 adds `uart_rx_i` and the firmware/status UART TX combine; I30-S04 extends it with loader arbitration. | `I30-S03` | `rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv` | `python tools\fpga_soc_top_peripherals.py --check` | I30-S05 UART smoke, I30-S06 closure archive, and I30-S04 loader arbitration. |
| `gpio_status_led_mux_missing` | I30-S03 ORs firmware GPIO/status LED requests with first-test status. | `I30-S03` | `rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv` | `python tools\fpga_soc_top_peripherals.py --check` | I30-S05 GPIO pass/fail smoke and I30-S06 closure archive. |
| `loader_handoff_absent` | I30-S04 replaces the absent external load path with `cpu_v01_fpga_soc_loader_handoff`, bounded data-RAM writes, tag-sidecar clearing, and status reporting. | `I30-S04` | `rtl/cpu_v01_fpga_top_loader_tb.sv` | `python tools\fpga_soc_loader_handoff.py --check` | I30-S05 loader smoke, I30-S06 closure archive, and I32-S01 monitor profile. |
| `top_smoke_evidence_missing` | I27-S05 is model evidence, not an RTL top-level firmware smoke. | `I30-S05` | `rtl/cpu_v01_fpga_top_soc_smoke_tb.sv` | `python tools\fpga_soc_top_smoke.py --check` | I30-S06 closure archive and I31-S01 first-pass build bundle. |

## Closure Order

The planned sequence is:

1. `I30-S02 data/MMIO decoder`
2. `I30-S03 UART/timer/GPIO/status and interrupt wiring`
3. `I30-S04 board-safe loader handoff`
4. `I30-S05 top-level SoC firmware smoke under Verilator`
5. `I30-S06 closure evidence archive`

The order is intentional. The data/MMIO decoder must exist before peripherals
can be integrated, and the peripheral path must exist before loader arbitration
or a real top-level firmware smoke can close.

## Closure Criteria

I30-S02 closes only when RAM accesses, every I27-S01 MMIO peripheral, and
reserved/fault windows are decoded deterministically while `tag_ram` remains
paired with `data_ram`.

I30-S03 closes only when the timer interrupt can assert and clear, firmware UART
RX/TX is wired with a status-stream TX mux policy, GPIO/status LEDs are
firmware-visible, and the interrupt lines match the I27 profile.

I30-S04 closes only when loader traffic cannot overwrite `instruction_rom`, can
only clear matching `tag_ram` sidecar bits, reports malformed images over
UART/debug status, and arbitrates cleanly with firmware/status UART output.

I30-S05 closes only when a Verilator top-level firmware smoke proves UART
output, timer interrupt service, syscall/trap progress, GPIO pass/fail, and
first-failure status together.

I30-S06 closes only when the closure archive links RTL sources, Verilator logs,
decoded UART/status or probe traces, replay mapping, remaining blockers, and
retest commands.

## Non-Goals

- No new peripherals beyond the I27-S01 minimal SoC map.
- No external DDR closure from I29.
- No physical board pass claim before I31.
- No interactive monitor expansion before I32-S01.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Every `cpu_v01_fpga_top` closure shortcut is mapped. | Met by the six-row blocker matrix. |
| Each shortcut has an owning RTL change. | Met by owner stories I30-S02 through I30-S05. |
| Each shortcut names a testbench and validator. | Met by the matrix `Testbench` and `Validator` columns. |
| Board-evidence handoff is explicit. | Met by the board-evidence handoff column and I30-S06 archive row. |

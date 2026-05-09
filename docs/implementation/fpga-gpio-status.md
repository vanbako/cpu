# FPGA GPIO Status

Story: I27-S04

Command:

```text
python tools\fpga_gpio_status.py --check
```

Related gates:

```text
python tools\fpga_soc_platform.py --check
python tools\fpga_smoke_firmware.py --check
```

## Scope

I27-S04 adds the firmware-visible GPIO/status block reserved by the I27-S01
`gpio_status` peripheral at `0x00F00200`. The block drives firmware-owned GPIO
outputs, exposes synchronized board inputs, controls status LEDs, selects debug
status probe sources, and raises the local `gpio_status` interrupt on board
input changes or software force.

The backlog mentions reset cause and build diagnostics. Those registers already
live in the I27-S01 `system_identity` peripheral: `RESET_CAUSE`, `BUILD_ID_LO`,
`BUILD_ID_HI`, and the `IMAGE_SHA256_*` cells. This story records that handoff
rather than duplicating diagnostic state in the GPIO block.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_gpio_status.py` | Executable GPIO/status model, register profile, JSON output, and validator. |
| `tools/fpga_gpio_status.py` | CLI for `--check`, `--json`, `--registers`, `--plan`, and `--demo`. |
| `rtl/cpu_v01_fpga_gpio_status.sv` | Cell-MMIO GPIO/status block with LED outputs and input-change interrupt. |
| `rtl/cpu_v01_fpga_gpio_status_tb.sv` | Standalone wrapper testbench for GPIO direction, LEDs, input interrupt, and debug force. |
| `tests/conformance/test_i27_s04_fpga_gpio_status.py` | Story conformance tests for model, docs, CLI, and RTL tokens. |

## Register Map

All addresses are CPU cell addresses under the I27-S01 `platform_devices`
window.

| Register | Cell | Access | Width | Semantics |
| --- | --- | --- | --- | --- |
| `GPIO_OUT` | `0x00F00200` | read-write | 16 | Firmware output value; driven pins are masked by `GPIO_DIR`. |
| `GPIO_IN` | `0x00F00201` | read-only | 16 | Synchronized board input and strap bits; read clears input-change interrupt. |
| `GPIO_DIR` | `0x00F00202` | read-write | 16 | Direction mask for firmware-owned outputs. |
| `STATUS_LEDS` | `0x00F00203` | read-write | 8 | Firmware status LEDs: PASS, FAIL, HEARTBEAT, and four software bits. |
| `DEBUG_STATUS_SELECT` | `0x00F00204` | read-write | 8 | Selects debug/status probe source; bit 7 software-forces `gpio_status`. |

## STATUS_LEDS Bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | `PASS` | Firmware-visible pass LED request. |
| 1 | `FAIL` | Firmware-visible fail LED request. |
| 2 | `HEARTBEAT` | Firmware-visible heartbeat LED request. |
| 3 | `SOFTWARE0` | Software status LED bit 0. |
| 4 | `SOFTWARE1` | Software status LED bit 1. |
| 5 | `SOFTWARE2` | Software status LED bit 2. |
| 6 | `SOFTWARE3` | Software status LED bit 3. |
| 7 | `RESERVED` | Reserved for a future top-level LED mux policy. |

The standalone RTL drives these outputs directly. I27-S05 must decide how
firmware-controlled LED requests are muxed with the existing first-test
pass/fail latches in `cpu_v01_fpga_top` so the first-test pass/fail behavior
does not regress.

## Interrupt And Diagnostics

`gpio_status` is a local interrupt line. It is asserted when the synchronized
`GPIO_IN` value changes and remains set until firmware reads `GPIO_IN`.
`DEBUG_STATUS_SELECT[7]` can software-force the same interrupt for simulation
and diagnostic sequencing; clearing that bit drops the forced interrupt.

Reset cause and build diagnostics are intentionally read from the
`system_identity` window:

- `RESET_CAUSE`
- `BUILD_ID_LO`
- `BUILD_ID_HI`
- `IMAGE_SHA256_0` through `IMAGE_SHA256_5`

The bring-up runbook can therefore use GPIO/status for live board state and
system identity for reset/build/image evidence.

## Wrapper And Simulation Checks

The Verilator command inventory is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_gpio_status_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_gpio_status_tb.sv
```

The standalone testbench covers:

- `GPIO_OUT` masked by `GPIO_DIR`;
- `STATUS_LEDS` driving PASS, FAIL, HEARTBEAT, and software status outputs;
- `GPIO_IN` synchronization, readback, and input-change interrupt clear;
- `DEBUG_STATUS_SELECT` software-forced interrupt assertion and clear.

I27-S05 must connect this block into the SoC shell, preserve first-test
pass/fail behavior, and capture GPIO-visible handler or smoke progress.

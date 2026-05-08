# FPGA Smoke Firmware

Story: I23-S04

Status: Implemented first-test smoke firmware profile

This story turns the FPGA top from a reset-visible wrapper into a first-test
runtime smoke design. The built-in instruction ROM now provides a deterministic
`PAUSE` stream, `cpu_v01_fpga_top` defaults fetch enabled, and the wrapper
projects pass, fail, heartbeat, retire count, and fault cause signals for board
or ILA observation.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_memories.sv` | Provides the built-in `PAUSE` ROM stream and optional `readmemh` override. |
| `rtl/cpu_v01_fpga_top.sv` | Enables fetch by default and converts retire/fault progress into pass/fail status. |
| `rtl/cpu_v01_fpga_first_test_tb.sv` | Verilator-oriented first-test smoke testbench. |
| `src/cpu_v01/fpga_smoke.py` | Structured smoke observation inventory and validator. |
| `tools/fpga_smoke_firmware.py` | CLI wrapper for checking or rendering the smoke profile. |
| `tests/conformance/test_i23_s04_fpga_smoke_firmware.py` | I23-S04 conformance coverage. |

## Command

```text
python tools\fpga_smoke_firmware.py --check
```

Verilator lint:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_first_test_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_first_test_tb.sv
```

## Firmware Contract

The built-in ROM stream uses `24'h05B05B`, which packs two 12-bit `PAUSE`
instructions per 24-bit cell. This is intentionally boring firmware: it proves
clock, reset, fetch, decode, retire, instruction ROM, and observation wiring
without depending on data memory, MMIO, branch control, or a loader.

The first-test pass threshold is eight normal retires:

- `FIRST_TEST_PASS_RETIRE_COUNT = 8`;
- `pass_led_o` asserts when the retire sequence reaches that threshold and no
  sticky fault has been observed;
- `fail_led_o` asserts on any retired fault packet;
- `heartbeat_led_o` follows `debug_retire_sequence[0]`;
- `status_retire_count_o` exposes `debug_retire_sequence[31:0]`;
- `status_fault_code_o` captures the first retired fault cause.

## Testbench Expectations

`cpu_v01_fpga_first_test_tb` releases reset, lets the PAUSE stream run, and
requires:

- reset observation;
- `pass_led_o` asserted;
- `fail_led_o` deasserted;
- at least eight retired instructions;
- retire/activity observation seen;
- heartbeat activity seen;
- reset PCC and SR debug projections still matching the reset contract.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A tiny deterministic program retires from FPGA-local ROM. | Met by the built-in PAUSE stream. |
| Pass/fail status is visible without a debugger. | Met by `pass_led_o` and `fail_led_o`. |
| Retire progress and fault state are observable. | Met by heartbeat, retire count, and fault-code outputs. |
| The smoke design remains independent of board peripherals. | Met: no external DRAM, UART, or MMIO dependency is required. |

## Deferrals

- I23-S05 owns board constraints, synthesis, implementation, and timing gates.
- I23-S06 owns programming steps and captured board evidence.

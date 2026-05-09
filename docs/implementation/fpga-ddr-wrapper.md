# FPGA DDR Wrapper

Story: I29-S02

Status: RTL calibration gate; board-specific DDR IP blocked

## Command

Validate the profile:

```text
python tools\fpga_ddr_wrapper.py --check
```

Related gates:

```text
python tools\fpga_external_memory.py --check
python tools\fpga_reset_cdc.py --check
```

Optional Verilator commands:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_ddr_calibration_gate_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_ddr_calibration_gate.sv rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv
$env:MAKEFLAGS="PYTHON3=$((Get-Command python).Source.Replace('\','/'))"; verilator --binary --timing --Mdir obj_dir\ddr_gate --top-module cpu_v01_fpga_ddr_calibration_gate_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_ddr_calibration_gate.sv rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv
obj_dir\ddr_gate\Vcpu_v01_fpga_ddr_calibration_gate_tb.exe
```

The `MAKEFLAGS` prefix is required on this MSYS2 Verilator install because the
Verilator make include otherwise invokes the blocked WindowsApps `python3`
shim during `verilator_includer`.

## Scope

I29-S02 adds the CPU-owned DDR calibration gate and visibility wrapper around
the I29-S01 request/response boundary. The wrapper exposes calibration status,
gates CPU traffic until `controller_ready`, converts blocked accesses and
controller response errors into CPU-owned `ACCESS_FAULT` responses, and asserts
`fail_visible_o` when calibration fails or does not complete.

This story does not claim board-calibrated DDR. The board-specific DDR IP,
physical pins, byte lanes, training parameters, generated clocks, and Gowin
evidence remain blocked until a verified controller instance and board reports
exist.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_ddr_calibration_gate.sv` | Board-neutral calibration/status gate between CPU external-memory requests and a DDR controller adapter. |
| `rtl/cpu_v01_fpga_ddr_calibration_gate_tb.sv` | Timeout, ready, pass-through, controller-error, and reset-request smoke testbench. |
| `src/cpu_v01/fpga_ddr_wrapper.py` | Structured I29-S02 profile and validator. |
| `tools/fpga_ddr_wrapper.py` | CLI wrapper for profile checks, JSON, rules, signals, blockers, and lint plan. |
| `tests/conformance/test_i29_s02_fpga_ddr_wrapper.py` | I29-S02 conformance coverage. |

## Visibility

The wrapper provides these shell-visible status outputs:

| Signal | Meaning |
| --- | --- |
| `status_calibration_done_o` | Mirrors `calibration_done` from the DDR controller wrapper. |
| `status_calibration_error_o` | Mirrors `calibration_error` from the DDR controller wrapper. |
| `status_init_in_progress_o` | Shows initialization or training is still active. |
| `status_controller_ready_o` | Derived gate: calibration done, no calibration error, no timeout, and no sticky controller error. |
| `status_access_gate_closed_o` | Indicates CPU external-memory traffic is blocked. |
| `status_timeout_o` | Calibration did not complete before `CALIBRATION_TIMEOUT_CYCLES`. |
| `status_error_code_o` | Sticky normalized calibration, timeout, or controller response error. |
| `fail_visible_o` | Failure output for LED, UART/status packet, or probe routing. |

The exact UART/status packet field assignment is reserved for a later status
layout update. I29-S02 requires that a failure signal exists and can be routed
visibly when the board wrapper is connected.

## Gate Behavior

| Rule | Behavior |
| --- | --- |
| `gate_until_controller_ready` | Before `controller_ready`, CPU requests are not forwarded to the DDR controller and receive precise `ACCESS_FAULT` responses. |
| `pass_ready_requests` | Once ready, one CPU request at a time is forwarded to the controller adapter. |
| `controller_error_fault` | `ctrl_rsp_error_i` converts the response into a precise `ACCESS_FAULT` and asserts `fail_visible_o`. |
| `calibration_timeout_visible_fail` | If `init_in_progress_i` stays high beyond `CALIBRATION_TIMEOUT_CYCLES`, `status_timeout_o`, `status_error_code_o`, and `fail_visible_o` assert. |
| `reset_request_clears_sticky_status` | `reset_request_i` asserts `controller_reset_o` and clears sticky timeout and controller-error status. |

The gate is intentionally single-outstanding for first bring-up. Burst
adaptation, byte-lane steering, and controller-specific queues stay behind the
board-specific DDR IP wrapper.

## Remaining Blockers

- The vendor DDR controller IP, physical pins, byte lanes, and training
  parameters are not committed.
- `ddr_ui_clk` and `ddr_ui_reset` still need I28-S02 reset/CDC treatment before
  top-level use.
- `cpu_v01_fpga_top still needs an external-memory decoder` before DDR data
  traffic is live.
- UART/status packet placement for DDR calibration fields is reserved but not
  assigned.
- Gowin reports and board evidence must exist before this can be claimed as
  board-calibrated DDR.

## Handoffs

- I29-S03 uses `status_controller_ready_o` and `fail_visible_o` for memory-test
  firmware progress and visible failure.
- I29-S04 decides coherent/cacheable and capability-tag policy before off-BRAM
  capability traffic.
- I29-S05 archives calibration, timeout, memory-test, UART/status, timing, and
  bitstream evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| FPGA shell exposes calibration done/error state. | Partially met by wrapper-visible `status_calibration_done_o` and `status_calibration_error_o`; top-level pin/status packet placement remains blocked. |
| CPU access is gated until ready. | Met by `gate_until_controller_ready` in RTL. |
| Calibration failure is visible. | Met by `fail_visible_o`, `status_timeout_o`, and `status_error_code_o`. |
| Board-specific IP details stay outside CPU-owned logic. | Met by the adapter boundary and blocker list. |

# FPGA Synthesis Gate

Story: I23-S05

Status: Implemented gate profile with board-verification blockers

Structured gate:

```text
python tools\fpga_synthesis_gate.py --check
```

Command plan:

```text
python tools\fpga_synthesis_gate.py --plan
python tools\fpga_synthesis_gate.py --gowin-tcl
```

## Purpose

I23-S05 turns the I23-S04 first-test smoke RTL into a repeatable FPGA build
gate for the Sipeed Tang Mega 138K Dock. The gate is intentionally strict: it
does not allow a board run to be counted as passing until clock, reset, pass,
fail, and heartbeat pins are constrained from the Sipeed board data and the
actual SOM package/device version has been verified.

The current implementation defines the scripted flow, required constraints,
toolchain expectations, report audit surface, and explicit blockers. The
physical Gowin place-and-route run remains blocked until the Tang Mega 138K
package and board pin overlay are confirmed.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_synthesis.py` | Structured I23-S05 synthesis/timing gate profile, command plan, Gowin Tcl template, and validator. |
| `tools/fpga_synthesis_gate.py` | CLI wrapper for checking, printing JSON, printing the command plan, and emitting the Gowin Tcl template. |
| `tests/conformance/test_i23_s05_fpga_synthesis_gate.py` | Conformance tests for the gate profile, commands, documentation, and blockers. |
| `docs/implementation/fpga-synthesis-gate.md` | This implementation note. |

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega 138K Dock` |
| Device | `GW5AST-LV138PG484A` pending physical verification |
| IDE package | `PBG484A` pending physical verification |
| Top module | `cpu_v01_fpga_top` |
| First-test clock target | `25_000_000` Hz |
| Constraint file | `constraints/tang_mega_138k_first_test.cst` |
| Timing file | `constraints/tang_mega_138k_first_test.sdc` |
| Build root | `build/fpga/tang_mega_138k/first_test` |

The package/device remains a gate blocker because public Tang Mega 138K sources
mix `PG484A` and `FPG676A` references. The gate therefore records
`GW5AST-LV138PG484A`/`PBG484A` as the non-Pro target but requires board marking
or JTAG/programmer confirmation before a real `gw_sh` run is accepted.

## Toolchain Gate

| Tool | Executable | Required | Role |
| --- | --- | --- | --- |
| Verilator | `verilator` | Yes | Pre-synthesis RTL lint/elaboration through `cpu_v01_fpga_first_test_tb`. |
| Gowin EDA command shell | `gw_sh` | Yes | Synthesis, place and route, bitstream generation, timing/utilization reports. |
| Gowin Programmer | `programmer_cli_or_gui` | Yes | Volatile SRAM programming or flash programming after build. |
| openFPGALoader | `openFPGALoader` | No | Optional programming path using the `tangmega138k` board flag after device/package confirmation. |

Official Gowin EDA remains the primary implementation flow because it covers
code synthesis, place and route, bitstream generation, download, and GAO debug.
openFPGALoader is documented as an optional programming path, not the primary
I23-S05 implementation gate.

## Required Constraints

| Signal | Required constraint | Gate behavior |
| --- | --- | --- |
| `board_clk_i` | Pin assignment plus 40 ns clock period. | Fail on `unconstrained_clock_or_reset`. |
| `board_reset_n_i` | Pin assignment, IO standard, and reset synchronizer treatment. | Fail on `unconstrained_clock_or_reset`. |
| `pass_led_o` | PMOD LED pin, IO standard, and polarity. | Fail on `missing_pass_fail_observation_pin`. |
| `fail_led_o` | PMOD LED pin, IO standard, and polarity. | Fail on `missing_pass_fail_observation_pin`. |
| `heartbeat_led_o` | PMOD LED pin, IO standard, and polarity. | Fail if no visible clock/reset progress output is available. |
| `status_fault_code_o`/`status_retire_count_o` | Optional GAO, UART, or ILA probe plan. | Not required for first LED smoke, but required for richer triage. |

## Gate Steps

| Step | Command | Pass criteria |
| --- | --- | --- |
| `rtl_preflight` | `verilator --lint-only --timing --top-module cpu_v01_fpga_first_test_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_first_test_tb.sv` | Verilator exits 0 for the first-test smoke testbench. |
| `gate_profile_check` | `python tools\fpga_synthesis_gate.py --check` | The checker reports zero profile issues. |
| `emit_gowin_tcl` | `python tools\fpga_synthesis_gate.py --gowin-tcl` | The template names every RTL source, `cpu_v01_fpga_top`, the constraints, and `run all`. |
| `gowin_synth_place_route` | `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl` | Gowin emits synthesis, timing, port, utilization, and bitstream outputs. |
| `report_audit` | `python tools\fpga_synthesis_gate.py --check-reports build\fpga\tang_mega_138k\first_test` | Reports contain timing slack, utilization, port assignment, and bitstream evidence. |

The Gowin Tcl template uses the Gowin project commands documented for
`add_file`, `set_device`, `set_option`, and `run all`. The template keeps
`<verified_B_or_C>` as a deliberate placeholder until the physical board has
been checked.

## Report Requirements

| Report | Required contents |
| --- | --- |
| `build/fpga/tang_mega_138k/first_test/impl/gwsynthesis/*.rpt` | `cpu_v01_fpga_top`, `cpu_v01_core`, and no memory/core black boxes. |
| `build/fpga/tang_mega_138k/first_test/impl/pnr/*timing*.rpt` | `board_clk_i`, slack, and no `negative_timing_slack_at_first_test_clock`. |
| `build/fpga/tang_mega_138k/first_test/impl/pnr/*ports*.rpt` | `pass_led_o`, `fail_led_o`, and `heartbeat_led_o` pin assignments. |
| `build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs` | Bitstream file for programmer handoff. |

## Blockers

- Confirm whether the physical board is the `PG484` non-Pro SOM or an
  `FPG676` Pro-style SOM.
- Extract `board_clk_i`, `board_reset_n_i`, `pass_led_o`, `fail_led_o`, and
  `heartbeat_led_o` from Sipeed's All PIN Constraints package. I24-S02 tracks
  this in `docs/implementation/fpga-constraints-overlay.md` and
  `python tools\fpga_constraints_overlay.py --check`.
- Verify LED polarity and 3.3 V IO standard before programming.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A scripted FPGA synthesis/place-route flow is defined. | Met by `tools/fpga_synthesis_gate.py --plan` and `--gowin-tcl`. |
| The flow reports utilization and timing. | Met by report requirements and the report-audit entry point. |
| The flow fails on unconstrained clocks/resets. | Met by mandatory `board_clk_i` and `board_reset_n_i` constraints and `unconstrained_clock_or_reset` failure condition. |
| The flow fails on black boxes. | Met by synthesis report requirements for `cpu_v01_fpga_top`, `cpu_v01_core`, and memory/core black-box checks. |
| The flow fails without visible pass/fail outputs. | Met by mandatory `pass_led_o`, `fail_led_o`, and `heartbeat_led_o` constraints. |
| Board-specific uncertainty is visible. | Met by explicit package and pin-extraction blockers. |

## Next

I23-S06 is tracked in `docs/implementation/fpga-board-bringup.md` and checked
with `python tools\fpga_bringup_runbook.py --check`. It should not claim a
physical pass until this gate has a verified constraint overlay, Gowin
timing/utilization reports, a bitstream, and observed LED or probe evidence.

# FPGA Gowin Build

Story: I24-S03

Status: Report audit implemented; physical Gowin run blocked

Structured gate:

```text
python tools\fpga_gowin_build.py --check
```

Command plan:

```text
python tools\fpga_gowin_build.py --plan
```

Report audit:

```text
python tools\fpga_gowin_build.py --audit-reports build\fpga\tang_mega_138k\first_test
```

## Purpose

I24-S03 turns the first-test Gowin build into an auditable handoff for board
programming. The story does not claim that Gowin has been run in this
repository. It defines the required command order and the report-bundle checks
that must pass before I24-S04 can program SRAM.

The real build remains `blocked` until I24-S01 identity evidence and I24-S02
constraint evidence are both confirmed. Once those gates pass, the report audit
must reject missing reports, black box evidence, unconstrained paths, negative
timing slack, missing pass/fail/heartbeat ports, and absent bitstream output.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_gowin_build.py` | Structured I24-S03 build profile, command plan, report requirements, and report-bundle auditor. |
| `tools/fpga_gowin_build.py` | CLI wrapper for checking, printing JSON, printing the command plan, and auditing reports. |
| `tests/conformance/test_i24_s03_fpga_gowin_build.py` | Conformance tests for profile dependencies, blocked/default audit, passing fixture bundle, failure markers, CLI output, and docs. |
| `docs/implementation/fpga-gowin-build.md` | This implementation note. |

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega Dock with 138K SOM` |
| Device | `GW5AST-LV138PG484A` |
| Package | `PBG484A` |
| Top module | `cpu_v01_fpga_top` |
| Build root | `build/fpga/tang_mega_138k/first_test` |
| Identity gate | `python tools\fpga_board_identity.py --check` |
| Constraints gate | `python tools\fpga_constraints_overlay.py --check` |
| Synthesis gate | `python tools\fpga_synthesis_gate.py --check` |

## Build Steps

| Step | Command | Required before it can pass |
| --- | --- | --- |
| `identity_audit` | `python tools\fpga_board_identity.py --audit-evidence` | Physical board marking or programmer/JTAG scan is captured and matches the target. |
| `constraints_audit` | `python tools\fpga_constraints_overlay.py --audit-evidence` | Identity is confirmed and verified Sipeed pin evidence exists. |
| `emit_gowin_tcl` | `python tools\fpga_synthesis_gate.py --gowin-tcl` | Target, CST, and SDC are verified. |
| `gowin_run_all` | `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl` | Gowin EDA command shell is on `PATH`; the project uses the verified target. |
| `report_audit` | `python tools\fpga_gowin_build.py --audit-reports build\fpga\tang_mega_138k\first_test` | Gowin reports and bitstream exist under the build root. |

## Report Requirements

| Requirement | Glob | Required evidence | Fails on |
| --- | --- | --- | --- |
| `synthesis_report` | `impl/gwsynthesis/*.rpt` | `cpu_v01_fpga_top`, `cpu_v01_core`. | `black box`, unresolved modules, or errors. |
| `timing_report` | `impl/pnr/*timing*.rpt` | `Slack`, `board_clk_i`. | `Slack -`, `VIOLATED`, `negative slack`, or `unconstrained`. |
| `ports_report` | `impl/pnr/*ports*.rpt` | `board_clk_i`, `board_reset_n_i`, `pass_led_o`, `fail_led_o`, `heartbeat_led_o`, `uart_tx_o`. | `unassigned`, `not constrained`, or missing LOC evidence. |
| `utilization_report` | `impl/pnr/*util*.rpt` | `LUT`, `Register`. | error or failed markers. |
| `bitstream` | `impl/pnr/*.fs` | File exists. | missing bitstream. |

The timing failure condition is `negative_timing_slack_at_first_test_clock`.
The visible-output failure condition is `missing_status_or_uart_observation_pin`.

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `passed` | Identity and constraints are confirmed, all reports exist, all required tokens are present, and no forbidden markers appear. | Hand the audited `.fs` bitstream to I24-S04 SRAM programming. |
| `failed` | Reports exist but contain missing tokens or failure markers such as black box, unconstrained path, or negative timing evidence. | Fix RTL, constraints, timing, or build settings and rerun Gowin. |
| `blocked` | Identity/constraints are not confirmed or reports/bitstream are missing. | Complete upstream evidence or rerun `gw_sh` before programming. |

I24-S04 board programming is tracked in
`docs/implementation/fpga-board-programming.md` and checked with
`python tools\fpga_board_programming.py --check`.

## Current Blocker

- I24-S01 physical identity evidence is not captured.
- I24-S02 verified pin evidence and final CST are not captured.
- Gowin EDA reports and bitstream are not present under
  `build/fpga/tang_mega_138k/first_test`.
- I24-S04 must not program SRAM until this report audit is `passed`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Gowin command order is documented. | Met by the build-step command plan. |
| Timing, utilization, ports, synthesis, and bitstream artifacts are required. | Met by report requirements and the report audit. |
| The audit fails on black boxes. | Met by forbidden synthesis report markers. |
| The audit fails on unconstrained paths or negative slack. | Met by timing report forbidden markers and `negative_timing_slack_at_first_test_clock`. |
| The audit fails without visible status pins. | Met by required `pass_led_o`, `fail_led_o`, and `heartbeat_led_o` port tokens. |
| Board programming is blocked until reports pass. | Met by `blocked` default status and the I24-S04 handoff rule. |

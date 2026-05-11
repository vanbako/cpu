# FPGA Retro Console Gowin Build

Story: I34-S03

Status: Gowin build evidence gate implemented; Retro Console 60K report capture
remains blocked until identity, constraints, reports, and bitstream evidence are
captured.

Validate the Retro Console Gowin profile:

```text
python tools\fpga_retro_console_gowin.py --check
```

Print the evidence template:

```text
python tools\fpga_retro_console_gowin.py --template
```

Audit a captured key/value evidence record:

```text
python tools\fpga_retro_console_gowin.py --audit docs\implementation\evidence\i34_s03_retro_console_gowin_build.txt
```

Audit a generated Gowin report bundle:

```text
python tools\fpga_retro_console_gowin.py --audit-reports build\fpga\tang_60k_retro_console\first_test
```

## Purpose

I34-S03 records build feasibility for the Tang Retro Console with 60K SOM
alternate target. It consumes the I34-S01 identity gate, I34-S02 final
constraints, I28-S01 clock profile, and I28-S03 report parser. It captures
synthesis, place-route, timing, utilization, port mapping, warning policy,
bitstream path, and bitstream hash for the exact recorded 60K Gowin part.

This is not a first-pass release claim and must not claim a Tang Mega Dock with
138K SOM pass. The audit must not claim a Tang Mega Dock with 138K SOM pass
from Retro Console evidence.

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Retro Console with 60K SOM` |
| Top module | `cpu_v01_fpga_top` |
| Clock profile | `debug_direct_25mhz` |
| Build root | `build/fpga/tang_60k_retro_console/first_test` |
| Identity gate | `python tools\fpga_retro_console_identity.py --check` |
| Constraints gate | `python tools\fpga_retro_console_constraints.py --check` |
| Clock gate | `python tools\fpga_clock_profiles.py --check` |
| Report parser | `python tools\fpga_gowin_reports.py --check` |
| Evidence path | `docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt` |

## Evidence Format

```text
story=I34-S03
captured_at=
repository_commit=
board=Sipeed Tang Retro Console with 60K SOM
identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt
constraints_evidence=docs/implementation/evidence/i34_s02_retro_console_pins.txt
cst_path=constraints/tang_60k_retro_console_first_test.cst
sdc_path=constraints/tang_60k_retro_console_first_test.sdc
gowin_part=
top_module=cpu_v01_fpga_top
clock_profile=debug_direct_25mhz
build_root=build/fpga/tang_60k_retro_console/first_test
gowin_run_command=gw_sh build/fpga/tang_60k_retro_console/first_test/run_gowin.tcl
synthesis_report=build/fpga/tang_60k_retro_console/first_test/impl/gwsynthesis/synth.rpt
place_route_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/place_route.rpt
timing_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_timing.rpt
utilization_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_util.rpt
ports_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_ports.rpt
warnings_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/warnings.rpt
bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs
bitstream_sha256=
worst_slack_ns=
unconstrained_paths=0
required_ports=board_clk_i,board_reset_n_i,pass_led_o,fail_led_o,heartbeat_led_o,uart_tx_o
port_mapping_status=captured
warning_policy=no_black_boxes_no_errors_no_failed_markers_no_unconstrained_paths
report_parser_audit=python tools\fpga_gowin_reports.py --audit-reports build\fpga\tang_60k_retro_console\first_test
build_result=retro_console_gowin_build_pass
retest_commands=python tools\fpga_retro_console_identity.py --check ; python tools\fpga_retro_console_constraints.py --check ; python tools\fpga_clock_profiles.py --check ; python tools\fpga_gowin_reports.py --check ; python tools\fpga_retro_console_gowin.py --check
```

## Report Requirements

| Requirement | Field | Policy |
| --- | --- | --- |
| Identity | `identity_evidence` | I34-S01 must audit as the 60K alternate target. |
| Constraints | `constraints_evidence` | I34-S02 must audit as confirmed and final CST/SDC files must be used. |
| Synthesis | `synthesis_report` | `cpu_v01_fpga_top` and `cpu_v01_core` are present with no black boxes. |
| Place-route | `place_route_report` | Place-route completion or equivalent PNR report is captured. |
| Timing | `timing_report` | `worst_slack_ns` is nonnegative and `unconstrained_paths=0`. |
| Utilization | `utilization_report` | LUT and Register utilization are present. |
| Ports | `ports_report` | Clock, reset, pass/fail/heartbeat, and UART TX are assigned from Retro Console pins. |
| Warning policy | `warning_policy` | Black boxes, errors, failed markers, unconstrained paths, and timing violations are rejected. |
| Bitstream | `bitstream_path`, `bitstream_sha256` | The `.fs` path and 64-character SHA-256 are captured. |

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `passed` | Evidence is complete, report policy is clean, timing slack is nonnegative, ports are assigned, and bitstream identity is recorded for the 60K build. | Hand `bitstream_path` and `bitstream_sha256` to I34-S04. |
| `blocked` | Identity, constraints, reports, or bitstream evidence is missing. | Capture I34-S01/I34-S02 evidence and rerun Gowin for the 60K target. |
| `failed` | Timing, unconstrained paths, or report policy failed. | Fix constraints, RTL, or clock settings before programming. |
| `invalid` | The evidence record is malformed, points at the wrong board/build root, has a bad hash, or carries the wrong target. | Fix the record and rerun the audit. |

`negative_timing_slack_at_first_test_clock` and nonzero `unconstrained_paths`
are explicit failures.

## Blockers

- I34-S01 physical identity evidence is not captured in this repository.
- I34-S02 final pin evidence and final Retro Console CST/SDC files are not
  captured in this repository.
- No Gowin reports or bitstream for the 60K target are captured yet.
- The Tang Mega Dock with 138K SOM remains the active first CPU path.

## Handoff

I34-S04 consumes only an I34-S03 `passed` record when programming the Retro
Console SRAM. I34-S05 consumes the timing, port, UART, and bitstream identity
if programming or smoke observation fails. I34-S06 archives the pass or blocker
without changing the 138K first CPU handoff policy.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Synthesis, place-route, timing, utilization, and ports are captured. | Met by required report fields and the report parser audit. |
| Warning policy is explicit. | Met by `warning_policy` and invalid/failed audit states. |
| Bitstream path and hash are captured. | Met by `bitstream_path` and `bitstream_sha256`. |
| The exact 60K target is used. | Met by `gowin_part`, the Retro Console build root, and the I34-S01/I34-S02 gates. |
| I34-S04 handoff is explicit. | Met by the passed audit action and handoff section. |

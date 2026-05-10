# FPGA First-Pass Gowin Build

Story: I31-S02

Status: Gowin evidence gate implemented; report capture blocked

## Command

Validate the first-pass Gowin profile:

```text
python tools\fpga_first_pass_gowin.py --check
```

Print an evidence template:

```text
python tools\fpga_first_pass_gowin.py --template
```

Audit a captured evidence record:

```text
python tools\fpga_first_pass_gowin.py --audit docs\implementation\evidence\i31_s02_gowin_build_timing.txt
```

Audit a generated Gowin report bundle:

```text
python tools\fpga_first_pass_gowin.py --audit-reports build\fpga\tang_mega_138k\first_test
```

Required upstream gates:

```text
python tools\fpga_first_pass_bundle.py --check
python tools\fpga_gowin_build.py --check
python tools\fpga_gowin_reports.py --check
```

## Scope

I31-S02 captures the first integrated SoC top Gowin build and timing evidence
for the frozen I31-S01 bundle. It does not program the board. I31-S03 consumes
only a passing I31-S02 record with a bitstream path and `bitstream_sha256`.

The expected evidence record is:

```text
docs/implementation/evidence/i31_s02_gowin_build_timing.txt
```

The default audit is `blocked` until the record or real Gowin reports exist.
The audit must fail on negative slack, unconstrained paths, black boxes, failed
markers, missing status/UART ports, missing utilization, missing reports, or a
missing bitstream hash.

## Build Selection

| Field | Value |
| --- | --- |
| `first_pass_bundle` | `docs/implementation/evidence/i31_s01_first_pass_build_bundle.txt` |
| `top_module` | `cpu_v01_fpga_top` |
| `selected_image` | `builtin.first_test_pause_stream` |
| `clock_profile` | `debug_direct_25mhz` |
| `build_root` | `build/fpga/tang_mega_138k/first_test` |
| `gowin_run_command` | `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl` |
| `build_result` | `gowin_build_pass` |

## Required Record Fields

| Field | Requirement |
| --- | --- |
| `story` | Must be `I31-S02`. |
| `captured_at` | Local capture timestamp. |
| `repository_commit` | Repository commit used for the build. |
| `first_pass_bundle` | I31-S01 frozen bundle path. |
| `top_module`, `selected_image`, `clock_profile` | Must match I31-S01. |
| `build_root` | Must be `build/fpga/tang_mega_138k/first_test`. |
| `gowin_run_command` | Exact Gowin command used for the run. |
| `synthesis_report` | Synthesis report path. |
| `place_route_report` | Place-route or equivalent PNR report path. |
| `timing_report` | Timing report path. |
| `utilization_report` | Utilization report path. |
| `ports_report` | Port assignment report path. |
| `warnings_report` | Warning or log summary path. |
| `bitstream_path` | Produced `.fs` bitstream path. |
| `bitstream_sha256` | 64-character SHA-256 of the produced bitstream. |
| `worst_slack_ns` | Parsed worst slack, nonnegative. |
| `unconstrained_paths` | Must be `0`. |
| `required_ports` | Must include clock, reset, pass/fail/heartbeat LEDs, and UART TX. |
| `warning_policy` | Must reject black boxes, errors, failed markers, and unconstrained paths. |
| `gowin_reports_audit` | I28-S03 audit command or output link. |
| `gowin_build_audit` | I24-S03 audit command or output link. |
| `build_result` | Must be `gowin_build_pass`. |
| `retest_commands` | Commands to rerun bundle, build, report parser, and reproducible-build gates. |

## Report Policy

The I31-S02 policy composes the I24-S03 build handoff and I28-S03 parser:

- `synthesis_report` must show `cpu_v01_fpga_top` and `cpu_v01_core` with no
  black boxes or unresolved modules.
- `place_route_report` must capture place-route completion or equivalent PNR
  output.
- `timing_report` must provide `worst_slack_ns` and zero `unconstrained_paths`.
- `utilization_report` must preserve at least LUT and Register counts.
- `ports_report` must assign `board_clk_i`, `board_reset_n_i`, `pass_led_o`,
  `fail_led_o`, `heartbeat_led_o`, and `uart_tx_o`.
- `warning_policy` rejects black boxes, errors, failed markers, timing
  violations, and unconstrained paths.
- `bitstream_path` and `bitstream_sha256` bind the exact `.fs` file handed to
  programming.

## Status Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `passed` | Reports are complete, timing policy passes, ports/utilization are present, and bitstream identity is recorded. | Hand `bitstream_path` and `bitstream_sha256` to I31-S03. |
| `blocked` | I31-S01 is not frozen, reports are missing, or no evidence record exists. | Capture the frozen bundle and Gowin reports. |
| `failed` | Timing or report policy failed. | Fix RTL, constraints, timing, or build settings and rerun Gowin. |
| `invalid` | Key fields, links, bitstream hash, or policy fields are malformed. | Fix the evidence record and rerun the audit. |

## Retest Commands

```text
python tools\fpga_first_pass_bundle.py --check
python tools\fpga_gowin_build.py --check
python tools\fpga_gowin_reports.py --check
python tools\fpga_gowin_reports.py --audit-reports build\fpga\tang_mega_138k\first_test
python tools\fpga_reproducible_build.py --check
```

## Handoff

I31-S03 consumes only a `passed` I31-S02 record. SRAM programming must record
the same `bitstream_path`, `bitstream_sha256`, reset release, heartbeat,
pass/fail LEDs, UART/status packets, and optional probe captures.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Synthesis evidence is required. | Met by `synthesis_report`. |
| Place-route evidence is required. | Met by `place_route_report`. |
| Timing evidence is required and fails on negative slack. | Met by `timing_report`, `worst_slack_ns`, and `negative_timing_slack_at_first_test_clock`. |
| Unconstrained paths fail the audit. | Met by `unconstrained_paths=0` and `unconstrained_paths_present`. |
| Utilization, ports, and warning policy are required. | Met by `utilization_report`, `ports_report`, and `warning_policy`. |
| Bitstream path and hash are required. | Met by `bitstream_path` and `bitstream_sha256`. |
| Programming handoff is explicit. | Met by the I31-S03 handoff rule. |

# FPGA Gowin Report Parser

Story: I28-S03

Structured gate:

```text
python tools\fpga_gowin_reports.py --check
```

Parse a generated report bundle:

```text
python tools\fpga_gowin_reports.py --audit-reports build\fpga\tang_mega_138k\first_test
```

Related gates:

```text
python tools\fpga_clock_profiles.py --check
python tools\fpga_gowin_build.py --check
```

## Scope

I28-S03 adds an automated parser for Gowin report bundles. I24-S03 still owns
the coarse build handoff and physical-evidence blocker. This parser extracts
the details that later timing and reproducibility stories need: worst slack,
clock summary, utilization, unconstrained paths, port assignments, warnings,
errors, and bitstream identity.

The default timing policy uses `debug_direct_25mhz` from I28-S01. A report
bundle passes only when required reports exist, worst slack is nonnegative,
unconstrained paths are zero, required status/UART ports are assigned,
utilization metrics are present, forbidden report markers are absent, and each
bitstream records path, size, and SHA-256.

## Parsed Evidence

| Evidence | Source glob | Extracted fields |
| --- | --- | --- |
| Synthesis report | `impl/gwsynthesis/*.rpt` | Black-box, unresolved-module, warning, and error markers. |
| Timing report | `impl/pnr/*timing*.rpt` | Worst slack, clock summary, unconstrained paths, timing violations, and target-margin warning. |
| Ports report | `impl/pnr/*ports*.rpt` | `board_clk_i`, `board_reset_n_i`, `pass_led_o`, `fail_led_o`, `heartbeat_led_o`, and `uart_tx_o` LOC assignments. |
| Utilization report | `impl/pnr/*util*.rpt` | At minimum `LUT` and `Register`; optional B-SRAM/BRAM metrics are preserved when present. |
| Bitstream | `impl/pnr/*.fs` | Bitstream identity: path, size, and SHA-256 hash. |

## CI Policy

| Policy | Failure marker |
| --- | --- |
| Missing timing, port, utilization, synthesis, or bitstream reports block the parser. | `blocked` with `missing_reports`. |
| Negative worst slack fails the parser. | `negative_timing_slack_at_first_test_clock`. |
| Any nonzero or unqualified unconstrained paths fail the parser. | `unconstrained_paths_present`. |
| Missing visible status or UART ports fail the parser. | `missing_status_or_uart_observation_pin`. |
| Missing utilization metrics fail the parser. | `missing_utilization_metric`. |
| Black boxes, unresolved modules, errors, failed markers, or violated timing fail the parser. | `forbidden_report_token:*` or `gowin_error_or_failed_marker_present`. |

Worst slack below the I28-S01 target slack but above the minimum is reported as
`timing_slack_below_target_margin`. That is a margin warning, not a failure,
because I28-S04 owns frequency-margin tracking and conservative default
selection.

## Current Blocker

- No real Gowin report bundle or `.fs` bitstream exists under
  `build/fpga/tang_mega_138k/first_test`.
- I24-S01 identity and I24-S02 pin evidence are still blocked, so report
  parsing is currently exercised through fixtures.
- The release generated-clock profile remains blocked until I28-S02/I28-S04
  close the PLL wrapper and timing-evidence path.

## Handoffs

- I28-S04 should consume worst slack, margin warnings, clock summary, and
  selected clock profile when tracking maximum passing frequency.
- I28-S05 should archive parsed utilization, warnings, port assignments, and
  bitstream identity in the reproducible FPGA build profile.
- I24-S03 remains the physical build handoff gate and can continue to reject
  incomplete report bundles before programming.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The parser extracts slack. | Met by `worst_slack_ns`. |
| The parser extracts utilization. | Met by parsed `LUT`, `Register`, and optional BRAM metrics. |
| The parser extracts unconstrained paths. | Met by `unconstrained_paths`. |
| The parser extracts ports. | Met by required port assignment records. |
| The parser extracts warnings. | Met by `warning_lines`. |
| The parser extracts bitstream identity. | Met by path, size, and SHA-256 records. |
| The parser extracts clock summary. | Met by clock-name, MHz, period, and source-line records. |
| CI-style checks fail on policy violations. | Met by `failed` audits and named policy violations. |

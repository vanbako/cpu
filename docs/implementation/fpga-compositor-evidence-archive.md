# FPGA Compositor Evidence Archive

Story: I36-S06

Status: archive gate defined; physical evidence is blocked until a concrete
Gowin report bundle and external-memory evidence archive are captured

Structured gate:

```text
python tools\fpga_compositor_evidence.py --check
```

Inspect the archive contract, template, or default audit:

```text
python tools\fpga_compositor_evidence.py --json
python tools\fpga_compositor_evidence.py --template
python tools\fpga_compositor_evidence.py --fields
python tools\fpga_compositor_evidence.py --blockers
python tools\fpga_compositor_evidence.py --audit-default
```

Audit a captured archive:

```text
python tools\fpga_compositor_evidence.py --audit docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt
```

Required gates:

```text
python tools\fpga_compositor_demo.py --check
python tools\fpga_gowin_reports.py --check
python tools\fpga_external_memory_evidence.py --check
```

## Archive Path

The expected evidence record is:

```text
docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt
```

The default audit reports `blocked` while that file is absent. A passing archive
must be a key-value record generated from the template and must end with
`archive_result=compositor_evidence_archived`.

## Required Metrics

The evidence record captures:

| Metric | Required value or rule |
| --- | --- |
| `pixel_clock_hz` | `74250000`, the 74.25 MHz 720p pixel clock. |
| `bandwidth_scenario` | `two_plane_xrgb8888`. |
| `required_bandwidth_bytes_per_second` | `594,000,000 bytes/s`. |
| `required_cells_per_second` | `99,000,000 48-bit cells/s` by derivation from 6-byte CPU cells. |
| `line_buffer_required_cells` | Derived from two XRGB8888 active lines. |
| `line_buffer_allocated_cells` | Must cover the line-buffer depth. |
| `utilization_lut`, `utilization_register`, `utilization_bram` | Nonnegative values from the parsed Gowin utilization report. |
| `timing_slack_ns` | Nonnegative worst slack from the parsed Gowin timing report. |
| `underflow_counter_one_plane` | `0`. |
| `underflow_counter_overlay` | `0`. |
| `underflow_counter_error` | Nonzero, proving the deterministic error path. |

The line-buffer depth comes from the I36-S01 policy:
`VIDEO_UNDERFLOW_COUNT` is the status counter that must be archived with the
one-plane, overlay, swap, and error-path demos.

## Links

Required archive links:

- `timing_report_bundle`: Gowin timing and utilization report root for the
  compositor build.
- `gowin_report_audit`: I28-S03 parser audit output from
  `python tools\fpga_gowin_reports.py --check` or a captured audit JSON.
- `external_memory_evidence`: I29-S05 external-memory evidence archive from
  `python tools\fpga_external_memory_evidence.py --check`.

The `ddr_calibration_dependency` field must mention `controller_ready` and
point back to the I29-S05 DDR calibration evidence. This prevents the
compositor archive from claiming enough bandwidth before DDR calibration and
external-memory testing are dispositioned.

## Reduced Mode

If `available_bandwidth_bytes_per_second` is below the
`594,000,000 bytes/s` two-plane requirement, the archive cannot pass with
`reduced_mode_fallback=none`. It must name a concrete fallback such as a lower
resolution, fewer planes, RGB565-only scanout, or a BRAM-only fixture, then file
residual blockers and retest commands.

## Handoff

I36-S07 consumes this archive before claiming first board compositor evidence.
The board run must link this timing, bandwidth, resource, DDR calibration,
underflow, and reduced-mode disposition alongside visible capture or blocker
evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Pixel clock and memory bandwidth assumptions are recorded. | Met by `pixel_clock_hz`, `bandwidth_scenario`, and required bandwidth fields. |
| Line-buffer depth and underflow counters are archived. | Met by line-buffer fields plus `VIDEO_UNDERFLOW_COUNT` demo counters. |
| Resource and timing evidence is required. | Met by Gowin utilization fields, `timing_slack_ns`, and `timing_report_bundle`. |
| DDR calibration dependency is explicit. | Met by `external_memory_evidence` and `ddr_calibration_dependency`. |
| Reduced-mode fallback is captured when bandwidth is insufficient. | Met by `reduced_mode_fallback` and residual-blocker audit rules. |

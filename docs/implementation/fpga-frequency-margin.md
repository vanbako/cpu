# FPGA Frequency Margin

Story: I28-S04

Structured gate:

```text
python tools\fpga_frequency_margin.py --check
```

Related gates:

```text
python tools\fpga_gowin_reports.py --check
python tools\fpga_clock_profiles.py --check
```

Evidence template:

```text
python tools\fpga_frequency_margin.py --template
```

## Scope

I28-S04 tracks first-test frequency sweep results and records the conservative
clock defaults used for bring-up and debug. It consumes I28-S03 parsed Gowin
report audits rather than raw timing text. A passing sweep point records the
clock profile, requested frequency, report status, worst slack, target-margin
status, bitstream_sha256, policy violations, and margin warnings.

The repository currently has no physical Gowin sweep evidence, so the default
summary is `documented_blocker`. Both `selected_debug_default_hz` and
`selected_release_default_hz` remain at 25 MHz using `debug_direct_25mhz`.

## Default Policy

| Field | Value |
| --- | --- |
| Current clock profile | `debug_direct_25mhz` |
| Debug default | 25 MHz |
| Release default | 25 MHz |
| Evidence path | `docs/implementation/evidence/i28_s04_frequency_sweep.json` |
| Maximum passing clock | None until parsed report evidence exists |

If a future frequency sweep records a higher maximum passing build, the maximum
passing value is stored separately from the selected defaults. The lower 25 MHz
default stays selected for bring-up and debug until a later policy change has
real timing margin and reset/CDC evidence.

## Frequency Sweep Record

Each point uses:

```text
profile_id
requested_hz
build_root
report_status
worst_slack_ns
target_margin_met
bitstream_sha256
policy_violations
margin_warnings
notes
```

Use:

```text
python tools\fpga_frequency_margin.py --audit-reports build\fpga\tang_mega_138k\first_test --requested-hz 25000000
```

to convert one I28-S03 report audit into a sweep summary point. The command
does not replace the evidence archive; it prints the JSON that can be copied
into `docs/implementation/evidence/i28_s04_frequency_sweep.json` after a real
Gowin build exists.

## Current Blockers

- No physical Gowin frequency sweep evidence has been captured in
  `docs/implementation/evidence`.
- I24-S01 identity and I24-S02 pin evidence are still blocked.
- Keep debug and release defaults at 25 MHz until parsed report evidence
  exists.

## Handoffs

- I28-S05 must archive the selected clock profile, parsed report bundle,
  bitstream hash, and sweep summary.
- I29 external-memory work must not raise the board default before I28 timing
  margin is recorded.
- `release_pll_25mhz` remains conservative until PLL/reset evidence and
  passing reports exist.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Frequency sweep results identify the highest passing build. | Met by `maximum_passing_hz` when passing points exist. |
| Documented blockers are recorded when no sweep exists. | Met by default `documented_blocker` status. |
| A lower default clock is selected for bring-up/debug. | Met by 25 MHz `selected_debug_default_hz`. |
| Release default remains conservative. | Met by 25 MHz `selected_release_default_hz`. |
| Parsed report evidence drives the sweep. | Met by the I28-S03 `--audit-reports` handoff. |

# FPGA First-Pass Build Bundle

Story: I31-S01

Status: Bundle gate implemented; captured bundle blocked

## Command

Validate the first-pass bundle profile:

```text
python tools\fpga_first_pass_bundle.py --check
```

Print a bundle template:

```text
python tools\fpga_first_pass_bundle.py --template
```

Audit a captured bundle record:

```text
python tools\fpga_first_pass_bundle.py --audit docs\implementation\evidence\i31_s01_first_pass_build_bundle.txt
```

Required upstream gates:

```text
python tools\fpga_soc_top_archive.py --check
python tools\fpga_reproducible_build.py --check
python tools\fpga_board_identity.py --check
python tools\fpga_constraints_overlay.py --check
```

## Scope

I31-S01 freezes the first-pass board build bundle before the integrated SoC top
is handed to Gowin. It does not claim synthesis, timing, bitstream generation,
SRAM programming, or physical LED/UART/probe evidence. Those remain I31-S02 and
later board-run stories.

The expected bundle record is:

```text
docs/implementation/evidence/i31_s01_first_pass_build_bundle.txt
```

The default audit is `blocked` until that record exists. Once captured, the
record freezes the selected `cpu_v01_fpga_top`, the built-in first-test image,
the final CST/SDC paths, `debug_direct_25mhz`, idle loader status, expected
LED/UART/probe signatures, and the exact retest commands.

## Frozen Selection

| Field | Value |
| --- | --- |
| `top_module` | `cpu_v01_fpga_top` |
| `selected_image` | `builtin.first_test_pause_stream` |
| `constraints_cst` | `constraints/tang_mega_138k_first_test.cst` |
| `constraints_sdc` | `constraints/tang_mega_138k_first_test.sdc` |
| `clock_profile` | `debug_direct_25mhz` |
| `loader_status` | `idle_disabled_for_first_pass_build` |
| `gowin_build_root` | `build/fpga/tang_mega_138k/first_test` |
| `bundle_result` | `frozen_for_gowin` |

The selected image is the I23-S04 built-in PAUSE stream carried by the
`reset_pass.first_test_pause_stream` smoke-corpus case. The loader path is held
idle for the first pass so I31-S02 validates the fixed image and top-level
integration before live loading is involved.

## Required Record Fields

| Field | Requirement |
| --- | --- |
| `story` | Must be `I31-S01`. |
| `prepared_at` | Local bundle timestamp. |
| `repository_commit` | Repository commit used for the bundle. |
| `board`, `device`, `package` | Must match the Tang Mega 138K target profile. |
| `soc_top_archive` | I30-S06 closure archive path. |
| `reproducible_build_manifest` | I28-S05 reproducible-build manifest path. |
| `board_identity` | I24-S01 identity evidence path. |
| `top_module` | Must be `cpu_v01_fpga_top`. |
| `selected_image` | Must be `builtin.first_test_pause_stream`. |
| `image_source` | Source note for the I23-S04 PAUSE stream. |
| `constraints_cst`, `constraints_sdc` | Final CST path and active SDC path. |
| `clock_profile` | Must be `debug_direct_25mhz`. |
| `loader_status` | Must be `idle_disabled_for_first_pass_build`. |
| `expected_led_signature` | Frozen pass/fail/heartbeat LED expectation. |
| `expected_uart_signature` | Frozen UART/status packet expectation. |
| `expected_probe_signature` | Frozen optional GAO/ILA probe expectation. |
| `gowin_build_root` | Must be `build/fpga/tang_mega_138k/first_test`. |
| `bundle_result` | Must be `frozen_for_gowin`. |
| `remaining_blockers` | `none` before I31-S02 handoff. |
| `retest_commands` | Commands to rerun the upstream gates and Gowin build gate. |

## Expected Signatures

The bundle consumes the I26-S05 `reset_pass.first_test_pause_stream` signature:

- LED: heartbeat toggles, pass asserts, fail remains deasserted.
- UART: pass flag set, retire count at least 8, fault code zero.
- Probe: retire sequence reaches the pass threshold with no sticky fault.

These are expectations for later capture. They are not physical evidence until
I31-S03 records programming and board observations against an exact bitstream.

## Retest Commands

The bundle must preserve commands sufficient to rebuild or reject the handoff:

```text
python tools\fpga_soc_top_archive.py --check
python tools\fpga_reproducible_build.py --check
python tools\fpga_board_identity.py --check
python tools\fpga_constraints_overlay.py --check
python tools\fpga_clock_profiles.py --check
python tools\fpga_smoke_corpus.py --check
python tools\fpga_gowin_build.py --check
```

## Status Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `frozen` | A complete bundle exists with `bundle_result=frozen_for_gowin`, no remaining blockers, and exact selections. | I31-S02 may consume it for Gowin build and timing audit. |
| `blocked` | No bundle record exists yet. | Capture the bundle only after closure archive and board identity inputs are ready. |
| `invalid` | Required fields, selections, or evidence links are missing or malformed. | Fix the key=value record and rerun the audit. |
| `needs_followup` | A bundle exists, but result or blocker disposition is not clean. | Resolve blockers before I31-S02. |

## Handoff

I31-S02 consumes only a `frozen` I31-S01 bundle. I31-S02 owns Gowin synthesis,
place-route, timing, utilization, port, warning, bitstream path, and bitstream
hash evidence. I31-S03 owns SRAM programming and the first physical LED, UART,
and probe observations.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Selected top is frozen. | Met by `top_module=cpu_v01_fpga_top` and the I30-S06 archive link. |
| Selected image is frozen. | Met by `selected_image=builtin.first_test_pause_stream`. |
| Constraints and clock profile are frozen. | Met by the CST/SDC fields and `debug_direct_25mhz`. |
| Loader status is explicit. | Met by `loader_status=idle_disabled_for_first_pass_build`. |
| Expected LED/UART/probe signatures are explicit. | Met by `expected_led_signature`, `expected_uart_signature`, and `expected_probe_signature`. |
| Gowin build handoff is explicit. | Met by the I31-S02 handoff rule and retest commands. |

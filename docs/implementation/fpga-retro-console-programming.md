# FPGA Retro Console Programming

Story: I34-S04

Status: Retro Console 60K SRAM programming gate implemented; physical
programming and smoke observations remain blocked until board evidence exists.

Validate the programming profile:

```text
python tools\fpga_retro_console_programming.py --check
```

Print an evidence template:

```text
python tools\fpga_retro_console_programming.py --template
```

Audit a captured evidence record:

```text
python tools\fpga_retro_console_programming.py --audit docs\implementation\evidence\i34_s04_retro_console_programming.txt
```

Required upstream gates:

```text
python tools\fpga_retro_console_gowin.py --check
python tools\fpga_uart_status_streamer.py --check
python tools\fpga_probe_bundles.py --check
```

## Scope

I34-S04 records Retro Console 60K SRAM programming and smoke observations for
the exact I34-S03 bitstream. It requires programming log, reset release,
heartbeat, pass/fail outputs, UART/status packet or probe capture, and exact
bitstream identity. It must not claim a Tang Mega Dock with 138K SOM pass.

The expected evidence record is:

```text
docs/implementation/evidence/i34_s04_retro_console_programming.txt
```

## Required Record Fields

| Field | Requirement |
| --- | --- |
| `story` | Must be `I34-S04`. |
| `programmed_at` | Local programming timestamp. |
| `repository_commit` | Repository commit used for the board run. |
| `board` | Must match `Sipeed Tang Retro Console with 60K SOM`. |
| `retro_console_gowin` | I34-S03 evidence path. |
| `bitstream_path` | Exact Retro Console `.fs` bitstream path from I34-S03. |
| `bitstream_sha256` | 64-character SHA-256 of the programmed bitstream. |
| `programming_tool` | Gowin Programmer or approved equivalent. |
| `programming_mode` | Must be `SRAM`. |
| `programming_result` | Must be `success`. |
| `programming_log` | Captured programming log path. |
| `reset_released` | Must be `yes`. |
| `reset_observation` | Reset release log, photo, or probe path. |
| `observation_duration_s` | At least `10`. |
| `heartbeat_observed` | Must be `yes`. |
| `pass_output_observed` | `yes` or `no`. |
| `fail_output_observed` | `yes` or `no`. |
| `board_result` | `retro_console_smoke_pass` or `failure_observed`. |
| `uart_log` | Raw UART/status capture log path or `none`. |
| `uart_status_packet_hex` | 32-byte I25-S01 packet as 64 hex characters, or `none` when probe evidence carries the observation. |
| `decoded_status_packet` | Decoded packet record path, transcript, or `none`. |
| `probe_capture` | GAO/ILA or probe capture path, or `none`. |
| `status_retire_count` | Decoded or probe-derived retire count. |
| `status_fault_code` | Decoded or probe-derived fault code. |
| `pass_fail_state` | Decoded or observed pass/fail state. |
| `primary_138k_claim` | Must be `no`. |
| `retest_commands` | Commands to rerun Gowin, identity, UART status, and probe gates. |

## Evidence Format

```text
story=I34-S04
programmed_at=
repository_commit=
board=Sipeed Tang Retro Console with 60K SOM
retro_console_gowin=docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt
bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs
bitstream_sha256=
programming_tool=Gowin Programmer
programming_mode=SRAM
programming_result=success
programming_log=docs/implementation/evidence/i34_s04_programming.log
reset_released=yes
reset_observation=docs/implementation/evidence/i34_s04_reset_release.txt
observation_duration_s=10
heartbeat_observed=yes
pass_output_observed=yes
fail_output_observed=no
board_result=retro_console_smoke_pass
uart_log=docs/implementation/evidence/i34_s04_uart.log
uart_status_packet_hex=
decoded_status_packet=docs/implementation/evidence/i34_s04_status_packet.json
probe_capture=none
status_retire_count=
status_fault_code=
pass_fail_state=first_pass
primary_138k_claim=no
retest_commands=python tools\fpga_retro_console_gowin.py --check ; python tools\fpga_retro_console_identity.py --check ; python tools\fpga_uart_status_streamer.py --check ; python tools\fpga_probe_bundles.py --check
```

## Observation Rules

For `board_result=retro_console_smoke_pass`:

- `pass_output_observed=yes`;
- `fail_output_observed=no`;
- `pass_fail_state=first_pass`;
- `status_retire_count` is at least `8`;
- `status_fault_code=0`;
- `primary_138k_claim=no`.

For `board_result=failure_observed`, the record is still accepted as captured
evidence when programming succeeded, reset was released, heartbeat was seen,
and at least one of fail output, failed packet state, or nonzero fault code
names the failure. That handoff goes to I34-S05 for replay classification.

## UART And Probe Evidence

The record must include either `uart_status_packet_hex` plus `uart_log`, or a
concrete `probe_capture`. When a UART packet is present, it must decode as an
I25-S01 32-byte debug/status packet and match `pass_fail_state`,
`status_retire_count`, and `status_fault_code`.

## Status Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `observed` | SRAM programming succeeded and reset, heartbeat, pass/fail, UART/probe evidence, bitstream identity, and 138K non-claim guard are captured. | Hand `retro_console_smoke_pass` to I34-S06 or `failure_observed` to I34-S05. |
| `blocked` | I34-S03 is not passed, or no observation record exists. | Complete Gowin evidence, program SRAM, and capture board observations. |
| `invalid` | Required fields, links, bitstream hash, 138K claim guard, or UART packet decode are malformed. | Fix or recapture the evidence record. |
| `needs_capture` | Programming record exists but reset, heartbeat, pass/fail, duration, UART/probe, or result evidence is insufficient. | Recapture reset, LED/UART, or probe evidence. |

## Retest Commands

```text
python tools\fpga_retro_console_gowin.py --check
python tools\fpga_retro_console_identity.py --check
python tools\fpga_uart_status_streamer.py --check
python tools\fpga_probe_bundles.py --check
```

## Handoff

I34-S05 consumes `failure_observed` evidence for replay mapping and failure
classification. I34-S06 consumes `retro_console_smoke_pass` evidence or the
classified failure disposition while preserving the active Tang Mega Dock with
138K SOM first CPU handoff policy.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Programming log is required. | Met by `programming_log`. |
| Reset release is required. | Met by `reset_released` and `reset_observation`. |
| Heartbeat and pass/fail are recorded. | Met by `heartbeat_observed`, `pass_output_observed`, and `fail_output_observed`. |
| UART/status packet or probe evidence is required. | Met by `uart_status_packet_hex`, `uart_log`, and `probe_capture`. |
| Evidence is tied to the exact bitstream. | Met by `bitstream_path` and `bitstream_sha256`. |
| The 138K first-pass board is not claimed. | Met by `primary_138k_claim=no` and the audit guard. |
| Downstream pass/failure handoff is explicit. | Met by the I34-S05 and I34-S06 handoff rules. |

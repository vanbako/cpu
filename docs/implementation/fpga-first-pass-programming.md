# FPGA First-Pass Programming

Story: I31-S03

Status: Integrated CPU programming gate implemented; board observation blocked

## Command

Validate the programming observation profile:

```text
python tools\fpga_first_pass_programming.py --check
```

Print an evidence template:

```text
python tools\fpga_first_pass_programming.py --template
```

Audit a captured evidence record:

```text
python tools\fpga_first_pass_programming.py --audit docs\implementation\evidence\i31_s03_integrated_cpu_programming.txt
```

Required upstream gates:

```text
python tools\fpga_first_pass_gowin.py --check
python tools\fpga_board_programming.py --check
python tools\fpga_uart_status_streamer.py --check
python tools\fpga_probe_bundles.py --check
```

## Scope

I31-S03 records the first integrated CPU SRAM programming observation for the
exact I31-S02 bitstream. It does not classify failures or archive final board
closure. I31-S04 consumes captured failures for replay classification, and
I31-S05 consumes a first-pass observation or blocker disposition for archive.

The expected evidence record is:

```text
docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt
```

The default audit is `blocked` until the record exists and I31-S02 has a
passing Gowin evidence record. The evidence must bind programming, reset
release, heartbeat, pass/fail LEDs, UART/status packets, and optional probes to
the exact `bitstream_sha256`.

## Required Record Fields

| Field | Requirement |
| --- | --- |
| `story` | Must be `I31-S03`. |
| `programmed_at` | Local programming timestamp. |
| `repository_commit` | Repository commit used for the board run. |
| `board` | Must match `Sipeed Tang Mega Dock with 138K SOM`. |
| `first_pass_gowin` | I31-S02 evidence path. |
| `top_module` | Must be `cpu_v01_fpga_top`. |
| `selected_image` | Must be `builtin.first_test_pause_stream`. |
| `bitstream_path` | Exact `.fs` bitstream path from I31-S02. |
| `bitstream_sha256` | 64-character SHA-256 of the programmed bitstream. |
| `programming_tool` | Gowin Programmer or approved equivalent. |
| `programming_mode` | Must be `SRAM`. |
| `programming_result` | Must be `success`. |
| `programming_log` | Captured programming log path. |
| `reset_released` | Must be `yes`. |
| `reset_observation` | Reset release log, photo, or probe path. |
| `observation_duration_s` | At least `10`. |
| `heartbeat_observed` | Must be `yes`. |
| `pass_led_observed` | `yes` or `no`. |
| `fail_led_observed` | `yes` or `no`. |
| `board_result` | `first_pass` or `failure_observed`. |
| `uart_log` | Raw UART/status capture log path. |
| `uart_status_packet_hex` | 32-byte I25-S01 packet as 64 hex characters. |
| `decoded_status_packet` | Decoded packet record path or transcript. |
| `status_retire_count` | Decoded retire count. |
| `status_fault_code` | Decoded fault code. |
| `pass_fail_state` | Decoded packet pass/fail state. |
| `probe_capture` | Optional GAO/ILA or probe capture path; `none` is allowed. |
| `retest_commands` | Commands to rerun Gowin, programming, UART status, and probe gates. |

## Observation Rules

For `board_result=first_pass`:

- `pass_led_observed=yes`;
- `fail_led_observed=no`;
- `pass_fail_state=first_pass`;
- `status_retire_count` is at least `8`;
- `status_fault_code=0`.

For `board_result=failure_observed`, the record is still accepted as captured
evidence when programming succeeded, reset was released, heartbeat was seen,
and at least one of fail LED, failed packet state, or nonzero fault code names
the failure. That handoff goes to I31-S04 for replay classification.

## UART And Probe Evidence

The UART packet must decode as an I25-S01 32-byte debug/status packet. The
decoded `pass_fail_state`, `status_retire_count`, and `status_fault_code`
fields must match the record. `probe_capture` is optional, but when present it
should use the I25-S03 clock/reset, status-packet, or memory-handshake probe
bundles.

## Status Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `observed` | Programming succeeded and reset, LEDs, UART/status packet, bitstream identity, and pass/fail result are captured. | Hand `first_pass` to I31-S05 or `failure_observed` to I31-S04. |
| `blocked` | I31-S02 is not passed, or no observation record exists. | Complete Gowin evidence, program SRAM, and capture board observations. |
| `invalid` | Required fields, links, bitstream hash, or UART packet decode are malformed. | Fix or recapture the evidence record. |
| `needs_capture` | Programming record exists but reset, heartbeat, pass/fail, duration, or result evidence is insufficient. | Recapture reset, LED, UART, or probe evidence. |

## Retest Commands

```text
python tools\fpga_first_pass_gowin.py --check
python tools\fpga_board_programming.py --check
python tools\fpga_uart_status_streamer.py --check
python tools\fpga_probe_bundles.py --check
```

## Handoff

I31-S04 consumes `failure_observed` evidence for replay mapping and failure
classification. I31-S05 consumes `first_pass` evidence or the classified
failure disposition for the final first physical single-core CPU archive.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Programming log is required. | Met by `programming_log`. |
| Reset release is required. | Met by `reset_released` and `reset_observation`. |
| Heartbeat and pass/fail are recorded. | Met by `heartbeat_observed`, `pass_led_observed`, and `fail_led_observed`. |
| UART/status packet evidence is required. | Met by `uart_status_packet_hex`, `uart_log`, and `decoded_status_packet`. |
| Optional probe capture is supported. | Met by `probe_capture` and the I25-S03 handoff. |
| Evidence is tied to the exact bitstream. | Met by `bitstream_path` and `bitstream_sha256`. |
| Downstream pass/failure handoff is explicit. | Met by the I31-S04 and I31-S05 handoff rules. |

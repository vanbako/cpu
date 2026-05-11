# FPGA Board Programming

Story: I24-S04

Status: Programming evidence gate implemented; physical board run blocked

Structured gate:

```text
python tools\fpga_board_programming.py --check
```

Evidence template:

```text
python tools\fpga_board_programming.py --template
```

Evidence audit:

```text
python tools\fpga_board_programming.py --audit-evidence docs\implementation\evidence\i24_s04_sram_programming.txt
```

## Purpose

I24-S04 is the first physical programming and observation story. It programs
the audited first-test `.fs` bitstream into SRAM, releases `board_reset_n_i`,
and records whether `heartbeat_led_o`, `pass_led_o`, and `fail_led_o` match
the expected first-test behavior.

This story is currently `blocked`: I24-S03 must pass
`python tools\fpga_gowin_build.py --check` and
`python tools\fpga_gowin_build.py --audit-reports` before any SRAM programming
can count as evidence.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_programming.py` | Structured I24-S04 programming profile, evidence parser, audit rules, and validator. |
| `tools/fpga_board_programming.py` | CLI wrapper for checking, printing JSON, printing the evidence template, and auditing programming evidence. |
| `tests/conformance/test_i24_s04_fpga_board_programming.py` | Conformance tests for evidence fields, blocked/default audit, pass/fail observations, CLI output, and docs. |
| `docs/implementation/fpga-board-programming.md` | This implementation note. |

## Evidence Format

The record lives at
`docs/implementation/evidence/i24_s04_sram_programming.txt` and uses:

```text
story=I24-S04
board=Sipeed Tang Mega Dock with 138K SOM
gowin_build_root=build/fpga/tang_mega_138k/first_test
bitstream_path=
programming_tool=Gowin Programmer
programming_mode=SRAM
programming_result=
programmed_at=
programming_log=
reset_released=
observation_duration_s=10
heartbeat_observed=
pass_led_observed=
fail_led_observed=
led_evidence=
status_retire_count=
status_fault_code=
```

## Pass Rules

| Field | Required result |
| --- | --- |
| `programming_mode` | `SRAM`; flash programming is deferred until SRAM passes repeatably. |
| `programming_result` | `success`. |
| `reset_released` | `yes`; the observation starts after `board_reset_n_i` is released. |
| `observation_duration_s` | At least `10`. |
| `heartbeat_observed` | `yes`, proving clock/reset/retire progress. |
| `pass_led_observed` | `yes`, proving the smoke firmware reached pass. |
| `fail_led_observed` | `no`, proving no fail indication was observed during the pass window. |
| `status_retire_count` | At least `8`. |
| `status_fault_code` | `0`. |
| `programming_log` | Path to the captured programming log. |
| `led_evidence` | Photo, video, or probe capture path. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `passed` | I24-S03 passed and the programming/observation evidence matches every pass rule. | Archive the evidence in I24-S05. |
| `failed` | Evidence was captured but programming, reset, heartbeat, pass, fail, retire, or fault observations did not match. | Triage the board run and do not archive it as a first pass. |
| `invalid` | Required evidence fields are missing or malformed. | Fix or recapture the evidence record. |
| `blocked` | I24-S03 has not passed or no programming evidence exists. | Do not program SRAM yet, or capture the missing evidence after prerequisites pass. |

I24-S05 first-board evidence archiving is tracked in
`docs/implementation/fpga-first-board-evidence.md` and checked with
`python tools\fpga_first_board_archive.py --check`.

## Current Blocker

- I24-S03 Gowin report audit is not `passed`.
- No SRAM programming log is captured.
- No reset observation, LED/probe evidence, `status_retire_count`, or
  `status_fault_code` evidence is captured.
- I24-S05 must not archive a board pass until this audit is `passed`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Programming uses the exact audited bitstream. | Met by `gowin_build_root` and `bitstream_path` fields. |
| SRAM mode is required before flash programming. | Met by the `programming_mode=SRAM` audit rule. |
| Reset handling is recorded. | Met by `reset_released` and the `board_reset_n_i` observation requirement. |
| Pass/fail/heartbeat observations are captured. | Met by `heartbeat_observed`, `pass_led_observed`, `fail_led_observed`, and `led_evidence`. |
| Retire/fault probes are captured when available. | Met by required `status_retire_count` and `status_fault_code`. |
| First-pass evidence has a handoff. | Met by the I24-S05 archive action on `passed`. |

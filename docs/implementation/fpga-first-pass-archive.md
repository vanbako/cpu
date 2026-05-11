# FPGA First-Pass Archive

Story: I31-S05

Status: First physical CPU pass/archive gate implemented; physical evidence blocked

Structured gate:

```text
python tools\fpga_first_pass_archive.py --check
```

Evidence template:

```text
python tools\fpga_first_pass_archive.py --template
```

Evidence audit:

```text
python tools\fpga_first_pass_archive.py --audit docs\implementation\evidence\i31_s05_first_cpu_pass_archive.txt
```

## Purpose

I31-S05 is the final archive record for the first physical integrated
single-core CPU run. It accepts either a clean `first_pass_archived` result from
I31-S03 or a `blocker_disposition_archived` result backed by I31-S04 replay
classification. In both cases the archive links board identity, constraints,
Gowin reports, bitstream identity, programming, reset, LED/UART/probe evidence,
pass/fail result, residual blockers, filed issues, and retest steps.

The archive does not claim a board pass while physical evidence is absent. The
default audit is `blocked` until I24-S05 and I31-S03 evidence exist, and failure
closure remains blocked until I31-S04 has classified the replay.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_first_pass_archive.py` | Structured I31-S05 archive profile, parser, audit rules, template, and validator. |
| `tools/fpga_first_pass_archive.py` | CLI wrapper for check, JSON, template, fields, retest commands, and archive audit. |
| `tests/conformance/test_i31_s05_fpga_first_pass_archive.py` | Conformance coverage for first-pass and blocker archive paths, CLI, docs, and dependencies. |
| `docs/implementation/fpga-first-pass-archive.md` | This implementation note. |

## Evidence Format

The archive record lives at
`docs/implementation/evidence/i31_s05_first_cpu_pass_archive.txt` and uses:

```text
story=I31-S05
archived_at=
repository_commit=
board=Sipeed Tang Mega Dock with 138K SOM
first_board_archive=docs/implementation/evidence/i24_s05_first_board_archive.txt
first_board_archive_status=archived
identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt
constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt
gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl
bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs
bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
programming_evidence=docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt
programming_status=observed
programming_board_result=first_pass
programming_log=docs/implementation/evidence/i31_s03_programming.log
reset_observation=docs/implementation/evidence/i31_s03_reset_release.txt
led_evidence=docs/implementation/evidence/i31_s03_leds.mp4
uart_log=docs/implementation/evidence/i31_s03_uart.log
decoded_status_packet=docs/implementation/evidence/i31_s03_status_packet.json
probe_capture=none
replay_classification=not_required_first_pass
replay_status=not_required
replay_case_id=none
first_mismatch=none
debug_evidence=none
pass_fail_result=first_pass
archive_result=first_pass_archived
residual_blockers=none
filed_issues=none
retest_steps=python tools\fpga_first_board_archive.py --check ; python tools\fpga_first_pass_programming.py --check ; python tools\fpga_first_pass_replay.py --check
```

For a failure disposition, set `archive_result=blocker_disposition_archived`,
`programming_board_result=failure_observed`, `pass_fail_result=failure_observed`,
`first_board_archive_status=needs_followup`, link
`replay_classification=docs/implementation/evidence/i31_s04_failure_replay_classification.txt`,
set `replay_status=classified`, preserve `replay_case_id` and `first_mismatch`,
and record concrete `residual_blockers`, `filed_issues`, and `retest_steps`.

## Required Gates

| Gate | Command | Role |
| --- | --- | --- |
| First-board archive | `python tools\fpga_first_board_archive.py --check` | Supplies scan, constraints, reports, bitstream, programming, reset, and LED evidence links. |
| First-pass programming | `python tools\fpga_first_pass_programming.py --check` | Supplies the pass/failure result, programming log, reset, LEDs, UART/status, and probes. |
| First-pass replay | `python tools\fpga_first_pass_replay.py --check` | Required for `failure_observed` blocker disposition and `first_mismatch` preservation. |

## Result Rules

| Archive result | Required programming result | Replay and blocker requirement |
| --- | --- | --- |
| `first_pass_archived` | `programming_status=observed` and `programming_board_result=first_pass`. | `replay_status=not_required`, `residual_blockers=none`, `filed_issues=none`, and concrete `retest_steps`. |
| `blocker_disposition_archived` | `programming_status=observed` and `programming_board_result=failure_observed`. | `replay_status=classified`, `replay_case_id`, `first_mismatch`, `residual_blockers`, `filed_issues`, and concrete `retest_steps`. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `archived` | First pass or classified blocker disposition has all required evidence links. | Hand to I31-S06 and later release-candidate evidence. |
| `needs_followup` | Evidence exists but blockers, filed issues, or retest steps are incomplete. | File blockers and record retest commands. |
| `invalid` | Required fields, links, bitstream hash, result consistency, or replay disposition are malformed. | Fix the archive record and rerun the audit. |
| `blocked` | I24-S05, I31-S03, or needed I31-S04 evidence is absent. | Capture the upstream board evidence before closure. |

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Scan, reports, and bitstream are linked. | Met by `identity_evidence`, `constraints_evidence`, `gowin_report_bundle`, `bitstream_path`, and `bitstream_sha256`. |
| Programming, reset, LED/UART/probe evidence are linked. | Met by `programming_evidence`, `programming_log`, `reset_observation`, `led_evidence`, `uart_log`, `decoded_status_packet`, and `probe_capture`. |
| Replay and first mismatch are linked for failures. | Met by `replay_classification`, `replay_status`, `replay_case_id`, and `first_mismatch`. |
| Pass/fail result is explicit. | Met by `pass_fail_result` and `archive_result`. |
| Residual blockers, filed issues, and retest steps are captured. | Met by `residual_blockers`, `filed_issues`, and `retest_steps`. |
| Downstream retest matrix has a stable handoff. | Met by the `archived` action to I31-S06. |

# FPGA Retro Console Archive

Story: I34-S06

Status: Retro Console 60K pass/blocker archive gate implemented; physical
archive evidence remains blocked until board observations exist.

Structured gate:

```text
python tools\fpga_retro_console_archive.py --check
```

Evidence template:

```text
python tools\fpga_retro_console_archive.py --template
```

Evidence audit:

```text
python tools\fpga_retro_console_archive.py --audit docs\implementation\evidence\i34_s06_retro_console_archive.txt
```

## Purpose

I34-S06 archives either a Retro Console 60K smoke pass or a classified blocker.
The archive links board scan, constraints, Gowin reports, bitstream identity,
SRAM programming, reset, LED/UART/probe observations, replay results, residual
blockers, filed issues, retest commands, and the board handoff policy. It must
not claim the Tang Mega Dock with 138K SOM path; `primary_138k_claim=no` and
`primary_138k_path_status=i31_i32_continue_on_tang_mega_138k` keep the I31/I32
path active while the Retro Console result is archived.

The gate also links I32-S05 interactive corpus readiness so future monitor
sessions can reuse the same board-program selection once the 60K path is no
longer deferred or blocked.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_retro_console_archive.py` | Structured I34-S06 profile, template, parser, audit rules, pass/blocker policy, and validator. |
| `tools/fpga_retro_console_archive.py` | CLI wrapper for checking, JSON, template, field list, retest commands, and evidence audit. |
| `tests/conformance/test_i34_s06_fpga_retro_console_archive.py` | Conformance coverage for dependencies, pass/blocker archives, handoff policy, CLI output, and docs. |
| `docs/implementation/fpga-retro-console-archive.md` | This implementation note. |

## Evidence Format

The archive record lives at
`docs/implementation/evidence/i34_s06_retro_console_archive.txt` and uses:

```text
story=I34-S06
archived_at=
repository_commit=
board=Sipeed Tang Retro Console with 60K SOM
identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt
identity_status=alternate_target_verified
constraints_evidence=docs/implementation/evidence/i34_s02_retro_console_constraints.txt
constraints_status=confirmed
gowin_evidence=docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt
gowin_status=passed
gowin_report_bundle=build/fpga/tang_60k_retro_console/first_test/impl
bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs
bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
programming_evidence=docs/implementation/evidence/i34_s04_retro_console_programming.txt
programming_status=observed
programming_board_result=retro_console_smoke_pass
programming_log=docs/implementation/evidence/i34_s04_programming.log
reset_observation=docs/implementation/evidence/i34_s04_reset_release.txt
led_evidence=docs/implementation/evidence/i34_s04_leds.mp4
uart_log=docs/implementation/evidence/i34_s04_uart.log
decoded_status_packet=docs/implementation/evidence/i34_s04_status_packet.json
probe_capture=none
replay_classification=not_required_retro_console_smoke_pass
replay_status=not_required
replay_case_id=none
first_mismatch=none
failure_class=none
interactive_corpus=python tools\fpga_interactive_corpus.py --check
interactive_corpus_status=published_interactive_board_program_corpus
pass_fail_result=retro_console_smoke_pass
archive_result=retro_console_pass_archived
retro_console_handoff_policy=retro_console_ready_with_138k_i31_i32_active
primary_138k_claim=no
primary_138k_path_status=i31_i32_continue_on_tang_mega_138k
residual_blockers=none
filed_issues=none
retest_steps=python tools\fpga_retro_console_identity.py --check ; python tools\fpga_retro_console_constraints.py --check ; python tools\fpga_retro_console_gowin.py --check ; python tools\fpga_retro_console_programming.py --check ; python tools\fpga_retro_console_replay.py --check ; python tools\fpga_interactive_corpus.py --check
```

## Required Gates

| Gate | Command | Role |
| --- | --- | --- |
| Identity | `python tools\fpga_retro_console_identity.py --check` | Supplies board scan, marking, device, and package evidence. |
| Constraints | `python tools\fpga_retro_console_constraints.py --check` | Supplies Retro Console CST/SDC and pin evidence. |
| Gowin build | `python tools\fpga_retro_console_gowin.py --check` | Supplies report bundle, timing, ports, bitstream path, and bitstream hash. |
| Programming | `python tools\fpga_retro_console_programming.py --check` | Supplies SRAM programming, reset, LED, UART/status, and probe observations. |
| Replay | `python tools\fpga_retro_console_replay.py --check` | Supplies classified failure replay evidence when the board result is `failure_observed`. |
| Interactive corpus | `python tools\fpga_interactive_corpus.py --check` | Preserves the I32-S05 program corpus handoff for future monitor sessions. |

## Archive Results

| Archive result | Required result | Replay requirement | Blocker policy |
| --- | --- | --- | --- |
| `retro_console_pass_archived` | `pass_fail_result=retro_console_smoke_pass` | `replay_status=not_required` and `replay_classification=not_required_retro_console_smoke_pass`. | `residual_blockers=none` and `filed_issues=none`. |
| `retro_console_blocker_archived` | `pass_fail_result=failure_observed` | `replay_status=classified`, `replay_case_id`, `failure_class`, and `first_mismatch` from I34-S05. | Concrete `residual_blockers`, `filed_issues`, and `retest_steps`. |

## Handoff Policy

`retro_console_handoff_policy` is one of:

- `retro_console_ready_with_138k_i31_i32_active` for an archived smoke pass that
  still keeps the I31/I32 Tang Mega Dock with 138K SOM path active.
- `retro_console_deferred_while_138k_i31_i32_active` for an archived blocker
  that keeps the 60K path deferred while I31/I32 continue on the 138K board.

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `archived` | Retro Console pass or blocker evidence is internally consistent and has handoff policy. | Hand the archive to release traceability and future board planning. |
| `needs_followup` | Blocker archive lacks filed issues, residual blocker names, or retest steps. | File blockers and record concrete rerun steps. |
| `invalid` | Required fields, links, bitstream hash, pass/blocker result, replay, or 138K guard fields are malformed. | Fix the archive record and rerun the audit. |
| `blocked` | I34-S04 has not captured a pass/failure observation or no archive record exists. | Complete Retro Console programming, replay failures through I34-S05, then archive. |

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Board scan, constraints, reports, and bitstream are linked. | Met by `identity_evidence`, `constraints_evidence`, `gowin_report_bundle`, `bitstream_path`, and `bitstream_sha256`. |
| Programming and LED/UART/probe captures are linked. | Met by `programming_evidence`, `programming_log`, `reset_observation`, `led_evidence`, `uart_log`, `decoded_status_packet`, and `probe_capture`. |
| Replay results are linked for failures. | Met by `replay_classification`, `replay_status`, `replay_case_id`, `failure_class`, and `first_mismatch`. |
| Residual blockers and retest commands are archived. | Met by `residual_blockers`, `filed_issues`, and `retest_steps`. |
| The 60K path handoff remains explicit while I31/I32 continue on the 138K board. | Met by `retro_console_handoff_policy`, `primary_138k_claim=no`, and `primary_138k_path_status=i31_i32_continue_on_tang_mega_138k`. |
| I32-S05 remains linked. | Met by `interactive_corpus` and `interactive_corpus_status`. |

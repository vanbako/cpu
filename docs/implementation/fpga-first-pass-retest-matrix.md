# FPGA First-Pass Retest Matrix

Story: I31-S06

Status: Board retest matrix published

Structured gate:

```text
python tools\fpga_first_pass_retest_matrix.py --check
```

Print commands:

```text
python tools\fpga_first_pass_retest_matrix.py --commands
```

Print acceptance criteria:

```text
python tools\fpga_first_pass_retest_matrix.py --criteria
```

## Purpose

I31-S06 publishes the reproducible retest matrix for the first physical
integrated single-core CPU pass. It names the exact commands to rerun, the
required captures for each phase, the known board assumptions, rerun criteria,
and acceptance criteria for either `first_pass_archived` or
`blocker_disposition_archived` in I31-S05.

The matrix keeps the board retest decision separate from implementation
changes. It does not change RTL, firmware, or evidence formats; it tells the
next run what must be recaptured and what is sufficient to accept or rerun the
first CPU pass.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_first_pass_retest_matrix.py` | Structured I31-S06 matrix rows, commands, assumptions, criteria, renderer, and validator. |
| `tools/fpga_first_pass_retest_matrix.py` | CLI wrapper for check, JSON, command list, required captures, and criteria output. |
| `tests/conformance/test_i31_s06_fpga_first_pass_retest_matrix.py` | Conformance coverage for phases, commands, captures, assumptions, criteria, CLI, and docs. |
| `docs/implementation/fpga-first-pass-retest-matrix.md` | This implementation note. |

## Matrix

| Phase | Command | Required captures | Rerun criteria | Acceptance criteria |
| --- | --- | --- | --- | --- |
| `identity_constraints` | `python tools\fpga_first_board_archive.py --check` | I24-S01 identity evidence, I24-S02 CST overlay, I24-S03 report bundle and bitstream path. | Board, package, constraints, PLL, Gowin reports, pins, clocks, reset, LED, UART, or probe overlay changes. | I24-S05 links concrete scan, constraints, reports, bitstream, programming, reset, and LED evidence. |
| `sram_programming_observation` | `python tools\fpga_first_pass_programming.py --check` | `bitstream_sha256`, SRAM `programming_log`, `reset_observation`, heartbeat, pass/fail LEDs, UART log, decoded status packet, and optional probe capture. | Bitstream, image, constraints, reset, UART status transport, probes, programming log, reset release, heartbeat, LED, or UART evidence changes. | I31-S03 is `observed`; first pass has pass LED yes, fail LED no, `pass_fail_state=first_pass`, retire count at least 8, and fault code 0. |
| `failure_replay_classification` | `python tools\fpga_first_pass_replay.py --check` | Captured status packet, replay mapping, selected replay command, observed trace or `none`, `first_mismatch`, debug evidence, and filed issue. | Fail LED, failed status, nonzero fault, suspicious heartbeat/reset behavior, missing replay, missing `first_mismatch`, missing class, or missing issue. | I31-S04 is `classified` with class `clock_reset`, `memory`, `firmware`, `trap`, `translation`, `loader`, or `board_integration`. |
| `final_archive` | `python tools\fpga_first_pass_archive.py --check` | I31-S05 archive, pass/fail result, archive result, residual blockers, filed issues, and retest steps. | Any upstream evidence link changes, archive result changes, or blockers/issues change. | I31-S05 is `archived`; `first_pass_archived` has no residual blockers; `blocker_disposition_archived` has concrete blockers, issues, `first_mismatch`, and retest steps. |
| `local_regression_gate` | `python tools\local_checks.py` | Local gate transcript, conformance/litmus pass counts, and non-fatal CRLF warnings. | Before release-candidate handoff and after any source, tool, RTL, test, or documentation change. | `local_checks.py` exits 0 with spec reference, story coverage, conformance, litmus, and whitespace gates passing. |

## Known Board Assumptions

- Target board is `Sipeed Tang Mega 138K Dock`.
- `SRAM mode` is required for first-pass programming evidence.
- Bitstream identity comes from I31-S02 and is repeated in I31-S03/I31-S05.
- UART status packets use the `I25-S01 32-byte packet` layout.
- A first CPU pass is not accepted without `archive_result=first_pass_archived`.
- A board failure is not triaged without `replay_status=classified`.

## Acceptance Rules

Accept a first CPU pass only when:

- I31-S03 is `observed` with `board_result=first_pass`.
- Pass LED is yes, fail LED is no, status packet is first pass, retire count is at least 8, and fault code is 0.
- I31-S05 is `archived` with `archive_result=first_pass_archived` and `residual_blockers=none`.
- `python tools\local_checks.py` exits 0 for the same repository commit.

Accept a blocker disposition only when:

- I31-S03 is `observed` with `board_result=failure_observed`.
- I31-S04 is `classified` and preserves `replay_case_id` plus `first_mismatch`.
- I31-S05 is `archived` with `archive_result=blocker_disposition_archived`.
- `residual_blockers`, `filed_issues`, and `retest_steps` are concrete.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Reproducible commands are named. | Met by the matrix command column and `--commands`. |
| Required captures are named. | Met by the matrix required captures column and `--captures`. |
| Known board assumptions are explicit. | Met by the known board assumptions section. |
| Rerun criteria are explicit. | Met by the rerun criteria column. |
| Exact criteria for rerunning or accepting the first CPU pass are explicit. | Met by the acceptance criteria column and first-pass/blocker acceptance rules. |
| I31-S05 is the archive handoff. | Met by the final archive phase and `python tools\fpga_first_pass_archive.py --check`. |

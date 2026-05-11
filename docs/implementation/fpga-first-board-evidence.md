# FPGA First Board Evidence

Story: I24-S05

Status: Archive gate implemented; physical first-board archive blocked

Structured gate:

```text
python tools\fpga_first_board_archive.py --check
```

Evidence template:

```text
python tools\fpga_first_board_archive.py --template
```

Archive audit:

```text
python tools\fpga_first_board_archive.py --audit-archive docs\implementation\evidence\i24_s05_first_board_archive.txt
```

## Purpose

I24-S05 closes the first FPGA board-test thread by collecting the evidence
needed to reference the run from later stories. It does not replace the I24-S04
programming gate: `python tools\fpga_board_programming.py --check` and a
passing I24-S04 audit remain prerequisites before this archive can pass.

The story is currently `blocked` because no physical I24-S04 programming
evidence exists yet. Once the board run exists, this note requires links to
the scan, constraints, Gowin reports, bitstream, programming log, reset
observation, LED/probe capture, and any residual defects or retest steps.
I25-S05 adds `python tools\fpga_debug_evidence.py --check` for nontrivial
failure captures; first-board archives that are not `first_pass` should link
that debug-evidence record before downstream FPGA work treats the failure as
triaged.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_first_board_archive.py` | Structured I24-S05 archive profile, evidence parser, blocker-disposition audit, and validator. |
| `tools/fpga_first_board_archive.py` | CLI wrapper for checking, printing JSON, printing the archive template, and auditing captured archive evidence. |
| `tests/conformance/test_i24_s05_fpga_first_board_archive.py` | Conformance tests for required links, blocked/default audit, blocker disposition, CLI output, and docs. |
| `docs/implementation/fpga-first-board-evidence.md` | This implementation note. |

## Evidence Format

The archive record lives at
`docs/implementation/evidence/i24_s05_first_board_archive.txt` and uses:

```text
story=I24-S05
board=Sipeed Tang Mega Dock with 138K SOM
archived_at=
identity_evidence=docs/implementation/evidence/i24_s01_board_identity.txt
constraints_evidence=docs/implementation/evidence/i24_s02_pin_overlay.txt
gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl
bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs
programming_evidence=docs/implementation/evidence/i24_s04_sram_programming.txt
programming_log=docs/implementation/evidence/i24_s04_programming.log
reset_observation=docs/implementation/evidence/i24_s04_reset_observation.txt
led_evidence=docs/implementation/evidence/i24_s04_led.mp4
board_result=first_pass
residual_blockers=none
filed_issues=none
retest_steps=none
```

## Archive Rules

| Field | Required result |
| --- | --- |
| `programming_evidence` | Links the I24-S04 SRAM programming record. |
| `identity_evidence` | Links the I24-S01 scan or marking evidence. |
| `constraints_evidence` | Links the I24-S02 pin overlay evidence. |
| `gowin_report_bundle` | Links the I24-S03 report bundle used for programming. |
| `bitstream_path` | Names the exact audited `.fs` bitstream. |
| `programming_log` | Links the programming tool log. |
| `reset_observation` | Links the reset assertion/release observation. |
| `led_evidence` | Links the heartbeat, pass, and fail LED photo/video/probe evidence. |
| `board_result` | Must be `first_pass` for a passing archive. |
| `residual_blockers` | `none`, or named blockers. |
| `filed_issues` | `none` only when `residual_blockers=none`; otherwise issue IDs or links. |
| `retest_steps` | `none` only when `residual_blockers=none`; otherwise concrete retest steps. |

## Audit Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `archived` | I24-S04 passed, all required links are concrete, and blockers are closed or filed. | Reference this archive from downstream FPGA stories. |
| `needs_followup` | Evidence exists, but the board result is not `first_pass` or residual blocker disposition is incomplete. | File blockers and record retest steps. |
| `invalid` | Required archive fields or links are missing or malformed. | Fix or recapture the archive record. |
| `blocked` | I24-S04 has not passed or no archive record exists. | Complete programming evidence before archiving first-board completion. |

## Current Blocker

- I24-S04 SRAM programming evidence has not passed.
- No first-board archive record is captured.
- Residual blockers cannot be closed or filed until the physical run exists.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| First-board evidence note links scan evidence. | Met by required `identity_evidence`. |
| Report bundle and bitstream are linked. | Met by `gowin_report_bundle` and `bitstream_path`. |
| Programming and observation captures are linked. | Met by `programming_evidence`, `programming_log`, `reset_observation`, and `led_evidence`. |
| Residual defects or blockers are closed or filed. | Met by `residual_blockers`, `filed_issues`, and `retest_steps`. |
| Downstream stories have a stable handoff. | Met by the `archived` audit status and action. |

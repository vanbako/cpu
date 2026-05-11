# Release Regression Capture

Story: I33-S02

Status: Capture gate implemented; release regression remains blocked until the
full command-log and artifact archive is recorded.

Structured gate:

```text
python tools\release_regression_capture.py --check
```

Prerequisite checklist gate:

```text
python tools\release_candidate_checklist.py --check
```

Evidence template:

```text
python tools\release_regression_capture.py --template
```

Audit captured evidence:

```text
python tools\release_regression_capture.py --audit-evidence docs\implementation\evidence\i33_s02_release_regression_capture.txt
```

## Purpose

I33-S02 turns the I33-S01 release-candidate checklist into an explicit full
regression capture contract. It records the exact commit, release-candidate ID,
RC checklist evidence, local checks, drift checks, fast/slow/full Verilator
suites, FPGA validators, reproducible-build metadata, raw command logs, and
blocker disposition.

## Required Commands

| Item | Command | Required evidence |
| --- | --- | --- |
| RC checklist audit | `python tools\release_candidate_checklist.py --audit-evidence docs\implementation\evidence\i33_s01_release_candidate_checklist.txt` | `release_checklist` points at `docs/implementation/evidence/i33_s01_release_candidate_checklist.txt` and `release_checklist_status=accepted`. |
| Local checks | `python tools\local_checks.py` | `local_checks_log` transcript with `local_checks_status=passed`. |
| Spec reference drift | `python tools\spec_reference_check.py` | `spec_reference_log` transcript with `spec_reference_status=passed`. |
| Story coverage drift | `python tools\story_coverage.py --check-drift` | `story_coverage_log` transcript with `story_coverage_status=passed`. |
| Fast Verilator suite | `python tools\verilator_diff_harness.py --suite fast` | `fast_verilator_log` transcript with `fast_verilator_status=passed`. |
| Slow Verilator suite | `python tools\verilator_diff_harness.py --suite slow` | `slow_verilator_log` transcript with `slow_verilator_status=passed`. |
| Full Verilator suite | `python tools\verilator_diff_harness.py --suite all` | `full_verilator_log` transcript with `full_verilator_status=passed`. |
| FPGA validators | `python tools\fpga_board_identity.py --check`, `python tools\fpga_constraints_overlay.py --check`, `python tools\fpga_gowin_reports.py --check`, `python tools\fpga_reproducible_build.py --check`, `python tools\fpga_monitor_board_session.py --check` | `fpga_validator_logs` archive with `fpga_validator_status=passed`. |
| Reproducible build | `python tools\fpga_reproducible_build.py --check` | `reproducible_build_manifest` points at `docs/implementation/evidence/i28_s05_reproducible_build_manifest.json` and `reproducible_build_status=captured`. |

## Evidence Path

```text
docs/implementation/evidence/i33_s02_release_regression_capture.txt
```

## Evidence Format

```text
story=I33-S02
captured_at=
repository_commit=
release_candidate_id=single-core-v0.1-rc1
release_checklist=docs/implementation/evidence/i33_s01_release_candidate_checklist.txt
release_checklist_status=accepted
local_checks_log=docs/implementation/evidence/i33_s02_local_checks.log
local_checks_status=passed
spec_reference_log=docs/implementation/evidence/i33_s02_spec_reference.log
spec_reference_status=passed
story_coverage_log=docs/implementation/evidence/i33_s02_story_coverage.log
story_coverage_status=passed
fast_verilator_log=docs/implementation/evidence/i33_s02_verilator_fast.log
fast_verilator_status=passed
slow_verilator_log=docs/implementation/evidence/i33_s02_verilator_slow.log
slow_verilator_status=passed
full_verilator_log=docs/implementation/evidence/i33_s02_verilator_all.log
full_verilator_status=passed
fpga_validator_logs=docs/implementation/evidence/i33_s02_fpga_validators
fpga_validator_status=passed
reproducible_build_manifest=docs/implementation/evidence/i28_s05_reproducible_build_manifest.json
reproducible_build_status=captured
command_log_archive=docs/implementation/evidence/i33_s02_command_logs
unexplained_failures=none
regression_result=full_regression_artifacts_captured
residual_blockers=none
signed_off_by=
signed_off_at=
```

For an explained regression blocker, set
`regression_result=regression_blocker_captured` and name concrete
`residual_blockers` while keeping `unexplained_failures=none`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, artifact paths are concrete, all clean-capture statuses pass, and `unexplained_failures=none`. | Hand command logs and artifact paths to I33-S03. |
| `needs_followup` | A blocker capture is syntactically complete but does not name residual blockers or leaves failure disposition incomplete. | File or close blockers before release packaging. |
| `invalid` | Evidence is malformed, incomplete, names the wrong story, has inconsistent statuses, or points at the wrong checklist/build artifacts. | Fix the capture record and rerun the audit. |
| `blocked` | No regression capture evidence exists. | Keep release-candidate work blocked until the full archive is captured. |

## Handoff

I33-S03 consumes the command logs and artifact statuses for architecture-to-test
traceability. I33-S04 consumes `residual_blockers` and
`unexplained_failures`. I33-S05 consumes `command_log_archive`,
`release_checklist`, and `reproducible_build_manifest` when building the final
release-candidate bundle.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Full local checks and drift checks are captured. | Met by `local_checks_log`, `spec_reference_log`, and `story_coverage_log`. |
| Fast, slow, and full Verilator suites are captured. | Met by `fast_verilator_log`, `slow_verilator_log`, and `full_verilator_log`. |
| FPGA validators are archived. | Met by `fpga_validator_logs` and `fpga_validator_status`. |
| Reproducible-build metadata is tied to I28-S05. | Met by `reproducible_build_manifest` and `reproducible_build_status`. |
| Command logs and failure disposition are explicit. | Met by `command_log_archive`, `unexplained_failures`, `regression_result`, and `residual_blockers`. |

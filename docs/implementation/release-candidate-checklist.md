# Release Candidate Checklist

Story: I33-S01

Status: Checklist gate implemented; release-candidate readiness remains blocked
until physical FPGA evidence, full regression evidence, known limitations, and
artifact paths are captured.

Structured gate:

```text
python tools\release_candidate_checklist.py --check
```

Evidence template:

```text
python tools\release_candidate_checklist.py --template
```

Audit captured evidence:

```text
python tools\release_candidate_checklist.py --audit-evidence docs\implementation\evidence\i33_s01_release_candidate_checklist.txt
```

## Purpose

I33-S01 defines the single-core v0.1 release-candidate checklist. It is not a
release tag and does not waive physical evidence. The checklist names every
required gate before an RC can proceed: local checks, Verilator suites, FPGA
pass/session evidence, traceability, known limitations, and artifact bundle
handoff.

## Required Checklist Items

| Item | Gate | Required evidence |
| --- | --- | --- |
| Local checks | `python tools\local_checks.py` | Full command log with zero exit status. |
| Spec reference drift | `python tools\spec_reference_check.py` | No stale or missing story references. |
| Story coverage drift | `python tools\story_coverage.py --check-drift` | No missing index rows or unowned implementation docs. |
| Fast Verilator suite | `python tools\verilator_diff_harness.py --suite fast` | Passing fast-suite summary and selected cases. |
| Full Verilator suite | `python tools\verilator_diff_harness.py --suite all` | Passing full-suite summary or explicitly accepted blocker. |
| First CPU pass archive | `python tools\fpga_first_pass_archive.py --check` | I31-S05 archive status `archived`. |
| Interactive board session | `python tools\fpga_monitor_board_session.py --check` | I32-S06 board-session status `accepted`. |
| Reproducible build | `python tools\fpga_reproducible_build.py --check` | Captured manifest with tool versions and bitstream hash. |
| Known limitations | `docs/implementation/single-core-v0.1-known-limitations.md` | Published limitation/deferred-surface document. |
| Release bundle | `docs/implementation/evidence/i33_s05_release_candidate_bundle.txt` | Artifact path reserved for I33-S05. |

## Evidence Path

```text
docs/implementation/evidence/i33_s01_release_candidate_checklist.txt
```

## Evidence Format

```text
story=I33-S01
release_candidate_id=single-core-v0.1-rc1
repository_commit=
target_board=Sipeed Tang Mega Dock with 138K SOM
local_checks_status=passed
spec_reference_status=passed
story_coverage_status=passed
fast_verilator_status=passed
full_verilator_status=passed
first_pass_archive_status=archived
monitor_board_session_status=accepted
reproducible_build_status=captured
known_limitations_status=published
artifact_manifest_status=reserved
known_limitations_path=docs/implementation/single-core-v0.1-known-limitations.md
artifact_manifest_path=docs/implementation/evidence/i33_s05_release_candidate_bundle.txt
rc_decision=ready_for_rc_tag
residual_blockers=none
signed_off_by=
signed_off_at=
```

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, all statuses are passing/captured/published, and `residual_blockers=none`. | Run I33-S02 full regression and artifact capture. |
| `needs_followup` | The checklist is syntactically complete but the RC decision/blocker fields are inconsistent. | Close blockers or set a concrete blocked disposition. |
| `invalid` | Evidence is malformed, incomplete, names the wrong board/story, has bad statuses, or points at wrong artifact paths. | Fix the checklist record and rerun the audit. |
| `blocked` | No checklist evidence exists. | Keep RC work blocked until evidence is captured. |

## Handoff

I33-S02 consumes this checklist to run the full regression and artifact-capture
gate. I33-S04 consumes `known_limitations_path` and the blocker inventory.
I33-S05 consumes `artifact_manifest_path` and the required evidence list when
building the reproducible release-candidate bundle.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Required local checks are named. | Met by `python tools\local_checks.py`, spec reference, and story coverage gates. |
| Required Verilator suites are named. | Met by fast and full `verilator_diff_harness.py` gates. |
| Required FPGA evidence is named. | Met by I31-S05 and I32-S06 status fields. |
| Documentation and limitations are required. | Met by `known_limitations_path` and `known_limitations_status`. |
| Artifact handoff is explicit. | Met by `artifact_manifest_path`, `artifact_manifest_status`, and I33-S05 handoff. |

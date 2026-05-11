# Release Traceability Audit

Story: I33-S03

Status: Traceability gate implemented; release traceability remains blocked
until the audit evidence and summary inventory are captured.

Structured gate:

```text
python tools\release_traceability_audit.py --check
```

Current inventory summary:

```text
python tools\release_traceability_audit.py --summary-json
```

Evidence template:

```text
python tools\release_traceability_audit.py --template
```

Audit captured evidence:

```text
python tools\release_traceability_audit.py --audit-evidence docs\implementation\evidence\i33_s03_release_traceability_audit.txt
```

## Purpose

I33-S03 freezes the release-candidate traceability contract before limitations
and release packaging. It connects the I33-S02 regression capture to the
conformance index, story drift checks, architecture owner stories, E15 audit
coverage, conformance tests, litmus tests, indexed RTL gate rows, and indexed
evidence notes.

## Required Inputs

| Input | Command or artifact | Required evidence |
| --- | --- | --- |
| Regression capture | `python tools\release_regression_capture.py --check` | `release_regression_capture` points at `docs/implementation/evidence/i33_s02_release_regression_capture.txt` and `release_regression_status=accepted`. |
| Spec-reference drift | `python tools\spec_reference_check.py` | `spec_reference_log` transcript with `spec_reference_status=passed`. |
| Story-coverage drift | `python tools\story_coverage.py --check-drift` | `story_coverage_log` transcript with `story_coverage_status=passed`. |
| Test-index conformance | `python -m unittest tests.conformance.test_i01_s03_test_index` | `test_index_log` transcript with `test_index_status=passed`. |
| Story-drift conformance | `python -m unittest tests.conformance.test_i12_s03_story_drift` | `story_drift_log` transcript with `story_drift_status=passed`. |
| Traceability inventory | `python tools\release_traceability_audit.py --summary-json` | `traceability_summary` points at `docs/implementation/evidence/i33_s03_traceability_summary.json` and `traceability_status=passed`. |

## Audited Scopes

| Scope | Requirement |
| --- | --- |
| Implementation stories | Every indexed implementation story exists in `agile-impl-v0.1.md`; future release/backlog stories are explicitly listed in `deferred_missing_stories`. |
| Conformance tests | Every `tests\conformance\test_*.py` file appears in `docs/implementation/conformance-test-index.md`, and the filename story matches the index story. |
| Litmus tests | Every `tests\litmus\test_*.py` file appears in `docs/implementation/conformance-test-index.md`, and the filename story matches the index story. |
| RTL gate rows | Indexed `rtl\` artifacts exist and carry architecture owner plus E15 coverage metadata. |
| Evidence notes | Indexed evidence-note rows exist and carry architecture owner plus E15 coverage metadata. |
| owner_coverage | Every index row has at least one E-story owner and at least one E15 coverage item. |
| Stale references | Spec-reference and story-coverage drift commands report no stale artifact paths or missing owners. |

## Evidence Path

```text
docs/implementation/evidence/i33_s03_release_traceability_audit.txt
```

Summary inventory path:

```text
docs/implementation/evidence/i33_s03_traceability_summary.json
```

## Evidence Format

```text
story=I33-S03
audited_at=
repository_commit=
release_regression_capture=docs/implementation/evidence/i33_s02_release_regression_capture.txt
release_regression_status=accepted
spec_reference_log=docs/implementation/evidence/i33_s03_spec_reference.log
spec_reference_status=passed
story_coverage_log=docs/implementation/evidence/i33_s03_story_coverage.log
story_coverage_status=passed
test_index_log=docs/implementation/evidence/i33_s03_test_index.log
test_index_status=passed
story_drift_log=docs/implementation/evidence/i33_s03_story_drift.log
story_drift_status=passed
traceability_summary=docs/implementation/evidence/i33_s03_traceability_summary.json
traceability_status=passed
indexed_artifact_count=
indexed_story_count=
conformance_test_count=
litmus_test_count=
rtl_artifact_rows=
evidence_note_rows=
unindexed_tests=none
stale_references=none
missing_owner_coverage=none
deferred_missing_stories=I33-S04,I33-S05,I33-S06,I34-S03,I34-S04,I34-S05,I34-S06
traceability_result=traceability_audit_clean
traceability_blockers=none
signed_off_by=
signed_off_at=
```

For an explained blocker, set
`traceability_result=traceability_blocker_captured`, name concrete
`traceability_blockers`, and record the affected rows in `unindexed_tests`,
`stale_references`, or `missing_owner_coverage`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, command statuses pass, artifact paths are concrete, owner/E15 coverage is clean, and only explicit future stories remain deferred. | Hand the summary to I33-S04 and I33-S05. |
| `needs_followup` | The record is syntactically complete but names unresolved traceability issues or blocker disposition is incomplete. | Fix the index or file release blockers. |
| `invalid` | Evidence is malformed, incomplete, names the wrong story, has inconsistent statuses, or points at the wrong artifacts. | Fix the traceability record and rerun the audit. |
| `blocked` | No traceability evidence exists. | Keep limitations freeze and release packaging blocked. |

## Handoff

I33-S04 consumes the clean owner/E15 inventory before freezing known limitations
and errata. I33-S05 consumes `traceability_summary`, command logs, and the
`docs/implementation/conformance-test-index.md` state for the release bundle.
I33-S06 consumes any `traceability_blocker_captured` findings as post-release
backlog input.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Every implementation story with release evidence is indexed. | Met by `indexed_story_count`, explicit `deferred_missing_stories`, and backlog-story validation. |
| Every conformance and litmus test is indexed. | Met by `conformance_test_count`, `litmus_test_count`, and `unindexed_tests=none`. |
| RTL gate and evidence-note rows are audited. | Met by `rtl_artifact_rows`, `evidence_note_rows`, owner checks, and stale-path checks. |
| Architecture owner and E15 coverage are mandatory. | Met by the `owner_coverage` scope and `missing_owner_coverage=none`. |
| Stale references are blocked. | Met by spec-reference/story-coverage drift logs and `stale_references=none`. |

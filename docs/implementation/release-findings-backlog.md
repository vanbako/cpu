# Release Findings Backlog

Story: I33-S06

Status: Findings backlog gate implemented; release-findings triage remains
blocked until concrete bundle and triage evidence are captured.

Structured gate:

```text
python tools\release_findings_backlog.py --check
```

Findings evidence template:

```text
python tools\release_findings_backlog.py --template
```

Findings manifest template:

```text
python tools\release_findings_backlog.py --manifest-template
```

Audit captured evidence:

```text
python tools\release_findings_backlog.py --audit-evidence docs\implementation\evidence\i33_s06_release_findings_backlog.txt
```

## Purpose

I33-S06 opens the next backlog from release findings. It consumes the I33-S05
release-candidate bundle, routes remaining defects and deferred work to
post-v0.1 implementation or architecture follow-up, preserves retest commands,
and records that the frozen v0.1 contract remains unchanged.

## Required Inputs

| Input | Command or artifact | Findings field |
| --- | --- | --- |
| Release bundle gate | `python tools\release_candidate_bundle.py --check` | `release_candidate_bundle`, `release_bundle_status` |
| Release bundle evidence | `docs/implementation/evidence/i33_s05_release_candidate_bundle.txt` | `release_candidate_bundle` |
| Bundle manifest | `docs/implementation/evidence/i33_s05_release_candidate_manifest.json` | `bundle_manifest` |
| Known limitations | `docs/implementation/single-core-v0.1-known-limitations.md` | `implementation_findings`, `architecture_findings`, `board_findings` |
| Rerun commands | `docs/implementation/evidence/i33_s05_rerun_commands.txt` | `retest_commands` |

## Evidence Path

```text
docs/implementation/evidence/i33_s06_release_findings_backlog.txt
```

Findings manifest path:

```text
docs/implementation/evidence/i33_s06_release_findings_backlog.json
```

Retest command capture:

```text
docs/implementation/evidence/i33_s06_retest_commands.txt
```

## Finding Routes

| Finding | Source | Target | Contract impact |
| --- | --- | --- | --- |
| `physical_board_pass_blocked` | I33-S04/I33-S05 `release_blockers` | I31/I32 board-evidence rerun | `unchanged` |
| `release_candidate_not_tagged` | I33-S04/I33-S05 `release_blockers` | Release tag decision | `unchanged` |
| `rtl_unsupported_capability_subset` | Known limitations | post-v0.1 RTL capability backlog | `unchanged` |
| `multicore_fabric_deferred` | Known limitations | post-v0.1 multicore/fabric backlog | `unchanged` |
| `ddr_board_ip_deferred` | Known limitations | I29 external-memory board evidence | `unchanged` |
| `retro_console_60k_deferred` | I34 alternate target | I34-S03 through I34-S06 | `unchanged` |
| `cacheable_tag_policy_deferred` | Known limitations | post-v0.1 architecture or implementation backlog | `unchanged` |
| `architecture_errata_none_known` | Known limitations | Architecture backlog only if a late erratum appears | `unchanged` |
| `release_retest_commands` | I33-S05 rerun commands | post-v0.1 retest matrix | `unchanged` |

## Evidence Format

```text
story=I33-S06
triaged_at=
repository_commit=
release_candidate_bundle=docs/implementation/evidence/i33_s05_release_candidate_bundle.txt
release_bundle_status=accepted
bundle_manifest=docs/implementation/evidence/i33_s05_release_candidate_manifest.json
release_blockers=physical_board_pass_blocked,release_candidate_not_tagged
implementation_findings=rtl_unsupported_capability_subset,multicore_fabric_deferred
architecture_findings=architecture_errata_none_known,cacheable_tag_policy_deferred
board_findings=physical_board_pass_blocked,ddr_board_ip_deferred,retro_console_60k_deferred
deferred_work_status=triaged
post_v0_1_backlog=docs/implementation/evidence/i33_s06_release_findings_backlog.json
post_v0_1_backlog_status=opened
frozen_contract_status=unchanged
tag_decision_status=blocked_until_board_evidence_and_bundle_signoff
retest_commands=docs/implementation/evidence/i33_s06_retest_commands.txt
retest_status=captured
findings_result=release_findings_backlog_opened
findings_blockers=none
signed_off_by=
signed_off_at=
```

For an explained triage blocker, set
`findings_result=release_findings_blocker_captured` and name concrete
`findings_blockers`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, the I33-S05 bundle is accepted, deferred work is triaged, post-v0.1 backlog artifacts are named, retest commands are captured, and `frozen_contract_status=unchanged`. | Hand the findings manifest to post-v0.1 planning and tag review. |
| `needs_followup` | The record is syntactically complete but an explained blocker has no blocker disposition. | Name untriaged findings blockers or rerun missing captures. |
| `invalid` | Evidence is malformed, incomplete, names the wrong story, changes the frozen contract, has inconsistent statuses, or points at wrong artifacts. | Fix the findings record and rerun the audit. |
| `blocked` | No release-findings evidence exists. | Keep post-v0.1 planning and tag decisions blocked. |

## Handoff

The post-v0.1 implementation backlog consumes `implementation_findings`,
`board_findings`, and `retest_commands`. The architecture backlog consumes
`architecture_findings` only when a real erratum or contract gap is found. A
tag decision consumes the I33-S05 bundle and this findings manifest instead of
silently changing the frozen v0.1 contract.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Remaining defects and deferred work are triaged. | Met by `implementation_findings`, `architecture_findings`, `board_findings`, and the finding-route table. |
| Post-v0.1 backlog artifacts are explicit. | Met by `post_v0_1_backlog` and `post_v0_1_backlog_status`. |
| Retest commands are preserved. | Met by `retest_commands` and `retest_status`. |
| The frozen v0.1 contract is not silently changed. | Met by requiring `frozen_contract_status=unchanged`. |

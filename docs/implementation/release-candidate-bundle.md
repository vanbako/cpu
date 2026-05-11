# Release Candidate Bundle

Story: I33-S05

Status: Bundle gate implemented; release-candidate bundling remains blocked
until concrete artifacts are captured.

Structured gate:

```text
python tools\release_candidate_bundle.py --check
```

Bundle evidence template:

```text
python tools\release_candidate_bundle.py --template
```

Bundle manifest template:

```text
python tools\release_candidate_bundle.py --manifest-template
```

Audit captured evidence:

```text
python tools\release_candidate_bundle.py --audit-evidence docs\implementation\evidence\i33_s05_release_candidate_bundle.txt
```

## Purpose

I33-S05 defines the reproducible release-candidate bundle. It records the exact
commit, tool versions, generated images, bitstream hashes, Gowin reports,
evidence archives, release documents, and rerun commands. This gate does not
silently rebuild or reinterpret artifacts; a later tag decision consumes the
captured bundle manifest.

## Required Inputs

| Input | Command or artifact | Bundle field |
| --- | --- | --- |
| Release checklist | `python tools\release_candidate_checklist.py --check` | `release_checklist`, `release_checklist_status` |
| Regression capture | `python tools\release_regression_capture.py --check` | `regression_capture`, `regression_status` |
| Traceability audit | `python tools\release_traceability_audit.py --check` | `traceability_audit`, `traceability_status` |
| Known limitations | `python tools\release_known_limitations.py --check` | `known_limitations`, `known_limitations_status` |
| Reproducible build | `python tools\fpga_reproducible_build.py --check` | `reproducible_build_manifest`, `reproducible_build_status` |
| Program manifest | `python tools\fpga_program_manifest.py --check` | generated image source manifest |
| BRAM images | `python tools\fpga_bram_images.py --check` | `generated_images_manifest`, `generated_images_status` |
| Gowin reports | `python tools\fpga_gowin_reports.py --check` | `gowin_reports`, `report_status`, `bitstream_hashes`, `bitstream_status` |

## Evidence Path

```text
docs/implementation/evidence/i33_s05_release_candidate_bundle.txt
```

Bundle manifest path:

```text
docs/implementation/evidence/i33_s05_release_candidate_manifest.json
```

## Required Bundle Artifacts

| Artifact | Category | Path |
| --- | --- | --- |
| Repository commit | commit | `<git commit>` |
| Tool versions | tool_versions | `docs/implementation/evidence/i33_s05_tool_versions.txt` |
| Generated images | generated_images | `docs/implementation/evidence/i33_s05_generated_images_manifest.json` |
| Bitstream hashes | bitstream_hashes | `docs/implementation/evidence/i33_s05_bitstream_hashes.txt` |
| Gowin reports | reports | `build/fpga/tang_mega_138k/first_test/impl` |
| Evidence archives | evidence_archives | `docs/implementation/evidence` |
| Documents | documents | `docs/implementation` |
| Rerun commands | rerun_commands | `docs/implementation/evidence/i33_s05_rerun_commands.txt` |

The bundle must include
`docs/implementation/single-core-v0.1-known-limitations.md` and
`docs/implementation/evidence/i28_s05_reproducible_build_manifest.json`.

## Evidence Format

```text
story=I33-S05
bundled_at=
repository_commit=
release_candidate_id=single-core-v0.1-rc1
release_checklist=docs/implementation/evidence/i33_s01_release_candidate_checklist.txt
release_checklist_status=accepted
regression_capture=docs/implementation/evidence/i33_s02_release_regression_capture.txt
regression_status=accepted
traceability_audit=docs/implementation/evidence/i33_s03_release_traceability_audit.txt
traceability_status=accepted
known_limitations=docs/implementation/single-core-v0.1-known-limitations.md
known_limitations_status=accepted
reproducible_build_manifest=docs/implementation/evidence/i28_s05_reproducible_build_manifest.json
reproducible_build_status=captured
tool_versions_path=docs/implementation/evidence/i33_s05_tool_versions.txt
tool_versions_status=captured
generated_images_manifest=docs/implementation/evidence/i33_s05_generated_images_manifest.json
generated_images_status=captured
bitstream_hashes=docs/implementation/evidence/i33_s05_bitstream_hashes.txt
bitstream_status=captured
gowin_reports=build/fpga/tang_mega_138k/first_test/impl
report_status=captured
evidence_archives=docs/implementation/evidence
evidence_status=captured
docs_archive=docs/implementation
docs_status=captured
rerun_commands=docs/implementation/evidence/i33_s05_rerun_commands.txt
rerun_status=captured
bundle_manifest=docs/implementation/evidence/i33_s05_release_candidate_manifest.json
bundle_result=release_candidate_bundle_captured
release_blockers=physical_board_pass_blocked,release_candidate_not_tagged
signed_off_by=
signed_off_at=
```

For an explained bundle blocker, set
`bundle_result=release_candidate_bundle_blocker_captured` and name concrete
`release_blockers`.

## Rerun Commands

```text
python tools\release_candidate_checklist.py --check
python tools\release_regression_capture.py --check
python tools\release_traceability_audit.py --check
python tools\release_known_limitations.py --check
python tools\fpga_reproducible_build.py --check
python tools\fpga_program_manifest.py --check
python tools\fpga_bram_images.py --check
python tools\fpga_gowin_reports.py --check
python tools\release_candidate_bundle.py --check
```

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, upstream release gates are accepted, captured artifacts have concrete paths, and release blockers are carried into the bundle. | Hand the bundle manifest to I33-S06. |
| `needs_followup` | The record is syntactically complete but a blocker disposition is incomplete. | Name blockers or rerun missing captures. |
| `invalid` | Evidence is malformed, incomplete, names the wrong story, has inconsistent statuses, or points at wrong artifacts. | Fix the bundle record and rerun the audit. |
| `blocked` | No release-candidate bundle evidence exists. | Keep release findings and tag decisions blocked. |

## Handoff

I33-S06 consumes `release_blockers`, the bundle manifest, and the rerun-command
list to open the post-release-findings backlog. A tag decision must consume
this bundle instead of rebuilding artifacts silently.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Commit and tool versions are recorded. | Met by `repository_commit` and `tool_versions_path`. |
| Generated images are recorded. | Met by `generated_images_manifest`. |
| Bitstream hashes and reports are recorded. | Met by `bitstream_hashes` and `gowin_reports`. |
| Evidence archives and documents are included. | Met by `evidence_archives`, `docs_archive`, and known limitations. |
| Rerun commands are explicit. | Met by `rerun_commands` and the command list above. |

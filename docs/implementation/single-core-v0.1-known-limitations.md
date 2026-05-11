# Single-Core v0.1 Known Limitations

Story: I33-S04

Status: Known-limitations and errata freeze profile implemented; release
tagging remains blocked until physical board evidence, release bundling, and
release-findings triage are complete.

Structured gate:

```text
python tools\release_known_limitations.py --check
```

Evidence template:

```text
python tools\release_known_limitations.py --template
```

Audit captured evidence:

```text
python tools\release_known_limitations.py --audit-evidence docs\implementation\evidence\i33_s04_known_limitations_freeze.txt
```

Prerequisite traceability gate:

```text
python tools\release_traceability_audit.py --check
```

## Purpose

I33-S04 freezes the known-limitations and errata inventory for the single-core
v0.1 release path. This document is a release input, not a release tag. It
lists unsupported features, board blockers, deferred multicore/fabric work,
DDR and external-memory boundaries, cacheable/tag behavior, architecture
errata status, and release scope.

## Evidence Path

```text
docs/implementation/evidence/i33_s04_known_limitations_freeze.txt
```

Prerequisite traceability evidence:

```text
docs/implementation/evidence/i33_s03_release_traceability_audit.txt
```

## Unsupported Features

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `rtl_unsupported_capability_subset` | `CINCADDR`, `CSETBOUNDS`, `CSEAL`, and `CUNSEAL` remain outside the single-core RTL release. | `docs/implementation/rtl-semantic-closure.md` | Add a post-v0.1 RTL capability-expansion story. |

## Board Blockers

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `physical_board_pass_blocked` | Physical FPGA pass evidence is not yet archived. Release-candidate tagging remains blocked until the Tang Mega Dock with 138K SOM evidence is captured or explicitly classified. | `docs/implementation/fpga-first-pass-archive.md`, `docs/implementation/fpga-monitor-board-session.md` | Run the Mega Dock 138K board-evidence path. |
| `retro_console_60k_deferred` | Tang Retro Console with 60K SOM is a second-board target and is not the first release target. | `docs/implementation/fpga-retro-console-identity.md` | Resume I34-S03 through I34-S06 after Mega Dock evidence. |

## Multicore And Fabric

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `single_core_only` | The release is single-core only. Multicore startup, fabric links, coherence, and cross-core debug remain deferred. | `docs/implementation/rtl-semantic-closure.md` | Open post-v0.1 multicore/fabric RTL backlog. |

## DDR And External Memory

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `ddr_board_ip_deferred` | Board-specific DDR controller IP, physical DDR pins, byte-lane mapping, training, and board-calibrated DDR pass are not claimed. | `docs/implementation/fpga-ddr-wrapper.md`, `docs/implementation/fpga-external-memory.md` | Complete I29-S05 board evidence before claiming DDR pass. |

## Cacheable And Tag Behavior

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `external_cacheable_tags_deferred` | External DDR remains normal-uncacheable with no tag sidecar. Capability `CLC` and `CSC` to external DDR fault until a cacheable/tag policy is implemented and verified. | `docs/implementation/fpga-external-memory-policy.md` | Add coherent/cacheable and tag-sidecar evidence in a later story. |

## Architecture Errata

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `architecture_errata_none_known` | No architecture errata are known for the frozen single-core contract. | `docs/implementation/release-traceability-audit.md` | Feed any late errata into I33-S06 release-findings backlog without silently changing the frozen v0.1 contract. |

## Release Scope

| Item | Limitation | Evidence | Follow-up |
| --- | --- | --- | --- |
| `release_candidate_not_tagged` | This freeze is not a release tag. I33-S05 must still produce the reproducible release-candidate bundle and I33-S06 must triage findings. | `docs/implementation/release-candidate-checklist.md` | Finish I33-S05 and I33-S06 before any tag decision. |

## Evidence Format

```text
story=I33-S04
frozen_at=
repository_commit=
traceability_audit=docs/implementation/evidence/i33_s03_release_traceability_audit.txt
traceability_status=accepted
limitations_doc=docs/implementation/single-core-v0.1-known-limitations.md
unsupported_features_status=listed
board_blockers_status=listed
multicore_fabric_status=listed
ddr_external_memory_status=listed
cacheable_tag_status=listed
architecture_errata_status=none_known
release_scope_status=listed
limitations_result=known_limitations_frozen
release_blockers=physical_board_pass_blocked,release_candidate_not_tagged
signed_off_by=
signed_off_at=
```

For an explained limitations blocker, set
`limitations_result=known_limitations_blocker_captured` and name concrete
`release_blockers`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Required fields are complete, traceability is accepted, limitation categories are listed, architecture errata are `none_known` or listed, and release blockers are named. | Hand this document to I33-S05. |
| `needs_followup` | The record is syntactically complete but a blocker disposition is incomplete. | File release blockers or route them to I33-S06. |
| `invalid` | Evidence is malformed, incomplete, names the wrong story, has inconsistent statuses, or points at the wrong artifacts. | Fix the freeze record and rerun the audit. |
| `blocked` | No limitations-freeze evidence exists. | Keep release bundling blocked. |

## Handoff

I33-S05 consumes this known-limitations document and the freeze evidence when
building the reproducible release-candidate bundle. I33-S06 consumes
`release_blockers` and any late errata as release findings without changing
the frozen v0.1 contract.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Unsupported features are explicit. | Met by `rtl_unsupported_capability_subset`. |
| Board blockers are explicit. | Met by `physical_board_pass_blocked` and `retro_console_60k_deferred`. |
| Deferred multicore/fabric work is explicit. | Met by `single_core_only`. |
| DDR and external-memory limits are explicit. | Met by `ddr_board_ip_deferred`. |
| Cacheable/tag behavior is explicit. | Met by `external_cacheable_tags_deferred`. |
| Architecture errata are explicit. | Met by `architecture_errata_none_known`. |

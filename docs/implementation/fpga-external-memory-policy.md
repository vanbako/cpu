# FPGA External Memory Policy

Story: I29-S04

Status: Conservative normal-uncacheable payload policy

## Command

Validate the policy profile and executable fixtures:

```text
python tools\fpga_external_memory_policy.py --check
```

Inspect the profile, run, rules, or fixture outcomes:

```text
python tools\fpga_external_memory_policy.py --json
python tools\fpga_external_memory_policy.py --run
python tools\fpga_external_memory_policy.py --rules
python tools\fpga_external_memory_policy.py --fixtures
```

Required gates:

```text
python tools\fpga_external_memory.py --check
python tools\fpga_ddr_wrapper.py --check
python tools\fpga_external_memory_tests.py --check
python -m unittest tests.litmus.test_i06_s04_memory_litmus
python -m unittest tests.conformance.test_i15_s02_tag_integrity
```

## Scope

I29-S04 keeps the first `external_ddr_payload` window conservative:

- memory type is `normal_uncacheable`;
- I29-S03 firmware remains BRAM-resident and uses DDR only as data memory;
- CPU payload `LD48` and `ST48` traffic is allowed after `controller_ready`;
- `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL` are not required for the
  CPU-only payload tests;
- no trusted external capability-tag sidecar exists;
- `CLC` and `CSC` to external DDR raise CPU-owned `ACCESS_FAULT`;
- payload writes, serialized capability payload bits, and DMA-style writes
  cannot create valid tags.

This story does not claim cacheable external DDR, coherent external-agent
sharing, off-BRAM instruction fetch, or trusted tag storage.

## Policy Rules

| Rule | Requirement | Evidence |
| --- | --- | --- |
| `select_normal_uncacheable` | The first external DDR window remains `normal_uncacheable`. | I29-S01 window profile and I29-S04 memory-type fixture. |
| `preserve_program_order_for_payload` | BRAM-resident firmware observes its own external DDR payload stores before later loads. | I29-S04 ordering fixture and I29-S03 walking/burst tests. |
| `no_cache_maintenance_for_cpu_payload` | CPU-only payload tests require no `CACHE.CLEAN`, `CACHE.INVAL`, or `CACHE.CLEANINVAL`. | I06-S04 remains the cache-maintenance reference gate. |
| `fault_external_clc_csc` | `CLC` and `CSC` to external DDR raise `ACCESS_FAULT`. | I29-S04 tag fixture and I15-S02 tag non-forgery gate. |
| `payload_writes_do_not_forge_tags` | Payload writes never create valid capability tags. | Serialized capability payload bits remain untagged. |
| `bram_resident_firmware_only` | The I29-S03 firmware runs from BRAM and uses DDR as data memory only. | I29-S03 firmware profile and I29-S05 evidence handoff. |

## Handoff

I29-S05 must archive board evidence for this conservative policy before a DDR
pass is claimed. A later cacheable-DDR story must add coherent/cacheable litmus
evidence before changing the selected memory type. A later tag-sidecar story
must prove trusted tag storage, tag clearing, and non-forgery before enabling
external-memory `CLC` or `CSC`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The selected external-memory type is explicit. | Met: `normal_uncacheable`. |
| Cache-maintenance requirements are explicit. | Met: not required for CPU-only payload tests; I06-S04 remains the reference gate. |
| Ordering behavior is executable. | Met by the store-then-load fixture. |
| Capability-tag policy is executable. | Met by `CLC`/`CSC` `ACCESS_FAULT` and non-forgery fixtures. |
| Firmware handoff remains BRAM-resident. | Met by the I29-S03 fixture check. |

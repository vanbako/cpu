# FPGA External Memory Evidence

Story: I29-S05

Status: Evidence gate blocked until physical DDR board run

## Command

Validate the evidence profile:

```text
python tools\fpga_external_memory_evidence.py --check
```

Inspect the profile, template, required fields, blockers, or a captured record:

```text
python tools\fpga_external_memory_evidence.py --json
python tools\fpga_external_memory_evidence.py --template
python tools\fpga_external_memory_evidence.py --fields
python tools\fpga_external_memory_evidence.py --blockers
python tools\fpga_external_memory_evidence.py --audit docs\implementation\evidence\i29_s05_external_memory_board_evidence.txt
```

Required gates:

```text
python tools\fpga_ddr_wrapper.py --check
python tools\fpga_external_memory_tests.py --check
python tools\fpga_external_memory_policy.py --check
python tools\fpga_reproducible_build.py --check
```

Archive path:

```text
docs/implementation/evidence/i29_s05_external_memory_board_evidence.txt
```

## Scope

I29-S05 defines the first external-memory FPGA evidence archive. It does not
claim board DDR success until the archive links concrete DDR calibration,
memory-test pass/fail, timing reports, debug/status, UART/status, probe or LED,
bitstream identity, and blocker disposition evidence.

The expected pass result is `external_memory_pass`. Any other result, missing
capture, missing `bitstream_sha256`, missing residual-blocker disposition, or
placeholder evidence path keeps the audit blocked, invalid, or in follow-up.

## Required Evidence

| Field | Purpose |
| --- | --- |
| `board_identity_evidence` | Links the verified device/package evidence. |
| `ddr_calibration_evidence` | Shows DDR calibration done/error state and any timeout/error code. |
| `memory_test_program` | Must be `external_memory.ddr_bram_resident_test`. |
| `memory_test_result` | Must be `external_memory_pass`. |
| `memory_test_log` | Includes walking-pattern, address-line, burst, alignment, and fault-injection observations. |
| `timing_report_bundle` | Links Gowin timing reports and utilization reports for the programmed build. |
| `debug_status_capture` | Captures decoded debug/status fields for pass/fail or first failure. |
| `uart_status_capture` | Captures UART/status output or transcript. |
| `probe_capture` | Links LED, GAO/ILA, or probe evidence. |
| `bitstream_sha256` | Records the 64-hex-character SHA-256 of the programmed bitstream. |
| `policy_status` | Must match `normal_uncacheable_no_tag_sidecar`. |
| `residual_blockers`, `filed_issues`, `retest_steps` | Close blockers as `none` or file them with retest steps. |

## Blocked Items

- Board-specific DDR controller IP and verified pin constraints are still
  required before a pass archive.
- Gowin timing reports and bitstream identity must be linked.
- Memory-test evidence must include walking-pattern, address-line, burst,
  alignment, and fault-injection observations.
- UART/status or probe evidence must preserve the first failure sample when the
  result is not a pass.
- Residual blockers must be closed as `none` or filed with retest steps.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| DDR calibration evidence is required. | Met by `ddr_calibration_evidence`. |
| Memory-test pass/fail evidence is required. | Met by `memory_test_result` and `memory_test_log`. |
| Timing reports and bitstream identity are required. | Met by `timing_report_bundle` and `bitstream_sha256`. |
| Debug/status and UART/status evidence are required. | Met by `debug_status_capture` and `uart_status_capture`. |
| Residual blockers are explicit. | Met by blocker disposition fields and follow-up audit status. |

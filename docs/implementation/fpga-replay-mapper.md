# FPGA Replay Mapper

Story: I25-S04

Status: Replay mapper implemented for UART and probe status captures

Structured gate:

```text
python tools\fpga_replay_mapper.py --check
```

Map a captured packet:

```text
python tools\fpga_replay_mapper.py --map-hex <packet_hex>
```

## Purpose

I25-S04 maps a captured FPGA debug/status record back to the closest Verilator
replay case. The input is the I25-S01 32-byte packet captured over `UART` or
from a `GAO/ILA` probe bundle. The output is a ranked set of `core.*` or golden
case IDs plus replay commands.

The mapper does not claim that the small first-test firmware is identical to a
full regression case. It chooses the nearest existing case so board failures
can be reproduced with the same harness that reports first-mismatch
diagnostics.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_replay_mapper.py` | Structured I25-S04 replay heuristics, packet mapper, command renderer, and validator. |
| `tools/fpga_replay_mapper.py` | CLI wrapper for checking, JSON profile, example mapping, and packet-hex mapping. |
| `tests/conformance/test_i25_s04_fpga_replay_mapper.py` | Conformance tests for heuristic coverage, packet mapping, CLI output, docs, and prerequisite gates. |
| `docs/implementation/fpga-replay-mapper.md` | This implementation note. |

## Inputs

| Field | Source | Use |
| --- | --- | --- |
| `flags` | I25-S01 status flags | Classifies reset, idle, retire, fault, pass, fail, and heartbeat. |
| `slot` | I25-S01 slot byte | Selects fetch/decode replay when slot placement is suspicious. |
| `pass_fail_state` | I25-S01 pass/fail state | Distinguishes idle, running, first-pass, failed, and blocked captures. |
| `pc_cell` | I25-S01 PC cell | Helps decide whether a fault is near reset/fetch or later execution. |
| `retire_count` | I25-S01 retire count | Distinguishes no-retire, first-pass, and late-failure captures. |
| `fault_code` | I25-S01 sticky fault code | Selects fault-oriented replay cases. |
| `trap_cause` | I25-S01 sampled trap cause | Overrides sticky fault code when present. |
| `build_id` | I25-S01 build identity | Preserved with evidence to identify the bitstream. |
| `sequence` | I25-S01 packet sequence | Names the suggested observed-trace path. |

## Heuristics

| Heuristic | Condition | Primary case | Secondary cases |
| --- | --- | --- | --- |
| `reset_or_idle` | Reset asserted or idle with no retire progress. | `core.shell.reset_idle` | none |
| `first_pass_or_running` | `first_pass`, `pass_led`, or retire count at the pass threshold without a fault. | `core.scalar.integer_ops_add_mul` | `integer_ops.add_mul`, `reset_smoke.add_slot0` |
| `fetch_decode_fault` | Illegal, breakpoint, align, or low-PC access fault. | `core.fetch_decode.slot1_48bit_placement` | `fault_cases.slot1_48bit_placement` |
| `capability_or_memory_fault` | Capability tag, bounds, permission, seal, or local-store fault. | `core.cap_mem.memory_tag_ops` | `fault_cases.invalid_tag_csetaddr`, `memory_tag_ops.csc_clc_st48_ld48` |
| `trap_or_return_fault` | Syscall or return-stack fault. | `core.control_trap.sys_iret` | `traps.sys_to_tvc`, `traps.sys_iret_return` |
| `translation_fault` | Page fault. | `core.mmu_tlb.translation_sfence` | none |
| `scalar_fault` | Divide-by-zero or scalar arithmetic trap. | `fault_cases.divide_by_zero` | `core.scalar.integer_ops_add_mul` |

## Commands

Decode the captured packet first when needed:

```text
python tools\fpga_debug_status_packet.py --decode-hex <packet_hex>
```

Then map it:

```text
python tools\fpga_replay_mapper.py --map-hex <packet_hex>
```

Run the top-ranked replay command:

```text
python tools\verilator_diff_harness.py --case-id core.fetch_decode.slot1_48bit_placement
```

If the board capture has been converted to a retire trace, run the observed
trace comparison to preserve the harness first-mismatch line:

```text
python tools\verilator_diff_harness.py --case-id core.fetch_decode.slot1_48bit_placement --observed-trace build\fpga\captures\status_sequence_<sequence>_retire_trace.json
```

## Preservation Rules

- Preserve the original packet hex and decoded JSON.
- Preserve the selected case ID and all ranked alternatives.
- Preserve the Verilator harness first-mismatch line when an `observed-trace`
  is available.
- Preserve the UART or GAO/ILA capture path with the board evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Captured status records map to replay cases. | Met by `--map-hex` and the ranked candidate output. |
| Nearest `core.*` or golden cases are selected. | Met by the heuristic table and regression registry validation. |
| Replay commands are printed. | Met by each candidate's `python tools\verilator_diff_harness.py --case-id ...` command. |
| First-mismatch diagnostics are preserved. | Met by observed-trace commands and preservation rules. |
| I25-S02 and I22-S08 are used directly. | Met by packet decode and the existing Verilator regression registry. |

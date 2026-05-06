# Golden Retire Trace Corpus

Story: I20-S02

Status: Draft implementation profile

The golden retire trace corpus is the semantic reference input for the future
Verilator differential harness. It is generated from the Python semantic model
instead of being hand-written, so expected packets stay aligned with the current
instruction, pipeline, trap, memory/tag, and protected-stack semantics.

## Command

Print the full machine-readable corpus:

```text
python tools\golden_trace_corpus.py
```

List case IDs:

```text
python tools\golden_trace_corpus.py --list
```

Print one case:

```text
python tools\golden_trace_corpus.py --case memory_tag_ops.csc_clc_st48_ld48
```

The generator also exposes `cpu_v01.golden_traces.golden_trace_corpus_json()`
for tests and later harness code.

## Packet Shape

Each case contains ordered retire packets with:

- `valid`;
- `sequence`;
- `pc_cell`;
- `slot`;
- `instruction_length`;
- `mnemonic`;
- `opcode_id`;
- `result_kind`;
- `result_stage`;
- exactly one of `normal_effects`, `fault_packet`, or `redirect_packet`;
- optional `trap_entry` metadata.

Normal-effect packets serialize integer writes, capability writes, CSR writes,
CCSR writes, memory effects, reservation effects, TLB effects, `PCC` updates,
and `EPCC` updates. Capability values include payload fields, architectural tag,
and the four 24-bit payload cells.

Fault packets serialize `cause`, `faulting_location`, `tval`, `capcause`, and
`fault_cap_idx`.

## Corpus Categories

The initial deterministic corpus covers:

| Category | Case ID | Coverage |
| --- | --- | --- |
| `reset_smoke` | `reset_smoke.add_slot0` | Cold reset into the first slot-0 retire packet. |
| `integer_ops` | `integer_ops.add_mul` | Straight-line integer writes and dependent retire order. |
| `capability_derivation` | `capability_derivation.csetaddr_candperm` | Capability cursor derivation and permission masking. |
| `memory_tag_ops` | `memory_tag_ops.csc_clc_st48_ld48` | Capability store/load, integer store tag clear, and integer load. |
| `traps` | `traps.sys_to_tvc` | Precise synchronous `SYS` fault and direct TVC entry. |
| `calls_returns` | `calls_returns.direct_call_ret` | Direct `CALL`, protected return-stack push, and `RET`. |
| `fault_cases` | `fault_cases.divide_by_zero` | Integer divide-by-zero precise fault. |
| `fault_cases` | `fault_cases.slot1_48bit_placement` | 48-bit instruction placement fault from slot 1. |

## Determinism Rules

- Case IDs are stable API names for later RTL fixtures.
- Packet sequences start at 0 within each case and are contiguous.
- Fixture memories and reset vectors are fixed in the generator.
- The JSON output is sorted by key and contains only primitive JSON values.
- Unsupported or faulting work is represented as bounded precise retire
  packets, not as an indefinite stall.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Deterministic fixtures cover reset smoke. | Met. |
| Deterministic fixtures cover integer operations. | Met. |
| Deterministic fixtures cover capability derivation. | Met. |
| Deterministic fixtures cover memory/tag operations. | Met. |
| Deterministic fixtures cover traps. | Met. |
| Deterministic fixtures cover calls/returns. | Met. |
| Deterministic fixtures cover selected fault cases. | Met. |
| Expected retire packets are machine-readable. | Met. |

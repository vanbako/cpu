# RTL Readiness Gap Report

Story: I20-S08

Status: Draft readiness gate

This report is the current boundary for future RTL commits. The RTL
surface is intentionally fixture-slice based: it proves selected retire
packet paths against the semantic golden corpus, but it is not yet a
complete CPU implementation.

## Gate Command

Run this before future RTL commits:

```text
python tools\local_checks.py
```

Slice-specific checks covered by the gate through conformance tests:

- `python tools\rtl_smoke_slice.py --check`
- `python tools\rtl_cap_mem_slice.py --check`
- `python tools\rtl_fault_trap_slice.py --check`
- `python tools\verilator_diff_harness.py`

## Implemented RTL Surface

| Story | Surface | Artifacts | Golden cases | Mnemonics |
| --- | --- | --- | --- | --- |
| `I20-S01` | first-slice RTL contract | `docs/implementation/rtl-first-slice-contract.md` | - | - |
| `I20-S02` | semantic golden retire corpus | `src/cpu_v01/golden_traces.py`, `tools/golden_trace_corpus.py` | `reset_smoke.add_slot0`, `integer_ops.add_mul`, `capability_derivation.cmove_cgetaddr`, `capability_derivation.csetaddr_candperm`, `memory_tag_ops.csc_clc_st48_ld48`, `traps.sys_to_tvc`, `traps.sys_iret_return`, `calls_returns.direct_call_ret`, `fault_cases.divide_by_zero`, `fault_cases.invalid_tag_csetaddr`, `fault_cases.slot1_48bit_placement` | - |
| `I20-S03` | SystemVerilog package/interface contract | `rtl/cpu_v01_pkg.sv`, `src/cpu_v01/sv_contract.py` | - | - |
| `I20-S04` | Verilator differential harness skeleton | `src/cpu_v01/verilator_harness.py`, `tools/verilator_diff_harness.py` | - | - |
| `I20-S05` | reset, ADD, slot, and placement-fault smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_smoke_core.sv`, `rtl/cpu_v01_smoke_tb.sv` | `reset_smoke.add_slot0`, `fault_cases.slot1_48bit_placement` | `ADD` |
| `I20-S06` | capability register and memory/tag smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_cap_mem_core.sv`, `rtl/cpu_v01_cap_mem_tb.sv` | `capability_derivation.cmove_cgetaddr`, `capability_derivation.csetaddr_candperm`, `memory_tag_ops.csc_clc_st48_ld48`, `fault_cases.invalid_tag_csetaddr` | `CMOVE`, `CGETADDR`, `CSETADDR`, `CANDPERM`, `CSC`, `CLC`, `ST48`, `LD48` |
| `I20-S07` | precise fault, trap, IRET, and protected-stack smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_fault_trap_core.sv`, `rtl/cpu_v01_fault_trap_tb.sv` | `fault_cases.divide_by_zero`, `traps.sys_to_tvc`, `traps.sys_iret_return`, `calls_returns.direct_call_ret` | `DIV`, `SYS`, `IRET`, `CALL`, `RET` |

## Golden Corpus Coverage

| Case | Category | Packets | RTL status |
| --- | --- | ---: | --- |
| `reset_smoke.add_slot0` | `reset_smoke` | 1 | `I20-S05` RTL smoke slice |
| `integer_ops.add_mul` | `integer_ops` | 2 | semantic-only; ADD smoke covered, MUL deferred |
| `capability_derivation.cmove_cgetaddr` | `capability_derivation` | 2 | `I20-S06` RTL capability/memory slice |
| `capability_derivation.csetaddr_candperm` | `capability_derivation` | 2 | `I20-S06` RTL capability/memory slice |
| `memory_tag_ops.csc_clc_st48_ld48` | `memory_tag_ops` | 4 | `I20-S06` RTL capability/memory slice |
| `traps.sys_to_tvc` | `traps` | 1 | `I20-S07` RTL fault/trap slice |
| `traps.sys_iret_return` | `traps` | 2 | `I20-S07` RTL fault/trap slice |
| `calls_returns.direct_call_ret` | `calls_returns` | 2 | `I20-S07` RTL fault/trap slice |
| `fault_cases.divide_by_zero` | `fault_cases` | 1 | `I20-S07` RTL fault/trap slice |
| `fault_cases.invalid_tag_csetaddr` | `fault_cases` | 1 | `I20-S06` RTL capability/memory slice |
| `fault_cases.slot1_48bit_placement` | `fault_cases` | 1 | `I20-S05` RTL smoke slice |

## Partial Support Notes

- RTL is fixture-slice based; there is no integrated general-purpose CPU core yet.
- `ADD` is covered by the reset smoke fixture, not the full integer ALU family.
- `DIV` is covered for the divide-by-zero precise fault path; normal MDU results remain deferred.
- `CALL`/`RET` cover direct protected-stack transactions; `CALLC` and broader call hazards remain deferred.
- `SYS`/`IRET` cover direct synchronous trap entry and restore; interrupts and debug monitor entry remain deferred.

## Unsupported Instructions

Mandatory mnemonics without an RTL golden-slice path: `CPY`, `NEG`, `ADDU`, `SUB`, `SUBU`, `MUL`, `MULU`, `DIVU`, `MOD`, `MODU`, `NOT`, `AND`, `OR`, `XOR`, `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR`, `CMP`, `CMPU`, `TST`, `SETCC`, `CMOVCC`, `BSET`, `BCLR`, `LL48`, `SC48`, `CINCADDR`, `CSETBOUNDS`, `CSEAL`, `CUNSEAL`, `BRA`, `BCC`, `JMP`, `BRK`, `EPCCRD`, `EPCCWR`, `WFI`, `PAUSE`, `CALLC`, `FENCE`, `FENCE.I`, `SFENCE.VM`, `SFENCE.VM.ASID`, `SFENCE.VM.VA`, `SFENCE.VM.VA_ASID`, `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR`, `CCSRRD`, `CCSRWR`, `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL`.

## Unsupported Interfaces

- No integrated `cpu_v01_core` top-level is implemented.
- `cpu_v01_imem_if`, `cpu_v01_dmem_if`, and `cpu_v01_tagmem_if` are contract surfaces, not live ports in the slice RTL.
- Verilator run/build remains a harness boundary; observed trace comparison is supported when a trace file is provided.
- Interrupt, debug, MMIO, DMA, and secondary-core external inputs are not represented by slice RTL.
- Cache, TLB, coherence, and page-table ports are deferred.

## Known Deferrals

- Multicore execution.
- L1/L2 caches and noncoherent DMA.
- Full RADIX4 page walking and TLBs.
- Interrupt controller and MMIO device model.
- Branch predictor performance behavior.
- Firmware/kernel boot beyond fixtures needed by the golden corpus.
- Atomics, LL/SC reservations, fences, and cache-maintenance execution.
- Debug halt, single-step, and debug-monitor RTL entry.
- Full binary decoder, issue, hazard, replay, and external memory integration.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Implemented RTL surface is listed. | Met. |
| Known deferrals are listed. | Met. |
| Unsupported instructions and interfaces are listed. | Met. |
| Golden corpus coverage is listed. | Met. |
| Local command gating future RTL commits is listed. | Met. |

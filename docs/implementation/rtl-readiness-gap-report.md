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
- `python tools\rtl_scalar_control_slice.py --check`
- `python tools\rtl_mmu_tlb_slice.py --check`
- `python tools\rtl_atomic_cache_slice.py --check`
- `python tools\rtl_control_trap_slice.py --check`
- `python tools\verilator_diff_harness.py --suite fast`
- `python tools\rtl_semantic_closure.py --check`

Verilator fixture build commands for the current self-checking RTL slices:

| Fixture | Top module | Command |
| --- | --- | --- |
| reset/add smoke | `cpu_v01_smoke_tb` | `verilator --binary --timing --top-module cpu_v01_smoke_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_smoke_core.sv rtl/cpu_v01_smoke_tb.sv` |
| capability/memory smoke | `cpu_v01_cap_mem_tb` | `verilator --binary --timing --top-module cpu_v01_cap_mem_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_cap_mem_core.sv rtl/cpu_v01_cap_mem_tb.sv` |
| fault/trap smoke | `cpu_v01_fault_trap_tb` | `verilator --binary --timing --top-module cpu_v01_fault_trap_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fault_trap_core.sv rtl/cpu_v01_fault_trap_tb.sv` |
| scalar/control smoke | `cpu_v01_scalar_control_tb` | `verilator --binary --timing --top-module cpu_v01_scalar_control_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_scalar_control_core.sv rtl/cpu_v01_scalar_control_tb.sv` |
| MMU/TLB smoke | `cpu_v01_mmu_tlb_tb` | `verilator --binary --timing --top-module cpu_v01_mmu_tlb_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_mmu_tlb_core.sv rtl/cpu_v01_mmu_tlb_tb.sv` |
| atomic/cache smoke | `cpu_v01_atomic_cache_tb` | `verilator --binary --timing --top-module cpu_v01_atomic_cache_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_atomic_cache_core.sv rtl/cpu_v01_atomic_cache_tb.sv` |
| control/trap smoke | `cpu_v01_control_trap_tb` | `verilator --binary --timing --top-module cpu_v01_control_trap_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_control_trap_core.sv rtl/cpu_v01_control_trap_tb.sv` |

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
| `I21-S01` | scalar integer, branch/control, CSR, and CCSR smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_scalar_control_core.sv`, `rtl/cpu_v01_scalar_control_tb.sv` | - | `CPY`, `NEG`, `ADD`, `ADDU`, `SUB`, `SUBU`, `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, `MODU`, `NOT`, `AND`, `OR`, `XOR`, `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR`, `CMP`, `CMPU`, `TST`, `SETCC`, `CMOVCC`, `BSET`, `BCLR`, `BRA`, `BCC`, `JMP`, `BRK`, `EPCCRD`, `EPCCWR`, `PAUSE`, `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR`, `CCSRRD`, `CCSRWR` |
| `I21-S02` | RADIX4, TLB, SATP, ASID, page-fault, and SFENCE smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_mmu_tlb_core.sv`, `rtl/cpu_v01_mmu_tlb_tb.sv` | - | `SFENCE.VM`, `SFENCE.VM.ASID`, `SFENCE.VM.VA`, `SFENCE.VM.VA_ASID` |
| `I21-S03` | LL/SC, reservation, fence, and cache-maintenance smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_atomic_cache_core.sv`, `rtl/cpu_v01_atomic_cache_tb.sv` | - | `LL48`, `SC48`, `FENCE`, `FENCE.I`, `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL` |
| `I21-S04` | CALLC, RET pop faults, SYS/SCALL, syscall frame, and IRET smoke RTL | `rtl/cpu_v01_pkg.sv`, `rtl/cpu_v01_control_trap_core.sv`, `rtl/cpu_v01_control_trap_tb.sv` | `callc.entry_success`, `callc.entry_tag_fault`, `ret.pop_success`, `ret.pop_underflow_tag`, `ret.unprotected_permission_fault`, `sys.sys_trap_frame_save`, `sys.scall_alias_trap_frame_save`, `syscall.ok_frame_restore_iret` | `CALLC`, `RET`, `SYS`, `SCALL`, `IRET` |
| `I21-S05` | Verilator fast/slow regression-suite gate | `src/cpu_v01/verilator_harness.py`, `tools/verilator_diff_harness.py` | - | - |
| `I21-S06` | single-core RTL semantic closure report | `docs/implementation/rtl-semantic-closure.md`, `tools/rtl_semantic_closure.py` | - | - |

## Golden Corpus Coverage

| Case | Category | Packets | RTL status |
| --- | --- | ---: | --- |
| `reset_smoke.add_slot0` | `reset_smoke` | 1 | `I20-S05` RTL smoke slice |
| `integer_ops.add_mul` | `integer_ops` | 2 | `I21-S01` RTL scalar/control slice projection |
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
- `I21-S01` expands scalar, branch, CSR, and CCSR coverage as a deterministic slice; full decode and issue remain deferred.
- `I21-S02` expands RADIX4, TLB, SATP, ASID, page-fault, and SFENCE coverage as a deterministic slice; integrated page-walker ports remain deferred.
- `I21-S03` expands LL/SC, reservation, fence, and cache-maintenance coverage as a deterministic slice; integrated cache hierarchy behavior remains deferred.
- `I21-S04` expands `CALLC`, `RET` pop faults, `SYS`/`SCALL`, syscall frame save/restore, and `IRET` user return as a deterministic slice.
- `CALL`/`RET`/`CALLC` cover protected-stack transactions; broader call hazards remain deferred.
- `SYS`/`SCALL`/`IRET` cover direct synchronous trap entry and restore; interrupts and debug monitor entry remain deferred.

## Unsupported Instructions

Mandatory mnemonics without an RTL golden-slice path: `CINCADDR`, `CSETBOUNDS`, `CSEAL`, `CUNSEAL`, `WFI`.

## Unsupported Interfaces

- No integrated `cpu_v01_core` top-level is implemented.
- `cpu_v01_imem_if`, `cpu_v01_dmem_if`, and `cpu_v01_tagmem_if` are contract surfaces, not live ports in the slice RTL.
- Verilator run/build remains a harness boundary; observed trace comparison is supported when a trace file is provided.
- Interrupt, debug, MMIO, DMA, and secondary-core external inputs are not represented by slice RTL.
- Integrated cache hierarchy, coherence, integrated page-table walker, and remote TLB shootdown ports are deferred.

## Known Deferrals

- Multicore execution.
- L1/L2 cache hierarchy and noncoherent DMA.
- Integrated page-table walker ports, remote TLB shootdown, and MMU replay timing.
- Interrupt controller and MMIO device model.
- Branch predictor performance behavior.
- Firmware/kernel boot beyond fixtures needed by the golden corpus.
- Integrated cache hierarchy, store-buffer timing, and multicore coherence.
- Debug halt, single-step, and debug-monitor RTL entry.
- Full binary decoder, issue, hazard, replay, and external memory integration.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Implemented RTL surface is listed. | Met. |
| Known deferrals are listed. | Met. |
| Unsupported instructions and interfaces are listed. | Met. |
| Golden corpus coverage is listed. | Met. |
| Verilator fixture commands are listed. | Met. |
| Local command gating future RTL commits is listed. | Met. |

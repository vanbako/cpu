# RTL Capability And Memory Slice

Story: I20-S06

Status: Draft RTL smoke implementation

The second SystemVerilog slice extends the I20-S05 smoke RTL with deterministic
capability register and memory/tag behavior. It remains a bounded single-core
fixture, not a full CPU pipeline. Fault/trap entry, protected-stack control
flow, atomics, TLBs, caches, interrupts, debug, MMIO, DMA, and secondary cores
remain deferred.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds capability write, memory effect, and tag write retire packet fields. |
| `rtl/cpu_v01_cap_mem_core.sv` | Deterministic capability/memory slice for `CMOVE`, `CGETADDR`, `CSETADDR`, `CANDPERM`, `CSC`, `CLC`, `ST48`, `LD48`, and invalid-tag fault. |
| `rtl/cpu_v01_cap_mem_tb.sv` | Verilator-oriented smoke testbench for final register, memory, tag, and fault observations. |

## Local Commands

Validate the source/golden projection boundary:

```text
python tools\rtl_cap_mem_slice.py --check
```

Print the packet projection:

```text
python tools\rtl_cap_mem_slice.py --json
```

The projection is derived from these golden corpus cases:

- `capability_derivation.cmove_cgetaddr`;
- `capability_derivation.csetaddr_candperm`;
- `memory_tag_ops.csc_clc_st48_ld48`;
- `fault_cases.invalid_tag_csetaddr`.

## Covered Behavior

- `CMOVE` copies capability payload and tag to `C2`.
- `CGETADDR` writes the moved cursor to `D3`.
- `CSETADDR` derives a new capability cursor for `C4`.
- `CANDPERM` reduces permissions to `LD` for `C5`.
- `CSC` writes capability payload and tag to a memory slot.
- `CLC` reloads payload and tag into `C6`.
- `ST48` writes an integer payload and clears the overlapped capability tag.
- `LD48` reads the integer payload after the tag clear.
- Invalid source tag on `CSETADDR` produces `CAPABILITY_TAG_FAULT` with
  `CAPCAUSE=TAG` and `FAULTCAPIDX=C1` before destination writeback.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| RTL passes golden cases for capability payload/tag registers. | Met. |
| RTL covers `CMOVE`, `CGETADDR`, `CSETADDR`, and `CANDPERM`. | Met. |
| RTL covers `LD48`, `ST48`, `CLC`, and `CSC`. | Met. |
| RTL covers tag clears. | Met. |
| RTL covers invalid-tag faults. | Met. |

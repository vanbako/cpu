# RTL Integrated Core Plan

Story: I22-S01

Status: Planned implementation profile

Covered implementation stories: I22-S01 through I22-S08.

## Purpose

I22 converts the I20 and I21 fixture-slice RTL into a single integrated
`cpu_v01_core` that can run golden programs through real top-level fetch,
decode, execute, memory, trap, and retire paths.

The goal is not a multicore or fabric implementation. The CPU repository should
produce one deterministic single-core RTL top level with clear external
attachment points. Point-to-point module links, switch routing, discovery, and
computer-level topology remain separate computer-architecture work.

## Integration Boundary

The integrated core must expose CPU-owned interfaces only:

- clock and reset;
- instruction memory request/response;
- data memory request/response;
- tag-memory request/response for capability slots;
- interrupt, event, and debug-observation inputs that can remain minimally
  stubbed until later stories;
- retire packet output for the differential harness.

The core must not assume a shared system bus. Later endpoint or fabric work
should adapt to these CPU-visible memory, tag, event, and retire contracts.

## Story Refinement

| Story | Refined deliverable | Done when |
| --- | --- | --- |
| I22-S01 | Integrated `cpu_v01_core` shell and port contract. | The top-level module elaborates with package types, reset state is visible, all external ports have deterministic idle behavior, and a no-program smoke build can produce retire/debug idle observations. |
| I22-S02 | Fetch, slot sequencing, and 12/24/48 decode path. | Instruction-memory fixtures drive legal and illegal placement cases through the top level, including hidden slot fall-through, explicit slot-0 targets, and illegal encodings. |
| I22-S03 | Scalar, branch, CSR, CCSR, and retire execution. | Scalar/control golden programs retire from `cpu_v01_core` with matching architectural writes, redirects, fault packets, and first-mismatch diagnostics. |
| I22-S04 | Capability register, data memory, and tag-memory integration. | Capability derivation plus `LD48`/`ST48`/`CLC`/`CSC` cases use the top-level data and tag ports and preserve tag non-forgery and precise-fault no-effect rules. |
| I22-S05 | Trap, syscall, protected call, and return integration. | Direct trap entry, `IRET`, `CALL`, `CALLC`, protected `RET`, `SYS`/`SCALL`, syscall frame restore, and priority cases pass through one redirect/trap path. |
| I22-S06 | MMU, TLB, SATP/ASID, page-walk, and translation fault integration. | Instruction and data accesses share the integrated translation path; page-walk, permission, memory-type, stale TLB, and `SFENCE.VM*` cases pass. |
| I22-S07 | LL/SC, reservation, fence, and cache-maintenance integration. | Top-level cases cover reservation lifecycle, conflict clears, trap/fence clears, `FENCE`, `FENCE.I`, and `CACHE.*` access checks at retire boundaries. |
| I22-S08 | Integrated-core Verilator regression gate. | Fast and slow harness suites can select `cpu_v01_core` cases by ID, compare observed retire traces, and report remaining deferrals separately from slice-only coverage. |

## Readiness Rules

Each story should leave one of these concrete artifacts:

- an RTL module or testbench under `rtl/`;
- a Python harness/model update under `src/cpu_v01/` or `tools/`;
- a conformance test under `tests/conformance/`;
- a litmus projection under `tests/litmus/` for ordering-heavy cases;
- an implementation note when behavior is intentionally deferred.

I22-S01 introduces `rtl/cpu_v01_core.sv` and the
`rtl/cpu_v01_core_shell_tb.sv` no-program smoke boundary. Existing slice RTL
should remain available as small regression fixtures until the integrated core
fully covers their golden cases.

## Deferrals

I22 keeps these surfaces out of scope:

- multicore execution;
- point-to-point fabric links and switches;
- endpoint enumeration, routing, link training, and packet protocol;
- coherent interconnect and external cache hierarchy;
- noncoherent external-agent DMA beyond existing CPU-visible fixture effects;
- debug monitor entry beyond observation hooks needed by the retire harness;
- firmware or kernel boot flows that are not needed by selected golden cases.

## Acceptance Review

| Acceptance criterion | Planned evidence |
| --- | --- |
| The integrated-core top-level boundary is explicit. | `rtl/cpu_v01_core.sv`, package/interface docs, and I22-S01 tests. |
| Fixture slices are promoted rather than discarded. | Golden cases move from slice projection to observed `cpu_v01_core` retire traces. |
| CPU/fabric ownership is separated. | External links remain abstract CPU-visible ports; fabric topology stays out of this repository. |
| Regression gating is concrete. | I22-S08 updates the Verilator harness and local gate to fail on integrated-core mismatches. |

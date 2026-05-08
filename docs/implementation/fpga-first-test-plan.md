# FPGA First-Test Bring-Up Plan

Story: I23-S01

Status: Planned FPGA first-test profile

Covered implementation stories: I23-S01 through I23-S06.

## Purpose

I23 turns the integrated single-core `cpu_v01_core` from a Verilator-gated RTL
target into the smallest useful FPGA smoke design. The objective is to prove
that the core can be clocked, reset, connected to FPGA-local memories, loaded
with a tiny deterministic program, and observed through simple board-visible
signals.

This is not a complete SoC milestone. The first FPGA test should avoid external
DRAM, complex MMIO, multicore startup, fabric routing, cache hierarchy tuning,
and long-running firmware. Those surfaces stay behind the simulation gates until
the first physical clock/reset/memory path is trustworthy.

## Target Profile

The first-test design should be board-neutral at the CPU wrapper boundary and
board-specific only at the constraint and pin overlay layer.

Minimum assumptions:

- one free-running FPGA clock that can be divided or constrained to a safe
  bring-up frequency;
- one asynchronous board reset normalized by the top wrapper;
- enough block RAM for a tiny instruction ROM, data RAM, and tag RAM;
- at least one LED or status pin for pass/fail observation;
- optional UART or integrated logic analyzer probes for retire, fault, and
  heartbeat visibility;
- no dependency on external DRAM, cache-coherent fabric, or board peripherals
  other than reset, clock, status, and optional debug observation.

## Bring-Up Boundary

The FPGA top level should instantiate the existing integrated core through the
same CPU-owned contracts used by the RTL regression gate:

- clock and synchronized reset;
- instruction memory request and response;
- data memory request and response;
- tag-memory request and response for capability slots;
- interrupt/event inputs held in deterministic idle state;
- retire/fault/debug observation outputs projected to status probes.

The wrapper may adapt memory latency to FPGA BRAM timing, but it must not change
architectural retire behavior. Any latency-specific behavior that cannot yet be
represented in the golden trace harness should be listed as an I23 deferral.

## Story Refinement

| Story | Refined deliverable | Done when |
| --- | --- | --- |
| I23-S01 | FPGA first-test target profile and bring-up boundary. | The plan names clock/reset, BRAM memory map, ROM image format, observation outputs, tool flow, and non-goals for the first board smoke. |
| I23-S02 | Board-neutral `cpu_v01_fpga_top` wrapper. | The wrapper instantiates `cpu_v01_core`, synchronizes reset, ties idle interrupts/events, exposes status/debug pins, and elaborates with the core and memory adapters. |
| I23-S03 | FPGA ROM, data RAM, and tag RAM adapters. | BRAM-friendly adapters satisfy the core handshakes, load the tiny ROM image, provide deterministic reset contents, and clear tags on integer stores. |
| I23-S04 | Tiny smoke firmware and visible observation path. | A minimal program retires a deterministic sequence, writes pass/fail status, and exposes heartbeat, retire count, and fault cause through LEDs, UART, or ILA probes. |
| I23-S05 | Synthesis, implementation, and timing gate. | A scripted FPGA build runs synthesis and implementation, reports utilization and timing, and fails on missing constraints, black boxes, or unconstrained clocks/resets. |
| I23-S06 | First board bring-up runbook and evidence. | The runbook lists programming steps, reset procedure, expected observations, common failure triage, and captured first-pass evidence or the documented blocker. |

## First-Test Memory Map

The concrete sizes can change with the target board, but the initial map should
stay small and explicit:

| Region | Purpose | Initial expectation |
| --- | --- | --- |
| Instruction ROM | Reset program and pass/fail branch path. | Initialized from a generated text or memory initialization file derived from the tiny ROM fixture. |
| Data RAM | Scalar scratch state and status word. | Zeroed or explicitly initialized at configuration time. |
| Tag RAM | Capability-slot tags for data-memory capability operations. | Reset-cleared, with integer stores forcing the corresponding tag state invalid. |
| Status projection | Board-visible pass/fail, heartbeat, retire, and fault state. | Memory-mapped or wrapper-local status translated to LED/UART/ILA probes. |

## Acceptance Review

| Acceptance criterion | Planned evidence |
| --- | --- |
| The FPGA target is narrow enough for first hardware bring-up. | This profile, I23-S01 story row, and explicit non-goals. |
| The integrated core remains the CPU under test. | `cpu_v01_fpga_top` instantiates `cpu_v01_core` rather than a fixture slice. |
| FPGA memories preserve architectural tag behavior. | BRAM adapters and simulation tests cover initialization, load/store handshakes, and tag clear on integer writes. |
| The board can show a deterministic result without a debugger. | Pass/fail LED or status pin plus optional UART/ILA probes. |
| The FPGA build is repeatable. | One scripted synthesis/implementation command with constraints and timing/utilization reports. |
| The first physical test is auditable. | A runbook records programming steps, observed signals, timing result, and pass evidence or blocker. |

## Deferrals

- external DRAM and memory controllers;
- general-purpose MMIO peripheral set;
- bootloader, storage, or program download protocol;
- multicore startup and fabric links;
- coherent interconnect and external cache hierarchy;
- performance tuning beyond meeting a conservative first-test clock;
- broad firmware or kernel workloads beyond the deterministic smoke program.

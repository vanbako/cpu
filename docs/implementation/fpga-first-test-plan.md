# FPGA First-Test Bring-Up Plan

Story: I23-S01

Status: Planned FPGA first-test profile

Covered implementation stories: I23-S01 through I23-S06.

Structured profile:

```text
python tools\fpga_first_test_profile.py --check
```

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

Physical target board:

- board `Sipeed Tang Mega 138K Dock`, treated as the non-Pro Tang Mega 138K
  target for the first hardware smoke;
- FPGA `GW5AST-LV138PG484A`, IDE package `PBG484A`, and Device Version `B/C`
  until the actual SOM marking or JTAG scan says otherwise;
- board resources relevant to the first smoke: 6120 Kbits B-SRAM in 340
  blocks, 1080 Kbits distributed SRAM, 298 18x18 multipliers, 12 PLLs, 16
  global clocks, 24 high-speed clocks, one flash device, onboard USB JTAG/UART,
  4 battery LEDs plus 8 PMOD LEDs, 3 user keys plus one reconfig key, and 3.3 V
  GPIO tolerance on the expansion headers;
- first-test non-dependencies: 1 GiB DDR3, PCIe, USB3, HDMI, GbE, ADC, SD,
  audio, and hard AE350 RISC-V resources stay outside the initial CPU smoke.

Public-source package note: Sipeed's Chinese Tang Mega 138K page and FAQ name
`GW5AST-LV138PG484A` with package `PBG484A`, while the current English
precautions row and the openFPGALoader board table also mention
`GW5AST-LV138FPG676A` for Tang Mega 138K. `GW5AST-LV138FPG676A` is also the
consistent Tang Mega 138K Pro Dock device. I23-S05 must verify the actual SOM
marking or programmer/JTAG scan before locking the build script, and must take
clock/reset/LED pin assignments from Sipeed's `All PIN Constraints` package.

Minimum assumptions:

- profile name `cpu_v01_fpga_first_test_bram_smoke`;
- FPGA top module `cpu_v01_fpga_top`, with `cpu_v01_core` as the core under
  test;
- one free-running FPGA clock input named `board_clk_i` that can be divided or
  constrained to a first-test core clock at or below 25 MHz;
- one active-low asynchronous board reset input named `board_reset_n_i`,
  normalized by at least a two-stage synchronizer before it reaches the core;
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

| Region | Port | Base cell | Size | Purpose | Initial expectation |
| --- | --- | --- | --- | --- | --- |
| `instruction_rom` | `imem` | `0x000000001000` | 1024 cells | Reset program and pass/fail branch path. | Initialized from `build/fpga/first_test_rom.mem`. |
| `data_ram` | `dmem` | `0x000000010000` | 4096 cells | Scalar scratch state and status word. | Zeroed or initialized from `build/fpga/first_test_data.mem`. |
| `tag_ram` | `tagmem` | `0x000000010000` | 4096 slots | Capability-slot tags for the data RAM range. | Reset-cleared, with integer stores forcing the corresponding tag state invalid. |

The image format is `hex24-cells-v1`: one 6-hex-digit 24-bit cell per line in
ascending cell-address order. The ROM image is derived from the tiny reset smoke
fixture until I23-S04 replaces it with the dedicated FPGA smoke firmware.

## Observation Contract

| Signal | Required | Source | Purpose |
| --- | --- | --- | --- |
| `pass_led` | Yes | `first_test_status.pass` | Visible successful completion without a debugger. |
| `fail_led` | Yes | `first_test_status.fail` | Visible trapped or failed completion without a debugger. |
| `heartbeat_led` | Yes | `debug_retire_sequence` | Shows clock/reset and retire observation are alive. |
| `fault_code_probe` | No | `retire_packet.fault.cause` | UART or ILA fault triage. |
| `retire_count_probe` | No | `debug_retire_sequence` | UART or ILA retire progress. |

## Synthesis Flow Contract

I23-S05 owns the board-specific scripts, but I23-S01 fixes the flow contract:

1. lint or elaborate `cpu_v01_fpga_top`;
2. synthesize the BRAM smoke design for the verified Tang Mega 138K FPGA
   package;
3. place and route with Sipeed Tang Mega 138K board constraints;
4. report timing and utilization.

The flow must fail on a missing `cpu_v01_core` or memory black box,
unconstrained `board_clk_i` or `board_reset_n_i`, negative slack at the
first-test clock, or missing pass/fail observation pins.

I23-S05 is tracked in `docs/implementation/fpga-synthesis-gate.md` and checked
with:

```text
python tools\fpga_synthesis_gate.py --check
```

Official Gowin EDA is the primary synthesis/place-route/bitstream flow for the
first board test because Gowin's tool covers code synthesis, place and route,
bitstream generation, and download. Sipeed documents Tang Mega 138K support in
recent Gowin EDA releases and recommends the standalone 1.9.12 SP1 Programmer
for better flash programming compatibility. For volatile or flash programming,
the board exposes USB JTAG/UART; openFPGALoader also lists a `tangmega138k`
board entry, but the device/package ambiguity above must be resolved before
using that path as an automated gate.

## Target Board Source Notes

| Source | Used for | Follow-up |
| --- | --- | --- |
| Sipeed Tang Mega 138K Dock wiki: <https://wiki.sipeed.com/hardware/en/tang/tang-mega-138k/mega-138k> | Board features, resources, USB JTAG/UART, Gowin EDA/programmer guidance, and hardware-resource links. | Verify the English-page package inconsistency against the physical SOM. |
| Sipeed Tang Mega 138K Chinese wiki: <https://wiki.sipeed.com/hardware/zh/tang/tang-mega-138k/mega-138k> | Cross-check for `GW5AST-LV138PG484A`, `PBG484A`, Device Version `B/C`, and 3.3 V GPIO warning. | Prefer this package data for the non-Pro Dock until board scan confirms. |
| Sipeed Tang Mega 138K examples: <https://github.com/sipeed/TangMega-138K-example> | Board examples, PMOD LED path, DDR/peripheral examples, and likely reference project structure. | Pull only pin/project details needed for the first-test overlay. |
| Gowin EDA page: <https://www.gowinsemi.com/en/support/home/> | Official vendor flow scope for synthesis, place and route, bitstream generation, download, and GAO debug. | Install/select the supported Windows tool version before I23-S05. |
| openFPGALoader board list: <https://trabucayre.github.io/openFPGALoader/compatibility/board.html> | Alternative programming path and board flag `tangmega138k`. | Use only after confirming package/device compatibility with this board. |

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

# FPGA Board Bring-Up Runbook

Story: I23-S06

Status: Runbook implemented with physical-execution blocker

Structured runbook:

```text
python tools\fpga_bringup_runbook.py --check
```

Command plan:

```text
python tools\fpga_bringup_runbook.py --plan
```

## Purpose

I23-S06 turns the first-test synthesis gate into a repeatable physical
bring-up procedure for the Sipeed Tang Mega Dock with 138K SOM. The runbook covers the
programming path, reset procedure, expected LED/probe observations, first-pass
evidence, and failure triage.

The story is not a physical pass yet. A board execution can only be accepted
after I23-S05 has a verified Tang Mega 138K CST overlay, a completed Gowin
build, timing/utilization/port reports, and a bitstream. Until then, this
document records the documented blocker required by the story acceptance text.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_bringup.py` | Structured I23-S06 board runbook, evidence contract, command plan, and validator. |
| `tools/fpga_bringup_runbook.py` | CLI wrapper for checking, rendering JSON, and printing the board bring-up plan. |
| `tests/conformance/test_i23_s06_fpga_board_bringup.py` | Conformance tests for runbook prerequisites, procedure, observations, evidence, triage, and documentation. |
| `docs/implementation/fpga-board-bringup.md` | This implementation note. |

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega Dock with 138K SOM` |
| Device | `GW5AST-LV138PG484A` pending physical verification |
| IDE package | `PBG484A` pending physical verification |
| Top module | `cpu_v01_fpga_top` |
| Synthesis gate | `python tools\fpga_synthesis_gate.py --check` |
| Programming mode | Gowin Programmer SRAM first, flash only after repeatable SRAM pass |

The package/device ambiguity remains a hard gate. The non-Pro first-test target
is `GW5AST-LV138PG484A` with `PBG484A`, but public sources also mention
`FPG676`. The first board session must record the board marking or
programmer/JTAG scan before the CST and Gowin device selection are considered
locked.

## Prerequisites

| Prerequisite | Required evidence | Blocker if missing |
| --- | --- | --- |
| `device_package_confirmed` | Board marking or programmer/JTAG scan confirms `GW5AST-LV138PG484A`/`PBG484A`, or updates the target overlay. | Do not lock the CST or program the board until the `PG484` versus `FPG676` ambiguity is resolved. |
| `i23_s05_gate_passed` | `python tools\fpga_synthesis_gate.py --check` passes and Gowin timing, utilization, ports, and bitstream reports exist. | Record a documented blocker instead of claiming first-board execution. |
| `constraints_verified` | `constraints/tang_mega_138k_first_test.cst` maps `board_clk_i`, `board_reset_n_i`, `pass_led_o`, `fail_led_o`, and `heartbeat_led_o` with correct IO standard and polarity; I24-S02 is checked with `python tools\fpga_constraints_overlay.py --check`. | Return to I24-S02 and extract the verified Sipeed pin overlay. |
| `board_power_and_usb_ready` | Tang Mega Dock with 138K SOM is powered and onboard USB JTAG/UART enumerates. | Triage cable, driver, boot mode, and board power before programming. |
| `programmer_selected` | Gowin Programmer or openFPGALoader command is selected for the verified device, with SRAM programming selected first. | Do not use flash programming until volatile programming has a repeatable pass. |

## Procedure

1. Record board identity. Inspect the Tang Mega 138K SOM marking and/or run a
   programmer/JTAG scan. Save the observed device, package, and device version.
   Stop if the board reports `FPG676` or another package not covered by the
   current target profile.
2. Verify I23-S05. Run `python tools\fpga_synthesis_gate.py --check`, emit the
   Gowin Tcl, run `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl`,
   and audit reports with
   `python tools\fpga_synthesis_gate.py --check-reports build\fpga\tang_mega_138k\first_test`.
3. Prepare the board. Connect board power and onboard USB JTAG/UART, confirm
   3.3 V IO safety for the selected LED pins, and keep `board_reset_n_i`
   asserted.
4. Program SRAM. Program the first-test `.fs` bitstream with Gowin Programmer
   SRAM mode. Use openFPGALoader only after the device/package scan matches the
   selected `tangmega138k` path.
5. Release reset. Release `board_reset_n_i` and observe the board for at least
   10 seconds.
6. Capture evidence. Save the programming log, report bundle, device scan,
   reset observation, and LED photo or video. If the board cannot be executed,
   capture the exact documented blocker instead.

## Expected Observations

| Observation | Required | Expected result | Evidence capture |
| --- | --- | --- | --- |
| `heartbeat_led_o` | Yes | Toggles after reset release, proving `board_clk_i` and synchronized reset are alive. | Short video or logic capture showing heartbeat activity. |
| `pass_led_o` | Yes | Asserts after the smoke firmware reaches its deterministic pass condition. | Photo or video that also identifies the programmed board. |
| `fail_led_o` | Yes | Remains deasserted during and after the pass observation. | Photo, video, or probe capture showing fail low when pass is high. |
| `status_retire_count_o` | No | Advances to at least 8 retired instructions during the smoke run. | GAO, UART, or logic-analyzer capture when available. |
| `status_fault_code_o` | No | Stays zero for the passing first-test program. | GAO, UART, or logic-analyzer capture when available. |

## Evidence Contract

| Evidence | Required | Path or record | Acceptance rule |
| --- | --- | --- | --- |
| `device_scan_record` | Yes | `docs/implementation/evidence/i23_s06_device_scan.txt` | Names the observed FPGA device, package, and device version used by the build. |
| `i23_s05_report_bundle` | Yes | `build/fpga/tang_mega_138k/first_test/impl` | Includes synthesis, timing, port, utilization, and bitstream artifacts accepted by `python tools\fpga_gowin_build.py --audit-reports`. |
| `bitstream_path` | Yes | `build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs` | Matches the build audited immediately before programming. |
| `programming_log` | Yes | `docs/implementation/evidence/i24_s04_sram_programming.txt` | I24-S04 evidence record names the programmer command/tool, selected SRAM mode, target device, successful exit, and captured log path. |
| `reset_observation` | Yes | `docs/implementation/evidence/i23_s06_reset_observation.txt` | Records reset assertion/release timing and the first 10 seconds of observation. |
| `led_photo_or_video` | Yes | `docs/implementation/evidence/i23_s06_led_evidence.*` | Shows `heartbeat_led_o` activity, `pass_led_o` asserted, and `fail_led_o` deasserted on the programmed board. |
| `first_board_archive` | Yes | `docs/implementation/evidence/i24_s05_first_board_archive.txt` | Links scan, reports, bitstream, programming, reset, LED/probe evidence, and residual blocker disposition accepted by `python tools\fpga_first_board_archive.py --check`. |
| `debug_evidence` | Failure only | `docs/implementation/evidence/i25_s05_debug_evidence.txt` | Required for nontrivial failures; accepted by `python tools\fpga_debug_evidence.py --check` and records UART or GAO/ILA capture plus replay mapping. |
| `documented_blocker` | Yes | `docs/implementation/fpga-board-bringup.md#current-blocker` | Acceptable instead of physical pass evidence only when board execution cannot yet be performed. |

## Triage

| Symptom | Likely causes | Actions |
| --- | --- | --- |
| `no_jtag_device` | USB cable/driver issue, board power missing, wrong programmer mode. | Verify power, try Gowin Programmer scan, and record scan failure as blocker. |
| `programmer_rejects_device_or_package` | `PG484`/`FPG676` target mismatch, wrong Device Version B/C, stale CST/project. | Record the actual scan, update the target profile, and rerun I23-S05 before programming. |
| `no_heartbeat` | `board_clk_i` not pinned, `board_reset_n_i` held active, PLL or clock constraint issue. | Probe clock/reset, inspect the port report, and rerun with reset held/released observations. |
| `fail_led_asserted` | Smoke firmware trapped, memory image mismatch, tag RAM initialization mismatch. | Capture `status_fault_code_o`, capture `status_retire_count_o`, map the packet with `python tools\fpga_replay_mapper.py --map-hex`, replay the selected Verilator case, and file I25-S05 debug evidence. |
| `pass_never_asserts` | ROM did not execute, retire path stalled, LED polarity inverted. | Check heartbeat, capture retire count, classify with I25-S05 as `firmware`, `memory`, `trap`, or `translation`, and verify LED polarity and ROM image. |
| `timing_or_report_missing` | Gowin flow incomplete, report paths changed, negative timing slack. | Rerun report audit, fix the I23-S05 gate, and do not count board evidence. |

## Current Blocker

- Physical Tang Mega 138K device/package scan has not been captured in this
  repository. I24-S01 tracks this through
  `docs/implementation/fpga-board-identity.md` and
  `python tools\fpga_board_identity.py --check`.
- Verified Tang Mega 138K CST pin overlay for `board_clk_i`,
  `board_reset_n_i`, `pass_led_o`, `fail_led_o`, and `heartbeat_led_o` is
  still pending.
- Gowin timing, utilization, ports, and bitstream reports are not yet present
  under `build/fpga/tang_mega_138k/first_test`.
- No I24-S04 programming record, reset observation, or LED photo/video evidence
  has been captured yet. The concrete programming gate is tracked in
  `docs/implementation/fpga-board-programming.md` and checked with
  `python tools\fpga_board_programming.py --check`.
- No I24-S05 first-board archive has been captured yet.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Programming steps are documented. | Met by the board identity, I23-S05 verification, board preparation, SRAM programming, reset, and capture procedure. |
| Reset handling is explicit. | Met by the keep-reset-asserted preparation step and `board_reset_n_i` release observation. |
| Expected observations are explicit. | Met by required `heartbeat_led_o`, `pass_led_o`, and `fail_led_o`, plus optional `status_retire_count_o` and `status_fault_code_o`. |
| Triage paths are documented. | Met by JTAG, package, heartbeat, fail LED, missing pass, and missing report triage rows. |
| Captured evidence or blocker is available. | Met by the evidence contract and this current blocker section until physical board execution is possible. |

# FPGA Retro Console Identity

Story: I34-S01

Status: Retro Console identified as a 60K SOM alternate target; first-pass CPU
bring-up continues on the Tang Mega Dock with the 138K SOM.

Structured gate:

```text
python tools\fpga_retro_console_identity.py --check
```

Evidence template:

```text
python tools\fpga_retro_console_identity.py --template
```

Audit captured evidence:

```text
python tools\fpga_retro_console_identity.py --audit-evidence docs\implementation\evidence\i34_s01_retro_console_identity.txt
```

Required upstream gates:

```text
python tools\fpga_first_test_profile.py --check
python -m unittest tests.conformance.test_i23_s06_fpga_board_bringup
```

## Purpose

I34-S01 records that the Retro Console path is the `Sipeed Tang Retro Console
with 60K SOM`, not a 138K first-pass board. The observed JTAG identity for the
Retro Console 60K path is `0x0001481B`, matching a `GW5AT/GW5A 60B-class`
device. The active 138K CPU bring-up path is now
`Sipeed Tang Mega Dock with 138K SOM`.

This story is only the Retro Console 60K identity and deferral gate. It does
not claim an actual package, clock pin, reset pin, LED pin, UART pin, or board
pass. I34-S02 must use captured 60K evidence and do not assume Dock pin names.

## Evidence Path

```text
docs/implementation/evidence/i34_s01_retro_console_identity.txt
```

## Evidence Format

The captured evidence record is a key/value file:

```text
story=I34-S01
board=Sipeed Tang Retro Console with 60K SOM
source=
observed_device=
observed_idcode=
observed_package=
observed_device_version=
gowin_part=
programming_path=
clock_sources=
reset_sources=
visible_outputs=
uart_debug_access=
selected_first_target=no
primary_138k_target=Sipeed Tang Mega Dock with 138K SOM
observed_tool=
observed_at=
evidence_notes=
```

Required fields:

| Field | Required | Expected content |
| --- | --- | --- |
| `story` | Yes | `I34-S01`. |
| `board` | Yes | `Sipeed Tang Retro Console with 60K SOM`. |
| `source` | Yes | `board_marking`, `programmer_jtag_scan`, `vendor_schematic`, or a combination. |
| `observed_device` | Yes | Exact 60B-class device string, for example `GW5AT-60B` or `GW5A-60B`. |
| `observed_idcode` | Yes | `0x0001481B`. |
| `observed_package` | Yes | Exact package string from marking, vendor file, or programmer scan. |
| `observed_device_version` | Yes | Gowin Device Version selected for build, normally `B` or `C`. |
| `gowin_part` | Yes | Full Gowin target part/package string for I34-S02 and I34-S03. |
| `programming_path` | Yes | SRAM programming route, cable, and tool, for example `Gowin Programmer SRAM`. |
| `clock_sources` | Yes | Verified clock source names and frequencies for constraints. |
| `reset_sources` | Yes | Reset input selected for the first CPU test. |
| `visible_outputs` | Yes | LED, display, PMOD, or probe pins for heartbeat/pass/fail. |
| `uart_debug_access` | Yes | UART/JTAG/debug path for status packets or monitor traffic. |
| `selected_first_target` | Yes | `no`. |
| `primary_138k_target` | Yes | `Sipeed Tang Mega Dock with 138K SOM`. |
| `observed_tool` | Yes | Tool or method used to capture the evidence. |
| `observed_at` | Yes | Local date/time of capture. |
| `evidence_notes` | No | Photo, screenshot, raw scan log path, or pinout caveats. |

## Capture Procedure

1. Inspect the Retro Console board marking and record the printed FPGA device
   and package when visible.
2. Run a Gowin Programmer scan and record the 60K device, ID code, package,
   Device Version, and exact `gowin_part` setting that a 60K build would use.
3. Record the SRAM programming path. `Gowin Programmer SRAM` is the preferred
   first evidence path unless a verified alternative is available.
4. Record the clock source, reset source, visible outputs, and UART/debug
   access that can be used for heartbeat, pass/fail, and status packet capture.
5. Keep `selected_first_target=no` and
   `primary_138k_target=Sipeed Tang Mega Dock with 138K SOM` so the Retro
   Console 60K path cannot silently replace the active 138K path.
6. Run `python tools\fpga_retro_console_identity.py --audit-evidence`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `alternate_target_verified` | Required fields are complete, the device is 60B-class, `observed_idcode=0x0001481B`, and the Mega Dock 138K SOM remains primary. | Use the record as the I34-S02 CST/SDC source of truth for the alternate 60K path. |
| `invalid` | Evidence is malformed, incomplete, names the wrong board/story, selects the Retro Console first, or names a non-60K device. | Fix or recapture the evidence record. |
| `blocked` | No evidence file exists yet. | Keep I34-S02 blocked and do not lock board constraints. |

## Handoff

I34-S02 consumes the observed device/package, `gowin_part`, clock source, reset
source, visible output, and UART/debug access fields for a Retro Console 60K
overlay. I34-S03 consumes the same 60K Gowin target and programming path if the
alternate path is built. I34-S06 archives the Retro Console 60K pass or blocker
without taking over I31/I32, which continue on the Tang Mega Dock with 138K SOM.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Retro Console is treated as a 60K SOM target. | Met by `board=Sipeed Tang Retro Console with 60K SOM`, `GW5AT/GW5A 60B-class`, and `observed_idcode=0x0001481B`. |
| Mega Dock with 138K SOM remains the active first-pass target. | Met by `selected_first_target=no` and `primary_138k_target=Sipeed Tang Mega Dock with 138K SOM`. |
| Device/package and toolchain target are explicit. | Met by required `observed_device`, `observed_idcode`, `observed_package`, `observed_device_version`, and `gowin_part` fields. |
| Programming path, clock/reset, visible outputs, and UART/debug access are explicit. | Met by required handoff fields and audit. |
| Constraints are blocked until evidence exists. | Met by the default `blocked` audit when no evidence file exists. |

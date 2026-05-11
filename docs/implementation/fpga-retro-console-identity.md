# FPGA Retro Console Identity

Story: I34-S01

Status: Retro Console selected as active first physical CPU target; physical
identity capture blocked until board marking or programmer scan evidence is
recorded.

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

I34-S01 makes the `Sipeed Tang 138K Retro Console` the active first physical
CPU test board because that is the available board to test first. The existing
`Sipeed Tang Mega 138K Dock` path remains as a fallback target and should not
be deleted.

This story is only the identity and first-target selection gate. It does not
claim an actual FPGA package, clock pin, reset pin, LED pin, UART pin, or board
pass. I34-S02 must use the captured evidence and do not assume Dock pin names.

## Evidence Path

```text
docs/implementation/evidence/i34_s01_retro_console_identity.txt
```

## Evidence Format

The captured evidence record is a key/value file:

```text
story=I34-S01
board=Sipeed Tang 138K Retro Console
source=
observed_device=
observed_package=
observed_device_version=
gowin_part=
programming_path=
clock_sources=
reset_sources=
visible_outputs=
uart_debug_access=
selected_first_target=yes
supersedes_board=Sipeed Tang Mega 138K Dock
observed_tool=
observed_at=
evidence_notes=
```

Required fields:

| Field | Required | Expected content |
| --- | --- | --- |
| `story` | Yes | `I34-S01`. |
| `board` | Yes | `Sipeed Tang 138K Retro Console`. |
| `source` | Yes | `board_marking`, `programmer_jtag_scan`, `vendor_schematic`, or a combination. |
| `observed_device` | Yes | Exact device string from marking, vendor file, or programmer scan. |
| `observed_package` | Yes | Exact package string from marking, vendor file, or programmer scan. |
| `observed_device_version` | Yes | Gowin Device Version selected for build, normally `B` or `C`. |
| `gowin_part` | Yes | Full Gowin target part/package string for I34-S02 and I34-S03. |
| `programming_path` | Yes | SRAM programming route, cable, and tool, for example `Gowin Programmer SRAM`. |
| `clock_sources` | Yes | Verified clock source names and frequencies for constraints. |
| `reset_sources` | Yes | Reset input selected for the first CPU test. |
| `visible_outputs` | Yes | LED, display, PMOD, or probe pins for heartbeat/pass/fail. |
| `uart_debug_access` | Yes | UART/JTAG/debug path for status packets or monitor traffic. |
| `selected_first_target` | Yes | `yes`. |
| `supersedes_board` | Yes | `Sipeed Tang Mega 138K Dock`. |
| `observed_tool` | Yes | Tool or method used to capture the evidence. |
| `observed_at` | Yes | Local date/time of capture. |
| `evidence_notes` | No | Photo, screenshot, raw scan log path, or pinout caveats. |

## Capture Procedure

1. Inspect the Retro Console board marking and record the printed FPGA device
   and package when visible.
2. Run a Gowin Programmer scan and record the device, package, Device Version,
   and the exact `gowin_part` setting that the build will use.
3. Record the SRAM programming path. `Gowin Programmer SRAM` is the preferred
   first evidence path unless a verified alternative is available.
4. Record the clock source, reset source, visible outputs, and UART/debug
   access that can be used for heartbeat, pass/fail, and status packet capture.
5. Keep `selected_first_target=yes` and
   `supersedes_board=Sipeed Tang Mega 138K Dock` to document that the Retro
   Console is tested first while the Dock path remains available.
6. Run `python tools\fpga_retro_console_identity.py --audit-evidence`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `selected_first_target` | Required fields are complete and the Retro Console is selected first. | Use the record as the I34-S02 CST/SDC source of truth. |
| `invalid` | Evidence is malformed, incomplete, names the wrong board/story, or does not select the Retro Console first. | Fix or recapture the evidence record. |
| `blocked` | No evidence file exists yet. | Keep I34-S02 blocked and do not lock board constraints. |

## Handoff

I34-S02 consumes the observed device/package, `gowin_part`, clock source, reset
source, visible output, and UART/debug access fields. I34-S03 consumes the same
Gowin target and programming path when building and auditing reports. I34-S06
archives the first Retro Console CPU pass or blocker and decides whether I31
and I32 continue on the Retro Console first or fall back to the Dock.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Retro Console is selected before the Tang Mega 138K Dock. | Met by `selected_first_target=yes` and `supersedes_board=Sipeed Tang Mega 138K Dock`. |
| Device/package and toolchain target are explicit. | Met by required `observed_device`, `observed_package`, `observed_device_version`, and `gowin_part` fields. |
| Programming path, clock/reset, visible outputs, and UART/debug access are explicit. | Met by required handoff fields and audit. |
| Constraints are blocked until evidence exists. | Met by the default `blocked` audit when no evidence file exists. |

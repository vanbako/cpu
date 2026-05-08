# FPGA Constraints Overlay

Story: I24-S02

Status: CST template and SDC implemented; verified pin overlay blocked

Structured gate:

```text
python tools\fpga_constraints_overlay.py --check
```

Evidence audit:

```text
python tools\fpga_constraints_overlay.py --audit-evidence docs\implementation\evidence\i24_s02_constraint_pins.txt
```

## Purpose

I24-S02 creates the first-test Tang Mega 138K constraint overlay boundary. It
defines the required signals, IO standard, clock period, evidence format, CST
template, and SDC timing file for the `cpu_v01_fpga_top` first board smoke.

The final `constraints/tang_mega_138k_first_test.cst` must not be created from
guesswork. The current repository provides
`constraints/tang_mega_138k_first_test.cst.template` and
`constraints/tang_mega_138k_first_test.sdc`; the pin evidence audit remains
`blocked` until `python tools\fpga_board_identity.py --check` passes and a real
I24-S01 identity record confirms `GW5AST-LV138PG484A` / `PBG484A`.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_constraints.py` | Structured I24-S02 overlay profile, CST/SDC renderers, evidence parser, audit rules, and validator. |
| `tools/fpga_constraints_overlay.py` | CLI wrapper for checking, printing JSON, printing CST/SDC templates, and auditing pin evidence. |
| `constraints/tang_mega_138k_first_test.cst.template` | Non-programming CST template with placeholder `I24_S02_PIN_*` tokens. |
| `constraints/tang_mega_138k_first_test.sdc` | First-test timing file with `board_clk_i` constrained to `40.000` ns and reset false-pathed from the async input. |
| `tests/conformance/test_i24_s02_fpga_constraints_overlay.py` | Conformance tests for the profile, templates, evidence audit, CLI, and documentation. |
| `docs/implementation/fpga-constraints-overlay.md` | This implementation note. |

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega 138K Dock` |
| Device | `GW5AST-LV138PG484A` |
| Package | `PBG484A` |
| Identity gate | `python tools\fpga_board_identity.py --check` |
| Final CST path | `constraints/tang_mega_138k_first_test.cst` |
| CST template | `constraints/tang_mega_138k_first_test.cst.template` |
| SDC path | `constraints/tang_mega_138k_first_test.sdc` |
| Evidence path | `docs/implementation/evidence/i24_s02_constraint_pins.txt` |

## Required Signals

| Signal | Direction | IO standard | Polarity | Evidence key | Purpose |
| --- | --- | --- | --- | --- | --- |
| `board_clk_i` | Input | `LVCMOS33` | free-running | `board_clk_i_pin` | 25 MHz first-test board clock constrained by `40.000` ns. |
| `board_reset_n_i` | Input | `LVCMOS33` | active low | `board_reset_n_i_pin` | Async board reset input synchronized inside `cpu_v01_fpga_top`. |
| `pass_led_o` | Output | `LVCMOS33` | active high or recorded in evidence | `pass_led_o_pin` | Visible first-test pass output. |
| `fail_led_o` | Output | `LVCMOS33` | active high or recorded in evidence | `fail_led_o_pin` | Visible first-test fail output. |
| `heartbeat_led_o` | Output | `LVCMOS33` | active high or recorded in evidence | `heartbeat_led_o_pin` | Visible clock/reset/retire heartbeat output. |

## Evidence Format

Use the template printed by:

```text
python tools\fpga_constraints_overlay.py --evidence-template
```

The record must include:

```text
story=I24-S02
identity_evidence=docs/implementation/evidence/i24_s01_device_identity.txt
source_constraints=
verified_by=
verified_at=
led_polarity=
board_clk_i_pin=
board_reset_n_i_pin=
pass_led_o_pin=
fail_led_o_pin=
heartbeat_led_o_pin=
board_clk_i_clock_period_ns=40.000
```

`source_constraints` must identify the Sipeed All PIN Constraints source used
for the confirmed device/package. If I24-S01 observes an `FPG676A` board, this
story remains blocked until the target profile and synthesis gate are updated.

## CST Template

The CST template deliberately contains placeholder tokens such as
`I24_S02_PIN_BOARD_CLK_I`. A real `constraints/tang_mega_138k_first_test.cst`
may only be created after the evidence audit reports `confirmed`.

Required CST shape:

```text
IO_LOC "board_clk_i" I24_S02_PIN_BOARD_CLK_I;
IO_PORT "board_clk_i" IO_TYPE=LVCMOS33;
```

The same `IO_LOC` and `IO_PORT` pattern is required for `board_reset_n_i`,
`pass_led_o`, `fail_led_o`, and `heartbeat_led_o`.

## SDC Timing

The SDC file is active because the clock name is already known:

```text
create_clock -name board_clk_i -period 40.000 [get_ports {board_clk_i}]
set_false_path -from [get_ports {board_reset_n_i}]
```

This gives I24-S03 a concrete timing file while keeping the pin-specific CST
blocked until board evidence exists.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `confirmed` | I24-S01 identity evidence is confirmed and every required pin/evidence field is present. | Create the final CST from the template, run I24-S03 Gowin build, and archive the evidence. |
| `invalid` | Pin evidence is malformed, missing required fields, missing pins, or has a non-`40.000` ns clock period. | Fix the evidence record and rerun the audit. |
| `blocked` | I24-S01 identity evidence is absent/unconfirmed or no I24-S02 pin evidence exists. | Keep the final CST absent and do not run the Gowin board build. |

## Current Blocker

- I24-S01 identity evidence is not physically captured in this repository.
- Sipeed All PIN Constraints source for the exact SOM/package has not been
  captured.
- Verified pins for `board_clk_i`, `board_reset_n_i`, `pass_led_o`,
  `fail_led_o`, and `heartbeat_led_o` are not yet recorded.
- I24-S03 must not run as a real board build until the CST placeholder tokens
  are replaced from verified board data.

I24-S03 is tracked in `docs/implementation/fpga-gowin-build.md` and checked
with `python tools\fpga_gowin_build.py --check`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Required clock, reset, and LED constraints are defined. | Met by the overlay profile, CST template, and evidence fields. |
| IO standard and polarity are explicit. | Met by required `LVCMOS33` and `led_polarity` evidence. |
| Clock timing is constrained. | Met by `constraints/tang_mega_138k_first_test.sdc` using `40.000` ns. |
| Physical pin assumptions are not silently guessed. | Met by the blocked audit until identity and pin evidence are captured. |
| I24-S03 has a clear handoff. | Met by the final CST path, SDC path, and confirmed-audit action list. |

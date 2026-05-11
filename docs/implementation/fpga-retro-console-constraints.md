# FPGA Retro Console Constraints

Story: I34-S02

Status: CST and SDC templates implemented; final Retro Console constraints
blocked until I34-S01 identity evidence and pin evidence are captured.

Structured gate:

```text
python tools\fpga_retro_console_constraints.py --check
```

CST template:

```text
python tools\fpga_retro_console_constraints.py --template
```

SDC template:

```text
python tools\fpga_retro_console_constraints.py --sdc-template
```

Evidence audit:

```text
python tools\fpga_retro_console_constraints.py --audit-evidence docs\implementation\evidence\i34_s02_retro_console_pins.txt
```

## Purpose

I34-S02 creates the Retro Console first-test constraint overlay boundary for
`cpu_v01_fpga_top`. The overlay defines the required CPU smoke-test signals,
required evidence fields, CST placeholder tokens, and SDC timing template. It
is deliberately not Tang Mega 138K Dock-derived: use Retro Console board
marking, schematic, programmer scan, pin spreadsheet, or vendor constraints,
not Tang Mega 138K Dock pin names.

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang 138K Retro Console` |
| Identity gate | `python tools\fpga_retro_console_identity.py --check` |
| Final CST path | `constraints/tang_138k_retro_console_first_test.cst` |
| CST template | `constraints/tang_138k_retro_console_first_test.cst.template` |
| Final SDC path | `constraints/tang_138k_retro_console_first_test.sdc` |
| SDC template | `constraints/tang_138k_retro_console_first_test.sdc.template` |
| Evidence path | `docs/implementation/evidence/i34_s02_retro_console_pins.txt` |

## Required Signals

| Signal | Direction | Evidence key | IO standard | Purpose |
| --- | --- | --- | --- | --- |
| `board_clk_i` | Input | `board_clk_i_pin` | `LVCMOS33_or_recorded` | Verified Retro Console clock input. |
| `board_reset_n_i` | Input | `board_reset_n_i_pin` | `LVCMOS33_or_recorded` | Verified reset or user input. |
| `pass_led_o` | Output | `pass_led_o_pin` | `LVCMOS33_or_recorded` | Visible first-test pass output. |
| `fail_led_o` | Output | `fail_led_o_pin` | `LVCMOS33_or_recorded` | Visible first-test fail output. |
| `heartbeat_led_o` | Output | `heartbeat_led_o_pin` | `LVCMOS33_or_recorded` | Visible clock/reset/retire heartbeat output. |
| `uart_tx_o` | Output | `uart_tx_o_pin` | `LVCMOS33_or_recorded` | UART status packet stream. |

## Evidence Format

Use the template printed by:

```text
python tools\fpga_retro_console_constraints.py --evidence-template
```

The record must include:

```text
story=I34-S02
identity_evidence=docs/implementation/evidence/i34_s01_retro_console_identity.txt
source_constraints=
verified_by=
verified_at=
io_voltage=
led_polarity=
uart_debug_mode=
pin_conflicts=
board_clk_i_pin=
board_reset_n_i_pin=
pass_led_o_pin=
fail_led_o_pin=
heartbeat_led_o_pin=
uart_tx_o_pin=
board_clk_i_clock_period_ns=
```

`pin_conflicts` must name board functions that share the selected pins, or
`none`. `board_clk_i_clock_period_ns` must be derived from the verified Retro
Console clock source captured in I34-S01.

## Templates

The CST template contains placeholder tokens such as:

```text
IO_LOC "board_clk_i" I34_S02_PIN_BOARD_CLK_I;
IO_PORT "board_clk_i" IO_TYPE=LVCMOS33_or_recorded;
```

The SDC template keeps the clock period as a placeholder until evidence is
captured:

```text
create_clock -name board_clk_i -period I34_S02_BOARD_CLK_PERIOD_NS [get_ports {board_clk_i}]
set_false_path -from [get_ports {board_reset_n_i}]
```

Final `constraints/tang_138k_retro_console_first_test.cst` and
`constraints/tang_138k_retro_console_first_test.sdc` files may only be created
after the evidence audit reports `confirmed`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `confirmed` | I34-S01 identity is selected and every required pin/evidence field is present. | Create final CST/SDC files and run I34-S03. |
| `invalid` | Pin evidence is malformed, incomplete, missing pins, or has a bad clock period. | Fix the evidence record and rerun the audit. |
| `blocked` | I34-S01 identity evidence is absent/unselected or no I34-S02 pin evidence exists. | Keep final constraints absent and do not run Gowin for the Retro Console. |

## Current Blocker

- I34-S01 identity evidence is not physically captured in this repository.
- Retro Console source constraints and selected pin conflicts are not captured.
- Final pin assignments for `board_clk_i`, `board_reset_n_i`, `pass_led_o`,
  `fail_led_o`, `heartbeat_led_o`, and `uart_tx_o` are not recorded.
- I34-S03 must not run as a real board build until placeholder tokens are
  replaced from verified Retro Console data.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Clock, reset, pass/fail/heartbeat, and UART/debug pins are represented. | Met by required signal and evidence fields. |
| IO standard, LED polarity, and pin conflicts are explicit. | Met by `io_voltage`, `led_polarity`, and `pin_conflicts`. |
| Clock timing is represented without guessing the period. | Met by `I34_S02_BOARD_CLK_PERIOD_NS` in the SDC template. |
| Dock pins are not assumed. | Met by the blocked audit and explicit Retro Console source-evidence requirement. |
| I34-S03 has a clear handoff. | Met by final CST/SDC paths and confirmed-audit action list. |

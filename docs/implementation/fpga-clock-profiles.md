# FPGA Clock Profiles

Story: I28-S01

Structured gate:

```text
python tools\fpga_clock_profiles.py --check
```

Render SDC fragments:

```text
python tools\fpga_clock_profiles.py --sdc debug_direct_25mhz
python tools\fpga_clock_profiles.py --sdc release_pll_25mhz
```

Related gates:

```text
python tools\fpga_constraints_overlay.py --check
python tools\fpga_gowin_build.py --check
```

## Scope

I28-S01 fixes the FPGA clock profile vocabulary before the reset/CDC and
timing-report stories harden the board build. The current FPGA top remains on
the direct 25 MHz `board_clk_i` path, matching the I24-S02 SDC, I23-S05 Gowin
target, I25-S02 UART status streamer, and I27-S02 UART MMIO divisor.

The release profile is defined but not selectable yet. It names a planned
Gowin rPLL 1:1 global-clock path and its generated-clock SDC, but the profile
stays blocked until a checked PLL wrapper exists and Gowin timing reports prove
nonnegative slack.

## Profiles

| Profile | Role | Source | PLL setting | Generated clocks | Status |
| --- | --- | --- | --- | --- | --- |
| `debug_direct_25mhz` | debug and first board bring-up | `board_clk_i`, 25 MHz, 40.000 ns | direct, no PLL | `core_clk`, `uart_status_clk`, `timer_gpio_clk` all at 25 MHz | Current default. |
| `release_pll_25mhz` | conservative release default | `board_clk_i`, 25 MHz, 40.000 ns | Gowin rPLL logical 1:1, 0 degree phase, 50 percent duty | `cpu_clk` and `uart_timer_gpio_clk` at 25 MHz | Blocked until PLL wrapper and timing evidence exist. |

The release frequency deliberately stays at 25 MHz. I28-S04 owns any increase
after I28-S03 can parse Gowin timing reports and a frequency sweep records the
maximum passing board build.

## SDC Policy

The active first-test SDC remains:

```text
create_clock -name board_clk_i -period 40.000 [get_ports {board_clk_i}]
set_false_path -from [get_ports {board_reset_n_i}]
```

The release profile adds this generated-clock template only after RTL contains
the matching PLL instance:

```text
create_generated_clock -name cpu_clk -source [get_ports {board_clk_i}] -divide_by 1 [get_pins {u_clock_pll/clkout}]
```

Do not copy the generated-clock line into
`constraints/tang_mega_138k_first_test.sdc` until the wrapper actually exposes
`u_clock_pll/clkout`.

## Timing Margin Policy

| Profile | Minimum slack | Target slack | Gate |
| --- | --- | --- | --- |
| `debug_direct_25mhz` | 0.000 ns | 1.000 ns | `python tools\fpga_gowin_build.py --check` |
| `release_pll_25mhz` | 0.000 ns | 1.500 ns | `python tools\fpga_gowin_build.py --audit-reports build\fpga\tang_mega_138k\first_test` |

The minimum slack is the hard pass/fail boundary. Target slack is the desired
margin for repeatable bring-up and release builds; missing target slack should
be recorded as timing risk even when the build is still nonnegative.

## Current Blockers

- I24-S01 identity evidence and I24-S02 pin evidence are still blocked.
- `cpu_v01_fpga_top` currently clocks the core directly from `board_clk_i`.
- The release PLL wrapper and generated-clock SDC must be added before
  selecting `release_pll_25mhz`.
- I28-S03 and I28-S04 must audit real Gowin timing reports before raising the
  default frequency.

## Handoffs

- I28-S02 should audit reset release, async board inputs, and any PLL lock or
  generated-clock crossings before release profile selection.
- I28-S03 should parse timing reports using the profile id, source clock,
  generated clock, and slack policy defined here.
- I28-S04 should record the maximum passing frequency and decide whether a
  higher release profile can replace the conservative 25 MHz default.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Debug and release profiles name source clocks. | Met by both profiles using `board_clk_i`. |
| PLL settings are explicit. | Met by direct/no-PLL debug and Gowin rPLL 1:1 release settings. |
| Generated clocks are named. | Met by the profile generated-clock tables. |
| SDC constraints are defined. | Met by the active debug SDC and blocked release generated-clock template. |
| Expected timing margins are recorded. | Met by the minimum slack and target slack policy. |

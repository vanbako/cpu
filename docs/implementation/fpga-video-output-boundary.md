# FPGA Video Output Boundary

Story: I35-S03

Status: pixel-domain output boundary implemented for 720p scanout

## Command

Validate the output-boundary profile:

```text
python tools\fpga_video_output.py --check
```

Print machine-readable profile data and handoff snippets:

```text
python tools\fpga_video_output.py --json
python tools\fpga_video_output.py --signals
python tools\fpga_video_output.py --sdc
python tools\fpga_video_output.py --plan
```

## Scope

I35-S03 connects the I35-S02 1280x720 timing generator to a board-facing output
boundary. The story keeps the implementation board-neutral: it exposes
registered RGB, sync, data-enable, pixel-clock, and output-enable signals, but
does not claim a final CST pinout, HDMI/TMDS encoding, or vendor PLL instance.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_video_output.py` | Executable output-boundary profile, CDC rules, SDC handoff, RTL command inventory, and validator. |
| `tools/fpga_video_output.py` | CLI for `--check`, `--json`, `--signals`, `--sdc`, and `--plan`. |
| `rtl/cpu_v01_fpga_video_output_boundary.sv` | Pixel-domain scanout boundary around `cpu_v01_fpga_video_timing`. |
| `rtl/cpu_v01_fpga_video_output_boundary_tb.sv` | Standalone self-checking testbench for reset blanking, enable blanking, hsync forwarding, and pixel-clock exposure. |
| `tests/conformance/test_i35_s03_fpga_video_output.py` | Story conformance tests for model, docs, CLI, and RTL tokens. |

## Clock And Reset

The output boundary uses the 74.25 MHz pixel domain required by the 720p mode.
For board integration, the expected generated-clock constraint template is:

```text
create_generated_clock -name video_pixel_clk -source [get_ports {board_clk_i}] -multiply_by 297 -divide_by 100 [get_pins {u_video_pll/clkout}]
```

The current RTL takes `pixel_clk_i` from a future board PLL wrapper and exposes
it as `video_pixel_clk_o` for board-adapter handoff. `pixel_reset_n_i` asserts
asynchronously and releases through `pixel_reset_sync_q`, with
`RESET_SYNC_STAGES = 2`.

## CDC Rules

| Crossing | Handling |
| --- | --- |
| `pixel_reset_release` | Asynchronous assertion, two-stage synchronized release in `video_pixel_clk`. |
| `scanout_enable_sync` | Single-bit scanout enable crosses through `scanout_enable_sync_q`. |
| `output_enable_sync` | Single-bit output blanking control crosses through `output_enable_sync_q`. |
| `registered_board_outputs` | `video_rgb_o`, `video_hsync_o`, `video_vsync_o`, and `video_de_o` register in the pixel domain before leaving the boundary. |
| `stable_pattern_config_boundary` | Multi-bit `pattern_select_i` and `bg_color_i` must be held stable while scanout is disabled until I35-S04 adds the MMIO update latch. |

## Board Outputs

| Signal | Role |
| --- | --- |
| `video_rgb_o` | Registered 24-bit RGB output. |
| `video_hsync_o` | Registered active-high horizontal sync. |
| `video_vsync_o` | Registered active-high vertical sync. |
| `video_de_o` | Registered active-video data enable. |
| `video_pixel_clk_o` | Forwarded pixel clock for the board adapter. |
| `video_output_enable_o` | Synchronized output-enable status for output buffers or debug probing. |

When `output_enable_async_i` is low, RGB and data-enable are forced blank while
hsync, vsync, vblank, and frame counting continue in the pixel domain. This
lets board bring-up observe timing without driving visible pixels.

## Verilator

The lint/elaboration command inventory is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_video_output_boundary_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_video_timing.sv rtl/cpu_v01_fpga_video_output_boundary.sv rtl/cpu_v01_fpga_video_output_boundary_tb.sv
```

The testbench checks reset blanking, active RGB forwarding, hsync forwarding,
pixel-clock exposure, and output-enable blanking.

## Handoffs

- I35-S04 owns firmware-visible MMIO latching for multi-bit configuration,
  status bits, and vblank interrupt behavior.
- I35-S06 owns board-output adapter wiring and visible/probe evidence.
- I28-S03 must treat unconstrained `video_pixel_clk` paths as timing-report
  failures when this boundary is included in a board build.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Pixel-clock/reset sequencing is documented and linted. | Met by `pixel_reset_sync_q`, the generated-clock SDC template, and the Verilator command inventory. |
| Single-bit CDC controls are synchronized before use in scanout. | Met by `scanout_enable_sync_q` and `output_enable_sync_q`. |
| Board-facing RGB, sync, and data-enable outputs are registered. | Met by `cpu_v01_fpga_video_output_boundary`. |
| Board pin and physical-display evidence are deferred. | Met by explicit I35-S06 and I28-S03 handoffs. |

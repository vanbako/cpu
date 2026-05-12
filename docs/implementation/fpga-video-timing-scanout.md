# FPGA Video Timing Scanout

Story: I35-S02

Status: 720p timing generator and test-pattern scanout implemented

## Command

Validate the timing profile:

```text
python tools\fpga_video_timing.py --check
```

Print the profile and one-frame summary:

```text
python tools\fpga_video_timing.py --json
python tools\fpga_video_timing.py --frame-summary
```

Print the Verilator lint command:

```text
python tools\fpga_video_timing.py --plan
```

## Scope

I35-S02 implements the board-neutral 1280x720 scanout timing slice from the
I35-S01 display profile. It adds a pixel-domain timing generator, visible
coordinates, active-high syncs, data-enable, vblank, frame/line pulses, frame
counter, and deterministic test patterns. No framebuffer fetch or plane
composition happens in this story.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_video_timing.py` | Executable 720p timing model, one-frame summary, RTL command inventory, and validator. |
| `tools/fpga_video_timing.py` | CLI for `--check`, `--json`, `--frame-summary`, and `--plan`. |
| `rtl/cpu_v01_fpga_video_timing.sv` | Pixel-domain 720p timing and test-pattern RTL. |
| `rtl/cpu_v01_fpga_video_timing_tb.sv` | Standalone self-checking testbench for one frame and pattern outputs. |
| `tests/conformance/test_i35_s02_fpga_video_timing.py` | Story conformance tests for model, docs, CLI, and RTL tokens. |

## Timing

The scanout mode remains the I35-S01 720p target:

| Field | Value |
| --- | ---: |
| Active | 1280x720 |
| Total | 1650x750 |
| Pixel clock | 74.25 MHz |
| Horizontal sync pixels | 40 |
| Vertical sync lines | 5 |
| Active pixels/frame | 921600 |
| Total pixels/frame | 1237500 |

The Python model and RTL both count from `(0, 0)` through the total frame.
`de_o` is asserted only inside the active region. `hsync_o` and `vsync_o` are
active high in the porch-defined sync intervals. `vblank_o` is asserted for all
non-active vertical lines.

## Outputs

| Signal | Meaning |
| --- | --- |
| `pixel_x_o`, `pixel_y_o` | Active-region coordinates, zero outside active video. |
| `hsync_o`, `vsync_o` | Active-high sync outputs. |
| `de_o` | Active-video data-enable. |
| `vblank_o` | Vertical blanking interval. |
| `frame_start_o` | One-cycle pulse when the frame wraps. |
| `line_start_o` | One-cycle pulse when the line wraps. |
| `rgb_o` | 24-bit RGB test-pattern output. |
| `frame_count_o` | Completed-frame counter. |

## Patterns

| Pattern | Selector | Meaning |
| --- | ---: | --- |
| `background` | 0 | Emits `bg_color_i` inside active video. |
| `color_bars` | 1 | Eight deterministic color bars across the active width. |
| `checkerboard` | 2 | 32x32 pixel black/white checkerboard. |

The first active `color_bars` pixel is red. The checkerboard toggles at x=32
for y=0, which gives a simple simulation-visible check before board scanout.

## Verilator

The lint/elaboration command inventory is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_video_timing_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_video_timing.sv rtl/cpu_v01_fpga_video_timing_tb.sv
```

The testbench checks active-pixel, hsync, vsync, and vblank counts across one
full frame, verifies frame wrap, and checks color-bar, checkerboard, and
background pattern output.

## Handoffs

- I35-S03 owns pixel clock/reset/CDC and board-output pin or adapter handling.
- I35-S04 maps scanout status into MMIO and vblank interrupt routing.
- I36-S02 consumes the coordinates and active-video timing for framebuffer
  fetch and line buffering.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| 1280x720 counters generate stable hsync, vsync, data-enable, frame, line, and pixel coordinates. | Met by the Python model and RTL/testbench contract. |
| Deterministic test pattern emits without CPU framebuffer traffic. | Met by background, color bars, and checkerboard modes. |
| No framebuffer or plane-composition behavior is introduced. | Met by explicit non-goals and no read-master use. |
| Verilator-visible command inventory exists. | Met by `python tools\fpga_video_timing.py --plan`. |

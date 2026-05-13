# FPGA Video Scanout Gate

Story: I35-S05

Status: 720p scanout simulation and report gate implemented

## Command

Validate the gate:

```text
python tools\fpga_video_scanout_gate.py --check
```

Print structured profile data and the executable one-frame summary:

```text
python tools\fpga_video_scanout_gate.py --json
python tools\fpga_video_scanout_gate.py --summary
python tools\fpga_video_scanout_gate.py --plan
```

Audit generated Gowin reports:

```text
python tools\fpga_video_scanout_gate.py --audit-reports build\fpga\tang_mega_138k\first_test
```

Required prerequisite gates:

```text
python tools\fpga_video_timing.py --check
python tools\fpga_video_output.py --check
python tools\fpga_video_mmio.py --check
python tools\fpga_gowin_reports.py --check
```

## Scope

I35-S05 is an evidence gate for the I35 video foundation. It does not claim
board-visible output or final CST pin wiring. It proves that the existing
1280x720 timing model, output boundary, video MMIO block, and vblank IRQ
contract can be checked together before I35-S06 attempts physical scanout.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_video_scanout_gate.py` | Executable gate profile, one-frame summary, Gowin report audit wrapper, and validator. |
| `tools/fpga_video_scanout_gate.py` | CLI for `--check`, `--json`, `--summary`, `--plan`, and `--audit-reports`. |
| `rtl/cpu_v01_fpga_video_scanout_gate_tb.sv` | Combined self-checking testbench for MMIO-programmed scanout, vblank IRQ, frame-count readback, and underflow status. |
| `tests/conformance/test_i35_s05_fpga_video_scanout_gate.py` | Story conformance tests for model, docs, CLI, RTL tokens, and report-audit fixtures. |

## Simulation Gate

The exact one-frame timing remains the I35-S02 720p mode:

| Field | Value |
| --- | ---: |
| Active video | 1280x720 |
| Total timing | 1650x750 |
| Pixel clock | 74.25 MHz |
| Active pixels | 921600 |
| Hsync pixels | 30000 |
| Vsync pixels | 8250 |
| Vblank pixels | 49500 |
| Vblank start cycle | 1188000 |
| Full frame cycles | 1237500 |

`cpu_v01_fpga_video_scanout_gate_tb` instantiates
`cpu_v01_fpga_video_output_boundary` and `cpu_v01_fpga_video_mmio` together.
The testbench programs `VIDEO_CONTROL`, `VIDEO_TEST_PATTERN`,
`VIDEO_BG_COLOR`, and `VIDEO_IRQ_ENABLE`, waits for scanout to reach vblank,
checks that the vblank IRQ is raised, acknowledges it, waits for frame-count
advance, reads `VIDEO_FRAME_COUNT`, and confirms `VIDEO_UNDERFLOW_COUNT`
remains zero.

The focused Verilator lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_video_scanout_gate_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_video_timing.sv rtl/cpu_v01_fpga_video_output_boundary.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_video_scanout_gate_tb.sv
```

## Report Gate

The report audit reuses the I28-S03 parser and adds video-specific checks:

| Field | Required result |
| --- | --- |
| `video_pixel_clk` | Clock summary exists and reports 74.25 MHz within tolerance. |
| Worst slack | Parsed by the Gowin report parser and nonnegative under the selected profile. |
| Utilization | At least the I28-S03 `LUT` and `Register` metrics are present. |
| Unconstrained paths | Must be zero. |
| Warnings | CDC, clock-domain, asynchronous-path, unsynchronized, and metastability warnings fail as `unexpected_video_cdc_warning`. |
| Bitstream identity | Path, size, and SHA-256 are preserved by I28-S03 for handoff evidence. |

The current default report audit is blocked until a real Gowin report bundle and
bitstream exist under `build/fpga/tang_mega_138k/first_test`. Fixture report
bundles exercise pass and failure behavior in conformance tests.

## Handoffs

- I35-S06 consumes this gate before claiming visible display or probe evidence.
- I36-S04 consumes the vblank IRQ behavior for atomic plane descriptor updates.
- I28-S03 remains the underlying timing, utilization, unconstrained-path,
  warning, and bitstream identity parser.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Focused tests or validators check exact 720p frame timing. | Met by `simulate_video_scanout_gate_summary`, the I35-S02 timing summary, and the timing RTL testbench. |
| MMIO behavior is checked with scanout enabled. | Met by `cpu_v01_fpga_video_scanout_gate_tb` programming video control, pattern, and background registers. |
| Vblank IRQ behavior is checked. | Met by the combined testbench and executable Python summary. |
| Unexpected CDC warnings are rejected. | Met by the report audit policy marker `unexpected_video_cdc_warning`. |
| Gowin/Verilator report fields cover clock, utilization, and unconstrained paths. | Met by the Verilator command inventory and Gowin report audit fields. |

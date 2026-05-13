# FPGA Compositor Single-Plane Fetch

Story: I36-S02

Status: single-plane framebuffer fetch and line-buffer fixture implemented

## Command

Validate the fetch profile:

```text
python tools\fpga_compositor_fetch.py --check
```

Print structured data, read-master signals, demos, or Verilator plan:

```text
python tools\fpga_compositor_fetch.py --json
python tools\fpga_compositor_fetch.py --signals
python tools\fpga_compositor_fetch.py --demo
python tools\fpga_compositor_fetch.py --underflow-demo
python tools\fpga_compositor_fetch.py --plan
```

Required prerequisite gates:

```text
python tools\fpga_compositor_framebuffer.py --check
python tools\fpga_video_timing.py --check
python tools\fpga_ddr_wrapper.py --check
```

## Scope

I36-S02 adds the first scanout read-master and single-plane line-buffer RTL. It
consumes the I36-S01 framebuffer memory policy, the I35-S02 timing coordinates,
and the I29-S02 DDR-wrapper readiness gate. The implementation is intentionally
board-neutral and fixture-oriented: BRAM or an abstract external-memory adapter
returns one payload cell per visible fixture pixel, while `plane_stride_cells_i`
selects the source line.

The shared CPU/compositor data-memory arbiter remains an I36-S08 handoff. This
story does not route CPU data/MMIO traffic through the fetch block and does not
claim DDR bandwidth closure.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_compositor_fetch.py` | Executable single-plane fetch model, RGB conversion helpers, profile, command inventory, and validator. |
| `tools/fpga_compositor_fetch.py` | CLI for `--check`, `--json`, `--signals`, `--demo`, `--underflow-demo`, and `--plan`. |
| `rtl/cpu_v01_fpga_single_plane_fetch.sv` | Read-master and line-buffer RTL for one visible plane. |
| `rtl/cpu_v01_fpga_single_plane_fetch_tb.sv` | Self-checking fixture for request addresses, RGB565, XRGB8888, and underflow. |
| `tests/conformance/test_i36_s02_fpga_compositor_fetch.py` | Story conformance tests for model, docs, CLI, RTL tokens, and Verilator lint. |

## Read Master

The fetch block uses only the video scanout read-master boundary:

| Signal | Direction | Role |
| --- | --- | --- |
| `video_rd_req_valid_o` | fetch to memory | A one-cell pixel fetch request is valid. |
| `video_rd_req_ready_i` | memory to fetch | Adapter accepted the request. |
| `video_rd_req_addr_o` | fetch to memory | Cell address for `base + y * stride + x`. |
| `video_rd_req_len_cells_o` | fetch to memory | Always `1` for the first fixture profile. |
| `video_rd_rsp_valid_i` | memory to fetch | Response cell is valid. |
| `video_rd_rsp_ready_o` | fetch to memory | Line buffer can accept a response. |
| `video_rd_rsp_data_i` | memory to fetch | Payload cell containing one fixture pixel. |
| `video_rd_rsp_error_i` | memory to fetch | Adapter reported missing data or an access error. |

There is no CPU request port in `cpu_v01_fpga_single_plane_fetch`; CPU writes
populate payload memory through existing data paths. Arbitration between CPU
data/MMIO traffic and compositor scanout reads is owned by I36-S08.

## Line Buffer And Formats

The first RTL fixture stores fetched pixels in `line_rgb_q` with validity bits
in `line_valid_q`. The policy retains the I36-S01 two-line target and 1280-pixel
line-buffer sizing, while the standalone testbench instantiates an 8-pixel
fixture.

Supported first formats:

| Format | Selector | Conversion |
| --- | ---: | --- |
| `rgb565` | `0` | `rgb565_to_rgb888` expands 5:6:5 into 8-bit RGB. |
| `xrgb8888` | `1` | `xrgb8888_to_rgb888` ignores the X byte and emits RGB. |

If a pixel is requested before its line-buffer valid bit is set, or a response
arrives with `video_rd_rsp_error_i`, the block emits background RGB and pulses
`underflow_pulse_o`. I35-S04 exposes accumulated underflows through
`VIDEO_UNDERFLOW_COUNT`.

## Verilator

The focused lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_single_plane_fetch_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_single_plane_fetch.sv rtl/cpu_v01_fpga_single_plane_fetch_tb.sv
```

The testbench checks stride-relative request addresses, RGB565 red/green/blue
and white conversion, XRGB8888 conversion, missing-data underflow, and response
error underflow.

## Handoffs

- I36-S03 layers multi-plane composition on top of the single-plane RGB output.
- I36-S06 archives timing, bandwidth, resource, and underflow evidence.
- I36-S08 arbitrates CPU data/MMIO traffic against compositor scanout reads.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A scanout read master fetches one visible plane. | Met by `cpu_v01_fpga_single_plane_fetch` request/response signals and stride-relative addresses. |
| BRAM fixture or abstract memory adapter can feed the block. | Met by the one-cell fixture protocol and self-checking testbench. |
| Stride and format conversion are handled. | Met by `plane_stride_cells_i`, `rgb565`, and `xrgb8888` conversion. |
| Underflow is deterministic. | Met by `underflow_pulse_o` on missing valid pixels or response errors. |
| CPU data/MMIO traffic remains separated. | Met by the absence of CPU request ports and the I36-S08 arbitration handoff. |

# FPGA Compositor Pipeline

Story: I36-S03

Status: two-plane compositor pipeline fixture implemented

## Command

Validate the compositor pipeline profile:

```text
python tools\fpga_compositor_pipeline.py --check
```

Print structured data, rule list, demo pixels, or the Verilator plan:

```text
python tools\fpga_compositor_pipeline.py --json
python tools\fpga_compositor_pipeline.py --rules
python tools\fpga_compositor_pipeline.py --demo
python tools\fpga_compositor_pipeline.py --plan
```

Required prerequisite gate:

```text
python tools\fpga_compositor_fetch.py --check
```

## Scope

I36-S03 adds the first multi-plane composition stage on top of the I36-S02
single-plane fetch output. The implementation supports two planes with
enable, position, size, z-order, global alpha, color-key transparency, and
background color. It clips pixels outside each plane rectangle and exposes
`plane0_sample_o` and `plane1_sample_o` so fixture tests can prove the
compositor does not sample outside configured framebuffer bounds.

This story does not add shadow descriptor registers, firmware programming, or
CPU/compositor memory arbitration. I36-S04 owns vblank-atomic descriptor
latching, I36-S05 owns firmware/monitor demos, and I36-S08 owns shared memory
arbitration.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_compositor_pipeline.py` | Executable composition model, alpha/key helpers, profile, command inventory, and validator. |
| `tools/fpga_compositor_pipeline.py` | CLI for `--check`, `--json`, `--rules`, `--demo`, and `--plan`. |
| `rtl/cpu_v01_fpga_compositor_pipeline.sv` | Two-plane compositor RTL. |
| `rtl/cpu_v01_fpga_compositor_pipeline_tb.sv` | Self-checking testbench for z-order, global alpha, color-key, and clipping. |
| `tests/conformance/test_i36_s03_fpga_compositor_pipeline.py` | Story conformance tests for model, docs, CLI, RTL tokens, and Verilator lint. |

## Composition Rules

| Rule | Behavior |
| --- | --- |
| Enable | Disabled or invalid planes are ignored. |
| Clipping | Pixels outside plane `x/y/width/height` are clipped and not sampled. |
| Z-order | Higher `z` wins when two visible planes cover a pixel. |
| Global alpha | `alpha=255` is opaque; `alpha=0` is transparent; intermediate alpha blends over the current lower layer. |
| Color-key | A color-key hit is transparent and reveals the lower layer. |
| Background | Background RGB is emitted when no plane contributes a visible pixel. |

## RTL Interface

The fixture compositor consumes already-fetched RGB for two planes and the
current scanout coordinate. The key observable outputs are:

| Signal | Role |
| --- | --- |
| `rgb_o` | Composited RGB output. |
| `de_o` | Registered data-enable. |
| `selected_plane_o` | `0` background, `1` plane 0, `2` plane 1. |
| `plane0_sample_o` | Plane 0 was inside its configured rectangle for this pixel. |
| `plane1_sample_o` | Plane 1 was inside its configured rectangle for this pixel. |

`plane0_sample_o` and `plane1_sample_o` are the fixture guard for no read
outside configured bounds. Fetch scheduling still belongs to I36-S02 and
shared CPU/compositor arbitration remains with I36-S08.

## Verilator

The focused lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_pipeline_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_pipeline.sv rtl/cpu_v01_fpga_compositor_pipeline_tb.sv
```

The testbench checks plane 0 selection, plane 1 alpha blending over plane 0,
color-key transparency, and clipped pixels leaving both `plane*_sample_o`
signals low.

## Handoffs

- I36-S04 latches plane descriptors atomically at vblank.
- I36-S05 adds firmware and monitor demos for programming planes.
- I36-S08 arbitrates CPU data/MMIO traffic against compositor scanout reads.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| At least two planes compose by enable, position, size, and z-order. | Met by `cpu_v01_fpga_compositor_pipeline` and model demos. |
| Global alpha or color-key behavior is implemented. | Met by global alpha blending and color-key transparency. |
| Background color is used when no plane contributes. | Met by `background_rgb_i`. |
| Clipping is deterministic. | Met by rectangle checks and `plane*_sample_o` outputs. |
| No read outside configured framebuffer bounds is observable. | Met by sample outputs staying low for clipped planes. |

# FPGA Compositor Vblank Descriptors

Story: I36-S04

Status: vblank-atomic descriptor latch fixture implemented

## Command

Validate the descriptor latch profile:

```text
python tools\fpga_compositor_vblank.py --check
```

Print structured data, descriptor fields, demo states, or Verilator plan:

```text
python tools\fpga_compositor_vblank.py --json
python tools\fpga_compositor_vblank.py --fields
python tools\fpga_compositor_vblank.py --demo
python tools\fpga_compositor_vblank.py --plan
```

Required prerequisite gates:

```text
python tools\fpga_compositor_pipeline.py --check
python tools\fpga_video_mmio.py --check
```

## Scope

I36-S04 adds a shadow-to-active descriptor latch for the first two compositor
planes. Firmware or monitor code can write shadow descriptor fields at any time,
but the active descriptor consumed by fetch/composition updates only on a
vblank rising edge. This prevents mid-frame tearing from CPU writes to plane
configuration.

This story does not add the final firmware-visible plane MMIO register map.
I36-S05 owns firmware and monitor demos that program descriptors, and I36-S08
owns shared CPU/compositor memory arbitration.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_compositor_vblank.py` | Executable descriptor latch model, profile, command inventory, and validator. |
| `tools/fpga_compositor_vblank.py` | CLI for `--check`, `--json`, `--fields`, `--demo`, and `--plan`. |
| `rtl/cpu_v01_fpga_compositor_descriptor_latch.sv` | Two-plane shadow/active descriptor latch RTL. |
| `rtl/cpu_v01_fpga_compositor_descriptor_latch_tb.sv` | Self-checking testbench for pending status and vblank application. |
| `tests/conformance/test_i36_s04_fpga_compositor_vblank.py` | Story conformance tests for model, docs, CLI, RTL tokens, and Verilator lint. |

## Descriptor Fields

| Field | Packed value |
| --- | --- |
| `control` | Bit 0 enable, bit 1 color-key enable. |
| `base_cell` | 48-bit framebuffer base cell. |
| `stride_cells` | 16-bit stride in cells. |
| `position_xy` | X in bits 11:0, Y in bits 27:16. |
| `size_wh` | Width in bits 11:0, height in bits 27:16. |
| `format_z_alpha` | Format in bits 3:0, z in bits 11:8, alpha in bits 23:16. |
| `color_key_rgb` | RGB color key in bits 23:0. |

The RTL exposes active descriptor outputs for both planes. Shadow descriptor
writes set `descriptor_pending`. A vblank rising edge copies every shadow field
into the active descriptor bank, clears pending, pulses
`descriptor_applied_pulse`, and increments `applied_count`.

## Tearing Policy

Mid-frame writes are allowed only into shadow descriptors. The active descriptor
bank remains unchanged until `vblank_i` rises. A pending descriptor update can
therefore be observed before vblank, while scanout continues with the previous
active descriptor. The I35-S04 `video_vblank` behavior is the timing source for
this latch.

## Verilator

The focused lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_descriptor_latch_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_descriptor_latch.sv rtl/cpu_v01_fpga_compositor_descriptor_latch_tb.sv
```

The testbench writes plane 0 shadow fields, confirms active fields do not
change before vblank, checks `descriptor_pending`, applies on vblank, and
verifies active base, position, size, format, z, alpha, color-key state, and
`applied_count`.

## Handoffs

- I36-S05 firmware and monitor demos program the shadow descriptor fields.
- I36-S06 archives descriptor pending/applied and underflow evidence.
- I36-S08 arbitrates memory once CPU writes and scanout reads overlap.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Shadow registers latch plane base, stride, format, position, size, alpha/key, and enable. | Met by the descriptor field map and RTL shadow fields. |
| Active descriptors update atomically at vblank. | Met by vblank rising-edge copy into active fields. |
| Pending/applied status is visible. | Met by `descriptor_pending`, `descriptor_applied_pulse`, and `applied_count`. |
| Mid-frame tearing from CPU writes is prevented. | Met by active fields remaining unchanged until vblank. |

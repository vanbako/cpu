# FPGA Compositor Framebuffer Policy

Story: I36-S01

Status: Framebuffer memory and pixel-format policy implemented

## Command

Validate the policy:

```text
python tools\fpga_compositor_framebuffer.py --check
```

Print the structured policy:

```text
python tools\fpga_compositor_framebuffer.py --json
```

List formats or framebuffer windows:

```text
python tools\fpga_compositor_framebuffer.py --formats
python tools\fpga_compositor_framebuffer.py --windows
```

## Scope

I36-S01 defines the memory policy for framebuffer planes before fetch RTL or
composition RTL exists. It consumes the I35-S01 video profile and the I29-S01
external-memory boundary. The policy reserves a payload-only framebuffer heap,
defines stride and alignment rules, selects first pixel formats, sizes the line
buffer target, and keeps capability tags out of scanout-visible surfaces.

This story does not implement the fetch master, compositor pipeline, vblank
descriptor latch, memory arbiter, firmware demo, or board evidence. Those are
owned by I36-S02, I36-S03, I36-S04, I36-S05, I36-S08, and I36-S07.

Required prerequisite gates:

```text
python tools\fpga_video_display.py --check
python tools\fpga_external_memory.py --check
python tools\fpga_soc_top_decoder.py --check
```

## Framebuffer Window

The first full-resolution framebuffer heap lives inside the I29-S01
`external_ddr_payload` window:

| Field | Value |
| --- | --- |
| Name | `external_ddr_framebuffer_heap` |
| Base | `0x01100000` |
| End | `0x01500000` |
| Size | `0x00400000` cells |
| Memory type | normal uncacheable |
| Cacheability | Uncacheable until a future coherent graphics policy exists. |
| Tag policy | payload-only, no capability tags |

BRAM fixtures may cover reduced-size planes and line-buffer tests. Full
1280x720 framebuffers require the external-memory window.

## Pixel Formats

Pixel bytes are little-endian within 48-bit payload cells. Framebuffer base and
stride values are aligned to 16 cells.

| Format | Bytes/px | 720p frame bytes | 720p frame cells | Alpha policy | First owner |
| --- | ---: | ---: | ---: | --- | --- |
| `rgb565` | 2 | 1,843,200 | 307,200 | opaque | I36-S02 |
| `xrgb8888` | 4 | 3,686,400 | 614,400 | ignored X byte, opaque | I36-S02 |
| `indexed8` | 1 | 921,600 | 153,600 | palette-entry policy deferred | I36-S03 |

The reserved heap can hold at least two 1280x720 `xrgb8888` frames. Smaller
formats and overlays use the same base, stride, size, and clipping policy that
I36-S02 and I36-S03 will implement.

## Line Buffer

The first line-buffer policy targets the largest initial format:

| Field | Value |
| --- | ---: |
| Active width | 1280 |
| Max bytes/px | 4 |
| Buffered lines | 2 |
| Required cells | 1707 |
| Allocated cells | 2048 |
| Underflow counter | `VIDEO_UNDERFLOW_COUNT` |

Underflow is visible through the I35-S01 `VIDEO_UNDERFLOW_COUNT` register and
is closed in I36-S06 timing and bandwidth evidence.

## Memory Ownership

- CPU and loader writes populate framebuffer payloads through existing memory
  paths.
- The compositor reads framebuffer payloads through the I35-S01 read-only
  scanout master.
- Framebuffer payload memory is not capability-tag-bearing storage.
- `CLC` and `CSC` targeting framebuffer surfaces remain rejected by the
  external-memory tag policy until a future tag-sidecar story exists.
- CPU/compositor arbitration is closed by I36-S08 before shared-memory board
  demos are claimed.

## Non-Goals

- Cache-coherent graphics.
- Capability tag sidecars for framebuffers.
- Shader or graphics command processor.
- PCIe-like graphics endpoint.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Framebuffer window is reserved. | Met by `external_ddr_framebuffer_heap`. |
| Line-buffer size and stride/alignment policy are defined. | Met. |
| RGB565, XRGB8888, and indexed format policy is explicit. | Met. |
| Cacheability and capability-tag exclusions are explicit. | Met by normal uncacheable, payload-only memory. |
| CPU/compositor memory arbitration handoff is explicit. | Met by I36-S08. |

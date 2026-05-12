# FPGA Video Display Profile

Story: I35-S01

Status: Display profile and CPU/compositor interface implemented

## Command

Validate the profile:

```text
python tools\fpga_video_display.py --check
```

Print the structured profile:

```text
python tools\fpga_video_display.py --json
```

List video registers or scanout read-master signals:

```text
python tools\fpga_video_display.py --registers
python tools\fpga_video_display.py --signals
```

## Scope

I35-S01 defines the first same-FPGA display subsystem boundary. The CPU programs
the video block through local MMIO in the existing `platform_devices` window.
The scanout side owns a future framebuffer read master for payload reads into
BRAM or external memory. A PCIe-like endpoint, graphics command queue, shader
pipeline, cache-coherent GPU fabric, and display capability-tag sidecar are
explicit non-goals for this integration path.

This story does not implement scanout RTL, board pins, framebuffer fetch, plane
composition, or memory arbitration. Those are handed to I35-S02, I35-S03,
I35-S04, I36-S01, and I36-S08.

Required prerequisite gates:

```text
python tools\fpga_soc_platform.py --check
python tools\fpga_soc_top_decoder.py --check
python tools\fpga_clock_profiles.py --check
```

## 720p Timing Target

The first mode is CEA-style 1280x720 at 60 Hz:

| Field | Value |
| --- | ---: |
| Active width | 1280 |
| Active height | 720 |
| Pixel clock | 74.25 MHz |
| Horizontal front porch | 110 |
| Horizontal sync | 40 |
| Horizontal back porch | 220 |
| Horizontal total | 1650 |
| Vertical front porch | 5 |
| Vertical sync | 5 |
| Vertical back porch | 20 |
| Vertical total | 750 |
| Sync polarity | Active high hsync and vsync |

I35-S02 consumes this timing profile when it implements the counter and
test-pattern scanout RTL.

## MMIO Window

The video control/status block reserves the next free 0x100-cell slot in
`platform_devices`:

| Field | Value |
| --- | --- |
| Peripheral | `video_display` |
| Base | `0x00F00500` |
| End | `0x00F00600` |
| Size | `0x100` cells |
| Access | Device ordered local MMIO |
| Interrupt line | `video_vblank` |
| Interrupt bit | 4 |

I35-S04 wires this window into the top-level data/MMIO decoder and routes
`video_vblank` through the existing interrupt-controller model.

## Register Summary

| Register | Offset | Access | Purpose |
| --- | ---: | --- | --- |
| `VIDEO_CONTROL` | `0x00` | rw | Enable scanout and select reset/test-pattern behavior. |
| `VIDEO_MODE` | `0x01` | rw | Selected timing mode; zero is `cea_720p60`. |
| `VIDEO_STATUS` | `0x02` | ro | Enabled, in-vblank, underflow, and mode-valid status bits. |
| `VIDEO_IRQ_ENABLE` | `0x03` | rw | Enable vblank and error interrupt sources. |
| `VIDEO_IRQ_ACK` | `0x04` | w1c | Acknowledge sticky vblank and error interrupt sources. |
| `VIDEO_FRAME_COUNT` | `0x05` | ro | Completed frame count. |
| `VIDEO_LINE_COUNT` | `0x06` | ro | Pixel-domain line counter snapshot. |
| `VIDEO_PIXEL_COUNT` | `0x07` | ro | Pixel-domain pixel counter snapshot. |
| `VIDEO_TEST_PATTERN` | `0x08` | rw | Pattern selector before framebuffer fetch exists. |
| `VIDEO_BG_COLOR` | `0x09` | rw | RGB background color. |
| `VIDEO_UNDERFLOW_COUNT` | `0x0A` | ro | Scanout read or line-buffer underflow count. |
| `VIDEO_FB_MASTER_STATUS` | `0x0B` | ro | Read-master idle, busy, blocked, and error status bits. |

## Framebuffer Read-Master Boundary

The display block does not receive pixel data over MMIO. It will read payload
memory through a bounded read-only framebuffer read master:

| Signal | Direction | Width | Purpose |
| --- | --- | ---: | --- |
| `video_rd_req_valid` | display to memory | 1 | Scanout read request is valid. |
| `video_rd_req_ready` | memory to display | 1 | Memory arbiter can accept a scanout read request. |
| `video_rd_req_addr` | display to memory | 48 | Cell address for the next payload read. |
| `video_rd_req_len_cells` | display to memory | 8 | Bounded burst length in cells. |
| `video_rd_rsp_valid` | memory to display | 1 | Read response data is valid. |
| `video_rd_rsp_ready` | display to memory | 1 | Scanout can accept response data. |
| `video_rd_rsp_data` | memory to display | 48 | Payload data from BRAM or external memory. |
| `video_rd_rsp_error` | memory to display | 1 | Memory boundary reported a scanout read error. |

The display master reads payload data only. It never accepts, creates, or stores
capability tags. I36-S01 owns framebuffer memory layout, pixel packing,
line-buffer sizing, cacheability, and tag-policy details for planes.

## Pixel Formats

The profile reserves these format names for later stories:

| Format | Owner | Notes |
| --- | --- | --- |
| `test_pattern` | I35-S02 | No framebuffer traffic. |
| `rgb565` | I36-S01 | Compact first framebuffer format. |
| `xrgb8888` | I36-S01 | Wider debug/demo format when bandwidth allows. |

## Handoffs

- I35-S02 implements the 1280x720 timing generator and test-pattern scanout.
- I35-S03 owns pixel-clock/reset/CDC and board-output handoff.
- I35-S04 integrates the MMIO window and `video_vblank` interrupt routing.
- I36-S01 defines framebuffer windows, bandwidth, formats, and tag policy.
- I36-S08 closes CPU/compositor memory arbitration once framebuffer fetch
  shares BRAM or external-memory access with CPU data traffic.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| 1280x720 timing target is fixed. | Met by the CEA-style 720p60 timing table. |
| CPU/compositor interface is local MMIO plus framebuffer read master. | Met. |
| PCIe-like fabric is excluded for same-FPGA integration. | Met. |
| Vblank/status interrupt ownership is named. | Met by `video_vblank` bit 4 and I35-S04 handoff. |
| Memory ownership and tag policy are explicit. | Met by the payload-only read-master boundary and I36-S01 handoff. |

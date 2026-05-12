# FPGA Video MMIO And IRQ

Story: I35-S04

Status: video control/status MMIO and vblank IRQ routing implemented

## Command

Validate the story profile:

```text
python tools\fpga_video_mmio.py --check
```

Print profile, register, IRQ-demo, and lint command data:

```text
python tools\fpga_video_mmio.py --json
python tools\fpga_video_mmio.py --registers
python tools\fpga_video_mmio.py --irq-demo
python tools\fpga_video_mmio.py --plan
```

## Scope

I35-S04 turns the I35-S01 video register allocation into an RTL MMIO block and
routes its `video_vblank` interrupt through the existing SoC interrupt
controller. The CPU reaches the block through the existing
`cpu_v01_fpga_soc_dmem_decoder` local-MMIO path at `0x00F00500`.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_video_mmio.py` | Executable MMIO/IRQ profile, register behavior model, validator, and vblank IRQ demo. |
| `tools/fpga_video_mmio.py` | CLI for `--check`, `--json`, `--registers`, `--irq-demo`, and `--plan`. |
| `rtl/cpu_v01_fpga_top.sv` | Adds `cpu_v01_fpga_video_mmio`, the video decoder target, and IRQ bit 4 routing. |
| `rtl/cpu_v01_fpga_video_mmio_tb.sv` | Standalone self-checking RTL testbench for video register and IRQ behavior. |
| `tests/conformance/test_i35_s04_fpga_video_mmio.py` | Story conformance tests for model, docs, CLI, RTL tokens, and handoffs. |

## Register Behavior

| Register | Offset | Access | Behavior |
| --- | ---: | --- | --- |
| `VIDEO_CONTROL` | `0x00` | rw | Bit 0 enables scanout; bit 1 enables visible output. |
| `VIDEO_MODE` | `0x01` | rw | Mode selector; mode 0 is the supported 720p mode. |
| `VIDEO_STATUS` | `0x02` | ro | Reports enabled, in-vblank, underflow-pending, mode-valid, and vblank-pending bits. |
| `VIDEO_IRQ_ENABLE` | `0x03` | rw | Bit 0 enables vblank IRQ; bit 1 enables underflow IRQ. |
| `VIDEO_IRQ_ACK` | `0x04` | w1c | Clears sticky vblank and underflow pending bits. |
| `VIDEO_FRAME_COUNT` | `0x05` | ro | 48-bit frame counter snapshot. |
| `VIDEO_LINE_COUNT` | `0x06` | ro | Current scanout line snapshot. |
| `VIDEO_PIXEL_COUNT` | `0x07` | ro | Current scanout pixel snapshot. |
| `VIDEO_TEST_PATTERN` | `0x08` | rw | Test-pattern selector for the scanout/output boundary. |
| `VIDEO_BG_COLOR` | `0x09` | rw | 24-bit background RGB. |
| `VIDEO_UNDERFLOW_COUNT` | `0x0A` | ro | 48-bit underflow pulse counter. |
| `VIDEO_FB_MASTER_STATUS` | `0x0B` | ro | Framebuffer/read-master status snapshot for later compositor fetch. |

## Interrupt Routing

`cpu_v01_fpga_video_mmio` records a sticky vblank-pending bit on the rising edge
of `video_vblank_i`. When `VIDEO_IRQ_ENABLE[0]` is set, the block asserts
`video_vblank_irq_o`. The top maps that source to interrupt-controller bit 4,
the `video_vblank` line from I35-S01.

The external interrupt aggregate now uses mask `16'h001B`: UART RX bit 0, UART
TX bit 1, GPIO/status bit 3, and video_vblank bit 4. Timer compare remains on
the core timer interrupt input and is not part of that external mask.

Firmware clears sticky video events by writing one to `VIDEO_IRQ_ACK`.

## Decoder And Top Handoff

`cpu_v01_fpga_soc_dmem_decoder` now routes the video window:

| Target | Base | End |
| --- | ---: | ---: |
| `video_display` | `0x00F00500` | `0x00F00600` |

The top-level source and control handoff is intentionally narrow:

- `video_scanout_enable_o`, `video_output_enable_o`, `video_test_pattern_o`,
  and `video_bg_color_o` are produced by the MMIO block for the scanout/output
  boundary.
- `VIDEO_FRAME_COUNT`, `VIDEO_LINE_COUNT`, `VIDEO_PIXEL_COUNT`, and vblank
  inputs are wired as scanout-side status sources. The board-neutral top ties
  them low until I35-S05 combines this with scanout simulation evidence.
- I36-S04 consumes `video_vblank` for atomic plane descriptor updates.

## Verilator

The focused lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_video_mmio_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_video_mmio_tb.sv
```

The testbench checks scanout/output enable writes, test-pattern/background
writes, vblank status and IRQ assertion, IRQ acknowledgement, frame-count
readback, line/pixel readback, and underflow counting.

## Handoffs

- I35-S05 proves combined scanout timing, MMIO behavior, vblank IRQ behavior,
  and lint/timing evidence.
- I35-S06 captures board-visible scanout and status evidence.
- I36-S04 consumes vblank for atomic plane descriptor updates.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Firmware can enable scanout and output. | Met by `VIDEO_CONTROL` and the RTL control outputs. |
| Firmware can select mode/test pattern and background color. | Met by `VIDEO_MODE`, `VIDEO_TEST_PATTERN`, and `VIDEO_BG_COLOR`. |
| Firmware can read status, frame, line, pixel, underflow, and fetch-status registers. | Met by the `cpu_v01_fpga_video_mmio` register map. |
| Firmware can acknowledge vblank. | Met by `VIDEO_IRQ_ACK` write-one-to-clear behavior. |
| Display interrupt routes through the existing interrupt controller. | Met by `video_vblank` bit 4 and external mask `16'h001B`. |

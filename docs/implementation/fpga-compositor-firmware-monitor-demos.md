# FPGA Compositor Firmware And Monitor Demos

Story: I36-S05

Status: firmware and monitor demo fixture defined

Structured gate:

```text
python tools\fpga_compositor_demo.py --check
```

Run the modeled demos or inspect profile data:

```text
python tools\fpga_compositor_demo.py --run
python tools\fpga_compositor_demo.py --json
python tools\fpga_compositor_demo.py --cases
python tools\fpga_compositor_demo.py --plan
```

Required gates:

```text
python tools\fpga_compositor_vblank.py --check
python tools\fpga_program_loader.py --check
python tools\fpga_monitor_session.py --check
```

## Purpose

I36-S05 defines deterministic firmware and monitor fixtures for the compositor
path. The fixtures fill reduced framebuffers, program I36-S04 shadow
descriptors, wait for vblank through `WAIT_VBLANK`, and record visible/status
signatures. This is not a physical board capture; I36-S07 owns board evidence
or blocker disposition.

The command vocabulary used by the fixture is:

- `LOAD_IMAGE`
- `COMPOSITOR_FILL`
- `PROGRAM_PLANE`
- `WAIT_VBLANK`
- `SWAP_DESCRIPTOR`
- `READ_STATUS`

`LOAD_IMAGE` remains tied to the I26-S04 board-safe loader hashes. The monitor
case uses the I32-S03 monitor-session case identity, while compositor-specific
operations are modeled as demo fixture commands rather than a new transport
command set.

## Demo Cases

| Case | Actor | Program image | Coverage |
| --- | --- | --- | --- |
| `one_plane_fill` | firmware | `relocation.branch_call_data_fpga` | Fill one XRGB8888 framebuffer, program plane 0, wait for vblank, observe a red plane 0 pixel. |
| `overlay_swap` | monitor | `call_return.direct_call_ret_fpga` | Fill base and overlay framebuffers, program two planes, wait for vblank, swap plane 1 to a new framebuffer, and wait for a second vblank. |
| `error_path_underflow` | firmware | `syscall_trap.sys_pause_iret_fpga` | Program an out-of-window plane base and observe deterministic underflow status with background visible. |

Each descriptor phase checks that `descriptor_pending` is set by
`PROGRAM_PLANE` or `SWAP_DESCRIPTOR`, that vblank clears the pending bit, and
that `applied_count` advances only after `WAIT_VBLANK`.

## Expected Observations

The `one_plane_fill` firmware case samples `(1, 1)` after the first vblank and
expects `0xFF0000` from `plane0`.

The `overlay_swap` monitor case first samples `(2, 1)` with a half-alpha blue
overlay over a red base and expects `0x7F0080` from `plane1`. It then swaps the
plane 1 descriptor to a green framebuffer and, after the second vblank, expects
`0x00FF00` from `plane1`.

The `error_path_underflow` firmware case samples `(0, 0)` after programming a
bad framebuffer base. The expected RGB remains the compositor background
`0x102030`, the selected plane is `background`, and the UART/status signature
contains `UNDERFLOW_ERROR`.

## Signatures

Each case records a distinct digest over expected LED, expected UART, expected
probe, and status-code fields:

| Case phase | expected LED | expected UART | expected probe |
| --- | --- | --- | --- |
| `one_plane_fill:one_plane` | `I36S05_LED_ONE_PLANE_PASS` | `I36-S05 ONE_PLANE rgb=FF0000 applied=1` | `plane0_active selected=plane0 underflow=0` |
| `overlay_swap:overlay` | `I36S05_LED_OVERLAY_PASS` | `I36-S05 OVERLAY rgb=7F0080 applied=1` | `plane1_over_plane0 alpha=128 underflow=0` |
| `overlay_swap:swap` | `I36S05_LED_SWAP_PASS` | `I36-S05 SWAP rgb=00FF00 applied=2` | `plane1_swap selected=plane1 underflow=0` |
| `error_path_underflow:bad_base` | `I36S05_LED_UNDERFLOW_ERROR` | `I36-S05 UNDERFLOW_ERROR bad_base` | `plane0_underflow selected=background underflow=1` |

## Handoffs

- I36-S06 archives timing, bandwidth, resource, and underflow evidence for
  these demos.
- I36-S07 captures first board compositor demo evidence or blocker disposition.
- I36-S08 closes shared CPU/compositor memory arbitration before board claims.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Firmware or monitor fixtures fill framebuffers. | Met by `COMPOSITOR_FILL` surfaces for one-plane, overlay, and swap buffers. |
| Fixtures program plane descriptors and wait for vblank. | Met by `PROGRAM_PLANE`, `SWAP_DESCRIPTOR`, `WAIT_VBLANK`, `descriptor_pending`, and `applied_count` checks. |
| Descriptor swaps produce visible changes only after vblank. | Met by the monitor `overlay_swap` second phase applying on the second vblank. |
| One-plane, overlay, and error-path signatures are distinct. | Met by expected LED, expected UART, expected probe, and digest checks for all phases. |

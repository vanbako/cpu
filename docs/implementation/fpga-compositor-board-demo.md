# FPGA Compositor Board Demo

Story: I36-S07

Status: board compositor archive gate implemented; physical compositor evidence
is blocked until a real board run or classified blocker archive exists

## Command

Validate the archive profile:

```text
python tools\fpga_compositor_board.py --check
```

Print the template, field list, retest commands, blocker policy, or structured
profile:

```text
python tools\fpga_compositor_board.py --template
python tools\fpga_compositor_board.py --fields
python tools\fpga_compositor_board.py --retest
python tools\fpga_compositor_board.py --blockers
python tools\fpga_compositor_board.py --json
python tools\fpga_compositor_board.py --audit-default
```

Audit a captured board compositor run:

```text
python tools\fpga_compositor_board.py --audit docs\implementation\evidence\i36_s07_compositor_board_demo.txt
```

Required upstream gates:

```text
python tools\fpga_compositor_evidence.py --check
python tools\fpga_video_board_scanout.py --check
python tools\fpga_compositor_demo.py --check
```

## Scope

I36-S07 archives the first board-visible compositor demo result, or a
classified blocker when the board run cannot show a compositor result. It does
not claim board success from simulation alone. The archive requires I36-S06
timing/bandwidth/resource/underflow evidence and I35-S06 board scanout evidence
before a compositor board pass can close.

## Evidence Format

The archive record lives at:

```text
docs/implementation/evidence/i36_s07_compositor_board_demo.txt
```

It uses key-value fields:

```text
story=I36-S07
archived_at=
repository_commit=
board=Sipeed Tang Mega Dock with 138K SOM
video_board_scanout=docs/implementation/evidence/i35_s06_video_board_scanout.txt
video_board_scanout_status=archived
compositor_evidence=docs/implementation/evidence/i36_s06_compositor_evidence_archive.txt
compositor_evidence_status=archived
compositor_demo_gate=python tools\fpga_compositor_demo.py --check
compositor_demo_status=passed
bitstream_path=build/fpga/tang_mega_138k/compositor/impl/pnr/compositor_demo.fs
bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
framebuffer_image_manifest=docs/implementation/evidence/i36_s07_framebuffer_manifest.json
framebuffer_image_hashes=one_plane=sha256:...,overlay=sha256:...,swap=sha256:...,error=sha256:...
firmware_command_log=docs/implementation/evidence/i36_s07_firmware_commands.log
visible_capture=docs/implementation/evidence/i36_s07_compositor_capture.jpg
probe_capture=none
vblank_log=docs/implementation/evidence/i36_s07_vblank.log
underflow_log=docs/implementation/evidence/i36_s07_underflow.log
status_log=docs/implementation/evidence/i36_s07_status.log
replay_or_simulation_commands=python tools\fpga_compositor_demo.py --run ; python tools\fpga_compositor_board.py --audit docs\implementation\evidence\i36_s07_compositor_board_demo.txt
pass_fail_result=compositor_board_pass
archive_result=compositor_board_pass_archived
blocker_class=none
blocker_evidence=none
residual_blockers=none
filed_issues=none
retest_criteria=python tools\fpga_compositor_evidence.py --check ; python tools\fpga_video_board_scanout.py --check ; python tools\fpga_compositor_demo.py --check ; python tools\fpga_compositor_board.py --audit docs\implementation\evidence\i36_s07_compositor_board_demo.txt
```

## Required Evidence

| Field | Required result |
| --- | --- |
| `bitstream_sha256` | SHA-256 of the bitstream that drove the compositor board run. |
| `framebuffer_image_manifest` | Manifest for the board-loaded framebuffer images. |
| `framebuffer_image_hashes` | Hashes for `one_plane`, `overlay`, `swap`, and `error` images. |
| `firmware_command_log` | Firmware or monitor command transcript, including fill, program-plane, wait-vblank, swap, and status commands. |
| `visible_capture` | Photo/video of compositor output, or `none` when probe output carries the result. |
| `probe_capture` | ILA/logic/UART probe output, or `none` when visible capture carries the result. |
| `vblank_log` | Vblank wait and descriptor-applied observations. |
| `underflow_log` | Underflow counters for one-plane, overlay/swap, and error-path demos. |
| `status_log` | Decoded status/UART/pass-fail log for the compositor run. |
| `replay_or_simulation_commands` | Nearest replay or simulation commands, including `python tools\fpga_compositor_demo.py --run`. |

## Result Rules

| Archive result | Pass/fail result | Evidence policy | Blocker policy |
| --- | --- | --- | --- |
| `compositor_board_pass_archived` | `compositor_board_pass` | Requires visible_capture or probe_capture plus framebuffer, command, vblank, underflow, status, and replay evidence. | `blocker_class=none`, `blocker_evidence=none`, `residual_blockers=none`, and `filed_issues=none`. |
| `compositor_board_blocker_archived` | `failure_observed` | Requires concrete blocker evidence, status logs, replay/simulation commands, and retest_criteria. | Requires `blocker_class`, `residual_blockers`, and `filed_issues`. |

`blocker_class` is one of `scanout_precondition`, `compositor_timing`,
`framebuffer_image`, `firmware_command`, `vblank_descriptor`,
`underflow_status`, `visible_output`, `probe_capture`, `memory_bandwidth`, or
`board_integration`.

## Current Blocker

- No physical compositor bitstream, framebuffer image manifest, or board-loaded
  framebuffer hashes have been captured.
- No board firmware command log, visible_capture, probe_capture, vblank_log,
  underflow_log, or status_log exists for the compositor demo.
- I36-S06 compositor evidence and I35-S06 board scanout evidence are still
  blocked by default in the current repository state, so I36-S07 remains
  blocked until both prerequisites are archived.

## Handoff

- I36-S08 can use a classified `memory_bandwidth` or `underflow_status`
  blocker as arbitration input, but cannot claim board composition pass
  evidence from this gate alone.
- Later board retests can reference `compositor_board_pass_archived` only when
  the exact bitstream, framebuffer images, command transcript, visible/probe
  capture, vblank/underflow/status logs, and replay commands are linked.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Bitstream and framebuffer images are linked. | Met by `bitstream_path`, `bitstream_sha256`, `framebuffer_image_manifest`, and `framebuffer_image_hashes`. |
| Firmware commands are archived. | Met by `firmware_command_log`. |
| Visible capture or probe output is archived. | Met by `visible_capture` or `probe_capture`. |
| Vblank, underflow, and status logs are archived. | Met by `vblank_log`, `underflow_log`, and `status_log`. |
| Replay or simulation commands are preserved. | Met by `replay_or_simulation_commands`. |
| Residual blockers and retest criteria are explicit. | Met by `blocker_class`, `blocker_evidence`, `residual_blockers`, `filed_issues`, and `retest_criteria`. |

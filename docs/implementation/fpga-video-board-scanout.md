# FPGA Video Board Scanout

Story: I35-S06

Status: board scanout archive gate implemented; physical scanout evidence is
blocked until a real board run exists

## Command

Validate the archive profile:

```text
python tools\fpga_video_board_scanout.py --check
```

Print the evidence template, field list, retest commands, or structured data:

```text
python tools\fpga_video_board_scanout.py --template
python tools\fpga_video_board_scanout.py --fields
python tools\fpga_video_board_scanout.py --retest
python tools\fpga_video_board_scanout.py --json
```

Audit a captured board run:

```text
python tools\fpga_video_board_scanout.py --audit docs\implementation\evidence\i35_s06_video_board_scanout.txt
```

Required upstream gates:

```text
python tools\fpga_video_scanout_gate.py --check
python tools\fpga_first_pass_archive.py --check
```

## Scope

I35-S06 archives the first board-visible 720p scanout result, or a classified
blocker when the board run cannot show a valid pattern. It does not claim a
physical display pass from simulation alone. The archive requires I35-S05
simulation/report gate evidence and an archived I31-S05 first-pass handoff
before board scanout evidence can close.

## Evidence Format

The archive record lives at
`docs/implementation/evidence/i35_s06_video_board_scanout.txt` and uses:

```text
story=I35-S06
archived_at=
repository_commit=
board=Sipeed Tang Mega Dock with 138K SOM
first_pass_archive=docs/implementation/evidence/i31_s05_first_cpu_pass_archive.txt
first_pass_archive_status=archived
scanout_gate=python tools\fpga_video_scanout_gate.py --check
scanout_gate_status=passed
gowin_report_bundle=build/fpga/tang_mega_138k/first_test/impl
bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first_video.fs
bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
display_adapter_wiring=docs/implementation/evidence/i35_s06_display_adapter_wiring.txt
pixel_clock_evidence=docs/implementation/evidence/i35_s06_pixel_clock_scope.png
timing_evidence=docs/implementation/evidence/i35_s06_720p_timing_decode.txt
visible_test_pattern_capture=docs/implementation/evidence/i35_s06_test_pattern.jpg
probe_capture=none
video_mmio_register_log=docs/implementation/evidence/i35_s06_video_mmio.log
vblank_status_observation=docs/implementation/evidence/i35_s06_vblank_status.txt
decoded_status_packet=docs/implementation/evidence/i35_s06_status_packet.json
pass_fail_result=scanout_pass
archive_result=board_scanout_pass_archived
blocker_class=none
blocker_evidence=none
residual_blockers=none
filed_issues=none
retest_steps=python tools\fpga_video_scanout_gate.py --check ; python tools\fpga_first_pass_archive.py --check ; python tools\fpga_video_board_scanout.py --audit docs\implementation\evidence\i35_s06_video_board_scanout.txt
```

## Required Evidence

| Field | Required result |
| --- | --- |
| `bitstream_sha256` | SHA-256 of the bitstream that drove the board. |
| `display_adapter_wiring` | Wiring note or photo for the display/output adapter. |
| `pixel_clock_evidence` | Pixel-clock report, scope measurement, or probe capture. |
| `timing_evidence` | 720p timing decode, report, or probe observation. |
| `visible_test_pattern_capture` | Photo/video of the test pattern, or `none` when probe evidence carries the result. |
| `probe_capture` | Probe/ILA/logic capture, or `none` when visible capture carries the result. |
| `video_mmio_register_log` | Firmware or monitor log showing video register programming. |
| `vblank_status_observation` | Vblank IRQ/status evidence or blocker-specific not-reached evidence. |
| `decoded_status_packet` | Decoded UART/status packet or transcript for the run. |

## Result Rules

| Archive result | Pass/fail result | Evidence policy | Blocker policy |
| --- | --- | --- | --- |
| `board_scanout_pass_archived` | `scanout_pass` | Requires a visible test pattern or probe capture plus vblank/status observations. | `blocker_class=none`, `blocker_evidence=none`, `residual_blockers=none`, and `filed_issues=none`. |
| `board_scanout_blocker_archived` | `failure_observed` | Requires concrete blocker evidence, vblank/status disposition, and retest steps. | Requires `blocker_class`, `residual_blockers`, and `filed_issues`. |

`blocker_class` is one of `display_adapter`, `pixel_clock`, `timing`,
`scanout_mmio`, `vblank_irq`, `bitstream`, or `board_integration`.

## Current Blocker

- No physical display/output adapter wiring has been captured.
- No board pixel-clock, timing, visible test-pattern, probe, or vblank/status
  observation exists.
- I31-S05 first-pass archive evidence is still blocked in the current
  repository state, so I35-S06 remains blocked by default.

## Handoffs

- I36-S07 consumes the scanout archive before claiming a compositor board demo.
- Later release evidence can reference `board_scanout_pass_archived` only when
  the exact bitstream, wiring, timing, vblank/status, and visible/probe
  evidence are linked.
- Classified blocker archives preserve filed issues and retest commands without
  claiming a board scanout pass.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Bitstream identity is recorded. | Met by `bitstream_path` and `bitstream_sha256`. |
| Display/output adapter wiring is recorded. | Met by `display_adapter_wiring`. |
| Pixel-clock and timing evidence are recorded. | Met by `pixel_clock_evidence` and `timing_evidence`. |
| Visible test pattern or probe capture is recorded. | Met by `visible_test_pattern_capture` or `probe_capture`. |
| Vblank/status observations are recorded. | Met by `vblank_status_observation`, `video_mmio_register_log`, and `decoded_status_packet`. |
| Residual blockers and retest commands are explicit. | Met by `blocker_class`, `blocker_evidence`, `residual_blockers`, `filed_issues`, and `retest_steps`. |

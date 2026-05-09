# FPGA Image Update Flow

Story: I26-S03

Status: Draft rebuild/update gate

## Command

Validate the flow:

```text
python tools\fpga_image_update_flow.py --check
```

Print the command plan:

```text
python tools\fpga_image_update_flow.py --plan
```

Print an evidence template:

```text
python tools\fpga_image_update_flow.py --template reset_smoke.reset_to_trap_fpga
```

Audit captured evidence:

```text
python tools\fpga_image_update_flow.py --audit-evidence docs\implementation\evidence\i26_s03_image_update.txt
```

## Scope

I26-S03 connects deterministic I26-S02 BRAM images to the bitstream used for a
board run. It names which artifacts require a full Gowin rebuild, which path
would be needed for memory updates, and how image identity must be recorded in
reports and board evidence.

Required upstream gates:

- `python tools\fpga_bram_images.py --check`
- `python tools\fpga_gowin_build.py --check`

The current safe default is `gowin_rebuild`. The optional `memory_update` mode
is blocked until the Gowin or programmer flow is verified for replacing GW5AST
BRAM initialization data without stale placement, timing, or bitstream identity
evidence.

## Rebuild Path

For every selected program:

1. Generate `rom.mem`, `data.mem`, and `tags.mem` from the manifest.
2. Record the selected manifest `image_sha256`.
3. Re-emit or reuse the checked Gowin Tcl.
4. Run `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl`.
5. Audit reports with `python tools\fpga_gowin_build.py --audit-reports build\fpga\tang_mega_138k\first_test`.
6. Record the output bitstream path and `bitstream_sha256`.
7. Carry `image_sha256` and `bitstream_sha256` into I24-S04 programming and
   later board evidence.

`rom.mem`, `data.mem`, and `tags.mem` all require a rebuild in the current
flow, because the generated memory images are consumed as synthesis/project
inputs rather than through a verified post-route patcher.

## Memory-Update Path

`memory_update` is a named but blocked mode. It may be used only after a later
story or tool run proves:

- the tool can update all selected BRAM init contents for `instruction_rom`,
  `data_ram`, and `tag_ram`;
- the update rejects malformed or stale `.mem` files;
- the report records the same manifest `image_sha256`;
- the post-update bitstream has a fresh `bitstream_sha256`;
- the board evidence links the update log before I24-S04 or I26-S04 uses it.

Until those are true, `memory_update` audits as blocked and cannot close board
programming evidence.

## Evidence Fields

`docs/implementation/evidence/i26_s03_image_update.txt` uses key/value fields:

```text
story=I26-S03
program_id=reset_smoke.reset_to_trap_fpga
image_sha256=
update_mode=gowin_rebuild
bram_images_verified=yes
generated_artifacts=rom.mem,data.mem,tags.mem
gowin_build_root=build/fpga/tang_mega_138k/first_test
gowin_audit_status=passed
bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs
bitstream_sha256=
memory_update_support_verified=no
memory_update_tool=none
memory_update_log=none
image_identity_recorded=yes
report_path=docs/implementation/evidence/i26_s03_image_update_report.json
recorded_at=
```

The audit fails if `image_sha256` does not match the selected I26-S01 manifest
entry. Rebuild mode is blocked unless the I24-S03 Gowin audit passes and a
64-character `bitstream_sha256` is recorded. Memory-update mode is blocked
unless tool support, update log, and post-update bitstream identity are all
recorded.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The flow names rebuild and memory-update modes. | Met by `gowin_rebuild` and `memory_update`. |
| Generated `rom.mem`, `data.mem`, and `tags.mem` are required for each program. | Met. |
| Rebuild mode requires Gowin report audit and bitstream identity. | Met. |
| Memory-update mode remains blocked until support is verified. | Met. |
| Image identity is recorded for I24-S04, I26-S04, and board evidence handoff. | Met. |

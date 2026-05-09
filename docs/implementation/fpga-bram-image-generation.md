# FPGA BRAM Image Generation

Story: I26-S02

Status: Draft deterministic generator

## Command

Validate the generator and its manifest inputs:

```text
python tools\fpga_bram_images.py --check
```

List generated bundles:

```text
python tools\fpga_bram_images.py --list
```

Print one rendered image without writing files:

```text
python tools\fpga_bram_images.py --print-image reset_smoke.reset_to_trap_fpga instruction_rom
```

Write artifacts under an explicit output root:

```text
python tools\fpga_bram_images.py --write --out-dir tmp_i26_s02_bram_images
```

Verify previously written artifacts:

```text
python tools\fpga_bram_images.py --verify tmp_i26_s02_bram_images
```

## Scope

I26-S02 consumes the I26-S01 manifest and emits deterministic BRAM
initialization text for every starter program. It does not rebuild Gowin
projects, patch bitstreams, or program the board. I26-S03 owns the rebuild or
memory-update decision, and I26-S04 owns any live UART/JTAG load path.

The required upstream gates are:

- `python tools\fpga_program_manifest.py --check`
- `python tools\fpga_smoke_firmware.py --check`

## Generated Artifacts

Each manifest entry produces three files under
`build/fpga/programs/<program-id>/` when written through `--write`:

| File | Memory | Format | Determinism rule |
| --- | --- | --- | --- |
| `rom.mem` | `instruction_rom` | `hex24-cells-v1` | One lowercase 6-hex-digit 24-bit cell per line, complete ROM depth, PAUSE fill outside placed sections. |
| `data.mem` | `data_ram` | `hex24-cells-v1` | One lowercase 6-hex-digit 24-bit cell per line, complete RAM depth, zero fill outside placed data sections. |
| `tags.mem` | `tag_ram` | `hex1-tags-v1` | One `0` or `1` tag bit per line, complete tag RAM depth, clear unless a trusted sidecar story adds tags. |

The generator hashes the exact rendered text, including the trailing newline.
Each artifact hash must match the corresponding I26-S01 `image_sha256`. This
keeps generated files tied to simulator-visible expected cells and tags without
committing generated build output.

## Starter Bundles

| Program ID | ROM source | Data source | Tag source |
| --- | --- | --- | --- |
| `reset_smoke.reset_to_trap_fpga` | Toolchain `main` plus `trap_handler` sections at reset and trap-handler cells. | Zero-filled. | Clear tags. |
| `syscall_trap.sys_pause_iret_fpga` | Toolchain packed SYS/PAUSE/IRET section at reset. | Zero-filled. | Clear tags. |
| `relocation.branch_call_data_fpga` | I17-S04 linked relocation text payload. | I17-S04 linked relocation data payload at `data_ram` base. | Clear tags. |

## Simulator Cross-Checks

The generator uses the manifest materialized cells as the reference model:

- rendered ROM lines are checked against `entry.materialized_cells("instruction_rom")`;
- rendered RAM lines are checked against `entry.materialized_cells("data_ram")`;
- rendered tag lines are checked against `entry.materialized_cells("tag_ram")`;
- line counts must match the FPGA memory depths from I23-S03;
- all rendered hashes must match the manifest image hashes.

The first board smoke firmware profile remains the active FPGA wrapper smoke
gate for this story. These generated images become board-selected inputs only
after I26-S03 records the rebuild or memory-update path and I26-S05 defines
which observations close each program.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| ROM/RAM/tag `.mem` artifacts are renderable for every I26-S01 starter entry. | Met. |
| The renderer is deterministic and hashes exact emitted text. | Met. |
| Generated cells and tags are checked against simulator-visible manifest cells. | Met. |
| File writing is explicit through `--write --out-dir`. | Met. |
| The profile validates through `python tools\fpga_bram_images.py --check`. | Met. |

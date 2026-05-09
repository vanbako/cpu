# FPGA Program-Image Manifest

Story: I26-S01

Status: Draft executable manifest

## Command

Validate the manifest:

```text
python tools\fpga_program_manifest.py --check
```

Print the manifest:

```text
python tools\fpga_program_manifest.py --json
```

List starter entries:

```text
python tools\fpga_program_manifest.py --list
```

## Scope

I26-S01 defines the loadable FPGA program-image manifest. It does not generate
`.mem` files, rebuild a bitstream, update an existing bitstream, or load a
program over UART/JTAG. Those handoffs belong to I26-S02, I26-S03, and I26-S04.

The manifest reuses existing architecture-facing fixtures instead of inventing
an FPGA-only program format:

- `python tools\toolchain_corpus.py --check` owns assembler, linker, object,
  and debug metadata fixture integrity.
- `python tools\fpga_memory_adapters.py --check` owns the `instruction_rom`,
  `data_ram`, and `tag_ram` adapter contract.
- `hex24-cells-v1` remains the instruction ROM and data RAM line format.
- `hex1-tags-v1` records the generated tag RAM sidecar as one clear or set tag
  bit per line in ascending cell-address order.

## Manifest Fields

Each entry records:

| Field | Meaning |
| --- | --- |
| `program_id` | Stable FPGA manifest ID used in artifact paths. |
| `source_case_id` | Toolchain corpus case ID or linked object fixture source. |
| `entry capability` | Reset `PCC` source, slot 0, cursor cell, bounds, and executable permission. |
| `sections` | Source section to FPGA memory placement, payload size, and section hash. |
| `memory_images` | `instruction_rom`, `data_ram`, and `tag_ram` artifact paths, formats, depths, fill values, and `image_sha256` hashes. |
| `expected_observations` | Board-visible LED, UART, GAO/ILA, or report evidence expected after the image is wrapped by later stories. |

Generated artifacts live under `build/fpga/programs/<program-id>/`:

| Memory | Artifact | Format | Fill policy |
| --- | --- | --- | --- |
| `instruction_rom` | `rom.mem` | `hex24-cells-v1` | `24'h05B05B` PAUSE cells outside placed program sections. |
| `data_ram` | `data.mem` | `hex24-cells-v1` | Zero-filled cells outside placed data sections. |
| `tag_ram` | `tags.mem` | `hex1-tags-v1` | Clear tags unless a later trusted sidecar story explicitly installs tags. |

The entry-level `image_sha256` hashes the entry capability and all three memory
image hashes. I26-S03 must copy that hash into rebuild, memory-update, and board
evidence records so a physical run can be tied back to the selected manifest
entry.

## Starter Entries

| Program ID | Source | Memory binding | Expected observation |
| --- | --- | --- | --- |
| `reset_smoke.reset_to_trap_fpga` | `reset_smoke.reset_to_trap_image` | `main` and `trap_handler` sections in `instruction_rom`; zero `data_ram`; clear `tag_ram`. | Retire progress through the main path and trap handler; syscall trap evidence captured by UART or GAO/ILA. |
| `syscall_trap.sys_pause_iret_fpga` | `syscall_trap.sys_pause_iret_binary` | Packed SYS/PAUSE/IRET text in `instruction_rom`; zero `data_ram`; clear `tag_ram`. | `status_fault_code_o` captures the syscall trap cause until I26-S05 adds a trap-aware pass harness. |
| `relocation.branch_call_data_fpga` | `relocation.branch_call_data_object` | Linked text in `instruction_rom`, linked data payload in `data_ram`, clear `tag_ram`. | `image_sha256` matches the selected manifest before Gowin rebuild or memory update; direct board execution waits for an I26-S05 harness because the corpus branch placement is not the FPGA reset address. |

## Tag Policy

The manifest preserves CPU v0.1 tag rules. Ordinary `hex24-cells-v1` payloads
never create valid capability tags. The default FPGA tag image is all clear.
Trusted capability sidecar installation remains outside I26-S01 and must not be
silently inferred from ordinary data cells.

Integer stores still clear tags through the I23-S03 tag RAM adapter. A future
program loader may add a trusted sidecar path only if it keeps the existing
`TRUSTED_CAPABILITY_SIDECAR` program-image rule and records that policy in the
manifest.

## Handoff

I26-S02 consumes this manifest to emit deterministic `rom.mem`, `data.mem`, and
`tags.mem` files and to check generated cells against simulator-visible
fixtures. I26-S03 records whether changing a manifest entry requires a Gowin
rebuild or can use a memory-update path. I26-S05 adds board smoke harnesses and
final pass/fail observations for multiple programs.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Manifest entries bind toolchain fixtures to `instruction_rom`, `data_ram`, and `tag_ram`. | Met. |
| Entry capability and image hashes are machine-readable. | Met. |
| The manifest uses `hex24-cells-v1` for ROM/RAM and a clear tag sidecar for `tag_ram`. | Met. |
| Expected board observations are listed without claiming a physical pass. | Met. |
| The profile validates through `python tools\fpga_program_manifest.py --check`. | Met. |

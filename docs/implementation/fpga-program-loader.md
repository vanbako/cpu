# FPGA Program Loader

Story: I26-S04

Status: Draft board-safe loader contract

## Command

Validate the loader profile and executable model:

```text
python tools\fpga_program_loader.py --check
```

List loadable manifest programs:

```text
python tools\fpga_program_loader.py --list
```

Run one modeled load:

```text
python tools\fpga_program_loader.py --run relocation.branch_call_data_fpga
```

Run malformed-image rejection fixtures:

```text
python tools\fpga_program_loader.py --rejections
```

## Scope

I26-S04 defines the board-safe load path that later SoC firmware or a debug
bridge can use after I26-S02 has produced deterministic BRAM images. The
current executable contract installs a bounded RAM image into `data_ram`,
rejects malformed images before state is changed, preserves the `tag_ram`
policy by clearing matching sidecar bits only, and reports success or failure
through UART/debug status.

Required upstream gates:

- `python tools\fpga_bram_images.py --check`
- `python tools\fpga_uart_mmio.py --check`
- `python tools\fpga_uart_status_streamer.py --check`
- `python tools\fpga_debug_status_packet.py --check`

The loader deliberately does not overwrite `instruction_rom`, generate trusted
capability tags, claim a board pass, or arbitrate the physical UART pin. I30-S04
owns SoC-top integration and UART/status arbitration. I32-S01 owns the later
interactive monitor command profile that can expand this command set.

## Loader Protocol

Two transports are named:

| Transport | Current status |
| --- | --- |
| `uart_mmio` | Uses the I27-S02 firmware-visible UART RX/TX registers. RX overrun aborts the frame. |
| `jtag_assisted` | Reserved for a bounded JTAG bridge after board scan and command evidence exist. |

The command sequence is intentionally chunked:

1. `LOAD_BEGIN program_id manifest_image_sha256 ram_image_sha256 target_memory base_cell cell_count`
2. `LOAD_CHUNK chunk_index payload_cells up_to_16 tag_bits_all_zero`
3. `LOAD_COMMIT payload_sha256`
4. `LOAD_ABORT status_code`

`LOAD_CHUNK` is bounded at 16 CPU cells. The UART FIFO is still the I27-S02
four-byte FIFO; firmware or debug firmware must drain it continuously and must
abort on `RX_OVERRUN` or `FRAME_ERROR` before accepting a commit.

## Bounds And Tags

The only accepted target is `data_ram`:

```text
0x00010000 .. 0x00011000
```

The request must cover the selected I26-S01 manifest RAM image exactly. The
loader checks both the whole-program `manifest_image_sha256` and the
`data_ram` `ram_image_sha256`. A payload outside the data RAM window, a stale
hash, an unknown `program_id`, an overlarge chunk, or a tag-bearing payload is
rejected before memory is modified.

`tag_ram` is never installed from host-supplied valid tags. For every accepted
data cell, the matching tag sidecar bit is cleared. This preserves the current
integer/untyped loader policy and leaves future trusted tag creation to a
separate story.

## Status Reporting

The status code names are:

| Code | Name | Meaning |
| --- | --- | --- |
| `0x0000` | `OK` | The bounded RAM image was installed. |
| `0x2601` | `BAD_PROGRAM` | `program_id` is not in the manifest. |
| `0x2602` | `BAD_HASH` | The manifest, RAM, or payload hash does not match. |
| `0x2603` | `BAD_TARGET` | The request targets a memory other than `data_ram`. |
| `0x2604` | `BOUNDS` | The payload range is outside the allowed RAM image. |
| `0x2605` | `TAG_POLICY` | The request carries nonzero tag bits or a tag count mismatch. |
| `0x2606` | `OVERRUN` | The observed command chunk exceeded the bounded frame size. |
| `0x2607` | `MALFORMED` | The command frame is structurally invalid. |

Success reports an ASCII UART line such as:

```text
I26-S04 LOAD OK program=relocation.branch_call_data_fpga cells=4096
```

Failure reports `I26-S04 LOAD ERR status=...` and emits an I25-S01 debug packet
with `pass_fail_state` set to `blocked`, `fault_valid` set, and the loader status
code in `fault_code`. Success uses the same debug/status path with
`pass_fail_state` set to `running` and `fault_code == 0`. The packet layout
remains owned by I25-S01 and the UART streamer remains owned by I25-S02.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A loader can install a bounded RAM image. | Met by the `data_ram` executable model and `--run` command. |
| Malformed images are rejected. | Met by rejection fixtures for unknown program, stale hash, bad target, bounds, tag policy, and overlarge chunks. |
| Tag policy is preserved. | Met by rejecting nonzero tag bits and clearing matching `tag_ram` sidecar bits on success. |
| Success/failure is reported over debug/status. | Met by UART ASCII status text plus I25-S01 debug packet status fields. |
| SoC-top and monitor handoffs are explicit. | Deferred to I30-S04 and I32-S01. |

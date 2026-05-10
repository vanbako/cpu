# FPGA Memory Adapters

Story: I23-S03

Status: Implemented FPGA BRAM adapter profile

This story adds the first FPGA-local memory blocks for `cpu_v01_fpga_top`: an
instruction ROM, data RAM, and tag RAM sidecar. The adapters are deliberately
small and synchronous so they can map to FPGA block RAM while preserving the
`cpu_v01_core` handshakes.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `rtl/cpu_v01_fpga_memories.sv` | BRAM-friendly instruction ROM, data RAM, and tag RAM modules. |
| `rtl/cpu_v01_fpga_memory_tb.sv` | Adapter smoke test for initialized ROM contents, data RAM read/write, and tag clear. |
| `rtl/cpu_v01_fpga_top.sv` | Instantiates the adapters behind the board-neutral FPGA wrapper. |
| `src/cpu_v01/fpga_memory.py` | Structured adapter inventory and source/documentation validator. |
| `tools/fpga_memory_adapters.py` | CLI wrapper for checking or rendering the adapter inventory. |
| `tests/conformance/test_i23_s03_fpga_memory_adapters.py` | I23-S03 conformance coverage. |

## Command

```text
python tools\fpga_memory_adapters.py --check
```

Verilator adapter lint:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_memory_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_memory_tb.sv
```

Verilator FPGA top lint with adapters:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_top_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv
```

## Adapter Contract

| Module | Role | Request behavior | Response behavior | Initialization | Tag policy |
| --- | --- | --- | --- | --- | --- |
| `cpu_v01_fpga_imem_rom` | Instruction ROM | Ready unless holding an unaccepted instruction response. | One-cycle response with two fetched 24-bit cells and a fetch fault on out-of-range access. | Built-in tiny PAUSE smoke image, or optional `readmemh` image. | No capability tags. |
| `cpu_v01_fpga_data_ram` | Data RAM | Always ready. | One-cycle read response; writes update cells and produce no response. | Zero-filled, or optional `readmemh` image. | Payload cells only. |
| `cpu_v01_fpga_tag_ram` | Tag RAM sidecar | Always ready. | One-cycle read response; writes update one tag bit and produce no response. | Configuration-cleared tag bits. | `CSC` preserves `req_wtag`; integer-store clear uses `req_wtag=0`. |

The ROM image format is compatible with the I23-S01 `hex24-cells-v1` profile:
one 6-hex-digit 24-bit cell per line in ascending cell-address order. The
default built-in image fills the first cells with `PAUSE` pairs so the adapter
has deterministic initialized content before I23-S04 adds the real smoke
firmware.

## Top-Level Attachment

`cpu_v01_fpga_top` now instantiates:

- `cpu_v01_fpga_imem_rom` at `RESET_VECTOR`;
- `cpu_v01_fpga_data_ram` at `DATA_RAM_BASE`;
- `cpu_v01_fpga_tag_ram` over the same `DATA_RAM_BASE` range.

The wrapper defaults `ENABLE_FETCH` to `1'b1` for the I23-S04 smoke firmware.
The reset-smoke testbench overrides `ENABLE_FETCH` to `1'b0`, so the wrapper
reset contract remains stable while the board-facing default fetches from the
ROM stream.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Instruction ROM satisfies the core instruction-memory handshake. | Met by ready/valid response logic and the adapter testbench. |
| The ROM has deterministic initialized contents. | Met by the built-in tiny PAUSE image and optional `readmemh` image path. |
| Data RAM supports BRAM-style reads and writes. | Met by one-cycle read responses and synchronous cell writes. |
| Tag RAM preserves capability-store tags and clears integer-store tags. | Met by tag write/read smoke checks for `req_wtag=1` and `req_wtag=0`. |
| The FPGA top uses the adapters instead of tied-off memory responses. | Met by `cpu_v01_fpga_top` adapter instantiations. |

## Deferrals

- I23-S05 owns board constraints, synthesis, implementation, and timing gates.
- I23-S06 owns captured board evidence.

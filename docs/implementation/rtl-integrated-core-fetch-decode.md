# RTL Integrated Core Fetch Decode

Story: I22-S02

Status: Draft RTL fetch/decode implementation

This story enables the first live front-end behavior in `cpu_v01_core`. The
core now requests a 48-bit fetch group, selects the current cell and hidden
slot, classifies 12/24/48-bit instruction sizes, and emits decode-only retire
packets or precise front-end faults.

I22-S02 still does not execute instructions. I22-S03 owns scalar, branch, CSR,
CCSR, and normal architectural effects after decode.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds the `OPC_WFI_12` selector so every 12-bit control opcode can be named by the integrated decoder. |
| `rtl/cpu_v01_core.sv` | Adds `ENABLE_FETCH`, fetch request/response states, 12/24/48-bit decode tables, slot sequencing, placement faults, and illegal-instruction faults. |
| `rtl/cpu_v01_core_fetch_decode_tb.sv` | Verilator-oriented fixture for legal 24-bit, packed 12-bit slot 0/slot 1, legal 48-bit, 48-bit placement fault, 24-bit slot-1 placement fault, and illegal opcode cases. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_fetch_decode.py --check
```

Print the size/major coverage projection:

```text
python tools\rtl_core_fetch_decode.py --json
```

The Verilator fixture command for this front-end slice is:

```text
verilator --binary --timing --top-module cpu_v01_core_fetch_decode_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_fetch_decode_tb.sv
```

## Implemented Behavior

- `imem_req_addr` is the 48-bit fetch-group base, `PCC.cursor & ~1`.
- `imem_req_valid`/`imem_rsp_ready` are driven by the fetch request and wait
  states when `ENABLE_FETCH=1`.
- 48-bit and 24-bit forms are recognized from the high 8-bit major field of the
  selected cell.
- 12-bit forms are recognized from the active 12-bit half selected by
  `PCC.slot`.
- 12-bit slot-0 fall-through advances to slot 1 in the same cell.
- 12-bit slot-1, 24-bit, and 48-bit fall-through return to slot 0 at the next
  architectural cell or fetch group.
- Recognizable 24-bit or 48-bit forms at slot 1 retire `ALIGN_FAULT`.
- Recognizable 48-bit forms at the second fetch-group cell retire
  `ALIGN_FAULT`.
- Unknown opcode contents retire `ILLEGAL_INSTRUCTION` with `TVAL=0`.

## Decode-Only Retire Packets

Legal instructions retire a packet with:

- `decoded.valid=1`;
- `decoded.opcode_id` set to the canonical opcode selector;
- `decoded.size_bits` set to 12, 24, or 48;
- `instruction_length` set to one cell for 12/24-bit forms and two cells for
  48-bit forms;
- `normal_valid=1`;
- no register, CSR, CCSR, memory, tag, trap, reservation, fence, or cache
  maintenance effect.

This keeps the differential harness boundary alive while avoiding partial
execution semantics before I22-S03.

## Deferred From This Story

- Scalar/control execution and all architectural writes: I22-S03.
- Capability and data/tag memory effects: I22-S04.
- Trap, syscall, protected call, and return effects: I22-S05.
- MMU/TLB translation: I22-S06.
- LL/SC, fences, and cache maintenance: I22-S07.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| The integrated core fetches through the instruction-memory port. | Met. |
| 12/24/48-bit decode selects canonical opcode IDs. | Met. |
| Slot sequencing follows E04-S01/E01-S05 placement rules. | Met. |
| Placement and illegal-instruction faults are precise retire packets. | Met. |
| Execution effects remain deferred to I22-S03 and later stories. | Met. |

# SystemVerilog Interface Specification

Story: I20-S03

Status: Draft generated-spec profile

The first RTL package and top-level port contract is generated from
`src/cpu_v01/sv_contract.py`. This story does not implement RTL behavior; it
fixes the names, widths, packet fields, and external interfaces that the first
SystemVerilog slice must use.

## Command

Render the Markdown spec:

```text
python tools\sv_interface_spec.py
```

Render machine-readable JSON:

```text
python tools\sv_interface_spec.py --format json
```

The generated package name is `cpu_v01_pkg`.

## Required Surfaces

The generated contract validates coverage for:

- `cells`;
- `capabilities`;
- `tags`;
- `csrs`;
- `decoded_opcodes`;
- `fault_packets`;
- `retire_packets`;
- `instruction_memory`;
- `data_memory`;
- `tag_memory`.

## Package Contents

The constant set is derived from the Python semantic model and includes:

- cell, address, fetch-group, integer-object, and capability-object widths;
- capability payload, cursor, bounds metadata, permission, object-type, flag,
  and tag widths;
- integer and capability register counts;
- scalar CSR value and number widths;
- fault cause, `CAPCAUSE`, `FAULTCAPIDX`, and retire sequence widths;
- one opcode selector constant for every mandatory v0.1 opcode form.

The packed type set includes:

- `cap_payload_t`;
- `cap_t`;
- `decoded_opcode_t`;
- `fault_packet_t`;
- `retire_packet_t`.

## Top-Level Interfaces

The generated interface specs are:

| Interface | Purpose |
| --- | --- |
| `cpu_v01_imem_if` | Instruction fetch group request/response. |
| `cpu_v01_dmem_if` | Data payload memory request/response. |
| `cpu_v01_tagmem_if` | Capability tag sidecar memory request/response. |
| `cpu_v01_retire_if` | Retire packet stream consumed by the differential harness. |

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Cells are covered. | Met. |
| Capabilities and tags are covered. | Met. |
| CSRs and decoded opcodes are covered. | Met. |
| Fault packets and retire packets are covered. | Met. |
| Instruction-memory, data-memory, and tag-memory ports are covered. | Met. |

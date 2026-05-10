# FPGA Monitor Command Profile

Story: I32-S01

Status: Interactive monitor command and transport profile defined

Structured gate:

```text
python tools\fpga_monitor_profile.py --check
```

List commands:

```text
python tools\fpga_monitor_profile.py --commands
```

Audit a command shape:

```text
python tools\fpga_monitor_profile.py --audit-command WRITE_MEMORY --target-memory data_ram --cell-count 1
```

## Purpose

I32-S01 defines the host-visible command and transport contract for the later
interactive board monitor. It does not implement ROM firmware or change RTL.
I32-S02 consumes this profile for the ROM monitor/trap shell, I32-S03 uses it
for multi-program sessions, and I32-S04 extends `READ_STATUS` and
`READ_MEMORY` into replayable debug snapshots.

Required upstream gates:

```text
python tools\fpga_program_loader.py --check
python tools\fpga_soc_loader_handoff.py --check
```

## Transports

| Transport | Status | Rules |
| --- | --- | --- |
| `uart_mmio_monitor` | Primary interactive transport after UART ownership is handed to monitor firmware. | Uses a length-prefixed or COBS-like binary frame over I27-S02 UART bytes; RX overrun or CRC failure aborts before state changes. |
| `jtag_assisted_monitor` | Reserved until board bridge evidence exists. | Uses the same command payload, status codes, memory policy, and synchronization boundary as UART. |

## Frame Rules

Each request carries:

```text
magic protocol_version sequence opcode payload_length payload crc32
```

Each response echoes `sequence` and `opcode`, carries `status_code`, and adds a
command-specific payload. Frame parse, CRC, unsupported transport, and bounds
failures return a status before mutating state. Commands that mutate memory
require the monitor to be halted.

## Commands

| Command | Opcode | Request | Response | Halted? | Policy |
| --- | --- | --- | --- | --- | --- |
| `HELLO` | `0x01` | `protocol_version`, `host_nonce` | `protocol_version`, `build_id`, `capabilities`, `status_code` | No | Establish protocol version. |
| `HALT` | `0x02` | `reason`, `timeout_cycles` | `halt_state`, `status_packet`, `status_code` | No | Enter safe monitor halt or trap-shell idle state. |
| `RESUME` | `0x03` | `resume_mode`, `entry_cell` | `running_state`, `status_code` | Yes | Resume only from halted monitor state. |
| `LOAD_IMAGE` | `0x04` | `program_id`, `manifest_image_sha256`, `ram_image_sha256`, `cell_count` | `loader_status`, `loaded_cells`, `status_packet`, `status_code` | Yes | Delegates bounded `data_ram` installation to I26-S04 and I30-S04. |
| `READ_STATUS` | `0x05` | `selector` | `status_packet`, `loader_status`, `monitor_state`, `status_code` | No | Reads status/debug records only. |
| `READ_MEMORY` | `0x06` | `target_memory`, `base_cell`, `cell_count` | `payload_cells`, `status_code` | Yes | Reads bounded `instruction_rom` or `data_ram` cells; tag sidecar provenance is not exposed here. |
| `WRITE_MEMORY` | `0x07` | `target_memory`, `base_cell`, `payload_cells`, `tag_bits_all_zero` | `written_cells`, `status_code` | Yes | Writes only bounded untagged `data_ram` cells through the loader policy. |

## Memory Policy

`READ_MEMORY` may read bounded `instruction_rom` and `data_ram` cells while the
monitor is halted. `WRITE_MEMORY` may write only the I26-S04 `data_ram` window,
uses the same 16-cell transfer bound as the loader, and requires
`tag_bits_all_zero`. Host commands cannot create valid tags. `instruction_rom`,
`tag_ram`, MMIO, and status registers are write-protected.

## Status Codes

| Code | Name | Meaning |
| --- | --- | --- |
| `0x0000` | `OK` | Command accepted. |
| `0x3201` | `BAD_COMMAND` | Opcode or command name is unknown. |
| `0x3202` | `BAD_LENGTH` | Payload length or cell count is invalid. |
| `0x3203` | `UNSUPPORTED_TRANSPORT` | Command is not allowed on the selected transport. |
| `0x3204` | `NOT_HALTED` | Command requires the monitor to be halted. |
| `0x3205` | `BUSY` | A prior command is still active. |
| `0x3206` | `BAD_ADDRESS` | Read address or memory target is not allowed. |
| `0x3207` | `WRITE_PROTECTED` | Write target is protected. |
| `0x3208` | `TAG_POLICY` | Write or load request attempts to create valid tags. |
| `0x3209` | `LOADER_ERROR` | I26-S04 loader rejected the image or target. |
| `0x320A` | `TIMEOUT` | Halt, frame, or transport operation timed out. |

The loader still reports detailed I26-S04 status codes such as `BAD_HASH` and
`TAG_POLICY` in the command payload. The monitor `status_code` reports the
outer command result.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| UART or JTAG transports are defined. | Met by `uart_mmio_monitor` and `jtag_assisted_monitor`. |
| `HELLO`, `HALT`, `RESUME`, `LOAD_IMAGE`, `READ_STATUS`, `READ_MEMORY`, and `WRITE_MEMORY` are covered. | Met by the command table and CLI command list. |
| Write-memory is bounded to allowed targets. | Met by the `data_ram`-only write policy and `tag_bits_all_zero` requirement. |
| Error/status codes are defined. | Met by the monitor status-code table. |
| I26-S04 and I30-S04 are used directly. | Met by required upstream gates and loader handoff references. |
| Firmware and debug-snapshot handoffs are explicit. | Met by I32-S02, I32-S03, and I32-S04 handoff notes. |

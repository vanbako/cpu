# FPGA Monitor Debug Snapshot

Story: I32-S04

Status: Debug snapshot and replay handoff fixture defined

Structured gate:

```text
python tools\fpga_monitor_snapshot.py --check
```

Capture the modeled snapshot:

```text
python tools\fpga_monitor_snapshot.py --snapshot
```

## Purpose

I32-S04 defines the monitor-side debug snapshot shape for interactive sessions.
It combines the I32-S02 monitor firmware state, the I09-S04 halted-core debug
ABI, and the I25-S04 replay mapper. The snapshot captures registers, CSR and
CCSR state, PC/slot, a read-only memory window, the 32-byte status packet, and
the nearest `replay_command` without enabling tag forgery.

Required gates:

```text
python tools\fpga_monitor_firmware.py --check
python -m unittest tests.conformance.test_i09_s04_debug_abi
python tools\fpga_replay_mapper.py --check
```

## Captured State

The fixture captures direct register state only while the core lifecycle is
`DEBUG_HALTED`.

| Class | Samples | Notes |
| --- | --- | --- |
| Integer registers | `D0`, `D1`, `D2`, `D3` | Scalar payload only. |
| General capability registers | `C0`, `C1` | Existing tag bits are reported; the snapshot path is read-only. |
| CCSR registers | `PCC`, `EPCC`, `TVC`, `RSC` | `PCC` and `EPCC` include hidden slot state. |
| Scalar CSR registers | `SR`, `CAUSE`, `TVAL`, `DEBUGCTL` | Scalar payload only, no tag or slot fields. |
| Memory window | `data_ram[0:4]` | Payload cells only; `tag_bits_exposed_to_host` is false. |

The memory window is read through the monitor `READ_MEMORY` policy. It does not
expose `tag_ram` as writable host data and does not issue `WRITE_MEMORY`.

## Replay Handoff

The snapshot preserves:

- decoded status packet fields
- original status packet hex
- I25-S04 ranked mapping diagnostics
- top replay case ID
- `replay_command`
- observed-trace comparison command

The default fixture intentionally records a monitor `BAD_COMMAND` status packet
after loading a bounded image. Because the monitor is halted and idle when the
packet is sampled, the nearest replay signature starts at
`core.shell.reset_idle`; the ranked diagnostics still preserve the packet hex
and observed-trace comparison command for triage.

## Tag Policy

The snapshot may report existing capability and CCSR tag bits, but it cannot
create tags:

- all register samples are `writable_by_snapshot=false`
- the memory window is `writable_by_snapshot=false`
- `tag_bits_exposed_to_host=false`
- memory tag bits before and after the snapshot are identical
- no `WRITE_MEMORY` commands are issued

This preserves the I15-S02 tag-integrity rule while still giving the host enough
state to decide whether I32-S04 should hand the failure to replay.

## Handoffs

- I32-S05 can attach this snapshot shape to each interactive corpus case.
- I32-S06 can archive packet hex, replay command, and memory/register samples
  with board evidence.
- Future monitor transports must preserve the no-tag-forgery tag policy in this
  profile.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Register, CSR, and CCSR state are captured. | Met by integer, capability, CCSR, and scalar CSR samples. |
| PC and slot are captured. | Met by `PCC` and top-level `pc_cell`/`pc_slot`. |
| A memory window is captured. | Met by the read-only `data_ram` window. |
| Status packet and nearest replay command are captured. | Met by packet hex plus I25-S04 `replay_command` and compare command. |
| Tag forgery is not enabled. | Met by read-only samples, unchanged tag bits, no `WRITE_MEMORY`, and `tag_bits_exposed_to_host=false`. |

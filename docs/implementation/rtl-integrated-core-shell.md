# RTL Integrated Core Shell

Story: I22-S01

Status: Draft RTL shell implementation

This story starts I22 by creating the integrated `cpu_v01_core` top-level
boundary. The shell is intentionally idle: it does not fetch, decode, execute,
or retire instructions yet. It fixes the final port names and reset/debug
observation surface that later I22 stories will fill in.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Shared cell, capability, fault, and retire packet types. |
| `rtl/cpu_v01_core.sv` | Integrated single-core top-level shell with instruction-memory, data-memory, tag-memory, event/debug, and retire ports. |
| `rtl/cpu_v01_core_shell_tb.sv` | No-program smoke testbench that checks reset PCC/SR observation and deterministic idle request/retire behavior. |

## Local Commands

Validate the source and port projection:

```text
python tools\rtl_core_shell.py --check
```

Print the port projection:

```text
python tools\rtl_core_shell.py --json
```

The Verilator fixture command for this no-program shell is:

```text
verilator --binary --timing --top-module cpu_v01_core_shell_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_shell_tb.sv
```

## Port Boundary

The shell exposes the CPU-owned top-level boundary:

- active-low reset and clock;
- instruction fetch request/response signals matching the I20-S03
  `cpu_v01_imem_if` contract;
- data payload request/response signals matching `cpu_v01_dmem_if`;
- capability tag sidecar request/response signals matching
  `cpu_v01_tagmem_if`;
- timer, software, external interrupt, external event, and debug halt inputs;
- retire valid/ready plus `retire_packet_t`;
- debug observation for idle state, reset completion, reset `PCC`, reset slot,
  reset `SR`, and next retire sequence.

With `ENABLE_FETCH=0`, the I22-S01 no-program shell keeps every request valid
low, every response ready low, and every retire packet invalid. `imem_req_addr`
mirrors the reset `PCC.cursor` so the fetch story can begin without renaming the
port.

## Reset Observation

The boot-core reset observation is:

- `PCC.tag = 1`;
- `PCC.cursor = RESET_VECTOR`;
- `PCC.otype = 0`;
- `PCC.permissions = EX`;
- `PCC.flags = G`;
- `PCC.slot = 0`;
- `SR = 0x0000_0000_00C0`;
- retire sequence `0`.

The shell does not model secondary cores. Multicore lifecycle remains outside
the single-core I22 implementation path.

## Deferred From This Story

- I22-S02 owns instruction fetch, 12/24/48-bit decode, placement faults, and
  illegal-instruction faults.
- I22-S03 through I22-S07 own execution, memory/tag, trap, MMU/TLB, atomic,
  fence, and cache-maintenance behavior.
- I22-S08 owns promotion of observed `cpu_v01_core` retire traces into the
  Verilator regression gate.
- Multicore execution, coherent interconnect, and point-to-point fabric packet
  topology remain out of scope for this CPU repository story.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `cpu_v01_core` exposes stable clock/reset, memory, tag, event/debug, and retire ports. | Met. |
| Reset `PCC`, slot, `SR`, and next retire sequence are visible for smoke checks. | Met. |
| No-program shell behavior is deterministic and idle. | Met. |
| Later fetch/decode work can begin without renaming the top-level boundary. | Met. |

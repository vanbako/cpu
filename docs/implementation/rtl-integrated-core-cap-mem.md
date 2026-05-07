# RTL Integrated Core Capability Memory

Story: I22-S04

Status: Draft integrated RTL memory implementation

This story moves the I20-S06 capability derivation and memory/tag behavior into
the live `cpu_v01_core` fetch/decode path. The top-level core now executes
representative capability register operations, drives the data-memory port for
`LD48`, `ST48`, `CLC`, and `CSC`, and drives the tag-memory port for capability
loads/stores and integer-store tag clears.

I22-S05 still owns trap, syscall, protected call, and return effects.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Provides shared capability, memory, tag, exception, and retire-packet fields. |
| `rtl/cpu_v01_core.sv` | Adds memory-pending states, capability derivation helpers, capability access checks, data-memory requests, tag-memory requests, and deferred memory retire packets. |
| `rtl/cpu_v01_core_cap_mem_tb.sv` | Verilator-oriented fixture for `CMOVE`, `CGETADDR`, `CSETADDR`, `CANDPERM`, `CSC`, `CLC`, `ST48`, `LD48`, and invalid-tag `CSETADDR`. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_cap_mem.py --check
```

Print the integrated capability/memory coverage projection:

```text
python tools\rtl_core_cap_mem.py --json
```

The Verilator source check for this story is:

```text
verilator --lint-only --timing --top-module cpu_v01_core_cap_mem_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_cap_mem_tb.sv
```

## Implemented Behavior

- `CMOVE` copies a capability payload and tag through the integrated capability
  register file.
- `CGETADDR` writes a capability cursor to an integer register.
- `CSETADDR` derives a new cursor after valid, unsealed, in-bounds checks.
- `CANDPERM` masks permissions without widening authority.
- `CSC` writes capability payload cells through the data-memory port and writes
  the architectural tag through the tag-memory port.
- `CLC` reads payload cells through the data-memory port, reads the tag through
  the tag-memory port, and retires a capability write.
- `ST48` writes two integer cells through the data-memory port and clears the
  overlapped capability slot tag through the tag-memory port.
- `LD48` reads two data cells through the data-memory port and retires an
  integer write.
- Invalid source tag on `CSETADDR` retires `CAPABILITY_TAG_FAULT` with
  `CAPCAUSE=TAG` and no destination capability write.

## Fixture Diagnostics

`cpu_v01_core_cap_mem_tb` checks first-observable retire effects for each class,
including `ST_MEM_DREQ`/tag-memory ordering, capability writeback, memory-effect
packets, tag writes, and invalid-tag fault suppression.

## Deferred From This Story

- Trap, syscall, protected call, and return effects: I22-S05.
- MMU/TLB translation and page-walk faults: I22-S06.
- LL/SC, fences, and cache maintenance: I22-S07.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Capability derivation retires through the top-level pipeline. | Met for the I22-S04 representative subset. |
| `LD48`, `ST48`, `CLC`, and `CSC` use the top-level data port. | Met. |
| Capability tag loads, stores, and integer-store clears use the tag-memory port. | Met. |
| Tag non-forgery is represented in retire effects. | Met for `CSC` preserve and `ST48` clear cases. |
| Faulting capability derivation has no partial architectural effect. | Met for invalid-tag `CSETADDR`. |

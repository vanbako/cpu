# Debugger ABI Supplement

Story: I09-S04

Status: Draft implementation profile

Owner sources:

- E05-S04 defines protected return-stack storage and debug unwind constraints.
- E12-S01 and E12-S03 define debug halt, monitor, resume, and single-step state.
- E15-S06 records the software-facing debug and unwind contract.

## Direct Register Access

Direct debug-transport register access is only valid while the core is in `DEBUG_HALTED`. A `DEBUG_MONITOR` executes as privileged software and accesses architectural state through the ordinary privileged instruction paths instead of the direct halted-core register view.

The halted-core debug view exposes:

- `D0-D15` as 48-bit integer payload registers with no tags;
- `C0-C7` as capability payload plus tag;
- `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC` as special capability payload plus tag;
- hidden slot state for `PCC` and `EPCC`;
- assigned scalar CSRs, with `COREID` and `TIMER` treated as read-only presentation fields.

Changing `DEBUGCTL` through the debug view follows the same side-effect rules as the modeled debug-control path.

## Protected Return-Stack Unwind

Debugger unwind operations are precise halted-boundary operations. They do not expose protected return-stack storage to ordinary load/store instructions.

The mandatory abstract operations are:

| Operation | Effect |
| --- | --- |
| `PEEK` | Read and validate the current sealed return capability without changing `RSC.cursor`. |
| `DROP` | Validate the current sealed return capability and advance `RSC.cursor` by one 4-cell return slot. |
| `REPLACE` | Atomically replace the current return slot with one valid sealed `OTYPE_RETURN` capability payload plus tag. |

All protected return-stack entries are one naturally aligned 4-cell capability slot. Replacement must update payload and tag together; integer stores are not a valid debug unwind mechanism.

# RTL Integrated Core Control Trap

Story: I22-S05

Status: Draft integrated RTL control/trap implementation

This story promotes the I21-S04 control-transfer, syscall, and protected
return-stack slice into the live `cpu_v01_core` fetch/decode path. The top-level
core now retires representative `CALL`, `CALLC`, `RET`, `SYS`/`SCALL`, and
`IRET` behavior through one architectural retire packet stream.

I22-S06 still owns MMU, TLB, page-walk, and translation-fault integration.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Provides shared opcode, exception, capability, CCSR, trap-frame, and retire-packet fields. |
| `rtl/cpu_v01_core.sv` | Adds protected return-slot state, return capability helpers, `CALL`/`CALLC` return-stack push, protected `RET`, syscall trap entry, and `IRET` frame restore. |
| `rtl/cpu_v01_core_control_trap_tb.sv` | Verilator-oriented fixture for direct `CALL`, `CALLC`, protected `RET`, `SYS`, `IRET`, invalid `CALLC`, and `RETURN_STACK_UNDERFLOW`. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_control_trap.py --check
```

Print the integrated control/trap coverage projection:

```text
python tools\rtl_core_control_trap.py --json
```

The Verilator source check for this story is:

```text
verilator --lint-only --timing --top-module cpu_v01_core_control_trap_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_control_trap_tb.sv
```

## Implemented Behavior

- `CALL` writes a return capability into the integrated protected return-stack
  slot model, retires `MEM_EFFECT_RETURN_STACK_PUSH`, updates `RSC`, and
  redirects `PCC` to the direct call target.
- `CALLC` validates the source capability tag, pushes the protected return
  capability, unseals the entry capability, and redirects `PCC` to the entry.
- Invalid `CALLC` source tags retire `CAPABILITY_TAG_FAULT` with the source
  capability index and no protected-stack write.
- Protected `RET` restores `PCC` from the saved return capability and advances
  `RSC`; an empty protected return slot retires `RETURN_STACK_UNDERFLOW`.
- `SYS` and its architectural alias `SCALL` retire `SYSCALL_TRAP`, save `EPCC`
  and `SR` in the trap-frame fields, and redirect to `TVC`.
- `IRET` retires `trap-frame` restore metadata and redirects to the saved
  `EPCC` cursor and slot.

## Fixture Diagnostics

`cpu_v01_core_control_trap_tb` checks first-observable retire effects for direct
`CALL`/`RET`, `CALLC`/`RET`, `SYS`/`IRET`, invalid `CALLC`, and protected-return
underflow. The fixture keeps data-memory and tag-memory ports idle because this
story validates the integrated retire effects, not the future memory-backed
protected-stack implementation.

## Deferred From This Story

- Memory-backed protected return-stack load/store sequencing and permission
  checks beyond the integrated retire packet model.
- MMU/TLB translation and page-walk faults: I22-S06.
- LL/SC, fences, and cache maintenance: I22-S07.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Direct calls and protected capability calls redirect through `cpu_v01_core`. | Met for representative `CALL` and `CALLC` cases. |
| Protected returns restore a saved return capability or fault precisely. | Met for pop success and `RETURN_STACK_UNDERFLOW`. |
| Syscall trap entry saves the trap frame and redirects to `TVC`. | Met for `SYS`; `SCALL` remains the same architectural opcode projection. |
| `IRET` restores `EPCC` slot-aware control flow. | Met. |
| Faulting protected-call and protected-return paths suppress normal retire effects. | Met for invalid `CALLC` tag and empty return-stack cases. |

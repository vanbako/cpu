# RTL Control/Trap Slice

Story: I21-S04

Status: Implemented deterministic RTL slice

## Scope

This slice expands the fixture RTL surface for protected control transfer and
syscall return paths. It covers:

- `CALLC` sealed-entry dispatch with protected return-stack push.
- `CALLC` entry capability tag fault reporting.
- `RET` protected return-stack pop and `RETURN_STACK_UNDERFLOW`/permission
  fault reporting.
- `SYS` and `SCALL` trap entry using the same opcode selector.
- syscall trap-frame save/restore metadata.
- `IRET` back to user mode at the saved slot-1 return point.

## Artifacts

- `rtl/cpu_v01_control_trap_core.sv`
- `rtl/cpu_v01_control_trap_tb.sv`
- `src/cpu_v01/rtl_control_trap.py`
- `tools/rtl_control_trap_slice.py`
- `tests/conformance/test_i21_s04_rtl_control_trap.py`

## Validation

```text
python tools\rtl_control_trap_slice.py --check
python -m unittest tests.conformance.test_i21_s04_rtl_control_trap
```

The projection derives CALLC, RET, SYS/SCALL, syscall return, and IRET rows
from the semantic helpers for call/return and the user/kernel syscall demo. The
SystemVerilog core is intentionally a deterministic smoke slice rather than an
integrated decoder or pipeline.

## Deferrals

`WFI`, interrupt delivery, debug monitor entry, nested trap replay timing, and
integrated fetch/decode/issue hazards remain for later stories.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CALLC` entry call and entry-tag fault are represented. | Met. |
| `RET` protected pop and protected pop faults are represented. | Met. |
| `SYS` and `SCALL` trap-frame save paths are represented. | Met. |
| Syscall frame restore and scalar/capability return values are represented. | Met. |
| `IRET` returns to user mode at the saved slot. | Met. |

# RTL Fault Trap Slice

Story: I20-S07

Status: Draft RTL smoke implementation

The third SystemVerilog slice extends the deterministic RTL smoke surface with
precise fault, direct trap-entry, `IRET`, and protected return-stack gates. It
is still a bounded single-core fixture, not a full CPU pipeline. Full decode,
interrupt priority, debug entry, atomics, TLBs, caches, MMIO, DMA, and
secondary cores remain deferred.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds fault/trap/control opcode constants plus CSR, CCSR, PCC, EPCC, trap-entry, and return-stack retire packet fields. |
| `rtl/cpu_v01_fault_trap_core.sv` | Deterministic fault/trap slice for `DIV`, `SYS`, `IRET`, `CALL`, and `RET` retire effects. |
| `rtl/cpu_v01_fault_trap_tb.sv` | Verilator-oriented smoke testbench for final fault, trap, return-stack, and control-transfer observations. |

## Local Commands

Validate the source/golden projection boundary:

```text
python tools\rtl_fault_trap_slice.py --check
```

Print the packet projection:

```text
python tools\rtl_fault_trap_slice.py --json
```

The projection is derived from these golden corpus cases:

- `fault_cases.divide_by_zero`;
- `traps.sys_to_tvc`;
- `traps.sys_iret_return`;
- `calls_returns.direct_call_ret`.

## Covered Behavior

- `DIV` divide-by-zero produces `DIVIDE_BY_ZERO` without normal effects.
- `SYS` produces `SYSCALL_TRAP` and marks direct TVC trap entry.
- `IRET` restores `PCC` from `EPCC` and writes `SR`.
- `CALL` writes a sealed local return capability at the protected return-stack
  slot, updates `RSC`, and redirects `PCC`.
- `RET` restores the return target and updates `RSC`, covering the paired
  golden packet from `calls_returns.direct_call_ret`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| RTL passes golden cases for fault packets. | Met. |
| RTL covers no-normal-effect faults. | Met. |
| RTL covers direct trap entry. | Met. |
| RTL covers `IRET`. | Met. |
| RTL covers direct `CALL` and protected return-stack push. | Met. |
| RTL covers all-or-nothing commit visibility for fault versus normal effects. | Met. |

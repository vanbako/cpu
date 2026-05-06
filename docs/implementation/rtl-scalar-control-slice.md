# RTL Scalar Control Slice

Story: I21-S01

Status: Draft RTL coverage implementation

This slice expands the deterministic SystemVerilog RTL surface to the scalar
integer ALU family, direct branch/control forms, scalar CSR operations, and
capability CSR operations that do not require MMU, atomics, cache maintenance,
interrupt wait, or external fabric behavior. It remains a bounded fixture, not
an integrated `cpu_v01_core`.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Adds scalar integer, branch/control, CSR, and CCSR opcode constants plus the `BREAKPOINT` exception constant and full fast CSR/CCSR names used by the slice. |
| `rtl/cpu_v01_scalar_control_core.sv` | Deterministic retire-packet fixture for integer writes, SR flag writes, branch PCC updates, `EPCCRD`, `EPCCWR`, `PAUSE`, `BRK`, CSR, and CCSR effects. |
| `rtl/cpu_v01_scalar_control_tb.sv` | Verilator-oriented smoke testbench for final scalar, branch/control, CSR, CCSR, pause, and breakpoint observations. |

## Local Commands

Validate the source and coverage projection boundary:

```text
python tools\rtl_scalar_control_slice.py --check
```

Print the coverage projection:

```text
python tools\rtl_scalar_control_slice.py --json
```

The Verilator fixture command for this bounded slice is:

```text
verilator --binary --timing --top-module cpu_v01_scalar_control_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_scalar_control_core.sv rtl/cpu_v01_scalar_control_tb.sv
```

## Covered Behavior

- Mandatory scalar integer mnemonics from `CPY` through `BCLR`, including
  normal `MUL`, `DIV`, `MOD`, shifts, rotates, flag writes, `SETCC`, and
  `CMOVCC`.
- Direct `BRA`, taken and not-taken `BCC`, `JMP`, `EPCCRD`, `EPCCWR`, `PAUSE`,
  and `BRK` retire effects.
- Scalar CSR `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR` for both 24-bit fast and
  48-bit extended forms.
- Capability CSR `CCSRRD` and `CCSRWR` 48-bit forms with tag-preserving
  capability write visibility.

## Deferred From This Slice

`CALL`, `RET`, `SYS`, and `IRET` stay covered by the I20-S07 fault/trap slice.
`WFI`, `CALLC`, `LL48`, `SC48`, fences, `SFENCE.*`, cache maintenance, MMU/TLB
effects, and external fabric behavior remain for later I21 stories.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Remaining mandatory scalar integer forms have RTL coverage tokens and a projection row. | Met. |
| Branch/control forms in scope cover direct PCC, EPCC, pause, and breakpoint effects. | Met. |
| CSR and CCSR forms cover 24-bit/48-bit scalar CSR and 48-bit CCSR retire effects. | Met. |
| MMU, atomic, cache-maintenance, interrupt-wait, and external-fabric behavior remain out of scope. | Met. |
| Local validation command is documented. | Met. |

# RTL Integrated Core Scalar Control

Story: I22-S03

Status: Draft integrated RTL execution implementation

This story moves the I21-S01 scalar/control retire effects into the live
`cpu_v01_core` fetch/decode path. The top-level core now owns integer register
state, capability register state, scalar CSR state, selected special CCSR
state, branch redirects, `EPCCRD`/`EPCCWR`, `PAUSE`, and no-effect `BRK`
fault retirement.

I22-S04 still owns capability derivation, data-memory operations, and tag-memory
effects.

## RTL Sources

| Source | Purpose |
| --- | --- |
| `rtl/cpu_v01_pkg.sv` | Provides the shared opcode, CSR, CCSR, exception, and retire-packet contract. |
| `rtl/cpu_v01_core.sv` | Adds architectural scalar/control state, `execute_decoded_packet`, register/CSR/CCSR commit helpers, branch redirect effects, EPCC effects, and no-effect decoded faults. |
| `rtl/cpu_v01_core_scalar_control_tb.sv` | Verilator-oriented fixture for golden scalar arithmetic, condition-code CSR writes, taken and not-taken control flow, fast and long CSR forms, CCSR forms, EPCC forms, `PAUSE`, and `BRK`. |

## Local Commands

Validate the source and coverage projection:

```text
python tools\rtl_core_scalar_control.py --check
```

Print the integrated scalar/control coverage projection:

```text
python tools\rtl_core_scalar_control.py --json
```

The Verilator source check for this story is:

```text
verilator --lint-only --timing --top-module cpu_v01_core_scalar_control_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_core_scalar_control_tb.sv
```

## Implemented Behavior

- `CSRRD D1, SR` reads the reset status register through the integrated core
  CSR file and retires an `integer_write`.
- `ADD D2, D1, D1` executes through the top-level integer register file.
- `CMP D2, D1` retires a `csr_write` to `SR`, giving later conditional branches
  real condition-code input.
- `BCC` not taken retires normally without `redirect` or `pcc_update`; `BRA`
  retires with both `redirect` and `pcc_update`.
- Fast and long `CSRRD`/`CSRWR` forms share the same CSR file.
- `EPCCRD` retires a capability write plus integer slot write; `EPCCWR` retires
  an `epcc_update`.
- `CCSRWR` retires a `ccsr_write` for selected special capability CSR state and `CCSRRD` reads it
  back through the capability register file.
- `PAUSE` retires normally with no register, CSR, CCSR, memory, tag, trap,
  reservation, fence, or cache effect.
- `BRK` retires `BREAKPOINT` as a decoded no-effect fault and does not advance
  the architectural `PCC`.

## Fixture Diagnostics

`cpu_v01_core_scalar_control_tb` checks fields at the first retire packet where
a mismatch can be observed, so failures name the broken effect class such as
`ADD`, `CSRWR.L`, `BRA redirect`, `EPCCWR`, `CCSRWR`, or `BRK fault`.

## Deferred From This Story

- Capability derivation and data/tag memory effects: I22-S04.
- Trap, syscall, protected call, and return effects: I22-S05.
- MMU/TLB translation: I22-S06.
- LL/SC, fences, and cache maintenance: I22-S07.
- Promotion of observed `cpu_v01_core` traces to the Verilator regression gate:
  I22-S08.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Golden scalar/control programs retire through the top-level pipeline. | Met for the I22-S03 scalar/control subset. |
| Register, CSR, and CCSR writes are emitted from `cpu_v01_core`. | Met. |
| Branch redirects and not-taken control flow are explicit retire effects. | Met. |
| `EPCCRD`, `EPCCWR`, `PAUSE`, and `BRK` are covered. | Met. |
| Faulting scalar/control instructions have no partial architectural effects. | Met for `BRK` and divide-by-zero execution paths. |

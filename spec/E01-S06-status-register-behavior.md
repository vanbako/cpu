# E01-S06: Status Register Behavior

Story: E01-S06

Status: Complete

Normative source: `design.md`, sections 3.5, 10.3, and 10.5

Prerequisite: `spec/E01-S02-integer-register-semantics.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`

## Decision

CPU v0.1 has one 48-bit scalar status register, `SR`.

`SR` contains condition flags, interrupt state, privilege state, trap nesting state, and a read-only mirror of the current instruction slot.

## Bit Layout

| Bit | Name | Access | Meaning |
| ---: | --- | --- | --- |
| 0 | `Z` | RW | Zero flag. |
| 1 | `N` | RW | Negative flag. |
| 2 | `C` | RW | Carry / no-borrow flag. |
| 3 | `V` | RW | Signed overflow flag. |
| 4 | `IE` | RW | Current interrupt enable. |
| 5 | `PIE` | RW | Previous interrupt enable. |
| 6 | `PRIV` | RW | Current privilege: `0=U`, `1=K`. |
| 7 | `PPRIV` | RW | Previous privilege: `0=U`, `1=K`. |
| 8 | `EXL` | RW | Exception level / in-trap state. |
| 9 | `SLOT` | RO | Current instruction slot mirror: `0=slot 0`, `1=slot 1`. |
| 47:10 | `RES0` | RZ/W0 | Reserved, reads as zero, writes must be zero. |

`PPRIV` is the explicit previous-privilege field required for trap return. It corresponds to the previous privilege state referenced by the trap model.

## Condition Flags

Condition flags are:

| Flag | Meaning |
| --- | --- |
| `Z` | Last explicit flag result was zero. |
| `N` | Most significant bit of the last explicit flag result was one. |
| `C` | Carry out for addition, no borrow for subtraction/compare, or instruction-defined carry. |
| `V` | Signed two's-complement overflow for addition/subtraction, or instruction-defined overflow. |

Condition flags are architectural state. They are not tied to any integer register.

## Flag Update Sources

Ordinary arithmetic, logic, move, shift, rotate, and bit-manipulation instructions do not update `Z`, `N`, `C`, or `V` implicitly.

Flags are updated only by:

- `CMP`
- `CMPU`
- `TST`
- Explicit flag-setting instruction forms, if later ISA stories define them
- Explicit privileged writes to `SR`, subject to CSR rules

Instructions that do not explicitly update flags leave all four condition flags unchanged.

Faulting flag-setting instructions leave all four condition flags unchanged unless a later instruction story explicitly defines an earlier committed side effect.

## `CMP` and `CMPU`

`CMP` and `CMPU` compare two operands by computing a subtraction in the selected operation width:

```text
diff = lhs - rhs
```

For a selected width `W`:

- `Z = 1` when `diff[W-1:0] == 0`, otherwise `0`.
- `N = diff[W-1]`.
- `C = 1` when the subtraction does not borrow, otherwise `0`.
- `V = 1` when signed subtraction overflows in width `W`, otherwise `0`.

`CMP` and `CMPU` use the same flag calculations. Signed and unsigned condition-code consumers interpret the resulting flags differently.

`CMP` and `CMPU` do not write an integer destination register.

## `TST`

`TST` tests bits by computing a bitwise AND in the selected operation width:

```text
test = lhs & rhs
```

For a selected width `W`:

- `Z = 1` when `test[W-1:0] == 0`, otherwise `0`.
- `N = test[W-1]`.
- `C = 0`.
- `V = 0`.

`TST` does not write an integer destination register.

## Explicit Flag-setting Forms

Later ISA stories may define flag-setting arithmetic or logic forms.

Required behavior:

- The instruction name or encoding must make flag setting explicit.
- The flag formulas must be specified by the instruction story.
- Non-flag-setting forms of the same operation must leave flags unchanged.

This keeps flag dependencies visible to compilers, simulators, and RTL scheduling.

## Interrupt and Trap State

`IE` enables maskable interrupt delivery when set to `1`.

`PIE` stores the previous interrupt-enable value during trap entry.

`PRIV` records the current privilege mode:

| Value | Mode |
| ---: | --- |
| 0 | User (`U`) |
| 1 | Kernel (`K`) |

`PPRIV` stores the previous privilege mode during trap entry.

`EXL=1` means the core is architecturally in exception level. While `EXL=1`, ordinary maskable interrupt delivery is disabled unless a later interrupt story defines a software-managed re-enable sequence.

Baseline trap entry updates:

```text
PIE   = IE
IE    = 0
PPRIV = PRIV
PRIV  = 1
EXL   = 1
SLOT  = 0
```

`EPCC` captures the interrupted or faulting `PCC` and slot according to E01-S04 and E01-S05.

Baseline trap return through `IRET` updates:

```text
IE   = PIE
PRIV = PPRIV
EXL  = 0
SLOT = EPCC.slot
```

The detailed direct-exception, vectored-interrupt, and nested-interrupt rules are defined by E07-S04, E07-S05, and E07-S06. Those stories may refine priority and exact sequencing, but must preserve the one-level `IE`/`PIE` and `PRIV`/`PPRIV` state model.

## Slot Mirror

`SR.SLOT` mirrors the current `PCC` hidden slot bit.

Rules:

- Sequential execution updates `SR.SLOT` with the same slot transitions defined for `PCC`.
- Explicit branches, jumps, calls, returns, traps, and interrupts enter slot 0 and therefore set `SR.SLOT=0`.
- `IRET` restores `SR.SLOT` from the slot captured in `EPCC`.
- `SR.SLOT` is read-only through scalar `SR` writes.
- A scalar write that attempts to change `SR.SLOT` raises illegal CSR write and leaves `SR` unchanged.

`SR.SLOT` exists for diagnostics, trap handling, and status inspection. It is not an independent program counter.

## Reset Value

The baseline reset value for `SR` is:

| Field | Reset value |
| --- | --- |
| `Z`, `N`, `C`, `V` | `0` |
| `IE` | `0` |
| `PIE` | `0` |
| `PRIV` | `1` |
| `PPRIV` | `1` |
| `EXL` | `0` |
| `SLOT` | `0` |
| `RES0` | `0` |

E11-S01 refines the full reset-state table. This story fixes the architectural `SR` baseline that reset must implement unless a later story explicitly revises it.

## Reserved-bit Behavior

Bits `47:10` are reserved-zero (`RES0`).

Rules:

- Reads return zero for every `RES0` bit.
- Writes must provide zero for every `RES0` bit.
- A write that attempts to set any `RES0` bit to one raises illegal CSR write.
- A faulting `SR` write leaves all `SR` fields unchanged.
- Future architecture revisions may assign `RES0` bits only with an explicit compatibility rule.

The exact CSR instruction fault code is defined by E02-S04 and the exception story.

## Privilege of Explicit Writes

Explicit writes to `SR` are privileged. User-mode attempts to write `SR` raise privilege violation.

User-mode reads of `SR` are reserved to the CSR access story. E02-S02 defines the final access mode for the mandatory `SR` CSR.

## Out of Scope for This Story

- Scalar CSR numbering and access modes: E02-S01 and E02-S02.
- CSR instruction read/modify/write atomicity: E02-S04.
- Full privilege model and privileged operation list: E07-S01.
- Exception cause table and fault priority: E07-S02.
- Direct trap entry and `IRET` sequencing details: E07-S04.
- Nested interrupt behavior beyond one saved level: E07-S06.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `SR` is 48 bits wide.
- `Z`, `N`, `C`, and `V` are individually readable and writable by privileged `SR` writes.
- Ordinary `ADD`, `SUB`, `AND`, `OR`, and `XOR` do not update flags.
- `CMP` sets `Z` for equal operands.
- `CMP` clears `C` when unsigned subtraction borrows.
- `CMP` sets `V` for signed subtraction overflow.
- `TST` sets `Z` when the bitwise AND result is zero.
- `TST` clears `C` and `V`.
- Trap entry copies `IE` to `PIE`, clears `IE`, copies `PRIV` to `PPRIV`, sets `PRIV=K`, and sets `EXL=1`.
- `IRET` restores `IE` from `PIE`, restores `PRIV` from `PPRIV`, clears `EXL`, and restores `SLOT` from `EPCC`.
- Direct control transfers set `SR.SLOT=0`.
- Fall-through from a slot-0 12-bit instruction sets `SR.SLOT=1`.
- `RES0` bits read as zero.
- Writes setting `RES0` bits raise illegal CSR write and leave `SR` unchanged.
- Writes attempting to change `SLOT` through `SR` raise illegal CSR write and leave `SR` unchanged.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `Z`, `N`, `C`, `V`, `IE`, `PIE`, `PRIV`, `EXL`, and `SLOT` are defined. | Met. |
| Current and previous privilege state are represented. | Met: `PRIV` and `PPRIV`. |
| Arithmetic does not update flags by default. | Met. |
| `CMP`, `TST`, or explicit flag-setting forms are defined as the source of condition flags. | Met. |
| Reserved bits have read and write behavior specified. | Met. |

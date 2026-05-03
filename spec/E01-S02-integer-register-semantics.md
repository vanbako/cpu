# E01-S02: Integer Register Semantics

Story: E01-S02

Status: Complete

Normative source: `design.md`, section 3.1

Prerequisite: `spec/E01-S01-cell-address-model.md`

Related sources:

- `spec/E01-S03-general-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`

## Decision

CPU v0.1 has 16 general integer/data registers:

- `D0`
- `D1`
- `D2`
- `D3`
- `D4`
- `D5`
- `D6`
- `D7`
- `D8`
- `D9`
- `D10`
- `D11`
- `D12`
- `D13`
- `D14`
- `D15`

Each `D` register is a 48-bit architectural register.

There is no hardwired zero register in v0.1. All `D0-D15` registers are writable architectural state.

## Register Role

Integer registers hold ordinary scalar data:

- Integer values.
- Offsets.
- Indexes.
- Sizes and counts.
- System-call arguments.
- Diagnostic values.
- Cell addresses used as data.

Integer registers do not carry capability tags and cannot authorize memory access. An integer value may numerically equal a cell address, but it is not a pointer unless used by an explicit capability instruction that preserves capability authority.

## Supported Operation Widths

Integer instruction forms may operate on these widths:

| Width name | Bits | Notes |
| --- | ---: | --- |
| `W8` | 8 | Sub-cell scalar width. |
| `W12` | 12 | Useful for instruction-field-sized values. |
| `W16` | 16 | Sub-cell scalar width. |
| `W24` | 24 | One cell of data. |
| `W32` | 32 | Conventional scalar width. |
| `W48` | 48 | Full integer register width. |

These widths describe register interpretation and writeback. They do not create byte-addressed or sub-cell-addressed memory.

## Read Semantics

For a width `W`, a narrow source read uses the low `W` bits of the source register:

```text
source_w = source[W-1:0]
```

Instruction signedness controls how the low `W` bits are interpreted for the operation:

- Unsigned forms interpret the source as `0 <= value < 2^W`.
- Signed forms interpret the source as a two's-complement value in the range `-2^(W-1)` to `2^(W-1)-1`.
- Bitwise forms treat the low `W` bits as an uninterpreted bit vector.

Bits above `W-1` in the source register are ignored by a narrow operation unless the instruction explicitly uses a full-width source.

## Write Forms

Narrow write behavior is explicit in the instruction form.

For a computed low-width result `result_w`, the destination write form is one of:

| Write form | Destination result |
| --- | --- |
| Zero-extending | `dest[W-1:0] = result_w`; `dest[47:W] = 0` |
| Sign-extending | `dest[W-1:0] = result_w`; `dest[47:W] = result_w[W-1]` |
| Full-width | `dest[47:0] = result_48` |

For `W48`, zero-extending, sign-extending, and full-width writes all write the same 48 destination bits. Encoders may reserve redundant `W48` extension variants if that simplifies decode.

Narrow writes never preserve old high bits. There is no partial-register merge form in v0.1.

## Arithmetic Result Width

Integer arithmetic results are computed modulo the selected result width unless an instruction explicitly defines a wider result.

Examples:

```text
W8 ADD zero-extending:
  result_w = (src0[7:0] + src1[7:0]) mod 2^8
  dest = zero_extend_48(result_w)

W12 SUB sign-extending:
  result_w = (src0[11:0] - src1[11:0]) mod 2^12
  dest = sign_extend_48(result_w)

W48 ADD full-width:
  dest = (src0 + src1) mod 2^48
```

Multiply, divide, modulo, shifts, rotates, comparisons, and bit operations get their detailed per-instruction rules in E04-S02. This story fixes only the register width and writeback model they must use.

## Flag Behavior

Ordinary arithmetic, logic, move, shift, rotate, and bit-manipulation instructions do not update condition flags implicitly.

Condition flags are updated only by:

- Dedicated compare/test instructions such as `CMP`, `CMPU`, and `TST`.
- Explicit flag-setting instruction forms, if such forms are later defined.

Instructions that do not explicitly set flags must leave `SR.Z`, `SR.N`, `SR.C`, and `SR.V` unchanged.

The exact `SR` flag bit positions and flag-update formulas are defined by E01-S06.

## Illegal or Reserved Width Encodings

Only `W8`, `W12`, `W16`, `W24`, `W32`, and `W48` are valid v0.1 integer operation widths.

Rules:

- Any instruction encoding that selects an unassigned width is reserved.
- Executing a reserved width encoding raises illegal-instruction exception.
- Reserved width encodings must not alias a valid width.
- Future architecture revisions may assign reserved width encodings only with an explicit compatibility rule.

If an instruction supports only a subset of widths, using a valid global width that is not supported by that instruction also raises illegal-instruction exception unless the instruction story defines another fault.

## Fault and Commit Behavior

Integer register writes commit at the architectural retire point.

If an instruction faults before commit:

- Destination integer registers are unchanged.
- Condition flags are unchanged unless the faulting instruction's later story explicitly says flags are committed before that fault.
- Memory and capability state are unchanged except for side effects explicitly defined by the faulting instruction story.

This preserves precise exception behavior for later pipeline and trap stories.

## Out of Scope for This Story

- Exact integer opcode table and operand formats: E04-S02.
- Status-register bit layout and trap-state fields: E01-S06.
- Integer calling convention roles: E05-S01.
- Multiply/divide latency and scoreboard behavior: E13-S02.
- CSR register semantics: E02-S01 and E02-S02.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `D0-D15` are all writable 48-bit registers.
- No `D` register is hardwired to zero.
- `W8`, `W12`, `W16`, `W24`, `W32`, and `W48` are accepted where the instruction supports them.
- Reserved width encodings raise illegal-instruction exception.
- `W8` zero-extending write clears destination bits `[47:8]`.
- `W8` sign-extending write fills destination bits `[47:8]` from bit 7.
- `W24` zero-extending write clears destination bits `[47:24]`.
- `W24` sign-extending write fills destination bits `[47:24]` from bit 23.
- Full-width writes update all 48 bits.
- Narrow writes do not preserve previous high bits.
- Ordinary `ADD`, `SUB`, `AND`, `OR`, and `XOR` forms leave condition flags unchanged.
- `CMP`, `CMPU`, and `TST` update flags without depending on an implicit arithmetic side effect.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Registers `D0-D15` are defined as 48-bit architectural registers. | Met. |
| Supported operation widths are listed as 8, 12, 16, 24, 32, and 48 bits. | Met. |
| Zero-extending, sign-extending, and full-width write forms are specified. | Met. |
| Flag-setting behavior is not implicit for ordinary arithmetic. | Met. |
| Illegal or reserved width encodings are documented. | Met. |

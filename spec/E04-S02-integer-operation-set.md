# E04-S02: Integer Operation Set

Story: E04-S02

Status: Complete

Normative source: `design.md`, section 7.1

Prerequisites:

- `spec/E01-S02-integer-register-semantics.md`
- `spec/E04-S01-instruction-fetch-groups.md`

Related sources:

- `spec/E01-S06-status-register-behavior.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`

## Decision

CPU v0.1 defines the mandatory integer operation set used by compiler, assembler, simulator, and RTL work.

The mandatory integer operations are:

- `CPY`
- `NEG`
- `ADD`
- `ADDU`
- `SUB`
- `SUBU`
- `MUL`
- `MULU`
- `DIV`
- `DIVU`
- `MOD`
- `MODU`
- `NOT`
- `AND`
- `OR`
- `XOR`
- `SHL`
- `SHRS`
- `SHRU`
- `ROL`
- `ROR`
- `CMP`
- `CMPU`
- `TST`
- `SETcc`
- `CMOVcc`
- `BSET`
- `BCLR`

All mandatory integer operations are user-mode instructions. They operate only on `D0-D15`, `SR` condition flags where explicitly stated, and normal `PCC` fall-through state.

They do not read or write capability registers, memory, scalar CSRs other than explicit flag updates for `CMP`, `CMPU`, and `TST`, or special capability registers.

## Common Integer Model

Each result-producing integer instruction, except `SETcc`, selects:

- An operation width `W`.
- A destination write form.

Supported widths are inherited from E01-S02:

| Width name | Bits |
| --- | ---: |
| `W8` | 8 |
| `W12` | 12 |
| `W16` | 16 |
| `W24` | 24 |
| `W32` | 32 |
| `W48` | 48 |

For a selected width `W`:

```text
mask(W) = 2^W - 1
uW(x)   = x[W-1:0]
sW(x)   = two's-complement interpretation of x[W-1:0]
```

Result-producing instructions compute a low-width result `result_w`, then write it according to the selected E01-S02 write form:

| Write form | Result |
| --- | --- |
| Zero-extending | `Dd = zero_extend_48(result_w)` |
| Sign-extending | `Dd = sign_extend_48(result_w)` |
| Full-width | `Dd = result_w` for `W48` |

For `W48`, all write forms write the same 48 bits.

For `W8`, `W12`, `W16`, `W24`, and `W32`, mandatory result-producing E04-S02 forms use either the zero-extending or sign-extending write form. A full-width write form is meaningful only for `W48` in v0.1.

If an instruction names the same register as a source and destination, all source operands are read before the destination write commits.

Faulting integer instructions leave destination registers and condition flags unchanged.

## Encoding Category

This story assigns semantic encoding categories, not final opcode bit positions.

| Operation family | Mandatory canonical category | Notes |
| --- | --- | --- |
| `CPY`, `NEG`, `NOT` | 24-bit | Register unary forms. |
| `ADD`, `ADDU`, `SUB`, `SUBU`, `AND`, `OR`, `XOR` | 24-bit | Register binary forms. |
| `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, `MODU` | 24-bit | Register binary MDU forms; latency is refined by E13-S02. |
| `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR` | 24-bit | Register shift or rotate count forms. |
| `CMP`, `CMPU`, `TST` | 24-bit | Register flag-setting forms with no integer destination. |
| `SETcc` | 24-bit | Condition-code-to-integer form. |
| `CMOVcc` | 24-bit | Conditional register move form. |
| `BSET`, `BCLR` | 24-bit | Register bit-index forms. |

The final opcode story may add 12-bit compact aliases for common register forms. A compact alias must be semantically identical to one of the mandatory 24-bit forms.

The final opcode story may add 48-bit integer-immediate or long-literal forms. No mandatory E04-S02 operation requires a 48-bit form for its register-register baseline.

Malformed encodings, unsupported width encodings, or unsupported operand-class encodings raise `ILLEGAL_INSTRUCTION`.

## Flag Behavior

Ordinary integer operations do not update flags:

- `CPY`
- `NEG`
- `ADD`
- `ADDU`
- `SUB`
- `SUBU`
- `MUL`
- `MULU`
- `DIV`
- `DIVU`
- `MOD`
- `MODU`
- `NOT`
- `AND`
- `OR`
- `XOR`
- `SHL`
- `SHRS`
- `SHRU`
- `ROL`
- `ROR`
- `SETcc`
- `CMOVcc`
- `BSET`
- `BCLR`

Only these E04-S02 instructions update `SR.Z`, `SR.N`, `SR.C`, and `SR.V`:

- `CMP`
- `CMPU`
- `TST`

This preserves the E01-S06 rule that ordinary arithmetic, logic, move, shift, rotate, and bit-manipulation instructions do not create implicit flag dependencies.

## Move, Negate, and Bitwise Unary

### `CPY`

`CPY Dd, Ds` copies the low-width source bits:

```text
result_w = uW(Ds)
```

It then writes `result_w` using the selected write form.

### `NEG`

`NEG Dd, Ds` computes two's-complement negation in the selected width:

```text
result_w = (0 - uW(Ds)) & mask(W)
```

Signed minimum negation wraps to itself. It does not trap.

### `NOT`

`NOT Dd, Ds` computes bitwise complement in the selected width:

```text
result_w = (~uW(Ds)) & mask(W)
```

## Add, Subtract, and Logical Binary

### `ADD` and `ADDU`

`ADD Dd, Da, Db` and `ADDU Dd, Da, Db` compute:

```text
result_w = (uW(Da) + uW(Db)) & mask(W)
```

`ADD` is the signed-intended spelling. `ADDU` is the unsigned-intended spelling. Because v0.1 writes only the low `W` result bits and ordinary arithmetic does not set flags, both have identical architectural writeback for the same operands, width, and write form.

Signed or unsigned overflow wraps modulo `2^W`. Overflow does not trap and does not update `SR.V`.

### `SUB` and `SUBU`

`SUB Dd, Da, Db` and `SUBU Dd, Da, Db` compute:

```text
result_w = (uW(Da) - uW(Db)) & mask(W)
```

`SUB` is the signed-intended spelling. `SUBU` is the unsigned-intended spelling. Both have identical architectural writeback for the same operands, width, and write form.

Signed or unsigned overflow and unsigned borrow wrap modulo `2^W`. They do not trap and do not update flags.

### `AND`, `OR`, and `XOR`

Logical binary operations treat inputs as width-limited bit vectors:

```text
AND: result_w = uW(Da) & uW(Db)
OR:  result_w = uW(Da) | uW(Db)
XOR: result_w = uW(Da) ^ uW(Db)
```

## Multiply

### `MUL`

`MUL Dd, Da, Db` interprets both inputs as signed `W`-bit two's-complement values:

```text
product = sW(Da) * sW(Db)
result_w = product mod 2^W
```

Only the low `W` product bits are written. Signed overflow is truncated modulo `2^W`; it does not trap and does not set flags.

### `MULU`

`MULU Dd, Da, Db` interprets both inputs as unsigned `W`-bit values:

```text
product = uW(Da) * uW(Db)
result_w = product & mask(W)
```

Only the low `W` product bits are written. Unsigned overflow is truncated modulo `2^W`; it does not trap and does not set flags.

E13-S02 owns multiplier latency, pipelining, scoreboard, and bypass behavior. Architecturally, `MUL` and `MULU` retire in program order and expose only their committed destination write.

## Divide and Modulo

### Divide-by-zero

`DIV`, `DIVU`, `MOD`, and `MODU` check the divisor before computing a result.

If `uW(Db) == 0`, the instruction raises `DIVIDE_BY_ZERO`.

On divide-by-zero:

```text
CAUSE       = DIVIDE_BY_ZERO
TVAL        = 0
CAPCAUSE    = NONE
FAULTCAPIDX = NONE
```

The destination register is unchanged, flags are unchanged, and the instruction does not increment `INSTRET`.

### `DIV`

`DIV Dd, Da, Db` performs signed two's-complement division.

For the normal case:

```text
quotient = trunc_toward_zero(sW(Da) / sW(Db))
result_w = quotient mod 2^W
```

Signed overflow is possible only for:

```text
sW(Da) = -2^(W-1)
sW(Db) = -1
```

For that case:

```text
result_w = 2^(W-1)
```

which is the original signed minimum value in two's-complement form. It does not trap.

### `DIVU`

`DIVU Dd, Da, Db` performs unsigned division:

```text
quotient = floor(uW(Da) / uW(Db))
result_w = quotient
```

### `MOD`

`MOD Dd, Da, Db` performs signed two's-complement remainder using the same quotient rule as `DIV`:

```text
quotient = trunc_toward_zero(sW(Da) / sW(Db))
remainder = sW(Da) - quotient * sW(Db)
result_w = remainder mod 2^W
```

The remainder has the same sign as the dividend or is zero.

For signed minimum divided by `-1`:

```text
result_w = 0
```

This case does not trap.

### `MODU`

`MODU Dd, Da, Db` performs unsigned remainder:

```text
result_w = uW(Da) mod uW(Db)
```

E13-S02 owns divider latency, iteration, scoreboard, and bypass behavior. Architecturally, divide and modulo exceptions are precise and are reported at retire according to E07-S03.

## Shifts and Rotates

Shift and rotate counts are read from the low 6 bits of the count register:

```text
count = Db[5:0]
```

The 6-bit count range is sufficient to represent every meaningful shift count for v0.1 widths up to 48.

### `SHL`

`SHL Dd, Da, Db` performs a logical left shift:

```text
if count >= W:
    result_w = 0
else:
    result_w = (uW(Da) << count) & mask(W)
```

### `SHRU`

`SHRU Dd, Da, Db` performs a logical right shift:

```text
if count >= W:
    result_w = 0
else:
    result_w = uW(Da) >> count
```

### `SHRS`

`SHRS Dd, Da, Db` performs an arithmetic right shift:

```text
if count >= W:
    result_w = mask(W) if sW(Da) < 0 else 0
else:
    result_w = (sW(Da) >> count) & mask(W)
```

The right shift of a negative signed value fills vacated high bits with ones.

### `ROL` and `ROR`

Rotates wrap within the selected width:

```text
rot = count mod W
```

`ROL`:

```text
if rot == 0:
    result_w = uW(Da)
else:
    result_w = ((uW(Da) << rot) | (uW(Da) >> (W - rot))) & mask(W)
```

`ROR`:

```text
if rot == 0:
    result_w = uW(Da)
else:
    result_w = ((uW(Da) >> rot) | (uW(Da) << (W - rot))) & mask(W)
```

## Compare and Test

`CMP`, `CMPU`, and `TST` update condition flags and do not write an integer destination register.

They use the selected width `W`.

### `CMP` and `CMPU`

`CMP Da, Db` and `CMPU Da, Db` compute a width-limited subtraction for flags:

```text
lhs = uW(Da)
rhs = uW(Db)
diff = (lhs - rhs) & mask(W)
```

They update flags according to E01-S06:

```text
SR.Z = 1 if diff == 0 else 0
SR.N = diff[W-1]
SR.C = 1 if lhs >= rhs else 0
SR.V = 1 if sign(lhs) != sign(rhs) and sign(diff) != sign(lhs) else 0
```

Here `sign(x)` is bit `W-1` of the width-limited value.

`CMP` and `CMPU` produce the same flag bits. Signed and unsigned condition-code consumers interpret those bits differently.

### `TST`

`TST Da, Db` computes a width-limited bitwise test:

```text
test = uW(Da) & uW(Db)
```

It updates:

```text
SR.Z = 1 if test == 0 else 0
SR.N = test[W-1]
SR.C = 0
SR.V = 0
```

## Condition-code Integer Operations

`SETcc` and `CMOVcc` use the same mandatory condition namespace as `Bcc` in E04-S04:

| Condition | Predicate |
| --- | --- |
| `AL` | `true` |
| `EQ` | `SR.Z = 1` |
| `NE` | `SR.Z = 0` |
| `CS` / `HS` | `SR.C = 1` |
| `CC` / `LO` | `SR.C = 0` |
| `MI` | `SR.N = 1` |
| `PL` | `SR.N = 0` |
| `VS` | `SR.V = 1` |
| `VC` | `SR.V = 0` |
| `HI` | `SR.C = 1 and SR.Z = 0` |
| `LS` | `SR.C = 0 or SR.Z = 1` |
| `GE` | `SR.N = SR.V` |
| `LT` | `SR.N != SR.V` |
| `GT` | `SR.Z = 0 and SR.N = SR.V` |
| `LE` | `SR.Z = 1 or SR.N != SR.V` |

An unassigned condition-code encoding raises `ILLEGAL_INSTRUCTION`.

### `SETcc`

`SETcc Dd` writes a boolean integer:

```text
Dd = 1 if condition_true(cc, SR) else 0
```

`SETcc` always writes a zero-extended 48-bit result. It does not use a width or sign-extension selector.

### `CMOVcc`

`CMOVcc Dd, Ds` conditionally copies a source register:

```text
if condition_true(cc, SR):
    Dd = write_form(uW(Ds))
else:
    Dd is unchanged
```

The false case performs no destination write. It does not merge partial register bits and does not apply the selected write form.

`CMOVcc` leaves flags unchanged.

## Bit Set and Bit Clear

`BSET` and `BCLR` use a register bit index.

The selected bit index is:

```text
index = Db[5:0] mod W
bit_mask = 1 << index
```

### `BSET`

`BSET Dd, Da, Db` sets one bit in the selected width:

```text
result_w = uW(Da) | bit_mask
```

### `BCLR`

`BCLR Dd, Da, Db` clears one bit in the selected width:

```text
result_w = uW(Da) & ~bit_mask
```

`BSET` and `BCLR` do not update flags.

## Overflow and Trap Summary

Integer overflow is deterministic and non-trapping in v0.1.

Rules:

- `ADD`, `ADDU`, `SUB`, `SUBU`, `NEG`, `MUL`, and `MULU` wrap or truncate modulo `2^W`.
- `DIV` signed minimum divided by `-1` returns signed minimum.
- `MOD` signed minimum modulo `-1` returns zero.
- Shifts with `count >= W` produce the explicit results defined above.
- Rotates use `count mod W`.
- `BSET` and `BCLR` use `index mod W`.
- The only arithmetic exception defined by E04-S02 is divide or modulo by zero.

No E04-S02 overflow case sets `SR.V` except `CMP` and `CMPU`, which update `SR.V` as part of their comparison flag result rather than trapping.

## Out of Scope for This Story

- Exact opcode bit positions, compact aliases, immediate encodings, and assembler suffix spelling: E04-S06 and the final opcode story.
- Integer load/store operations: E04-S03.
- Capability-register operations: E04-S05.
- Branch behavior using condition codes: E04-S04.
- Multiply/divide unit latency, scoreboarding, and bypassing: E13-S02.
- Counter behavior beyond ordinary `INSTRET` retirement: E12-S04.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- Every mandatory integer mnemonic listed by this story is accepted by the assembler once encoded.
- Reserved width encodings raise `ILLEGAL_INSTRUCTION`.
- Result-producing operations honor `W8`, `W12`, `W16`, `W24`, `W32`, and `W48`.
- Narrow zero-extending writes clear high destination bits.
- Narrow sign-extending writes fill high destination bits from the selected sign bit.
- `ADD` and `ADDU` wrap modulo `2^W`.
- `SUB` and `SUBU` wrap modulo `2^W`.
- `NEG` of signed minimum returns signed minimum.
- `MUL` and `MULU` write the low `W` product bits.
- `DIV` and `MOD` by zero raise `DIVIDE_BY_ZERO` and leave the destination unchanged.
- `DIV` signed minimum divided by `-1` returns signed minimum.
- `MOD` signed minimum modulo `-1` returns zero.
- `DIVU` and `MODU` use unsigned operands.
- `SHL` and `SHRU` with `count >= W` return zero.
- `SHRS` with `count >= W` returns all ones for a negative source and zero otherwise.
- `ROL` and `ROR` rotate by `count mod W`.
- `CMP` and `CMPU` update `Z`, `N`, `C`, and `V` according to E01-S06.
- `TST` updates `Z` and `N`, and clears `C` and `V`.
- Ordinary ALU, shift, rotate, multiply, divide, modulo, and bit operations leave flags unchanged.
- `SETcc` writes `0` or `1`.
- False `CMOVcc` leaves the destination unchanged.
- `BSET` and `BCLR` use `index mod W`.
- All mandatory integer operations have a canonical 24-bit register encoding category.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CPY`, `NEG`, `ADD`, `ADDU`, `SUB`, `SUBU`, `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, `MODU`, `NOT`, `AND`, `OR`, `XOR`, `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR`, `CMP`, `CMPU`, `TST`, `SETcc`, `CMOVcc`, `BSET`, and `BCLR` are listed. | Met. |
| Signed and unsigned behavior is defined. | Met: signed/unsigned arithmetic, multiply, divide, modulo, compare use cases, and branch-condition consumers are defined. |
| Divide-by-zero behavior is defined. | Met: `DIV`, `DIVU`, `MOD`, and `MODU` raise `DIVIDE_BY_ZERO` and leave destination state unchanged. |
| Overflow and flag behavior are defined. | Met: arithmetic overflow is non-trapping and modulo/truncated; only `CMP`, `CMPU`, and `TST` update flags. |
| Encoding category is assigned as 12-bit, 24-bit, or 48-bit where applicable. | Met: all mandatory register forms have a canonical 24-bit encoding category; 12-bit aliases and 48-bit immediate forms are deferred to the final opcode story. |

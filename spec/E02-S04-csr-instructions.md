# E02-S04: CSR Instructions

Story: E02-S04

Status: Complete

Normative source: `design.md`, sections 4 and 17.1

Prerequisite: `spec/E02-S01-scalar-csr-namespace.md`

Related sources:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E04-S01-instruction-fetch-groups.md`

## Decision

CPU v0.1 has four scalar CSR instructions:

- `CSRRD`
- `CSRWR`
- `CSRSET`
- `CSRCLR`

They access only the scalar CSR namespace defined by E02-S01. They do not access general capability registers, special capability registers, memory, or capability tags.

All scalar CSR data transfers use the 48-bit integer register file `D0-D15`.

## Instruction Forms

Architectural assembly forms:

| Instruction | Assembly form | Source registers | Destination registers | CSR operation |
| --- | --- | --- | --- | --- |
| `CSRRD` | `CSRRD Dd, csr` | none | `Dd` | Read CSR value. |
| `CSRWR` | `CSRWR csr, Ds` | `Ds` | none | Write CSR value from `Ds`. |
| `CSRSET` | `CSRSET Dd, csr, Ds` | `Ds` | `Dd` | Atomic read, set bits, and return old CSR value. |
| `CSRCLR` | `CSRCLR Dd, csr, Ds` | `Ds` | `Dd` | Atomic read, clear bits, and return old CSR value. |

`csr` is a scalar CSR selector. Assemblers may accept either the architectural CSR name or a numeric CSR number.

`Dd` and `Ds` are ordinary integer registers. There is no hardwired zero register, so no CSR form uses a register operand as a no-op suppressor.

If `Dd` and `Ds` name the same integer register, `Ds` is read before any destination writeback.

## Fast and Long CSR Forms

Every CSR instruction has two selector forms:

| Encoding form | Selector width | Reachable CSR numbers | Instruction-size class |
| --- | ---: | --- | --- |
| Fast/short CSR form | 4 bits | `0x00-0x0F` | Compact CSR form assigned by the opcode story |
| Long CSR form | 8 bits | `0x00-0xFF` | 48-bit instruction |

Rules:

- Fast/short CSR forms can name only the fast CSR window.
- Long CSR forms can name any scalar CSR number.
- A long-form access to CSR `0x00-0x0F` has the same architectural effect as the corresponding fast-form access.
- Long CSR forms are 48-bit instructions and must obey the E04-S01 placement rule for 48-bit instructions.
- Fast/short CSR forms are not the long form; exact opcode bit positions are assigned by the final ISA encoding story.
- Assemblers should choose the fast form for fast-window CSRs unless the source explicitly requests the long form or the opcode story requires a long form for the selected operand pattern.

## Operation Semantics

All CSR instruction reads and writes operate on 48-bit values.

### `CSRRD`

```text
old = read_csr(csr)
Dd  = old
```

`CSRRD` requires CSR read access. It does not require CSR write access.

### `CSRWR`

```text
new = Ds[47:0]
write_csr(csr, new)
```

`CSRWR` requires CSR write access. It does not require CSR read access and has no integer destination register.

### `CSRSET`

```text
old = read_csr(csr)
new = old | Ds[47:0]
write_csr(csr, new)
Dd  = old
```

`CSRSET` requires both CSR read access and CSR write access.

### `CSRCLR`

```text
old = read_csr(csr)
new = old & ~Ds[47:0]
write_csr(csr, new)
Dd  = old
```

`~Ds[47:0]` is the 48-bit bitwise complement of `Ds`.

`CSRCLR` requires both CSR read access and CSR write access.

## Access Checks

CSR instructions use the E02-S01 access-check order, refined as follows:

1. Decode the instruction encoding.
2. Decode the CSR selector.
3. Determine whether the CSR number is implemented or reserved.
4. Check read and write access classes required by the instruction.
5. Check current privilege against every required read and write privilege.
6. Read all integer source operands.
7. Compute the candidate CSR write value, if any.
8. Validate writable fields and apply WARL legalization, if any.
9. Commit CSR update and destination integer writeback atomically.

Malformed CSR instruction encodings raise `ILLEGAL_INSTRUCTION`.

Reserved CSR numbers raise `RESERVED_CSR_FAULT`.

If an instruction requires a CSR read and the CSR or targeted readable fields do not allow reads, the instruction raises `ILLEGAL_CSR_READ`.

If an instruction requires a CSR write and the CSR or targeted writable fields do not allow writes, the instruction raises `ILLEGAL_CSR_WRITE`.

If the CSR exists and the access class allows the operation but the current privilege is too low, the instruction raises `CSR_PRIVILEGE_FAULT`.

E07-S02 assigns numeric exception encodings for these named exceptions. Until E07-S02 is complete, tests should use the names in this story.

## Field Write Rules

CSR writes are checked against the target CSR's field rules before any architectural state changes.

Rules:

- `RW` fields accept the candidate write value.
- `RO` fields must receive their old value; attempting to change an `RO` field raises `ILLEGAL_CSR_WRITE`.
- `RZ/W0` fields must receive zero; attempting to write one raises `ILLEGAL_CSR_WRITE`.
- `WARL` fields accept any write input and store an architecturally legal value.
- `W1C` fields use the field-specific write-one-to-clear behavior defined by the CSR's story.

`CSRSET` and `CSRCLR` are logical read-modify-write operations over the full 48-bit value. When a CSR contains `W1C`, `RO`, or `RZ/W0` fields, the candidate value produced by the logical operation is still subject to the field rules above.

Software should use `CSRWR` with an explicit mask for `W1C` fields unless the CSR's defining story specifically defines useful `CSRSET` or `CSRCLR` behavior for those fields.

## Atomicity and Commit

Each CSR instruction is one architectural instruction.

Commit rules:

- On success, the CSR update and any destination integer-register write become visible together at the instruction retire point.
- On fault, the target CSR is unchanged.
- On fault, destination integer registers are unchanged.
- On fault, no CSR read side effect or write side effect is performed.
- `CSRSET` and `CSRCLR` are indivisible read-modify-write operations for the target CSR.
- Trap entry, interrupt delivery, debug entry, and hardware CSR updates cannot observe or expose the intermediate value between the read and write of `CSRSET` or `CSRCLR`.

If hardware updates the same CSR that a CSR instruction accesses, the implementation must serialize the hardware update either before or after the CSR instruction. Software observes one complete order, not a partially interleaved read-modify-write.

## Side Effects

CSR instruction side effects are limited to:

- Reading the selected scalar CSR.
- Writing the selected scalar CSR.
- Writing the destination integer register for `CSRRD`, `CSRSET`, and `CSRCLR`.
- Side effects defined by the selected CSR's own story.

CSR instructions do not directly access memory and do not directly read or write capability tags.

CSR instructions do not update `SR.Z`, `SR.N`, `SR.C`, or `SR.V` as arithmetic flags. An explicit successful write to `SR` may still change those fields because `SR` is the target CSR.

Writes to reporting CSRs such as `CAUSE` or `TVAL` do not synthesize hardware events unless the selected CSR's story explicitly defines such behavior.

## Examples

Read the current cycle counter:

```text
CSRRD D1, CYCLE
```

Write the kernel scratch CSR:

```text
CSRWR SCRATCH, D2
```

Set interrupt-enable mask bits and receive the old mask:

```text
CSRSET D3, IENABLE, D4
```

Clear ordinary read/write scratch bits and receive the old value:

```text
CSRCLR D5, SCRATCH, D6
```

Use the long form for an extended CSR number:

```text
CSRRD.L D7, 0x40
```

The `.L` suffix is assembler notation for forcing the long selector form. The opcode story assigns final suffix and encoding conventions.

## Out of Scope for This Story

- Exact opcode bit assignments: E04-S06.
- Extended CSR reservations and assigned extended CSR names: E02-S03.
- Capability CSR instruction semantics: E02-S05.
- Numeric exception cause encodings: E07-S02.
- Trap entry sequencing after a CSR fault: E07-S04.
- Counter increment timing around explicit counter writes: E12-S04.
- Final `SATP`, TLB, interrupt, debug, and performance-counter field behavior: later owning stories.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- `CSRRD Dd, csr` writes the selected CSR value to `Dd`.
- `CSRWR csr, Ds` writes `Ds[47:0]` to the selected CSR and writes no integer destination register.
- On an all-`RW` CSR, `CSRSET Dd, csr, Ds` stores `old | Ds` in the CSR and writes `old` to `Dd`.
- On an all-`RW` CSR, `CSRCLR Dd, csr, Ds` stores `old & ~Ds` in the CSR and writes `old` to `Dd`.
- If `Dd == Ds`, `CSRSET` and `CSRCLR` use the old source-register value as the mask.
- Fast-form CSR selectors can name only `0x00-0x0F`.
- Long-form CSR selectors can name `0x00-0xFF`.
- Long-form access to a fast-window CSR has the same effect as fast-form access.
- Long-form CSR instructions obey 48-bit instruction placement rules.
- `CSRRD` of a reserved CSR raises `RESERVED_CSR_FAULT` and leaves `Dd` unchanged.
- `CSRWR` to a read-only CSR raises `ILLEGAL_CSR_WRITE`.
- `CSRSET` on a write-only CSR raises `ILLEGAL_CSR_READ`.
- `CSRSET` that attempts to write one to an `RZ/W0` bit raises `ILLEGAL_CSR_WRITE`.
- User-mode access to a kernel-only CSR that otherwise allows the operation raises `CSR_PRIVILEGE_FAULT`.
- Faulting `CSRSET` and `CSRCLR` leave both the CSR and destination integer register unchanged.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR` are defined. | Met. |
| Source and destination register behavior is specified. | Met. |
| Atomicity of read-modify-write forms is specified. | Met. |
| Privileged access violations raise a named exception. | Met: `CSR_PRIVILEGE_FAULT`. |
| Short-form and long-form encodings are distinguished. | Met. |

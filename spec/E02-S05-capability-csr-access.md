# E02-S05: Capability CSR Access

Story: E02-S05

Status: Complete

Normative source: `design.md`, sections 3.3, 3.4, and 4

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E03-S01-capability-representation.md`

Related sources:

- `spec/E01-S03-general-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E02-S01-scalar-csr-namespace.md`
- `spec/E02-S04-csr-instructions.md`

## Decision

CPU v0.1 has two capability CSR instructions:

- `CCSRRD`
- `CCSRWR`

They provide explicit privileged access to special capability registers. They do not access scalar CSR numbers, integer registers, memory, or capability slots in memory.

Capability CSR transfers copy a full 96-bit capability payload and its out-of-band validity tag. They never synthesize a valid tag from integer data.

## Instruction Forms

Architectural assembly forms:

| Instruction | Assembly form | Source registers | Destination registers | Operation |
| --- | --- | --- | --- | --- |
| `CCSRRD` | `CCSRRD Cd, idx` | none | `Cd` | Read special capability register `idx` into general capability register `Cd`. |
| `CCSRWR` | `CCSRWR idx, Cs` | `Cs` | none | Write general capability register `Cs` into special capability register `idx`. |

`Cd` and `Cs` name general capability registers `C0-C7`.

`idx` is a capability CSR index. Assemblers may accept either the architectural special capability register name or a numeric CCSR index.

There is no scalar or integer operand form. Any encoding that attempts to use `D0-D15` as a CCSR source or destination is malformed and raises `ILLEGAL_INSTRUCTION`.

## CCSR Index Map

The v0.1 implemented CCSR index map is:

| CCSR index | Name | Access | Scope |
| ---: | --- | --- | --- |
| `0` | `PCC` | Kernel read/write | Per core |
| `1` | `DSC` | Kernel read/write | Per core |
| `2` | `RSC` | Kernel read/write | Per core |
| `3` | `DDC` | Kernel read/write | Per core |
| `4` | `EPCC` | Kernel read/write | Per core |
| `5` | `TVC` | Kernel read/write | Per core |
| `6` | `KSC` | Kernel read/write | Per core |
| `7` | `KRC` | Kernel read/write | Per core |

CCSR indices `8-255` are reserved.

Rules:

- CCSR indices are not scalar CSR numbers.
- Scalar `CSRRD 0x00` reads scalar `SR`, not `PCC`.
- `CCSRRD C0, 0` reads `PCC`, not scalar `SR`.
- Reserved CCSR indices raise `RESERVED_CCSR_FAULT`.
- Future architecture revisions may assign reserved CCSR indices only with an explicit compatibility rule.

## Encoding Class

`CCSRRD` and `CCSRWR` are capability/control instructions.

Baseline encoding contract:

- The CCSR selector is 8 bits.
- Both instructions can address CCSR indices `0-255`.
- Both instructions are in the 48-bit instruction-size class unless the final opcode story explicitly assigns an additional compact alias.
- 48-bit CCSR encodings must obey the E04-S01 48-bit instruction placement rules.

Exact opcode bit positions are assigned by E04-S06.

## `CCSRRD`

`CCSRRD` copies a special capability register into a general capability register:

```text
special = read_ccsr(idx)
Cd.payload = special.payload
Cd.tag     = special.tag
```

Rules:

- The 96-bit payload is copied exactly.
- The out-of-band tag is copied exactly.
- An invalid source tag produces an invalid destination tag.
- The destination general capability register is overwritten on success.
- No scalar CSR state is read.
- No integer register is written.

For `PCC` and `EPCC`, the hidden slot bit is not copied because general capability registers do not carry a slot bit.

## `CCSRWR`

`CCSRWR` copies a general capability register into a special capability register:

```text
source = Cs
special.payload = source.payload
special.tag     = source.tag
```

Rules:

- The 96-bit payload is copied exactly.
- The out-of-band tag is copied exactly.
- An invalid source tag writes an invalid special capability tag.
- `CCSRWR` cannot create a valid tag unless the source general capability register already has a valid tag.
- No independent scalar CSR state is written. `SR.SLOT` may reflect a `PCC` slot update as described below.
- No integer register is read.

`CCSRWR` does not validate that the installed capability is useful for the target register's implicit role. For example, writing a non-executable tagged capability to `PCC` can succeed as a privileged state write, but subsequent instruction fetch through `PCC` must still fail the normal execute-authority checks.

## Slot-bit Behavior

`PCC` and `EPCC` each carry a hidden slot bit according to E01-S05.

Rules:

- `CCSRRD` from `PCC` or `EPCC` does not expose the hidden slot bit.
- `CCSRWR` to `PCC` sets `PCC.slot = 0`.
- `CCSRWR` to `EPCC` sets `EPCC.slot = 0`.
- A successful `CCSRWR` to `PCC` makes `SR.SLOT` read as `0` after the write commits, because `SR.SLOT` mirrors the current `PCC` slot.
- `CCSRWR` to `EPCC` does not change `SR.SLOT`.
- No v0.1 CCSR instruction can write slot 1 into `PCC` or `EPCC`.

Later architecture revisions may add an explicit slot-aware CCSR form, but v0.1 software cannot directly install a slot-1 `PCC` or `EPCC` through CCSR access.

## Privilege and Access Checks

All implemented v0.1 CCSR indices are kernel-only for explicit reads and writes.

Access-check order:

1. Decode the instruction encoding.
2. Decode the general capability register operand.
3. Decode the CCSR index.
4. Determine whether the CCSR index is implemented or reserved.
5. Check that the operation is supported for the selected CCSR.
6. Check current privilege.
7. Read the source capability register for `CCSRWR`, if any.
8. Commit the destination capability update atomically.

Malformed CCSR instruction encodings raise `ILLEGAL_INSTRUCTION`.

Reserved CCSR indices raise `RESERVED_CCSR_FAULT`.

If a future CCSR is implemented but does not support the requested read or write operation, the instruction raises `ILLEGAL_CCSR_ACCESS`.

If the selected CCSR is implemented and supports the operation but the current mode is not kernel mode, the instruction raises `CCSR_PRIVILEGE_FAULT`.

E07-S02 assigns numeric exception encodings for these named exceptions. Until E07-S02 is complete, tests should use the names in this story.

## Atomicity and Commit

Each CCSR instruction is one architectural instruction.

Commit rules:

- On success, payload and tag are copied together at the instruction retire point.
- On success, `CCSRRD` updates only the destination general capability register.
- On success, `CCSRWR` updates only the target special capability register and any associated hidden slot update.
- On fault, the destination general capability register is unchanged.
- On fault, the target special capability register is unchanged.
- On fault, no payload-only or tag-only partial update is visible.
- Trap entry, interrupt delivery, debug entry, and hardware special-capability updates cannot observe a partial CCSR copy.

If hardware updates the same special capability register that a CCSR instruction accesses, the implementation must serialize the hardware update either before or after the CCSR instruction. Software observes one complete order.

## Authority and Tag Integrity

CCSR instructions move existing capability authority. They do not derive, widen, seal, unseal, decode from integers, or manufacture authority.

Rules:

- A valid tag can appear in a CCSR destination only if the source capability state already had a valid tag.
- An invalid-tag source remains invalid after the copy.
- Integer registers cannot be CCSR sources.
- Scalar CSR writes cannot change special capability payloads or tags.
- CCSR writes do not bypass later implicit-use checks for tag, bounds, permissions, seal state, or local/global state.
- Writing `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, or `KRC` does not grant authority absent from the copied source capability.

This preserves the pure-capability rule that authority flows only through tagged capability state.

## Examples

Save the current exception program counter capability:

```text
CCSRRD C0, EPCC
```

Install a trap-vector capability:

```text
CCSRWR TVC, C1
```

Install a new execution capability at slot 0:

```text
CCSRWR PCC, C2
```

Invalidate the default data capability by copying an invalid-tag general capability:

```text
CCSRWR DDC, C3
```

The last example invalidates `DDC` only if `C3.tag = 0`; the CCSR instruction copies the source tag exactly.

## Out of Scope for This Story

- Exact opcode bit assignments: E04-S06.
- Scalar CSR instruction semantics: E02-S04.
- Execute authority and `PCC` cursor advancement after installation: E06-S01.
- Control-transfer, `IRET`, and trap-entry semantics: E04-S04, E07-S04, and E07-S05.
- Reset contents of special capability registers: E11-S02.
- Numeric exception cause encodings: E07-S02.
- Future extended CCSR indices beyond `0-7`.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- `CCSRRD C0, PCC` copies `PCC.payload` into `C0.payload`.
- `CCSRRD C0, PCC` copies `PCC.tag` into `C0.tag`.
- `CCSRRD C0, PCC` does not expose `PCC.slot`.
- `CCSRWR PCC, C1` copies `C1.payload` into `PCC.payload`.
- `CCSRWR PCC, C1` copies `C1.tag` into `PCC.tag`.
- `CCSRWR PCC, C1` sets `PCC.slot=0`.
- `CCSRWR EPCC, C1` sets `EPCC.slot=0`.
- `CCSRWR DDC, C1` does not alter `PCC`, `EPCC`, or any scalar CSR.
- `CCSRWR TVC, C1` with `C1.tag=0` writes `TVC.tag=0`; it does not create a valid tag.
- User-mode `CCSRRD` of an implemented CCSR raises `CCSR_PRIVILEGE_FAULT`.
- User-mode `CCSRWR` of an implemented CCSR raises `CCSR_PRIVILEGE_FAULT`.
- CCSR index `8` raises `RESERVED_CCSR_FAULT`.
- Faulting `CCSRRD` leaves the destination general capability register unchanged.
- Faulting `CCSRWR` leaves the target special capability register unchanged.
- Scalar `CSRRD 0x00` still reads `SR`, while `CCSRRD C0, 0` reads `PCC`.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CCSRRD` and `CCSRWR` are defined or reserved for v0.1. | Met: both are defined. |
| Valid special capability register indices are listed. | Met. |
| Privilege requirements are documented. | Met: all implemented v0.1 CCSR indices are kernel-only. |
| Tag preservation rules for CCSR reads and writes are defined. | Met. |
| Invalid writes cannot forge capability tags. | Met. |

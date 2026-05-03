# E02-S01: Scalar CSR Namespace

Story: E02-S01

Status: Complete

Normative source: `design.md`, section 4

Prerequisite: `spec/E01-S06-status-register-behavior.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`

## Decision

CPU v0.1 has a dedicated scalar control/status register namespace with 256 architectural CSR numbers.

Scalar CSRs are separate from:

- Architectural memory.
- General integer registers.
- General capability registers.
- Special capability registers.

Scalar CSRs are 48-bit scalar registers unless the CSR's own story defines narrower implemented fields. Scalar CSRs do not carry capability tags and cannot contain dereferenceable authority.

## CSR Number Space

CSR numbers are 8 bits:

```text
CSR number range = 0x00-0xFF
```

The namespace is architectural. Unassigned numbers are reserved; they are not available for ad hoc implementation behavior.

## Fast CSR Window

CSR numbers `0x00-0x0F` are the fast CSR window. They are accessible by short instruction encodings that carry a 4-bit CSR index.

The fast CSR window is assigned to the mandatory v0.1 scalar CSR set:

| CSR number | Fast index | Name |
| ---: | ---: | --- |
| `0x00` | `0x0` | `SR` |
| `0x01` | `0x1` | `COREID` |
| `0x02` | `0x2` | `CYCLE` |
| `0x03` | `0x3` | `INSTRET` |
| `0x04` | `0x4` | `TVEC` |
| `0x05` | `0x5` | `CAUSE` |
| `0x06` | `0x6` | `TVAL` |
| `0x07` | `0x7` | `SCRATCH` |
| `0x08` | `0x8` | `IENABLE` |
| `0x09` | `0x9` | `IPENDING` |
| `0x0A` | `0xA` | `TIMER` |
| `0x0B` | `0xB` | `TIMECMP` |
| `0x0C` | `0xC` | `SATP` |
| `0x0D` | `0xD` | `ASID` |
| `0x0E` | `0xE` | `DEBUGCTL` |
| `0x0F` | `0xF` | `PERFSEL` |

E02-S02 defines the access mode, scope, reset value, and side effects for each mandatory CSR.

## Extended CSR Ranges

CSR numbers `0x10-0xFF` are extended CSR numbers accessed through long-form CSR instructions.

Initial range policy:

| Range | Use |
| --- | --- |
| `0x10-0x3F` | Architectural extension CSRs reserved for v0.1 follow-on stories. |
| `0x40-0x7F` | Performance, debug, cache, TLB, and capability-fault reporting reservations. |
| `0x80-0xBF` | Platform and interrupt-controller interface reservations. |
| `0xC0-0xEF` | Implementation-specific CSRs, only when explicitly enabled by platform documentation. |
| `0xF0-0xFF` | Reserved for future architectural control state. |

E02-S03 refines extended CSR reservations. Until assigned by a later story, every number in `0x10-0xFF` is reserved.

## CSR Access Forms

The architectural CSR access operations are:

- `CSRRD`
- `CSRWR`
- `CSRSET`
- `CSRCLR`

Encoding classes:

| Encoding class | CSR selector width | Reachable CSR numbers |
| --- | ---: | --- |
| Fast CSR form | 4 bits | `0x00-0x0F` |
| Long CSR form | 8 bits | `0x00-0xFF` |

The long form can access both fast-window CSRs and extended CSRs. A long-form access to `0x00-0x0F` has the same architectural effect as the corresponding fast-form access.

E02-S04 defines the exact operand order, read-modify-write behavior, destination writeback, and atomicity for `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR`.

## Reserved CSR Behavior

Reserved CSR numbers are architecturally inert.

Rules:

- Reading a reserved CSR raises illegal-instruction exception or the CSR-access exception code assigned by E07-S02.
- Writing a reserved CSR raises illegal-instruction exception or the CSR-access exception code assigned by E07-S02.
- Read-modify-write operations targeting a reserved CSR perform no read side effect, no write side effect, and no destination register write before fault.
- Reserved CSR reads never return implementation-defined values.
- Reserved CSR writes never silently discard data.
- Future architecture revisions may assign reserved CSR numbers only with an explicit compatibility rule.

## Implemented CSR Access Classes

Each implemented scalar CSR has independent read and write access classes:

| Class | Meaning |
| --- | --- |
| `RO` | Read-only. Writes fault. |
| `WO` | Write-only. Reads fault. |
| `RW` | Read/write. |
| `W1C` | Write-one-to-clear field behavior, if defined by the CSR story. |
| `WARL` | Write-any, read-legal field behavior, if defined by the CSR story. |
| `RZ/W0` | Reserved-zero field behavior within an implemented CSR. |

The access class is per CSR or per field, as specified by the CSR's defining story.

Writing a read-only CSR or read-only field raises illegal CSR write and leaves the CSR unchanged unless the CSR's defining story explicitly specifies partial-field behavior.

Reading a write-only CSR raises illegal CSR read unless the CSR's defining story provides a read value.

## Privilege Checks

Each implemented scalar CSR has a minimum read privilege and a minimum write privilege.

v0.1 privilege ordering:

```text
U = 0
K = 1
```

Access is allowed only when:

```text
current_privilege >= csr_min_privilege
```

Baseline checks:

1. Decode the CSR number.
2. Determine whether the CSR is implemented or reserved.
3. If reserved, raise the reserved CSR fault.
4. Check the access operation against the CSR's read/write class.
5. Check current privilege against the CSR's minimum privilege for that operation.
6. If all checks pass, perform the CSR operation.

If a CSR is implemented but the current mode lacks privilege, the access raises privilege violation rather than reserved CSR fault.

The detailed mandatory-CSR privilege matrix is defined by E02-S02. Until E02-S02 assigns an access mode, mandatory fast CSRs should be treated as kernel-only for writes; read privilege is CSR-specific and not finalized by this story.

## Relationship to Capability CSRs

Scalar CSR numbers do not address special capability registers.

Special capability registers are accessed through the parallel capability CSR mechanism:

```text
CCSRRD
CCSRWR
```

The CCSR index map starts at its own index 0 and is defined by E01-S04 and E02-S05. A scalar `CSRRD` of CSR `0x00` reads scalar `SR`; it does not read `PCC`.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Fast CSR encodings can name only CSR numbers `0x00-0x0F`.
- Long CSR encodings can name CSR numbers `0x00-0xFF`.
- Long-form access to `0x00` reaches `SR`.
- Fast-form access to index `0x0` reaches `SR`.
- Fast indices `0x0-0xF` map to the 16 mandatory CSR names listed in this story.
- Reserved CSR reads fault.
- Reserved CSR writes fault.
- Reserved CSR read-modify-write operations leave destination registers unchanged.
- Implemented CSR access with insufficient privilege raises privilege violation.
- Scalar CSR access cannot read or write special capability registers.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| 256 scalar CSR numbers are reserved architecturally. | Met. |
| 16 fast CSRs are identified for short encodings. | Met. |
| Extended CSR access through long-form instructions is defined. | Met. |
| Reserved CSR behavior is documented. | Met. |
| Privilege checks for CSR reads and writes are specified. | Met. |

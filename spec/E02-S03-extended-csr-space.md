# E02-S03: Extended CSR Space

Story: E02-S03

Status: Complete

Normative source: `design.md`, sections 4, 5.5, 10.4, and 15

Prerequisite: `spec/E02-S01-scalar-csr-namespace.md`

Related sources:

- `spec/E02-S02-mandatory-scalar-csrs.md`
- `spec/E02-S04-csr-instructions.md`
- `spec/E03-S06-capability-fault-reporting.md`

## Decision

CPU v0.1 reserves the extended scalar CSR numbers `0x10-0xFF` for long-form CSR access.

Extended CSR numbers are scalar CSR numbers. They are not capability CSR indices and do not address special capability registers.

The fast CSR window remains `0x00-0x0F`. No extended CSR is reachable through a fast/short CSR encoding.

## Reservation Classes

Extended CSR numbers have one of these reservation classes:

| Class | Meaning |
| --- | --- |
| Assigned | The CSR number has an architectural name in this story. Its owning story defines full behavior. |
| Reserved architectural | The CSR number is held for a future architectural feature. |
| Reserved platform | The CSR number is held for platform-defined control state. |
| Implementation-specific | The CSR number may be used only when platform documentation explicitly defines it. |
| Future architectural | The CSR number is held for later architecture revisions and is not available to v0.1 platforms. |

An assigned CSR is not automatically usable. If the owning story has not implemented its behavior, access still faults according to the unsupported-access rules below.

## Extended CSR Map

| CSR range | Reservation |
| --- | --- |
| `0x10-0x3F` | Reserved architectural extension CSRs. |
| `0x40-0x47` | `PMC0-PMC7` assigned performance monitor counter reservations. |
| `0x48` | `CACHECTL` assigned cache-control reservation. |
| `0x49` | `TLBCTL` assigned TLB-control reservation. |
| `0x4A` | `FAULTCAPIDX` assigned capability-fault reporting CSR. |
| `0x4B` | `CAPCAUSE` assigned capability-fault reporting CSR. |
| `0x4C-0x5F` | Reserved performance, debug, and observability CSRs. |
| `0x60-0x6F` | Reserved cache and memory-system control CSRs. |
| `0x70-0x7F` | Reserved TLB, MMU, and capability-fault extension CSRs. |
| `0x80-0xBF` | Reserved platform interrupt-controller interface CSRs. |
| `0xC0-0xEF` | Implementation-specific CSRs with mandatory platform documentation. |
| `0xF0-0xFF` | Future architectural CSRs, unavailable to v0.1 implementations. |

## Assigned Extended CSR Numbers

| CSR number | Name | Owning story | Default v0.1 access before owner behavior |
| ---: | --- | --- | --- |
| `0x40` | `PMC0` | E12-S05 | Reserved, access faults. |
| `0x41` | `PMC1` | E12-S05 | Reserved, access faults. |
| `0x42` | `PMC2` | E12-S05 | Reserved, access faults. |
| `0x43` | `PMC3` | E12-S05 | Reserved, access faults. |
| `0x44` | `PMC4` | E12-S05 | Reserved, access faults. |
| `0x45` | `PMC5` | E12-S05 | Reserved, access faults. |
| `0x46` | `PMC6` | E12-S05 | Reserved, access faults. |
| `0x47` | `PMC7` | E12-S05 | Reserved, access faults. |
| `0x48` | `CACHECTL` | E10-S05 | Reserved, access faults. |
| `0x49` | `TLBCTL` | E09-S03 and E08-S04 | Reserved, access faults. |
| `0x4A` | `FAULTCAPIDX` | E03-S06 and E07-S04 | Kernel read/write reporting CSR. |
| `0x4B` | `CAPCAUSE` | E03-S06 and E07-S04 | Kernel read/write reporting CSR. |

Assigned names must not be reused for any other CSR number.

## Capability-fault Reporting CSRs

`FAULTCAPIDX` and `CAPCAUSE` are per-core scalar reporting CSRs.

They are populated by capability-related traps according to E03-S06 and the precise trap-entry stories.

| CSR | Number | Access class | Read privilege | Write privilege | Reset value | Hardware side effect |
| --- | ---: | --- | --- | --- | --- | --- |
| `FAULTCAPIDX` | `0x4A` | `RW`, with `RZ/W0` fields | K | K | `NONE` | Hardware writes the relevant capability operand on capability faults. |
| `CAPCAUSE` | `0x4B` | `RW`, with `RZ/W0` fields | K | K | `NONE` | Hardware writes the capability-specific reason on capability faults. |

User-mode reads and writes of `FAULTCAPIDX` or `CAPCAUSE` raise `CSR_PRIVILEGE_FAULT`.

Kernel software may write these CSRs for trap-frame setup, testing, and diagnostic replay. Software writes do not synthesize a capability fault and do not alter `CAUSE`, `TVAL`, `EPCC`, or any capability register.

### `CAPCAUSE` Encoding

`CAPCAUSE` uses bits `[3:0]`.

| Value | Name | Meaning |
| ---: | --- | --- |
| `0x0` | `NONE` | No capability-specific cause. |
| `0x1` | `TAG` | Capability tag fault. |
| `0x2` | `BOUNDS` | Capability bounds fault. |
| `0x3` | `PERMISSION` | Capability permission fault. |
| `0x4` | `SEAL_TYPE` | Capability seal/type fault. |
| `0x5` | `LOCAL_STORE` | Capability local-store fault. |
| `0x6-0xF` | reserved | Reserved capability-fault reasons. |

Bits `[47:4]` are reserved-zero. Writes that set any reserved-zero bit to one raise `ILLEGAL_CSR_WRITE` and leave `CAPCAUSE` unchanged.

### `FAULTCAPIDX` Encoding

`FAULTCAPIDX` uses bits `[7:0]`.

| Value | Name | Meaning |
| ---: | --- | --- |
| `0x00` | `NONE` | No single capability operand is responsible. |
| `0x01` | `UNKNOWN` | The implementation cannot report a precise operand. |
| `0x10` | `C0` | General capability register `C0`. |
| `0x11` | `C1` | General capability register `C1`. |
| `0x12` | `C2` | General capability register `C2`. |
| `0x13` | `C3` | General capability register `C3`. |
| `0x14` | `C4` | General capability register `C4`. |
| `0x15` | `C5` | General capability register `C5`. |
| `0x16` | `C6` | General capability register `C6`. |
| `0x17` | `C7` | General capability register `C7`. |
| `0x20` | `PCC` | Program-counter capability. |
| `0x21` | `DDC` | Default data capability. |
| `0x22` | `DSC` | Data-stack capability. |
| `0x23` | `RSC` | Return-stack capability. |
| `0x24` | `KSC` | Kernel stack capability. |
| `0x25` | `KRC` | Kernel root capability. |
| `0x26` | `EPCC` | Exception program-counter capability. |
| `0x27` | `TVC` | Trap-vector capability. |

All other low-byte values are reserved. Bits `[47:8]` are reserved-zero.

Writes that set bits `[47:8]` to one raise `ILLEGAL_CSR_WRITE` and leave `FAULTCAPIDX` unchanged.

Kernel software should write only defined values to `FAULTCAPIDX`. A write of an unassigned low-byte value raises `ILLEGAL_CSR_WRITE` unless a later story assigns the value.

## Performance Counter Reservations

`PMC0-PMC7` reserve eight extended 48-bit performance monitor counters.

Rules:

- `PERFSEL` in the fast CSR window remains the mandatory selector/control CSR.
- `PMC0-PMC7` are not mandatory observable counters until E12-S05 defines them.
- Accesses to `PMC0-PMC7` raise `RESERVED_CSR_FAULT` until E12-S05 assigns implemented behavior.
- E12-S05 defines counter event bindings, privilege access, reset behavior, halt behavior, and overflow behavior.

Counter overflow for `PMC0-PMC7` is explicitly deferred to E12-S05. This story reserves no overflow interrupt, sticky overflow bit, or overflow reporting CSR for extended counters.

Mandatory `CYCLE` and `INSTRET` overflow behavior remains the modulo-`2^48` behavior defined by E02-S02 and refined by E12-S04.

## Cache and TLB Control Reservations

`CACHECTL` and `TLBCTL` reserve scalar control points for later cache and translation maintenance stories.

Rules:

- `CACHECTL` access raises `RESERVED_CSR_FAULT` until E10-S05 defines implemented behavior.
- `TLBCTL` access raises `RESERVED_CSR_FAULT` until E09-S03 or E08-S04 defines implemented behavior.
- Future implemented `CACHECTL` and `TLBCTL` behavior must be kernel-only unless the owning story explicitly defines a user-readable non-authority field.
- Future implementations must define side effects, ordering, and interaction with `FENCE`, `FENCE.I`, `SFENCE.VM`, or cache-maintenance instructions before software may use these CSRs.

## Platform Interrupt-controller CSR Space

CSR numbers `0x80-0xBF` are reserved for a platform-specific interrupt-controller interface.

Suggested subranges:

| CSR range | Intended use |
| --- | --- |
| `0x80-0x8F` | Per-core external interrupt status, threshold, claim, and completion interface. |
| `0x90-0x9F` | Software IPI and start-event interface reservations. |
| `0xA0-0xAF` | Message-signaled interrupt or interrupt-file interface reservations. |
| `0xB0-0xBF` | Platform-specific interrupt-controller extensions. |

Rules:

- The architecture reserves the range but does not define register fields in this story.
- A platform may implement CSRs in `0x80-0xBF` only with platform documentation.
- Undocumented platform CSR numbers in this range raise `RESERVED_CSR_FAULT`.
- Implemented platform interrupt CSRs are kernel-only unless the platform documentation and architecture profile explicitly allow a user-readable field.
- Platform interrupt CSRs must not alias mandatory fast CSRs or the assigned `0x40-0x4B` extended CSRs.

## Implementation-specific CSR Space

CSR numbers `0xC0-0xEF` are implementation-specific.

Rules:

- Implementations may define CSRs in this range only when platform documentation names the CSR number, access class, privilege, reset value, and side effects.
- Undocumented implementation-specific CSR numbers raise `RESERVED_CSR_FAULT`.
- Implementation-specific CSRs must not be required by portable v0.1 software.
- Implementation-specific CSRs must not alter the architectural behavior of mandatory or assigned architectural CSRs.
- Future architecture revisions may standardize behavior elsewhere without preserving implementation-specific behavior in this range.

## Unsupported-access Behavior

Unsupported extended CSR access follows E02-S04 fault and commit rules.

Rules:

- Reads of reserved, unimplemented, undocumented, or future architectural CSR numbers raise `RESERVED_CSR_FAULT`.
- Writes to reserved, unimplemented, undocumented, or future architectural CSR numbers raise `RESERVED_CSR_FAULT`.
- `CSRSET` or `CSRCLR` targeting a reserved, unimplemented, undocumented, or future architectural CSR raises `RESERVED_CSR_FAULT`.
- Faulting extended CSR accesses leave destination integer registers unchanged.
- Faulting extended CSR accesses leave all CSR state unchanged.
- Faulting extended CSR accesses have no read side effects, write side effects, counter side effects, cache side effects, TLB side effects, interrupt side effects, or capability-reporting side effects.
- Reserved extended CSR reads never return implementation-defined values.
- Reserved extended CSR writes are never silently ignored.
- If a CSR number is implemented but the operation is not allowed by its access class, the access raises `ILLEGAL_CSR_READ` or `ILLEGAL_CSR_WRITE` as defined by E02-S04.
- If a CSR number is implemented and supports the operation but the current privilege is too low, the access raises `CSR_PRIVILEGE_FAULT`.

This keeps unsupported access distinguishable from supported but unauthorized access.

## Out of Scope for This Story

- Exact `PMC0-PMC7` event semantics and overflow behavior: E12-S05.
- Mandatory `CYCLE` and `INSTRET` refinement: E12-S04.
- Cache maintenance operations and ordering: E10-S05.
- TLB invalidation and shootdown behavior: E09-S03 and E08-S04.
- Platform interrupt-controller field definitions: platform profiles and E07-S05.
- Numeric exception cause encodings for CSR faults: E07-S02.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Long-form `CSRRD 0x40` targets `PMC0`.
- Long-form `CSRRD 0x47` targets `PMC7`.
- Long-form `CSRRD 0x48` targets `CACHECTL`.
- Long-form `CSRRD 0x49` targets `TLBCTL`.
- Long-form `CSRRD 0x4A` targets `FAULTCAPIDX`.
- Long-form `CSRRD 0x4B` targets `CAPCAUSE`.
- Fast/short CSR encodings cannot name any extended CSR number.
- Access to unimplemented `PMC0` raises `RESERVED_CSR_FAULT`.
- Access to unimplemented `CACHECTL` raises `RESERVED_CSR_FAULT`.
- Access to unimplemented `TLBCTL` raises `RESERVED_CSR_FAULT`.
- Access to undocumented `0x80` platform interrupt CSR raises `RESERVED_CSR_FAULT`.
- Access to undocumented `0xC0` implementation-specific CSR raises `RESERVED_CSR_FAULT`.
- Access to `0xF0` raises `RESERVED_CSR_FAULT`.
- User-mode access to implemented `CAPCAUSE` raises `CSR_PRIVILEGE_FAULT`.
- Kernel write of `CAPCAUSE = TAG` is accepted.
- Kernel write of `FAULTCAPIDX = C3` is accepted.
- Kernel write of an unassigned `FAULTCAPIDX` value raises `ILLEGAL_CSR_WRITE`.
- Capability faults populate `CAPCAUSE` and `FAULTCAPIDX` using the encodings in this story.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `PMC0-PMC7`, `CACHECTL`, `TLBCTL`, `FAULTCAPIDX`, and `CAPCAUSE` are reserved. | Met. |
| Platform-specific interrupt controller CSR space is reserved. | Met: `0x80-0xBF`. |
| Unsupported CSR access behavior is specified. | Met. |
| Counter overflow behavior is defined or explicitly deferred. | Met: extended counter overflow is deferred to E12-S05. |

# E02-S02: Mandatory Scalar CSRs

Story: E02-S02

Status: Complete

Normative source: `design.md`, sections 4, 10.3, 10.4, 12.3, and 15

Prerequisite: `spec/E02-S01-scalar-csr-namespace.md`

Related sources:

- `spec/E01-S06-status-register-behavior.md`
- `spec/E03-S06-capability-fault-reporting.md`
- `spec/E09-S01-address-and-page-size.md`
- `spec/E09-S04-page-table-geometry.md`

## Decision

CPU v0.1 implements the 16 mandatory scalar CSRs in the fast CSR window defined by E02-S01.

All mandatory scalar CSRs are 48-bit scalar registers. They do not carry capability tags and do not contain dereferenceable authority.

The mandatory CSR set is per-core architectural state. No mandatory fast-window CSR is global shared state. Platform-wide interrupt-controller, cache, TLB, capability-fault, and performance counter extensions are assigned by E02-S03 or later stories.

## Access Privilege

Privilege names follow E02-S01:

```text
U = user
K = kernel
```

User-mode reads are allowed only for the non-authority observation CSRs listed in this story. User-mode writes to any mandatory scalar CSR fault; the exact fault class follows the E02-S01 access-check order.

Kernel mode can read every mandatory scalar CSR. Kernel writes are allowed only where the CSR access class permits writes.

## Mandatory CSR Table

| Number | Fast index | Name | Access class | Read privilege | Write privilege | Scope | Reset value | Side effects |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| `0x00` | `0x0` | `SR` | `RW`, with `RZ/W0` and `RO` fields | K | K | Per core | E01-S06 reset value | Controls flags, interrupt state, privilege state, exception-level state, and reports current slot. |
| `0x01` | `0x1` | `COREID` | `RO` | U | none | Per core | Platform assigned; core 0 reads `0` | Reports the stable architectural core identifier. |
| `0x02` | `0x2` | `CYCLE` | `RW` | U | K | Per core | `0` | Increments with the core cycle counter. Kernel writes set the counter value. |
| `0x03` | `0x3` | `INSTRET` | `RW` | U | K | Per core | `0` | Increments when an instruction retires. Kernel writes set the counter value. |
| `0x04` | `0x4` | `TVEC` | `WARL` | K | K | Per core | `0` | Provides scalar trap-vector control consumed by trap and interrupt entry. |
| `0x05` | `0x5` | `CAUSE` | `RW` | K | K | Per core | `0` | Hardware writes the architectural trap cause on trap entry. |
| `0x06` | `0x6` | `TVAL` | `RW` | K | K | Per core | `0` | Hardware writes the trap-associated cell address or scalar value when defined. |
| `0x07` | `0x7` | `SCRATCH` | `RW` | K | K | Per core | `0` | Kernel scratch register. Hardware does not interpret the value. |
| `0x08` | `0x8` | `IENABLE` | `RW` | K | K | Per core | `0` | Controls delivery eligibility for maskable interrupt sources. |
| `0x09` | `0x9` | `IPENDING` | `RW/W1C` by field | K | K | Per core | `0` | Reports pending interrupt sources; writable fields set or clear software-visible pending state. |
| `0x0A` | `0xA` | `TIMER` | `RO` | U | none | Per core | `0` | Increments with the architectural timer source. |
| `0x0B` | `0xB` | `TIMECMP` | `RW` | K | K | Per core | `0xFFFF_FFFF_FFFF` | Controls the per-core timer interrupt comparator. |
| `0x0C` | `0xC` | `SATP` | `WARL` | K | K | Per core | `0` | Selects address-translation mode and root state. |
| `0x0D` | `0xD` | `ASID` | `WARL` | K | K | Per core | `0` | Selects the active address-space identifier used by translation and TLB matching. |
| `0x0E` | `0xE` | `DEBUGCTL` | `WARL` | K | K | Per core | `0` | Controls architectural debug facilities. |
| `0x0F` | `0xF` | `PERFSEL` | `WARL` | K | K | Per core | `0` | Selects an architectural performance event source for later performance counters. |

`none` in the write-privilege column means that architectural writes fault in every privilege mode.

## CSR-specific Rules

### `SR`

`SR` uses the bit layout and reset value defined by E01-S06.

Rules:

- User-mode `CSRRD SR` raises privilege violation.
- User-mode writes to `SR` raise privilege violation.
- Kernel writes to `SR` must obey the E01-S06 reserved-zero and read-only slot rules.
- Trap entry and `IRET` update `SR` according to E01-S06 and the later trap stories.

The condition flags in `SR` are still usable by user-mode control-flow instructions. User mode is not required to read `SR` through CSR instructions to use condition-code branches.

### `COREID`

`COREID` is a stable per-core scalar identifier.

Rules:

- `COREID` values are unique among simultaneously active cores in a system.
- Core 0 reads `COREID=0`.
- Other cores read platform-assigned nonnegative values.
- `COREID` does not change until the next cold reset.
- Writes to `COREID` fault and leave the value unchanged.

### `CYCLE`, `INSTRET`, and `TIMER`

`CYCLE`, `INSTRET`, and `TIMER` are 48-bit counters.

Rules:

- Counter reads do not have side effects.
- Counter values wrap modulo `2^48`.
- `CYCLE` increments with the core cycle counter.
- `INSTRET` increments once for each architecturally retired instruction.
- Faulting instructions do not increment `INSTRET` unless a later precise-exception story defines a narrower retirement point.
- `TIMER` increments with the architectural timer source used for timer interrupt comparison.
- Kernel writes to `CYCLE` or `INSTRET` set the visible counter value.
- Writes to `TIMER` fault and leave `TIMER` unchanged.

E12-S04 refines counter increment timing, halt behavior, and overflow tests. This story fixes the mandatory CSR locations and baseline access privileges.

### `TVEC`

`TVEC` is scalar trap-vector control state. It works with the `TVC` special capability register from E01-S04.

Rules:

- `TVC` provides capability authority for trap and interrupt vector fetch.
- `TVEC` provides scalar control such as vector selection, offset, or mode fields.
- A reset value of `0` means the base trap-vector scalar control state.
- User-mode reads and writes fault.
- Kernel writes are `WARL`: unsupported encodings are forced to an architecturally legal value or fault, as finalized by the trap-vector stories.

E07-S04 and E07-S05 define exact direct-exception and vectored-interrupt target calculation. E02-S02 only assigns the CSR and baseline access behavior.

### `CAUSE` and `TVAL`

`CAUSE` and `TVAL` are trap reporting CSRs.

Rules:

- On trap entry, hardware writes `CAUSE` with the architectural trap class.
- On trap entry, hardware writes `TVAL` with the relevant cell address or scalar trap value when one exists.
- If a trap has no relevant `TVAL`, hardware writes `0`.
- Capability faults also populate capability-specific reporting CSRs assigned by E02-S03 and specified by E03-S06.
- Kernel software may write `CAUSE` and `TVAL`.
- Software writes to `CAUSE` or `TVAL` do not trigger trap entry, alter `EPCC`, or alter capability-fault reporting CSRs.
- User-mode reads and writes fault.

E07-S02 assigns exact `CAUSE` encodings.

### `SCRATCH`

`SCRATCH` is an uninterpreted per-core kernel scratch register.

Rules:

- Hardware does not read or write `SCRATCH`.
- Kernel software may use `SCRATCH` for trap-entry, scheduler, or ABI conventions.
- User-mode reads and writes fault.

### `IENABLE` and `IPENDING`

`IENABLE` and `IPENDING` provide the mandatory per-core interrupt control state required by the v0.1 interrupt model.

Rules:

- `IENABLE=0` after reset disables all maskable interrupt sources.
- Writing `IENABLE` updates the per-core interrupt enable mask.
- `IPENDING` reads report currently pending interrupt sources.
- `IPENDING` fields may be hardware-latched, level-derived, software-writable, or write-one-to-clear according to the interrupt source definition.
- Writing `1` to a writable W1C pending field clears that pending field.
- Writing `0` to a W1C pending field leaves that pending field unchanged.
- Writes that attempt to set read-only pending fields to `1` fault and leave `IPENDING` unchanged.
- User-mode reads and writes fault.

E07-S05 defines the interrupt-source bit map, priority, threshold behavior, and exact timer, software IPI, and external interrupt interactions.

### `TIMECMP`

`TIMECMP` is the per-core timer comparator.

Rules:

- The timer interrupt source is pending when the timer-comparison rule defined by the interrupt story is true for `TIMER` and `TIMECMP`.
- The baseline comparison is unsigned `TIMER >= TIMECMP`.
- Writing `TIMECMP` updates the comparator used for subsequent timer-pending evaluation.
- Resetting `TIMECMP` to all ones prevents an immediate timer interrupt at reset while `TIMER=0`.
- User-mode reads and writes fault.

E07-S05 may refine edge cases around timer wrap, priority, and delivery timing, but must preserve the CSR assignment and reset-disabled behavior.

### `SATP` and `ASID`

`SATP` and `ASID` provide the mandatory scalar MMU context controls.

Rules:

- `SATP=0` after reset means address translation is disabled.
- `ASID=0` after reset is the initial address-space identifier.
- `ASID[7:0]` is mandatory architectural state.
- `ASID[47:8]` is reserved-zero unless E09-S02 assigns more ASID bits.
- Kernel writes to `SATP` or `ASID` affect address translation for subsequent instruction fetches and data accesses.
- User-mode reads and writes fault.
- Writes to unsupported `SATP` modes or unsupported `ASID` bits are `WARL` or fault according to E09-S02.

E09-S02 defines the exact `SATP` field layout, including `MODE`, `ASID`, and `ROOT_PPN`. E09-S03 defines TLB matching, local invalidation, and shootdown behavior.

### `DEBUGCTL`

`DEBUGCTL` is mandatory per-core debug control state.

Rules:

- `DEBUGCTL=0` after reset means no optional debug control bit is enabled by reset.
- User-mode reads and writes fault.
- Kernel writes are `WARL`.
- Unassigned or unimplemented bits read as zero and must be written as zero unless E12-S01 assigns them.
- A software write to `DEBUGCTL` has only the debug side effects assigned by the debug story.

E12-S01 defines debug entry, halt, resume, breakpoint, and debug-vector behavior.

### `PERFSEL`

`PERFSEL` is mandatory per-core performance event selection state.

Rules:

- `PERFSEL=0` selects the default event source.
- `PERFSEL` does not change `CYCLE` or `INSTRET` behavior.
- User-mode reads and writes fault.
- Kernel writes are `WARL`.
- Unsupported event selectors read back as an architecturally legal selector or fault according to the performance-counter story.

E12-S05 defines extended performance counters and event selector encodings.

## Reset Contract

At cold reset, each core's mandatory scalar CSRs take the reset values in the mandatory CSR table.

The reset contract is architectural for a core when it begins normal instruction execution. E11-S01 may refine reset sequencing for secondary cores, ROM entry, debug entry, and platform devices, but software that starts executing on a core observes these baseline CSR values unless that later story explicitly defines an earlier firmware write.

## Fault Behavior

Faulting mandatory CSR accesses follow the E02-S01 access-check order.

Rules:

- User-mode access to a kernel-only mandatory CSR raises privilege violation.
- User-mode writes to writable kernel-only mandatory CSRs raise privilege violation.
- Writes to read-only mandatory CSRs raise illegal CSR write and leave the CSR unchanged.
- Writes that set reserved-zero fields to one raise illegal CSR write and leave the CSR unchanged.
- Read-modify-write operations that fault during access checks do not write a destination register and do not modify the target CSR.
- Software writes to reporting CSRs do not synthesize hardware events.

E02-S04 defines exact `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR` read-modify-write sequencing.

## Out of Scope for This Story

- Extended CSR reservation map: E02-S03.
- CSR instruction operand order and atomicity: E02-S04.
- Capability CSR access: E02-S05.
- Exact exception cause encodings: E07-S02.
- Direct exception and vectored interrupt target calculation: E07-S04 and E07-S05.
- Exact `SATP` layout and TLB behavior: E09-S02 and E09-S03.
- Complete reset-state table: E11-S01.
- Debug halt model: E12-S01.
- Counter increment and privilege refinements: E12-S04.
- Extended performance counter event selectors: E12-S05.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Fast CSR `0x0` names `SR`.
- Fast CSR `0x1` names `COREID`.
- Fast CSR `0x2` names `CYCLE`.
- Fast CSR `0x3` names `INSTRET`.
- Fast CSR `0x4` names `TVEC`.
- Fast CSR `0x5` names `CAUSE`.
- Fast CSR `0x6` names `TVAL`.
- Fast CSR `0x7` names `SCRATCH`.
- Fast CSR `0x8` names `IENABLE`.
- Fast CSR `0x9` names `IPENDING`.
- Fast CSR `0xA` names `TIMER`.
- Fast CSR `0xB` names `TIMECMP`.
- Fast CSR `0xC` names `SATP`.
- Fast CSR `0xD` names `ASID`.
- Fast CSR `0xE` names `DEBUGCTL`.
- Fast CSR `0xF` names `PERFSEL`.
- User-mode reads of `COREID`, `CYCLE`, `INSTRET`, and `TIMER` succeed.
- User-mode reads of other mandatory CSRs raise privilege violation.
- User-mode writes to writable kernel-only mandatory CSRs raise privilege violation.
- User-mode writes to `COREID` and `TIMER` raise illegal CSR write.
- Kernel writes to `COREID` and `TIMER` raise illegal CSR write.
- `SR`, `IENABLE`, `IPENDING`, `TIMECMP`, `SATP`, `ASID`, `DEBUGCTL`, and `PERFSEL` reset to the values listed in this story.
- `CYCLE`, `INSTRET`, and `TIMER` wrap modulo `2^48`.
- Trap entry writes `CAUSE` and `TVAL`.
- Software writes to `CAUSE` and `TVAL` do not cause trap entry.
- Changing `SATP` or `ASID` affects subsequent translation context.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `SR`, `COREID`, `CYCLE`, `INSTRET`, `TVEC`, `CAUSE`, `TVAL`, `SCRATCH`, `IENABLE`, `IPENDING`, `TIMER`, `TIMECMP`, `SATP`, `ASID`, `DEBUGCTL`, and `PERFSEL` are assigned. | Met. |
| Access mode, privilege, and reset value are defined for each mandatory CSR. | Met. |
| Per-core versus global scope is documented. | Met: all mandatory fast-window CSRs are per-core. |
| CSR side effects are listed. | Met. |

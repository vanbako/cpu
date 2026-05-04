# E04-S06: Mandatory MVP Additions

Story: E04-S06

Status: Complete

Normative source: `design.md`, section 17

Prerequisites:

- `spec/E02-S04-csr-instructions.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E06-S02-sealed-entry-capabilities.md`
- `spec/E08-S01-ll48-sc48.md`
- `spec/E08-S04-fence-instructions.md`

Related sources:

- `spec/E04-S02-integer-operation-set.md`
- `spec/E04-S03-memory-operation-set.md`
- `spec/E04-S05-capability-instruction-semantics.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E10-S05-cache-maintenance-operations.md`

## Decision

CPU v0.1 requires a small set of system, synchronization, capability-control, and control-flow instructions beyond the baseline integer and memory operations.

This story is the mandatory v0.1 ISA checklist for those additions. It does not duplicate each instruction's full semantics. The owning story listed in the tables below remains normative for operands, access checks, faults, atomicity, and detailed side effects.

An assembler, decoder, simulator, test suite, and RTL implementation claiming v0.1 support must implement every instruction listed as mandatory here.

## Mandatory Addition Checklist

The following instructions are mandatory v0.1 additions.

| Instruction | Required privilege | Owning story | Short description |
| --- | --- | --- | --- |
| `LL48` | `U` | E08-S01 | Atomic aligned 48-bit load-linked; installs a per-core reservation. |
| `SC48` | `U` | E08-S01 | Atomic aligned 48-bit store-conditional; returns `0` on success and `1` on non-trapping failure. |
| `FENCE` | `U` | E08-S04 | Orders older data-memory and cache-maintenance operations before younger data-memory and cache-maintenance operations. |
| `FENCE.I` | `K` | E08-S04 | Synchronizes local instruction fetch with prior code writes and instruction-cache maintenance. |
| `SFENCE.VM` | `K` | E08-S04 | Full local ITLB/DTLB invalidation and page-table store-to-translation ordering. |
| `SFENCE.VM.ASID` | `K` | E08-S04 | Local non-global TLB invalidation for one ASID. |
| `SFENCE.VM.VA` | `K` | E08-S04 | Local TLB invalidation for one virtual page across ASIDs, including global entries. |
| `SFENCE.VM.VA_ASID` | `K` | E08-S04 | Local non-global TLB invalidation for one virtual page and ASID. |
| `CSRRD` | CSR-specific | E02-S04 | Read a scalar CSR into an integer register. |
| `CSRWR` | CSR-specific | E02-S04 | Write an integer register value to a scalar CSR. |
| `CSRSET` | CSR-specific | E02-S04 | Atomic read, set bits, write CSR, and return the old CSR value. |
| `CSRCLR` | CSR-specific | E02-S04 | Atomic read, clear bits, write CSR, and return the old CSR value. |
| `CCSRRD` | `K` | E02-S05 | Read a special capability register into a general capability register. |
| `CCSRWR` | `K` | E02-S05 | Write a general capability register into a special capability register. |
| `EPCCRD` | `K` | E04-S04 | Slot-aware read of `EPCC` into a capability register plus integer slot result. |
| `EPCCWR` | `K` | E04-S04 | Slot-aware write of `EPCC` from a capability register plus integer slot operand. |
| `CALLC` | `U` | E06-S02 | Atomic call through a sealed entry capability with protected return-stack push. |
| `BRK` | `U` | E04-S04 | Precise synchronous breakpoint trap. |
| `SYS` | `U` | E04-S04 | Precise synchronous syscall/software trap. |
| `SCALL` | `U` | E04-S04 | Assembler synonym for `SYS` unless a future encoding story separates it. |
| `WFI` | `K` | E04-S04 | Wait-for-interrupt or low-power wait hint. |
| `PAUSE` | `U` | E04-S04 | Spin-wait hint with normal fall-through and no architectural side effects. |

`SYS` is the canonical mnemonic for the software-trap instruction. `SCALL` is a required assembler synonym for v0.1 source compatibility. A v0.1 binary encoding may implement one opcode for both mnemonics.

The `SFENCE.VM` rows are one mandatory instruction family. A v0.1 implementation must expose all four semantic forms unless the final binary encoding provides a single instruction with operands that can express the same `TLBI.ALL`, `TLBI.ASID`, `TLBI.VA`, and `TLBI.VA_ASID` effects.

## Required From Earlier Instruction Stories

The design note's MVP-required additions also include instructions already owned by earlier E04 stories. They remain mandatory in v0.1 and must be present in the same assembler, decoder, simulator, and RTL target.

| Instruction or family | Required privilege | Owning story | Short description |
| --- | --- | --- | --- |
| `CLC` | `U` | E04-S03/E04-S05 | Load one aligned 96-bit capability payload plus tag from memory. |
| `CSC` | `U` | E04-S03/E04-S05 | Store one aligned 96-bit capability payload plus tag to memory. |
| `CINCADDR` | `U` | E04-S05 | Add a signed cell offset to a capability cursor. |
| `CSETBOUNDS` | `U` | E04-S05 | Narrow a capability to bounds beginning at the source cursor. |
| `CANDPERM` | `U` | E04-S05 | Clear capability permission bits by mask. |
| `CSEAL` | `U` | E04-S05 | Seal an unsealed capability with authorized object type. |
| `CUNSEAL` | `U` | E04-S05 | Unseal a sealed capability with matching authority, except reserved architectural object types. |
| `SETcc` | `U` | E04-S02 | Write integer `1` or `0` according to a condition-code predicate. |
| `CMOVcc` | `U` | E04-S02 | Conditionally copy an integer register according to a condition-code predicate. |

This story does not reopen the complete integer, memory, capability, or control-transfer instruction lists. It records that these design-required additions are not optional extensions.

## Privilege Rules

Privilege classification follows E07-S01 and the owning instruction stories.

Summary:

- User mode may execute `LL48`, `SC48`, `FENCE`, `CALLC`, `BRK`, `SYS`/`SCALL`, `PAUSE`, `CLC`, `CSC`, ordinary capability derivation instructions, `SETcc`, and `CMOVcc`, subject to their non-privilege checks.
- `FENCE.I`, every `SFENCE.VM` form, `CCSRRD`, `CCSRWR`, `EPCCRD`, `EPCCWR`, and `WFI` require kernel mode.
- Scalar CSR instructions use the selected CSR's read/write privilege rules rather than one fixed instruction privilege.
- Kernel mode does not bypass capability authority, page permission, memory-type legality, alignment, or instruction-specific semantic checks.

User-mode execution of a kernel-only instruction raises the privilege exception assigned by the owning story, normally `PRIVILEGE_FAULT`. User-mode scalar CSR access to a kernel-only CSR raises `CSR_PRIVILEGE_FAULT`. User-mode CCSR access raises `CCSR_PRIVILEGE_FAULT`.

## Encoding Coverage Contract

This story owns the v0.1 opcode coverage requirement for the mandatory additions.

Required assembler/decoder behavior:

- Every mandatory instruction in this story must have at least one canonical accepted assembly spelling.
- Every mandatory instruction must have an encodable binary form or documented synonym mapping in the v0.1 target.
- Every canonical binary form must obey the instruction placement rules from E04-S01.
- Any compact alias must be semantically identical to the corresponding canonical form.
- Reserved or malformed encodings must raise the illegal-instruction exception assigned by E07-S02 and the relevant owning instruction story.

The exact numeric opcode bit assignments may be held in a separate opcode table generated from this checklist. That table must not omit a mandatory instruction or add an excluded instruction to the required v0.1 set.

## Optional Future Instructions Excluded From v0.1

The following instructions are not mandatory v0.1 instructions:

| Instruction or family | v0.1 status | Rationale |
| --- | --- | --- |
| `CAS48` | Excluded, optional future extension. | `LL48`/`SC48` are the mandatory MVP atomic primitive. |
| `CAS96` | Excluded, optional future extension. | Capability-width compare-and-swap needs additional tag and authority rules. |
| Generic `AMO*` read-modify-write family | Excluded, optional future extension. | No mandatory v0.1 atomic operation beyond `LL48`/`SC48`. |
| Coherent-I/O or tag-aware DMA instructions | Excluded, optional future extension. | v0.1 I/O is noncoherent and tag-unaware. |
| User-mode `FENCE.I` form | Excluded as an architectural instruction. | v0.1 exposes instruction-cache synchronization through kernel `FENCE.I` or a kernel ABI. |
| Wider or narrower mandatory MMIO load/store forms | Excluded. | v0.1 mandatory memory movement is cell-addressed `LD48`/`ST48`, `CLC`/`CSC`, and `LL48`/`SC48`. |

A future extension may add any excluded instruction only with its own compatibility story, opcode allocation, privilege rule, fault behavior, and tests. Existing v0.1 software must not require those instructions.

## Implementation Checklist

Minimum v0.1 implementation work items:

- Assembler accepts every mandatory mnemonic and required synonym listed here.
- Decoder recognizes every mandatory binary form and rejects reserved forms.
- Disassembler prints canonical names, with `SCALL` accepted as a source synonym for `SYS`.
- Simulator implements instruction semantics by delegating to the owning story behavior.
- RTL implements or traps exactly according to the mandatory versus excluded status.
- Conformance tests cover at least one successful execution and one privilege or malformed-encoding failure for every privileged mandatory instruction.
- ISA completeness review verifies that `CAS48`, `CAS96`, and generic `AMO*` are absent from the required baseline.

## Out of Scope for This Story

- Full semantic duplication for instructions owned by earlier stories.
- Numeric opcode bitfield layout and binary encoding diagrams, except for the coverage requirement above.
- Microarchitectural implementation details.
- Optional extensions beyond the required v0.1 baseline.
- Toolchain ABI conventions beyond required mnemonic availability.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- The ISA list includes `LL48` and `SC48`.
- The ISA list includes `FENCE`, `FENCE.I`, and the four `SFENCE.VM` semantic forms.
- The ISA list includes `CSRRD`, `CSRWR`, `CSRSET`, and `CSRCLR`.
- The ISA list includes `CCSRRD` and `CCSRWR`.
- The ISA list includes `EPCCRD` and `EPCCWR`.
- The ISA list includes `CALLC`.
- The ISA list includes `BRK`.
- The assembler accepts `SYS` and `SCALL` for the software-trap instruction.
- The ISA list includes `WFI` and `PAUSE`.
- User-mode `FENCE` and `PAUSE` execute without privilege fault.
- User-mode `FENCE.I`, `SFENCE.VM`, `CCSRRD`, `CCSRWR`, `EPCCRD`, `EPCCWR`, and `WFI` raise privilege faults.
- Scalar CSR instruction privilege follows the selected CSR.
- `CAS48`, `CAS96`, and generic `AMO*` are not required v0.1 instructions.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `LL48`, `SC48`, `FENCE`, `FENCE.I`, `SFENCE.VM`, `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR`, `CCSRRD`, `CCSRWR`, `EPCCRD`, `EPCCWR`, `CALLC`, `BRK`, `SYS` or `SCALL`, `WFI`, and `PAUSE` are in the v0.1 ISA list. | Met. |
| Each instruction has a short description and privilege rule. | Met. |
| Optional future instructions such as `CAS48` and `CAS96` are excluded from required v0.1. | Met. |

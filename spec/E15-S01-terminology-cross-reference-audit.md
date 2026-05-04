# E15-S01: Terminology and Cross-reference Audit

Story: E15-S01

Status: Complete

Prerequisites:

- Completed E01-E14 backlog

Audit tool:

- `tools/spec_reference_check.py`

## Decision

The completed E01-E14 v0.1 specification set has a stable story/artifact structure and no blocking terminology, ownership, or cross-reference inconsistencies.

Two non-blocking aliases are accepted:

- `PC subslot` is accepted as the historical E01-S05 story title and file name. The canonical runtime term is `hidden instruction slot` or `PCC.slot`.
- `WFI parked state` is accepted as prose that refers to the lifecycle state `WFI_PARKED`.

Future edits should prefer the canonical terms above, but no completed spec artifact needs a semantic correction for E15-S01.

## Audit Scope

This audit covers:

- `agile-v0.1.md`
- `design.md`
- All completed E01-E13 story artifacts in `spec/`
- All completed E14 spike artifacts in `spikes/`
- Existing support tools in `tools/`

E15 future-story artifact paths are planned work and are not treated as missing E01-E14 artifacts.

## Reference Check Result

Command:

```text
python tools\spec_reference_check.py
```

Observed result:

```text
Required story IDs checked: 70
Artifact story IDs found: 70
Markdown files scanned: 72
Issues: 0
```

The checker validates:

- Every completed E01-E14 detailed backlog story has a matching story artifact or spike artifact.
- Every completed artifact title begins with its story ID.
- Every completed artifact includes a matching `Story:` header.
- Every completed artifact includes a recognized `Status:` header.
- Story IDs referenced in markdown are known to the backlog or artifact set.
- Local markdown/tool references outside planned future-story blocks resolve on disk.

## Canonical Glossary

### Architectural Terms

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `cell` | E01-S01 | The 24-bit architectural address unit. |
| `cell address` | E01-S01 | Architectural memory address. No architectural byte addresses exist in v0.1. |
| `byte` | E01-S01 | Host/tooling concept only unless explicitly discussing external representation. |
| `48-bit integer object` | E01-S01, E04-S03 | Naturally aligned 2-cell integer memory object. |
| `96-bit capability object` | E01-S01, E03-S01, E03-S04 | Naturally aligned 4-cell capability payload plus out-of-band tag. |
| `capability slot` | E03-S04, E10-S02 | Naturally aligned 4-cell storage unit with one tag bit. |
| `fetch group` | E04-S01 | A 48-bit, 2-cell instruction fetch unit. |
| `hidden instruction slot` | E01-S05 | Slot bit for packed 12-bit instructions. Accepted aliases: `hidden slot`, `PC subslot`, `PCC.slot`, `EPCC.slot`. |
| `slot 0` | E01-S05 | First instruction position within a cell. All explicit control-transfer targets enter here. |
| `slot 1` | E01-S05 | Second 12-bit instruction position in a cell, reachable only by legal sequential fall-through or slot-aware restore. |
| `base page` | E09-S01 | `2^11` cells in v0.1. |
| `cache line` | E10-S02 | 16 cells, 48 bytes, four capability slots. |
| `virtual address` | E09-S01 | 48-bit cell address before translation. |
| `physical address` | E09-S01 | 48-bit cell address after translation. |
| `ASID` | E09-S02, E09-S03 | Address-space identifier used by translation, TLB matching, and predictor context rules. |
| `TLB` | E09-S03 | Translation lookaside buffer. v0.1 has private ITLB and DTLB per core. |
| `PTE` | E09-S05 | 48-bit page-table entry. |
| `TSO-like memory model` | E08-S03 | Coherent multi-copy-atomic CPU memory model for normal coherent cacheable memory. |
| `noncoherent DMA` | E10-S04 | Device access outside CPU cache coherence. |
| `platform profile` | E02-S03, E11-S01, E11-S03 | Platform-specific binding for values or mechanisms explicitly left outside the mandatory architecture. |
| `implementation-defined` | Multiple | Implementation choice that must be deterministic and documented where required. |

### Register and Control-state Names

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `D0-D15` | E01-S02 | General 48-bit integer registers. |
| `C0-C7` | E01-S03 | General capability registers. |
| `PCC` | E01-S04, E06-S01 | Program-counter capability; authorizes instruction fetch and carries cursor plus hidden slot state. |
| `DSC` | E01-S04, E05-S03 | Data-stack capability. |
| `RSC` | E01-S04, E05-S04, E06-S04 | Protected return-stack capability. |
| `DDC` | E01-S04 | Default data capability for explicit DDC-form accesses. |
| `EPCC` | E01-S04, E07-S04 | Exception program-counter capability plus hidden slot. |
| `TVC` | E01-S04, E07-S04, E07-S05 | Trap-vector capability. |
| `KSC` | E01-S04, E07-S04 | Kernel trap-stack capability. |
| `KRC` | E01-S04, E11-S02 | Kernel root capability. |
| `CSR` | E02-S01 | Scalar control/status register namespace. |
| `CCSR` | E01-S04, E02-S05 | Capability control/status register index space for special capability registers. |
| `SR` | E01-S06, E02-S02 | Status register. Contains flags, privilege, interrupt, exception-level, and slot mirror state. |
| `COREID` | E02-S02 | Stable per-core identifier. |
| `CYCLE` | E02-S02, E12-S04 | Mandatory cycle counter. |
| `INSTRET` | E02-S02, E12-S04 | Mandatory retired-instruction counter. |
| `TVEC` | E02-S02, E07-S04, E07-S05 | Scalar trap-vector control consumed with `TVC`. |
| `CAUSE` | E02-S02, E07-S02, E07-S04 | Trap-class cause CSR. |
| `TVAL` | E02-S02, E07-S02, E07-S04 | Trap value CSR, normally a cell address or scalar diagnostic value. |
| `SCRATCH` | E02-S02 | Kernel scratch CSR. |
| `IENABLE` | E02-S02, E07-S05 | Interrupt-enable CSR. |
| `IPENDING` | E02-S02, E07-S05 | Interrupt-pending CSR. |
| `TIMER` | E02-S02, E07-S05, E12-S04 | Architectural timer source. |
| `TIMECMP` | E02-S02, E07-S05 | Timer compare CSR. |
| `SATP` | E02-S02, E09-S02 | Translation mode, ASID, and root PPN state. |
| `DEBUGCTL` | E02-S02, E12-S01, E12-S03 | Debug control CSR. |
| `PERFSEL` | E02-S02, E12-S05 | Performance-counter selector/configuration CSR. |
| `PMC0-PMC7` | E02-S03, E12-S05 | Extended performance monitor counters. |
| `CACHECTL` | E02-S03, E10-S05 | Assigned cache-control CSR reservation. Instruction semantics remain owned by E10-S05. |
| `TLBCTL` | E02-S03, E09-S03, E08-S04 | Assigned TLB-control CSR reservation. Instruction semantics remain owned by E09-S03 and E08-S04. |
| `FAULTCAPIDX` | E02-S03, E03-S06, E07-S04 | Capability operand reporting CSR. |
| `CAPCAUSE` | E02-S03, E03-S06, E07-S04 | Capability-specific fault reason CSR. |

### Capability Terms

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `tag` | E01-S03, E03-S01, E03-S04 | Out-of-band validity bit for registers and memory capability slots. |
| `cursor/address` | E03-S01 | 48-bit current cell address in a capability payload. Accepted alias: `cursor`. |
| `bounds metadata` | E03-S01 | 30-bit compressed representation of half-open bounds. |
| `[base, top)` | E03-S01 | Half-open decoded bounds interval. |
| `permissions` | E03-S02 | 8-bit capability permission field. |
| `LD` | E03-S02 | Load-data permission. |
| `ST` | E03-S02 | Store-data permission. |
| `EX` | E03-S02 | Execute permission. |
| `LC` | E03-S02 | Load-capability permission. |
| `SC` | E03-S02 | Store-capability permission. |
| `SL` | E03-S02, E03-S05 | Store-local-capability permission. |
| `SEAL` | E03-S02, E03-S03 | Seal permission. |
| `UNSEAL` | E03-S02, E03-S03 | Unseal permission. |
| `object type` | E03-S01, E03-S03 | 8-bit sealing type. Accepted alias: `otype`. |
| `flags` | E03-S01, E03-S05 | Capability flag field, including global/local state. |
| `G` | E03-S05 | Global capability flag. |
| `local capability` | E03-S05 | Capability whose storage is restricted by `SL` rules. |
| `sealed capability` | E03-S03, E06-S02, E06-S03 | Capability sealed with an object type and unusable for ordinary dereference until unsealed by valid authority. |
| `OTYPE_ENTRY` | E06-S02 | Architectural object type for sealed entry capabilities. |
| `OTYPE_RETURN` | E06-S03 | Architectural object type for sealed return capabilities. |

### Exception, Interrupt, and Debug Cause Names

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `NONE` | E07-S02, E02-S03 | No exception or no capability-specific cause, depending on the reporting field. |
| `ILLEGAL_INSTRUCTION` | E07-S02 | Malformed, unsupported, or reserved instruction form. |
| `BREAKPOINT` | E07-S02, E04-S04, E12-S01 | Ordinary `BRK` breakpoint trap when `DEBUGCTL.BRKHALT=0`; hardware/debug breakpoint events report `DEBUG_HALT`. |
| `PRIVILEGE_FAULT` | E07-S02, E07-S01 | Insufficient privilege for an instruction or operation. |
| `DIVIDE_BY_ZERO` | E07-S02, E04-S02 | Divide or modulo by zero. |
| `ALIGN_FAULT` | E07-S02, E01-S05, E04-S01 | Misaligned memory object, illegal slot, illegal fetch placement, or explicit slot-1 target. |
| `ACCESS_FAULT` | E07-S02, E09-S06, E09-S07 | Physical, memory-type, bus, or platform access rejection. |
| `PAGE_FAULT` | E07-S02, E09-S05, E09-S07 | Translation or page permission fault. |
| `SYSCALL_TRAP` | E07-S02, E04-S04 | `SYS` or `SCALL` software trap. |
| `CAPABILITY_TAG_FAULT` | E07-S02, E03-S06 | Invalid capability tag. |
| `CAPABILITY_BOUNDS_FAULT` | E07-S02, E03-S06 | Capability bounds violation. |
| `CAPABILITY_PERMISSION_FAULT` | E07-S02, E03-S06 | Missing capability permission. |
| `CAPABILITY_SEAL_TYPE_FAULT` | E07-S02, E03-S06 | Incorrect sealed use or object-type authority mismatch. |
| `CAPABILITY_LOCAL_STORE_FAULT` | E07-S02, E03-S05, E03-S06 | Local capability stored without `SL`. |
| `DEBUG_HALT` | E07-S02, E12-S01, E12-S02, E12-S03 | Debug event trap class for external halt, `BRK` debug path, hardware breakpoint/watchpoint, single-step, and entry-failure fallback. |
| `RESERVED_CSR_FAULT` | E07-S02, E02-S01, E02-S03, E02-S04 | Access to reserved, future, unimplemented, or undocumented scalar CSR. |
| `ILLEGAL_CSR_READ` | E07-S02, E02-S04 | CSR exists but cannot be read by the requested operation. |
| `ILLEGAL_CSR_WRITE` | E07-S02, E02-S04 | CSR exists but cannot be written with the requested value or operation. |
| `CSR_PRIVILEGE_FAULT` | E07-S02, E02-S04 | Scalar CSR access lacks privilege. |
| `RESERVED_CCSR_FAULT` | E07-S02, E02-S05 | Capability CSR index is reserved or unimplemented. |
| `ILLEGAL_CCSR_ACCESS` | E07-S02, E02-S05 | CCSR exists but does not support the requested operation. |
| `CCSR_PRIVILEGE_FAULT` | E07-S02, E02-S05 | CCSR access lacks privilege. |
| `RETURN_STACK_UNDERFLOW` | E07-S02, E05-S04, E06-S04 | Return pop has no valid active return entry. |
| `RETURN_STACK_OVERFLOW` | E07-S02, E05-S04, E06-S04 | Return push target is outside `RSC` bounds. |
| `RETURN_STACK_PERMISSION_FAULT` | E07-S02, E06-S04 | Protected return-stack access lacks authority or ordinary access targets protected storage. |
| `TAG` | E02-S03, E03-S06 | `CAPCAUSE` value for tag fault. |
| `BOUNDS` | E02-S03, E03-S06 | `CAPCAUSE` value for bounds fault. |
| `PERMISSION` | E02-S03, E03-S06 | `CAPCAUSE` value for permission fault. |
| `SEAL_TYPE` | E02-S03, E03-S06 | `CAPCAUSE` value for seal/type fault. |
| `LOCAL_STORE` | E02-S03, E03-S06 | `CAPCAUSE` value for local-store fault. |
| `DCAUSE` | E12-S01 | Debug-specific cause field. Numeric values are owned by E12-S01 and refinements. |

### Memory-type Names

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `NORMAL_COHERENT` | E09-S06, E10-S03 | Cacheable normal memory participating in CPU coherence. Accepted prose alias: normal coherent cacheable memory. |
| `NORMAL_UNCACHEABLE` | E09-S06 | Normal memory that bypasses CPU data-cache allocation. |
| `DEVICE_ORDERED` | E09-S06 | Device or MMIO memory with ordered side-effecting accesses. Accepted prose alias: device ordered memory. |
| `reserved memory type` | E09-S05, E09-S06 | Memory-type encoding not implemented by v0.1 and required to fault when used as specified. |

### Instruction Names

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| Integer operation set | E04-S02 | Baseline integer ALU, compare, branch-condition, multiply, divide, and modulo semantics. |
| `LD48` | E04-S03 | Load a naturally aligned 48-bit integer object. |
| `ST48` | E04-S03 | Store a naturally aligned 48-bit integer object and clear overlapped capability tags. |
| `CLC` | E04-S03, E04-S05 | Load a naturally aligned capability payload plus tag. |
| `CSC` | E04-S03, E04-S05 | Store a naturally aligned capability payload plus tag. |
| `CSETADDR` | E03-S01, E04-S05 | Set capability cursor/address. |
| `CINCADDR` | E03-S01, E04-S05 | Increment capability cursor/address by signed cell offset. |
| `CSETBOUNDS` | E03-S01, E04-S05 | Narrow capability bounds. |
| `CANDPERM` | E03-S02, E04-S05 | Clear capability permission bits. |
| `CSEAL` | E03-S03, E04-S05 | Seal an unsealed capability. |
| `CUNSEAL` | E03-S03, E04-S05 | Unseal a sealed capability. |
| `CALL` | E04-S04, E06-S03 | Direct call with protected return-stack push. |
| `CALLC` | E04-S04, E06-S02 | Call through sealed entry capability with protected return-stack push. |
| `RET` | E04-S04, E06-S03 | Return through protected return-stack pop. |
| `JMP` | E04-S04 | Capability-target jump, slot 0 target only. |
| `Bcc` | E04-S04, E13-S04 | Conditional direct branch. |
| `SETcc` | E04-S02, E04-S06 | Set integer result from condition-code predicate. |
| `CMOVcc` | E04-S02, E04-S06 | Conditional integer move. |
| `BRK` | E04-S04, E12-S01 | Breakpoint/debug instruction. |
| `SYS` | E04-S04, E04-S06 | Canonical software-trap mnemonic. |
| `SCALL` | E04-S04, E04-S06 | Required assembler synonym for `SYS`. |
| `IRET` | E04-S04, E07-S06, E12-S01 | Return from trap, interrupt, or debug-monitor state. |
| `WFI` | E04-S04, E07-S05, E11-S03 | Wait-for-interrupt or low-power wait hint. |
| `PAUSE` | E04-S04 | Spin-wait hint. |
| `LL48` | E08-S01 | Load-linked 48-bit atomic primitive. |
| `SC48` | E08-S01 | Store-conditional 48-bit atomic primitive. |
| `FENCE` | E08-S04 | Data-memory and cache-maintenance ordering instruction. |
| `FENCE.I` | E08-S04 | Local instruction-fetch synchronization instruction. |
| `SFENCE.VM` family | E08-S04 | Local TLB invalidation and translation ordering forms. |
| `CACHE.CLEAN` | E10-S05 | Privileged cache clean operation. |
| `CACHE.INVAL` | E10-S05 | Privileged cache invalidate operation. |
| `CACHE.CLEANINVAL` | E10-S05 | Privileged clean-and-invalidate operation. |
| `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR` | E02-S04 | Scalar CSR access instruction forms. |
| `CCSRRD`, `CCSRWR` | E02-S05 | Capability CSR access instruction forms. |
| `EPCCRD`, `EPCCWR` | E04-S04 | Slot-aware `EPCC` read/write helpers. |

### State Names

| Canonical term | Owning story | Meaning and accepted aliases |
| --- | --- | --- |
| `U` | E07-S01 | User privilege mode. |
| `K` | E07-S01 | Kernel privilege mode. |
| `RUNNING` | E11-S01, E12-S01 | Core is fetching, executing, and retiring ordinary architectural instructions. |
| `STOPPED` | E11-S01, E11-S03 | Secondary core is not fetching or retiring ordinary instructions until startup. |
| `WFI_PARKED` | E11-S01, E11-S03 | Reset-time parked secondary-core state. Accepted prose alias: WFI parked state. |
| `START_PENDING` | E11-S03 | Secondary-core start signal accepted; mailbox validation or startup install in progress. |
| `STARTED` | E11-S03 | Secondary core has accepted a valid mailbox and may execute from requested entry state. |
| `START_FAILED` | E11-S03 | Secondary-core startup failed before requested entry state became executable. |
| `EMPTY`, `READY`, `CONSUMED`, `FAILED` | E11-S03 | Logical start-mailbox states. |
| `DEBUG_HALTED` | E12-S01 | Core is stopped for external debugger control and retires no ordinary instructions. |
| `DEBUG_MONITOR` | E12-S01 | Privileged debug-monitor software execution entered through debug vector. |
| `STEP_ACTIVE` | E12-S03 | Hidden single-step arm state. |

## Shared-subject Ownership Map

| Subject | Primary owner | Refining owners | Audit disposition |
| --- | --- | --- | --- |
| Story/artifact identity | `agile-v0.1.md` | Individual story artifacts | Pass. Story IDs and artifact IDs match for completed E01-E14. |
| `PCC` payload/tag | E01-S04 | E06-S01, E07-S04, E11-S02, E12-S01, E13-S01 | Pass. E01-S04 owns register identity; later stories own fetch, trap, reset, debug, and pipeline effects. |
| `PCC.slot` and `EPCC.slot` | E01-S05 | E01-S04, E01-S06, E04-S04, E07-S04, E12-S03, E13-S01 | Pass with alias note. Canonical term is hidden instruction slot. |
| `RSC` and protected return state | E05-S04 | E06-S03, E06-S04, E07-S03, E12-S01 | Pass. ABI, sealed return, protected access, precision, and debug access have distinct owners. |
| `SR` | E01-S06 | E02-S02, E07-S04, E07-S06, E12-S01 | Pass. Bit layout, CSR access, trap save/restore, and debug monitor behavior are separately owned. |
| Scalar CSR namespace | E02-S01 | E02-S02, E02-S03, E02-S04, E12-S04, E12-S05 | Pass. Namespace, mandatory rows, extended reservations, access instructions, and counters have clear ownership. |
| CCSR namespace | E01-S04 | E02-S05 | Pass. Register map and access semantics are not conflated with scalar CSR namespace. |
| `CAUSE` and `TVAL` | E02-S02 | E07-S02, E07-S04, instruction-specific stories | Pass. CSR allocation and trap-reporting semantics are separated. |
| `CAPCAUSE` and `FAULTCAPIDX` | E02-S03 | E03-S06, E07-S02, E07-S04 | Pass. Extended CSR allocation, capability reason names, and trap-entry population are separated. |
| Cache maintenance | E10-S05 | E08-S04, E09-S06, E10-S04 | Pass. Operation semantics, fence interaction, memory types, and DMA protocol are separately owned. |
| TLB invalidation | E09-S03 | E08-S04, E09-S02, E13-S04 | Pass. TLB model, `SFENCE.VM`, `SATP`, and predictor context rules have distinct owners. |
| Debug state | E12-S01 | E12-S02, E12-S03, E12-S04, E12-S05 | Pass. Halt, comparators, single-step, counters, and event counters have distinct owners. |
| Memory types | E09-S06 | E09-S05, E08-S03, E08-S04, E10-S03, E10-S04, E10-S05 | Pass. PTE encoding and memory-system behavior are separated. |
| Secondary-core lifecycle | E11-S01 | E11-S03, E09-S03, E12-S01 | Pass with alias note for `WFI_PARKED`. |

## Normative Language Taxonomy

| Language | Meaning in v0.1 specs | Audit disposition |
| --- | --- | --- |
| `must`, `must not`, `required` | Mandatory architectural requirement. | Accepted as normative. |
| `may` | Permitted behavior within stated bounds. | Accepted as normative permission. |
| `should` | Recommendation, not mandatory unless paired with a `must`. | Accepted as non-normative guidance unless the local paragraph states otherwise. |
| `reserved` | Architecturally held for future use or unavailable encoding/state. | Accepted when paired with access behavior or later owner. Numeric collision audit is E15-S02. |
| `deferred to E##-S##` | Owner is explicitly named by story ID. | Accepted. Unknown story IDs are checked by the reference checker. |
| `platform profile` or `platform-defined` | Platform must document the value or mechanism. | Accepted when the base architecture does not require a single value. |
| `implementation-defined` | Implementation must document the choice when required by the owning story. | Accepted. |
| `out of scope` | Not required for v0.1. | Accepted when not needed to satisfy the story's acceptance criteria. |
| `example`, `rationale`, `notes` | Explanatory material. | Accepted as non-normative unless a local requirement says otherwise. |

## Findings

| Finding | Severity | Disposition |
| --- | --- | --- |
| E15-S01-F01: Completed E01-E14 story IDs and artifacts are structurally consistent. | Pass | `tools/spec_reference_check.py` found zero issues. |
| E15-S01-F02: Planned E15 artifacts are referenced from the newly added backlog epic but do not exist yet. | Expected | The checker excludes future-story blocks unless that epic is explicitly included. |
| E15-S01-F03: `PC subslot` appears as the E01-S05 title/file wording while most normative prose uses `hidden slot` or `PCC.slot`. | Non-blocking wording | Treat `PC subslot` as a historical alias. Future prose should prefer `hidden instruction slot` or the concrete state name. |
| E15-S01-F04: `WFI parked state` appears in backlog acceptance wording while completed specs use `WFI_PARKED`. | Non-blocking wording | Treat prose as an alias for `WFI_PARKED`. Future prose should use the state name. |

## Handoff to Later Consistency Stories

E15-S01 intentionally does not prove that numeric values, bitfields, or event-priority matrices are mutually consistent. Those checks belong to:

- `E15-S02` for constants, encodings, and bitfields.
- `E15-S03` for state-transition composition.
- `E15-S04` for trap, interrupt, exception, and debug priority.
- `E15-S05` for memory, capability, MMU, cache, ordering, DMA, and tag composition.
- `E15-S06` for software-facing ABI, firmware, debug, and toolchain contracts.

The glossary and ownership map in this story are the canonical starting point for those audits.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A glossary covers architectural terms, CSR names, CCSR names, capability fields, exception names, memory-type names, instruction names, and state names. | Met. |
| Every story artifact listed in `agile-v0.1.md` exists and is linked from the correct backlog story. | Met for completed E01-E14 backlog; E15 future artifacts are planned work. |
| Cross-story references use stable story IDs and artifact paths. | Met for completed E01-E14 baseline. |
| Normative requirements are distinguishable from examples, notes, rationale, deferred items, and platform-profile choices. | Met by the taxonomy above; no blocking ambiguous category was found. |
| Duplicate terms and aliases are either consolidated or explicitly defined as aliases. | Met: `PC subslot` and `WFI parked state` are explicitly aliased to canonical terms. |
| Story ownership is clear for shared subjects such as `PCC`, `RSC`, `SR`, `CAUSE`, `CAPCAUSE`, cache maintenance, TLB invalidation, and debug state. | Met by the ownership map. |

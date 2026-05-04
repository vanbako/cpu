# E08-S04: Fence Instructions

Story: E08-S04

Status: Complete

Normative source: `design.md`, sections 11.2, 12.4, and 13

Prerequisites:

- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S03-tlb-model.md`
- `spec/E10-S05-cache-maintenance-operations.md`

Related sources:

- `spec/E07-S01-privilege-levels.md`
- `spec/E09-S06-page-memory-types.md`
- `spec/E10-S04-noncoherent-dma-policy.md`
- `spec/E10-S03-cpu-coherence-protocol.md`

## Decision

CPU v0.1 defines these mandatory fence and translation-maintenance instructions:

| Instruction family | Required privilege | Purpose |
| --- | --- | --- |
| `FENCE` | `U` | Orders data memory, device memory, DMA handoff, and cache-maintenance boundaries. |
| `FENCE.I` | `K` | Synchronizes local instruction fetch with prior code writes and instruction-cache maintenance. |
| `SFENCE.VM` | `K` | Orders page-table updates with local translation use and invalidates local TLB entries. |

`FENCE` is executable in both user and kernel mode. `FENCE.I` and `SFENCE.VM` are kernel-only in v0.1.

The final opcode bit assignments are owned by E04-S06. This story defines the architectural effects required of the mandatory instruction forms.

## Data-memory `FENCE`

`FENCE` has no operands.

Architectural effect:

```text
FENCE
```

All older data-memory and cache-maintenance operations by the executing core must be complete before any younger data-memory or cache-maintenance operation by that core is allowed to execute.

For `FENCE`, data-memory operations include:

- `LD48`
- `ST48`
- `CLC`
- `CSC`
- `LL48`
- `SC48`
- Data-stack and return-stack memory operations implemented using those memory operations
- `DEVICE_ORDERED` `LD48` and `ST48` MMIO transactions
- `CACHE.CLEAN`
- `CACHE.INVAL`
- `CACHE.CLEANINVAL`

Completion means:

| Operation class | Completion point before younger data access |
| --- | --- |
| `NORMAL_COHERENT` loads | Load value has been obtained from the allowed coherent source. |
| `NORMAL_COHERENT` stores | Store payload and tag effects are globally visible at the CPU coherence point. |
| `NORMAL_UNCACHEABLE` loads/stores | Transaction is complete at the backing-memory serialization point. |
| `DEVICE_ORDERED` loads/stores | Device transaction is accepted and ordered by the device/interconnect path. |
| `CACHE.*` operations | The maintenance effect required by E10-S05 has completed before the instruction retires. |

`FENCE` does not create a memory access, does not check page permissions, and does not require a capability operand.

## `FENCE` and TSO

For normal coherent cacheable memory, `FENCE` is the full data-memory barrier in the TSO-like model from E08-S03.

Minimum requirements:

- Older stores drain to global CPU visibility before younger loads, stores, atomics, or cache maintenance proceed.
- Older loads complete before younger data-memory operations proceed.
- Older capability payload writes and tag updates are ordered with younger capability loads and stores.
- Older `LL48` and `SC48` memory effects are ordered as their load or store class requires.

The store-buffering litmus with `FENCE` between each store and later load must forbid both loads from reading the old values, as required by E08-S03.

`FENCE` does not flush the data cache. It orders already-issued data memory operations; it does not clean, invalidate, allocate, or write back cache lines except as required to make older stores globally visible.

## `FENCE` and Device/DMA Sequences

`FENCE` is required at normal-memory/device boundaries.

Required portable sequences:

| Scenario | Sequence |
| --- | --- |
| CPU writes coherent buffer, then device reads it | CPU stores; `FENCE`; `CACHE.CLEAN`; `FENCE`; `ST48` device doorbell. |
| Device writes coherent buffer, then CPU reads it | Observe device completion; `FENCE`; `CACHE.INVAL`; `FENCE`; CPU loads. |
| Bidirectional coherent DMA buffer | CPU stores if any; `FENCE`; `CACHE.CLEANINVAL`; `FENCE`; doorbell; completion; `FENCE`; `CACHE.INVAL`; `FENCE`; CPU loads. |
| CPU writes uncacheable buffer, then device reads it | CPU stores; `FENCE`; `ST48` device doorbell. |
| Device writes uncacheable buffer, then CPU reads it | Observe device completion; `FENCE`; CPU loads. |
| CPU configures normal memory, then writes device registers | CPU stores; `FENCE`; device register stores. |
| CPU observes device status, then consumes normal memory | Device status load or interrupt observation; `FENCE`; CPU loads or cache maintenance. |

`FENCE` does not make DMA coherent by itself. For `NORMAL_COHERENT` buffers, the required cache maintenance still must be performed.

## `FENCE.I`

`FENCE.I` has no operands and is kernel-only.

Architectural effect:

```text
FENCE.I
```

After `FENCE.I` retires on a core, younger instruction fetch on that core must not use stale instruction bytes from before the `FENCE.I`.

Required local effects:

- Discard or invalidate local L1 instruction-cache state as needed.
- Discard local instruction prefetch, fetch queue, decode queue, and decoded-instruction state as needed.
- Ensure younger instruction fetch observes instruction bytes that are visible through the coherent hierarchy or backing memory according to the memory type.
- Preserve architectural capability and page-permission checks for younger fetches.

`FENCE.I` is local to the executing core. It does not invalidate other cores' L1 instruction caches and does not by itself send an IPI.

`FENCE.I` does not:

- Clean or invalidate L1 data-cache state.
- Modify L2 data-cache state.
- Invalidate ITLB or DTLB entries.
- Modify page-table memory.
- Modify branch-predictor state unless the implementation needs to do so to prevent stale instruction delivery.

If an implementation has branch-predictor, target-cache, or predecode structures that contain instruction bytes or translation-dependent fetch metadata, `FENCE.I` must invalidate or retag that state so it cannot bypass fresh instruction fetch and permission checks. Predictors that contain only hints may be retained.

## Code-write Synchronization

For code written through CPU data stores to `NORMAL_COHERENT` memory and later executed on the same core:

```text
store new code
FENCE
FENCE.I
execute new code
```

`FENCE` makes the code stores globally visible in the CPU coherent domain. `FENCE.I` prevents younger fetch from using stale local instruction-cache or predecode state.

For code written by one core and executed by another core:

```text
writer stores new code
writer FENCE
writer requests remote instruction synchronization
target FENCE.I
target FENCE
target acknowledges completion
writer waits for acknowledgment before starting target execution
```

The remote request and acknowledgment mechanism is software and platform defined, normally using an IPI and coherent memory flags. The target core must execute `FENCE.I` before acknowledging completion.

For code loaded by a noncoherent device or DMA engine into a `NORMAL_COHERENT` buffer, software must first perform the DMA completion sequence from E10-S04 and E10-S05:

```text
observe device completion
FENCE
CACHE.INVAL code_range
FENCE
FENCE.I
execute loaded code
```

For code stores that must also be visible to agents outside the CPU coherent domain, privileged software may use the conservative clean sequence from E10-S05:

```text
store new code
FENCE
CACHE.CLEAN code_range
FENCE.I
```

`FENCE.I` is kernel-only in v0.1. User-mode software that needs instruction-fetch synchronization must use a kernel ABI such as a syscall. The kernel ABI may validate the requested range, perform any required cache maintenance, and execute `FENCE.I` locally or remotely.

## `SFENCE.VM` Instruction Family

`SFENCE.VM` is the mandatory local TLB invalidation and page-table ordering family for v0.1.

All `SFENCE.VM` forms are kernel-only and have no destination register.

Required semantic forms:

| Instruction form | Source registers | E09-S03 operation |
| --- | --- | --- |
| `SFENCE.VM` | none | `TLBI.ALL` |
| `SFENCE.VM.ASID Da` | scalar ASID register | `TLBI.ASID(asid)` |
| `SFENCE.VM.VA Dv` | scalar virtual address register | `TLBI.VA(va)` |
| `SFENCE.VM.VA_ASID Dv, Da` | scalar virtual address and ASID registers | `TLBI.VA_ASID(va, asid)` |

`Dv[47:0]` is a virtual cell address. The low 11 page-offset bits are ignored for matching; invalidation uses `Dv[47:11]`.

`Da[7:0]` is the ASID operand. Upper scalar bits are ignored.

The instruction does not translate `Dv`, does not check that `Dv` is mapped, and does not require a capability authorizing `Dv`.

## `SFENCE.VM` Effects

Each `SFENCE.VM` form:

- Orders older page-table memory stores by the executing core before younger local address translations by that core.
- Invalidates the selected local `ITLB` and `DTLB` entries.
- Invalidates matching cached page-walk failures, if the implementation caches failures.
- Completes its local invalidation before it retires.
- Ensures younger instruction fetch and data memory operations use translations that survive the invalidation or are refilled after it.

The invalidation scope is local to the executing core.

`SFENCE.VM` does not:

- Modify page-table memory.
- Modify data or instruction cache contents.
- Clean or invalidate capability tags.
- Modify `SATP` or `ASID`.
- Send remote IPIs.
- Invalidate remote-core TLB entries.
- Flush branch predictors unless the implementation needs to do so to prevent translation-dependent predictor state from bypassing fresh translation and permission checks.

If a predictor, fetch target cache, or prefetch structure stores translation-dependent authority, it must be invalidated or tagged so that stale entries cannot survive the relevant `SFENCE.VM` and authorize younger fetch or data access.

## `SFENCE.VM` Scope Details

The `SFENCE.VM` forms use the invalidation rules from E09-S03:

| Form | Global entries | Non-global entries |
| --- | --- | --- |
| `SFENCE.VM` | Invalidated. | Invalidated for all ASIDs and VPNs. |
| `SFENCE.VM.ASID Da` | Not invalidated. | Invalidated when entry ASID equals `Da[7:0]`. |
| `SFENCE.VM.VA Dv` | Invalidated for `Dv[47:11]`. | Invalidated for `Dv[47:11]` across all ASIDs. |
| `SFENCE.VM.VA_ASID Dv, Da` | Not invalidated. | Invalidated when both VPN and ASID match. |

Software that changes a global mapping must use `SFENCE.VM` or `SFENCE.VM.VA` on every core that may hold the old global translation.

Software that reuses an ASID for a different address space must use `SFENCE.VM.ASID` or `SFENCE.VM` on every core that may hold entries for that ASID before executing the new address space with the reused ASID.

## Page-table Update Sequences

For a local page-table update to normal coherent page-table memory:

```text
ST48 updated PTE
SFENCE.VM.VA_ASID page_va, asid
access through updated mapping
```

`SFENCE.VM` provides the local store-to-translation ordering for the executing core. A separate `FENCE` is not required for the local core solely to make its own older PTE store visible to its own later page walk.

For a local global mapping update:

```text
ST48 updated global PTE
SFENCE.VM.VA page_va
```

For an ASID reuse on the local core:

```text
install new root or page tables for reused ASID
SFENCE.VM.ASID asid
write SATP/ASID as required by the context switch
enter reused address space
```

If software writes `SATP` or `ASID` before the invalidation, it must still execute the appropriate `SFENCE.VM` before relying on translations for the reused context.

When switching to a fresh ASID that cannot match stale entries, software does not need to invalidate entries for other ASIDs. Implementations may still flush more than requested.

## Remote TLB Shootdown

`SFENCE.VM` is local. Remote shootdown is a software protocol using IPI or another platform-defined inter-core signal.

Required sequence for page-table changes that can leave stale translations on other started cores:

```text
initiator updates page-table memory
initiator FENCE
initiator publishes shootdown request and sends IPI
target handler executes matching SFENCE.VM form
target handler FENCE
target handler writes acknowledgment
initiator waits for all acknowledgments
initiator FENCE
initiator reuses physical pages, reuses ASID, or assumes stale entries are gone
```

The initiator's first `FENCE` orders page-table stores before the shootdown request becomes visible. The target's `SFENCE.VM` invalidates local stale entries. The target's `FENCE` orders the completed invalidation before its acknowledgment store. The initiator's final `FENCE` orders acknowledgment observation before destructive reuse.

If a target core has not entered ordinary execution since reset and cannot hold runtime TLB entries, the platform may treat it as quiescent according to E09-S03 and E11-S03. Otherwise the initiator must wait for an explicit acknowledgment.

Remote instruction-cache synchronization for code changes is separate from remote TLB shootdown. If a page-table update also changes executable code or execute permission, software may need both `SFENCE.VM` and `FENCE.I` on affected cores.

## Privilege and Faults

Privilege rules:

| Instruction | User mode | Kernel mode |
| --- | --- | --- |
| `FENCE` | Allowed. | Allowed. |
| `FENCE.I` | `PRIVILEGE_FAULT`. | Allowed. |
| `SFENCE.VM*` | `PRIVILEGE_FAULT`. | Allowed. |

Fence instructions have no destination register. On a fault, they do not perform their normal memory, cache, TLB, predictor, or architectural-register effects. Any active `LL48`/`SC48` reservation is cleared by the resulting synchronous trap entry according to E08-S02.

`FENCE` and valid kernel-mode `FENCE.I`/`SFENCE.VM` forms do not raise page faults, access faults, alignment faults, or capability faults because they do not perform an addressed architectural memory access.

Reserved or malformed fence encodings raise the illegal-instruction exception assigned by E07-S02 and E04-S06.

## Interaction With Reservations

This story does not define a required LL/SC reservation-clear effect for `FENCE`, `FENCE.I`, or `SFENCE.VM`.

E08-S02 owns the complete reservation-clear and progress rules. Implementations may clear reservations conservatively around privileged maintenance operations only if they still satisfy the E08-S02 progress guarantee once that story is applied.

## Out of Scope for This Story

- Final opcode bit encodings and instruction-format placement: E04-S06.
- LL/SC progress and reservation-clear requirements: E08-S02.
- Cache maintenance operation internals: E10-S05.
- Detailed page-table geometry and PTE format: E09-S04 and E09-S05.
- Remote IPI delivery mechanics and interrupt-controller registers: E07-S05 and platform profiles.
- User-mode instruction-cache synchronization ABI beyond the kernel-only architectural `FENCE.I`.
- Coherent I/O.

## Verification Notes

Minimum conformance checks for later simulator, OS, and RTL work:

- `FENCE` drains older coherent stores before younger loads can execute.
- Store-buffering with `FENCE` between store and load forbids both cores reading the old values.
- `FENCE` orders CPU stores before `CACHE.CLEAN` in DMA-read setup.
- `FENCE` orders `CACHE.INVAL` before CPU loads in DMA-write completion.
- `FENCE` orders normal memory updates before `DEVICE_ORDERED` doorbell stores.
- User-mode `FENCE` succeeds.
- User-mode `FENCE.I` raises `PRIVILEGE_FAULT`.
- Kernel `FENCE.I` makes younger local fetch miss or refetch stale local instruction-cache state.
- `FENCE.I` does not invalidate ITLB or DTLB entries.
- `SFENCE.VM` invalidates all local ITLB and DTLB entries, including global entries.
- `SFENCE.VM.ASID` invalidates local non-global entries for the selected ASID and preserves global entries.
- `SFENCE.VM.VA` invalidates local entries for one VPN across ASIDs and includes global entries.
- `SFENCE.VM.VA_ASID` invalidates local non-global entries for one VPN and ASID.
- User-mode `SFENCE.VM` raises `PRIVILEGE_FAULT`.
- Local PTE update followed by matching `SFENCE.VM` prevents stale local translation use.
- Remote shootdown waits for target `SFENCE.VM` completion before physical-page or ASID reuse.
- Fence instructions do not modify data cache contents except through ordering of explicit cache-maintenance instructions.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `FENCE` orders data memory operations. | Met. |
| `FENCE.I` synchronizes instruction fetch with prior code writes. | Met. |
| `SFENCE.VM` or equivalent TLB invalidate instruction is defined. | Met. |
| Privilege rules are specified. | Met. |
| Fence effects on caches, TLBs, and predictors are documented where applicable. | Met. |

# E09-S03: TLB Model

Story: E09-S03

Status: Complete

Normative source: `design.md`, section 12.4

Prerequisite:

- `spec/E09-S02-satp-layout.md`

Related sources:

- `spec/E02-S03-extended-csr-space.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E09-S04-page-table-geometry.md`
- `spec/E11-S01-cold-reset-state.md`
- `spec/E11-S03-secondary-core-startup.md`

## Decision

CPU v0.1 has private per-core translation lookaside buffers:

- One private instruction TLB (`ITLB`) per core.
- One private data TLB (`DTLB`) per core.

TLBs cache page-table translation results. They are not architectural storage and are not directly readable by ordinary software.

Address translation is active only when `SATP.MODE=RADIX4`. When `SATP.MODE=BARE`, the core bypasses TLB lookup and page-table walking.

## TLB Scope

| TLB | Scope | Used for |
| --- | --- | --- |
| `ITLB` | Private to one core | Instruction fetch translations. |
| `DTLB` | Private to one core | Data, capability, atomic, stack, and page-table memory access translations. |

Rules:

- A valid TLB entry is visible only to the core that owns that TLB.
- TLB entries are not coherent between cores.
- Hardware may choose any TLB size, associativity, replacement policy, and refill timing if architectural behavior matches this story.
- Hardware may implement split or unified internal structures if software observes the required private `ITLB` and `DTLB` behavior.
- TLB state does not carry capability tags and cannot create capability authority.

## TLB Entry Contents

A v0.1 TLB entry caches at least:

| Field | Meaning |
| --- | --- |
| `valid` | Whether the entry can match. |
| `kind` | Instruction-side, data-side, or implementation-unified entry kind. |
| `MODE` | Translation mode used to create the entry, `RADIX4` in v0.1. |
| `VPN` | 37-bit virtual page number from `VA[47:11]`. |
| `ASID` | 8-bit ASID, unless the entry is global. |
| `global` | Entry may match all ASIDs when derived from a global PTE. |
| `PPN` | 37-bit physical page number. |
| `page_size` | `2^11` cells in v0.1. |
| `permissions` | Page permission and privilege metadata defined by E09-S05. |
| `memory_type` | Page memory type defined by E09-S06. |

All valid v0.1 TLB entries map exactly one base page of `2^11` cells.

`global` is derived from the PTE global bit defined by E09-S05. Until a valid global PTE format is defined and used, entries are non-global and must match exact ASID.

## TLB Lookup

When `SATP.MODE=RADIX4`, a translation lookup uses:

```text
vpn    = VA[47:11]
offset = VA[10:0]
asid   = active ASID from E09-S02
```

A TLB entry matches when all required conditions hold:

- `valid=1`.
- Entry `MODE=RADIX4`.
- Entry `VPN` equals the lookup `vpn`.
- Entry is global, or entry `ASID` equals the active ASID.
- Entry kind can serve the access path.

On a matching entry, the physical address is:

```text
PA[47:11] = entry.PPN
PA[10:0]  = VA[10:0]
```

The TLB hit must still enforce the current access type, current privilege, and cached page metadata. A TLB entry created while the core was in kernel mode must not authorize a user-mode access that the PTE permissions would reject.

If multiple entries match the same lookup with conflicting translations or permissions, behavior is architecturally undefined until software invalidates the stale entries. Implementations should avoid creating duplicate conflicting entries, but software must still perform the required invalidation sequence when changing page-table mappings.

## TLB Miss and Refill

On a TLB miss in `RADIX4` mode, hardware performs or invokes a page-table walk using:

- Current `SATP.ROOT_PPN`.
- Current active ASID.
- E09-S04 page-table geometry.
- E09-S05 PTE format and fault rules.

If the walk succeeds, hardware may install a TLB entry in the appropriate local TLB.

If the walk faults, the fault is reported through the page-fault path defined by E09-S05 and E09-S07. A faulting walk must not install a usable positive translation for that access.

An implementation may cache failed translations internally only if every local and remote invalidation operation defined by this story also invalidates the corresponding cached failure. After a required invalidation completes, software must not observe a stale cached page fault for the invalidated translation.

## Reset and Startup State

After cold reset:

- All `ITLB` and `DTLB` entries are invalid, or TLB state is architecturally ignored while `SATP.MODE=BARE`.
- Stale pre-reset TLB entries must not affect boot ROM fetch, early data access, or fault reporting.

After E11-S03 starts a secondary core, that core begins with `SATP=0` unless a platform profile explicitly defines a later virtual-memory startup handoff. With `SATP=0`, its TLBs are bypassed.

## Local Invalidation Primitives

CPU v0.1 requires privileged local TLB invalidation primitives.

The architectural invalidation effect is defined here. The final instruction encoding and fence-ordering details are defined by E08-S04. The mandatory instruction family is named `SFENCE.VM` unless E08-S04 chooses an equivalent final mnemonic.

Required local operations:

| Operation | Required invalidation effect |
| --- | --- |
| `TLBI.ALL` | Invalidate all local `ITLB` and `DTLB` entries, including global entries. |
| `TLBI.ASID(asid)` | Invalidate all local non-global entries whose ASID equals `asid`. |
| `TLBI.VA(va)` | Invalidate all local entries for `va[47:11]` across all ASIDs, including global entries. |
| `TLBI.VA_ASID(va, asid)` | Invalidate all local non-global entries for `va[47:11]` whose ASID equals `asid`. |

The same operation must affect both local `ITLB` and local `DTLB` unless E08-S04 later defines an explicit instruction-only or data-only maintenance form. v0.1 portable software should assume local invalidation is both instruction-side and data-side.

Local invalidation does not modify:

- Page-table memory.
- Data or instruction cache contents.
- Capability tags.
- `SATP`.
- `ASID`.
- General registers or capability registers, except for instruction-defined result registers if E08-S04 adds them.

Local invalidation is privileged. User-mode attempts to execute a local TLB invalidate instruction raise `PRIVILEGE_FAULT`.

## `SATP` and `ASID` Changes

A committed `SATP` or `ASID` write changes the active translation context for younger accesses according to E09-S02.

TLB behavior:

- When `SATP.MODE=BARE`, TLB entries are not used.
- A `SATP` write to `BARE` does not have to invalidate TLB entries, but those entries must be ignored while `BARE` is active.
- A `SATP` write to `RADIX4` may retain old TLB entries if normal matching rules prevent stale entries from being used incorrectly.
- An `ASID` write may retain entries for other ASIDs because exact-ASID matching prevents them from matching the new active ASID.
- If software reuses an ASID for a different address space, software must invalidate stale entries for that ASID on every core that may hold them before the reused ASID is allowed to execute.
- If software changes `SATP.ROOT_PPN` while keeping the same ASID, software must invalidate stale entries for that ASID or use a fresh ASID.

Implementations may conservatively flush all local TLB entries on any committed `SATP` or `ASID` write.

## Privilege Changes

TLB entries are not flushed automatically on `SR.PRIV` changes.

Required behavior:

- TLB hits must check access permissions using the current `SR.PRIV`.
- A user-mode fetch, load, store, or capability access must not succeed through a stale kernel-authorized interpretation of the entry.
- A kernel-mode access may use the same translation entry if the cached PTE metadata permits the access.

If an implementation caches privilege-specific derived permissions instead of raw PTE permission metadata, it must either include privilege state in the internal match key or invalidate/recompute the derived permission state on privilege changes. Software-visible behavior must match a fresh permission check using current privilege.

Privilege transitions through trap entry and `IRET` do not require software TLB invalidation unless the kernel also changes page tables, `SATP`, or `ASID`.

## Page-table Updates

Software must explicitly maintain TLB consistency when it changes page-table memory.

Required software rules:

- After installing a new mapping for an unmapped page, software must ensure the page-table stores are visible before relying on the mapping.
- After changing permissions, PPN, memory type, valid bit, leaf/non-leaf state, or global state for an existing mapping, software must invalidate stale TLB entries that could match the old translation.
- Before reusing a physical page that was formerly reachable through a stale translation, software must complete shootdown for every core that may hold that translation.
- Before reusing an ASID for a different address space, software must complete ASID-targeted or full invalidation on every core that may hold entries for that ASID.

The exact store-to-invalidate ordering primitive is finalized by E08-S04. Until then, the architectural intent is:

```text
write page-table memory
order page-table writes before translation maintenance
perform local invalidate
perform remote shootdown if any other core could hold stale entries
```

## Remote Shootdown

Remote shootdown is performed through IPI.

A conforming remote shootdown protocol has these steps:

1. The initiating core updates page-table memory or decides to reuse an ASID.
2. The initiating core orders those updates before publishing shootdown requests.
3. The initiating core sends a software IPI or platform IPI to every target core that may hold stale entries.
4. Each target handler performs the requested local TLB invalidation operation.
5. Each target reports completion through a coherent memory flag, platform interrupt-controller state, or another documented acknowledgment path.
6. The initiating core waits for all required acknowledgments before freeing physical memory, reusing an ASID, or assuming stale translations cannot be used.

The software IPI source and interrupt delivery mechanics are defined by E07-S05. The mailbox/start-event reserved platform range may also provide platform-specific IPI delivery, but the target core must still execute the local invalidation operation before acknowledging completion.

If a target core has interrupts masked, is in `SR.EXL=1`, or is otherwise delayed, shootdown completion is delayed. The initiating core must not treat an unacknowledged target as complete.

If a secondary core is still `STOPPED` or `WFI_PARKED` and has not entered ordinary execution since reset, it cannot hold valid runtime TLB entries. A platform may treat it as already quiescent for shootdown. If a parked core can hold retained TLB entries from an earlier `STARTED` lifetime in a future hotplug extension, that extension must define explicit invalidation before restart.

## Global Mappings

E09-S05 defines the PTE global bit.

TLB matching and invalidation rules for global entries:

- A global entry may match any active ASID.
- `TLBI.ASID(asid)` does not invalidate global entries.
- `TLBI.VA_ASID(va, asid)` does not invalidate global entries.
- `TLBI.ALL` invalidates global entries.
- `TLBI.VA(va)` invalidates global entries for the selected VPN.

Software that changes a global mapping must use `TLBI.ALL` or `TLBI.VA` on every affected core.

## Out of Scope for This Story

- PTE bit layout, accessed-bit behavior, and page-walk fault details: E09-S05.
- Page memory-type semantics: E09-S06.
- Combined capability, translation, privilege, and alignment fault priority: E09-S07.
- Final `SFENCE.VM` instruction encoding and data-memory fence ordering: E08-S04.
- Cache maintenance interactions for page-table memory stored in noncoherent memory: E10-S05.
- Hardware TLB size, associativity, replacement, and performance counters.
- Virtualization or guest TLB behavior.

## Verification Notes

Minimum conformance checks for later simulator, firmware, OS, and RTL work:

- Each core has independent `ITLB` and `DTLB` state.
- A TLB entry created on one core is not visible on another core.
- `SATP.MODE=BARE` bypasses TLB lookup.
- `RADIX4` TLB hits preserve the 11-bit page offset.
- Non-global entries match only when active ASID equals entry ASID.
- Global entries match across ASIDs.
- Changing `ASID` prevents non-global entries for the previous ASID from matching.
- `TLBI.ALL` invalidates both local `ITLB` and `DTLB`.
- `TLBI.ASID(asid)` invalidates non-global local entries for that ASID.
- `TLBI.VA(va)` invalidates matching local entries for all ASIDs and global mappings.
- `TLBI.VA_ASID(va, asid)` invalidates matching non-global local entries for that ASID.
- User-mode TLB invalidation raises `PRIVILEGE_FAULT`.
- Privilege changes do not require TLB flush, but current privilege is enforced on TLB hits.
- Remote shootdown by IPI invalidates stale target-core entries before acknowledgment.
- Reusing an ASID without shootdown can be detected as invalid software behavior in OS tests.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Each core has private ITLB and DTLB. | Met. |
| ASID support is mandatory. | Met: TLB entries match exact 8-bit ASID unless global. |
| Local TLB invalidate instructions are mandatory. | Met: required local invalidation primitives are defined for the mandatory `SFENCE.VM` family or equivalent. |
| Remote shootdown is performed through IPI. | Met. |
| TLB behavior on privilege and ASID changes is specified. | Met. |

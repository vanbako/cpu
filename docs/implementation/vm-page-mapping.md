# VM Page Mapping Fixture

Story: I18-S02

Status: Draft executable fixture

## Scope

This story adds the first kernel-owned VM allocation and page-mapping fixture
above the existing RADIX4 MMU model. It is a deterministic simulator fixture,
not a complete virtual-memory subsystem. Scheduling, syscall round trips, and
multi-address-space policy remain later I18 stories.

## Allocation

The fixture allocator reserves four base-page-aligned page-table pages in main
RAM: root, L1, L2, and L3. The pages are distinct, inside the test-platform RAM
region, and can be reproduced exactly for conformance tests.

`default_vm_entry_context` reuses the I18-S01 user entry context, replacing the
bare `SATP` value with a RADIX4 `SATP` that carries the fixture root page and a
nonzero ASID. The fixture also installs identity mappings for the user entry
text page and user data page so the entry context is meaningful under
translation.

## Mapping

`install_page_mapping` writes a complete 4-level path and one leaf PTE. It
validates all inputs before writing PTEs and rejects reserved page memory types.
`unmap_page` clears only the leaf PTE; it deliberately does not invalidate TLB
state. The executable map/unmap case demonstrates that a stale cached
translation remains usable until a kernel `SFENCE.VM.VA_ASID` retires and
commits through the normal execution path.

The fixture cases cover:

- mapping a user page and translating load/fetch accesses;
- unmapping a page and invalidating by virtual address plus ASID;
- read-only PTE permission rejection for a user store;
- device-ordered memory type rejection for cache maintenance;
- capability tag fault priority before an unmapped page walk.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Page-table allocation is deterministic and RAM-bounded. | Met. |
| Map, unmap, permission, ASID/TLB invalidation, and memory type cases run as executable fixtures. | Met. |
| Capability fault priority precedes page fault checks. | Met. |
| Invalid mapping setup rejects before PTE writes. | Met. |

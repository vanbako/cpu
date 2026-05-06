"""Kernel VM allocation and page-mapping fixtures for CPU v0.1.

Owner stories:
- E09-S02: SATP layout and ASID context fields.
- E09-S03: local TLB invalidation effects.
- E09-S06: page memory-type policy.
- E09-S07: effective-access translation and page fault priority.
- I18-S01: user process entry context.
- I18-S02: VM allocation and page-mapping fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import (
    cache_ops,
    capabilities as caps,
    csrs,
    execution,
    fence_ops,
    instructions,
    memory_ops,
    mmu,
    platform,
    state,
    user_process,
)
from .cells import (
    ADDRESS_SPACE_CELLS,
    BASE_PAGE_CELLS,
    CACHE_LINE_CELLS,
    align_down,
    cell_range,
    is_aligned,
    require_cell_address,
    require_cell_endpoint,
)
from .memory import TaggedMemory


VM_TABLE_BASE = platform.RAM_BASE + 0x2000
VM_TABLE_LIMIT = VM_TABLE_BASE + (4 * BASE_PAGE_CELLS)
VM_ROOT_TABLE = VM_TABLE_BASE
VM_L1_TABLE = VM_ROOT_TABLE + BASE_PAGE_CELLS
VM_L2_TABLE = VM_L1_TABLE + BASE_PAGE_CELLS
VM_L3_TABLE = VM_L2_TABLE + BASE_PAGE_CELLS

USER_VM_PAGE = 0x0000_4000_0000
USER_VM_OFFSET = 0x120
USER_VM_ADDRESS = USER_VM_PAGE + USER_VM_OFFSET
USER_VM_PHYSICAL_PAGE_A = platform.RAM_BASE + 0x4000
USER_VM_PHYSICAL_PAGE_B = USER_VM_PHYSICAL_PAGE_A + BASE_PAGE_CELLS
USER_VM_VALUE = 0x18_0202

SFENCE_VA_REGISTER = 14
SFENCE_ASID_REGISTER = 15


class VmFixtureError(ValueError):
    """Raised when a VM fixture allocation or mapping cannot be accepted."""


@dataclass
class VmPageAllocator:
    next_page: int = VM_TABLE_BASE
    limit: int = VM_TABLE_LIMIT
    allocated_pages: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        self.next_page = require_cell_address(self.next_page, "next_page")
        self.limit = require_cell_endpoint(self.limit, "limit")
        self.allocated_pages = tuple(self.allocated_pages)
        if not is_aligned(self.next_page, BASE_PAGE_CELLS):
            raise ValueError("next_page must be base-page aligned")
        if self.limit < self.next_page:
            raise ValueError("limit must not be below next_page")
        if self.limit % BASE_PAGE_CELLS:
            raise ValueError("limit must be base-page aligned")
        for page in self.allocated_pages:
            _validate_table_page(page, platform.TEST_PLATFORM_PROFILE)

    def allocate_page_table(
        self,
        profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
    ) -> int:
        """Allocate one base-page-aligned page-table page in main RAM."""
        if self.next_page + BASE_PAGE_CELLS > self.limit:
            raise VmFixtureError("VM page-table allocator exhausted")
        page = self.next_page
        _validate_table_page(page, profile)
        self.next_page += BASE_PAGE_CELLS
        self.allocated_pages = (*self.allocated_pages, page)
        return page


@dataclass(frozen=True)
class VmPageTables:
    root: int = VM_ROOT_TABLE
    l1: int = VM_L1_TABLE
    l2: int = VM_L2_TABLE
    l3: int = VM_L3_TABLE

    def __post_init__(self) -> None:
        for name, page in zip(("root", "l1", "l2", "l3"), self.pages):
            object.__setattr__(self, name, require_cell_address(page, name))
            _validate_table_page(page, platform.TEST_PLATFORM_PROFILE)
        if len(set(self.pages)) != len(self.pages):
            raise ValueError("VM page-table pages must be distinct")

    @property
    def pages(self) -> tuple[int, int, int, int]:
        return (self.root, self.l1, self.l2, self.l3)


@dataclass(frozen=True)
class VmMapping:
    virtual_page: int = USER_VM_PAGE
    physical_page: int = USER_VM_PHYSICAL_PAGE_A
    readable: bool = True
    writable: bool = True
    executable: bool = False
    user: bool = True
    global_mapping: bool = False
    accessed: bool = True
    memory_type: int = mmu.MEMORY_TYPE_NORMAL_COHERENT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "virtual_page",
            _require_base_page(self.virtual_page, "virtual_page"),
        )
        object.__setattr__(
            self,
            "physical_page",
            _require_base_page(self.physical_page, "physical_page"),
        )
        for field_name in (
            "readable",
            "writable",
            "executable",
            "user",
            "global_mapping",
            "accessed",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"{field_name} must be a bool")
        object.__setattr__(
            self,
            "memory_type",
            csrs.require_uint(self.memory_type, mmu.PTE_MT_BITS, "memory_type"),
        )

    def virtual_address(self, offset: int = USER_VM_OFFSET) -> int:
        return self.virtual_page + _require_page_offset(offset)

    def physical_address(self, offset: int = USER_VM_OFFSET) -> int:
        return self.physical_page + _require_page_offset(offset)


@dataclass(frozen=True)
class VmFixture:
    core: state.CoreState
    memory: TaggedMemory
    context: user_process.UserEntryContext
    tables: VmPageTables
    mapping: VmMapping

    def __post_init__(self) -> None:
        if not isinstance(self.core, state.CoreState):
            raise TypeError("core must be a CoreState")
        if not isinstance(self.memory, TaggedMemory):
            raise TypeError("memory must be a TaggedMemory")
        if not isinstance(self.context, user_process.UserEntryContext):
            raise TypeError("context must be a UserEntryContext")
        if not isinstance(self.tables, VmPageTables):
            raise TypeError("tables must be VmPageTables")
        if not isinstance(self.mapping, VmMapping):
            raise TypeError("mapping must be a VmMapping")


@dataclass(frozen=True)
class VmMapUnmapReport:
    first_load: instructions.ExecutionResult
    stale_load_after_unmap: instructions.ExecutionResult
    sfence: instructions.ExecutionResult
    load_after_sfence: instructions.ExecutionResult
    first_value: int
    stale_value: int
    leaf_pte_after_unmap: int
    tlb_entries_after_sfence: int


@dataclass(frozen=True)
class VmPermissionReport:
    load_result: instructions.ExecutionResult
    store_result: instructions.ExecutionResult
    loaded_value: int
    physical_value_after_store_attempt: int


@dataclass(frozen=True)
class VmMemoryTypeReport:
    cache_result: instructions.ExecutionResult
    mapped_memory_type: int
    fault_tval: int


@dataclass(frozen=True)
class VmFaultPriorityReport:
    load_result: instructions.ExecutionResult
    d0_after_fault: int
    tlb_entries_after_fault: int


def allocate_fixture_tables(
    allocator: VmPageAllocator | None = None,
) -> VmPageTables:
    """Allocate the four page-table pages used by the I18-S02 fixtures."""
    if allocator is None:
        allocator = VmPageAllocator()
    if not isinstance(allocator, VmPageAllocator):
        raise TypeError("allocator must be a VmPageAllocator")
    return VmPageTables(
        root=allocator.allocate_page_table(),
        l1=allocator.allocate_page_table(),
        l2=allocator.allocate_page_table(),
        l3=allocator.allocate_page_table(),
    )


def default_vm_entry_context(
    tables: VmPageTables | None = None,
    *,
    asid: int = user_process.USER_ASID,
) -> user_process.UserEntryContext:
    """Return the I18-S01 user entry context using a RADIX4 root table."""
    tables = _tables_or_default(tables)
    context = user_process.default_user_entry_context()
    satp = csrs.pack_satp(
        csrs.SATP_MODE_RADIX4,
        asid,
        tables.root >> csrs.SATP_ROOT_PPN_SHIFT,
    )
    return replace(context, satp=satp)


def validate_vm_mapping(
    mapping: VmMapping,
    tables: VmPageTables | None = None,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> tuple[str, ...]:
    """Return deterministic VM fixture mapping issues without writing PTEs."""
    if not isinstance(mapping, VmMapping):
        raise TypeError("mapping must be a VmMapping")
    tables = _tables_or_default(tables)
    if not isinstance(profile, platform.TestPlatformProfile):
        raise TypeError("profile must be a TestPlatformProfile")
    issues: list[str] = []
    for page in tables.pages:
        try:
            _validate_table_page(page, profile)
        except ValueError as exc:
            issues.append(str(exc))
    if mapping.memory_type == mmu.MEMORY_TYPE_RESERVED:
        issues.append("VM mapping memory_type must not be reserved")
    return tuple(dict.fromkeys(issues))


def install_page_mapping(
    memory: TaggedMemory,
    mapping: VmMapping | None = None,
    tables: VmPageTables | None = None,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> int:
    """Install one 4-level RADIX4 leaf mapping and return its leaf PTE address."""
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    mapping = _mapping_or_default(mapping)
    tables = _tables_or_default(tables)
    issues = validate_vm_mapping(mapping, tables, profile)
    if issues:
        raise VmFixtureError("; ".join(issues))
    l0, l1, l2, l3 = mmu.vpn_indexes(mapping.virtual_page)
    memory.st48(
        tables.root + (l0 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(tables.l1 >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        tables.l1 + (l1 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(tables.l2 >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    memory.st48(
        tables.l2 + (l2 * mmu.PTE_SIZE_CELLS),
        mmu.pte_value(tables.l3 >> csrs.SATP_ROOT_PPN_SHIFT),
    )
    leaf_address = leaf_pte_address(mapping.virtual_page, tables)
    memory.st48(
        leaf_address,
        mmu.pte_value(
            mapping.physical_page >> csrs.SATP_ROOT_PPN_SHIFT,
            read=mapping.readable,
            write=mapping.writable,
            execute=mapping.executable,
            user=mapping.user,
            global_mapping=mapping.global_mapping,
            accessed=mapping.accessed,
            memory_type=mapping.memory_type,
            software=True,
        ),
    )
    return leaf_address


def unmap_page(
    memory: TaggedMemory,
    virtual_page: int = USER_VM_PAGE,
    tables: VmPageTables | None = None,
) -> int:
    """Clear one leaf PTE without invalidating any cached TLB entry."""
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    tables = _tables_or_default(tables)
    leaf_address = leaf_pte_address(virtual_page, tables)
    memory.st48(leaf_address, 0)
    return leaf_address


def leaf_pte_address(
    virtual_page: int = USER_VM_PAGE,
    tables: VmPageTables | None = None,
) -> int:
    tables = _tables_or_default(tables)
    virtual_page = _require_base_page(virtual_page, "virtual_page")
    *_, l3 = mmu.vpn_indexes(virtual_page)
    return tables.l3 + (l3 * mmu.PTE_SIZE_CELLS)


def install_user_process_identity_mappings(
    memory: TaggedMemory,
    tables: VmPageTables | None = None,
) -> None:
    """Map the I18-S01 entry text and data pages at identity virtual addresses."""
    tables = _tables_or_default(tables)
    install_page_mapping(
        memory,
        VmMapping(
            virtual_page=align_down(user_process.USER_ENTRY_CELL, BASE_PAGE_CELLS),
            physical_page=align_down(user_process.USER_ENTRY_CELL, BASE_PAGE_CELLS),
            readable=True,
            writable=False,
            executable=True,
            user=True,
        ),
        tables,
    )
    install_page_mapping(
        memory,
        VmMapping(
            virtual_page=align_down(user_process.USER_DATA_BASE, BASE_PAGE_CELLS),
            physical_page=align_down(user_process.USER_DATA_BASE, BASE_PAGE_CELLS),
            readable=True,
            writable=True,
            executable=False,
            user=True,
        ),
        tables,
    )


def prepare_vm_fixture(
    mapping: VmMapping | None = None,
    tables: VmPageTables | None = None,
) -> VmFixture:
    """Build a user-mode core and memory image with a RADIX4 user mapping."""
    mapping = _mapping_or_default(mapping)
    tables = _tables_or_default(tables)
    core = platform.cold_reset_cores()[0]
    memory = TaggedMemory()
    context = default_vm_entry_context(tables)
    install_user_process_identity_mappings(memory, tables)
    install_page_mapping(memory, mapping, tables)
    user_process.load_user_process_image(context, memory)
    user_process.enter_user_process_context(core, context, memory)
    return VmFixture(core, memory, context, tables, mapping)


def virtual_authority(
    cursor: int = USER_VM_ADDRESS,
    *,
    permissions: caps.CapabilityPermission = (
        caps.CapabilityPermission.LD | caps.CapabilityPermission.ST
    ),
    tag: bool = True,
) -> caps.Capability:
    """Return a user capability that authorizes fixture virtual accesses."""
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(permissions),
        flags=int(caps.CapabilityFlag.G),
    ).with_bounds(0, ADDRESS_SPACE_CELLS)
    return caps.Capability(payload, tag)


def execute_user_ld48(
    core: state.CoreState,
    memory: TaggedMemory,
    address: int = USER_VM_ADDRESS,
    *,
    destination: int = 0,
) -> instructions.ExecutionResult:
    core.write_c(1, virtual_authority(address, permissions=caps.CapabilityPermission.LD))
    core.write_d(2, 0)
    result = memory_ops.execute_memory(
        core,
        memory,
        memory_ops.memory_instruction("LD48", (destination, 1, 2)),
    )
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def execute_user_st48(
    core: state.CoreState,
    memory: TaggedMemory,
    address: int = USER_VM_ADDRESS,
    *,
    value: int,
) -> instructions.ExecutionResult:
    core.write_c(
        1,
        virtual_authority(
            address,
            permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.ST,
        ),
    )
    core.write_d(2, 0)
    core.write_d(3, value)
    result = memory_ops.execute_memory(
        core,
        memory,
        memory_ops.memory_instruction("ST48", (1, 2, 3)),
    )
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


def execute_kernel_sfence_va_asid(
    core: state.CoreState,
    virtual_address: int = USER_VM_ADDRESS,
    asid: int = user_process.USER_ASID,
) -> instructions.ExecutionResult:
    """Run and commit an executable kernel `SFENCE.VM.VA_ASID` fixture."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    virtual_address = csrs.require_uint(virtual_address, csrs.CSR_BITS, "virtual_address")
    asid = csrs.require_uint(asid, csrs.SATP_ASID_BITS, "asid")
    old_sr = core.read_csr(csrs.CSR_SR)
    old_va = core.read_d(SFENCE_VA_REGISTER)
    old_asid = core.read_d(SFENCE_ASID_REGISTER)
    core.write_csr_raw(csrs.CSR_SR, old_sr | (1 << csrs.SR_PRIV_BIT))
    core.write_d(SFENCE_VA_REGISTER, virtual_address)
    core.write_d(SFENCE_ASID_REGISTER, asid)
    result = fence_ops.execute_fence(
        core,
        fence_ops.fence_instruction(
            "SFENCE.VM.VA_ASID",
            (SFENCE_VA_REGISTER, SFENCE_ASID_REGISTER),
        ),
    )
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    core.write_d(SFENCE_VA_REGISTER, old_va)
    core.write_d(SFENCE_ASID_REGISTER, old_asid)
    core.write_csr_raw(csrs.CSR_SR, old_sr)
    return result


def run_map_unmap_fixture() -> VmMapUnmapReport:
    """Map, unmap, and invalidate a user page through executable operations."""
    fixture = prepare_vm_fixture()
    core = fixture.core
    memory = fixture.memory
    mapping = fixture.mapping
    memory.st48(mapping.physical_address(), USER_VM_VALUE)

    first = execute_user_ld48(core, memory, mapping.virtual_address())
    first_value = core.read_d(0)
    leaf_address = unmap_page(memory, mapping.virtual_page, fixture.tables)
    stale = execute_user_ld48(core, memory, mapping.virtual_address())
    stale_value = core.read_d(0)
    sfence = execute_kernel_sfence_va_asid(
        core,
        mapping.virtual_address(),
        csrs.satp_asid(core.read_csr(csrs.CSR_SATP)),
    )
    entries_after_sfence = core.tlbs.entry_count()
    after_sfence = execute_user_ld48(core, memory, mapping.virtual_address())
    return VmMapUnmapReport(
        first_load=first,
        stale_load_after_unmap=stale,
        sfence=sfence,
        load_after_sfence=after_sfence,
        first_value=first_value,
        stale_value=stale_value,
        leaf_pte_after_unmap=memory.ld48(leaf_address),
        tlb_entries_after_sfence=entries_after_sfence,
    )


def run_permission_fixture() -> VmPermissionReport:
    """Exercise a read-only user page through load and store operations."""
    mapping = VmMapping(readable=True, writable=False)
    fixture = prepare_vm_fixture(mapping)
    memory = fixture.memory
    core = fixture.core
    memory.st48(mapping.physical_address(), USER_VM_VALUE)

    load = execute_user_ld48(core, memory, mapping.virtual_address())
    loaded_value = core.read_d(0)
    store = execute_user_st48(core, memory, mapping.virtual_address(), value=0xBAD)
    return VmPermissionReport(
        load_result=load,
        store_result=store,
        loaded_value=loaded_value,
        physical_value_after_store_attempt=memory.ld48(mapping.physical_address()),
    )


def run_memory_type_fixture() -> VmMemoryTypeReport:
    """Exercise a device-ordered mapping with a cache-maintenance operation."""
    tables = VmPageTables()
    mapping = VmMapping(
        physical_page=platform.DEVICE_BASE,
        user=False,
        memory_type=mmu.MEMORY_TYPE_DEVICE_ORDERED,
    )
    core = platform.cold_reset_cores()[0]
    memory = TaggedMemory()
    install_page_mapping(memory, mapping, tables)
    _install_radix4_satp(core, tables, user_process.USER_ASID)
    core.write_c(1, virtual_authority(mapping.virtual_address()))
    core.write_d(2, 0)
    core.write_d(3, CACHE_LINE_CELLS)

    result = cache_ops.execute_cache(
        core,
        memory,
        cache_ops.cache_instruction("CACHE.CLEAN", (1, 2, 3)),
    )
    fault_tval = result.fault_packet.tval if result.is_fault else 0
    return VmMemoryTypeReport(
        cache_result=result,
        mapped_memory_type=mapping.memory_type,
        fault_tval=fault_tval,
    )


def run_fault_priority_fixture() -> VmFaultPriorityReport:
    """Show capability tag failure wins before an unmapped-page fault."""
    tables = VmPageTables()
    core = platform.cold_reset_cores()[0]
    memory = TaggedMemory()
    _install_radix4_satp(core, tables, user_process.USER_ASID)
    core.write_c(
        1,
        virtual_authority(USER_VM_ADDRESS, permissions=caps.CapabilityPermission.LD, tag=False),
    )
    core.write_d(2, 0)
    core.write_d(0, 0x1234)

    result = memory_ops.execute_memory(
        core,
        memory,
        memory_ops.memory_instruction("LD48", (0, 1, 2)),
    )
    return VmFaultPriorityReport(
        load_result=result,
        d0_after_fault=core.read_d(0),
        tlb_entries_after_fault=core.tlbs.entry_count(),
    )


def _install_radix4_satp(
    core: state.CoreState,
    tables: VmPageTables,
    asid: int,
) -> None:
    core.write_csr_raw(
        csrs.CSR_SATP,
        csrs.pack_satp(
            csrs.SATP_MODE_RADIX4,
            asid,
            tables.root >> csrs.SATP_ROOT_PPN_SHIFT,
        ),
    )


def _tables_or_default(tables: VmPageTables | None) -> VmPageTables:
    if tables is None:
        return VmPageTables()
    if not isinstance(tables, VmPageTables):
        raise TypeError("tables must be VmPageTables")
    return tables


def _mapping_or_default(mapping: VmMapping | None) -> VmMapping:
    if mapping is None:
        return VmMapping()
    if not isinstance(mapping, VmMapping):
        raise TypeError("mapping must be a VmMapping")
    return mapping


def _require_base_page(address: int, name: str) -> int:
    address = require_cell_address(address, name)
    if not is_aligned(address, BASE_PAGE_CELLS):
        raise ValueError(f"{name} must be base-page aligned")
    return address


def _require_page_offset(offset: int) -> int:
    if type(offset) is not int:
        raise TypeError("offset must be an int")
    if not 0 <= offset < BASE_PAGE_CELLS:
        raise ValueError("offset must fit within one base page")
    return offset


def _validate_table_page(
    page: int,
    profile: platform.TestPlatformProfile,
) -> None:
    page = _require_base_page(page, "page_table")
    ram = profile.region_by_name("main_ram")
    if not ram.range.contains_range(cell_range(page, BASE_PAGE_CELLS)):
        raise ValueError("VM page-table page must be inside main RAM")

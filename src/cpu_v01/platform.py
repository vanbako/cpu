"""Minimal test-platform profile for CPU v0.1.

Owner stories:
- E11-S01: cold reset state and reset-vector binding.
- E11-S02: reset capability state.
- I08-S01: minimal test platform profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import mmu, reset
from .capabilities import (
    Capability,
    CapabilityFlag,
    CapabilityPayload,
    CapabilityPermission,
    OTYPE_UNSEALED,
)
from .cells import CellRange, require_cell_address, require_positive_cell_count
from .state import CoreLifecycle, CoreState, SLOT_0, SlottedCapability


RESET_VECTOR = 0x0000_1000
ROM_BASE = 0x0000_1000
ROM_CELLS = 0x0000_1000
RAM_BASE = 0x0001_0000
RAM_CELLS = 0x0001_0000
DEVICE_BASE = 0x00F0_0000
DEVICE_CELLS = 0x0000_1000
MAILBOX_BASE = 0x00F0_1000
MAILBOX_CELLS = 0x0000_0100


class MemoryRegionKind(Enum):
    ROM = "ROM"
    RAM = "RAM"
    DEVICE = "DEVICE"
    MAILBOX = "MAILBOX"


class FatalEntryPolicy(Enum):
    DEBUG_HALT = "DEBUG_HALT"


class DebugTransportPolicy(Enum):
    SIMULATED_MMIO = "SIMULATED_MMIO"


class CacheResetPolicy(Enum):
    DISABLED = "DISABLED"


class RamResetPolicy(Enum):
    UNINITIALIZED = "UNINITIALIZED"


@dataclass(frozen=True)
class MemoryRegion:
    name: str
    kind: MemoryRegionKind
    base: int
    size_cells: int
    permissions: CapabilityPermission
    memory_type: int = mmu.MEMORY_TYPE_NORMAL_COHERENT

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("region name must not be empty")
        object.__setattr__(self, "kind", MemoryRegionKind(self.kind))
        object.__setattr__(self, "base", require_cell_address(self.base, "base"))
        object.__setattr__(
            self,
            "size_cells",
            require_positive_cell_count(self.size_cells, "size_cells"),
        )
        object.__setattr__(self, "permissions", CapabilityPermission(self.permissions))
        object.__setattr__(self, "memory_type", int(self.memory_type))

    @property
    def end(self) -> int:
        return self.base + self.size_cells

    @property
    def range(self) -> CellRange:
        return CellRange(self.base, self.end)

    def contains(self, address: int) -> bool:
        address = require_cell_address(address)
        return self.base <= address < self.end

    def overlaps(self, other: "MemoryRegion") -> bool:
        return self.base < other.end and other.base < self.end

    @property
    def executable(self) -> bool:
        return bool(self.permissions & CapabilityPermission.EX)

    @property
    def writable(self) -> bool:
        return bool(self.permissions & CapabilityPermission.ST)

    @property
    def readable(self) -> bool:
        return bool(self.permissions & CapabilityPermission.LD)


@dataclass(frozen=True)
class TestPlatformProfile:
    name: str
    reset_vector: int
    core_count: int
    secondary_lifecycle: CoreLifecycle
    memory_regions: tuple[MemoryRegion, ...]
    fatal_entry_policy: FatalEntryPolicy
    debug_transport: DebugTransportPolicy
    halt_on_reset: bool
    cache_reset_policy: CacheResetPolicy
    ram_reset_policy: RamResetPolicy
    external_interrupt_pending_on_reset: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("profile name must not be empty")
        object.__setattr__(
            self,
            "reset_vector",
            require_cell_address(self.reset_vector, "reset_vector"),
        )
        if type(self.core_count) is not int:
            raise TypeError("core_count must be an int")
        object.__setattr__(self, "secondary_lifecycle", CoreLifecycle(self.secondary_lifecycle))
        object.__setattr__(self, "memory_regions", tuple(self.memory_regions))
        object.__setattr__(self, "fatal_entry_policy", FatalEntryPolicy(self.fatal_entry_policy))
        object.__setattr__(self, "debug_transport", DebugTransportPolicy(self.debug_transport))
        if type(self.halt_on_reset) is not bool:
            raise TypeError("halt_on_reset must be a bool")
        object.__setattr__(self, "cache_reset_policy", CacheResetPolicy(self.cache_reset_policy))
        object.__setattr__(self, "ram_reset_policy", RamResetPolicy(self.ram_reset_policy))
        if type(self.external_interrupt_pending_on_reset) is not bool:
            raise TypeError("external_interrupt_pending_on_reset must be a bool")

    def region_by_name(self, name: str) -> MemoryRegion:
        normalized = name.upper()
        for region in self.memory_regions:
            if region.name.upper() == normalized:
                return region
        raise KeyError(f"unknown platform memory region {name!r}")

    def region_for(self, address: int) -> MemoryRegion:
        address = require_cell_address(address)
        for region in self.memory_regions:
            if region.contains(address):
                return region
        raise KeyError(f"address 0x{address:X} is outside the platform memory map")

    @property
    def reset_rom_region(self) -> MemoryRegion:
        region = self.region_for(self.reset_vector)
        if region.kind is not MemoryRegionKind.ROM:
            raise ValueError("reset vector is not in a ROM region")
        return region


TEST_PLATFORM_PROFILE = TestPlatformProfile(
    name="cpu_v01_test_platform",
    reset_vector=RESET_VECTOR,
    core_count=reset.V01_CORE_COUNT,
    secondary_lifecycle=CoreLifecycle.STOPPED,
    memory_regions=(
        MemoryRegion(
            "boot_rom",
            MemoryRegionKind.ROM,
            ROM_BASE,
            ROM_CELLS,
            CapabilityPermission.EX,
            mmu.MEMORY_TYPE_NORMAL_COHERENT,
        ),
        MemoryRegion(
            "main_ram",
            MemoryRegionKind.RAM,
            RAM_BASE,
            RAM_CELLS,
            CapabilityPermission.LD
            | CapabilityPermission.ST
            | CapabilityPermission.LC
            | CapabilityPermission.SC
            | CapabilityPermission.SL,
            mmu.MEMORY_TYPE_NORMAL_COHERENT,
        ),
        MemoryRegion(
            "platform_devices",
            MemoryRegionKind.DEVICE,
            DEVICE_BASE,
            DEVICE_CELLS,
            CapabilityPermission.LD | CapabilityPermission.ST,
            mmu.MEMORY_TYPE_DEVICE_ORDERED,
        ),
        MemoryRegion(
            "secondary_mailbox",
            MemoryRegionKind.MAILBOX,
            MAILBOX_BASE,
            MAILBOX_CELLS,
            CapabilityPermission.LD | CapabilityPermission.ST,
            mmu.MEMORY_TYPE_DEVICE_ORDERED,
        ),
    ),
    fatal_entry_policy=FatalEntryPolicy.DEBUG_HALT,
    debug_transport=DebugTransportPolicy.SIMULATED_MMIO,
    halt_on_reset=False,
    cache_reset_policy=CacheResetPolicy.DISABLED,
    ram_reset_policy=RamResetPolicy.UNINITIALIZED,
)


def validate_profile(profile: TestPlatformProfile = TEST_PLATFORM_PROFILE) -> tuple[str, ...]:
    issues: list[str] = []
    if profile.core_count != reset.V01_CORE_COUNT:
        issues.append(f"core_count must be {reset.V01_CORE_COUNT}")
    if profile.secondary_lifecycle not in (CoreLifecycle.STOPPED, CoreLifecycle.WFI_PARKED):
        issues.append("secondary_lifecycle must be STOPPED or WFI_PARKED")

    regions = profile.memory_regions
    for index, region in enumerate(regions):
        if region.end <= region.base:
            issues.append(f"{region.name} has an empty range")
        for other in regions[index + 1 :]:
            if region.overlaps(other):
                issues.append(f"{region.name} overlaps {other.name}")

    rom_regions = tuple(region for region in regions if region.kind is MemoryRegionKind.ROM)
    ram_regions = tuple(region for region in regions if region.kind is MemoryRegionKind.RAM)
    device_regions = tuple(
        region
        for region in regions
        if region.kind in (MemoryRegionKind.DEVICE, MemoryRegionKind.MAILBOX)
    )
    if not rom_regions:
        issues.append("profile must define a ROM region")
    if not ram_regions:
        issues.append("profile must define a RAM region")
    if not device_regions:
        issues.append("profile must define a device or mailbox region")

    try:
        reset_rom = profile.reset_rom_region
    except (KeyError, ValueError) as exc:
        issues.append(str(exc))
    else:
        if not reset_rom.executable:
            issues.append("reset ROM must be executable")
        forbidden = (
            CapabilityPermission.ST
            | CapabilityPermission.SC
            | CapabilityPermission.SL
            | CapabilityPermission.SEAL
            | CapabilityPermission.UNSEAL
        )
        if reset_rom.permissions & forbidden:
            issues.append("reset ROM grants write, store-capability, seal, or unseal authority")

    if profile.halt_on_reset:
        issues.append("test platform reset must not enter debug halt by default")
    return tuple(issues)


def reset_pcc_capability(
    profile: TestPlatformProfile = TEST_PLATFORM_PROFILE,
) -> SlottedCapability:
    rom = profile.reset_rom_region
    payload = CapabilityPayload(
        cursor=profile.reset_vector,
        permissions=int(CapabilityPermission.EX),
        otype=OTYPE_UNSEALED,
        flags=int(CapabilityFlag.G),
    ).with_bounds(rom.base, rom.end)
    return SlottedCapability.from_capability(Capability.valid(payload), SLOT_0)


def cold_reset_cores(
    profile: TestPlatformProfile = TEST_PLATFORM_PROFILE,
) -> tuple[CoreState, ...]:
    issues = validate_profile(profile)
    if issues:
        raise ValueError("; ".join(issues))
    cores = list(reset.cold_reset_cores(profile.reset_vector, profile.secondary_lifecycle))
    cores[0].install_pcc(reset_pcc_capability(profile))
    return tuple(cores)

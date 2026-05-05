"""Program-image manifest boundaries for CPU v0.1 simulator fixtures.

Owner stories:
- I07-S03: byte-oriented containers serialize ordinary 24-bit cells.
- I08-S01: test-platform ROM/RAM/device region binding.
- I11-S01: program-image manifest and loader boundary contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from . import platform, serialization
from .capabilities import Capability
from .cells import (
    CAPABILITY_OBJECT_CELLS,
    CellRange,
    cell_range,
    is_aligned,
    require_cell_address,
)
from .memory import TaggedMemory
from .state import SLOT_0, require_slot


class ProgramImageError(ValueError):
    """Raised when a program-image manifest cannot be accepted."""


class ProgramImageSectionKind(Enum):
    TEXT = "TEXT"
    RODATA = "RODATA"
    DATA = "DATA"
    CAPDATA = "CAPDATA"


class ProgramImageTagPolicy(Enum):
    UNTYPED_CELLS = "UNTYPED_CELLS"
    TRUSTED_CAPABILITY_SIDECAR = "TRUSTED_CAPABILITY_SIDECAR"


class EntryCapabilitySource(Enum):
    RESET_PCC = "RESET_PCC"
    MANIFEST_ENTRY = "MANIFEST_ENTRY"


@dataclass(frozen=True)
class ProgramImageSection:
    """One manifest section mapped to a named platform memory region."""

    cell_section: serialization.CellSection
    region_name: str
    kind: ProgramImageSectionKind
    tag_policy: ProgramImageTagPolicy = ProgramImageTagPolicy.UNTYPED_CELLS

    def __post_init__(self) -> None:
        if not isinstance(self.cell_section, serialization.CellSection):
            raise TypeError("cell_section must be a CellSection")
        if not self.region_name:
            raise ValueError("region_name must not be empty")
        object.__setattr__(self, "kind", ProgramImageSectionKind(self.kind))
        object.__setattr__(self, "tag_policy", ProgramImageTagPolicy(self.tag_policy))

    @classmethod
    def from_cells(
        cls,
        *,
        name: str,
        region_name: str,
        base_cell: int,
        alignment_cells: int,
        payload_cells: tuple[int, ...],
        kind: ProgramImageSectionKind,
        tag_policy: ProgramImageTagPolicy = ProgramImageTagPolicy.UNTYPED_CELLS,
    ) -> "ProgramImageSection":
        return cls(
            serialization.CellSection(name, base_cell, alignment_cells, payload_cells),
            region_name,
            kind,
            tag_policy,
        )

    @classmethod
    def from_serialized_cells(
        cls,
        *,
        name: str,
        region_name: str,
        base_cell: int,
        alignment_cells: int,
        payload_octets: bytes | bytearray | memoryview,
        kind: ProgramImageSectionKind,
        tag_policy: ProgramImageTagPolicy = ProgramImageTagPolicy.UNTYPED_CELLS,
    ) -> "ProgramImageSection":
        return cls.from_cells(
            name=name,
            region_name=region_name,
            base_cell=base_cell,
            alignment_cells=alignment_cells,
            payload_cells=serialization.deserialize_cells(payload_octets),
            kind=kind,
            tag_policy=tag_policy,
        )

    @property
    def name(self) -> str:
        return self.cell_section.name

    @property
    def base_cell(self) -> int:
        return self.cell_section.base_cell

    @property
    def size_cells(self) -> int:
        return self.cell_section.size_cells

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    @property
    def range(self) -> CellRange:
        return cell_range(self.base_cell, self.size_cells)

    @property
    def uses_tag_sidecar(self) -> bool:
        return self.tag_policy is ProgramImageTagPolicy.TRUSTED_CAPABILITY_SIDECAR

    def contains_cell(self, address: int) -> bool:
        return self.cell_section.contains_cell(address)


@dataclass(frozen=True)
class ProgramImageManifest:
    """Manifest-level metadata for a simulator program image."""

    name: str
    entry_cell: int
    entry_source: EntryCapabilitySource
    sections: tuple[ProgramImageSection, ...]
    entry_slot: int = SLOT_0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("manifest name must not be empty")
        object.__setattr__(self, "entry_cell", require_cell_address(self.entry_cell, "entry_cell"))
        object.__setattr__(self, "entry_source", EntryCapabilitySource(self.entry_source))
        object.__setattr__(self, "entry_slot", require_slot(self.entry_slot))
        object.__setattr__(self, "sections", tuple(self.sections))
        for section in self.sections:
            if not isinstance(section, ProgramImageSection):
                raise TypeError("sections must contain ProgramImageSection values")

    @property
    def uses_reset_pcc(self) -> bool:
        return self.entry_source is EntryCapabilitySource.RESET_PCC


@dataclass(frozen=True)
class CapabilitySidecarEntry:
    """One trusted capability payload/tag installation requested by a loader."""

    section_name: str
    slot_base: int
    capability: Capability

    def __post_init__(self) -> None:
        if not self.section_name:
            raise ValueError("section_name must not be empty")
        object.__setattr__(self, "slot_base", require_cell_address(self.slot_base, "slot_base"))
        if not isinstance(self.capability, Capability):
            raise TypeError("capability must be a Capability")


@dataclass(frozen=True)
class ProgramImageLoadReport:
    sections_loaded: int
    cells_loaded: int
    sidecar_slots_loaded: int


def validate_program_image_manifest(
    manifest: ProgramImageManifest,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> tuple[str, ...]:
    """Return manifest acceptance issues without mutating simulator state."""
    if not isinstance(manifest, ProgramImageManifest):
        raise TypeError("manifest must be a ProgramImageManifest")
    if not isinstance(profile, platform.TestPlatformProfile):
        raise TypeError("profile must be a TestPlatformProfile")

    issues: list[str] = []
    if not manifest.sections:
        issues.append("program image must contain at least one section")
    if manifest.entry_slot != SLOT_0:
        issues.append("program image entry must enter slot 0")
    if manifest.uses_reset_pcc and manifest.entry_cell != profile.reset_vector:
        issues.append("RESET_PCC entry source requires entry_cell to equal the platform reset vector")

    seen_names: set[str] = set()
    for section in manifest.sections:
        if section.name in seen_names:
            issues.append(f"duplicate section name {section.name!r}")
        seen_names.add(section.name)
        issues.extend(_validate_section(section, profile))

    for left_index, left in enumerate(manifest.sections):
        for right in manifest.sections[left_index + 1 :]:
            if _ranges_overlap(left.range, right.range):
                issues.append(f"sections {left.name!r} and {right.name!r} overlap")

    if _entry_text_section(manifest, profile) is None:
        issues.append("entry_cell must be covered by a TEXT section in an executable region")

    return tuple(issues)


def require_valid_program_image_manifest(
    manifest: ProgramImageManifest,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> ProgramImageManifest:
    issues = validate_program_image_manifest(manifest, profile)
    if issues:
        raise ProgramImageError("; ".join(issues))
    return manifest


def validate_program_image_load(
    manifest: ProgramImageManifest,
    memory: TaggedMemory,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
    sidecars: Iterable[CapabilitySidecarEntry] = (),
) -> tuple[str, ...]:
    """Return loader acceptance issues without mutating memory."""
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    sidecar_tuple = _sidecar_tuple(sidecars)
    issues = list(validate_program_image_manifest(manifest, profile))
    section_by_name = {section.name: section for section in manifest.sections}

    for section in manifest.sections:
        if memory.overlaps_protected_range(section.base_cell, section.size_cells):
            issues.append(f"section {section.name!r} overlaps protected memory")

    sidecars_by_section: dict[str, list[CapabilitySidecarEntry]] = {}
    for sidecar in sidecar_tuple:
        section = section_by_name.get(sidecar.section_name)
        if section is None:
            issues.append(f"sidecar targets unknown section {sidecar.section_name!r}")
            continue
        sidecars_by_section.setdefault(section.name, []).append(sidecar)
        if not section.uses_tag_sidecar:
            issues.append(f"sidecar targets section {section.name!r} without sidecar policy")
            continue
        if not is_aligned(sidecar.slot_base, CAPABILITY_OBJECT_CELLS):
            issues.append(f"sidecar slot 0x{sidecar.slot_base:X} is not capability-slot aligned")
        sidecar_range = cell_range(sidecar.slot_base, CAPABILITY_OBJECT_CELLS)
        if not section.range.contains_range(sidecar_range):
            issues.append(f"sidecar slot 0x{sidecar.slot_base:X} is outside section {section.name!r}")

    for section in manifest.sections:
        if not section.uses_tag_sidecar:
            continue
        expected_slots = _section_capability_slots(section)
        observed_slots = {
            sidecar.slot_base
            for sidecar in sidecars_by_section.get(section.name, ())
        }
        missing = sorted(expected_slots - observed_slots)
        extras = sorted(observed_slots - expected_slots)
        if missing:
            issues.append(f"section {section.name!r} is missing sidecar slots")
        if extras:
            issues.append(f"section {section.name!r} has sidecar slots outside whole-slot coverage")

    return tuple(issues)


def load_program_image(
    manifest: ProgramImageManifest,
    memory: TaggedMemory,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
    sidecars: Iterable[CapabilitySidecarEntry] = (),
) -> ProgramImageLoadReport:
    """Load validated ordinary cells and explicit sidecar capabilities into memory."""
    sidecar_tuple = _sidecar_tuple(sidecars)
    issues = validate_program_image_load(manifest, memory, profile, sidecar_tuple)
    if issues:
        raise ProgramImageError("; ".join(issues))

    cells_loaded = 0
    for section in manifest.sections:
        memory.write_cells(section.base_cell, section.cell_section.payload_cells)
        cells_loaded += section.size_cells

    for sidecar in sidecar_tuple:
        memory.csc(sidecar.slot_base, sidecar.capability)

    return ProgramImageLoadReport(
        sections_loaded=len(manifest.sections),
        cells_loaded=cells_loaded,
        sidecar_slots_loaded=len(sidecar_tuple),
    )


def _validate_section(
    section: ProgramImageSection,
    profile: platform.TestPlatformProfile,
) -> tuple[str, ...]:
    issues = list(serialization.validate_section(section.cell_section))
    if section.size_cells == 0:
        issues.append(f"section {section.name!r} must not be empty")

    try:
        region = profile.region_by_name(section.region_name)
    except KeyError:
        issues.append(f"section {section.name!r} targets unknown region {section.region_name!r}")
        return tuple(issues)

    if not region.range.contains_range(section.range):
        issues.append(f"section {section.name!r} does not fit in region {region.name!r}")
    if region.kind not in (platform.MemoryRegionKind.ROM, platform.MemoryRegionKind.RAM):
        issues.append(f"section {section.name!r} targets non-loadable region {region.name!r}")
    if section.kind is ProgramImageSectionKind.TEXT and not region.executable:
        issues.append(f"TEXT section {section.name!r} must target an executable region")
    if section.kind in (ProgramImageSectionKind.DATA, ProgramImageSectionKind.CAPDATA) and not region.writable:
        issues.append(f"{section.kind.value} section {section.name!r} must target writable RAM")
    if section.kind is ProgramImageSectionKind.CAPDATA:
        if not section.uses_tag_sidecar:
            issues.append(f"CAPDATA section {section.name!r} requires a trusted capability sidecar")
        issues.extend(_validate_tag_sidecar(section, region))
    elif section.uses_tag_sidecar:
        issues.append(f"only CAPDATA section {section.name!r} may request a trusted capability sidecar")

    return tuple(issues)


def _validate_tag_sidecar(
    section: ProgramImageSection,
    region: platform.MemoryRegion,
) -> tuple[str, ...]:
    issues: list[str] = []
    if region.kind is not platform.MemoryRegionKind.RAM:
        issues.append(f"trusted capability sidecar for {section.name!r} must target RAM")
    if section.base_cell % CAPABILITY_OBJECT_CELLS:
        issues.append(f"trusted capability sidecar for {section.name!r} must start on a capability slot")
    if section.size_cells % CAPABILITY_OBJECT_CELLS:
        issues.append(f"trusted capability sidecar for {section.name!r} must cover whole capability slots")
    return tuple(issues)


def _entry_text_section(
    manifest: ProgramImageManifest,
    profile: platform.TestPlatformProfile,
) -> ProgramImageSection | None:
    for section in manifest.sections:
        if section.kind is not ProgramImageSectionKind.TEXT:
            continue
        if not section.contains_cell(manifest.entry_cell):
            continue
        try:
            region = profile.region_by_name(section.region_name)
        except KeyError:
            continue
        if region.executable:
            return section
    return None


def _ranges_overlap(left: CellRange, right: CellRange) -> bool:
    return left.base < right.top and right.base < left.top


def _section_capability_slots(section: ProgramImageSection) -> set[int]:
    return set(range(section.base_cell, section.end_cell, CAPABILITY_OBJECT_CELLS))


def _sidecar_tuple(sidecars: Iterable[CapabilitySidecarEntry]) -> tuple[CapabilitySidecarEntry, ...]:
    result = tuple(sidecars)
    for sidecar in result:
        if not isinstance(sidecar, CapabilitySidecarEntry):
            raise TypeError("sidecars must contain CapabilitySidecarEntry values")
    return result

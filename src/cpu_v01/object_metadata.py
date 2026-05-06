"""Relocatable object and symbol metadata for CPU v0.1 fixtures.

Owner stories:
- I07-S03: byte-oriented containers serialize ordinary 24-bit cells.
- I11-S01: program-image manifests consume section metadata.
- I17-S01: relocatable object and symbol metadata profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from . import cells, state


JsonValue = Any


class RelocatableObjectError(ValueError):
    """Raised when relocatable object metadata is not accepted."""


class ObjectSectionKind(Enum):
    TEXT = "TEXT"
    RODATA = "RODATA"
    DATA = "DATA"
    CAPDATA = "CAPDATA"


class CapabilitySidecarProvenance(Enum):
    NONE = "NONE"
    TRUSTED_LOADER = "TRUSTED_LOADER"


class ObjectSymbolKind(Enum):
    SECTION = "SECTION"
    FUNCTION = "FUNCTION"
    OBJECT = "OBJECT"
    CAPABILITY_OBJECT = "CAPABILITY_OBJECT"
    ENTRY = "ENTRY"


class ObjectSymbolBinding(Enum):
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"
    WEAK = "WEAK"


class AbiAttribute(Enum):
    CELL_ADDRESSED = "CELL_ADDRESSED"
    SLOT_AWARE_PCC = "SLOT_AWARE_PCC"
    PURE_CAPABILITY = "PURE_CAPABILITY"
    PROTECTED_RETURN_STACK = "PROTECTED_RETURN_STACK"
    CAPABILITY_TAG_SIDECARS = "CAPABILITY_TAG_SIDECARS"


MANDATORY_ABI_ATTRIBUTES = frozenset(
    {
        AbiAttribute.CELL_ADDRESSED,
        AbiAttribute.SLOT_AWARE_PCC,
        AbiAttribute.PURE_CAPABILITY,
    }
)


@dataclass(frozen=True)
class ObjectSection:
    """One relocatable section before final cell placement."""

    name: str
    kind: ObjectSectionKind
    alignment_cells: int
    size_cells: int
    sidecar_provenance: CapabilitySidecarProvenance = CapabilitySidecarProvenance.NONE

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("section name must not be empty")
        object.__setattr__(self, "kind", ObjectSectionKind(self.kind))
        object.__setattr__(
            self,
            "alignment_cells",
            cells.require_positive_cell_count(self.alignment_cells, "alignment_cells"),
        )
        object.__setattr__(
            self,
            "size_cells",
            cells.require_cell_count(self.size_cells, "size_cells"),
        )
        object.__setattr__(
            self,
            "sidecar_provenance",
            CapabilitySidecarProvenance(self.sidecar_provenance),
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "alignment_cells": self.alignment_cells,
            "size_cells": self.size_cells,
            "sidecar_provenance": self.sidecar_provenance.value,
        }


@dataclass(frozen=True)
class ObjectSymbol:
    """One slot-aware symbol in a relocatable section."""

    name: str
    section_name: str
    cell_offset: int
    kind: ObjectSymbolKind
    binding: ObjectSymbolBinding = ObjectSymbolBinding.LOCAL
    slot: int = state.SLOT_0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("symbol name must not be empty")
        if not self.section_name:
            raise ValueError("symbol section_name must not be empty")
        object.__setattr__(
            self,
            "cell_offset",
            cells.require_cell_count(self.cell_offset, "cell_offset"),
        )
        object.__setattr__(self, "kind", ObjectSymbolKind(self.kind))
        object.__setattr__(self, "binding", ObjectSymbolBinding(self.binding))
        object.__setattr__(self, "slot", state.require_slot(self.slot))

    @property
    def location_label(self) -> str:
        return f"{self.section_name}+{self.cell_offset}:slot{self.slot}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "section_name": self.section_name,
            "cell_offset": self.cell_offset,
            "slot": self.slot,
            "kind": self.kind.value,
            "binding": self.binding.value,
            "location": self.location_label,
        }


@dataclass(frozen=True)
class RelocatableObjectMetadata:
    """Metadata profile for one CPU v0.1 relocatable object fixture."""

    name: str
    sections: tuple[ObjectSection, ...]
    symbols: tuple[ObjectSymbol, ...]
    abi_attributes: tuple[AbiAttribute, ...]
    producer: str = "cpu_v01"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("object name must not be empty")
        if not self.producer:
            raise ValueError("producer must not be empty")
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "symbols", tuple(self.symbols))
        object.__setattr__(
            self,
            "abi_attributes",
            tuple(AbiAttribute(attribute) for attribute in self.abi_attributes),
        )
        for section in self.sections:
            if not isinstance(section, ObjectSection):
                raise TypeError("sections must contain ObjectSection values")
        for symbol in self.symbols:
            if not isinstance(symbol, ObjectSymbol):
                raise TypeError("symbols must contain ObjectSymbol values")

    def section_by_name(self, name: str) -> ObjectSection:
        for section in self.sections:
            if section.name == name:
                return section
        raise KeyError(f"unknown object section {name!r}")

    def symbol_by_name(self, name: str) -> ObjectSymbol:
        for symbol in self.symbols:
            if symbol.name == name:
                return symbol
        raise KeyError(f"unknown object symbol {name!r}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "producer": self.producer,
            "abi_attributes": [attribute.value for attribute in self.abi_attributes],
            "sections": [section.as_dict() for section in self.sections],
            "symbols": [symbol.as_dict() for symbol in self.symbols],
        }


def validate_relocatable_object_metadata(
    metadata: RelocatableObjectMetadata,
) -> tuple[str, ...]:
    """Return deterministic metadata acceptance issues without mutation."""
    if not isinstance(metadata, RelocatableObjectMetadata):
        raise TypeError("metadata must be RelocatableObjectMetadata")

    issues: list[str] = []
    if not metadata.sections:
        issues.append("relocatable object must contain at least one section")

    attributes = set(metadata.abi_attributes)
    for attribute in sorted(MANDATORY_ABI_ATTRIBUTES, key=lambda item: item.value):
        if attribute not in attributes:
            issues.append(f"object ABI attributes must include {attribute.value}")

    section_by_name: dict[str, ObjectSection] = {}
    for section in metadata.sections:
        if section.name in section_by_name:
            issues.append(f"duplicate section name {section.name!r}")
        else:
            section_by_name[section.name] = section
        issues.extend(_validate_section_sidecar(section))

    seen_symbols: set[str] = set()
    for symbol in metadata.symbols:
        if symbol.name in seen_symbols:
            issues.append(f"duplicate symbol name {symbol.name!r}")
        seen_symbols.add(symbol.name)
        section = section_by_name.get(symbol.section_name)
        if section is None:
            issues.append(f"symbol {symbol.name!r} targets unknown section {symbol.section_name!r}")
            continue
        issues.extend(_validate_symbol_location(symbol, section))
        issues.extend(_validate_symbol_kind(symbol, section))

    return tuple(issues)


def require_valid_relocatable_object_metadata(
    metadata: RelocatableObjectMetadata,
) -> RelocatableObjectMetadata:
    issues = validate_relocatable_object_metadata(metadata)
    if issues:
        raise RelocatableObjectError("; ".join(issues))
    return metadata


def _validate_section_sidecar(section: ObjectSection) -> tuple[str, ...]:
    issues: list[str] = []
    if section.kind is ObjectSectionKind.CAPDATA:
        if section.sidecar_provenance is not CapabilitySidecarProvenance.TRUSTED_LOADER:
            issues.append(
                f"CAPDATA section {section.name!r} must declare TRUSTED_LOADER sidecar provenance"
            )
        if section.alignment_cells % cells.CAPABILITY_OBJECT_CELLS:
            issues.append(
                f"CAPDATA section {section.name!r} alignment must preserve capability slots"
            )
        if section.size_cells % cells.CAPABILITY_OBJECT_CELLS:
            issues.append(
                f"CAPDATA section {section.name!r} must cover whole capability slots"
            )
    elif section.sidecar_provenance is not CapabilitySidecarProvenance.NONE:
        issues.append(
            f"non-CAPDATA section {section.name!r} must not declare capability sidecar provenance"
        )
    return tuple(issues)


def _validate_symbol_location(
    symbol: ObjectSymbol,
    section: ObjectSection,
) -> tuple[str, ...]:
    issues: list[str] = []
    if symbol.cell_offset >= section.size_cells:
        issues.append(f"symbol {symbol.name!r} is outside section {section.name!r}")
    if symbol.slot == state.SLOT_1 and section.kind is not ObjectSectionKind.TEXT:
        issues.append(f"symbol {symbol.name!r} uses slot 1 outside a TEXT section")
    if symbol.kind is ObjectSymbolKind.SECTION and (
        symbol.cell_offset != 0 or symbol.slot != state.SLOT_0
    ):
        issues.append(f"section symbol {symbol.name!r} must point at section slot 0")
    return tuple(issues)


def _validate_symbol_kind(
    symbol: ObjectSymbol,
    section: ObjectSection,
) -> tuple[str, ...]:
    if symbol.kind in (ObjectSymbolKind.FUNCTION, ObjectSymbolKind.ENTRY):
        if section.kind is not ObjectSectionKind.TEXT:
            return (f"{symbol.kind.value} symbol {symbol.name!r} must target TEXT",)
    if symbol.kind is ObjectSymbolKind.OBJECT:
        if section.kind not in (ObjectSectionKind.DATA, ObjectSectionKind.RODATA):
            return (f"OBJECT symbol {symbol.name!r} must target DATA or RODATA",)
    if symbol.kind is ObjectSymbolKind.CAPABILITY_OBJECT:
        if section.kind is not ObjectSectionKind.CAPDATA:
            return (f"CAPABILITY_OBJECT symbol {symbol.name!r} must target CAPDATA",)
    return ()

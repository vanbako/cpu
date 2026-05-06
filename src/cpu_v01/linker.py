"""Linker relocation fixtures for CPU v0.1 object metadata.

Owner stories:
- I07-S02: assembler/disassembler binary fixtures.
- I11-S02: program-image loading consumes placed cell payloads.
- I17-S01: relocatable object metadata profile.
- I17-S02: linker relocation fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from . import assembly, cells, object_metadata as obj, state
from .instructions import InstructionSize


JsonValue = Any


class LinkerError(ValueError):
    """Raised when link fixture validation or relocation fails."""


class RelocationKind(Enum):
    ABSOLUTE_CELL48 = "ABSOLUTE_CELL48"
    DIRECT_TARGET16 = "DIRECT_TARGET16"
    CONDITIONAL_TARGET12 = "CONDITIONAL_TARGET12"


@dataclass(frozen=True)
class SectionPayload:
    section_name: str
    payload_cells: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.section_name:
            raise ValueError("section_name must not be empty")
        object.__setattr__(
            self,
            "payload_cells",
            tuple(cells.require_cell_value(value) for value in self.payload_cells),
        )


@dataclass(frozen=True)
class Relocation:
    section_name: str
    cell_offset: int
    kind: RelocationKind
    symbol_name: str
    addend_cells: int = 0

    def __post_init__(self) -> None:
        if not self.section_name:
            raise ValueError("relocation section_name must not be empty")
        object.__setattr__(
            self,
            "cell_offset",
            cells.require_cell_count(self.cell_offset, "cell_offset"),
        )
        object.__setattr__(self, "kind", RelocationKind(self.kind))
        if not self.symbol_name:
            raise ValueError("relocation symbol_name must not be empty")
        if type(self.addend_cells) is not int:
            raise TypeError("addend_cells must be an int")


@dataclass(frozen=True)
class LinkerObject:
    metadata: obj.RelocatableObjectMetadata
    section_payloads: tuple[SectionPayload, ...]
    relocations: tuple[Relocation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, obj.RelocatableObjectMetadata):
            raise TypeError("metadata must be RelocatableObjectMetadata")
        object.__setattr__(self, "section_payloads", tuple(self.section_payloads))
        object.__setattr__(self, "relocations", tuple(self.relocations))
        for payload in self.section_payloads:
            if not isinstance(payload, SectionPayload):
                raise TypeError("section_payloads must contain SectionPayload values")
        for relocation in self.relocations:
            if not isinstance(relocation, Relocation):
                raise TypeError("relocations must contain Relocation values")


@dataclass(frozen=True)
class LinkedSection:
    object_name: str
    section_name: str
    base_cell: int
    payload_cells: tuple[int, ...]
    kind: obj.ObjectSectionKind

    @property
    def qualified_name(self) -> str:
        return f"{self.object_name}:{self.section_name}"

    @property
    def end_cell(self) -> int:
        return self.base_cell + len(self.payload_cells)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "object_name": self.object_name,
            "section_name": self.section_name,
            "qualified_name": self.qualified_name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "kind": self.kind.value,
            "payload_cells": list(self.payload_cells),
        }


@dataclass(frozen=True)
class ResolvedSymbol:
    name: str
    object_name: str
    section_name: str
    cell_address: int
    slot: int
    binding: obj.ObjectSymbolBinding
    kind: obj.ObjectSymbolKind

    @property
    def location_label(self) -> str:
        return f"0x{self.cell_address:X}:slot{self.slot}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "object_name": self.object_name,
            "section_name": self.section_name,
            "cell_address": self.cell_address,
            "slot": self.slot,
            "binding": self.binding.value,
            "kind": self.kind.value,
            "location": self.location_label,
        }


@dataclass(frozen=True)
class LinkedImage:
    sections: tuple[LinkedSection, ...]
    symbols: tuple[ResolvedSymbol, ...]

    def section_by_name(self, object_name: str, section_name: str) -> LinkedSection:
        for section in self.sections:
            if section.object_name == object_name and section.section_name == section_name:
                return section
        raise KeyError(f"unknown linked section {object_name}:{section_name}")

    def symbol_by_name(self, name: str) -> ResolvedSymbol:
        matches = tuple(symbol for symbol in self.symbols if symbol.name == name)
        if len(matches) != 1:
            raise KeyError(f"symbol {name!r} is not uniquely resolved")
        return matches[0]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "sections": [section.as_dict() for section in self.sections],
            "symbols": [symbol.as_dict() for symbol in self.symbols],
        }


def validate_linker_inputs(
    linker_objects: tuple[LinkerObject, ...],
    *,
    base_cell: int = 0,
) -> tuple[str, ...]:
    """Return deterministic linker input issues without producing an image."""
    issues, _ = _build_linked_image(linker_objects, base_cell=base_cell, apply_relocations=False)
    return issues


def link_objects(
    linker_objects: tuple[LinkerObject, ...],
    *,
    base_cell: int = 0,
) -> LinkedImage:
    """Place sections and apply supported relocation fixtures."""
    issues, image = _build_linked_image(linker_objects, base_cell=base_cell, apply_relocations=True)
    if issues:
        raise LinkerError("; ".join(issues))
    assert image is not None
    return image


def _build_linked_image(
    linker_objects: tuple[LinkerObject, ...],
    *,
    base_cell: int,
    apply_relocations: bool,
) -> tuple[tuple[str, ...], LinkedImage | None]:
    object_tuple = _linker_object_tuple(linker_objects)
    base_cell = cells.require_cell_address(base_cell, "base_cell")
    issues: list[str] = []

    seen_objects: set[str] = set()
    payloads_by_object: dict[tuple[str, str], SectionPayload] = {}
    for linker_object in object_tuple:
        object_name = linker_object.metadata.name
        if object_name in seen_objects:
            issues.append(f"duplicate object name {object_name!r}")
        seen_objects.add(object_name)
        issues.extend(obj.validate_relocatable_object_metadata(linker_object.metadata))
        issues.extend(_validate_payloads(linker_object, payloads_by_object))
        issues.extend(_validate_relocations(linker_object))

    placements: dict[tuple[str, str], int] = {}
    placed_sections: list[LinkedSection] = []
    current = base_cell
    for linker_object in object_tuple:
        object_name = linker_object.metadata.name
        for section in linker_object.metadata.sections:
            current = _align_up(current, section.alignment_cells)
            try:
                section_range = cells.cell_range(current, section.size_cells)
            except ValueError as exc:
                issues.append(f"section {object_name}:{section.name} placement failed: {exc}")
                continue
            placements[(object_name, section.name)] = section_range.base
            payload = payloads_by_object.get((object_name, section.name))
            if payload is not None:
                placed_sections.append(
                    LinkedSection(
                        object_name,
                        section.name,
                        section_range.base,
                        payload.payload_cells,
                        section.kind,
                    )
                )
            current = section_range.top

    symbols, global_symbols, symbol_issues = _resolve_symbols(object_tuple, placements)
    issues.extend(symbol_issues)
    if issues:
        return tuple(issues), None

    mutable_payloads: dict[tuple[str, str], list[int]] = {
        (section.object_name, section.section_name): list(section.payload_cells)
        for section in placed_sections
    }
    relocation_issues = _apply_relocations(
        object_tuple,
        placements,
        mutable_payloads,
        symbols,
        global_symbols,
        apply_relocations=apply_relocations,
    )
    issues.extend(relocation_issues)
    if issues:
        return tuple(issues), None

    image_sections = tuple(
        LinkedSection(
            section.object_name,
            section.section_name,
            section.base_cell,
            tuple(mutable_payloads[(section.object_name, section.section_name)]),
            section.kind,
        )
        for section in placed_sections
    )
    return (), LinkedImage(image_sections, tuple(symbols.values()))


def _linker_object_tuple(linker_objects: tuple[LinkerObject, ...]) -> tuple[LinkerObject, ...]:
    object_tuple = tuple(linker_objects)
    for linker_object in object_tuple:
        if not isinstance(linker_object, LinkerObject):
            raise TypeError("linker_objects must contain LinkerObject values")
    return object_tuple


def _validate_payloads(
    linker_object: LinkerObject,
    payloads_by_object: dict[tuple[str, str], SectionPayload],
) -> tuple[str, ...]:
    issues: list[str] = []
    object_name = linker_object.metadata.name
    section_by_name = {section.name: section for section in linker_object.metadata.sections}
    seen_payloads: set[str] = set()
    for payload in linker_object.section_payloads:
        key = (object_name, payload.section_name)
        if payload.section_name in seen_payloads:
            issues.append(f"duplicate payload for section {object_name}:{payload.section_name}")
        seen_payloads.add(payload.section_name)
        section = section_by_name.get(payload.section_name)
        if section is None:
            issues.append(f"payload targets unknown section {object_name}:{payload.section_name}")
            continue
        if len(payload.payload_cells) != section.size_cells:
            issues.append(
                f"payload for section {object_name}:{payload.section_name} has "
                f"{len(payload.payload_cells)} cells, expected {section.size_cells}"
            )
        payloads_by_object[key] = payload

    for section in linker_object.metadata.sections:
        if section.name not in seen_payloads:
            issues.append(f"missing payload for section {object_name}:{section.name}")
    return tuple(issues)


def _validate_relocations(linker_object: LinkerObject) -> tuple[str, ...]:
    issues: list[str] = []
    object_name = linker_object.metadata.name
    section_by_name = {section.name: section for section in linker_object.metadata.sections}
    for relocation in linker_object.relocations:
        section = section_by_name.get(relocation.section_name)
        if section is None:
            issues.append(
                f"relocation in {object_name} targets unknown section {relocation.section_name!r}"
            )
            continue
        cells_needed = 2 if relocation.kind is RelocationKind.ABSOLUTE_CELL48 else 1
        if relocation.cell_offset + cells_needed > section.size_cells:
            issues.append(
                f"relocation in {object_name}:{section.name} at cell {relocation.cell_offset} "
                f"does not fit {section.size_cells}-cell section"
            )
    return tuple(issues)


def _resolve_symbols(
    linker_objects: tuple[LinkerObject, ...],
    placements: dict[tuple[str, str], int],
) -> tuple[
    dict[tuple[str, str], ResolvedSymbol],
    dict[str, ResolvedSymbol],
    tuple[str, ...],
]:
    issues: list[str] = []
    symbols: dict[tuple[str, str], ResolvedSymbol] = {}
    global_symbols: dict[str, ResolvedSymbol] = {}
    for linker_object in linker_objects:
        object_name = linker_object.metadata.name
        for symbol in linker_object.metadata.symbols:
            section_base = placements.get((object_name, symbol.section_name))
            if section_base is None:
                continue
            resolved = ResolvedSymbol(
                symbol.name,
                object_name,
                symbol.section_name,
                section_base + symbol.cell_offset,
                symbol.slot,
                symbol.binding,
                symbol.kind,
            )
            symbols[(object_name, symbol.name)] = resolved
            if symbol.binding is obj.ObjectSymbolBinding.LOCAL:
                continue
            if symbol.name in global_symbols:
                issues.append(f"duplicate exported symbol {symbol.name!r}")
            else:
                global_symbols[symbol.name] = resolved
    return symbols, global_symbols, tuple(issues)


def _apply_relocations(
    linker_objects: tuple[LinkerObject, ...],
    placements: dict[tuple[str, str], int],
    mutable_payloads: dict[tuple[str, str], list[int]],
    symbols: dict[tuple[str, str], ResolvedSymbol],
    global_symbols: dict[str, ResolvedSymbol],
    *,
    apply_relocations: bool,
) -> tuple[str, ...]:
    issues: list[str] = []
    for linker_object in linker_objects:
        object_name = linker_object.metadata.name
        for relocation in linker_object.relocations:
            target = symbols.get((object_name, relocation.symbol_name))
            if target is None:
                target = global_symbols.get(relocation.symbol_name)
            if target is None:
                issues.append(f"undefined symbol {relocation.symbol_name!r} in {object_name}")
                continue
            value = target.cell_address + relocation.addend_cells
            if not 0 <= value < cells.ADDRESS_SPACE_CELLS:
                issues.append(f"relocation to {relocation.symbol_name!r} overflows 48-bit cell address")
                continue
            payload = mutable_payloads[(object_name, relocation.section_name)]
            patch_issue = _patch_relocation(payload, relocation, target, value, apply_relocations)
            if patch_issue is not None:
                issues.append(f"{object_name}:{relocation.section_name}: {patch_issue}")
    return tuple(issues)


def _patch_relocation(
    payload: list[int],
    relocation: Relocation,
    target: ResolvedSymbol,
    value: int,
    apply_relocations: bool,
) -> str | None:
    offset = relocation.cell_offset
    if relocation.kind is RelocationKind.ABSOLUTE_CELL48:
        if apply_relocations:
            payload[offset] = value & cells.CELL_MASK
            payload[offset + 1] = (value >> cells.CELL_BITS) & cells.CELL_MASK
        return None

    if target.slot != state.SLOT_0:
        return f"{relocation.kind.value} cannot encode slot {target.slot} target {target.name!r}"

    if relocation.kind is RelocationKind.DIRECT_TARGET16:
        if value >= (1 << 16):
            return f"DIRECT_TARGET16 relocation to {target.name!r} overflows 16 bits"
        try:
            decoded = assembly.decode_value(InstructionSize.BITS_24, payload[offset])
        except assembly.DecodeError as exc:
            return f"DIRECT_TARGET16 patch site is not a 24-bit instruction: {exc}"
        if decoded.form.mnemonic not in {"BRA", "CALL"}:
            return f"DIRECT_TARGET16 patch site must be BRA or CALL, got {decoded.form.mnemonic}"
        if apply_relocations:
            payload[offset] = (payload[offset] & 0xFF0000) | value
        return None

    if relocation.kind is RelocationKind.CONDITIONAL_TARGET12:
        if value >= (1 << 12):
            return f"CONDITIONAL_TARGET12 relocation to {target.name!r} overflows 12 bits"
        try:
            decoded = assembly.decode_value(InstructionSize.BITS_24, payload[offset])
        except assembly.DecodeError as exc:
            return f"CONDITIONAL_TARGET12 patch site is not a 24-bit instruction: {exc}"
        if decoded.form.mnemonic != "BCC":
            return f"CONDITIONAL_TARGET12 patch site must be BCC, got {decoded.form.mnemonic}"
        if apply_relocations:
            payload[offset] = (payload[offset] & 0xFFF000) | value
        return None

    raise AssertionError(f"unhandled relocation kind {relocation.kind}")


def _align_up(address: int, alignment_cells: int) -> int:
    alignment_cells = cells.require_positive_cell_count(alignment_cells, "alignment_cells")
    remainder = address % alignment_cells
    if remainder == 0:
        return address
    return address + alignment_cells - remainder

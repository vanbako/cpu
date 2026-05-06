"""Debug metadata fixtures for CPU v0.1 toolchain outputs.

Owner stories:
- E12-S01: halted-core debug register visibility.
- E15-S06: software-facing debug and unwind contract audit.
- I09-S04: debugger register access and unwind supplement.
- I17-S03: debug line, symbol, and register metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from . import abi, assembly, cells, debug_abi, linker, object_metadata as obj, state
from .instructions import InstructionSize


JsonValue = Any


class DebugMetadataError(ValueError):
    """Raised when debug metadata cannot be emitted for a linked image."""


class RegisterAbiRole(Enum):
    INTEGER_ARGUMENT = "INTEGER_ARGUMENT"
    INTEGER_RETURN = "INTEGER_RETURN"
    INTEGER_CALLER_SAVED = "INTEGER_CALLER_SAVED"
    INTEGER_CALLEE_SAVED = "INTEGER_CALLEE_SAVED"
    CAPABILITY_ARGUMENT = "CAPABILITY_ARGUMENT"
    CAPABILITY_RETURN = "CAPABILITY_RETURN"
    CAPABILITY_CALLER_SAVED = "CAPABILITY_CALLER_SAVED"
    CAPABILITY_CALLEE_SAVED = "CAPABILITY_CALLEE_SAVED"
    SYSCALL_SERVICE = "SYSCALL_SERVICE"
    SYSCALL_INTEGER_ARGUMENT = "SYSCALL_INTEGER_ARGUMENT"
    SYSCALL_INTEGER_RETURN = "SYSCALL_INTEGER_RETURN"
    SYSCALL_CAPABILITY_ARGUMENT = "SYSCALL_CAPABILITY_ARGUMENT"
    SYSCALL_CAPABILITY_RETURN = "SYSCALL_CAPABILITY_RETURN"
    CONTEXT_SWITCH = "CONTEXT_SWITCH"


@dataclass(frozen=True)
class SourceLine:
    section_name: str
    cell_offset: int
    slot: int
    source_file: str
    line_number: int
    column: int = 1
    source_text: str = ""

    def __post_init__(self) -> None:
        if not self.section_name:
            raise ValueError("source line section_name must not be empty")
        object.__setattr__(
            self,
            "cell_offset",
            cells.require_cell_count(self.cell_offset, "cell_offset"),
        )
        object.__setattr__(self, "slot", state.require_slot(self.slot))
        if not self.source_file:
            raise ValueError("source_file must not be empty")
        if type(self.line_number) is not int or self.line_number <= 0:
            raise ValueError("line_number must be a positive int")
        if type(self.column) is not int or self.column <= 0:
            raise ValueError("column must be a positive int")


@dataclass(frozen=True)
class FunctionRange:
    symbol_name: str
    size_cells: int
    source_file: str = ""

    def __post_init__(self) -> None:
        if not self.symbol_name:
            raise ValueError("function symbol_name must not be empty")
        object.__setattr__(
            self,
            "size_cells",
            cells.require_positive_cell_count(self.size_cells, "size_cells"),
        )


@dataclass(frozen=True)
class DebugObject:
    object_name: str
    source_lines: tuple[SourceLine, ...]
    function_ranges: tuple[FunctionRange, ...] = ()

    def __post_init__(self) -> None:
        if not self.object_name:
            raise ValueError("debug object_name must not be empty")
        object.__setattr__(self, "source_lines", tuple(self.source_lines))
        object.__setattr__(self, "function_ranges", tuple(self.function_ranges))
        for source_line in self.source_lines:
            if not isinstance(source_line, SourceLine):
                raise TypeError("source_lines must contain SourceLine values")
        for function_range in self.function_ranges:
            if not isinstance(function_range, FunctionRange):
                raise TypeError("function_ranges must contain FunctionRange values")


@dataclass(frozen=True)
class DebugLineRecord:
    object_name: str
    section_name: str
    cell_address: int
    slot: int
    source_file: str
    line_number: int
    column: int
    source_text: str = ""

    @property
    def location_label(self) -> str:
        return f"0x{self.cell_address:04X}:slot{self.slot}"

    @property
    def source_label(self) -> str:
        return f"{self.source_file}:{self.line_number}:{self.column}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "object_name": self.object_name,
            "section_name": self.section_name,
            "cell_address": self.cell_address,
            "slot": self.slot,
            "location": self.location_label,
            "source": self.source_label,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class DebugSymbolRecord:
    name: str
    object_name: str
    section_name: str
    cell_address: int
    slot: int
    kind: obj.ObjectSymbolKind
    binding: obj.ObjectSymbolBinding

    @property
    def location_label(self) -> str:
        return f"0x{self.cell_address:04X}:slot{self.slot}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "object_name": self.object_name,
            "section_name": self.section_name,
            "cell_address": self.cell_address,
            "slot": self.slot,
            "location": self.location_label,
            "kind": self.kind.value,
            "binding": self.binding.value,
        }


@dataclass(frozen=True)
class DebugFunctionRecord:
    name: str
    object_name: str
    section_name: str
    start_cell: int
    start_slot: int
    end_cell: int
    source_file: str = ""

    def contains_pcc(self, cell_address: int, slot: int) -> bool:
        cell_address = cells.require_cell_address(cell_address)
        slot = state.require_slot(slot)
        if not self.start_cell <= cell_address < self.end_cell:
            return False
        if cell_address == self.start_cell and slot < self.start_slot:
            return False
        return True

    @property
    def location_label(self) -> str:
        return f"0x{self.start_cell:04X}:slot{self.start_slot}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "object_name": self.object_name,
            "section_name": self.section_name,
            "start_cell": self.start_cell,
            "start_slot": self.start_slot,
            "end_cell": self.end_cell,
            "location": self.location_label,
            "source_file": self.source_file,
        }


@dataclass(frozen=True)
class DebugRegisterRecord:
    name: str
    register_class: debug_abi.DebugRegisterClass
    index: int
    readable: bool
    writable: bool
    tag_visible: bool
    slot_visible: bool
    abi_roles: tuple[RegisterAbiRole, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "register_class": self.register_class.value,
            "index": self.index,
            "readable": self.readable,
            "writable": self.writable,
            "tag_visible": self.tag_visible,
            "slot_visible": self.slot_visible,
            "abi_roles": [role.value for role in self.abi_roles],
        }


@dataclass(frozen=True)
class ProtectedUnwindHint:
    operation: debug_abi.DebugUnwindOperation
    updates_rsc_cursor: bool
    writes_return_slot: bool
    requires_valid_return_capability: bool
    atomic_payload_tag: bool
    entry_cells: int
    replacement_otype: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "operation": self.operation.value,
            "updates_rsc_cursor": self.updates_rsc_cursor,
            "writes_return_slot": self.writes_return_slot,
            "requires_valid_return_capability": self.requires_valid_return_capability,
            "atomic_payload_tag": self.atomic_payload_tag,
            "entry_cells": self.entry_cells,
            "replacement_otype": self.replacement_otype,
        }


@dataclass(frozen=True)
class DebugMetadataImage:
    line_records: tuple[DebugLineRecord, ...]
    symbol_records: tuple[DebugSymbolRecord, ...]
    function_records: tuple[DebugFunctionRecord, ...]
    register_records: tuple[DebugRegisterRecord, ...]
    unwind_hints: tuple[ProtectedUnwindHint, ...]

    def lines_for_pcc(self, cell_address: int, slot: int) -> tuple[DebugLineRecord, ...]:
        cell_address = cells.require_cell_address(cell_address)
        slot = state.require_slot(slot)
        return tuple(
            line
            for line in self.line_records
            if line.cell_address == cell_address and line.slot == slot
        )

    def line_for_pcc(self, cell_address: int, slot: int) -> DebugLineRecord | None:
        matches = self.lines_for_pcc(cell_address, slot)
        if not matches:
            return None
        return matches[0]

    def symbols_at(self, cell_address: int, slot: int) -> tuple[DebugSymbolRecord, ...]:
        cell_address = cells.require_cell_address(cell_address)
        slot = state.require_slot(slot)
        return tuple(
            symbol
            for symbol in self.symbol_records
            if symbol.cell_address == cell_address and symbol.slot == slot
        )

    def function_for_pcc(self, cell_address: int, slot: int) -> DebugFunctionRecord | None:
        cell_address = cells.require_cell_address(cell_address)
        slot = state.require_slot(slot)
        matches = tuple(
            function
            for function in self.function_records
            if function.contains_pcc(cell_address, slot)
        )
        if not matches:
            return None
        return sorted(
            matches,
            key=lambda function: (function.start_cell, function.start_slot, -function.end_cell),
            reverse=True,
        )[0]

    def register_by_name(self, name: str) -> DebugRegisterRecord:
        if not isinstance(name, str):
            raise TypeError("register name must be a str")
        normalized = name.upper()
        for register in self.register_records:
            if register.name == normalized:
                return register
        raise KeyError(f"unknown debug register metadata {name!r}")

    def unwind_hint(self, operation: debug_abi.DebugUnwindOperation | str) -> ProtectedUnwindHint:
        operation = debug_abi.DebugUnwindOperation(operation)
        for hint in self.unwind_hints:
            if hint.operation is operation:
                return hint
        raise KeyError(f"unknown unwind operation {operation.value!r}")

    def format_location(self, cell_address: int, slot: int) -> str:
        cell_address = cells.require_cell_address(cell_address)
        slot = state.require_slot(slot)
        parts = [f"0x{cell_address:04X}:slot{slot}"]
        exact_symbols = sorted(self.symbols_at(cell_address, slot), key=lambda symbol: symbol.name)
        if exact_symbols:
            parts.append("<" + ", ".join(symbol.name for symbol in exact_symbols) + ">")
        else:
            function = self.function_for_pcc(cell_address, slot)
            if function is not None:
                offset = cell_address - function.start_cell
                suffix = "" if offset == 0 else f"+0x{offset:X}"
                parts.append(f"<{function.name}{suffix}>")

        line = self.line_for_pcc(cell_address, slot)
        if line is not None:
            parts.append(line.source_label)
        return " ".join(parts)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "lines": [line.as_dict() for line in self.line_records],
            "symbols": [symbol.as_dict() for symbol in self.symbol_records],
            "functions": [function.as_dict() for function in self.function_records],
            "registers": [register.as_dict() for register in self.register_records],
            "unwind_hints": [hint.as_dict() for hint in self.unwind_hints],
        }


def validate_debug_metadata(
    linked_image: linker.LinkedImage,
    debug_objects: tuple[DebugObject, ...],
) -> tuple[str, ...]:
    """Return deterministic debug metadata issues without emitting records."""
    issues, _ = _build_debug_metadata(linked_image, debug_objects)
    return issues


def emit_debug_metadata(
    linked_image: linker.LinkedImage,
    debug_objects: tuple[DebugObject, ...],
) -> DebugMetadataImage:
    """Resolve source, symbol, register, and unwind metadata for a linked image."""
    issues, image = _build_debug_metadata(linked_image, debug_objects)
    if issues:
        raise DebugMetadataError("; ".join(issues))
    assert image is not None
    return image


def disassemble_linked_section(
    linked_image: linker.LinkedImage,
    object_name: str,
    section_name: str,
    debug_image: DebugMetadataImage,
) -> tuple[str, ...]:
    """Disassemble a linked text section with symbolic debug locations."""
    if not isinstance(debug_image, DebugMetadataImage):
        raise TypeError("debug_image must be a DebugMetadataImage")
    section = linked_image.section_by_name(object_name, section_name)
    if section.kind is not obj.ObjectSectionKind.TEXT:
        raise DebugMetadataError(f"section {object_name}:{section_name} is not TEXT")
    lines: list[str] = []
    for cell_address, slot, decoded in _iter_decoded_instructions(section):
        location = debug_image.format_location(cell_address, slot)
        lines.append(f"{location}: {assembly.format_instruction(decoded)}")
    return tuple(lines)


def _build_debug_metadata(
    linked_image: linker.LinkedImage,
    debug_objects: tuple[DebugObject, ...],
) -> tuple[tuple[str, ...], DebugMetadataImage | None]:
    if not isinstance(linked_image, linker.LinkedImage):
        raise TypeError("linked_image must be a LinkedImage")
    debug_object_tuple = tuple(debug_objects)
    for debug_object in debug_object_tuple:
        if not isinstance(debug_object, DebugObject):
            raise TypeError("debug_objects must contain DebugObject values")

    issues: list[str] = []
    sections = {
        (section.object_name, section.section_name): section
        for section in linked_image.sections
    }
    symbol_records = _symbol_records(linked_image)
    symbols_by_object_name = {
        (symbol.object_name, symbol.name): symbol
        for symbol in symbol_records
    }
    line_records: list[DebugLineRecord] = []
    function_records: list[DebugFunctionRecord] = []
    seen_line_locations: set[tuple[int, int]] = set()

    for debug_object in debug_object_tuple:
        if not any(section.object_name == debug_object.object_name for section in linked_image.sections):
            issues.append(f"debug object {debug_object.object_name!r} has no linked sections")
        for source_line in debug_object.source_lines:
            section = sections.get((debug_object.object_name, source_line.section_name))
            if section is None:
                issues.append(
                    f"source line targets unknown section "
                    f"{debug_object.object_name}:{source_line.section_name}"
                )
                continue
            if source_line.cell_offset >= len(section.payload_cells):
                issues.append(
                    f"source line {source_line.source_file}:{source_line.line_number} "
                    f"targets cell {source_line.cell_offset} outside "
                    f"{debug_object.object_name}:{source_line.section_name}"
                )
                continue
            if source_line.slot == state.SLOT_1 and section.kind is not obj.ObjectSectionKind.TEXT:
                issues.append(
                    f"source line {source_line.source_file}:{source_line.line_number} "
                    "uses slot 1 outside TEXT"
                )
                continue
            absolute_cell = section.base_cell + source_line.cell_offset
            line_key = (absolute_cell, source_line.slot)
            if line_key in seen_line_locations:
                issues.append(f"duplicate debug line for 0x{absolute_cell:04X}:slot{source_line.slot}")
                continue
            seen_line_locations.add(line_key)
            line_records.append(
                DebugLineRecord(
                    debug_object.object_name,
                    source_line.section_name,
                    absolute_cell,
                    source_line.slot,
                    source_line.source_file,
                    source_line.line_number,
                    source_line.column,
                    source_line.source_text,
                )
            )

        for function_range in debug_object.function_ranges:
            symbol = symbols_by_object_name.get((debug_object.object_name, function_range.symbol_name))
            if symbol is None:
                issues.append(
                    f"function range references unknown symbol "
                    f"{debug_object.object_name}:{function_range.symbol_name}"
                )
                continue
            if symbol.kind not in (obj.ObjectSymbolKind.FUNCTION, obj.ObjectSymbolKind.ENTRY):
                issues.append(
                    f"function range {debug_object.object_name}:{function_range.symbol_name} "
                    f"targets {symbol.kind.value} symbol"
                )
                continue
            section = sections.get((symbol.object_name, symbol.section_name))
            if section is None:
                issues.append(
                    f"function range {debug_object.object_name}:{function_range.symbol_name} "
                    "targets an unplaced section"
                )
                continue
            end_cell = symbol.cell_address + function_range.size_cells
            if end_cell > section.end_cell:
                issues.append(
                    f"function range {debug_object.object_name}:{function_range.symbol_name} "
                    f"exceeds section {symbol.section_name}"
                )
                continue
            function_records.append(
                DebugFunctionRecord(
                    symbol.name,
                    symbol.object_name,
                    symbol.section_name,
                    symbol.cell_address,
                    symbol.slot,
                    end_cell,
                    function_range.source_file,
                )
            )

    if issues:
        return tuple(issues), None

    image = DebugMetadataImage(
        line_records=tuple(line_records),
        symbol_records=symbol_records,
        function_records=tuple(function_records),
        register_records=emit_register_metadata(),
        unwind_hints=emit_protected_unwind_hints(),
    )
    return (), image


def emit_register_metadata() -> tuple[DebugRegisterRecord, ...]:
    return tuple(
        DebugRegisterRecord(
            view.name,
            view.register_class,
            view.index,
            view.readable,
            view.writable,
            view.tag_visible,
            view.slot_visible,
            _abi_roles_for_register(view),
        )
        for view in debug_abi.DEBUG_REGISTER_VIEWS
    )


def emit_protected_unwind_hints() -> tuple[ProtectedUnwindHint, ...]:
    return tuple(
        ProtectedUnwindHint(
            rule.operation,
            rule.updates_rsc_cursor,
            rule.writes_return_slot,
            rule.requires_valid_return_capability,
            rule.atomic_payload_tag,
            debug_abi.RETURN_STACK_ENTRY_CELLS,
            debug_abi.DEBUG_RETURN_REPLACEMENT_OTYPE,
        )
        for rule in debug_abi.DEBUG_UNWIND_RULES
    )


def _symbol_records(linked_image: linker.LinkedImage) -> tuple[DebugSymbolRecord, ...]:
    return tuple(
        DebugSymbolRecord(
            symbol.name,
            symbol.object_name,
            symbol.section_name,
            symbol.cell_address,
            symbol.slot,
            symbol.kind,
            symbol.binding,
        )
        for symbol in linked_image.symbols
    )


def _abi_roles_for_register(
    view: debug_abi.DebugRegisterView,
) -> tuple[RegisterAbiRole, ...]:
    roles: list[RegisterAbiRole] = []
    if view.register_class is debug_abi.DebugRegisterClass.INTEGER:
        index = view.index
        if index in abi.INTEGER_ARGUMENT_REGS:
            roles.append(RegisterAbiRole.INTEGER_ARGUMENT)
        if index in abi.INTEGER_RETURN_REGS:
            roles.append(RegisterAbiRole.INTEGER_RETURN)
        if index in abi.INTEGER_CALLER_SAVED_REGS:
            roles.append(RegisterAbiRole.INTEGER_CALLER_SAVED)
        if index in abi.INTEGER_CALLEE_SAVED_REGS:
            roles.append(RegisterAbiRole.INTEGER_CALLEE_SAVED)
        if index == abi.SYSCALL_SERVICE_REGISTER:
            roles.append(RegisterAbiRole.SYSCALL_SERVICE)
        if index in abi.SYSCALL_INTEGER_ARGUMENT_REGS:
            roles.append(RegisterAbiRole.SYSCALL_INTEGER_ARGUMENT)
        if index in abi.SYSCALL_INTEGER_RETURN_REGS:
            roles.append(RegisterAbiRole.SYSCALL_INTEGER_RETURN)
        if index in abi.CONTEXT_SWITCH_INTEGER_REGS:
            roles.append(RegisterAbiRole.CONTEXT_SWITCH)
    elif view.register_class is debug_abi.DebugRegisterClass.CAPABILITY:
        index = view.index
        if index in abi.CAPABILITY_ARGUMENT_REGS:
            roles.append(RegisterAbiRole.CAPABILITY_ARGUMENT)
        if index in abi.CAPABILITY_RETURN_REGS:
            roles.append(RegisterAbiRole.CAPABILITY_RETURN)
        if index in abi.CAPABILITY_CALLER_SAVED_REGS:
            roles.append(RegisterAbiRole.CAPABILITY_CALLER_SAVED)
        if index in abi.CAPABILITY_CALLEE_SAVED_REGS:
            roles.append(RegisterAbiRole.CAPABILITY_CALLEE_SAVED)
        if index in abi.SYSCALL_CAPABILITY_ARGUMENT_REGS:
            roles.append(RegisterAbiRole.SYSCALL_CAPABILITY_ARGUMENT)
        if index in abi.SYSCALL_CAPABILITY_RETURN_REGS:
            roles.append(RegisterAbiRole.SYSCALL_CAPABILITY_RETURN)
        if index in abi.CONTEXT_SWITCH_CAPABILITY_REGS:
            roles.append(RegisterAbiRole.CONTEXT_SWITCH)
    elif (
        view.register_class is debug_abi.DebugRegisterClass.SPECIAL_CAPABILITY
        and view.name in abi.CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS
    ):
        roles.append(RegisterAbiRole.CONTEXT_SWITCH)
    return tuple(dict.fromkeys(roles))


def _iter_decoded_instructions(
    section: linker.LinkedSection,
) -> tuple[tuple[int, int, assembly.EncodedInstruction], ...]:
    decoded: list[tuple[int, int, assembly.EncodedInstruction]] = []
    index = 0
    payload = section.payload_cells
    while index < len(payload):
        cell_address = section.base_cell + index
        if index + 1 < len(payload):
            long_value = payload[index] | (payload[index + 1] << cells.CELL_BITS)
            long_decoded = _try_decode(InstructionSize.BITS_48, long_value)
            if long_decoded is not None and long_decoded.size.is_legal_start(
                cell_address,
                state.SLOT_0,
            ):
                decoded.append((cell_address, state.SLOT_0, long_decoded))
                index += long_decoded.size.cells
                continue

        cell = payload[index]
        word_decoded = _try_decode(InstructionSize.BITS_24, cell)
        if word_decoded is not None:
            decoded.append((cell_address, state.SLOT_0, word_decoded))
            index += word_decoded.size.cells
            continue

        low = cell & 0xFFF
        high = (cell >> 12) & 0xFFF
        decoded.append((cell_address, state.SLOT_0, assembly.decode_value(InstructionSize.BITS_12, low)))
        if high:
            decoded.append((cell_address, state.SLOT_1, assembly.decode_value(InstructionSize.BITS_12, high)))
        index += 1
    return tuple(decoded)


def _try_decode(
    size: InstructionSize,
    value: int,
) -> assembly.EncodedInstruction | None:
    try:
        return assembly.decode_value(size, value)
    except assembly.DecodeError:
        return None

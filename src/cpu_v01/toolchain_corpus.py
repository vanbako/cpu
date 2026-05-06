"""Executable toolchain regression corpus for CPU v0.1 fixtures.

Owner stories:
- E01-S05: slot-aware instruction locations and labels.
- E04-S01/E04-S04/E04-S05: instruction packing, control flow, and capability memory.
- E05-S04: protected return-stack call/return behavior.
- E12-S01: debugger-visible locations and registers.
- E14-S02: cell-addressed object container spike.
- I17-S04: executable toolchain regression corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from . import (
    assembly,
    debug_metadata,
    golden_traces,
    linker,
    object_metadata as obj,
    platform,
    serialization,
    smoke,
    state,
)


JsonValue = Any


class ToolchainCorpusError(ValueError):
    """Raised when a requested toolchain corpus case is not valid."""


class ToolchainCorpusCategory(Enum):
    RESET_SMOKE = "reset_smoke"
    CALL_RETURN = "call_return"
    SYSCALL_TRAP = "syscall_trap"
    CAPABILITY_MEMORY = "capability_memory"
    RELOCATION = "relocation"
    DEBUG_METADATA = "debug_metadata"
    BAD_OBJECT = "bad_object"


REQUIRED_TOOLCHAIN_CORPUS_CATEGORIES = frozenset(
    category.value for category in ToolchainCorpusCategory
)


@dataclass(frozen=True)
class BinarySectionFixture:
    name: str
    source_lines: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("binary section name must not be empty")
        object.__setattr__(self, "source_lines", tuple(self.source_lines))
        if not self.source_lines:
            raise ValueError("binary section source_lines must not be empty")
        for source_line in self.source_lines:
            if not isinstance(source_line, str) or not source_line:
                raise ValueError("binary source lines must be nonempty strings")

    @property
    def payload_cells(self) -> tuple[int, ...]:
        return assembly.assemble_program(self.source_lines)

    @property
    def payload_octets(self) -> bytes:
        return serialization.serialize_cells(self.payload_cells)

    @property
    def disassembled_lines(self) -> tuple[str, ...]:
        return assembly.disassemble_program(self.payload_cells)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source_lines": list(self.source_lines),
            "payload_cells": list(self.payload_cells),
            "payload_octets_hex": self.payload_octets.hex(),
            "disassembled_lines": list(self.disassembled_lines),
        }


@dataclass(frozen=True)
class ToolchainCorpusCase:
    case_id: str
    category: ToolchainCorpusCategory
    description: str
    binary_sections: tuple[BinarySectionFixture, ...] = ()
    linker_objects: tuple[linker.LinkerObject, ...] = ()
    debug_objects: tuple[debug_metadata.DebugObject, ...] = ()
    base_cell: int = 0
    expected_linker_issues: tuple[str, ...] = ()
    golden_trace_case_id: str = ""

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must not be empty")
        object.__setattr__(self, "category", ToolchainCorpusCategory(self.category))
        if not self.description:
            raise ValueError("description must not be empty")
        object.__setattr__(self, "binary_sections", tuple(self.binary_sections))
        object.__setattr__(self, "linker_objects", tuple(self.linker_objects))
        object.__setattr__(self, "debug_objects", tuple(self.debug_objects))
        object.__setattr__(self, "expected_linker_issues", tuple(self.expected_linker_issues))
        for section in self.binary_sections:
            if not isinstance(section, BinarySectionFixture):
                raise TypeError("binary_sections must contain BinarySectionFixture values")
        for linker_object in self.linker_objects:
            if not isinstance(linker_object, linker.LinkerObject):
                raise TypeError("linker_objects must contain LinkerObject values")
        for debug_object in self.debug_objects:
            if not isinstance(debug_object, debug_metadata.DebugObject):
                raise TypeError("debug_objects must contain DebugObject values")

    def as_dict(self) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "case_id": self.case_id,
            "category": self.category.value,
            "description": self.description,
            "binary_sections": [section.as_dict() for section in self.binary_sections],
            "objects": [
                _linker_object_dict(linker_object)
                for linker_object in self.linker_objects
            ],
            "base_cell": self.base_cell,
            "expected_linker_issues": list(self.expected_linker_issues),
            "golden_trace_case_id": self.golden_trace_case_id,
        }
        if self.linker_objects:
            issues = linker.validate_linker_inputs(self.linker_objects, base_cell=self.base_cell)
            result["linker_issues"] = list(issues)
            if not self.expected_linker_issues and not issues:
                image = linker.link_objects(self.linker_objects, base_cell=self.base_cell)
                result["linked_image"] = image.as_dict()
                if self.debug_objects:
                    debug_image = debug_metadata.emit_debug_metadata(image, self.debug_objects)
                    result["debug_metadata"] = debug_image.as_dict()
        return result


def toolchain_corpus() -> tuple[ToolchainCorpusCase, ...]:
    """Return the deterministic I17-S04 toolchain regression corpus."""
    return (
        _reset_smoke_case(),
        _call_return_case(),
        _syscall_trap_case(),
        _capability_memory_case(),
        _relocation_case(),
        _debug_metadata_case(),
        _bad_object_case(),
    )


def toolchain_corpus_as_dicts() -> tuple[dict[str, JsonValue], ...]:
    return tuple(case.as_dict() for case in toolchain_corpus())


def toolchain_corpus_json(*, indent: int = 2) -> str:
    return json.dumps(toolchain_corpus_as_dicts(), indent=indent, sort_keys=True)


def toolchain_case_by_id(case_id: str) -> ToolchainCorpusCase:
    for case in toolchain_corpus():
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


def validate_toolchain_corpus(
    cases: tuple[ToolchainCorpusCase, ...] | None = None,
) -> tuple[str, ...]:
    if cases is None:
        cases = toolchain_corpus()
    cases = tuple(cases)
    issues: list[str] = []

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("toolchain corpus case IDs are not unique")

    categories = {case.category.value for case in cases}
    for category in sorted(REQUIRED_TOOLCHAIN_CORPUS_CATEGORIES - categories):
        issues.append(f"missing toolchain corpus category {category}")

    for case in cases:
        if not case.binary_sections and not case.linker_objects and not case.golden_trace_case_id:
            issues.append(f"{case.case_id}: no executable fixture evidence")
        _validate_binary_sections(case, issues)
        _validate_golden_trace_reference(case, issues)
        _validate_object_fixture(case, issues)

    try:
        json.dumps(tuple(case.as_dict() for case in cases), sort_keys=True)
    except (TypeError, ToolchainCorpusError) as exc:
        issues.append(f"toolchain corpus is not JSON serializable: {exc}")

    return tuple(issues)


def require_valid_toolchain_corpus(
    cases: tuple[ToolchainCorpusCase, ...] | None = None,
) -> tuple[ToolchainCorpusCase, ...]:
    if cases is None:
        cases = toolchain_corpus()
    cases = tuple(cases)
    issues = validate_toolchain_corpus(cases)
    if issues:
        raise ToolchainCorpusError("; ".join(issues))
    return cases


def _validate_binary_sections(case: ToolchainCorpusCase, issues: list[str]) -> None:
    for section in case.binary_sections:
        try:
            payload_cells = section.payload_cells
            roundtrip = serialization.deserialize_cells(section.payload_octets)
            disassembled = assembly.disassemble_program(payload_cells)
        except (
            assembly.AssemblyError,
            assembly.DecodeError,
            serialization.SerializationError,
        ) as exc:
            issues.append(f"{case.case_id}:{section.name}: binary fixture failed: {exc}")
            continue
        if roundtrip != payload_cells:
            issues.append(f"{case.case_id}:{section.name}: serialized cells do not round-trip")
        if disassembled != section.source_lines:
            issues.append(f"{case.case_id}:{section.name}: disassembly does not match source")


def _validate_golden_trace_reference(case: ToolchainCorpusCase, issues: list[str]) -> None:
    if not case.golden_trace_case_id:
        return
    try:
        golden_traces.golden_trace_case_by_id(case.golden_trace_case_id)
    except KeyError:
        issues.append(f"{case.case_id}: unknown golden trace case {case.golden_trace_case_id!r}")


def _validate_object_fixture(case: ToolchainCorpusCase, issues: list[str]) -> None:
    if not case.linker_objects:
        if case.debug_objects:
            issues.append(f"{case.case_id}: debug metadata has no linked object fixture")
        return

    linker_issues = linker.validate_linker_inputs(case.linker_objects, base_cell=case.base_cell)
    if case.expected_linker_issues:
        joined = "; ".join(linker_issues)
        for expected in case.expected_linker_issues:
            if expected not in joined:
                issues.append(f"{case.case_id}: missing expected linker issue {expected!r}")
        try:
            linker.link_objects(case.linker_objects, base_cell=case.base_cell)
        except linker.LinkerError:
            return
        issues.append(f"{case.case_id}: bad object fixture linked successfully")
        return

    if linker_issues:
        issues.append(f"{case.case_id}: unexpected linker issues: {'; '.join(linker_issues)}")
        return

    image = linker.link_objects(case.linker_objects, base_cell=case.base_cell)
    if case.debug_objects:
        debug_issues = debug_metadata.validate_debug_metadata(image, case.debug_objects)
        if debug_issues:
            issues.append(f"{case.case_id}: debug metadata issues: {'; '.join(debug_issues)}")
        else:
            debug_metadata.emit_debug_metadata(image, case.debug_objects)


def _reset_smoke_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "reset_smoke.reset_to_trap_image",
        ToolchainCorpusCategory.RESET_SMOKE,
        "Serialized reset-to-trap smoke image with main and handler sections.",
        binary_sections=(
            BinarySectionFixture("main", smoke.SMOKE_MAIN_SOURCE),
            BinarySectionFixture("trap_handler", smoke.SMOKE_HANDLER_SOURCE),
        ),
        base_cell=platform.RESET_VECTOR,
        golden_trace_case_id="reset_smoke.add_slot0",
    )


def _call_return_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "call_return.direct_call_ret_binary",
        ToolchainCorpusCategory.CALL_RETURN,
        "Direct CALL followed by a packed 12-bit RET fixture.",
        binary_sections=(BinarySectionFixture("text", ("CALL 0x104", "RET")),),
        golden_trace_case_id="calls_returns.direct_call_ret",
    )


def _syscall_trap_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "syscall_trap.sys_pause_iret_binary",
        ToolchainCorpusCategory.SYSCALL_TRAP,
        "Packed SYS/PAUSE trap site plus aligned IRET handler instruction.",
        binary_sections=(BinarySectionFixture("text", ("SYS", "PAUSE", "IRET")),),
        golden_trace_case_id="traps.sys_iret_return",
    )


def _capability_memory_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "capability_memory.csc_clc_st48_ld48_binary",
        ToolchainCorpusCategory.CAPABILITY_MEMORY,
        "Capability memory transfer and integer tag-clear binary fixture.",
        binary_sections=(
            BinarySectionFixture(
                "text",
                (
                    "CSC C1, D0, C2",
                    "CLC C3, C1, D0",
                    "ST48 C1, D0, D4",
                    "LD48 D5, C1, D0",
                ),
            ),
        ),
        golden_trace_case_id="memory_tag_ops.csc_clc_st48_ld48",
    )


def _relocation_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "relocation.branch_call_data_object",
        ToolchainCorpusCategory.RELOCATION,
        "Relocatable object patches branch, call, conditional branch, and data targets.",
        binary_sections=(
            BinarySectionFixture(
                "text",
                ("BRA 0x203", "Bcc EQ, 0x203", "CALL 0x203", "RET"),
            ),
        ),
        linker_objects=(_relocation_object(),),
        base_cell=0x0200,
    )


def _debug_metadata_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "debug_metadata.lines_symbols_registers",
        ToolchainCorpusCategory.DEBUG_METADATA,
        "Linked object with source lines, symbol ranges, ABI register metadata, and unwind hints.",
        binary_sections=(BinarySectionFixture("text", ("BRA 0x301", "RET", "BRK")),),
        linker_objects=(_debug_object_fixture(),),
        debug_objects=(_debug_object_records(),),
        base_cell=0x0300,
    )


def _bad_object_case() -> ToolchainCorpusCase:
    return ToolchainCorpusCase(
        "bad_object.missing_payload_and_abi",
        ToolchainCorpusCategory.BAD_OBJECT,
        "Rejected object fixture with incomplete ABI attributes and missing section payload.",
        linker_objects=(_bad_object_fixture(),),
        expected_linker_issues=(
            "object ABI attributes must include PURE_CAPABILITY",
            "missing payload for section bad:data",
        ),
    )


def _relocation_object() -> linker.LinkerObject:
    metadata = obj.RelocatableObjectMetadata(
        name="reloc",
        sections=(
            obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 4),
            obj.ObjectSection("data", obj.ObjectSectionKind.DATA, 2, 2),
        ),
        symbols=(
            obj.ObjectSymbol(
                "_start",
                "text",
                0,
                obj.ObjectSymbolKind.ENTRY,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "reloc_target",
                "text",
                3,
                obj.ObjectSymbolKind.FUNCTION,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "reloc_data",
                "data",
                0,
                obj.ObjectSymbolKind.OBJECT,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
        ),
        abi_attributes=_mandatory_abi_attributes(),
    )
    return linker.LinkerObject(
        metadata,
        section_payloads=(
            linker.SectionPayload(
                "text",
                (
                    assembly.assemble_line("BRA 0").cells[0],
                    assembly.assemble_line("Bcc EQ, 0").cells[0],
                    assembly.assemble_line("CALL 0").cells[0],
                    assembly.assemble_program(("RET",))[0],
                ),
            ),
            linker.SectionPayload("data", (0, 0)),
        ),
        relocations=(
            linker.Relocation("text", 0, linker.RelocationKind.DIRECT_TARGET16, "reloc_target"),
            linker.Relocation(
                "text",
                1,
                linker.RelocationKind.CONDITIONAL_TARGET12,
                "reloc_target",
            ),
            linker.Relocation("text", 2, linker.RelocationKind.DIRECT_TARGET16, "reloc_target"),
            linker.Relocation("data", 0, linker.RelocationKind.ABSOLUTE_CELL48, "reloc_target"),
        ),
    )


def _debug_object_fixture() -> linker.LinkerObject:
    metadata = obj.RelocatableObjectMetadata(
        name="dbgcorpus",
        sections=(obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 2),),
        symbols=(
            obj.ObjectSymbol(
                "_start",
                "text",
                0,
                obj.ObjectSymbolKind.ENTRY,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "after_branch",
                "text",
                1,
                obj.ObjectSymbolKind.FUNCTION,
                obj.ObjectSymbolBinding.GLOBAL,
            ),
            obj.ObjectSymbol(
                "break_slot",
                "text",
                1,
                obj.ObjectSymbolKind.FUNCTION,
                slot=state.SLOT_1,
            ),
        ),
        abi_attributes=(
            *_mandatory_abi_attributes(),
            obj.AbiAttribute.PROTECTED_RETURN_STACK,
        ),
    )
    return linker.LinkerObject(
        metadata,
        section_payloads=(
            linker.SectionPayload(
                "text",
                (
                    assembly.assemble_line("BRA 0").cells[0],
                    assembly.assemble_program(("RET", "BRK"))[0],
                ),
            ),
        ),
        relocations=(
            linker.Relocation(
                "text",
                0,
                linker.RelocationKind.DIRECT_TARGET16,
                "after_branch",
            ),
        ),
    )


def _debug_object_records() -> debug_metadata.DebugObject:
    return debug_metadata.DebugObject(
        "dbgcorpus",
        source_lines=(
            debug_metadata.SourceLine(
                "text",
                0,
                state.SLOT_0,
                "corpus/debug.cv01",
                1,
                source_text="BRA after_branch",
            ),
            debug_metadata.SourceLine(
                "text",
                1,
                state.SLOT_0,
                "corpus/debug.cv01",
                2,
                source_text="RET",
            ),
            debug_metadata.SourceLine(
                "text",
                1,
                state.SLOT_1,
                "corpus/debug.cv01",
                3,
                source_text="BRK",
            ),
        ),
        function_ranges=(
            debug_metadata.FunctionRange("_start", 2, "corpus/debug.cv01"),
            debug_metadata.FunctionRange("after_branch", 1, "corpus/debug.cv01"),
        ),
    )


def _bad_object_fixture() -> linker.LinkerObject:
    metadata = obj.RelocatableObjectMetadata(
        name="bad",
        sections=(
            obj.ObjectSection("text", obj.ObjectSectionKind.TEXT, 2, 1),
            obj.ObjectSection("data", obj.ObjectSectionKind.DATA, 2, 1),
        ),
        symbols=(obj.ObjectSymbol("_start", "text", 0, obj.ObjectSymbolKind.ENTRY),),
        abi_attributes=(obj.AbiAttribute.CELL_ADDRESSED, obj.AbiAttribute.SLOT_AWARE_PCC),
    )
    return linker.LinkerObject(
        metadata,
        section_payloads=(
            linker.SectionPayload("text", (assembly.assemble_program(("RET",))[0],)),
        ),
    )


def _mandatory_abi_attributes() -> tuple[obj.AbiAttribute, ...]:
    return (
        obj.AbiAttribute.CELL_ADDRESSED,
        obj.AbiAttribute.SLOT_AWARE_PCC,
        obj.AbiAttribute.PURE_CAPABILITY,
    )


def _linker_object_dict(linker_object: linker.LinkerObject) -> dict[str, JsonValue]:
    return {
        "metadata": linker_object.metadata.as_dict(),
        "section_payloads": [
            {
                "section_name": payload.section_name,
                "payload_cells": list(payload.payload_cells),
            }
            for payload in linker_object.section_payloads
        ],
        "relocations": [
            {
                "section_name": relocation.section_name,
                "cell_offset": relocation.cell_offset,
                "kind": relocation.kind.value,
                "symbol_name": relocation.symbol_name,
                "addend_cells": relocation.addend_cells,
            }
            for relocation in linker_object.relocations
        ],
    }

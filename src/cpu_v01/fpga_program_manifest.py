"""FPGA program-image manifest for loadable BRAM fixtures.

Owner stories:
- I26-S01: define the FPGA program-image manifest.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    cells,
    fpga_first_test,
    fpga_memory,
    linker,
    platform,
    smoke,
    toolchain_corpus,
)


JsonValue = Any

FPGA_PROGRAM_MANIFEST_STORY = "I26-S01"
FPGA_PROGRAM_MANIFEST_DOC = Path("docs/implementation/fpga-program-image-manifest.md")
FPGA_PROGRAM_MANIFEST_TOOL = "python tools\\fpga_program_manifest.py --check"
FPGA_PROGRAM_IMAGE_ROOT = Path("build/fpga/programs")
FPGA_PROGRAM_ROM_FORMAT = fpga_first_test.IMAGE_FORMAT_NAME
FPGA_PROGRAM_DATA_FORMAT = fpga_first_test.IMAGE_FORMAT_NAME
FPGA_PROGRAM_TAG_FORMAT = "hex1-tags-v1"
FPGA_PROGRAM_ROM_FILL_CELL = 0x05B05B
FPGA_PROGRAM_DATA_FILL_CELL = 0x000000
FPGA_PROGRAM_TAG_CLEAR = 0


@dataclass(frozen=True)
class FpgaProgramEntryCapability:
    source: str
    slot: int
    cursor_cell: int
    bounds_base_cell: int
    bounds_top_cell: int
    permissions: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "source": self.source,
            "slot": self.slot,
            "cursor_cell": self.cursor_cell,
            "bounds_base_cell": self.bounds_base_cell,
            "bounds_top_cell": self.bounds_top_cell,
            "permissions": list(self.permissions),
        }


@dataclass(frozen=True)
class FpgaProgramSectionBinding:
    source_case_id: str
    source_section: str
    source_kind: str
    target_memory: str
    base_cell: int
    payload_cells: tuple[int, ...]
    section_kind: str
    tag_policy: str

    def __post_init__(self) -> None:
        if not self.source_case_id:
            raise ValueError("source_case_id must not be empty")
        if not self.source_section:
            raise ValueError("source_section must not be empty")
        if not self.source_kind:
            raise ValueError("source_kind must not be empty")
        if not self.target_memory:
            raise ValueError("target_memory must not be empty")
        object.__setattr__(self, "base_cell", cells.require_cell_address(self.base_cell))
        object.__setattr__(
            self,
            "payload_cells",
            tuple(cells.require_cell_value(value) for value in self.payload_cells),
        )
        if not self.payload_cells:
            raise ValueError("payload_cells must not be empty")
        if not self.section_kind:
            raise ValueError("section_kind must not be empty")
        if not self.tag_policy:
            raise ValueError("tag_policy must not be empty")

    @property
    def end_cell(self) -> int:
        return self.base_cell + len(self.payload_cells)

    @property
    def cell_count(self) -> int:
        return len(self.payload_cells)

    @property
    def payload_sha256(self) -> str:
        return _sha256(_hex24_lines(self.payload_cells))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "source_case_id": self.source_case_id,
            "source_section": self.source_section,
            "source_kind": self.source_kind,
            "target_memory": self.target_memory,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "cell_count": self.cell_count,
            "section_kind": self.section_kind,
            "tag_policy": self.tag_policy,
            "payload_sha256": self.payload_sha256,
        }


@dataclass(frozen=True)
class FpgaProgramMemoryImage:
    memory_name: str
    artifact_path: Path
    format_name: str
    depth_cells: int
    fill_value: int
    source_sections: tuple[str, ...]
    image_sha256: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "memory_name": self.memory_name,
            "artifact_path": self.artifact_path.as_posix(),
            "format_name": self.format_name,
            "depth_cells": self.depth_cells,
            "fill_value": self.fill_value,
            "source_sections": list(self.source_sections),
            "image_sha256": self.image_sha256,
        }


@dataclass(frozen=True)
class FpgaProgramExpectedObservation:
    signal: str
    expected: str
    evidence: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "signal": self.signal,
            "expected": self.expected,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class FpgaProgramManifestEntry:
    program_id: str
    source_case_id: str
    description: str
    board_run_class: str
    entry_capability: FpgaProgramEntryCapability
    sections: tuple[FpgaProgramSectionBinding, ...]
    expected_observations: tuple[FpgaProgramExpectedObservation, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.program_id:
            raise ValueError("program_id must not be empty")
        if not self.source_case_id:
            raise ValueError("source_case_id must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")
        if not self.board_run_class:
            raise ValueError("board_run_class must not be empty")
        if not isinstance(self.entry_capability, FpgaProgramEntryCapability):
            raise TypeError("entry_capability must be a FpgaProgramEntryCapability")
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "expected_observations", tuple(self.expected_observations))
        object.__setattr__(self, "notes", tuple(self.notes))
        if not self.sections:
            raise ValueError("manifest entry must contain at least one section")
        if not self.expected_observations:
            raise ValueError("manifest entry must contain expected observations")
        for section in self.sections:
            if not isinstance(section, FpgaProgramSectionBinding):
                raise TypeError("sections must contain FpgaProgramSectionBinding values")
        for observation in self.expected_observations:
            if not isinstance(observation, FpgaProgramExpectedObservation):
                raise TypeError("expected_observations must contain FpgaProgramExpectedObservation values")

    @property
    def entry_cell(self) -> int:
        return self.entry_capability.cursor_cell

    @property
    def image_sha256(self) -> str:
        payload = {
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "entry_capability": self.entry_capability.as_dict(),
            "memory_images": [image.as_dict() for image in self.memory_images()],
        }
        return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    def memory_images(self) -> tuple[FpgaProgramMemoryImage, ...]:
        return tuple(_memory_image_for_entry(self, memory) for memory in _manifest_memories())

    def materialized_cells(self, memory_name: str) -> tuple[int, ...]:
        memory = _memory_by_name(memory_name)
        if memory.name == "tag_ram":
            return tuple(FPGA_PROGRAM_TAG_CLEAR for _ in range(memory.size_cells))
        fill = _memory_fill_value(memory.name)
        values = [fill for _ in range(memory.size_cells)]
        for section in self.sections:
            if section.target_memory != memory.name:
                continue
            offset = section.base_cell - memory.base_cell
            values[offset : offset + section.cell_count] = section.payload_cells
        return tuple(values)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "description": self.description,
            "board_run_class": self.board_run_class,
            "entry_cell": self.entry_cell,
            "entry_capability": self.entry_capability.as_dict(),
            "sections": [section.as_dict() for section in self.sections],
            "memory_images": [image.as_dict() for image in self.memory_images()],
            "image_sha256": self.image_sha256,
            "expected_observations": [
                observation.as_dict() for observation in self.expected_observations
            ],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FpgaProgramManifestProfile:
    story: str
    board: str
    fpga_top_module: str
    source_corpus_tool: str
    memory_adapter_tool: str
    image_root: Path
    rom_format: str
    data_format: str
    tag_format: str
    entries: tuple[FpgaProgramManifestEntry, ...]

    def entry_by_id(self, program_id: str) -> FpgaProgramManifestEntry:
        for entry in self.entries:
            if entry.program_id == program_id:
                return entry
        raise KeyError(program_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "fpga_top_module": self.fpga_top_module,
            "source_corpus_tool": self.source_corpus_tool,
            "memory_adapter_tool": self.memory_adapter_tool,
            "image_root": self.image_root.as_posix(),
            "rom_format": self.rom_format,
            "data_format": self.data_format,
            "tag_format": self.tag_format,
            "entries": [entry.as_dict() for entry in self.entries],
        }


def fpga_program_manifest_profile() -> FpgaProgramManifestProfile:
    return FpgaProgramManifestProfile(
        story=FPGA_PROGRAM_MANIFEST_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        fpga_top_module=fpga_first_test.FPGA_TOP_MODULE,
        source_corpus_tool="python tools\\toolchain_corpus.py --check",
        memory_adapter_tool="python tools\\fpga_memory_adapters.py --check",
        image_root=FPGA_PROGRAM_IMAGE_ROOT,
        rom_format=FPGA_PROGRAM_ROM_FORMAT,
        data_format=FPGA_PROGRAM_DATA_FORMAT,
        tag_format=FPGA_PROGRAM_TAG_FORMAT,
        entries=(
            _reset_smoke_entry(),
            _call_return_entry(),
            _capability_memory_entry(),
            _syscall_trap_entry(),
            _relocation_entry(),
        ),
    )


def fpga_program_manifest_entries() -> tuple[FpgaProgramManifestEntry, ...]:
    return fpga_program_manifest_profile().entries


def fpga_program_manifest_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_program_manifest_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_program_manifest(profile: FpgaProgramManifestProfile | None = None) -> str:
    if profile is None:
        profile = fpga_program_manifest_profile()
    lines = [
        "# FPGA Program-Image Manifest",
        "",
        f"Story: `{profile.story}`",
        f"Board: `{profile.board}`",
        f"FPGA top: `{profile.fpga_top_module}`",
        f"Image root: `{profile.image_root.as_posix()}`",
        "",
        "## Entries",
        "",
    ]
    for entry in profile.entries:
        lines.extend(
            (
                f"### `{entry.program_id}`",
                "",
                f"- Source case: `{entry.source_case_id}`.",
                f"- Board run class: `{entry.board_run_class}`.",
                f"- Entry cell: `0x{entry.entry_cell:08X}`.",
                f"- Image hash: `{entry.image_sha256}`.",
                "- Memories: "
                + ", ".join(
                    f"`{image.memory_name}` -> `{image.artifact_path.as_posix()}`"
                    for image in entry.memory_images()
                )
                + ".",
                "",
            )
        )
    return "\n".join(lines)


def validate_fpga_program_manifest(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []
    profile = fpga_program_manifest_profile()

    if profile.story != FPGA_PROGRAM_MANIFEST_STORY:
        issues.append("FPGA program manifest story mismatch")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("FPGA program manifest target board mismatch")
    if profile.fpga_top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("FPGA program manifest top-module mismatch")
    if profile.rom_format != fpga_first_test.IMAGE_FORMAT_NAME:
        issues.append("ROM image format must reuse the I23-S01 hex24-cells-v1 format")
    if profile.data_format != fpga_first_test.IMAGE_FORMAT_NAME:
        issues.append("data image format must reuse the I23-S01 hex24-cells-v1 format")

    issues.extend(toolchain_corpus.validate_toolchain_corpus())
    issues.extend(fpga_memory.validate_fpga_memory_adapters(root))

    entry_ids = [entry.program_id for entry in profile.entries]
    if len(entry_ids) != len(set(entry_ids)):
        issues.append("FPGA program manifest entry IDs are not unique")
    if len(profile.entries) < 3:
        issues.append("FPGA program manifest must publish at least three starter entries")

    for entry in profile.entries:
        _validate_entry(entry, issues)

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA program manifest is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_PROGRAM_MANIFEST_DOC)
    for token in (
        "Story: I26-S01",
        FPGA_PROGRAM_MANIFEST_TOOL,
        "python tools\\toolchain_corpus.py --check",
        "python tools\\fpga_memory_adapters.py --check",
        "build/fpga/programs",
        "hex24-cells-v1",
        "hex1-tags-v1",
        "instruction_rom",
        "data_ram",
        "tag_ram",
        "entry capability",
        "image_sha256",
        "reset_smoke.reset_to_trap_fpga",
        "syscall_trap.sys_pause_iret_fpga",
        "relocation.branch_call_data_fpga",
        "I26-S02",
        "I26-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_PROGRAM_MANIFEST_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _validate_entry(entry: FpgaProgramManifestEntry, issues: list[str]) -> None:
    try:
        toolchain_corpus.toolchain_case_by_id(entry.source_case_id)
    except KeyError:
        issues.append(f"{entry.program_id}: unknown toolchain source case {entry.source_case_id!r}")

    if entry.entry_capability.source != "RESET_PCC":
        issues.append(f"{entry.program_id}: entry capability must use RESET_PCC")
    if entry.entry_capability.slot != 0:
        issues.append(f"{entry.program_id}: entry capability must enter slot 0")
    if entry.entry_cell != platform.RESET_VECTOR:
        issues.append(f"{entry.program_id}: entry cell must equal platform reset vector")
    if "EX" not in entry.entry_capability.permissions:
        issues.append(f"{entry.program_id}: entry capability must be executable")

    target_memories = {section.target_memory for section in entry.sections}
    if "instruction_rom" not in target_memories:
        issues.append(f"{entry.program_id}: no instruction_rom section")
    for memory_name in ("instruction_rom", "data_ram", "tag_ram"):
        try:
            entry.materialized_cells(memory_name)
        except (KeyError, ValueError) as exc:
            issues.append(f"{entry.program_id}: cannot materialize {memory_name}: {exc}")

    for section in entry.sections:
        try:
            memory = _memory_by_name(section.target_memory)
        except KeyError:
            issues.append(f"{entry.program_id}:{section.source_section}: unknown memory {section.target_memory!r}")
            continue
        if section.base_cell < memory.base_cell or section.end_cell > memory.end_cell:
            issues.append(
                f"{entry.program_id}:{section.source_section}: section does not fit in {memory.name}"
            )
        if section.target_memory == "instruction_rom" and section.section_kind != "TEXT":
            issues.append(f"{entry.program_id}:{section.source_section}: ROM section must be TEXT")
        if section.target_memory == "data_ram" and section.section_kind not in ("DATA", "RODATA"):
            issues.append(f"{entry.program_id}:{section.source_section}: data RAM section kind mismatch")
        if section.target_memory == "tag_ram":
            issues.append(f"{entry.program_id}:{section.source_section}: tag RAM is generated from tag policy")

    for left_index, left in enumerate(entry.sections):
        for right in entry.sections[left_index + 1 :]:
            if left.target_memory != right.target_memory:
                continue
            if left.base_cell < right.end_cell and right.base_cell < left.end_cell:
                issues.append(
                    f"{entry.program_id}: sections {left.source_section!r} and {right.source_section!r} overlap"
                )

    images = {image.memory_name: image for image in entry.memory_images()}
    if set(images) != {"instruction_rom", "data_ram", "tag_ram"}:
        issues.append(f"{entry.program_id}: memory image set must include ROM, data, and tag RAM")
    for image in images.values():
        if len(image.image_sha256) != 64:
            issues.append(f"{entry.program_id}: {image.memory_name} hash is not SHA-256")
        if not image.artifact_path.as_posix().startswith(FPGA_PROGRAM_IMAGE_ROOT.as_posix()):
            issues.append(f"{entry.program_id}: {image.memory_name} artifact is outside image root")
    if len(entry.image_sha256) != 64:
        issues.append(f"{entry.program_id}: combined image hash is not SHA-256")


def _reset_smoke_entry() -> FpgaProgramManifestEntry:
    case_id = "reset_smoke.reset_to_trap_image"
    sections = _binary_sections_by_name(case_id)
    return FpgaProgramManifestEntry(
        program_id="reset_smoke.reset_to_trap_fpga",
        source_case_id=case_id,
        description="Reset-to-trap smoke fixture placed into FPGA instruction ROM.",
        board_run_class="debug_status_expected_trap_then_pause",
        entry_capability=_entry_capability(),
        sections=(
            _section_from_binary(case_id, sections["main"], "instruction_rom", platform.RESET_VECTOR),
            _section_from_binary(case_id, sections["trap_handler"], "instruction_rom", smoke.SMOKE_HANDLER_CELL),
        ),
        expected_observations=(
            FpgaProgramExpectedObservation(
                "status_retire_count_o",
                "advances through the main path and trap handler",
                "UART status packet or GAO/ILA retire capture",
            ),
            FpgaProgramExpectedObservation(
                "status_fault_code_o",
                "reports syscall trap before IRET returns to PAUSE",
                "I25-S05 debug evidence when used on board",
            ),
        ),
        notes=(
            "Uses existing simulator reset capability semantics; no FPGA-only entry format.",
            "I26-S05 must wrap this fixture with a board pass/fail policy before claiming a pass.",
        ),
    )


def _syscall_trap_entry() -> FpgaProgramManifestEntry:
    case_id = "syscall_trap.sys_pause_iret_binary"
    section = _binary_sections_by_name(case_id)["text"]
    return FpgaProgramManifestEntry(
        program_id="syscall_trap.sys_pause_iret_fpga",
        source_case_id=case_id,
        description="Compact SYS/PAUSE/IRET binary fixture for FPGA trap-path observation.",
        board_run_class="debug_status_expected_trap",
        entry_capability=_entry_capability(),
        sections=(
            _section_from_binary(case_id, section, "instruction_rom", platform.RESET_VECTOR),
        ),
        expected_observations=(
            FpgaProgramExpectedObservation(
                "fail_led_o",
                "may assert until I26-S05 supplies a trap-aware pass harness",
                "LED plus UART/probe capture",
            ),
            FpgaProgramExpectedObservation(
                "status_fault_code_o",
                "captures the syscall trap cause",
                "I25-S01 status packet decoded by I25-S02",
            ),
        ),
        notes=(
            "The entry is intentionally not a first-board pass program yet.",
            "It exists so I26-S02 has a deterministic trap image to generate.",
        ),
    )


def _call_return_entry() -> FpgaProgramManifestEntry:
    case_id = "call_return.direct_call_ret_binary"
    section = _binary_sections_by_name(case_id)["text"]
    return FpgaProgramManifestEntry(
        program_id="call_return.direct_call_ret_fpga",
        source_case_id=case_id,
        description="Direct CALL/RET control-flow binary fixture for FPGA smoke corpus use.",
        board_run_class="control_flow_harness_required",
        entry_capability=_entry_capability(),
        sections=(
            _section_from_binary(case_id, section, "instruction_rom", platform.RESET_VECTOR),
        ),
        expected_observations=(
            FpgaProgramExpectedObservation(
                "status_retire_count_o",
                "shows CALL/RET progress when wrapped by a pass/fail harness",
                "UART status packet or GAO/ILA retire capture",
            ),
            FpgaProgramExpectedObservation(
                "status_fault_code_o",
                "stays zero for the bounded control-flow harness",
                "I26-S05 corpus observation record",
            ),
        ),
        notes=(
            "The raw fixture is a corpus image, not a standalone board pass program.",
            "I26-S05 owns the expected control-flow observation signature.",
        ),
    )


def _capability_memory_entry() -> FpgaProgramManifestEntry:
    case_id = "capability_memory.csc_clc_st48_ld48_binary"
    section = _binary_sections_by_name(case_id)["text"]
    return FpgaProgramManifestEntry(
        program_id="capability_memory.csc_clc_st48_ld48_fpga",
        source_case_id=case_id,
        description="Capability memory transfer and integer tag-clear binary fixture.",
        board_run_class="capability_register_setup_required",
        entry_capability=_entry_capability(),
        sections=(
            _section_from_binary(case_id, section, "instruction_rom", platform.RESET_VECTOR),
        ),
        expected_observations=(
            FpgaProgramExpectedObservation(
                "status_fault_code_o",
                "stays zero only when the harness installs the expected capability registers",
                "UART status packet or GAO/ILA fault capture",
            ),
            FpgaProgramExpectedObservation(
                "tag_ram",
                "starts clear and later shows CSC/tag-clear effects through probes or replay",
                "I26-S05 corpus observation record",
            ),
        ),
        notes=(
            "The generated tag image remains clear; runtime CSC is responsible for valid tag creation.",
            "The harness must install source capabilities before this becomes a board pass program.",
        ),
    )


def _relocation_entry() -> FpgaProgramManifestEntry:
    case_id = "relocation.branch_call_data_object"
    case = toolchain_corpus.toolchain_case_by_id(case_id)
    image = linker.link_objects(case.linker_objects, base_cell=case.base_cell)
    text = image.section_by_name("reloc", "text")
    data = image.section_by_name("reloc", "data")
    return FpgaProgramManifestEntry(
        program_id="relocation.branch_call_data_fpga",
        source_case_id=case_id,
        description="Linked relocation fixture with text in ROM and relocated data in data RAM.",
        board_run_class="linker_image_identity_check",
        entry_capability=_entry_capability(),
        sections=(
            _section_from_linked(case_id, text, "instruction_rom", platform.RESET_VECTOR, "TEXT"),
            _section_from_linked(case_id, data, "data_ram", platform.RAM_BASE, "DATA"),
        ),
        expected_observations=(
            FpgaProgramExpectedObservation(
                "image_sha256",
                "matches the manifest before Gowin rebuild or memory update",
                "I26-S03 build or memory-update report",
            ),
            FpgaProgramExpectedObservation(
                "board_run_class",
                "remains linker_image_identity_check until an I26-S05 harness supplies executable placement",
                "manifest review before board run selection",
            ),
        ),
        notes=(
            "The linked payload is produced at the I17-S04 corpus base because the conditional branch fixture overflows if relinked at the FPGA reset vector.",
            "Data RAM placement uses the linked data payload but the FPGA memory map owns final placement.",
            "Tag RAM remains all clear because the fixture does not request trusted capability sidecars.",
        ),
    )


def _entry_capability() -> FpgaProgramEntryCapability:
    rom = _memory_by_name("instruction_rom")
    return FpgaProgramEntryCapability(
        source="RESET_PCC",
        slot=0,
        cursor_cell=platform.RESET_VECTOR,
        bounds_base_cell=rom.base_cell,
        bounds_top_cell=rom.end_cell,
        permissions=("EX",),
    )


def _section_from_binary(
    case_id: str,
    section: toolchain_corpus.BinarySectionFixture,
    target_memory: str,
    base_cell: int,
) -> FpgaProgramSectionBinding:
    return FpgaProgramSectionBinding(
        source_case_id=case_id,
        source_section=section.name,
        source_kind="toolchain_binary_section",
        target_memory=target_memory,
        base_cell=base_cell,
        payload_cells=section.payload_cells,
        section_kind="TEXT",
        tag_policy="no_tags",
    )


def _section_from_linked(
    case_id: str,
    section: linker.LinkedSection,
    target_memory: str,
    base_cell: int,
    section_kind: str,
) -> FpgaProgramSectionBinding:
    return FpgaProgramSectionBinding(
        source_case_id=case_id,
        source_section=section.qualified_name,
        source_kind="linked_section",
        target_memory=target_memory,
        base_cell=base_cell,
        payload_cells=section.payload_cells,
        section_kind=section_kind,
        tag_policy="untyped_cells",
    )


def _binary_sections_by_name(
    case_id: str,
) -> dict[str, toolchain_corpus.BinarySectionFixture]:
    case = toolchain_corpus.toolchain_case_by_id(case_id)
    return {section.name: section for section in case.binary_sections}


def _memory_image_for_entry(
    entry: FpgaProgramManifestEntry,
    memory: fpga_first_test.FpgaMemoryRegion,
) -> FpgaProgramMemoryImage:
    materialized = entry.materialized_cells(memory.name)
    if memory.name == "tag_ram":
        format_name = FPGA_PROGRAM_TAG_FORMAT
        image_hash = _sha256(_hex1_lines(materialized))
    else:
        format_name = FPGA_PROGRAM_ROM_FORMAT if memory.name == "instruction_rom" else FPGA_PROGRAM_DATA_FORMAT
        image_hash = _sha256(_hex24_lines(materialized))
    section_names = tuple(
        section.source_section for section in entry.sections if section.target_memory == memory.name
    )
    return FpgaProgramMemoryImage(
        memory_name=memory.name,
        artifact_path=_artifact_path(entry.program_id, memory.name),
        format_name=format_name,
        depth_cells=memory.size_cells,
        fill_value=_memory_fill_value(memory.name),
        source_sections=section_names,
        image_sha256=image_hash,
    )


def _artifact_path(program_id: str, memory_name: str) -> Path:
    basename = {
        "instruction_rom": "rom.mem",
        "data_ram": "data.mem",
        "tag_ram": "tags.mem",
    }[memory_name]
    return FPGA_PROGRAM_IMAGE_ROOT / program_id.replace(".", "_") / basename


def _memory_fill_value(memory_name: str) -> int:
    if memory_name == "instruction_rom":
        return FPGA_PROGRAM_ROM_FILL_CELL
    if memory_name == "data_ram":
        return FPGA_PROGRAM_DATA_FILL_CELL
    if memory_name == "tag_ram":
        return FPGA_PROGRAM_TAG_CLEAR
    raise KeyError(memory_name)


def _memory_by_name(memory_name: str) -> fpga_first_test.FpgaMemoryRegion:
    return fpga_first_test.FPGA_FIRST_TEST_PROFILE.memory_by_name(memory_name)


def _manifest_memories() -> tuple[fpga_first_test.FpgaMemoryRegion, ...]:
    return (
        _memory_by_name("instruction_rom"),
        _memory_by_name("data_ram"),
        _memory_by_name("tag_ram"),
    )


def _hex24_lines(values: tuple[int, ...]) -> str:
    return "".join(f"{value:06x}\n" for value in values)


def _hex1_lines(values: tuple[int, ...]) -> str:
    return "".join(f"{value & 1:x}\n" for value in values)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

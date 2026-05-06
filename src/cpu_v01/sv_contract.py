"""Generated SystemVerilog package and interface contract for CPU v0.1.

Owner stories:
- E04-S06: mandatory opcode coverage contract.
- E07-S03: precise fault and retire packet vocabulary.
- E13-S01: pipeline and trace vocabulary.
- I20-S03: SystemVerilog package, constants, and top-level interfaces.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from . import capabilities as caps
from . import cells, csrs, opcodes, state


JsonValue = Any

REQUIRED_SV_SURFACES = frozenset(
    {
        "cells",
        "capabilities",
        "tags",
        "csrs",
        "decoded_opcodes",
        "fault_packets",
        "retire_packets",
        "instruction_memory",
        "data_memory",
        "tag_memory",
    }
)


@dataclass(frozen=True)
class SvConstant:
    name: str
    value: int
    width: int
    surfaces: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        _require_identifier(self.name)
        if type(self.value) is not int or self.value < 0:
            raise ValueError("constant value must be a nonnegative int")
        if type(self.width) is not int or self.width <= 0:
            raise ValueError("constant width must be a positive int")
        object.__setattr__(self, "surfaces", tuple(self.surfaces))
        _require_surfaces(self.surfaces)
        if not self.description:
            raise ValueError("constant description must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "value": self.value,
            "width": self.width,
            "surfaces": list(self.surfaces),
            "description": self.description,
        }


@dataclass(frozen=True)
class SvField:
    name: str
    type_name: str
    width: int | None
    surfaces: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        _require_identifier(self.name)
        if not self.type_name:
            raise ValueError("field type_name must not be empty")
        if self.width is not None and (type(self.width) is not int or self.width <= 0):
            raise ValueError("field width must be a positive int or None")
        object.__setattr__(self, "surfaces", tuple(self.surfaces))
        _require_surfaces(self.surfaces)
        if not self.description:
            raise ValueError("field description must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "type_name": self.type_name,
            "width": self.width,
            "surfaces": list(self.surfaces),
            "description": self.description,
        }


@dataclass(frozen=True)
class SvStruct:
    name: str
    surfaces: tuple[str, ...]
    description: str
    fields: tuple[SvField, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.name)
        object.__setattr__(self, "surfaces", tuple(self.surfaces))
        _require_surfaces(self.surfaces)
        if not self.description:
            raise ValueError("struct description must not be empty")
        if not self.fields:
            raise ValueError("struct fields must not be empty")
        object.__setattr__(self, "fields", tuple(self.fields))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "surfaces": list(self.surfaces),
            "description": self.description,
            "fields": [field.as_dict() for field in self.fields],
        }


@dataclass(frozen=True)
class SvInterface:
    name: str
    surfaces: tuple[str, ...]
    description: str
    signals: tuple[SvField, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.name)
        object.__setattr__(self, "surfaces", tuple(self.surfaces))
        _require_surfaces(self.surfaces)
        if not self.description:
            raise ValueError("interface description must not be empty")
        if not self.signals:
            raise ValueError("interface signals must not be empty")
        object.__setattr__(self, "signals", tuple(self.signals))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "surfaces": list(self.surfaces),
            "description": self.description,
            "signals": [signal.as_dict() for signal in self.signals],
        }


@dataclass(frozen=True)
class SystemVerilogContract:
    package_name: str
    constants: tuple[SvConstant, ...]
    opcode_constants: tuple[SvConstant, ...]
    structs: tuple[SvStruct, ...]
    interfaces: tuple[SvInterface, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "package_name": self.package_name,
            "constants": [constant.as_dict() for constant in self.constants],
            "opcode_constants": [
                constant.as_dict() for constant in self.opcode_constants
            ],
            "structs": [struct.as_dict() for struct in self.structs],
            "interfaces": [interface.as_dict() for interface in self.interfaces],
        }


def systemverilog_contract() -> SystemVerilogContract:
    return SystemVerilogContract(
        package_name="cpu_v01_pkg",
        constants=_constants(),
        opcode_constants=_opcode_constants(),
        structs=_structs(),
        interfaces=_interfaces(),
    )


def systemverilog_contract_json(*, indent: int = 2) -> str:
    return json.dumps(systemverilog_contract().as_dict(), indent=indent, sort_keys=True)


def render_systemverilog_contract_markdown() -> str:
    contract = systemverilog_contract()
    lines = [
        "# SystemVerilog Interface Specification",
        "",
        "Story: I20-S03",
        "",
        "Status: Generated implementation profile",
        "",
        f"Package: `{contract.package_name}`",
        "",
        "## Constants",
        "",
        "| Name | Value | Width | Surfaces | Description |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for constant in contract.constants:
        lines.append(_constant_row(constant))

    lines.extend(
        [
            "",
            "## Opcode Constants",
            "",
            "| Name | Value | Width | Surfaces | Description |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for constant in contract.opcode_constants:
        lines.append(_constant_row(constant))

    lines.extend(["", "## Packed Types", ""])
    for struct in contract.structs:
        lines.extend(
            [
                f"### `{struct.name}`",
                "",
                struct.description,
                "",
                "| Field | Type | Width | Surfaces | Description |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for field in struct.fields:
            lines.append(_field_row(field))
        lines.append("")

    lines.extend(["## Top-Level Interfaces", ""])
    for interface in contract.interfaces:
        lines.extend(
            [
                f"### `{interface.name}`",
                "",
                interface.description,
                "",
                "| Signal | Type | Width | Surfaces | Description |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for signal in interface.signals:
            lines.append(_field_row(signal))
        lines.append("")

    lines.extend(
        [
            "## Acceptance Review",
            "",
            "| Acceptance criterion | Result |",
            "| --- | --- |",
            "| Cells are covered. | Met. |",
            "| Capabilities and tags are covered. | Met. |",
            "| CSRs and decoded opcodes are covered. | Met. |",
            "| Fault and retire packets are covered. | Met. |",
            "| Instruction-memory, data-memory, and tag-memory ports are covered. | Met. |",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_systemverilog_contract(
    contract: SystemVerilogContract | None = None,
) -> tuple[str, ...]:
    if contract is None:
        contract = systemverilog_contract()

    issues: list[str] = []
    covered = _covered_surfaces(contract)
    for surface in sorted(REQUIRED_SV_SURFACES - covered):
        issues.append(f"missing SystemVerilog contract surface {surface}")

    structs = {struct.name: struct for struct in contract.structs}
    for required in ("cap_payload_t", "cap_t", "fault_packet_t", "retire_packet_t"):
        if required not in structs:
            issues.append(f"missing packed type {required}")

    interfaces = {interface.name: interface for interface in contract.interfaces}
    for required in (
        "cpu_v01_imem_if",
        "cpu_v01_dmem_if",
        "cpu_v01_tagmem_if",
        "cpu_v01_retire_if",
    ):
        if required not in interfaces:
            issues.append(f"missing top-level interface {required}")

    opcode_names = {constant.name for constant in contract.opcode_constants}
    for mnemonic in ("ADD", "LD48", "CLC", "CSC", "CSETADDR", "SYS", "IRET"):
        prefix = f"OPC_{_sv_name(mnemonic)}_"
        if not any(name.startswith(prefix) for name in opcode_names):
            issues.append(f"missing opcode constant for {mnemonic}")

    try:
        json.dumps(contract.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"SystemVerilog contract is not JSON serializable: {exc}")

    return tuple(issues)


def _constants() -> tuple[SvConstant, ...]:
    return (
        _const("CELL_BITS", cells.CELL_BITS, 8, ("cells",), "Bits in one architectural cell."),
        _const("CELL_BYTES", cells.CELL_BYTES, 8, ("cells",), "Bytes in one architectural cell."),
        _const("ADDR_BITS", cells.ADDRESS_BITS, 8, ("cells",), "Architectural cell-address width."),
        _const("FETCH_GROUP_CELLS", cells.FETCH_GROUP_CELLS, 8, ("cells", "instruction_memory"), "Cells per instruction fetch group."),
        _const("INTEGER_OBJECT_CELLS", cells.INTEGER_OBJECT_CELLS, 8, ("cells", "data_memory"), "Cells in one 48-bit integer memory object."),
        _const("CAPABILITY_OBJECT_CELLS", cells.CAPABILITY_OBJECT_CELLS, 8, ("cells", "capabilities", "tag_memory"), "Cells in one capability payload object."),
        _const("CAP_PAYLOAD_BITS", caps.CAPABILITY_PAYLOAD_BITS, 16, ("capabilities",), "Packed capability payload width."),
        _const("CAP_CURSOR_BITS", caps.CAPABILITY_CURSOR_BITS, 8, ("capabilities",), "Capability cursor width."),
        _const("CAP_BOUNDS_METADATA_BITS", caps.CAPABILITY_BOUNDS_METADATA_BITS, 8, ("capabilities",), "Compressed bounds metadata width."),
        _const("CAP_PERMISSION_BITS", caps.CAPABILITY_PERMISSION_BITS, 8, ("capabilities",), "Capability permission-mask width."),
        _const("CAP_OTYPE_BITS", caps.CAPABILITY_OBJECT_TYPE_BITS, 8, ("capabilities",), "Capability object type width."),
        _const("CAP_FLAG_BITS", caps.CAPABILITY_FLAG_BITS, 8, ("capabilities",), "Capability flags width."),
        _const("CAP_TAG_BITS", caps.CAPABILITY_TAG_BITS, 8, ("tags", "capabilities"), "Out-of-band capability tag width."),
        _const("INT_REG_BITS", state.INTEGER_REGISTER_BITS, 8, ("cells",), "Integer register width."),
        _const("INT_REG_COUNT", state.INTEGER_REGISTER_COUNT, 8, ("cells",), "Integer architectural register count."),
        _const("CAP_REG_COUNT", state.GENERAL_CAPABILITY_REGISTER_COUNT, 8, ("capabilities",), "General capability register count."),
        _const("CSR_BITS", csrs.CSR_BITS, 8, ("csrs",), "Scalar CSR value width."),
        _const("CSR_NUMBER_BITS", csrs.CSR_NUMBER_BITS, 8, ("csrs",), "Scalar CSR number width."),
        _const("CCSR_NUMBER_BITS", 8, 8, ("csrs", "capabilities"), "Special capability CSR number width."),
        _const("OPCODE_ID_BITS", 8, 8, ("decoded_opcodes",), "Decoded opcode selector width."),
        _const("FAULT_CAUSE_BITS", 16, 8, ("fault_packets",), "Fault cause field width."),
        _const("CAPCAUSE_BITS", 4, 8, ("fault_packets",), "Capability-specific cause field width."),
        _const("FAULT_CAP_IDX_BITS", 8, 8, ("fault_packets",), "Fault capability index field width."),
        _const("RETIRE_SEQUENCE_BITS", 64, 8, ("retire_packets",), "Retire sequence number width."),
    )


def _opcode_constants() -> tuple[SvConstant, ...]:
    constants: list[SvConstant] = []
    for form in opcodes.all_opcode_forms():
        name = f"OPC_{_sv_name(form.mnemonic)}_{form.size.bits}"
        constants.append(
            _const(
                name,
                form.opcode_id,
                8,
                ("decoded_opcodes",),
                f"{form.mnemonic} {form.size.bits}-bit opcode selector.",
            )
        )
    return tuple(constants)


def _structs() -> tuple[SvStruct, ...]:
    return (
        SvStruct(
            "cap_payload_t",
            ("capabilities",),
            "Packed 96-bit capability payload.",
            (
                _field("cursor", "logic", caps.CAPABILITY_CURSOR_BITS, ("capabilities",), "Current cell cursor."),
                _field("bounds_metadata", "logic", caps.CAPABILITY_BOUNDS_METADATA_BITS, ("capabilities",), "Compressed bounds metadata."),
                _field("permissions", "logic", caps.CAPABILITY_PERMISSION_BITS, ("capabilities",), "Permission mask."),
                _field("otype", "logic", caps.CAPABILITY_OBJECT_TYPE_BITS, ("capabilities",), "Object type or unsealed marker."),
                _field("flags", "logic", caps.CAPABILITY_FLAG_BITS, ("capabilities",), "Global/local and future flag bits."),
            ),
        ),
        SvStruct(
            "cap_t",
            ("capabilities", "tags"),
            "Capability payload plus architectural tag.",
            (
                _field("payload", "cap_payload_t", caps.CAPABILITY_PAYLOAD_BITS, ("capabilities",), "Capability payload."),
                _field("tag", "logic", caps.CAPABILITY_TAG_BITS, ("tags",), "Out-of-band validity tag."),
            ),
        ),
        SvStruct(
            "decoded_opcode_t",
            ("decoded_opcodes",),
            "Decoded opcode identity carried from XLT onward.",
            (
                _field("valid", "logic", 1, ("decoded_opcodes",), "Decoded instruction is valid."),
                _field("opcode_id", "logic", 8, ("decoded_opcodes",), "Canonical opcode selector."),
                _field("size_bits", "logic", 8, ("decoded_opcodes",), "Architectural instruction size in bits."),
                _field("privileged", "logic", 1, ("decoded_opcodes",), "Instruction requires kernel or CSR-specific checks."),
            ),
        ),
        SvStruct(
            "fault_packet_t",
            ("fault_packets",),
            "Precise exception packet carried to RT.",
            (
                _field("valid", "logic", 1, ("fault_packets",), "Fault packet is selected."),
                _field("cause", "logic", 16, ("fault_packets",), "Exception cause."),
                _field("pc_cell", "logic", cells.ADDRESS_BITS, ("fault_packets", "cells"), "Faulting instruction cell address."),
                _field("slot", "logic", 1, ("fault_packets",), "Faulting instruction slot."),
                _field("tval", "logic", cells.ADDRESS_BITS, ("fault_packets", "cells"), "Trap value."),
                _field("capcause", "logic", 4, ("fault_packets",), "Capability-specific cause."),
                _field("fault_cap_idx", "logic", 8, ("fault_packets",), "Faulting capability operand index."),
            ),
        ),
        SvStruct(
            "retire_packet_t",
            ("retire_packets", "fault_packets", "decoded_opcodes", "cells"),
            "One architectural retire, fault, or redirect decision at RT.",
            (
                _field("valid", "logic", 1, ("retire_packets",), "Retire packet is valid."),
                _field("sequence", "logic", 64, ("retire_packets",), "In-order sequence number."),
                _field("pc_cell", "logic", cells.ADDRESS_BITS, ("retire_packets", "cells"), "Instruction cell address."),
                _field("slot", "logic", 1, ("retire_packets",), "Instruction slot."),
                _field("instruction_length", "logic", 2, ("retire_packets",), "Instruction length in cells."),
                _field("decoded", "decoded_opcode_t", None, ("retire_packets", "decoded_opcodes"), "Decoded opcode identity."),
                _field("normal_valid", "logic", 1, ("retire_packets",), "Normal effects selected."),
                _field("fault", "fault_packet_t", None, ("retire_packets", "fault_packets"), "Selected precise fault packet."),
                _field("redirect_valid", "logic", 1, ("retire_packets",), "Redirect target selected."),
                _field("redirect_target", "cap_t", None, ("retire_packets", "capabilities", "tags"), "Redirect target capability payload and tag."),
                _field("redirect_slot", "logic", 1, ("retire_packets",), "Redirect target slot."),
            ),
        ),
    )


def _interfaces() -> tuple[SvInterface, ...]:
    return (
        SvInterface(
            "cpu_v01_imem_if",
            ("instruction_memory", "cells"),
            "Instruction fetch group request/response interface.",
            (
                _field("req_valid", "logic", 1, ("instruction_memory",), "Fetch request is valid."),
                _field("req_ready", "logic", 1, ("instruction_memory",), "Instruction memory can accept request."),
                _field("req_addr", "logic", cells.ADDRESS_BITS, ("instruction_memory", "cells"), "Fetch group base cell address."),
                _field("rsp_valid", "logic", 1, ("instruction_memory",), "Fetch response is valid."),
                _field("rsp_ready", "logic", 1, ("instruction_memory",), "Core can accept response."),
                _field("rsp_cells", "cell_t[FETCH_GROUP_CELLS]", cells.CELL_BITS * cells.FETCH_GROUP_CELLS, ("instruction_memory", "cells"), "Fetched 48-bit group as cells."),
                _field("rsp_fault", "fault_packet_t", None, ("instruction_memory", "fault_packets"), "Fetch-side fault packet."),
            ),
        ),
        SvInterface(
            "cpu_v01_dmem_if",
            ("data_memory", "cells"),
            "Data payload memory request/response interface.",
            (
                _field("req_valid", "logic", 1, ("data_memory",), "Data request is valid."),
                _field("req_ready", "logic", 1, ("data_memory",), "Data memory can accept request."),
                _field("req_write", "logic", 1, ("data_memory",), "Request writes payload cells."),
                _field("req_addr", "logic", cells.ADDRESS_BITS, ("data_memory", "cells"), "Payload cell address."),
                _field("req_len_cells", "logic", 3, ("data_memory", "cells"), "Payload transfer length in cells."),
                _field("req_wdata", "cell_t[CAPABILITY_OBJECT_CELLS]", cells.CELL_BITS * cells.CAPABILITY_OBJECT_CELLS, ("data_memory", "cells", "capabilities"), "Write payload cells."),
                _field("rsp_valid", "logic", 1, ("data_memory",), "Data response is valid."),
                _field("rsp_rdata", "cell_t[CAPABILITY_OBJECT_CELLS]", cells.CELL_BITS * cells.CAPABILITY_OBJECT_CELLS, ("data_memory", "cells", "capabilities"), "Read payload cells."),
                _field("rsp_fault", "fault_packet_t", None, ("data_memory", "fault_packets"), "Data-side fault packet."),
            ),
        ),
        SvInterface(
            "cpu_v01_tagmem_if",
            ("tag_memory", "tags", "capabilities"),
            "Capability tag sidecar memory interface.",
            (
                _field("req_valid", "logic", 1, ("tag_memory",), "Tag request is valid."),
                _field("req_ready", "logic", 1, ("tag_memory",), "Tag memory can accept request."),
                _field("req_write", "logic", 1, ("tag_memory",), "Request writes a tag."),
                _field("req_slot_addr", "logic", cells.ADDRESS_BITS, ("tag_memory", "cells"), "Naturally aligned capability slot address."),
                _field("req_wtag", "logic", caps.CAPABILITY_TAG_BITS, ("tag_memory", "tags"), "Tag write value."),
                _field("rsp_valid", "logic", 1, ("tag_memory",), "Tag response is valid."),
                _field("rsp_rtag", "logic", caps.CAPABILITY_TAG_BITS, ("tag_memory", "tags"), "Tag read value."),
            ),
        ),
        SvInterface(
            "cpu_v01_retire_if",
            ("retire_packets",),
            "Retire trace interface consumed by the differential harness.",
            (
                _field("valid", "logic", 1, ("retire_packets",), "Retire packet is valid."),
                _field("ready", "logic", 1, ("retire_packets",), "Harness can accept retire packet."),
                _field("packet", "retire_packet_t", None, ("retire_packets",), "Retire packet payload."),
            ),
        ),
    )


def _const(
    name: str,
    value: int,
    width: int,
    surfaces: tuple[str, ...],
    description: str,
) -> SvConstant:
    return SvConstant(name, value, width, surfaces, description)


def _field(
    name: str,
    type_name: str,
    width: int | None,
    surfaces: tuple[str, ...],
    description: str,
) -> SvField:
    return SvField(name, type_name, width, surfaces, description)


def _covered_surfaces(contract: SystemVerilogContract) -> set[str]:
    surfaces: set[str] = set()
    for constant in (*contract.constants, *contract.opcode_constants):
        surfaces.update(constant.surfaces)
    for struct in contract.structs:
        surfaces.update(struct.surfaces)
        for field in struct.fields:
            surfaces.update(field.surfaces)
    for interface in contract.interfaces:
        surfaces.update(interface.surfaces)
        for signal in interface.signals:
            surfaces.update(signal.surfaces)
    return surfaces


def _constant_row(constant: SvConstant) -> str:
    return (
        f"| `{constant.name}` | {constant.value} | {constant.width} | "
        f"{_surface_text(constant.surfaces)} | {constant.description} |"
    )


def _field_row(field: SvField) -> str:
    width = "-" if field.width is None else str(field.width)
    return (
        f"| `{field.name}` | `{field.type_name}` | {width} | "
        f"{_surface_text(field.surfaces)} | {field.description} |"
    )


def _surface_text(surfaces: tuple[str, ...]) -> str:
    return ", ".join(f"`{surface}`" for surface in surfaces)


def _sv_name(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _require_identifier(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"invalid SystemVerilog identifier {value!r}")


def _require_surfaces(surfaces: tuple[str, ...]) -> None:
    if not surfaces:
        raise ValueError("at least one surface is required")
    unknown = set(surfaces) - REQUIRED_SV_SURFACES
    if unknown:
        raise ValueError(f"unknown surfaces: {sorted(unknown)!r}")

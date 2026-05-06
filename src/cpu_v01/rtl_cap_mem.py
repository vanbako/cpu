"""Capability and memory/tag SystemVerilog slice validation helpers.

Owner stories:
- I20-S02: semantic golden retire trace corpus.
- I20-S03: generated SystemVerilog package/interface contract.
- I20-S06: capability register and memory/tag RTL behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import golden_traces


JsonValue = Any

RTL_CAP_MEM_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_cap_mem_core.sv"),
    Path("rtl/cpu_v01_cap_mem_tb.sv"),
)
RTL_CAP_MEM_CASE_IDS = (
    "capability_derivation.cmove_cgetaddr",
    "capability_derivation.csetaddr_candperm",
    "memory_tag_ops.csc_clc_st48_ld48",
    "fault_cases.invalid_tag_csetaddr",
)


@dataclass(frozen=True)
class RtlCapMemPacketProjection:
    case_id: str
    sequence: int
    mnemonic: str
    pc_cell: int
    opcode_id: int | None
    normal_valid: bool
    integer_write_register: str | None = None
    integer_write_value: int | None = None
    capability_write_register: str | None = None
    capability_write_tag: bool | None = None
    capability_write_cursor: int | None = None
    capability_write_permissions: int | None = None
    memory_effect_kind: str | None = None
    memory_effect_address: int | None = None
    memory_tag_write: bool | None = None
    fault_cause: str | None = None
    capcause: str | None = None
    fault_cap_idx: str | None = None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "sequence": self.sequence,
            "mnemonic": self.mnemonic,
            "pc_cell": self.pc_cell,
            "opcode_id": self.opcode_id,
            "normal_valid": self.normal_valid,
            "integer_write_register": self.integer_write_register,
            "integer_write_value": self.integer_write_value,
            "capability_write_register": self.capability_write_register,
            "capability_write_tag": self.capability_write_tag,
            "capability_write_cursor": self.capability_write_cursor,
            "capability_write_permissions": self.capability_write_permissions,
            "memory_effect_kind": self.memory_effect_kind,
            "memory_effect_address": self.memory_effect_address,
            "memory_tag_write": self.memory_tag_write,
            "fault_cause": self.fault_cause,
            "capcause": self.capcause,
            "fault_cap_idx": self.fault_cap_idx,
        }


def cap_mem_slice_case_ids() -> tuple[str, ...]:
    return RTL_CAP_MEM_CASE_IDS


def cap_mem_packet_projections() -> tuple[RtlCapMemPacketProjection, ...]:
    projections: list[RtlCapMemPacketProjection] = []
    for case_id in RTL_CAP_MEM_CASE_IDS:
        case = golden_traces.golden_trace_case_by_id(case_id)
        for packet in case.packets:
            projections.append(_project_packet(case_id, packet))
    return tuple(projections)


def cap_mem_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(projection.as_dict() for projection in cap_mem_packet_projections()),
        indent=indent,
        sort_keys=True,
    )


def validate_rtl_cap_mem_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CAP_MEM_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL cap/mem source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_cap_mem_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_cap_mem_tb.sv")

    for token in (
        "OPC_CMOVE_48",
        "OPC_CGETADDR_48",
        "OPC_CSETADDR_48",
        "OPC_CANDPERM_48",
        "OPC_LD48_24",
        "OPC_ST48_24",
        "OPC_CLC_24",
        "OPC_CSC_24",
        "EXC_CAPABILITY_TAG_FAULT",
        "CAPCAUSE_TAG",
        "capability_write_valid",
        "memory_effect_kind",
        "tag_write_valid",
    ):
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_cap_mem_core",
        "ST_CMOVE",
        "ST_CGETADDR",
        "ST_CSETADDR",
        "ST_CANDPERM",
        "ST_CSC",
        "ST_CLC",
        "ST_ST48",
        "ST_LD48",
        "ST_INVALID_TAG_FAULT",
        "cap_with_cursor",
        "cap_with_permissions",
        "memory_tag_q <= 1'b0",
        "retire_packet_q.fault.cause <= EXC_CAPABILITY_TAG_FAULT",
    ):
        if token not in core:
            issues.append(f"cpu_v01_cap_mem_core.sv missing {token}")

    for token in (
        "module cpu_v01_cap_mem_tb",
        "CMOVE/CGETADDR smoke result mismatch",
        "CSETADDR/CANDPERM smoke result mismatch",
        "ST48/LD48 tag-clear smoke result mismatch",
        "invalid-tag fault smoke result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_cap_mem_tb.sv missing {token}")

    projections = cap_mem_packet_projections()
    mnemonics = {projection.mnemonic for projection in projections}
    for mnemonic in ("CMOVE", "CGETADDR", "CSETADDR", "CANDPERM", "CSC", "CLC", "ST48", "LD48"):
        if mnemonic not in mnemonics:
            issues.append(f"missing cap/mem projection for {mnemonic}")

    by_mnemonic = {projection.mnemonic: projection for projection in projections}
    if by_mnemonic["CMOVE"].capability_write_register != "C2":
        issues.append("CMOVE projection must write C2")
    if by_mnemonic["CGETADDR"].integer_write_value != 0x2200:
        issues.append("CGETADDR projection must write D3 with cursor 0x2200")
    if by_mnemonic["CANDPERM"].capability_write_permissions != 1:
        issues.append("CANDPERM projection must reduce permissions to LD")
    if by_mnemonic["ST48"].memory_tag_write is not False:
        issues.append("ST48 projection must clear the memory tag")
    if by_mnemonic["LD48"].integer_write_value != 0x123456789ABC:
        issues.append("LD48 projection must load the ST48 value")

    invalid = next(
        projection
        for projection in projections
        if projection.case_id == "fault_cases.invalid_tag_csetaddr"
    )
    if invalid.fault_cause != "CAPABILITY_TAG_FAULT":
        issues.append("invalid-tag projection must fault with CAPABILITY_TAG_FAULT")
    if invalid.capcause != "TAG" or invalid.fault_cap_idx != "C1":
        issues.append("invalid-tag projection must report TAG/C1")

    return tuple(issues)


def _project_packet(case_id: str, packet: dict[str, JsonValue]) -> RtlCapMemPacketProjection:
    normal_effects = packet.get("normal_effects")
    fault_packet = packet.get("fault_packet")
    integer_write_register = None
    integer_write_value = None
    capability_write_register = None
    capability_write_tag = None
    capability_write_cursor = None
    capability_write_permissions = None
    memory_effect_kind = None
    memory_effect_address = None
    memory_tag_write = None

    if isinstance(normal_effects, dict):
        integer_writes = normal_effects.get("integer_writes", [])
        if integer_writes:
            integer_write_register = integer_writes[0]["register"]
            integer_write_value = integer_writes[0]["value"]

        capability_writes = normal_effects.get("capability_writes", [])
        if capability_writes:
            write = capability_writes[0]
            capability = write["capability"]
            payload = capability["payload"]
            capability_write_register = write["register"]
            capability_write_tag = capability["tag"]
            capability_write_cursor = payload["cursor"]
            capability_write_permissions = payload["permissions"]

        memory_effects = normal_effects.get("memory_effects", [])
        if memory_effects:
            effect = memory_effects[0]
            memory_effect_kind = effect["kind"]
            memory_effect_address = effect["address"]
            memory_tag_write = True if effect["kind"] == "CSC" else False

    fault_cause = None
    capcause = None
    fault_cap_idx = None
    if isinstance(fault_packet, dict):
        fault_cause = fault_packet["cause"]
        capcause = fault_packet["capcause"]
        fault_cap_idx = fault_packet["fault_cap_idx"]

    return RtlCapMemPacketProjection(
        case_id=case_id,
        sequence=packet["sequence"],
        mnemonic=packet["mnemonic"],
        pc_cell=packet["pc_cell"],
        opcode_id=packet["opcode_id"],
        normal_valid=normal_effects is not None,
        integer_write_register=integer_write_register,
        integer_write_value=integer_write_value,
        capability_write_register=capability_write_register,
        capability_write_tag=capability_write_tag,
        capability_write_cursor=capability_write_cursor,
        capability_write_permissions=capability_write_permissions,
        memory_effect_kind=memory_effect_kind,
        memory_effect_address=memory_effect_address,
        memory_tag_write=memory_tag_write,
        fault_cause=fault_cause,
        capcause=capcause,
        fault_cap_idx=fault_cap_idx,
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

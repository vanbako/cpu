"""Integrated cpu_v01_core capability and memory/tag helpers.

Owner stories:
- I22-S04: integrated capability derivation, data memory, and tag memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import rtl_cap_mem


JsonValue = Any

RTL_CORE_CAP_MEM_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_cap_mem_tb.sv"),
)
RTL_CORE_CAP_MEM_DOC = Path("docs/implementation/rtl-integrated-core-cap-mem.md")


@dataclass(frozen=True)
class IntegratedCapMemCoverageRow:
    case_id: str
    mnemonic: str
    retire_effects: tuple[str, ...]
    integrated_path: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "mnemonic": self.mnemonic,
            "retire_effects": list(self.retire_effects),
            "integrated_path": self.integrated_path,
        }


def integrated_cap_mem_coverage_rows() -> tuple[IntegratedCapMemCoverageRow, ...]:
    return tuple(
        IntegratedCapMemCoverageRow(
            case_id=projection.case_id,
            mnemonic=projection.mnemonic,
            retire_effects=_retire_effects(projection),
            integrated_path="cpu_v01_core.execute_decoded_packet+memory_states",
        )
        for projection in rtl_cap_mem.cap_mem_packet_projections()
    )


def integrated_cap_mem_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in integrated_cap_mem_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_cap_mem_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_CAP_MEM_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_core_cap_mem_tb {sources}"
    )


def validate_rtl_core_cap_mem(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_CAP_MEM_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing integrated core cap/mem source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_cap_mem_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_CAP_MEM_DOC)

    for token in (
        "ST_MEM_DREQ",
        "ST_MEM_DWAIT",
        "ST_MEM_TAG_REQ",
        "ST_MEM_TAG_WAIT",
        "dmem_req_valid = state_q == ST_MEM_DREQ",
        "tagmem_req_valid = state_q == ST_MEM_TAG_REQ",
        "cap_payload_cell",
        "cap_from_cells",
        "cap_contains_range",
        "memory_access_check",
        "prepare_memory_op",
        "start_pending_packet",
        "OPC_LD48_24",
        "OPC_ST48_24",
        "OPC_CLC_24",
        "OPC_CSC_24",
        "OPC_CMOVE_48",
        "OPC_CGETADDR_48",
        "OPC_CSETADDR_48",
        "OPC_CANDPERM_48",
        "MEM_EFFECT_ST48",
        "MEM_EFFECT_CSC",
        "EXC_CAPABILITY_TAG_FAULT",
        "CAPCAUSE_TAG",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "module cpu_v01_core_cap_mem_tb",
        "cpu_v01_core_cap_mem_fixture",
        "CCSRRD C1, PCC",
        "CMOVE C2, C1",
        "CGETADDR D3, C2",
        "CSETADDR C4, C1, D3",
        "CANDPERM C5, C4, D1",
        "CSC C1, D0, C2",
        "CLC C6, C1, D0",
        "ST48 C1, D0, D7",
        "LD48 D8, C1, D0",
        "integrated cap/mem CLC mismatch",
        "integrated cap/mem ST48 mismatch",
        "integrated cap/mem invalid-tag fault mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_cap_mem_tb.sv missing {token}")

    rows = integrated_cap_mem_coverage_rows()
    mnemonics = {row.mnemonic for row in rows}
    for mnemonic in ("CMOVE", "CGETADDR", "CSETADDR", "CANDPERM", "CSC", "CLC", "ST48", "LD48"):
        if mnemonic not in mnemonics:
            issues.append(f"missing integrated cap/mem projection for {mnemonic}")

    by_mnemonic = {row.mnemonic: row for row in rows}
    if by_mnemonic["ST48"].retire_effects != ("memory_effect:ST48", "tag_write:clear"):
        issues.append("ST48 row must identify integer memory write and tag clear")
    if by_mnemonic["CSC"].retire_effects != ("memory_effect:CSC", "tag_write:preserve"):
        issues.append("CSC row must identify capability memory write and tag preserve")
    invalid = next(row for row in rows if row.case_id == "fault_cases.invalid_tag_csetaddr")
    if invalid.retire_effects != ("fault:CAPABILITY_TAG_FAULT",):
        issues.append("invalid-tag row must identify CAPABILITY_TAG_FAULT")

    for token in (
        "Story: I22-S04",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_cap_mem_tb.sv",
        "python tools\\rtl_core_cap_mem.py --check",
        "cpu_v01_core_cap_mem_tb",
        "ST_MEM_DREQ",
        "tag-memory",
        "CMOVE",
        "CGETADDR",
        "CSETADDR",
        "CANDPERM",
        "LD48",
        "ST48",
        "CLC",
        "CSC",
        "invalid-tag",
        "I22-S05",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_CAP_MEM_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"integrated cap/mem coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _retire_effects(projection: rtl_cap_mem.RtlCapMemPacketProjection) -> tuple[str, ...]:
    if projection.fault_cause:
        return (f"fault:{projection.fault_cause}",)
    effects: list[str] = []
    if projection.integer_write_register:
        effects.append("integer_write")
    if projection.capability_write_register:
        effects.append("capability_write")
    if projection.memory_effect_kind:
        effects.append(f"memory_effect:{projection.memory_effect_kind}")
        effects.append("tag_write:preserve" if projection.memory_tag_write else "tag_write:clear")
    if not effects:
        effects.append("normal_retire:no_write")
    return tuple(effects)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

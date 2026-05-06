"""First SystemVerilog smoke-slice validation helpers.

Owner stories:
- I20-S01: first RTL slice contract.
- I20-S02: semantic golden retire trace corpus.
- I20-S03: generated SystemVerilog package/interface contract.
- I20-S05: first single-core SystemVerilog smoke slice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import golden_traces, opcodes


JsonValue = Any

RTL_SMOKE_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_smoke_core.sv"),
    Path("rtl/cpu_v01_smoke_tb.sv"),
)
RTL_SMOKE_CASE_IDS = (
    "reset_smoke.add_slot0",
    "fault_cases.slot1_48bit_placement",
)


@dataclass(frozen=True)
class RtlSmokePacketProjection:
    case_id: str
    sequence: int
    pc_cell: int
    slot: int
    opcode_id: int | None
    normal_valid: bool
    integer_write_register: str | None = None
    integer_write_value: int | None = None
    fault_cause: str | None = None
    result_stage: str = ""

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "sequence": self.sequence,
            "pc_cell": self.pc_cell,
            "slot": self.slot,
            "opcode_id": self.opcode_id,
            "normal_valid": self.normal_valid,
            "integer_write_register": self.integer_write_register,
            "integer_write_value": self.integer_write_value,
            "fault_cause": self.fault_cause,
            "result_stage": self.result_stage,
        }


def smoke_slice_case_ids() -> tuple[str, ...]:
    return RTL_SMOKE_CASE_IDS


def smoke_slice_packet_projections() -> tuple[RtlSmokePacketProjection, ...]:
    projections: list[RtlSmokePacketProjection] = []
    for case_id in RTL_SMOKE_CASE_IDS:
        case = golden_traces.golden_trace_case_by_id(case_id)
        if len(case.packets) != 1:
            raise ValueError(f"{case_id} must contain exactly one first-slice packet")
        packet = case.packets[0]
        integer_write_register = None
        integer_write_value = None
        normal_effects = packet.get("normal_effects")
        if isinstance(normal_effects, dict):
            writes = normal_effects.get("integer_writes", [])
            if writes:
                write = writes[0]
                integer_write_register = write["register"]
                integer_write_value = write["value"]
        fault_cause = None
        fault_packet = packet.get("fault_packet")
        if isinstance(fault_packet, dict):
            fault_cause = fault_packet["cause"]
        projections.append(
            RtlSmokePacketProjection(
                case_id=case_id,
                sequence=packet["sequence"],
                pc_cell=packet["pc_cell"],
                slot=packet["slot"],
                opcode_id=packet["opcode_id"],
                normal_valid=packet["normal_effects"] is not None,
                integer_write_register=integer_write_register,
                integer_write_value=integer_write_value,
                fault_cause=fault_cause,
                result_stage=packet["result_stage"],
            )
        )
    return tuple(projections)


def smoke_slice_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(projection.as_dict() for projection in smoke_slice_packet_projections()),
        indent=indent,
        sort_keys=True,
    )


def validate_rtl_smoke_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_SMOKE_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL smoke source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_smoke_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_smoke_tb.sv")

    for token in (
        "package cpu_v01_pkg",
        "typedef struct packed",
        "retire_packet_t",
        "integer_write_valid",
        "integer_write_index",
        "integer_write_value",
        "OPC_ADD_24",
        "EXC_ALIGN_FAULT",
    ):
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_smoke_core",
        "FORCE_ILLEGAL_SLOT1",
        "slot_q != SLOT_0",
        "d_regs[rd] <= add_result",
        "retire_packet_q.normal_valid <= 1'b1",
        "retire_packet_q.fault.valid <= 1'b1",
        "retire_packet_q.integer_write_value <= add_result",
        "pc_q <= pc_q + 48'd1",
    ):
        if token not in core:
            issues.append(f"cpu_v01_smoke_core.sv missing {token}")

    for token in (
        "module cpu_v01_smoke_tb",
        "normal_core",
        "placement_core",
        "normal_packet.integer_write_value != 48'h0000_0000_0030",
        "placement_packet.fault.cause != EXC_ALIGN_FAULT",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_smoke_tb.sv missing {token}")

    projections = smoke_slice_packet_projections()
    reset_projection = projections[0]
    if reset_projection.case_id != "reset_smoke.add_slot0":
        issues.append("first smoke projection must be reset_smoke.add_slot0")
    if reset_projection.integer_write_register != "D2":
        issues.append("reset smoke projection must write D2")
    if reset_projection.integer_write_value != 0x30:
        issues.append("reset smoke projection must write 0x30")
    if reset_projection.opcode_id != opcodes.opcode_form_for("ADD").opcode_id:
        issues.append("reset smoke projection must use ADD opcode")

    placement_projection = projections[1]
    if placement_projection.fault_cause != "ALIGN_FAULT":
        issues.append("placement smoke projection must fault with ALIGN_FAULT")
    if placement_projection.result_stage != "PD":
        issues.append("placement smoke projection must be detected at PD")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

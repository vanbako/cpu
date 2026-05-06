"""Fault, trap, IRET, and protected-stack SystemVerilog slice helpers.

Owner stories:
- I20-S02: semantic golden retire trace corpus.
- I20-S03: generated SystemVerilog package/interface contract.
- I20-S07: precise fault, trap, and protected-stack RTL gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import golden_traces


JsonValue = Any

RTL_FAULT_TRAP_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_fault_trap_core.sv"),
    Path("rtl/cpu_v01_fault_trap_tb.sv"),
)
RTL_FAULT_TRAP_CASE_IDS = (
    "fault_cases.divide_by_zero",
    "traps.sys_to_tvc",
    "traps.sys_iret_return",
    "calls_returns.direct_call_ret",
)


@dataclass(frozen=True)
class RtlFaultTrapPacketProjection:
    case_id: str
    sequence: int
    mnemonic: str
    pc_cell: int
    opcode_id: int | None
    normal_valid: bool
    fault_cause: str | None = None
    trap_entered: bool = False
    trap_target_cursor: int | None = None
    csr_write_register: str | None = None
    csr_write_value: int | None = None
    ccsr_write_register: str | None = None
    ccsr_write_cursor: int | None = None
    memory_effect_kind: str | None = None
    memory_effect_address: int | None = None
    memory_capability_cursor: int | None = None
    memory_capability_otype: int | None = None
    memory_tag_write: bool | None = None
    pcc_update_cursor: int | None = None
    pcc_update_slot: int | None = None
    epcc_update_cursor: int | None = None
    epcc_update_slot: int | None = None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "sequence": self.sequence,
            "mnemonic": self.mnemonic,
            "pc_cell": self.pc_cell,
            "opcode_id": self.opcode_id,
            "normal_valid": self.normal_valid,
            "fault_cause": self.fault_cause,
            "trap_entered": self.trap_entered,
            "trap_target_cursor": self.trap_target_cursor,
            "csr_write_register": self.csr_write_register,
            "csr_write_value": self.csr_write_value,
            "ccsr_write_register": self.ccsr_write_register,
            "ccsr_write_cursor": self.ccsr_write_cursor,
            "memory_effect_kind": self.memory_effect_kind,
            "memory_effect_address": self.memory_effect_address,
            "memory_capability_cursor": self.memory_capability_cursor,
            "memory_capability_otype": self.memory_capability_otype,
            "memory_tag_write": self.memory_tag_write,
            "pcc_update_cursor": self.pcc_update_cursor,
            "pcc_update_slot": self.pcc_update_slot,
            "epcc_update_cursor": self.epcc_update_cursor,
            "epcc_update_slot": self.epcc_update_slot,
        }


def fault_trap_slice_case_ids() -> tuple[str, ...]:
    return RTL_FAULT_TRAP_CASE_IDS


def fault_trap_packet_projections() -> tuple[RtlFaultTrapPacketProjection, ...]:
    projections: list[RtlFaultTrapPacketProjection] = []
    for case_id in RTL_FAULT_TRAP_CASE_IDS:
        case = golden_traces.golden_trace_case_by_id(case_id)
        for index, packet in enumerate(case.packets):
            projections.append(_project_packet(case, index, packet))
    return tuple(projections)


def fault_trap_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(projection.as_dict() for projection in fault_trap_packet_projections()),
        indent=indent,
        sort_keys=True,
    )


def validate_rtl_fault_trap_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_FAULT_TRAP_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL fault/trap source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_fault_trap_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fault_trap_tb.sv")

    for token in (
        "OPC_DIV_24",
        "OPC_SYS_12",
        "OPC_IRET_24",
        "OPC_CALL_24",
        "OPC_RET_12",
        "EXC_DIVIDE_BY_ZERO",
        "EXC_SYSCALL_TRAP",
        "MEM_EFFECT_RETURN_STACK_PUSH",
        "trap_entry_valid",
        "pcc_update_valid",
        "epcc_update_valid",
        "csr_write_valid",
        "ccsr_write_valid",
    ):
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_fault_trap_core",
        "ST_DIV_ZERO_FAULT",
        "ST_SYS_TRAP",
        "ST_IRET",
        "ST_CALL",
        "ST_RET",
        "retire_packet_q.fault.cause <= cause",
        "retire_packet_q.trap_entry_valid <= 1'b1",
        "retire_packet_q.pcc_update_valid <= 1'b1",
        "retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH",
        "retire_packet_q.ccsr_write_index <= CCSR_RSC",
    ):
        if token not in core:
            issues.append(f"cpu_v01_fault_trap_core.sv missing {token}")

    for token in (
        "module cpu_v01_fault_trap_tb",
        "divide fault smoke result mismatch",
        "SYS trap entry smoke result mismatch",
        "IRET PCC restore smoke result mismatch",
        "CALL protected return-stack push smoke result mismatch",
        "RET protected return-stack restore smoke result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fault_trap_tb.sv missing {token}")

    projections = fault_trap_packet_projections()
    by_case_mnemonic = {
        (projection.case_id, projection.mnemonic): projection
        for projection in projections
    }

    divide = by_case_mnemonic[("fault_cases.divide_by_zero", "DIV")]
    if divide.normal_valid or divide.fault_cause != "DIVIDE_BY_ZERO":
        issues.append("divide projection must be a no-normal-effect DIVIDE_BY_ZERO fault")

    sys = by_case_mnemonic[("traps.sys_to_tvc", "SYS")]
    if sys.fault_cause != "SYSCALL_TRAP" or not sys.trap_entered:
        issues.append("SYS projection must trap with SYSCALL_TRAP")
    if sys.trap_target_cursor != 0x9000:
        issues.append("SYS projection must enter TVC at 0x9000")

    iret = by_case_mnemonic[("traps.sys_iret_return", "IRET")]
    if iret.pcc_update_cursor != 0x1750:
        issues.append("IRET projection must restore EPCC cursor 0x1750")
    if iret.csr_write_register != "SR":
        issues.append("IRET projection must restore SR")

    call = by_case_mnemonic[("calls_returns.direct_call_ret", "CALL")]
    if call.memory_effect_kind != "RETURN_STACK_PUSH":
        issues.append("CALL projection must push the protected return stack")
    if call.memory_effect_address != 0x3000 or call.memory_tag_write is not True:
        issues.append("CALL projection must write a tagged return capability at 0x3000")
    if call.ccsr_write_register != "RSC" or call.ccsr_write_cursor != 0x3000:
        issues.append("CALL projection must decrement RSC to 0x3000")
    if call.pcc_update_cursor != 0x1510:
        issues.append("CALL projection must redirect PCC to 0x1510")

    ret = by_case_mnemonic[("calls_returns.direct_call_ret", "RET")]
    if ret.pcc_update_cursor != 0x1501 or ret.ccsr_write_cursor != 0x3004:
        issues.append("RET projection must restore return PCC and RSC")

    return tuple(issues)


def _project_packet(
    case: golden_traces.GoldenTraceCase,
    packet_index: int,
    packet: dict[str, JsonValue],
) -> RtlFaultTrapPacketProjection:
    normal_effects = packet.get("normal_effects")
    fault_packet = packet.get("fault_packet")
    trap_entry = packet.get("trap_entry")

    csr_write_register = None
    csr_write_value = None
    ccsr_write_register = None
    ccsr_write_cursor = None
    memory_effect_kind = None
    memory_effect_address = None
    memory_capability_cursor = None
    memory_capability_otype = None
    memory_tag_write = None
    pcc_update_cursor = None
    pcc_update_slot = None
    epcc_update_cursor = None
    epcc_update_slot = None

    if isinstance(normal_effects, dict):
        csr_writes = normal_effects.get("csr_writes", [])
        if csr_writes:
            csr_write_register = csr_writes[0]["register"]
            csr_write_value = csr_writes[0]["value"]

        ccsr_writes = normal_effects.get("ccsr_writes", [])
        if ccsr_writes:
            write = ccsr_writes[0]
            ccsr_write_register = write["register"]
            ccsr_write_cursor = write["capability"]["payload"]["cursor"]

        memory_effects = normal_effects.get("memory_effects", [])
        if memory_effects:
            effect = memory_effects[0]
            memory_effect_kind = effect["kind"]
            memory_effect_address = effect["address"]
            capability = effect.get("capability")
            if isinstance(capability, dict):
                memory_capability_cursor = capability["payload"]["cursor"]
                memory_capability_otype = capability["payload"]["otype"]
                memory_tag_write = capability["tag"]

        pcc_update = normal_effects.get("pcc_update")
        if isinstance(pcc_update, dict):
            pcc_update_cursor = pcc_update["payload"]["cursor"]
            pcc_update_slot = pcc_update["slot"]

        epcc_update = normal_effects.get("epcc_update")
        if isinstance(epcc_update, dict):
            epcc_update_cursor = epcc_update["payload"]["cursor"]
            epcc_update_slot = epcc_update["slot"]

    fault_cause = None
    if isinstance(fault_packet, dict):
        fault_cause = fault_packet["cause"]

    trap_entered = isinstance(trap_entry, dict) and trap_entry.get("entered") is True
    trap_target_cursor = None
    if trap_entered:
        trap_target_cursor = _trap_target_cursor(case, packet_index)

    return RtlFaultTrapPacketProjection(
        case_id=case.case_id,
        sequence=packet["sequence"],
        mnemonic=packet["mnemonic"],
        pc_cell=packet["pc_cell"],
        opcode_id=packet["opcode_id"],
        normal_valid=normal_effects is not None,
        fault_cause=fault_cause,
        trap_entered=trap_entered,
        trap_target_cursor=trap_target_cursor,
        csr_write_register=csr_write_register,
        csr_write_value=csr_write_value,
        ccsr_write_register=ccsr_write_register,
        ccsr_write_cursor=ccsr_write_cursor,
        memory_effect_kind=memory_effect_kind,
        memory_effect_address=memory_effect_address,
        memory_capability_cursor=memory_capability_cursor,
        memory_capability_otype=memory_capability_otype,
        memory_tag_write=memory_tag_write,
        pcc_update_cursor=pcc_update_cursor,
        pcc_update_slot=pcc_update_slot,
        epcc_update_cursor=epcc_update_cursor,
        epcc_update_slot=epcc_update_slot,
    )


def _trap_target_cursor(case: golden_traces.GoldenTraceCase, packet_index: int) -> int | None:
    if packet_index + 1 < len(case.packets):
        return int(case.packets[packet_index + 1]["pc_cell"])
    pcc = case.final_observations.get("pcc")
    if isinstance(pcc, dict):
        payload = pcc.get("payload")
        if isinstance(payload, dict):
            return int(payload["cursor"])
    return None


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

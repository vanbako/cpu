"""Integrated cpu_v01_core SystemVerilog shell helpers.

Owner stories:
- I22-S01: integrated single-core RTL top-level shell.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JsonValue = Any

RTL_CORE_SHELL_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_shell_tb.sv"),
)
RTL_CORE_SHELL_DOC = Path("docs/implementation/rtl-integrated-core-shell.md")


@dataclass(frozen=True)
class RtlCorePort:
    name: str
    direction: str
    type_name: str
    group: str
    idle_value: str
    summary: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "type_name": self.type_name,
            "group": self.group,
            "idle_value": self.idle_value,
            "summary": self.summary,
        }


def core_shell_ports() -> tuple[RtlCorePort, ...]:
    return (
        RtlCorePort("clk", "input", "logic", "clock_reset", "-", "Core clock."),
        RtlCorePort("rst_n", "input", "logic", "clock_reset", "-", "Active-low reset."),
        RtlCorePort("imem_req_valid", "output", "logic", "instruction_memory", "0", "Instruction fetch request valid."),
        RtlCorePort("imem_req_ready", "input", "logic", "instruction_memory", "-", "Instruction memory request ready."),
        RtlCorePort("imem_req_addr", "output", "addr_t", "instruction_memory", "reset PCC cursor", "Instruction fetch group cell address."),
        RtlCorePort("imem_rsp_valid", "input", "logic", "instruction_memory", "-", "Instruction fetch response valid."),
        RtlCorePort("imem_rsp_ready", "output", "logic", "instruction_memory", "0", "Core accepts instruction response."),
        RtlCorePort("imem_rsp_cells", "input", "cell_t[FETCH_GROUP_CELLS]", "instruction_memory", "-", "Fetched instruction cells."),
        RtlCorePort("imem_rsp_fault", "input", "fault_packet_t", "instruction_memory", "-", "Fetch-side fault packet."),
        RtlCorePort("dmem_req_valid", "output", "logic", "data_memory", "0", "Data request valid."),
        RtlCorePort("dmem_req_ready", "input", "logic", "data_memory", "-", "Data memory request ready."),
        RtlCorePort("dmem_req_write", "output", "logic", "data_memory", "0", "Data request writes payload."),
        RtlCorePort("dmem_req_addr", "output", "addr_t", "data_memory", "0", "Data payload cell address."),
        RtlCorePort("dmem_req_len_cells", "output", "logic[2:0]", "data_memory", "0", "Data payload transfer length in cells."),
        RtlCorePort("dmem_req_wdata", "output", "cell_t[CAPABILITY_OBJECT_CELLS]", "data_memory", "0", "Data payload write cells."),
        RtlCorePort("dmem_rsp_valid", "input", "logic", "data_memory", "-", "Data response valid."),
        RtlCorePort("dmem_rsp_rdata", "input", "cell_t[CAPABILITY_OBJECT_CELLS]", "data_memory", "-", "Data response payload cells."),
        RtlCorePort("dmem_rsp_fault", "input", "fault_packet_t", "data_memory", "-", "Data-side fault packet."),
        RtlCorePort("tagmem_req_valid", "output", "logic", "tag_memory", "0", "Tag request valid."),
        RtlCorePort("tagmem_req_ready", "input", "logic", "tag_memory", "-", "Tag memory request ready."),
        RtlCorePort("tagmem_req_write", "output", "logic", "tag_memory", "0", "Tag request writes tag."),
        RtlCorePort("tagmem_req_slot_addr", "output", "addr_t", "tag_memory", "0", "Capability slot address."),
        RtlCorePort("tagmem_req_wtag", "output", "logic", "tag_memory", "0", "Tag write value."),
        RtlCorePort("tagmem_rsp_valid", "input", "logic", "tag_memory", "-", "Tag response valid."),
        RtlCorePort("tagmem_rsp_rtag", "input", "logic", "tag_memory", "-", "Tag response value."),
        RtlCorePort("timer_interrupt_pending", "input", "logic", "events", "-", "Timer interrupt input."),
        RtlCorePort("software_interrupt_pending", "input", "logic", "events", "-", "Software IPI input."),
        RtlCorePort("external_interrupt_pending", "input", "logic", "events", "-", "External interrupt input."),
        RtlCorePort("external_event_valid", "input", "logic", "events", "-", "Fabric or endpoint event input."),
        RtlCorePort("external_event_cause", "input", "logic[15:0]", "events", "-", "Fabric or endpoint event cause."),
        RtlCorePort("debug_halt_request", "input", "logic", "debug", "-", "Debug halt request input."),
        RtlCorePort("retire_valid", "output", "logic", "retire", "0", "Retire packet valid."),
        RtlCorePort("retire_ready", "input", "logic", "retire", "-", "Differential harness ready."),
        RtlCorePort("retire_packet", "output", "retire_packet_t", "retire", "0", "Retire packet payload."),
        RtlCorePort("core_idle", "output", "logic", "debug", "1 after reset", "No instruction is in flight."),
        RtlCorePort("reset_observed", "output", "logic", "debug", "1 after reset", "Reset state has reached observable idle."),
        RtlCorePort("debug_pcc", "output", "cap_t", "debug", "reset ROM PCC", "Reset PCC observation."),
        RtlCorePort("debug_pcc_slot", "output", "logic", "debug", "0", "Reset PCC slot observation."),
        RtlCorePort("debug_sr", "output", "int_reg_t", "debug", "0xC0", "Reset SR observation."),
        RtlCorePort("debug_retire_sequence", "output", "logic[RETIRE_SEQUENCE_BITS-1:0]", "debug", "0", "Next retire sequence observation."),
    )


def core_shell_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_SHELL_SOURCE_FILES)
    return (
        "verilator --binary --timing --top-module "
        f"cpu_v01_core_shell_tb {sources}"
    )


def core_shell_ports_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(port.as_dict() for port in core_shell_ports()),
        indent=indent,
        sort_keys=True,
    )


def validate_rtl_core_shell(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_SHELL_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL core shell source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_shell_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_SHELL_DOC)

    for token in (
        "module cpu_v01_core",
        "RESET_VECTOR",
        "RESET_PCC_PERMISSIONS",
        "imem_req_valid",
        "imem_rsp_ready",
        "dmem_req_valid",
        "dmem_req_write",
        "tagmem_req_valid",
        "tagmem_req_write",
        "timer_interrupt_pending",
        "software_interrupt_pending",
        "external_interrupt_pending",
        "external_event_valid",
        "debug_halt_request",
        "retire_packet_t",
        "debug_pcc",
        "debug_sr",
        "SR_RESET_VALUE = 48'h0000_0000_00C0",
        "assign imem_req_valid = 1'b0",
        "assign dmem_req_valid = 1'b0",
        "assign tagmem_req_valid = 1'b0",
        "assign retire_valid = retire_packet_q.valid",
        "reset_pcc(RESET_VECTOR)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "module cpu_v01_core_shell_tb",
        "integrated core shell did not expose idle reset observation",
        "integrated core shell did not keep all request and retire ports idle",
        "integrated core shell reset PCC/SR observation mismatch",
        "debug_pcc.payload.permissions != 8'd4",
        "debug_sr != 48'h0000_0000_00C0",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_shell_tb.sv missing {token}")

    groups = {port.group for port in core_shell_ports()}
    for required in (
        "clock_reset",
        "instruction_memory",
        "data_memory",
        "tag_memory",
        "events",
        "debug",
        "retire",
    ):
        if required not in groups:
            issues.append(f"core shell port projection missing group {required}")

    by_name = {port.name: port for port in core_shell_ports()}
    for name, idle in {
        "imem_req_valid": "0",
        "dmem_req_valid": "0",
        "tagmem_req_valid": "0",
        "retire_valid": "0",
        "debug_sr": "0xC0",
    }.items():
        port = by_name.get(name)
        if port is None:
            issues.append(f"core shell port projection missing {name}")
        elif port.idle_value != idle:
            issues.append(f"core shell port {name} idle value must be {idle}")

    try:
        json.dumps(tuple(port.as_dict() for port in core_shell_ports()), sort_keys=True)
    except TypeError as exc:
        issues.append(f"core shell port projection is not JSON serializable: {exc}")

    for token in (
        "Story: I22-S01",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_shell_tb.sv",
        "python tools\\rtl_core_shell.py --check",
        "cpu_v01_core_shell_tb",
        "no-program",
        "I22-S02",
        "point-to-point fabric",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_SHELL_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

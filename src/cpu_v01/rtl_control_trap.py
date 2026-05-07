"""Control-transfer, syscall, and protected-stack SystemVerilog slice helpers.

Owner stories:
- I21-S04: RTL control-transfer, syscall, and protected call/return coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    call_ops,
    capabilities as caps,
    instructions,
    opcodes,
    reset,
    return_ops,
    state,
    syscall_demo,
)
from .memory import TaggedMemory


JsonValue = Any

CALL_SITE = 0x1000
CALL_ENTRY = 0x1800
RETURN_STACK_BASE = 0x3000
RETURN_STACK_TOP = 0x3100
RETURN_STACK_ANCHOR = 0x3040
RETURN_STACK_SLOT = 0x303C
CALL_ENTRY_REGISTER = 2

RTL_CONTROL_TRAP_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_control_trap_core.sv"),
    Path("rtl/cpu_v01_control_trap_tb.sv"),
)
RTL_CONTROL_TRAP_DOC = Path("docs/implementation/rtl-control-trap-slice.md")

CONTROL_TRAP_MNEMONICS = ("CALLC", "RET", "SYS", "SCALL", "IRET")
DEFERRED_MNEMONICS = ("WFI",)


@dataclass(frozen=True)
class RtlControlTrapCoverageRow:
    case_id: str
    category: str
    mnemonic: str
    source_mnemonic: str
    opcode_id: int
    size_bits: int
    normal_valid: bool
    fault_cause: str | None = None
    capcause: str | None = None
    fault_cap_idx: str | None = None
    fault_tval: int | None = None
    trap_entered: bool = False
    trap_frame_saved: bool = False
    trap_frame_restored: bool = False
    saved_epcc_cursor: int | None = None
    saved_epcc_slot: int | None = None
    return_epcc_cursor: int | None = None
    return_epcc_slot: int | None = None
    service_number: int | None = None
    syscall_status: str | None = None
    return_d0: int | None = None
    return_d1: int | None = None
    return_c0_cursor: int | None = None
    final_user_mode: bool | None = None
    pcc_update_cursor: int | None = None
    pcc_update_slot: int | None = None
    rsc_cursor_after: int | None = None
    return_stack_effect: str = "none"
    memory_effect_address: int | None = None
    memory_tag_write: bool | None = None

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "mnemonic": self.mnemonic,
            "source_mnemonic": self.source_mnemonic,
            "opcode_id": self.opcode_id,
            "size_bits": self.size_bits,
            "normal_valid": self.normal_valid,
            "fault_cause": self.fault_cause,
            "capcause": self.capcause,
            "fault_cap_idx": self.fault_cap_idx,
            "fault_tval": self.fault_tval,
            "trap_entered": self.trap_entered,
            "trap_frame_saved": self.trap_frame_saved,
            "trap_frame_restored": self.trap_frame_restored,
            "saved_epcc_cursor": self.saved_epcc_cursor,
            "saved_epcc_slot": self.saved_epcc_slot,
            "return_epcc_cursor": self.return_epcc_cursor,
            "return_epcc_slot": self.return_epcc_slot,
            "service_number": self.service_number,
            "syscall_status": self.syscall_status,
            "return_d0": self.return_d0,
            "return_d1": self.return_d1,
            "return_c0_cursor": self.return_c0_cursor,
            "final_user_mode": self.final_user_mode,
            "pcc_update_cursor": self.pcc_update_cursor,
            "pcc_update_slot": self.pcc_update_slot,
            "rsc_cursor_after": self.rsc_cursor_after,
            "return_stack_effect": self.return_stack_effect,
            "memory_effect_address": self.memory_effect_address,
            "memory_tag_write": self.memory_tag_write,
        }


def control_trap_mnemonics() -> tuple[str, ...]:
    return CONTROL_TRAP_MNEMONICS


def control_trap_case_ids() -> tuple[str, ...]:
    return tuple(row.case_id for row in control_trap_coverage_rows())


def control_trap_coverage_rows() -> tuple[RtlControlTrapCoverageRow, ...]:
    report = syscall_demo.run_syscall_demo()
    return (
        _callc_success_row(),
        _callc_fault_row(),
        _ret_success_row(),
        _ret_underflow_row(),
        _ret_permission_row(),
        _sys_trap_row(report, source_mnemonic="SYS"),
        _sys_trap_row(report, source_mnemonic="SCALL"),
        _syscall_return_row(report),
    )


def control_trap_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in control_trap_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def control_trap_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CONTROL_TRAP_SOURCE_FILES)
    return f"verilator --binary --timing --top-module cpu_v01_control_trap_tb {sources}"


def validate_rtl_control_trap_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CONTROL_TRAP_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL control/trap source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_control_trap_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_control_trap_tb.sv")
    doc = _read_if_exists(root / RTL_CONTROL_TRAP_DOC)

    for token in _required_package_tokens():
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_control_trap_core",
        "ST_CALLC_ENTRY",
        "ST_CALLC_TAG_FAULT",
        "ST_RET_POP",
        "ST_RET_UNDERFLOW",
        "ST_RET_PERMISSION_FAULT",
        "ST_SYS_TRAP",
        "ST_SCALL_TRAP_ALIAS",
        "ST_SYSCALL_FRAME_SAVE",
        "ST_SYSCALL_FRAME_RESTORE",
        "ST_IRET_USER_RETURN",
        "retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH",
        "retire_packet_q.trap_frame_save_valid <= 1'b1",
        "retire_packet_q.trap_frame_restore_valid <= 1'b1",
        "retire_packet_q.syscall_service_valid <= 1'b1",
        "retire_packet_q.syscall_return_valid <= 1'b1",
        "start_fault_packet(OPC_SCALL_12, 8'd12, EXC_SYSCALL_TRAP)",
        "start_fault_packet(OPC_RET_12, 8'd12, EXC_RETURN_STACK_UNDERFLOW)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_control_trap_core.sv missing {token}")

    for token in (
        "module cpu_v01_control_trap_tb",
        "CALLC entry protected-stack result mismatch",
        "CALLC entry fault result mismatch",
        "RET pop result mismatch",
        "RET protected pop fault result mismatch",
        "SYS/SCALL trap-frame save result mismatch",
        "syscall frame restore result mismatch",
        "IRET user return result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_control_trap_tb.sv missing {token}")

    rows = control_trap_coverage_rows()
    by_case = {row.case_id: row for row in rows}
    callc = by_case["callc.entry_success"]
    if (
        callc.pcc_update_cursor != CALL_ENTRY
        or callc.rsc_cursor_after != RETURN_STACK_SLOT
        or callc.return_stack_effect != "push"
    ):
        issues.append("CALLC success row must unseal entry and push return stack")
    callc_fault = by_case["callc.entry_tag_fault"]
    if (
        callc_fault.fault_cause != "CAPABILITY_TAG_FAULT"
        or callc_fault.fault_cap_idx != "C2"
    ):
        issues.append("CALLC fault row must report C2 tag failure")
    ret = by_case["ret.pop_success"]
    if ret.pcc_update_cursor != CALL_ENTRY or ret.rsc_cursor_after != RETURN_STACK_ANCHOR:
        issues.append("RET success row must restore target and advance RSC")
    ret_underflow = by_case["ret.pop_underflow_tag"]
    if (
        ret_underflow.fault_cause != "RETURN_STACK_UNDERFLOW"
        or ret_underflow.capcause != "TAG"
    ):
        issues.append("RET underflow row must report a tag underflow")
    ret_permission = by_case["ret.unprotected_permission_fault"]
    if ret_permission.fault_cause != "RETURN_STACK_PERMISSION_FAULT":
        issues.append("RET permission row must report protected-storage permission fault")
    sys = by_case["sys.sys_trap_frame_save"]
    scall = by_case["sys.scall_alias_trap_frame_save"]
    if not sys.trap_entered or not sys.trap_frame_saved:
        issues.append("SYS row must enter trap and save a frame")
    if scall.opcode_id != sys.opcode_id or scall.source_mnemonic != "SCALL":
        issues.append("SCALL row must be an alias of SYS")
    syscall = by_case["syscall.ok_frame_restore_iret"]
    if (
        not syscall.trap_frame_restored
        or syscall.syscall_status != "OK"
        or syscall.final_user_mode is not True
        or syscall.return_epcc_slot != 1
    ):
        issues.append("syscall return row must restore frame and return to user slot 1")

    covered = {row.mnemonic for row in rows}
    for mnemonic in CONTROL_TRAP_MNEMONICS:
        if mnemonic not in covered:
            issues.append(f"missing control/trap projection for {mnemonic}")
    for mnemonic in DEFERRED_MNEMONICS:
        if mnemonic in covered:
            issues.append(f"{mnemonic} must stay deferred from I21-S04")
    if opcodes.opcode_form_for("SCALL") != opcodes.opcode_form_for("SYS"):
        issues.append("SCALL must stay an alias of SYS")

    for token in (
        "Story: I21-S04",
        "python tools\\rtl_control_trap_slice.py --check",
        "cpu_v01_control_trap_core.sv",
        "CALLC",
        "SCALL",
        "RETURN_STACK_UNDERFLOW",
        "syscall trap-frame",
        "remain for later stories",
    ):
        if token not in doc:
            issues.append(f"{RTL_CONTROL_TRAP_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _callc_success_row() -> RtlControlTrapCoverageRow:
    core, memory = _prepared_call_core()
    core.write_c(CALL_ENTRY_REGISTER, _entry_capability(CALL_ENTRY))
    result = call_ops.execute_call(
        core,
        memory,
        call_ops.call_instruction("CALLC", (CALL_ENTRY_REGISTER,), location=_location(core)),
    )
    effects = _normal_effects(result)
    return RtlControlTrapCoverageRow(
        "callc.entry_success",
        "call",
        "CALLC",
        "CALLC",
        opcodes.opcode_form_for("CALLC").opcode_id,
        24,
        True,
        pcc_update_cursor=effects.pcc_update.payload.cursor,
        pcc_update_slot=effects.pcc_update.slot,
        rsc_cursor_after=_ccsr_cursor(effects, "RSC"),
        return_stack_effect="push",
        memory_effect_address=_memory_effect_address(effects),
        memory_tag_write=_memory_tag_write(effects),
    )


def _callc_fault_row() -> RtlControlTrapCoverageRow:
    core, memory = _prepared_call_core()
    core.write_c(CALL_ENTRY_REGISTER, _entry_capability(CALL_ENTRY, tag=False))
    result = call_ops.execute_call(
        core,
        memory,
        call_ops.call_instruction("CALLC", (CALL_ENTRY_REGISTER,), location=_location(core)),
    )
    return _fault_row(
        "callc.entry_tag_fault",
        "call",
        "CALLC",
        "CALLC",
        result,
        24,
    )


def _ret_success_row() -> RtlControlTrapCoverageRow:
    core, memory = _prepared_ret_core(protected=True)
    memory.csc(RETURN_STACK_SLOT, _return_capability(CALL_ENTRY))
    result = return_ops.execute_return(
        core,
        memory,
        return_ops.return_instruction(location=_location(core)),
    )
    effects = _normal_effects(result)
    return RtlControlTrapCoverageRow(
        "ret.pop_success",
        "return",
        "RET",
        "RET",
        opcodes.opcode_form_for("RET").opcode_id,
        12,
        True,
        pcc_update_cursor=effects.pcc_update.payload.cursor,
        pcc_update_slot=effects.pcc_update.slot,
        rsc_cursor_after=_ccsr_cursor(effects, "RSC"),
        return_stack_effect="pop",
        memory_effect_address=RETURN_STACK_SLOT,
        memory_tag_write=True,
    )


def _ret_underflow_row() -> RtlControlTrapCoverageRow:
    core, memory = _prepared_ret_core(protected=True)
    memory.csc(RETURN_STACK_SLOT, _return_capability(CALL_ENTRY, tag=False))
    result = return_ops.execute_return(
        core,
        memory,
        return_ops.return_instruction(location=_location(core)),
    )
    return _fault_row("ret.pop_underflow_tag", "return", "RET", "RET", result, 12)


def _ret_permission_row() -> RtlControlTrapCoverageRow:
    core, memory = _prepared_ret_core(protected=False)
    memory.csc(RETURN_STACK_SLOT, _return_capability(CALL_ENTRY))
    result = return_ops.execute_return(
        core,
        memory,
        return_ops.return_instruction(location=_location(core)),
    )
    return _fault_row(
        "ret.unprotected_permission_fault",
        "return",
        "RET",
        "RET",
        result,
        12,
    )


def _sys_trap_row(
    report: syscall_demo.SyscallDemoReport,
    *,
    source_mnemonic: str,
) -> RtlControlTrapCoverageRow:
    case_id = "sys.sys_trap_frame_save"
    if source_mnemonic == "SCALL":
        case_id = "sys.scall_alias_trap_frame_save"
    return RtlControlTrapCoverageRow(
        case_id,
        "syscall",
        source_mnemonic,
        source_mnemonic,
        opcodes.opcode_form_for(source_mnemonic).opcode_id,
        12,
        False,
        fault_cause="SYSCALL_TRAP",
        trap_entered=report.trap_entry.entered,
        trap_frame_saved=True,
        saved_epcc_cursor=report.saved_frame.epcc.payload.cursor,
        saved_epcc_slot=report.saved_frame.epcc.slot,
        service_number=report.service_number,
    )


def _syscall_return_row(
    report: syscall_demo.SyscallDemoReport,
) -> RtlControlTrapCoverageRow:
    return RtlControlTrapCoverageRow(
        "syscall.ok_frame_restore_iret",
        "syscall",
        "IRET",
        "IRET",
        opcodes.opcode_form_for("IRET").opcode_id,
        24,
        report.iret_result.is_normal_retire,
        trap_frame_restored=True,
        return_epcc_cursor=report.return_frame.epcc.payload.cursor,
        return_epcc_slot=report.return_frame.epcc.slot,
        service_number=report.service_number,
        syscall_status=report.status.name,
        return_d0=report.return_d0,
        return_d1=report.return_d1,
        return_c0_cursor=report.return_c0.payload.cursor if report.return_c0.is_valid else None,
        final_user_mode=report.final_user_mode,
        pcc_update_cursor=report.final_pcc.payload.cursor,
        pcc_update_slot=report.final_pcc.slot,
    )


def _fault_row(
    case_id: str,
    category: str,
    mnemonic: str,
    source_mnemonic: str,
    result: instructions.ExecutionResult,
    size_bits: int,
) -> RtlControlTrapCoverageRow:
    if result.fault_packet is None:
        raise ValueError(f"{case_id} did not produce a fault")
    packet = result.fault_packet
    return RtlControlTrapCoverageRow(
        case_id,
        category,
        mnemonic,
        source_mnemonic,
        opcodes.opcode_form_for(mnemonic).opcode_id,
        size_bits,
        False,
        fault_cause=packet.cause.name,
        capcause=packet.capcause.name,
        fault_cap_idx=packet.fault_cap_idx.name,
        fault_tval=packet.tval,
    )


def _prepared_call_core() -> tuple[state.CoreState, TaggedMemory]:
    core = reset.cold_reset_core(0, CALL_SITE)
    memory = TaggedMemory()
    memory.protect_range(RETURN_STACK_BASE, RETURN_STACK_TOP - RETURN_STACK_BASE)
    core.install_pcc(
        state.SlottedCapability.from_capability(_executable_capability(CALL_SITE), state.SLOT_0)
    )
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], _rsc_push_capability())
    return core, memory


def _prepared_ret_core(*, protected: bool) -> tuple[state.CoreState, TaggedMemory]:
    core = reset.cold_reset_core(0, CALL_SITE)
    memory = TaggedMemory()
    if protected:
        memory.protect_range(RETURN_STACK_BASE, RETURN_STACK_TOP - RETURN_STACK_BASE)
    core.install_pcc(
        state.SlottedCapability.from_capability(_executable_capability(CALL_SITE), state.SLOT_0)
    )
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], _rsc_pop_capability())
    return core, memory


def _normal_effects(result: instructions.ExecutionResult) -> instructions.ArchitecturalEffects:
    if result.normal is None:
        raise ValueError("expected normal retire")
    return result.normal.effects


def _ccsr_cursor(effects: instructions.ArchitecturalEffects, name: str) -> int | None:
    index = state.SPECIAL_NAME_TO_CCSR_INDEX[name]
    for write_index, capability in effects.ccsr_writes:
        if write_index == index:
            return capability.payload.cursor
    return None


def _memory_effect_address(effects: instructions.ArchitecturalEffects) -> int | None:
    if not effects.memory_effects:
        return None
    effect = effects.memory_effects[0]
    return getattr(effect, "address", None)


def _memory_tag_write(effects: instructions.ArchitecturalEffects) -> bool | None:
    if not effects.memory_effects:
        return None
    effect = effects.memory_effects[0]
    capability = getattr(effect, "capability", None)
    if isinstance(capability, caps.Capability):
        return capability.tag
    return None


def _location(core: state.CoreState) -> instructions.InstructionLocation:
    return instructions.InstructionLocation(core.pcc)


def _executable_capability(cursor: int) -> caps.Capability:
    return _capability(
        cursor,
        base=CALL_SITE,
        top=0x2000,
        permissions=int(caps.CapabilityPermission.EX),
    )


def _entry_capability(cursor: int, *, tag: bool = True) -> caps.Capability:
    return _capability(
        cursor,
        base=CALL_SITE,
        top=0x2000,
        permissions=int(caps.CapabilityPermission.EX),
        tag=tag,
        otype=caps.OTYPE_ENTRY,
    )


def _return_capability(cursor: int, *, tag: bool = True) -> caps.Capability:
    return _capability(
        cursor,
        base=CALL_SITE,
        top=0x2000,
        permissions=int(caps.CapabilityPermission.EX),
        tag=tag,
        otype=caps.OTYPE_RETURN,
        flags=0,
    )


def _rsc_push_capability() -> caps.Capability:
    return _capability(
        RETURN_STACK_ANCHOR,
        base=RETURN_STACK_BASE,
        top=RETURN_STACK_TOP,
        permissions=int(
            caps.CapabilityPermission.ST
            | caps.CapabilityPermission.SC
            | caps.CapabilityPermission.SL
        ),
        flags=0,
    )


def _rsc_pop_capability() -> caps.Capability:
    return _capability(
        RETURN_STACK_SLOT,
        base=RETURN_STACK_BASE,
        top=RETURN_STACK_TOP,
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.LC),
        flags=0,
    )


def _capability(
    cursor: int,
    *,
    base: int,
    top: int,
    permissions: int,
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=flags,
    )
    return caps.Capability(payload, tag)


def _required_package_tokens() -> tuple[str, ...]:
    return (
        "OPC_CALLC_24",
        "OPC_SCALL_12",
        "OPC_RET_12",
        "OPC_SYS_12",
        "OPC_IRET_24",
        "EXC_CAPABILITY_BOUNDS_FAULT",
        "EXC_CAPABILITY_PERMISSION_FAULT",
        "EXC_CAPABILITY_SEAL_TYPE_FAULT",
        "EXC_RETURN_STACK_UNDERFLOW",
        "EXC_RETURN_STACK_OVERFLOW",
        "EXC_RETURN_STACK_PERMISSION_FAULT",
        "CAPCAUSE_NONE",
        "CAPCAUSE_TAG",
        "CAPCAUSE_BOUNDS",
        "CAPCAUSE_PERMISSION",
        "CAPCAUSE_SEAL_TYPE",
        "CAPCAUSE_LOCAL_STORE",
        "FAULT_CAP_IDX_C2",
        "FAULT_CAP_IDX_RSC",
        "trap_frame_save_valid",
        "trap_frame_restore_valid",
        "trap_frame_epcc_value",
        "trap_frame_epcc_slot",
        "trap_frame_sr_value",
        "syscall_service_valid",
        "syscall_service_number",
        "syscall_status",
        "syscall_return_valid",
        "syscall_return_d0",
        "syscall_return_d1",
        "syscall_return_c0",
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

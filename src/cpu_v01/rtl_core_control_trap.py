"""Integrated cpu_v01_core control, trap, and return helpers.

Owner stories:
- I22-S05: integrated trap, syscall, protected call, and return behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import rtl_control_trap


JsonValue = Any

RTL_CORE_CONTROL_TRAP_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_control_trap_tb.sv"),
)
RTL_CORE_CONTROL_TRAP_DOC = Path("docs/implementation/rtl-integrated-core-control-trap.md")


@dataclass(frozen=True)
class IntegratedControlTrapCoverageRow:
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


def integrated_control_trap_coverage_rows() -> tuple[IntegratedControlTrapCoverageRow, ...]:
    return tuple(
        IntegratedControlTrapCoverageRow(
            case_id=row.case_id,
            mnemonic=row.mnemonic,
            retire_effects=_retire_effects(row),
            integrated_path="cpu_v01_core.execute_decoded_packet",
        )
        for row in rtl_control_trap.control_trap_coverage_rows()
    )


def integrated_control_trap_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in integrated_control_trap_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_control_trap_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_CONTROL_TRAP_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_core_control_trap_tb {sources}"
    )


def validate_rtl_core_control_trap(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_CONTROL_TRAP_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing integrated core control/trap source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_control_trap_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_CONTROL_TRAP_DOC)

    for token in (
        "return_stack_slot_q",
        "return_stack_slot_slot_q",
        "return_stack_cap",
        "return_capability",
        "unsealed_capability",
        "next_pcc",
        "next_slot",
        "OPC_CALL_24",
        "OPC_CALLC_24",
        "OPC_RET_12",
        "OPC_SYS_12",
        "OPC_IRET_24",
        "MEM_EFFECT_RETURN_STACK_PUSH",
        "EXC_RETURN_STACK_UNDERFLOW",
        "EXC_SYSCALL_TRAP",
        "trap_entry_valid",
        "trap_frame_save_valid",
        "trap_frame_restore_valid",
        "commit_epcc_update",
        "commit_pcc_update(tvc_q, SLOT_0)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "module cpu_v01_core_control_trap_tb",
        "cpu_v01_core_control_trap_fixture",
        "CALL 0x5002",
        "CALLC C1",
        "SYS; PAUSE",
        "IRET",
        "CALLC C0 invalid tag",
        "RET with empty protected return stack",
        "integrated control/trap CALL mismatch",
        "integrated control/trap SYS mismatch",
        "integrated control/trap RET underflow mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_control_trap_tb.sv missing {token}")

    rows = integrated_control_trap_coverage_rows()
    covered = {row.mnemonic for row in rows}
    for mnemonic in rtl_control_trap.CONTROL_TRAP_MNEMONICS:
        if mnemonic not in covered:
            issues.append(f"missing integrated control/trap projection for {mnemonic}")

    by_case = {row.case_id: row for row in rows}
    if "return_stack_push" not in by_case["callc.entry_success"].retire_effects:
        issues.append("CALLC success row must identify protected return-stack push")
    if by_case["callc.entry_tag_fault"].retire_effects != ("fault:CAPABILITY_TAG_FAULT",):
        issues.append("CALLC tag fault row must identify CAPABILITY_TAG_FAULT")
    if by_case["ret.pop_underflow_tag"].retire_effects != ("fault:RETURN_STACK_UNDERFLOW",):
        issues.append("RET underflow row must identify RETURN_STACK_UNDERFLOW")
    if "trap_frame_save" not in by_case["sys.sys_trap_frame_save"].retire_effects:
        issues.append("SYS row must identify trap-frame save")
    if "trap_frame_restore" not in by_case["syscall.ok_frame_restore_iret"].retire_effects:
        issues.append("IRET/syscall row must identify trap-frame restore")

    for token in (
        "Story: I22-S05",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_control_trap_tb.sv",
        "python tools\\rtl_core_control_trap.py --check",
        "cpu_v01_core_control_trap_tb",
        "CALL",
        "CALLC",
        "RET",
        "SYS",
        "SCALL",
        "IRET",
        "RETURN_STACK_UNDERFLOW",
        "trap-frame",
        "I22-S06",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_CONTROL_TRAP_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"integrated control/trap coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _retire_effects(row: rtl_control_trap.RtlControlTrapCoverageRow) -> tuple[str, ...]:
    effects: list[str] = []
    if row.fault_cause:
        effects.append(f"fault:{row.fault_cause}")
    if row.return_stack_effect == "push":
        effects.append("return_stack_push")
    if row.return_stack_effect == "pop":
        effects.append("return_stack_pop")
    if row.pcc_update_cursor is not None:
        effects.append("pcc_update")
    if row.rsc_cursor_after is not None:
        effects.append("ccsr_write:RSC")
    if row.trap_entered:
        effects.append("trap_entry")
    if row.trap_frame_saved:
        effects.append("trap_frame_save")
    if row.trap_frame_restored:
        effects.append("trap_frame_restore")
    if row.service_number is not None:
        effects.append("syscall_service")
    if row.syscall_status is not None:
        effects.append("syscall_return")
    if not effects:
        effects.append("normal_retire:no_write")
    return tuple(effects)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

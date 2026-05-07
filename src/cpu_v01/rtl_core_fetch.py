"""Integrated cpu_v01_core fetch/decode helpers.

Owner stories:
- I22-S02: integrated instruction fetch, slot sequencing, and decode.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import opcodes
from .instructions import InstructionSize


JsonValue = Any

RTL_CORE_FETCH_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_fetch_decode_tb.sv"),
)
RTL_CORE_FETCH_DOC = Path("docs/implementation/rtl-integrated-core-fetch-decode.md")


@dataclass(frozen=True)
class FetchDecodeCoverageRow:
    size_bits: int
    opcode_ids: tuple[int, ...]
    mnemonics: tuple[str, ...]
    placement_rule: str
    rtl_function: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "size_bits": self.size_bits,
            "opcode_ids": list(self.opcode_ids),
            "mnemonics": list(self.mnemonics),
            "placement_rule": self.placement_rule,
            "rtl_function": self.rtl_function,
        }


def fetch_decode_coverage_rows() -> tuple[FetchDecodeCoverageRow, ...]:
    forms_by_size: dict[InstructionSize, list[opcodes.OpcodeForm]] = {
        InstructionSize.BITS_12: [],
        InstructionSize.BITS_24: [],
        InstructionSize.BITS_48: [],
    }
    for form in opcodes.all_opcode_forms():
        forms_by_size[form.size].append(form)

    return (
        FetchDecodeCoverageRow(
            12,
            tuple(form.opcode_id for form in forms_by_size[InstructionSize.BITS_12]),
            tuple(form.mnemonic for form in forms_by_size[InstructionSize.BITS_12]),
            "slot 0 or slot 1 of either fetch-group cell",
            "is_12_opcode",
        ),
        FetchDecodeCoverageRow(
            24,
            tuple(form.opcode_id for form in forms_by_size[InstructionSize.BITS_24]),
            tuple(form.mnemonic for form in forms_by_size[InstructionSize.BITS_24]),
            "slot 0 of either fetch-group cell",
            "is_24_major",
        ),
        FetchDecodeCoverageRow(
            48,
            tuple(form.opcode_id for form in forms_by_size[InstructionSize.BITS_48]),
            tuple(form.mnemonic for form in forms_by_size[InstructionSize.BITS_48]),
            "slot 0 of the first fetch-group cell",
            "is_48_major",
        ),
    )


def fetch_decode_coverage_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in fetch_decode_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_fetch_decode_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_FETCH_SOURCE_FILES)
    return (
        "verilator --binary --timing --top-module "
        f"cpu_v01_core_fetch_decode_tb {sources}"
    )


def validate_rtl_core_fetch_decode(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_FETCH_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL core fetch/decode source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_fetch_decode_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_FETCH_DOC)

    if "OPC_WFI_12" not in package:
        issues.append("cpu_v01_pkg.sv missing OPC_WFI_12")

    for token in (
        "ENABLE_FETCH",
        "ST_FETCH_REQ",
        "ST_FETCH_WAIT",
        "ST_DECODE",
        "fetch_group_base",
        "imem_req_valid = fetch_enabled && state_q == ST_FETCH_REQ",
        "imem_rsp_ready = fetch_enabled && state_q == ST_FETCH_WAIT",
        "is_12_opcode",
        "is_24_major",
        "is_48_major",
        "opcode_id_for_12",
        "start_decoded_packet",
        "start_fault_packet",
        "advance_pc",
        "EXC_ALIGN_FAULT",
        "EXC_ILLEGAL_INSTRUCTION",
        "pcc_slot_q <= SLOT_1",
        "pcc_q.payload.cursor <= fetch_pc_q + 48'd2",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for form in opcodes.all_opcode_forms():
        if form.size is InstructionSize.BITS_12:
            token = f"12'h{form.opcode_id:03X}"
        else:
            token = f"8'h{form.opcode_id:02X}"
        if token not in core:
            issues.append(
                f"cpu_v01_core.sv decode table missing {form.mnemonic} {form.size.bits}-bit token {token}"
            )

    for token in (
        "module cpu_v01_core_fetch_decode_tb",
        "cpu_v01_core_fetch_decode_fixture",
        "integrated core fetch/decode legal sequence mismatch",
        "did not fault 48-bit instruction at second fetch-group cell",
        "did not fault 24-bit instruction at slot 1",
        "did not fault illegal opcode contents",
        "OPC_ADD_24",
        "OPC_PAUSE_12",
        "OPC_BRK_12",
        "OPC_CGETADDR_48",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_fetch_decode_tb.sv missing {token}")

    rows = fetch_decode_coverage_rows()
    accounted = {
        mnemonic
        for row in rows
        for mnemonic in row.mnemonics
    }
    if accounted != set(opcodes.mandatory_mnemonics()):
        missing = ", ".join(sorted(set(opcodes.mandatory_mnemonics()) - accounted))
        extra = ", ".join(sorted(accounted - set(opcodes.mandatory_mnemonics())))
        issues.append(f"fetch/decode coverage mismatch missing={missing} extra={extra}")

    for token in (
        "Story: I22-S02",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_fetch_decode_tb.sv",
        "python tools\\rtl_core_fetch_decode.py --check",
        "cpu_v01_core_fetch_decode_tb",
        "12/24/48",
        "placement",
        "illegal-instruction",
        "I22-S03",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_FETCH_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"fetch/decode coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

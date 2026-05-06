"""Scalar, branch, CSR, and CCSR SystemVerilog slice helpers.

Owner stories:
- I21-S01: RTL scalar, branch, CSR, and CCSR instruction coverage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import integer, opcodes
from .instructions import InstructionSize


JsonValue = Any

RTL_SCALAR_CONTROL_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_scalar_control_core.sv"),
    Path("rtl/cpu_v01_scalar_control_tb.sv"),
)
RTL_SCALAR_CONTROL_DOC = Path("docs/implementation/rtl-scalar-control-slice.md")

INTEGER_MNEMONICS = tuple(
    form.mnemonic
    for form in opcodes.all_opcode_forms()
    if form.mnemonic in integer.MANDATORY_INTEGER_MNEMONICS
)
CONTROL_MNEMONICS = (
    "BRA",
    "BCC",
    "JMP",
    "BRK",
    "EPCCRD",
    "EPCCWR",
    "PAUSE",
)
CSR_MNEMONICS = ("CSRRD", "CSRWR", "CSRSET", "CSRCLR")
CCSR_MNEMONICS = ("CCSRRD", "CCSRWR")
SCALAR_CONTROL_MNEMONICS = tuple(
    dict.fromkeys(
        (
            *INTEGER_MNEMONICS,
            *CONTROL_MNEMONICS,
            *CSR_MNEMONICS,
            *CCSR_MNEMONICS,
        )
    )
)

DEFERRED_MNEMONICS = (
    "LL48",
    "SC48",
    "CALL",
    "RET",
    "SYS",
    "IRET",
    "WFI",
    "CALLC",
    "FENCE",
    "FENCE.I",
    "SFENCE.VM",
    "SFENCE.VM.ASID",
    "SFENCE.VM.VA",
    "SFENCE.VM.VA_ASID",
    "CACHE.CLEAN",
    "CACHE.INVAL",
    "CACHE.CLEANINVAL",
)


@dataclass(frozen=True)
class RtlScalarControlCoverageRow:
    mnemonic: str
    family: str
    opcode_ids: tuple[int, ...]
    size_bits: tuple[int, ...]
    privilege_classes: tuple[str, ...]
    rtl_states: tuple[str, ...]
    retire_effects: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "mnemonic": self.mnemonic,
            "family": self.family,
            "opcode_ids": list(self.opcode_ids),
            "size_bits": list(self.size_bits),
            "privilege_classes": list(self.privilege_classes),
            "rtl_states": list(self.rtl_states),
            "retire_effects": list(self.retire_effects),
        }


def scalar_control_mnemonics() -> tuple[str, ...]:
    return SCALAR_CONTROL_MNEMONICS


def scalar_control_coverage_rows() -> tuple[RtlScalarControlCoverageRow, ...]:
    return tuple(_coverage_row(mnemonic) for mnemonic in SCALAR_CONTROL_MNEMONICS)


def scalar_control_projection_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in scalar_control_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def scalar_control_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_SCALAR_CONTROL_SOURCE_FILES)
    return (
        "verilator --binary --timing --top-module "
        f"cpu_v01_scalar_control_tb {sources}"
    )


def validate_rtl_scalar_control_slice(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_SCALAR_CONTROL_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing RTL scalar/control source {path.as_posix()}")

    package = _read_if_exists(root / "rtl" / "cpu_v01_pkg.sv")
    core = _read_if_exists(root / "rtl" / "cpu_v01_scalar_control_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_scalar_control_tb.sv")
    doc = _read_if_exists(root / RTL_SCALAR_CONTROL_DOC)

    for token in _required_package_tokens():
        if token not in package:
            issues.append(f"cpu_v01_pkg.sv missing {token}")

    for token in (
        "module cpu_v01_scalar_control_core",
        "ST_CPY",
        "ST_BCLR",
        "ST_BRA",
        "ST_BCC_TAKEN",
        "ST_BCC_NOT_TAKEN",
        "ST_JMP",
        "ST_EPCCRD",
        "ST_EPCCWR",
        "ST_PAUSE",
        "ST_BRK",
        "ST_CSRRD",
        "ST_CSRCLR48",
        "ST_CCSRRD",
        "ST_CCSRWR",
        "retire_packet_q.integer_write_valid <= 1'b1",
        "retire_packet_q.csr_write_valid <= 1'b1",
        "retire_packet_q.ccsr_write_valid <= 1'b1",
        "retire_packet_q.pcc_update_valid <= 1'b1",
        "retire_packet_q.epcc_update_valid <= 1'b1",
        "start_fault_packet(OPC_BRK_12, 8'd12, EXC_BREAKPOINT)",
    ):
        if token not in core:
            issues.append(f"cpu_v01_scalar_control_core.sv missing {token}")

    for token in (
        "module cpu_v01_scalar_control_tb",
        "scalar integer coverage result mismatch",
        "branch/control coverage result mismatch",
        "CSR coverage result mismatch",
        "CCSR coverage result mismatch",
        "BRK breakpoint coverage result mismatch",
        "PAUSE retire coverage result mismatch",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_scalar_control_tb.sv missing {token}")

    rows = scalar_control_coverage_rows()
    covered = {row.mnemonic for row in rows}
    expected = set(SCALAR_CONTROL_MNEMONICS)
    if covered != expected:
        missing = ", ".join(sorted(expected - covered))
        extra = ", ".join(sorted(covered - expected))
        issues.append(f"scalar/control coverage mismatch missing={missing} extra={extra}")

    for mnemonic in DEFERRED_MNEMONICS:
        if mnemonic in covered:
            issues.append(f"{mnemonic} must stay deferred from I21-S01")

    by_mnemonic = {row.mnemonic: row for row in rows}
    for mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
        row = by_mnemonic.get(mnemonic)
        if row is None or row.family != "integer":
            issues.append(f"missing integer coverage row for {mnemonic}")
    if by_mnemonic["BRK"].retire_effects != ("fault:BREAKPOINT",):
        issues.append("BRK row must identify BREAKPOINT fault effect")
    if set(by_mnemonic["CSRRD"].size_bits) != {24, 48}:
        issues.append("CSRRD row must cover 24-bit and 48-bit forms")
    if set(by_mnemonic["CSRWR"].size_bits) != {24, 48}:
        issues.append("CSRWR row must cover 24-bit and 48-bit forms")
    if by_mnemonic["CCSRWR"].retire_effects != ("ccsr_write",):
        issues.append("CCSRWR row must identify CCSR write effect")

    for token in (
        "Story: I21-S01",
        "python tools\\rtl_scalar_control_slice.py --check",
        "cpu_v01_scalar_control_core.sv",
        "CSRRD",
        "CCSRWR",
        "BRK",
    ):
        if token not in doc:
            issues.append(f"{RTL_SCALAR_CONTROL_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _coverage_row(mnemonic: str) -> RtlScalarControlCoverageRow:
    forms = opcodes.opcode_forms_for(mnemonic)
    return RtlScalarControlCoverageRow(
        mnemonic=mnemonic,
        family=_family(mnemonic),
        opcode_ids=tuple(form.opcode_id for form in forms),
        size_bits=tuple(form.size.bits for form in forms),
        privilege_classes=tuple(form.privilege.value for form in forms),
        rtl_states=_rtl_states(mnemonic, forms),
        retire_effects=_retire_effects(mnemonic),
    )


def _family(mnemonic: str) -> str:
    if mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
        return "integer"
    if mnemonic in CONTROL_MNEMONICS:
        return "control"
    if mnemonic in CSR_MNEMONICS:
        return "csr"
    if mnemonic in CCSR_MNEMONICS:
        return "ccsr"
    raise AssertionError(f"unhandled scalar/control mnemonic {mnemonic}")


def _rtl_states(
    mnemonic: str,
    forms: tuple[opcodes.OpcodeForm, ...],
) -> tuple[str, ...]:
    if mnemonic == "BCC":
        return ("ST_BCC_TAKEN", "ST_BCC_NOT_TAKEN")
    if len(forms) == 2 and {form.size for form in forms} == {
        InstructionSize.BITS_24,
        InstructionSize.BITS_48,
    }:
        return (f"ST_{mnemonic}", f"ST_{mnemonic}48")
    return (f"ST_{mnemonic}",)


def _retire_effects(mnemonic: str) -> tuple[str, ...]:
    if mnemonic in {"CMP", "CMPU", "TST"}:
        return ("csr_write:SR",)
    if mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
        return ("integer_write",)
    if mnemonic in {"BRA", "BCC", "JMP"}:
        return ("pcc_update",)
    if mnemonic == "BRK":
        return ("fault:BREAKPOINT",)
    if mnemonic == "EPCCRD":
        return ("capability_write", "integer_write:slot")
    if mnemonic == "EPCCWR":
        return ("epcc_update",)
    if mnemonic == "PAUSE":
        return ("normal_retire:no_write",)
    if mnemonic == "CSRRD":
        return ("integer_write",)
    if mnemonic == "CSRWR":
        return ("csr_write",)
    if mnemonic in {"CSRSET", "CSRCLR"}:
        return ("integer_write:old_csr", "csr_write")
    if mnemonic == "CCSRRD":
        return ("capability_write",)
    if mnemonic == "CCSRWR":
        return ("ccsr_write",)
    raise AssertionError(f"unhandled retire effects for {mnemonic}")


def _required_package_tokens() -> tuple[str, ...]:
    tokens: list[str] = [
        "EXC_BREAKPOINT",
        "CSR_SCRATCH",
        "CSR_DEBUGCTL",
        "CCSR_PCC",
        "CCSR_DSC",
        "CCSR_EPCC",
        "integer_write_valid",
        "capability_write_valid",
        "csr_write_valid",
        "ccsr_write_valid",
        "pcc_update_valid",
        "epcc_update_valid",
    ]
    for row in scalar_control_coverage_rows():
        for form in opcodes.opcode_forms_for(row.mnemonic):
            tokens.append(_opcode_token(form))
    return tuple(dict.fromkeys(tokens))


def _opcode_token(form: opcodes.OpcodeForm) -> str:
    suffix = {
        InstructionSize.BITS_12: "12",
        InstructionSize.BITS_24: "24",
        InstructionSize.BITS_48: "48",
    }[form.size]
    mnemonic = form.mnemonic.replace(".", "_")
    return f"OPC_{mnemonic}_{suffix}"


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

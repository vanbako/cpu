"""Integrated cpu_v01_core scalar/control execution helpers.

Owner stories:
- I22-S03: integrated scalar, branch, CSR, CCSR, and retire execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import rtl_scalar_control


JsonValue = Any

RTL_CORE_SCALAR_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_core_scalar_control_tb.sv"),
)
RTL_CORE_SCALAR_DOC = Path("docs/implementation/rtl-integrated-core-scalar-control.md")


@dataclass(frozen=True)
class IntegratedScalarControlCoverageRow:
    mnemonic: str
    family: str
    size_bits: tuple[int, ...]
    retire_effects: tuple[str, ...]
    integrated_path: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "mnemonic": self.mnemonic,
            "family": self.family,
            "size_bits": list(self.size_bits),
            "retire_effects": list(self.retire_effects),
            "integrated_path": self.integrated_path,
        }


def integrated_scalar_control_coverage_rows() -> tuple[IntegratedScalarControlCoverageRow, ...]:
    return tuple(
        IntegratedScalarControlCoverageRow(
            mnemonic=row.mnemonic,
            family=row.family,
            size_bits=row.size_bits,
            retire_effects=row.retire_effects,
            integrated_path="cpu_v01_core.execute_decoded_packet",
        )
        for row in rtl_scalar_control.scalar_control_coverage_rows()
    )


def integrated_scalar_control_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(row.as_dict() for row in integrated_scalar_control_coverage_rows()),
        indent=indent,
        sort_keys=True,
    )


def core_scalar_control_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in RTL_CORE_SCALAR_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_core_scalar_control_tb {sources}"
    )


def validate_rtl_core_scalar_control(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in RTL_CORE_SCALAR_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing integrated core scalar/control source {path.as_posix()}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_core_scalar_control_tb.sv")
    doc = _read_if_exists(root / RTL_CORE_SCALAR_DOC)

    for token in (
        "d_regs [INT_REG_COUNT]",
        "c_regs [CAP_REG_COUNT]",
        "csr_regs [CSR_COUNT]",
        "epcc_q",
        "dsc_q",
        "execute_decoded_packet",
        "commit_integer_write",
        "commit_capability_write",
        "commit_csr_write",
        "commit_ccsr_write",
        "commit_pcc_update",
        "commit_epcc_update",
        "mark_decoded_fault",
        "retire_packet_q.redirect_valid <= 1'b1",
        "OPC_CSRRD_48",
        "OPC_CSRWR_48",
        "OPC_CCSRRD_48",
        "OPC_CCSRWR_48",
        "OPC_BRK_12",
        "EXC_BREAKPOINT",
        "EXC_DIVIDE_BY_ZERO",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for row in rtl_scalar_control.scalar_control_coverage_rows():
        for opcode_id in row.opcode_ids:
            token = (
                f"12'h{opcode_id:03X}"
                if 12 in row.size_bits and len(row.size_bits) == 1
                else f"OPC_{row.mnemonic.replace('.', '_')}_"
            )
            if token not in core:
                issues.append(
                    f"cpu_v01_core.sv missing integrated scalar/control token for {row.mnemonic}"
                )
                break

    for token in (
        "module cpu_v01_core_scalar_control_tb",
        "cpu_v01_core_scalar_control_fixture",
        "integrated scalar/control CSRRD SR mismatch",
        "integrated scalar/control ADD mismatch",
        "integrated scalar/control CMP SR mismatch",
        "integrated scalar/control BCC should not be taken",
        "integrated scalar/control BRA redirect mismatch",
        "integrated scalar/control EPCCRD mismatch",
        "integrated scalar/control EPCCWR mismatch",
        "integrated scalar/control CCSRWR mismatch",
        "integrated scalar/control CCSRRD mismatch",
        "integrated scalar/control BRK fault mismatch",
        "OPC_PAUSE_12",
        "OPC_BRK_12",
        "OPC_CSRRD_48",
        "OPC_CCSRWR_48",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_core_scalar_control_tb.sv missing {token}")

    rows = integrated_scalar_control_coverage_rows()
    covered = {row.mnemonic for row in rows}
    expected = set(rtl_scalar_control.scalar_control_mnemonics())
    if covered != expected:
        missing = ", ".join(sorted(expected - covered))
        extra = ", ".join(sorted(covered - expected))
        issues.append(f"integrated scalar/control coverage mismatch missing={missing} extra={extra}")

    by_mnemonic = {row.mnemonic: row for row in rows}
    if by_mnemonic["BRK"].retire_effects != ("fault:BREAKPOINT",):
        issues.append("BRK row must identify BREAKPOINT no-effect fault")
    if by_mnemonic["PAUSE"].retire_effects != ("normal_retire:no_write",):
        issues.append("PAUSE row must identify no-write normal retire")
    if set(by_mnemonic["CSRRD"].size_bits) != {24, 48}:
        issues.append("CSRRD row must cover integrated fast and long forms")
    if by_mnemonic["CCSRWR"].retire_effects != ("ccsr_write",):
        issues.append("CCSRWR row must identify integrated CCSR write")

    for token in (
        "Story: I22-S03",
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_core_scalar_control_tb.sv",
        "python tools\\rtl_core_scalar_control.py --check",
        "cpu_v01_core_scalar_control_tb",
        "execute_decoded_packet",
        "integer_write",
        "csr_write",
        "ccsr_write",
        "redirect",
        "EPCCRD",
        "EPCCWR",
        "BRK",
        "I22-S04",
    ):
        if token not in doc:
            issues.append(f"{RTL_CORE_SCALAR_DOC.as_posix()} missing {token}")

    try:
        json.dumps(tuple(row.as_dict() for row in rows), sort_keys=True)
    except TypeError as exc:
        issues.append(f"integrated scalar/control coverage is not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

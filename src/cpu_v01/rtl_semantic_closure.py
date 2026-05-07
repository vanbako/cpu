"""Single-core RTL semantic closure report helpers.

Owner stories:
- I21-S06: single-core RTL semantic closure report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import golden_traces, invariants, opcodes, rtl_readiness


JsonValue = Any
RTL_SEMANTIC_CLOSURE_DOC = Path("docs/implementation/rtl-semantic-closure.md")
RTL_SEMANTIC_CLOSURE_TOOL = Path("tools/rtl_semantic_closure.py")
LOCAL_GATE_COMMANDS = (
    "python tools\\spec_reference_check.py",
    "python tools\\spec_constants_model.py",
    "python tools\\story_coverage.py --check-drift",
    "python tools\\toolchain_corpus.py --check",
    "python tools\\verilator_diff_harness.py --suite fast",
    'python -m unittest discover -s tests/conformance -p "test_*.py"',
    'python -m unittest discover -s tests/litmus -p "test_*.py"',
    "git diff --check",
)


@dataclass(frozen=True)
class InstructionFamilyClosure:
    family: str
    mnemonics: tuple[str, ...]
    rtl_stories: tuple[str, ...]
    unsupported_mnemonics: tuple[str, ...] = ()
    deferral: str = ""

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "family": self.family,
            "mnemonics": list(self.mnemonics),
            "rtl_stories": list(self.rtl_stories),
            "unsupported_mnemonics": list(self.unsupported_mnemonics),
            "deferral": self.deferral,
        }


@dataclass(frozen=True)
class GoldenCaseClosure:
    case_id: str
    category: str
    packet_count: int
    rtl_status: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "packet_count": self.packet_count,
            "rtl_status": self.rtl_status,
        }


@dataclass(frozen=True)
class InvariantClosure:
    key: str
    area: str
    implementation_story: str
    summary: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "key": self.key,
            "area": self.area,
            "implementation_story": self.implementation_story,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class RtlSemanticClosureReport:
    status: str
    local_gate_commands: tuple[str, ...]
    instruction_families: tuple[InstructionFamilyClosure, ...]
    golden_cases: tuple[GoldenCaseClosure, ...]
    invariants: tuple[InvariantClosure, ...]
    unsupported_mnemonics: tuple[str, ...]
    deferrals: tuple[str, ...]
    readiness_criteria: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "local_gate_commands": list(self.local_gate_commands),
            "instruction_families": [
                family.as_dict() for family in self.instruction_families
            ],
            "golden_cases": [case.as_dict() for case in self.golden_cases],
            "invariants": [invariant.as_dict() for invariant in self.invariants],
            "unsupported_mnemonics": list(self.unsupported_mnemonics),
            "deferrals": list(self.deferrals),
            "readiness_criteria": list(self.readiness_criteria),
        }


def rtl_semantic_closure_report() -> RtlSemanticClosureReport:
    readiness = rtl_readiness.rtl_readiness_report()
    unsupported = readiness.unsupported_mnemonics
    return RtlSemanticClosureReport(
        status="single-core fixture-slice semantic closure published",
        local_gate_commands=LOCAL_GATE_COMMANDS,
        instruction_families=_instruction_families(unsupported),
        golden_cases=tuple(
            GoldenCaseClosure(
                row.case_id,
                row.category,
                row.packet_count,
                row.rtl_status,
            )
            for row in readiness.golden_coverage
        ),
        invariants=tuple(
            InvariantClosure(
                check.key,
                check.area.value,
                check.implementation_story,
                check.summary,
            )
            for check in invariants.invariant_checks()
        ),
        unsupported_mnemonics=unsupported,
        deferrals=readiness.known_deferrals,
        readiness_criteria=(
            "`python tools\\local_checks.py` passes, including the fast Verilator regression gate.",
            "Mandatory unsupported mnemonics are limited to documented deferrals.",
            "Golden retire cases have an RTL status or explicit semantic-only status.",
            "Security and precision invariants are mapped to conformance artifacts.",
            "Integrated multicore/fabric RTL starts only after `cpu_v01_core` exists and the deferred interfaces are modeled.",
        ),
    )


def rtl_semantic_closure_json(*, indent: int = 2) -> str:
    return json.dumps(rtl_semantic_closure_report().as_dict(), indent=indent, sort_keys=True)


def render_rtl_semantic_closure_markdown(
    report: RtlSemanticClosureReport | None = None,
) -> str:
    if report is None:
        report = rtl_semantic_closure_report()
    lines = [
        "# RTL Semantic Closure Report",
        "",
        "Story: I21-S06",
        "",
        f"Status: {report.status}",
        "",
        "This is the single-core RTL semantic closure boundary for CPU v0.1. It",
        "summarizes what the fixture RTL slices cover, what remains deferred, and",
        "which local gates must pass before starting multicore or fabric RTL.",
        "",
        "## Local Gates",
        "",
    ]
    lines.extend(f"- `{command}`" for command in report.local_gate_commands)

    lines.extend(
        [
            "",
            "## Instruction Families",
            "",
            "| Family | Mnemonics | RTL stories | Unsupported | Deferral |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for family in report.instruction_families:
        lines.append(
            "| "
            f"{family.family} | {_csv_code(family.mnemonics)} | "
            f"{_csv_code(family.rtl_stories)} | "
            f"{_csv_code(family.unsupported_mnemonics)} | "
            f"{family.deferral or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Golden Cases",
            "",
            "| Case | Category | Packets | RTL status |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for case in report.golden_cases:
        lines.append(
            f"| `{case.case_id}` | `{case.category}` | {case.packet_count} | {case.rtl_status} |"
        )

    lines.extend(
        [
            "",
            "## Invariants",
            "",
            "| Key | Area | Story | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for invariant in report.invariants:
        lines.append(
            f"| `{invariant.key}` | `{invariant.area}` | `{invariant.implementation_story}` | {invariant.summary} |"
        )

    lines.extend(["", "## Unsupported Deferrals", ""])
    lines.append(
        "Mandatory mnemonics without a single-core RTL slice: "
        + _csv_code(report.unsupported_mnemonics)
        + "."
    )
    lines.extend(f"- {item}" for item in report.deferrals)

    lines.extend(["", "## Readiness Criteria", ""])
    lines.extend(f"- {criterion}" for criterion in report.readiness_criteria)

    lines.extend(
        [
            "",
            "## Acceptance Review",
            "",
            "| Acceptance criterion | Result |",
            "| --- | --- |",
            "| Mandatory instruction families are mapped. | Met. |",
            "| Golden cases are mapped. | Met. |",
            "| Invariants are mapped. | Met. |",
            "| Unsupported deferrals are explicit. | Met. |",
            "| Local gate commands and multicore/fabric readiness criteria are listed. | Met. |",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_rtl_semantic_closure(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    report = rtl_semantic_closure_report()
    issues: list[str] = []

    mandatory = set(opcodes.mandatory_mnemonics())
    accounted = {
        mnemonic
        for family in report.instruction_families
        for mnemonic in (*family.mnemonics, *family.unsupported_mnemonics)
        if mnemonic in mandatory
    }
    if accounted != mandatory:
        missing = ", ".join(sorted(mandatory - accounted))
        extra = ", ".join(sorted(accounted - mandatory))
        issues.append(f"mandatory mnemonic closure mismatch missing={missing} extra={extra}")

    expected_unsupported = set(rtl_readiness.rtl_readiness_report().unsupported_mnemonics)
    if set(report.unsupported_mnemonics) != expected_unsupported:
        issues.append("closure unsupported mnemonics must mirror RTL readiness")
    if set(report.unsupported_mnemonics) != {
        "CINCADDR",
        "CSETBOUNDS",
        "CSEAL",
        "CUNSEAL",
        "WFI",
    }:
        issues.append("single-core closure deferrals must be the final documented set")

    if not any("verilator_diff_harness.py --suite fast" in command for command in report.local_gate_commands):
        issues.append("closure local gates must include the fast Verilator regression gate")
    if not report.golden_cases:
        issues.append("closure report must map golden cases")
    if not report.invariants:
        issues.append("closure report must map invariants")
    for key in ("capability_monotonicity", "tag_non_forgery", "precise_fault_effects"):
        if key not in {invariant.key for invariant in report.invariants}:
            issues.append(f"closure report missing invariant {key}")

    rendered = render_rtl_semantic_closure_markdown(report)
    for token in (
        "Story: I21-S06",
        "Instruction Families",
        "Golden Cases",
        "Invariants",
        "Unsupported Deferrals",
        "Readiness Criteria",
        "multicore/fabric",
        "CINCADDR",
        "WFI",
    ):
        if token not in rendered:
            issues.append(f"rendered closure report missing {token}")

    for path in (RTL_SEMANTIC_CLOSURE_DOC, RTL_SEMANTIC_CLOSURE_TOOL):
        if not (root / path).exists():
            issues.append(f"missing closure artifact {path.as_posix()}")

    doc_path = root / RTL_SEMANTIC_CLOSURE_DOC
    if doc_path.exists():
        doc = doc_path.read_text(encoding="utf-8")
        for token in (
            "Story: I21-S06",
            "python tools\\rtl_semantic_closure.py --check",
            "Instruction Families",
            "Golden Cases",
            "Invariants",
            "Unsupported Deferrals",
            "Readiness Criteria",
        ):
            if token not in doc:
                issues.append(f"{RTL_SEMANTIC_CLOSURE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(report.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"closure report is not JSON serializable: {exc}")

    return tuple(issues)


def _instruction_families(
    unsupported: tuple[str, ...],
) -> tuple[InstructionFamilyClosure, ...]:
    unsupported_set = set(unsupported)
    return (
        InstructionFamilyClosure(
            "integer",
            (
                "CPY",
                "NEG",
                "ADD",
                "ADDU",
                "SUB",
                "SUBU",
                "MUL",
                "MULU",
                "DIV",
                "DIVU",
                "MOD",
                "MODU",
                "NOT",
                "AND",
                "OR",
                "XOR",
                "SHL",
                "SHRS",
                "SHRU",
                "ROL",
                "ROR",
                "CMP",
                "CMPU",
                "TST",
                "SETCC",
                "CMOVCC",
                "BSET",
                "BCLR",
            ),
            ("I21-S01",),
        ),
        InstructionFamilyClosure(
            "memory-tag",
            ("LD48", "ST48", "CLC", "CSC", "LL48", "SC48"),
            ("I20-S06", "I21-S03"),
        ),
        InstructionFamilyClosure(
            "capability-derivation",
            ("CMOVE", "CGETADDR", "CSETADDR", "CANDPERM"),
            ("I20-S06",),
            tuple(mnemonic for mnemonic in ("CINCADDR", "CSETBOUNDS", "CSEAL", "CUNSEAL") if mnemonic in unsupported_set),
            "Remaining derivation forms stay semantic/property covered until the integrated RTL decoder and capability ALU are widened.",
        ),
        InstructionFamilyClosure(
            "control-trap",
            (
                "BRA",
                "BCC",
                "CALL",
                "RET",
                "JMP",
                "BRK",
                "SYS",
                "IRET",
                "EPCCRD",
                "EPCCWR",
                "PAUSE",
                "CALLC",
            ),
            ("I20-S07", "I21-S01", "I21-S04"),
            tuple(mnemonic for mnemonic in ("WFI",) if mnemonic in unsupported_set),
            "WFI waits for interrupt-controller RTL and integrated sleep/wakeup timing.",
        ),
        InstructionFamilyClosure(
            "system-ordering-csr",
            (
                "FENCE",
                "FENCE.I",
                "SFENCE.VM",
                "SFENCE.VM.ASID",
                "SFENCE.VM.VA",
                "SFENCE.VM.VA_ASID",
                "CSRRD",
                "CSRWR",
                "CSRSET",
                "CSRCLR",
                "CCSRRD",
                "CCSRWR",
            ),
            ("I21-S01", "I21-S02", "I21-S03"),
        ),
        InstructionFamilyClosure(
            "cache-maintenance",
            ("CACHE.CLEAN", "CACHE.INVAL", "CACHE.CLEANINVAL"),
            ("I21-S03",),
        ),
    )


def _csv_code(values: tuple[str, ...]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{value}`" for value in values)

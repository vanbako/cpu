"""RTL readiness gap report inventory.

Owner stories:
- I20-S04: Verilator differential harness skeleton.
- I20-S07: precise fault, trap, and protected-stack RTL gates.
- I20-S08: RTL readiness gap report and CI command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    golden_traces,
    opcodes,
    rtl_cap_mem,
    rtl_fault_trap,
    rtl_mmu_tlb,
    rtl_smoke,
    rtl_scalar_control,
)


JsonValue = Any
RTL_GATE_COMMAND = "python tools\\local_checks.py"
RTL_READINESS_DOC = Path("docs/implementation/rtl-readiness-gap-report.md")

RTL_SLICE_CHECK_COMMANDS = (
    "python tools\\rtl_smoke_slice.py --check",
    "python tools\\rtl_cap_mem_slice.py --check",
    "python tools\\rtl_fault_trap_slice.py --check",
    "python tools\\rtl_scalar_control_slice.py --check",
    "python tools\\rtl_mmu_tlb_slice.py --check",
    "python tools\\verilator_diff_harness.py",
)

SUPPORTED_RTL_CASE_MNEMONICS = frozenset(
    {
        "ADD",
        "DIV",
        "LD48",
        "ST48",
        "CLC",
        "CSC",
        "CMOVE",
        "CGETADDR",
        "CSETADDR",
        "CANDPERM",
        "CALL",
        "RET",
        "SYS",
        "IRET",
        *rtl_scalar_control.scalar_control_mnemonics(),
        *rtl_mmu_tlb.mmu_tlb_mnemonics(),
    }
)

PARTIAL_SUPPORT_NOTES = (
    "RTL is fixture-slice based; there is no integrated general-purpose CPU core yet.",
    "`I21-S01` expands scalar, branch, CSR, and CCSR coverage as a deterministic slice; full decode and issue remain deferred.",
    "`I21-S02` expands RADIX4, TLB, SATP, ASID, page-fault, and SFENCE coverage as a deterministic slice; integrated page-walker ports remain deferred.",
    "`CALL`/`RET` cover direct protected-stack transactions; `CALLC` and broader call hazards remain deferred.",
    "`SYS`/`IRET` cover direct synchronous trap entry and restore; interrupts and debug monitor entry remain deferred.",
)

KNOWN_DEFERRALS = (
    "Multicore execution.",
    "L1/L2 caches and noncoherent DMA.",
    "Integrated page-table walker ports, remote TLB shootdown, and MMU replay timing.",
    "Interrupt controller and MMIO device model.",
    "Branch predictor performance behavior.",
    "Firmware/kernel boot beyond fixtures needed by the golden corpus.",
    "Atomics, LL/SC reservations, fences, and cache-maintenance execution.",
    "Debug halt, single-step, and debug-monitor RTL entry.",
    "Full binary decoder, issue, hazard, replay, and external memory integration.",
)

UNSUPPORTED_INTERFACES = (
    "No integrated `cpu_v01_core` top-level is implemented.",
    "`cpu_v01_imem_if`, `cpu_v01_dmem_if`, and `cpu_v01_tagmem_if` are contract surfaces, not live ports in the slice RTL.",
    "Verilator run/build remains a harness boundary; observed trace comparison is supported when a trace file is provided.",
    "Interrupt, debug, MMIO, DMA, and secondary-core external inputs are not represented by slice RTL.",
    "Cache, coherence, integrated page-table walker, and remote TLB shootdown ports are deferred.",
)


@dataclass(frozen=True)
class RtlSurface:
    story: str
    title: str
    artifacts: tuple[str, ...]
    golden_cases: tuple[str, ...] = ()
    mnemonics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "title": self.title,
            "artifacts": list(self.artifacts),
            "golden_cases": list(self.golden_cases),
            "mnemonics": list(self.mnemonics),
        }


@dataclass(frozen=True)
class GoldenCoverageRow:
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
class VerilatorFixtureCommand:
    name: str
    top_module: str
    source_files: tuple[str, ...]
    command: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "top_module": self.top_module,
            "source_files": list(self.source_files),
            "command": self.command,
        }


@dataclass(frozen=True)
class RtlReadinessReport:
    gate_command: str
    slice_check_commands: tuple[str, ...]
    verilator_fixture_commands: tuple[VerilatorFixtureCommand, ...]
    implemented_surfaces: tuple[RtlSurface, ...]
    golden_coverage: tuple[GoldenCoverageRow, ...]
    unsupported_mnemonics: tuple[str, ...]
    partial_support_notes: tuple[str, ...]
    known_deferrals: tuple[str, ...]
    unsupported_interfaces: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "gate_command": self.gate_command,
            "slice_check_commands": list(self.slice_check_commands),
            "verilator_fixture_commands": [
                fixture.as_dict() for fixture in self.verilator_fixture_commands
            ],
            "implemented_surfaces": [
                surface.as_dict() for surface in self.implemented_surfaces
            ],
            "golden_coverage": [row.as_dict() for row in self.golden_coverage],
            "unsupported_mnemonics": list(self.unsupported_mnemonics),
            "partial_support_notes": list(self.partial_support_notes),
            "known_deferrals": list(self.known_deferrals),
            "unsupported_interfaces": list(self.unsupported_interfaces),
        }


def rtl_readiness_report() -> RtlReadinessReport:
    """Return the current I20-S08 RTL readiness inventory."""
    return RtlReadinessReport(
        gate_command=RTL_GATE_COMMAND,
        slice_check_commands=RTL_SLICE_CHECK_COMMANDS,
        verilator_fixture_commands=_verilator_fixture_commands(),
        implemented_surfaces=_implemented_surfaces(),
        golden_coverage=_golden_coverage(),
        unsupported_mnemonics=_unsupported_mnemonics(),
        partial_support_notes=PARTIAL_SUPPORT_NOTES,
        known_deferrals=KNOWN_DEFERRALS,
        unsupported_interfaces=UNSUPPORTED_INTERFACES,
    )


def rtl_readiness_report_json(*, indent: int = 2) -> str:
    return json.dumps(rtl_readiness_report().as_dict(), indent=indent, sort_keys=True)


def render_rtl_readiness_markdown(report: RtlReadinessReport | None = None) -> str:
    if report is None:
        report = rtl_readiness_report()

    lines = [
        "# RTL Readiness Gap Report",
        "",
        "Story: I20-S08",
        "",
        "Status: Draft readiness gate",
        "",
        "This report is the current boundary for future RTL commits. The RTL",
        "surface is intentionally fixture-slice based: it proves selected retire",
        "packet paths against the semantic golden corpus, but it is not yet a",
        "complete CPU implementation.",
        "",
        "## Gate Command",
        "",
        "Run this before future RTL commits:",
        "",
        "```text",
        report.gate_command,
        "```",
        "",
        "Slice-specific checks covered by the gate through conformance tests:",
        "",
    ]
    lines.extend(f"- `{command}`" for command in report.slice_check_commands)

    lines.extend(
        [
            "",
            "Verilator fixture build commands for the current self-checking RTL slices:",
            "",
            "| Fixture | Top module | Command |",
            "| --- | --- | --- |",
        ]
    )
    for fixture in report.verilator_fixture_commands:
        lines.append(
            f"| {fixture.name} | `{fixture.top_module}` | `{fixture.command}` |"
        )

    lines.extend(
        [
            "",
            "## Implemented RTL Surface",
            "",
            "| Story | Surface | Artifacts | Golden cases | Mnemonics |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for surface in report.implemented_surfaces:
        lines.append(
            "| "
            f"`{surface.story}` | {surface.title} | {_csv_code(surface.artifacts)} | "
            f"{_csv_code(surface.golden_cases)} | {_csv_code(surface.mnemonics)} |"
        )

    lines.extend(
        [
            "",
            "## Golden Corpus Coverage",
            "",
            "| Case | Category | Packets | RTL status |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for row in report.golden_coverage:
        lines.append(
            f"| `{row.case_id}` | `{row.category}` | {row.packet_count} | {row.rtl_status} |"
        )

    lines.extend(["", "## Partial Support Notes", ""])
    lines.extend(f"- {note}" for note in report.partial_support_notes)

    lines.extend(["", "## Unsupported Instructions", ""])
    lines.append(
        "Mandatory mnemonics without an RTL golden-slice path: "
        + _csv_code(report.unsupported_mnemonics)
        + "."
    )

    lines.extend(["", "## Unsupported Interfaces", ""])
    lines.extend(f"- {item}" for item in report.unsupported_interfaces)

    lines.extend(["", "## Known Deferrals", ""])
    lines.extend(f"- {item}" for item in report.known_deferrals)

    lines.extend(
        [
            "",
            "## Acceptance Review",
            "",
            "| Acceptance criterion | Result |",
            "| --- | --- |",
            "| Implemented RTL surface is listed. | Met. |",
            "| Known deferrals are listed. | Met. |",
            "| Unsupported instructions and interfaces are listed. | Met. |",
            "| Golden corpus coverage is listed. | Met. |",
            "| Verilator fixture commands are listed. | Met. |",
            "| Local command gating future RTL commits is listed. | Met. |",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_rtl_readiness_report(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    report = rtl_readiness_report()
    issues: list[str] = []

    if report.gate_command != "python tools\\local_checks.py":
        issues.append("RTL gate command must be python tools\\local_checks.py")

    for check in (
        rtl_smoke.validate_rtl_smoke_slice,
        rtl_cap_mem.validate_rtl_cap_mem_slice,
        rtl_fault_trap.validate_rtl_fault_trap_slice,
        rtl_scalar_control.validate_rtl_scalar_control_slice,
        rtl_mmu_tlb.validate_rtl_mmu_tlb_slice,
    ):
        issues.extend(check(root))

    for fixture in report.verilator_fixture_commands:
        for source_file in fixture.source_files:
            if not (root / source_file).exists():
                issues.append(
                    f"Verilator fixture {fixture.name} references missing source {source_file}"
                )
            if source_file not in fixture.command:
                issues.append(
                    f"Verilator fixture {fixture.name} command missing {source_file}"
                )
        if f"--top-module {fixture.top_module}" not in fixture.command:
            issues.append(
                f"Verilator fixture {fixture.name} command missing top module {fixture.top_module}"
            )

    stories = {surface.story for surface in report.implemented_surfaces}
    for story in ("I20-S05", "I20-S06", "I20-S07", "I21-S01", "I21-S02"):
        if story not in stories:
            issues.append(f"missing implemented RTL surface for {story}")

    coverage_by_case = {row.case_id: row for row in report.golden_coverage}
    for case in golden_traces.golden_trace_corpus():
        if case.case_id not in coverage_by_case:
            issues.append(f"missing golden coverage row for {case.case_id}")
    if "integer_ops.add_mul" in coverage_by_case:
        status = coverage_by_case["integer_ops.add_mul"].rtl_status
        if "I21-S01" not in status:
            issues.append("integer_ops.add_mul coverage must name I21-S01")

    unsupported = set(report.unsupported_mnemonics)
    for mnemonic in ("CALLC", "WFI", "LL48", "SC48", "FENCE.I", "CACHE.CLEAN"):
        if mnemonic not in unsupported:
            issues.append(f"unsupported mnemonic list must include {mnemonic}")

    for phrase in (
        "Multicore execution.",
        "L1/L2 caches and noncoherent DMA.",
        "Integrated page-table walker ports, remote TLB shootdown, and MMU replay timing.",
        "Interrupt controller and MMIO device model.",
        "Branch predictor performance behavior.",
        "Firmware/kernel boot beyond fixtures needed by the golden corpus.",
    ):
        if phrase not in report.known_deferrals:
            issues.append(f"known deferrals must keep visible: {phrase}")

    rendered = render_rtl_readiness_markdown(report)
    for token in (
        "Story: I20-S08",
        report.gate_command,
        "Implemented RTL Surface",
        "Verilator fixture build commands",
        "Golden Corpus Coverage",
        "Unsupported Instructions",
        "Unsupported Interfaces",
        "Known Deferrals",
        "I21-S01",
        "I21-S02",
    ):
        if token not in rendered:
            issues.append(f"rendered readiness report missing {token}")

    doc_path = root / RTL_READINESS_DOC
    if doc_path.exists():
        doc = doc_path.read_text(encoding="utf-8")
        for token in (
            "Story: I20-S08",
            report.gate_command,
            "`I20-S07`",
            "`I21-S01`",
            "`I21-S02`",
        ):
            if token not in doc:
                issues.append(f"{RTL_READINESS_DOC.as_posix()} missing {token}")
    else:
        issues.append(f"missing RTL readiness doc {RTL_READINESS_DOC.as_posix()}")

    return tuple(issues)


def _verilator_fixture_commands() -> tuple[VerilatorFixtureCommand, ...]:
    return tuple(
        _verilator_fixture_command(
            name,
            top_module,
            tuple(path.as_posix() for path in source_files),
        )
        for name, top_module, source_files in (
            ("reset/add smoke", "cpu_v01_smoke_tb", rtl_smoke.RTL_SMOKE_SOURCE_FILES),
            (
                "capability/memory smoke",
                "cpu_v01_cap_mem_tb",
                rtl_cap_mem.RTL_CAP_MEM_SOURCE_FILES,
            ),
            (
                "fault/trap smoke",
                "cpu_v01_fault_trap_tb",
                rtl_fault_trap.RTL_FAULT_TRAP_SOURCE_FILES,
            ),
            (
                "scalar/control smoke",
                "cpu_v01_scalar_control_tb",
                rtl_scalar_control.RTL_SCALAR_CONTROL_SOURCE_FILES,
            ),
            (
                "MMU/TLB smoke",
                "cpu_v01_mmu_tlb_tb",
                rtl_mmu_tlb.RTL_MMU_TLB_SOURCE_FILES,
            ),
        )
    )


def _verilator_fixture_command(
    name: str,
    top_module: str,
    source_files: tuple[str, ...],
) -> VerilatorFixtureCommand:
    command = " ".join(
        (
            "verilator",
            "--binary",
            "--timing",
            "--top-module",
            top_module,
            *source_files,
        )
    )
    return VerilatorFixtureCommand(name, top_module, source_files, command)


def _implemented_surfaces() -> tuple[RtlSurface, ...]:
    return (
        RtlSurface(
            "I20-S01",
            "first-slice RTL contract",
            ("docs/implementation/rtl-first-slice-contract.md",),
        ),
        RtlSurface(
            "I20-S02",
            "semantic golden retire corpus",
            ("src/cpu_v01/golden_traces.py", "tools/golden_trace_corpus.py"),
            tuple(case.case_id for case in golden_traces.golden_trace_corpus()),
        ),
        RtlSurface(
            "I20-S03",
            "SystemVerilog package/interface contract",
            ("rtl/cpu_v01_pkg.sv", "src/cpu_v01/sv_contract.py"),
        ),
        RtlSurface(
            "I20-S04",
            "Verilator differential harness skeleton",
            ("src/cpu_v01/verilator_harness.py", "tools/verilator_diff_harness.py"),
        ),
        RtlSurface(
            "I20-S05",
            "reset, ADD, slot, and placement-fault smoke RTL",
            tuple(path.as_posix() for path in rtl_smoke.RTL_SMOKE_SOURCE_FILES),
            rtl_smoke.smoke_slice_case_ids(),
            ("ADD",),
        ),
        RtlSurface(
            "I20-S06",
            "capability register and memory/tag smoke RTL",
            tuple(path.as_posix() for path in rtl_cap_mem.RTL_CAP_MEM_SOURCE_FILES),
            rtl_cap_mem.cap_mem_slice_case_ids(),
            ("CMOVE", "CGETADDR", "CSETADDR", "CANDPERM", "CSC", "CLC", "ST48", "LD48"),
        ),
        RtlSurface(
            "I20-S07",
            "precise fault, trap, IRET, and protected-stack smoke RTL",
            tuple(path.as_posix() for path in rtl_fault_trap.RTL_FAULT_TRAP_SOURCE_FILES),
            rtl_fault_trap.fault_trap_slice_case_ids(),
            ("DIV", "SYS", "IRET", "CALL", "RET"),
        ),
        RtlSurface(
            "I21-S01",
            "scalar integer, branch/control, CSR, and CCSR smoke RTL",
            tuple(path.as_posix() for path in rtl_scalar_control.RTL_SCALAR_CONTROL_SOURCE_FILES),
            mnemonics=rtl_scalar_control.scalar_control_mnemonics(),
        ),
        RtlSurface(
            "I21-S02",
            "RADIX4, TLB, SATP, ASID, page-fault, and SFENCE smoke RTL",
            tuple(path.as_posix() for path in rtl_mmu_tlb.RTL_MMU_TLB_SOURCE_FILES),
            mnemonics=rtl_mmu_tlb.mmu_tlb_mnemonics(),
        ),
    )


def _golden_coverage() -> tuple[GoldenCoverageRow, ...]:
    case_to_status: dict[str, str] = {}
    for case_id in rtl_smoke.smoke_slice_case_ids():
        case_to_status[case_id] = "`I20-S05` RTL smoke slice"
    for case_id in rtl_cap_mem.cap_mem_slice_case_ids():
        case_to_status[case_id] = "`I20-S06` RTL capability/memory slice"
    for case_id in rtl_fault_trap.fault_trap_slice_case_ids():
        case_to_status[case_id] = "`I20-S07` RTL fault/trap slice"
    case_to_status["integer_ops.add_mul"] = "`I21-S01` RTL scalar/control slice projection"

    return tuple(
        GoldenCoverageRow(
            case.case_id,
            case.category,
            len(case.packets),
            case_to_status.get(case.case_id, "semantic-only"),
        )
        for case in golden_traces.golden_trace_corpus()
    )


def _unsupported_mnemonics() -> tuple[str, ...]:
    return tuple(
        mnemonic
        for mnemonic in opcodes.mandatory_mnemonics()
        if mnemonic not in SUPPORTED_RTL_CASE_MNEMONICS
    )


def _csv_code(values: tuple[str, ...]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{value}`" for value in values)

"""Verilator differential harness skeleton for golden retire traces.

Owner stories:
- I20-S02: semantic golden retire trace corpus.
- I20-S03: generated SystemVerilog package/interface contract.
- I20-S04: Verilator differential harness skeleton.
- I21-S05: Verilator regression-suite gate.
- I22-S08: integrated cpu_v01_core regression gate.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from . import golden_traces, sv_contract, toolchain_corpus


JsonValue = Any
RETIRE_TRACE_FILENAME = "retire_trace.json"
RTL_RUN_DEFERRED_MESSAGE = (
    "integrated cpu_v01_core top-level binary execution is deferred to the "
    "external Verilator/make runner; dry-run selection and observed-trace "
    "comparison are gateable"
)


class HarnessStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class HarnessSuite(Enum):
    FAST = "fast"
    SLOW = "slow"
    ALL = "all"


@dataclass(frozen=True)
class RegressionCase:
    case_id: str
    source: str
    suite: HarnessSuite
    description: str
    golden_trace_case_id: str = ""
    packet_count: int = 0
    top_module: str = ""
    source_files: tuple[str, ...] = ()
    deferred_reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("case_id must be a nonempty str")
        if self.source not in {"golden", "toolchain", "integrated"}:
            raise ValueError("source must be golden, toolchain, or integrated")
        object.__setattr__(self, "suite", HarnessSuite(self.suite))
        if not isinstance(self.description, str) or not self.description:
            raise ValueError("description must be a nonempty str")
        if type(self.packet_count) is not int or self.packet_count < 0:
            raise ValueError("packet_count must be a nonnegative int")
        object.__setattr__(self, "source_files", tuple(self.source_files))
        if self.source == "integrated" and not self.top_module:
            raise ValueError("integrated cases must name a top_module")
        if self.source == "integrated" and not self.source_files:
            raise ValueError("integrated cases must name source_files")

    @property
    def has_retire_trace(self) -> bool:
        return bool(self.golden_trace_case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "source": self.source,
            "suite": self.suite.value,
            "description": self.description,
            "golden_trace_case_id": self.golden_trace_case_id,
            "packet_count": self.packet_count,
            "top_module": self.top_module,
            "source_files": list(self.source_files),
            "deferred_reason": self.deferred_reason,
        }


@dataclass(frozen=True)
class TraceMismatch:
    case_id: str
    sequence: int | None
    field: str
    expected: JsonValue
    observed: JsonValue

    def message(self) -> str:
        location = self.case_id
        if self.sequence is not None:
            location = f"{location} packet {self.sequence}"
        return (
            f"{location}: {self.field} mismatch; "
            f"expected {self.expected!r}, observed {self.observed!r}"
        )


@dataclass(frozen=True)
class HarnessConfig:
    build_dir: Path
    observed_trace: Path | None = None
    observed_cases: tuple[dict[str, JsonValue], ...] | None = None
    case_ids: tuple[str, ...] = ()
    suite: HarnessSuite = HarnessSuite.ALL
    dry_run: bool = True
    verilator_executable: str = "verilator"
    require_verilator: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "build_dir", Path(self.build_dir))
        if self.observed_trace is not None:
            object.__setattr__(self, "observed_trace", Path(self.observed_trace))
        if self.observed_cases is not None:
            object.__setattr__(self, "observed_cases", tuple(self.observed_cases))
        object.__setattr__(self, "case_ids", tuple(self.case_ids))
        object.__setattr__(self, "suite", HarnessSuite(self.suite))
        if any(not isinstance(case_id, str) or not case_id for case_id in self.case_ids):
            raise ValueError("case_ids must be nonempty strings")
        if type(self.dry_run) is not bool:
            raise TypeError("dry_run must be a bool")
        if not isinstance(self.verilator_executable, str) or not self.verilator_executable:
            raise ValueError("verilator_executable must be a nonempty str")
        if type(self.require_verilator) is not bool:
            raise TypeError("require_verilator must be a bool")


@dataclass(frozen=True)
class HarnessResult:
    status: HarnessStatus
    message: str
    case_count: int = 0
    packet_count: int = 0
    mismatch: TraceMismatch | None = None
    verilator_path: str | None = None
    observed_trace: Path | None = None
    suite: HarnessSuite | None = None
    selected_case_ids: tuple[str, ...] = ()
    deferrals: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {HarnessStatus.PASSED, HarnessStatus.SKIPPED}


def regression_cases(suite: HarnessSuite = HarnessSuite.ALL) -> tuple[RegressionCase, ...]:
    suite = HarnessSuite(suite)
    golden_by_id = {case.case_id: case for case in golden_traces.golden_trace_corpus()}
    cases: list[RegressionCase] = []
    for case in golden_by_id.values():
        cases.append(
            RegressionCase(
                case.case_id,
                "golden",
                _golden_suite(case),
                case.description,
                case.case_id,
                len(case.packets),
            )
        )

    for case in toolchain_corpus.require_valid_toolchain_corpus():
        packet_count = 0
        if case.golden_trace_case_id:
            packet_count = len(golden_by_id[case.golden_trace_case_id].packets)
        cases.append(
            RegressionCase(
                case.case_id,
                "toolchain",
                _toolchain_suite(case),
                case.description,
                case.golden_trace_case_id,
                packet_count,
            )
        )

    cases.extend(_integrated_core_cases(golden_by_id))

    if suite is HarnessSuite.ALL:
        return tuple(cases)
    return tuple(case for case in cases if case.suite is suite)


def regression_case_ids(suite: HarnessSuite = HarnessSuite.ALL) -> tuple[str, ...]:
    return tuple(case.case_id for case in regression_cases(suite))


def expected_retire_cases(
    *,
    case_ids: tuple[str, ...] = (),
    suite: HarnessSuite = HarnessSuite.ALL,
) -> tuple[dict[str, JsonValue], ...]:
    selected = _select_regression_cases(case_ids=case_ids, suite=suite)
    return _expected_retire_cases_for(selected)


def integrated_core_verilator_commands(
    suite: HarnessSuite = HarnessSuite.ALL,
) -> tuple[str, ...]:
    return tuple(
        _verilator_command(case)
        for case in regression_cases(suite)
        if case.source == "integrated"
    )


def integrated_core_deferrals(
    suite: HarnessSuite = HarnessSuite.ALL,
) -> tuple[str, ...]:
    return _selected_deferrals(
        tuple(case for case in regression_cases(suite) if case.source == "integrated")
    )


def run_harness(config: HarnessConfig) -> HarnessResult:
    """Run the regression harness or skip when Verilator/RTL is unavailable."""
    corpus = golden_traces.golden_trace_corpus()
    issues = [
        *golden_traces.validate_golden_trace_corpus(corpus),
        *sv_contract.validate_systemverilog_contract(),
        *toolchain_corpus.validate_toolchain_corpus(),
    ]
    if issues:
        return HarnessResult(
            HarnessStatus.FAILED,
            "harness prerequisites failed: " + "; ".join(issues),
        )

    try:
        selected_cases = _select_regression_cases(
            case_ids=config.case_ids,
            suite=config.suite,
        )
    except KeyError as exc:
        return HarnessResult(
            HarnessStatus.FAILED,
            str(exc),
            suite=config.suite,
        )
    expected_cases = _expected_retire_cases_for(selected_cases)
    case_count = len(selected_cases)
    packet_count = sum(len(case["packets"]) for case in expected_cases)
    selected_case_ids = tuple(case.case_id for case in selected_cases)
    deferrals = _selected_deferrals(selected_cases)

    if config.observed_cases is not None or config.observed_trace is not None:
        observed = (
            config.observed_cases
            if config.observed_cases is not None
            else _load_trace_file(config.observed_trace)
        )
        assert observed is not None
        mismatch = compare_retire_traces(
            expected_cases,
            observed,
        )
        if mismatch is not None:
            return HarnessResult(
                HarnessStatus.FAILED,
                mismatch.message(),
                case_count=case_count,
                packet_count=packet_count,
                mismatch=mismatch,
                observed_trace=config.observed_trace,
                suite=config.suite,
                selected_case_ids=selected_case_ids,
                deferrals=deferrals,
            )
        return HarnessResult(
            HarnessStatus.PASSED,
            f"observed retire trace matches {len(expected_cases)} selected cases",
            case_count=case_count,
            packet_count=packet_count,
            observed_trace=config.observed_trace,
            suite=config.suite,
            selected_case_ids=selected_case_ids,
            deferrals=deferrals,
        )

    verilator_path = shutil.which(config.verilator_executable)
    if verilator_path is None:
        status = HarnessStatus.FAILED if config.require_verilator else HarnessStatus.SKIPPED
        return HarnessResult(
            status,
            f"{config.verilator_executable} not found; no RTL simulation was run",
            case_count=case_count,
            packet_count=packet_count,
            suite=config.suite,
            selected_case_ids=selected_case_ids,
            deferrals=deferrals,
        )

    if config.dry_run:
        return HarnessResult(
            HarnessStatus.PASSED,
            f"dry-run regression gate validated for {case_count} selected cases",
            case_count=case_count,
            packet_count=packet_count,
            verilator_path=verilator_path,
            suite=config.suite,
            selected_case_ids=selected_case_ids,
            deferrals=deferrals,
        )

    return HarnessResult(
        HarnessStatus.SKIPPED,
        RTL_RUN_DEFERRED_MESSAGE,
        case_count=case_count,
        packet_count=packet_count,
        verilator_path=verilator_path,
        suite=config.suite,
        selected_case_ids=selected_case_ids,
        deferrals=deferrals,
    )


def compare_retire_traces(
    expected_cases: tuple[dict[str, JsonValue], ...],
    observed_cases: tuple[dict[str, JsonValue], ...],
) -> TraceMismatch | None:
    expected_by_id = _cases_by_id(expected_cases)
    observed_by_id = _cases_by_id(observed_cases)

    for case_id, expected_case in expected_by_id.items():
        observed_case = observed_by_id.get(case_id)
        if observed_case is None:
            return TraceMismatch(case_id, None, "case", "present", "missing")

        expected_packets = expected_case.get("packets", ())
        observed_packets = observed_case.get("packets", ())
        if not isinstance(expected_packets, list) or not isinstance(observed_packets, list):
            return TraceMismatch(case_id, None, "packets", "list", type(observed_packets).__name__)
        if len(expected_packets) != len(observed_packets):
            return TraceMismatch(
                case_id,
                None,
                "packet_count",
                len(expected_packets),
                len(observed_packets),
            )

        for sequence, (expected_packet, observed_packet) in enumerate(
            zip(expected_packets, observed_packets)
        ):
            mismatch = _compare_json_values(
                case_id,
                sequence,
                "",
                expected_packet,
                observed_packet,
            )
            if mismatch is not None:
                return mismatch

    extra_cases = sorted(set(observed_by_id) - set(expected_by_id))
    if extra_cases:
        return TraceMismatch(extra_cases[0], None, "case", "absent", "present")
    return None


def harness_summary(result: HarnessResult) -> str:
    lines = [f"Status: {result.status.value}", result.message]
    if result.suite is not None:
        lines.append(f"Suite: {result.suite.value}")
    if result.case_count:
        lines.append(f"Cases: {result.case_count}")
    if result.packet_count:
        lines.append(f"Packets: {result.packet_count}")
    if result.selected_case_ids:
        lines.append("Selected cases: " + ", ".join(result.selected_case_ids))
    if result.verilator_path:
        lines.append(f"Verilator: {result.verilator_path}")
    if result.observed_trace:
        lines.append(f"Observed trace: {result.observed_trace}")
    if result.deferrals:
        lines.append("Deferrals:")
        for deferral in result.deferrals:
            lines.append(f"- {deferral}")
    return "\n".join(lines)


def _select_regression_cases(
    *,
    case_ids: tuple[str, ...],
    suite: HarnessSuite,
) -> tuple[RegressionCase, ...]:
    if case_ids:
        by_id = {case.case_id: case for case in regression_cases(HarnessSuite.ALL)}
        selected: list[RegressionCase] = []
        for case_id in case_ids:
            try:
                selected.append(by_id[case_id])
            except KeyError as exc:
                raise KeyError(f"unknown regression case ID {case_id!r}") from exc
        return tuple(selected)
    return regression_cases(suite)


def _expected_retire_cases_for(
    selected_cases: tuple[RegressionCase, ...],
) -> tuple[dict[str, JsonValue], ...]:
    golden_by_id = {
        case.case_id: case.as_dict()
        for case in golden_traces.golden_trace_corpus()
    }
    expected_cases: list[dict[str, JsonValue]] = []
    for case in selected_cases:
        if not case.golden_trace_case_id:
            continue
        expected = dict(golden_by_id[case.golden_trace_case_id])
        if case.case_id != case.golden_trace_case_id:
            expected["source_golden_case_id"] = case.golden_trace_case_id
        expected["case_id"] = case.case_id
        expected["regression_source"] = case.source
        expected["suite"] = case.suite.value
        expected_cases.append(expected)
    return tuple(expected_cases)


def _integrated_core_cases(
    golden_by_id: dict[str, golden_traces.GoldenTraceCase],
) -> tuple[RegressionCase, ...]:
    common_sources = ("rtl/cpu_v01_pkg.sv", "rtl/cpu_v01_core.sv")
    cases = (
        (
            "core.shell.reset_idle",
            HarnessSuite.FAST,
            "Integrated core reset/idle top-level smoke.",
            "",
            "cpu_v01_core_shell_tb",
            (*common_sources, "rtl/cpu_v01_core_shell_tb.sv"),
            "No retire trace is expected for the no-program shell smoke.",
        ),
        (
            "core.fetch_decode.slot1_48bit_placement",
            HarnessSuite.FAST,
            "Integrated fetch/decode placement-fault fixture.",
            "fault_cases.slot1_48bit_placement",
            "cpu_v01_core_fetch_decode_tb",
            (*common_sources, "rtl/cpu_v01_core_fetch_decode_tb.sv"),
            "",
        ),
        (
            "core.scalar.integer_ops_add_mul",
            HarnessSuite.FAST,
            "Integrated scalar/control ADD/MUL retire fixture.",
            "integer_ops.add_mul",
            "cpu_v01_core_scalar_control_tb",
            (*common_sources, "rtl/cpu_v01_core_scalar_control_tb.sv"),
            "",
        ),
        (
            "core.cap_mem.memory_tag_ops",
            HarnessSuite.SLOW,
            "Integrated capability/data/tag-memory fixture.",
            "memory_tag_ops.csc_clc_st48_ld48",
            "cpu_v01_core_cap_mem_tb",
            (*common_sources, "rtl/cpu_v01_core_cap_mem_tb.sv"),
            "",
        ),
        (
            "core.control_trap.sys_iret",
            HarnessSuite.SLOW,
            "Integrated trap-frame save and IRET fixture.",
            "traps.sys_iret_return",
            "cpu_v01_core_control_trap_tb",
            (*common_sources, "rtl/cpu_v01_core_control_trap_tb.sv"),
            "",
        ),
        (
            "core.mmu_tlb.translation_sfence",
            HarnessSuite.SLOW,
            "Integrated MMU/TLB translation and SFENCE fixture.",
            "",
            "cpu_v01_core_mmu_tlb_tb",
            (*common_sources, "rtl/cpu_v01_core_mmu_tlb_tb.sv"),
            "MMU/TLB fixture assertions are top-level checks until trace capture covers translation and TLB metadata.",
        ),
        (
            "core.atomic_cache.llsc_cache",
            HarnessSuite.SLOW,
            "Integrated LL/SC, reservation, fence, and cache-maintenance fixture.",
            "",
            "cpu_v01_core_atomic_cache_tb",
            (*common_sources, "rtl/cpu_v01_core_atomic_cache_tb.sv"),
            "Atomic/cache fixture assertions are top-level checks until trace capture covers reservation and cache metadata.",
        ),
    )
    result: list[RegressionCase] = []
    for (
        case_id,
        suite,
        description,
        golden_trace_case_id,
        top_module,
        source_files,
        deferred_reason,
    ) in cases:
        packet_count = 0
        if golden_trace_case_id:
            packet_count = len(golden_by_id[golden_trace_case_id].packets)
        result.append(
            RegressionCase(
                case_id,
                "integrated",
                suite,
                description,
                golden_trace_case_id,
                packet_count,
                top_module,
                source_files,
                deferred_reason,
            )
        )
    return tuple(result)


def _verilator_command(case: RegressionCase) -> str:
    sources = " ".join(case.source_files)
    return f"verilator --lint-only --timing --top-module {case.top_module} {sources}"


def _selected_deferrals(selected_cases: tuple[RegressionCase, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    deferrals: list[str] = []
    for case in selected_cases:
        if not case.deferred_reason or case.deferred_reason in seen:
            continue
        seen.add(case.deferred_reason)
        deferrals.append(case.deferred_reason)
    return tuple(deferrals)


def _golden_suite(case: golden_traces.GoldenTraceCase) -> HarnessSuite:
    fast_categories = {"reset_smoke", "integer_ops", "traps", "calls_returns"}
    if case.category in fast_categories and len(case.packets) <= 2:
        return HarnessSuite.FAST
    return HarnessSuite.SLOW


def _toolchain_suite(case: toolchain_corpus.ToolchainCorpusCase) -> HarnessSuite:
    if case.golden_trace_case_id and not case.linker_objects and not case.debug_objects:
        return HarnessSuite.FAST
    return HarnessSuite.SLOW


def _load_trace_file(path: Path) -> tuple[dict[str, JsonValue], ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("observed trace file must contain a JSON list of cases")
    if not all(isinstance(case, dict) for case in data):
        raise ValueError("observed trace cases must be JSON objects")
    return tuple(data)


def _cases_by_id(cases: tuple[dict[str, JsonValue], ...]) -> dict[str, dict[str, JsonValue]]:
    by_id: dict[str, dict[str, JsonValue]] = {}
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("trace case is missing case_id")
        if case_id in by_id:
            raise ValueError(f"duplicate trace case {case_id}")
        by_id[case_id] = case
    return by_id


def _compare_json_values(
    case_id: str,
    sequence: int,
    field: str,
    expected: JsonValue,
    observed: JsonValue,
) -> TraceMismatch | None:
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            return TraceMismatch(case_id, sequence, field or ".", "object", type(observed).__name__)
        for key in expected:
            child_field = f"{field}.{key}" if field else key
            if key not in observed:
                return TraceMismatch(case_id, sequence, child_field, expected[key], "missing")
            mismatch = _compare_json_values(
                case_id,
                sequence,
                child_field,
                expected[key],
                observed[key],
            )
            if mismatch is not None:
                return mismatch
        extra = sorted(set(observed) - set(expected))
        if extra:
            child_field = f"{field}.{extra[0]}" if field else extra[0]
            return TraceMismatch(case_id, sequence, child_field, "absent", observed[extra[0]])
        return None

    if isinstance(expected, list):
        if not isinstance(observed, list):
            return TraceMismatch(case_id, sequence, field, "list", type(observed).__name__)
        if len(expected) != len(observed):
            return TraceMismatch(case_id, sequence, f"{field}.length", len(expected), len(observed))
        for index, (expected_item, observed_item) in enumerate(zip(expected, observed)):
            child_field = f"{field}[{index}]"
            mismatch = _compare_json_values(
                case_id,
                sequence,
                child_field,
                expected_item,
                observed_item,
            )
            if mismatch is not None:
                return mismatch
        return None

    if expected != observed:
        return TraceMismatch(case_id, sequence, field, expected, observed)
    return None

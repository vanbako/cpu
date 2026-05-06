"""Verilator differential harness skeleton for golden retire traces.

Owner stories:
- I20-S02: semantic golden retire trace corpus.
- I20-S03: generated SystemVerilog package/interface contract.
- I20-S04: Verilator differential harness skeleton.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from . import golden_traces, sv_contract


JsonValue = Any
RETIRE_TRACE_FILENAME = "retire_trace.json"
RTL_RUN_DEFERRED_MESSAGE = (
    "RTL build/run command is intentionally deferred until an integrated "
    "cpu_v01_core top-level is implemented"
)


class HarnessStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


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
    dry_run: bool = True
    verilator_executable: str = "verilator"
    require_verilator: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "build_dir", Path(self.build_dir))
        if self.observed_trace is not None:
            object.__setattr__(self, "observed_trace", Path(self.observed_trace))
        if self.observed_cases is not None:
            object.__setattr__(self, "observed_cases", tuple(self.observed_cases))
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

    @property
    def ok(self) -> bool:
        return self.status in {HarnessStatus.PASSED, HarnessStatus.SKIPPED}


def run_harness(config: HarnessConfig) -> HarnessResult:
    """Run the skeleton harness or skip when Verilator/RTL is unavailable."""
    corpus = golden_traces.golden_trace_corpus()
    issues = [
        *golden_traces.validate_golden_trace_corpus(corpus),
        *sv_contract.validate_systemverilog_contract(),
    ]
    if issues:
        return HarnessResult(
            HarnessStatus.FAILED,
            "harness prerequisites failed: " + "; ".join(issues),
        )

    case_count = len(corpus)
    packet_count = sum(len(case.packets) for case in corpus)

    if config.observed_cases is not None or config.observed_trace is not None:
        observed = (
            config.observed_cases
            if config.observed_cases is not None
            else _load_trace_file(config.observed_trace)
        )
        assert observed is not None
        mismatch = compare_retire_traces(
            tuple(case.as_dict() for case in corpus),
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
            )
        return HarnessResult(
            HarnessStatus.PASSED,
            f"observed retire trace matches {case_count} golden cases",
            case_count=case_count,
            packet_count=packet_count,
            observed_trace=config.observed_trace,
        )

    verilator_path = shutil.which(config.verilator_executable)
    if verilator_path is None:
        status = HarnessStatus.FAILED if config.require_verilator else HarnessStatus.SKIPPED
        return HarnessResult(
            status,
            f"{config.verilator_executable} not found; no RTL simulation was run",
            case_count=case_count,
            packet_count=packet_count,
        )

    if config.dry_run:
        return HarnessResult(
            HarnessStatus.PASSED,
            f"dry-run harness boundary validated for {case_count} golden cases",
            case_count=case_count,
            packet_count=packet_count,
            verilator_path=verilator_path,
        )

    return HarnessResult(
        HarnessStatus.SKIPPED,
        RTL_RUN_DEFERRED_MESSAGE,
        case_count=case_count,
        packet_count=packet_count,
        verilator_path=verilator_path,
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
    if result.case_count:
        lines.append(f"Cases: {result.case_count}")
    if result.packet_count:
        lines.append(f"Packets: {result.packet_count}")
    if result.verilator_path:
        lines.append(f"Verilator: {result.verilator_path}")
    if result.observed_trace:
        lines.append(f"Observed trace: {result.observed_trace}")
    return "\n".join(lines)


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

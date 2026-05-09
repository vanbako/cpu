"""BRAM-resident FPGA external-memory test firmware profile.

Owner stories:
- I29-S03: add external-memory test firmware.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import cells, fpga_ddr_wrapper, fpga_debug_status, fpga_external_memory, fpga_smoke_corpus


JsonValue = Any

FPGA_EXTERNAL_MEMORY_TESTS_STORY = "I29-S03"
FPGA_EXTERNAL_MEMORY_TESTS_DOC = Path("docs/implementation/fpga-external-memory-tests.md")
FPGA_EXTERNAL_MEMORY_TESTS_TOOL = "python tools\\fpga_external_memory_tests.py --check"
FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID = "external_memory.ddr_bram_resident_test"
FPGA_EXTERNAL_MEMORY_TEST_BOARD_STATUS = "blocked_until_board_ddr_ip"
FPGA_EXTERNAL_MEMORY_TEST_EXECUTION_REGION = "bram_resident"
PROGRESS_CODE_BASE = 0x290300
PROGRESS_CODE_PASS = 0x2903F0
PROGRESS_CODE_FAIL = 0x2903FF

REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES = frozenset(
    {
        "walking_pattern",
        "address_line",
        "burst",
        "alignment",
        "fault_injection",
    }
)


@dataclass(frozen=True)
class FpgaExternalMemoryFirmwareCase:
    case_id: str
    category: str
    start_cell: int
    length_cells: int
    stride_cells: int
    pattern_seed: int
    progress_code: int
    expected_result: str
    expected_uart_signature: str
    expected_probe_signature: str
    fault_injection: str = "none"

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("external memory test case_id must not be empty")
        if self.category not in REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES:
            raise ValueError(f"unknown external memory test category {self.category!r}")
        object.__setattr__(self, "start_cell", cells.require_cell_address(self.start_cell))
        object.__setattr__(
            self,
            "length_cells",
            cells.require_positive_cell_count(self.length_cells, "length_cells"),
        )
        object.__setattr__(
            self,
            "stride_cells",
            cells.require_positive_cell_count(self.stride_cells, "stride_cells"),
        )
        object.__setattr__(
            self,
            "pattern_seed",
            cells.require_cell_value(self.pattern_seed, "pattern_seed"),
        )
        object.__setattr__(
            self,
            "progress_code",
            cells.require_cell_value(self.progress_code, "progress_code"),
        )
        if not self.expected_result:
            raise ValueError("external memory test expected_result must not be empty")
        if not self.expected_uart_signature:
            raise ValueError("external memory test expected_uart_signature must not be empty")
        if not self.expected_probe_signature:
            raise ValueError("external memory test expected_probe_signature must not be empty")

    @property
    def end_cell(self) -> int:
        return self.start_cell + self.length_cells

    @property
    def addresses(self) -> tuple[int, ...]:
        if self.category == "address_line":
            offsets = (0, 1, 2, 4, 8, 16, 32, 64)
            return tuple(self.start_cell + offset for offset in offsets)
        return tuple(
            self.start_cell + index * self.stride_cells for index in range(self.length_cells)
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "start_cell": self.start_cell,
            "end_cell": self.end_cell,
            "length_cells": self.length_cells,
            "stride_cells": self.stride_cells,
            "pattern_seed": self.pattern_seed,
            "progress_code": self.progress_code,
            "expected_result": self.expected_result,
            "expected_uart_signature": self.expected_uart_signature,
            "expected_probe_signature": self.expected_probe_signature,
            "fault_injection": self.fault_injection,
        }


@dataclass(frozen=True)
class FpgaExternalMemoryTestResult:
    case_id: str
    category: str
    passed: bool
    writes: int
    reads: int
    progress_code: int
    first_address: int
    last_address: int
    fault_observed: bool
    observation: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "passed": self.passed,
            "writes": self.writes,
            "reads": self.reads,
            "progress_code": self.progress_code,
            "first_address": self.first_address,
            "last_address": self.last_address,
            "fault_observed": self.fault_observed,
            "observation": self.observation,
        }


@dataclass(frozen=True)
class FpgaExternalMemoryTestRun:
    story: str
    program_id: str
    execution_region: str
    board_status: str
    controller_ready_required: bool
    pass_led: bool
    fail_led: bool
    status_codes: tuple[int, ...]
    results: tuple[FpgaExternalMemoryTestResult, ...]

    @property
    def passed(self) -> bool:
        return self.pass_led and not self.fail_led and all(result.passed for result in self.results)

    def result_by_id(self, case_id: str) -> FpgaExternalMemoryTestResult:
        for result in self.results:
            if result.case_id == case_id:
                return result
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "program_id": self.program_id,
            "execution_region": self.execution_region,
            "board_status": self.board_status,
            "controller_ready_required": self.controller_ready_required,
            "passed": self.passed,
            "pass_led": self.pass_led,
            "fail_led": self.fail_led,
            "status_codes": list(self.status_codes),
            "results": [result.as_dict() for result in self.results],
        }


@dataclass(frozen=True)
class FpgaExternalMemoryFirmwareProfile:
    story: str
    program_id: str
    execution_region: str
    board_status: str
    ddr_wrapper_gate: str
    smoke_corpus_gate: str
    debug_status_gate: str
    external_window_name: str
    external_window_base: int
    external_window_end: int
    required_categories: tuple[str, ...]
    cases: tuple[FpgaExternalMemoryFirmwareCase, ...]
    progress_registers: tuple[str, ...]
    handoffs: tuple[str, ...]
    blockers: tuple[str, ...]

    def case_by_id(self, case_id: str) -> FpgaExternalMemoryFirmwareCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "program_id": self.program_id,
            "execution_region": self.execution_region,
            "board_status": self.board_status,
            "ddr_wrapper_gate": self.ddr_wrapper_gate,
            "smoke_corpus_gate": self.smoke_corpus_gate,
            "debug_status_gate": self.debug_status_gate,
            "external_window_name": self.external_window_name,
            "external_window_base": self.external_window_base,
            "external_window_end": self.external_window_end,
            "required_categories": list(self.required_categories),
            "cases": [case.as_dict() for case in self.cases],
            "progress_registers": list(self.progress_registers),
            "handoffs": list(self.handoffs),
            "blockers": list(self.blockers),
        }


class ExternalMemoryAccessFault(RuntimeError):
    """Raised when the firmware model sees a CPU-owned external-memory fault."""


class _FirmwareDdrMemory:
    def __init__(
        self,
        window: cells.CellRange,
        *,
        controller_ready: bool = True,
        fault_addresses: frozenset[int] = frozenset(),
    ) -> None:
        self.window = window
        self.controller_ready = controller_ready
        self.fault_addresses = fault_addresses
        self.storage: dict[int, int] = {}
        self.reads = 0
        self.writes = 0

    def write_cell(self, address: int, value: int) -> None:
        self._check_access(address)
        self.storage[address] = cells.require_cell_value(value)
        self.writes += 1

    def read_cell(self, address: int) -> int:
        self._check_access(address)
        self.reads += 1
        return self.storage.get(address, 0)

    def write_integer(self, address: int, low_cell: int, high_cell: int) -> None:
        self._check_integer_alignment(address)
        self.write_cell(address, low_cell)
        self.write_cell(address + 1, high_cell)

    def read_integer(self, address: int) -> tuple[int, int]:
        self._check_integer_alignment(address)
        return (self.read_cell(address), self.read_cell(address + 1))

    def _check_integer_alignment(self, address: int) -> None:
        if not cells.is_aligned(address, cells.INTEGER_OBJECT_CELLS):
            raise ExternalMemoryAccessFault("external DDR integer access is not 2-cell aligned")

    def _check_access(self, address: int) -> None:
        address = cells.require_cell_address(address)
        if not self.controller_ready:
            raise ExternalMemoryAccessFault("external DDR access before controller_ready")
        if not self.window.contains_address(address):
            raise ExternalMemoryAccessFault("external DDR address is outside external_ddr_payload")
        if address in self.fault_addresses:
            raise ExternalMemoryAccessFault("injected DDR controller error")


def fpga_external_memory_tests_profile() -> FpgaExternalMemoryFirmwareProfile:
    external_profile = fpga_external_memory.fpga_external_memory_profile()
    window = external_profile.window_by_name("external_ddr_payload")
    return FpgaExternalMemoryFirmwareProfile(
        story=FPGA_EXTERNAL_MEMORY_TESTS_STORY,
        program_id=FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID,
        execution_region=FPGA_EXTERNAL_MEMORY_TEST_EXECUTION_REGION,
        board_status=FPGA_EXTERNAL_MEMORY_TEST_BOARD_STATUS,
        ddr_wrapper_gate=fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        smoke_corpus_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        debug_status_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        external_window_name=window.name,
        external_window_base=window.base_cell,
        external_window_end=window.end_cell,
        required_categories=tuple(sorted(REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES)),
        cases=_firmware_cases(window.base_cell),
        progress_registers=(
            "STATUS_LEDS software vector carries the active test phase",
            "UART/status packet pass_fail_state reports running, first_pass, failed, or blocked",
            "fault_code reports ACCESS_FAULT for alignment or injected controller faults",
            "probe bundle captures status_controller_ready_o, fail_visible_o, and progress_code",
        ),
        handoffs=(
            "I29-S04 owns cacheability, ordering, and capability-tag policy before off-BRAM execution",
            "I29-S05 archives board DDR calibration, memory-test pass/fail, UART/status, and timing evidence",
        ),
        blockers=(
            "board-specific DDR controller IP and physical pin constraints are still blocked",
            "cpu_v01_fpga_top still needs an external-memory decoder before this runs on hardware",
            "BRAM image generation for this firmware is a planned I26 image-corpus extension",
        ),
    )


def fpga_external_memory_tests_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_external_memory_tests_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def fpga_external_memory_tests_run_json(*, indent: int = 2) -> str:
    return json.dumps(run_fpga_external_memory_tests().as_dict(), indent=indent, sort_keys=True)


def run_fpga_external_memory_tests() -> FpgaExternalMemoryTestRun:
    profile = fpga_external_memory_tests_profile()
    window = cells.cell_range(
        profile.external_window_base,
        profile.external_window_end - profile.external_window_base,
    )
    status_codes: list[int] = []
    results: list[FpgaExternalMemoryTestResult] = []
    for case in profile.cases:
        status_codes.append(case.progress_code)
        result = _run_case(window, case)
        results.append(result)
    all_passed = all(result.passed for result in results)
    status_codes.append(PROGRESS_CODE_PASS if all_passed else PROGRESS_CODE_FAIL)
    return FpgaExternalMemoryTestRun(
        story=FPGA_EXTERNAL_MEMORY_TESTS_STORY,
        program_id=profile.program_id,
        execution_region=profile.execution_region,
        board_status=profile.board_status,
        controller_ready_required=True,
        pass_led=all_passed,
        fail_led=not all_passed,
        status_codes=tuple(status_codes),
        results=tuple(results),
    )


def render_fpga_external_memory_tests() -> str:
    profile = fpga_external_memory_tests_profile()
    lines = [
        "# FPGA External Memory Tests",
        "",
        f"Story: {profile.story}",
        f"Program: `{profile.program_id}`",
        f"Execution: `{profile.execution_region}`",
        f"Board status: `{profile.board_status}`",
        f"Window: `{profile.external_window_name}` "
        f"`0x{profile.external_window_base:08X}`..`0x{profile.external_window_end:08X}`",
        "",
        "## Cases",
        "",
        "| Case | Category | Progress | Expected result |",
        "| --- | --- | --- | --- |",
    ]
    for case in profile.cases:
        lines.append(
            f"| `{case.case_id}` | `{case.category}` | "
            f"`0x{case.progress_code:06X}` | {case.expected_result} |"
        )
    lines.extend(["", "## Handoffs", ""])
    lines.extend(f"- {handoff}." for handoff in profile.handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_external_memory_tests(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_external_memory_tests_profile()
    run = run_fpga_external_memory_tests()
    issues: list[str] = []

    if profile.story != FPGA_EXTERNAL_MEMORY_TESTS_STORY or run.story != FPGA_EXTERNAL_MEMORY_TESTS_STORY:
        issues.append("FPGA external-memory tests story mismatch")
    if profile.program_id != FPGA_EXTERNAL_MEMORY_TEST_PROGRAM_ID:
        issues.append("FPGA external-memory tests must publish the BRAM-resident program ID")
    if profile.execution_region != FPGA_EXTERNAL_MEMORY_TEST_EXECUTION_REGION:
        issues.append("FPGA external-memory tests must run from BRAM")
    if profile.board_status != FPGA_EXTERNAL_MEMORY_TEST_BOARD_STATUS:
        issues.append("FPGA external-memory tests must keep board status blocked until DDR IP exists")

    issues.extend(fpga_external_memory.validate_fpga_external_memory(root))
    issues.extend(fpga_ddr_wrapper.validate_fpga_ddr_wrapper(root))
    issues.extend(fpga_smoke_corpus.validate_fpga_smoke_corpus(root))
    issues.extend(fpga_debug_status.validate_fpga_debug_status(root))

    external_window = fpga_external_memory.fpga_external_memory_profile().window_by_name(
        "external_ddr_payload"
    )
    if profile.external_window_base != external_window.base_cell:
        issues.append("external-memory tests must start at external_ddr_payload base")
    if profile.external_window_end != external_window.end_cell:
        issues.append("external-memory tests must stay inside external_ddr_payload")

    case_ids = [case.case_id for case in profile.cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("external-memory test case IDs are not unique")
    categories = {case.category for case in profile.cases}
    for category in sorted(REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES - categories):
        issues.append(f"missing external-memory test category {category}")
    for category in sorted(categories - REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES):
        issues.append(f"unknown external-memory test category {category}")

    window_range = cells.cell_range(
        profile.external_window_base,
        profile.external_window_end - profile.external_window_base,
    )
    for case in profile.cases:
        if not window_range.contains_range(cells.cell_range(min(case.addresses), _address_span(case))):
            issues.append(f"{case.case_id}: addresses leave external_ddr_payload")
        if case.progress_code not in run.status_codes:
            issues.append(f"{case.case_id}: progress code missing from run status codes")
        if "UART" not in case.expected_uart_signature:
            issues.append(f"{case.case_id}: UART signature must name UART/status output")
        if "probe" not in case.expected_probe_signature.lower():
            issues.append(f"{case.case_id}: probe signature must name probe evidence")

    if not run.passed or not run.pass_led or run.fail_led:
        issues.append("external-memory test run must pass all modeled cases")
    if run.status_codes[-1] != PROGRESS_CODE_PASS:
        issues.append("external-memory test run must finish with the pass progress code")
    if not run.controller_ready_required:
        issues.append("external-memory test run must require controller_ready")
    if not run.result_by_id("fault_injection.controller_error").fault_observed:
        issues.append("fault-injection case must observe a CPU-owned fault")
    if not run.result_by_id("alignment.integer_object").fault_observed:
        issues.append("alignment case must observe the misaligned access fault")

    issues.extend(_validate_doc(root))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"external-memory test objects are not JSON serializable: {exc}")

    return tuple(issues)


def _firmware_cases(base: int) -> tuple[FpgaExternalMemoryFirmwareCase, ...]:
    return (
        FpgaExternalMemoryFirmwareCase(
            case_id="walking_pattern.low_window",
            category="walking_pattern",
            start_cell=base + 0x1000,
            length_cells=8,
            stride_cells=1,
            pattern_seed=0x5A0001,
            progress_code=PROGRESS_CODE_BASE + 0x10,
            expected_result="write/read walking 24-bit patterns with no mismatch",
            expected_uart_signature="UART/status reports walking_pattern complete and no fault_code",
            expected_probe_signature="probe observes controller_ready, readback match, and pass progress",
        ),
        FpgaExternalMemoryFirmwareCase(
            case_id="address_line.power_of_two_offsets",
            category="address_line",
            start_cell=base + 0x2000,
            length_cells=65,
            stride_cells=1,
            pattern_seed=0xA50001,
            progress_code=PROGRESS_CODE_BASE + 0x20,
            expected_result="power-of-two offsets retain independent sentinel values",
            expected_uart_signature="UART/status reports address_line complete and no alias fault",
            expected_probe_signature="probe captures distinct ext_mem_req_addr power-of-two offsets",
        ),
        FpgaExternalMemoryFirmwareCase(
            case_id="burst.contiguous_cells",
            category="burst",
            start_cell=base + 0x3000,
            length_cells=16,
            stride_cells=1,
            pattern_seed=0xB00001,
            progress_code=PROGRESS_CODE_BASE + 0x30,
            expected_result="contiguous 16-cell write/read burst preserves order",
            expected_uart_signature="UART/status reports burst complete with retire progress",
            expected_probe_signature="probe observes monotonically increasing ext_mem_req_addr during burst",
        ),
        FpgaExternalMemoryFirmwareCase(
            case_id="alignment.integer_object",
            category="alignment",
            start_cell=base + 0x4000,
            length_cells=4,
            stride_cells=2,
            pattern_seed=0xC00001,
            progress_code=PROGRESS_CODE_BASE + 0x40,
            expected_result="aligned integer LD/ST passes and misaligned integer access faults before completion",
            expected_uart_signature="UART/status reports alignment complete with expected ACCESS_FAULT sample",
            expected_probe_signature="probe shows no controller transaction for the misaligned request",
        ),
        FpgaExternalMemoryFirmwareCase(
            case_id="fault_injection.controller_error",
            category="fault_injection",
            start_cell=base + 0x5000,
            length_cells=1,
            stride_cells=1,
            pattern_seed=0xD00001,
            progress_code=PROGRESS_CODE_BASE + 0x50,
            expected_result="injected controller error becomes a CPU-owned ACCESS_FAULT and visible failure sample",
            expected_uart_signature="UART/status reports fault_injection complete with ACCESS_FAULT then recovery",
            expected_probe_signature="probe captures fail_visible_o and status_error_code_o for injected controller error",
            fault_injection="controller_error",
        ),
    )


def _run_case(
    window: cells.CellRange,
    case: FpgaExternalMemoryFirmwareCase,
) -> FpgaExternalMemoryTestResult:
    fault_addresses = (
        frozenset({case.start_cell}) if case.fault_injection == "controller_error" else frozenset()
    )
    memory = _FirmwareDdrMemory(window, fault_addresses=fault_addresses)
    fault_observed = False
    passed = True
    observation = "completed"

    try:
        if case.category == "walking_pattern":
            _run_pattern_case(memory, case)
            observation = "walking pattern readback matched"
        elif case.category == "address_line":
            _run_address_line_case(memory, case)
            observation = "address-line sentinels remained independent"
        elif case.category == "burst":
            _run_pattern_case(memory, case)
            observation = "contiguous burst readback matched"
        elif case.category == "alignment":
            _run_alignment_case(memory, case)
            fault_observed = True
            observation = "aligned integer access passed and misaligned access faulted"
        elif case.category == "fault_injection":
            try:
                memory.write_cell(case.start_cell, case.pattern_seed)
            except ExternalMemoryAccessFault:
                fault_observed = True
                observation = "injected controller fault converted to CPU-owned access fault"
            else:
                passed = False
                observation = "injected controller fault was not observed"
        else:
            passed = False
            observation = f"unknown category {case.category}"
    except ExternalMemoryAccessFault as exc:
        passed = False
        observation = str(exc)

    expected_fault = case.category in {"alignment", "fault_injection"}
    if expected_fault and not fault_observed:
        passed = False
    addresses = case.addresses
    return FpgaExternalMemoryTestResult(
        case_id=case.case_id,
        category=case.category,
        passed=passed,
        writes=memory.writes,
        reads=memory.reads,
        progress_code=case.progress_code,
        first_address=min(addresses),
        last_address=max(addresses),
        fault_observed=fault_observed,
        observation=observation,
    )


def _run_pattern_case(memory: _FirmwareDdrMemory, case: FpgaExternalMemoryFirmwareCase) -> None:
    for index, address in enumerate(case.addresses):
        memory.write_cell(address, _pattern(case.pattern_seed, index))
    for index, address in enumerate(case.addresses):
        expected = _pattern(case.pattern_seed, index)
        observed = memory.read_cell(address)
        if observed != expected:
            raise ExternalMemoryAccessFault(
                f"DDR readback mismatch at 0x{address:012X}: expected 0x{expected:06X}, got 0x{observed:06X}"
            )


def _run_address_line_case(
    memory: _FirmwareDdrMemory,
    case: FpgaExternalMemoryFirmwareCase,
) -> None:
    for index, address in enumerate(case.addresses):
        memory.write_cell(address, _pattern(case.pattern_seed, index))
    for index, address in enumerate(case.addresses):
        expected = _pattern(case.pattern_seed, index)
        observed = memory.read_cell(address)
        if observed != expected:
            raise ExternalMemoryAccessFault(
                f"DDR address-line alias at 0x{address:012X}: expected 0x{expected:06X}, got 0x{observed:06X}"
            )


def _run_alignment_case(
    memory: _FirmwareDdrMemory,
    case: FpgaExternalMemoryFirmwareCase,
) -> None:
    memory.write_integer(case.start_cell, case.pattern_seed, _pattern(case.pattern_seed, 1))
    observed = memory.read_integer(case.start_cell)
    expected = (case.pattern_seed, _pattern(case.pattern_seed, 1))
    if observed != expected:
        raise ExternalMemoryAccessFault("aligned integer DDR readback mismatch")
    try:
        memory.read_integer(case.start_cell + 1)
    except ExternalMemoryAccessFault:
        return
    raise ExternalMemoryAccessFault("misaligned integer DDR access did not fault")


def _pattern(seed: int, index: int) -> int:
    return cells.mask_cell(seed ^ ((index + 1) * 0x010101))


def _address_span(case: FpgaExternalMemoryFirmwareCase) -> int:
    addresses = case.addresses
    return (max(addresses) - min(addresses)) + 1


def _validate_doc(root: Path) -> tuple[str, ...]:
    doc = _read_if_exists(root / FPGA_EXTERNAL_MEMORY_TESTS_DOC)
    issues: list[str] = []
    for token in (
        "Story: I29-S03",
        FPGA_EXTERNAL_MEMORY_TESTS_TOOL,
        "python tools\\fpga_ddr_wrapper.py --check",
        "python tools\\fpga_smoke_corpus.py --check",
        "python tools\\fpga_debug_status_packet.py --check",
        "BRAM-resident",
        "external_ddr_payload",
        "controller_ready",
        "walking_pattern",
        "address_line",
        "burst",
        "alignment",
        "fault_injection",
        "debug/status",
        "UART/status",
        "ACCESS_FAULT",
        "I29-S04",
        "I29-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_EXTERNAL_MEMORY_TESTS_DOC.as_posix()} missing {token}")
    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

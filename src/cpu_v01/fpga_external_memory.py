"""FPGA external-memory attachment and DDR bring-up boundary profile.

Owner stories:
- I29-S01: define the external-memory attachment and DDR bring-up boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import cells, fpga_first_test, fpga_reproducible_build, fpga_soc_platform, mmu, platform


JsonValue = Any

FPGA_EXTERNAL_MEMORY_STORY = "I29-S01"
FPGA_EXTERNAL_MEMORY_DOC = Path("docs/implementation/fpga-external-memory.md")
FPGA_EXTERNAL_MEMORY_TOOL = "python tools\\fpga_external_memory.py --check"
FPGA_EXTERNAL_MEMORY_PROFILE_NAME = "cpu_v01_fpga_external_memory_boundary"
FPGA_EXTERNAL_MEMORY_STATUS = "boundary_profile"
FPGA_EXTERNAL_MEMORY_BASE = 0x0100_0000
FPGA_EXTERNAL_MEMORY_CELLS = 0x0100_0000
FPGA_EXTERNAL_MEMORY_END = FPGA_EXTERNAL_MEMORY_BASE + FPGA_EXTERNAL_MEMORY_CELLS


_MEMORY_TYPE_NAMES = {
    mmu.MEMORY_TYPE_NORMAL_COHERENT: "normal_coherent",
    mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE: "normal_uncacheable",
    mmu.MEMORY_TYPE_DEVICE_ORDERED: "device_ordered",
}


@dataclass(frozen=True)
class ExternalMemoryWindow:
    name: str
    base_cell: int
    size_cells: int
    memory_type: int
    cacheability: str
    access_policy: str
    tag_policy: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("external memory window name must not be empty")
        object.__setattr__(self, "base_cell", cells.require_cell_address(self.base_cell))
        object.__setattr__(
            self,
            "size_cells",
            cells.require_positive_cell_count(self.size_cells, "size_cells"),
        )
        if self.end_cell > cells.ADDRESS_SPACE_CELLS:
            raise ValueError("external memory window exceeds the address space")
        if self.memory_type not in _MEMORY_TYPE_NAMES:
            raise ValueError("external memory window has an unsupported memory type")
        if not self.cacheability:
            raise ValueError("external memory window cacheability must not be empty")
        if not self.access_policy:
            raise ValueError("external memory window access_policy must not be empty")
        if not self.tag_policy:
            raise ValueError("external memory window tag_policy must not be empty")

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    @property
    def memory_type_name(self) -> str:
        return _MEMORY_TYPE_NAMES[self.memory_type]

    def overlaps_platform_region(self, region: platform.MemoryRegion) -> bool:
        return self.base_cell < region.end and region.base < self.end_cell

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "memory_type": self.memory_type,
            "memory_type_name": self.memory_type_name,
            "cacheability": self.cacheability,
            "access_policy": self.access_policy,
            "tag_policy": self.tag_policy,
        }


@dataclass(frozen=True)
class BoundarySignal:
    name: str
    direction: str
    width: str
    owner: str
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("boundary signal name must not be empty")
        if self.direction not in {"in", "out", "inout"}:
            raise ValueError("boundary signal direction must be in, out, or inout")
        if not self.width:
            raise ValueError("boundary signal width must not be empty")
        if not self.owner:
            raise ValueError("boundary signal owner must not be empty")
        if not self.purpose:
            raise ValueError("boundary signal purpose must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "width": self.width,
            "owner": self.owner,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class CalibrationStatusField:
    name: str
    width_bits: int
    access: str
    reset_value: int
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("calibration status name must not be empty")
        if type(self.width_bits) is not int or self.width_bits <= 0 or self.width_bits > 48:
            raise ValueError("calibration status width_bits must be in 1..48")
        if self.access not in {"ro", "wo", "rw", "w1c"}:
            raise ValueError("calibration status access must be ro, wo, rw, or w1c")
        if type(self.reset_value) is not int or self.reset_value < 0:
            raise ValueError("calibration status reset_value must be a nonnegative int")
        if not self.purpose:
            raise ValueError("calibration status purpose must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "width_bits": self.width_bits,
            "access": self.access,
            "reset_value": self.reset_value,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class ExternalMemoryFaultRule:
    name: str
    owner: str
    condition: str
    architectural_result: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("external memory fault name must not be empty")
        if self.owner != "CPU":
            raise ValueError("external memory architectural faults must be CPU-owned")
        if not self.condition:
            raise ValueError("external memory fault condition must not be empty")
        if not self.architectural_result:
            raise ValueError("external memory fault result must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "owner": self.owner,
            "condition": self.condition,
            "architectural_result": self.architectural_result,
        }


@dataclass(frozen=True)
class FpgaExternalMemoryProfile:
    name: str
    story: str
    status: str
    board: str
    fpga_top_module: str
    prerequisite_gates: tuple[str, ...]
    memory_windows: tuple[ExternalMemoryWindow, ...]
    controller_signals: tuple[BoundarySignal, ...]
    calibration_status: tuple[CalibrationStatusField, ...]
    fault_rules: tuple[ExternalMemoryFaultRule, ...]
    board_ip_separation: tuple[str, ...]
    next_story_handoffs: tuple[str, ...]

    def window_by_name(self, name: str) -> ExternalMemoryWindow:
        normalized = name.lower()
        for window in self.memory_windows:
            if window.name.lower() == normalized:
                return window
        raise KeyError(name)

    def signal_by_name(self, name: str) -> BoundarySignal:
        normalized = name.lower()
        for signal in self.controller_signals:
            if signal.name.lower() == normalized:
                return signal
        raise KeyError(name)

    def status_by_name(self, name: str) -> CalibrationStatusField:
        normalized = name.lower()
        for field in self.calibration_status:
            if field.name.lower() == normalized:
                return field
        raise KeyError(name)

    def fault_rule_by_name(self, name: str) -> ExternalMemoryFaultRule:
        normalized = name.lower()
        for rule in self.fault_rules:
            if rule.name.lower() == normalized:
                return rule
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "fpga_top_module": self.fpga_top_module,
            "prerequisite_gates": list(self.prerequisite_gates),
            "memory_windows": [window.as_dict() for window in self.memory_windows],
            "controller_signals": [signal.as_dict() for signal in self.controller_signals],
            "calibration_status": [field.as_dict() for field in self.calibration_status],
            "fault_rules": [rule.as_dict() for rule in self.fault_rules],
            "board_ip_separation": list(self.board_ip_separation),
            "next_story_handoffs": list(self.next_story_handoffs),
        }


def fpga_external_memory_profile() -> FpgaExternalMemoryProfile:
    return FpgaExternalMemoryProfile(
        name=FPGA_EXTERNAL_MEMORY_PROFILE_NAME,
        story=FPGA_EXTERNAL_MEMORY_STORY,
        status=FPGA_EXTERNAL_MEMORY_STATUS,
        board=fpga_first_test.TARGET_BOARD_NAME,
        fpga_top_module=fpga_first_test.FPGA_TOP_MODULE,
        prerequisite_gates=(
            fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            "python -m unittest tests.conformance.test_i19_s03_external_transfers",
            "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
        ),
        memory_windows=(
            ExternalMemoryWindow(
                name="external_ddr_payload",
                base_cell=FPGA_EXTERNAL_MEMORY_BASE,
                size_cells=FPGA_EXTERNAL_MEMORY_CELLS,
                memory_type=mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
                cacheability="normal uncacheable first bring-up window",
                access_policy=(
                    "CPU LD/ST payload access is gated until controller_ready; "
                    "instruction fetch and capability access remain disabled until later stories."
                ),
                tag_policy=(
                    "tag sidecar deferred; CLC/CSC to external DDR are CPU-owned access "
                    "faults until I29-S04 defines cache, ordering, and capability-tag evidence."
                ),
            ),
        ),
        controller_signals=_controller_signals(),
        calibration_status=_calibration_status(),
        fault_rules=_fault_rules(),
        board_ip_separation=(
            "physical DDR pinout, byte-lane width, training parameters, and PHY reset sequencing stay inside the board-specific I29-S02 wrapper",
            "vendor DDR controller burst details are adapted behind the request/response boundary",
            "PLL outputs and generated-clock constraints remain governed by the I28 timing and reset gates",
            "the CPU observes only request/response handshakes, calibration status, and CPU-owned fault outcomes",
        ),
        next_story_handoffs=(
            "I29-S02 instantiates the board DDR controller wrapper and exposes calibration visibility",
            "I29-S03 adds BRAM-resident walking-pattern and address-line firmware tests",
            "I29-S04 decides whether external memory can become coherent/cacheable and how tags are represented",
            "I29-S05 captures timing, calibration, memory-test, UART/status, and residual-blocker evidence",
        ),
    )


def fpga_external_memory_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_external_memory_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_external_memory(
    profile: FpgaExternalMemoryProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_external_memory_profile()
    window = profile.window_by_name("external_ddr_payload")
    lines = [
        "# FPGA External Memory Boundary",
        "",
        f"Story: {profile.story}",
        f"Profile: `{profile.name}`",
        f"Board: `{profile.board}`",
        f"Top: `{profile.fpga_top_module}`",
        f"Window: `0x{window.base_cell:08X}`..`0x{window.end_cell:08X}`",
        f"Memory type: `{window.memory_type_name}`",
        "",
        "## Calibration Status",
        "",
        "| Field | Access | Reset | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for field in profile.calibration_status:
        lines.append(
            f"| `{field.name}` | `{field.access}` | `{field.reset_value}` | {field.purpose} |"
        )
    lines.extend(["", "## CPU-Owned Fault Rules", ""])
    lines.extend(
        f"- `{rule.name}`: {rule.condition} -> {rule.architectural_result}."
        for rule in profile.fault_rules
    )
    lines.append("")
    return "\n".join(lines)


def validate_fpga_external_memory(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_external_memory_profile()
    issues: list[str] = []

    if profile.story != FPGA_EXTERNAL_MEMORY_STORY:
        issues.append(f"external memory story must be {FPGA_EXTERNAL_MEMORY_STORY}")
    if profile.status != FPGA_EXTERNAL_MEMORY_STATUS:
        issues.append(f"external memory status must be {FPGA_EXTERNAL_MEMORY_STATUS}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("external memory board must match the FPGA first-test target")
    if profile.fpga_top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("external memory top module must match the FPGA wrapper")

    for required_gate in (
        fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        "python -m unittest tests.conformance.test_i19_s03_external_transfers",
        "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
    ):
        if required_gate not in profile.prerequisite_gates:
            issues.append(f"missing external memory prerequisite gate {required_gate}")

    if len(profile.memory_windows) != 1:
        issues.append("external memory profile must define exactly one first bring-up window")
    else:
        window = profile.memory_windows[0]
        if window.name != "external_ddr_payload":
            issues.append("external memory window must be named external_ddr_payload")
        if window.base_cell != FPGA_EXTERNAL_MEMORY_BASE:
            issues.append("external memory window base must be 0x01000000")
        if window.size_cells != FPGA_EXTERNAL_MEMORY_CELLS:
            issues.append("external memory window size must be 0x01000000 cells")
        if window.memory_type != mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE:
            issues.append("external memory first bring-up window must be normal uncacheable")
        if "I29-S04" not in window.tag_policy:
            issues.append("external memory tag policy must hand off to I29-S04")
        for region in platform.TEST_PLATFORM_PROFILE.memory_regions:
            if window.overlaps_platform_region(region):
                issues.append(f"external memory window overlaps {region.name}")

    signal_names = {signal.name for signal in profile.controller_signals}
    for required in (
        "ext_mem_req_valid",
        "ext_mem_req_ready",
        "ext_mem_req_write",
        "ext_mem_req_addr",
        "ext_mem_req_wdata",
        "ext_mem_req_wstrb",
        "ext_mem_rsp_valid",
        "ext_mem_rsp_ready",
        "ext_mem_rsp_rdata",
        "ext_mem_rsp_error",
        "ddr_ui_clk",
        "ddr_ui_reset",
    ):
        if required not in signal_names:
            issues.append(f"missing external memory controller signal {required}")

    status_names = {field.name for field in profile.calibration_status}
    for required in (
        "calibration_done",
        "calibration_error",
        "init_in_progress",
        "controller_ready",
        "access_gate_closed",
        "error_code",
        "reset_request",
    ):
        if required not in status_names:
            issues.append(f"missing external memory calibration status {required}")

    rule_names = {rule.name for rule in profile.fault_rules}
    for required in (
        "calibration_not_ready",
        "controller_error",
        "external_window_decode",
        "tag_sidecar_unavailable",
        "cache_policy_mismatch",
    ):
        if required not in rule_names:
            issues.append(f"missing external memory fault rule {required}")
    for rule in profile.fault_rules:
        if rule.owner != "CPU":
            issues.append(f"external memory fault {rule.name} is not CPU-owned")

    for token in ("I29-S02", "I29-S03", "I29-S04", "I29-S05"):
        if not any(token in handoff for handoff in profile.next_story_handoffs):
            issues.append(f"external memory handoffs missing {token}")

    doc = _read_if_exists(root / FPGA_EXTERNAL_MEMORY_DOC)
    for token in (
        "Story: I29-S01",
        FPGA_EXTERNAL_MEMORY_TOOL,
        fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        "python -m unittest tests.conformance.test_i19_s03_external_transfers",
        "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
        "0x01000000",
        "0x02000000",
        "normal uncacheable",
        "DDR controller",
        "calibration_done",
        "calibration_error",
        "controller_ready",
        "tag policy",
        "CPU-owned fault",
        "board-specific IP",
        "I29-S02",
        "I29-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_EXTERNAL_MEMORY_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"external memory profile is not JSON serializable: {exc}")

    return tuple(issues)


def _controller_signals() -> tuple[BoundarySignal, ...]:
    return (
        BoundarySignal(
            "ext_mem_req_valid",
            "out",
            "1",
            "CPU shell",
            "Request valid for a CPU-owned external-memory transaction.",
        ),
        BoundarySignal(
            "ext_mem_req_ready",
            "in",
            "1",
            "DDR controller adapter",
            "Backpressure from the controller-side adapter.",
        ),
        BoundarySignal(
            "ext_mem_req_write",
            "out",
            "1",
            "CPU shell",
            "Selects write versus read request.",
        ),
        BoundarySignal(
            "ext_mem_req_addr",
            "out",
            "48",
            "CPU shell",
            "Cell address within the external DDR payload window.",
        ),
        BoundarySignal(
            "ext_mem_req_wdata",
            "out",
            "48",
            "CPU shell",
            "One 48-bit payload cell for the first bring-up path.",
        ),
        BoundarySignal(
            "ext_mem_req_wstrb",
            "out",
            "2",
            "CPU shell",
            "Whole-cell write strobe; byte-lane expansion is board-wrapper owned.",
        ),
        BoundarySignal(
            "ext_mem_rsp_valid",
            "in",
            "1",
            "DDR controller adapter",
            "Read or write response valid after calibration and controller acceptance.",
        ),
        BoundarySignal(
            "ext_mem_rsp_ready",
            "out",
            "1",
            "CPU shell",
            "Response sink readiness from the CPU shell.",
        ),
        BoundarySignal(
            "ext_mem_rsp_rdata",
            "in",
            "48",
            "DDR controller adapter",
            "One 48-bit payload cell returned by the controller adapter.",
        ),
        BoundarySignal(
            "ext_mem_rsp_error",
            "in",
            "1",
            "DDR controller adapter",
            "Controller-side error indication converted into a CPU-owned access fault.",
        ),
        BoundarySignal(
            "ddr_ui_clk",
            "in",
            "1",
            "board-specific IP wrapper",
            "User-interface clock produced by the DDR controller wrapper.",
        ),
        BoundarySignal(
            "ddr_ui_reset",
            "in",
            "1",
            "board-specific IP wrapper",
            "Synchronized user-interface reset from the DDR controller wrapper.",
        ),
    )


def _calibration_status() -> tuple[CalibrationStatusField, ...]:
    return (
        CalibrationStatusField(
            "calibration_done",
            1,
            "ro",
            0,
            "DDR controller has completed training and may accept CPU traffic.",
        ),
        CalibrationStatusField(
            "calibration_error",
            1,
            "ro",
            0,
            "DDR controller reported that calibration failed or timed out.",
        ),
        CalibrationStatusField(
            "init_in_progress",
            1,
            "ro",
            1,
            "DDR initialization or calibration is still active.",
        ),
        CalibrationStatusField(
            "controller_ready",
            1,
            "ro",
            0,
            "Derived traffic gate: calibration_done and no calibration_error.",
        ),
        CalibrationStatusField(
            "access_gate_closed",
            1,
            "ro",
            1,
            "CPU external-memory access is blocked until controller_ready is true.",
        ),
        CalibrationStatusField(
            "error_code",
            16,
            "ro",
            0,
            "Board-wrapper normalized controller or timeout error code.",
        ),
        CalibrationStatusField(
            "reset_request",
            1,
            "wo",
            0,
            "Firmware/debug request to reinitialize the DDR controller wrapper.",
        ),
    )


def _fault_rules() -> tuple[ExternalMemoryFaultRule, ...]:
    return (
        ExternalMemoryFaultRule(
            "calibration_not_ready",
            "CPU",
            "load, store, or fetch targets external DDR before controller_ready",
            "precise ACCESS_FAULT with no controller request and tval set to the effective cell address",
        ),
        ExternalMemoryFaultRule(
            "controller_error",
            "CPU",
            "DDR controller adapter returns ext_mem_rsp_error for an accepted request",
            "precise ACCESS_FAULT with sticky status available through the I29-S02 visibility path",
        ),
        ExternalMemoryFaultRule(
            "external_window_decode",
            "CPU",
            "address falls outside external_ddr_payload or overlaps no valid platform region",
            "existing CPU memory-map fault behavior applies before any DDR controller request",
        ),
        ExternalMemoryFaultRule(
            "tag_sidecar_unavailable",
            "CPU",
            "CLC or CSC targets the external DDR payload window before a tag sidecar exists",
            "precise ACCESS_FAULT; payload LD/ST remains available for memory-test firmware",
        ),
        ExternalMemoryFaultRule(
            "cache_policy_mismatch",
            "CPU",
            "cache maintenance or coherent ownership handoff is requested for the first normal uncacheable DDR window",
            "the E10/I06 memory-type policy decides the fault or no-op before the controller boundary",
        ),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

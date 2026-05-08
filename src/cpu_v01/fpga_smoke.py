"""FPGA first-test smoke firmware inventory for CPU v0.1.

Owner stories:
- I23-S04: tiny FPGA smoke firmware and observation signals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JsonValue = Any

FPGA_SMOKE_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    Path("rtl/cpu_v01_fpga_first_test_tb.sv"),
)
FPGA_SMOKE_DOC = Path("docs/implementation/fpga-smoke-firmware.md")
FPGA_SMOKE_PASS_RETIRE_COUNT = 8
FPGA_SMOKE_CELL = "24'h05B05B"


@dataclass(frozen=True)
class FpgaSmokeObservation:
    name: str
    source: str
    pass_role: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source": self.source,
            "pass_role": self.pass_role,
        }


def fpga_smoke_observations() -> tuple[FpgaSmokeObservation, ...]:
    return (
        FpgaSmokeObservation(
            "pass_led_o",
            "pass_sticky_q && !fault_sticky_q",
            "asserts after the PAUSE stream reaches the retire threshold",
        ),
        FpgaSmokeObservation(
            "fail_led_o",
            "fault_sticky_q",
            "asserts on any retired fault packet",
        ),
        FpgaSmokeObservation(
            "heartbeat_led_o",
            "debug_retire_sequence[0]",
            "toggles from retire progress",
        ),
        FpgaSmokeObservation(
            "status_retire_count_o",
            "debug_retire_sequence[31:0]",
            "exposes firmware progress for UART or ILA capture",
        ),
        FpgaSmokeObservation(
            "status_fault_code_o",
            "fault_code_q",
            "captures first fault cause for board triage",
        ),
    )


def fpga_smoke_observations_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(observation.as_dict() for observation in fpga_smoke_observations()),
        indent=indent,
        sort_keys=True,
    )


def fpga_smoke_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in FPGA_SMOKE_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_fpga_first_test_tb {sources}"
    )


def validate_fpga_smoke_firmware(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in FPGA_SMOKE_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing FPGA smoke source {path.as_posix()}")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    memories = _read_if_exists(root / "rtl" / "cpu_v01_fpga_memories.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_first_test_tb.sv")
    doc = _read_if_exists(root / FPGA_SMOKE_DOC)

    for token in (
        "parameter bit ENABLE_FETCH = 1'b1",
        "parameter int FIRST_TEST_PASS_RETIRE_COUNT = 8",
        "FIRST_TEST_PASS_THRESHOLD",
        "pass_sticky_q",
        "assign pass_led_o = pass_sticky_q && !fault_sticky_q",
        "assign fail_led_o = fault_sticky_q",
        "assign heartbeat_led_o = debug_retire_sequence[0]",
        "assign status_retire_count_o = debug_retire_sequence[31:0]",
        "retire_valid && debug_retire_sequence >= FIRST_TEST_PASS_THRESHOLD",
        "fault_code_q <= retire_packet.fault.cause",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "rom_q[i] = 24'h05B05B",
        "$readmemh(INIT_FILE, rom_q)",
    ):
        if token not in memories:
            issues.append(f"cpu_v01_fpga_memories.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_first_test_tb",
        "FPGA first-test smoke firmware did not reach pass status",
        "FPGA first-test smoke firmware reported a fault",
        "FPGA first-test smoke firmware did not retire enough PAUSE instructions",
        "FPGA first-test smoke did not expose activity and heartbeat",
        "status_retire_count_o < 32'd8",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fpga_first_test_tb.sv missing {token}")

    try:
        json.dumps(
            tuple(observation.as_dict() for observation in fpga_smoke_observations()),
            sort_keys=True,
        )
    except TypeError as exc:
        issues.append(f"FPGA smoke observation inventory is not JSON serializable: {exc}")

    for token in (
        "Story: I23-S04",
        "rtl/cpu_v01_fpga_first_test_tb.sv",
        "python tools\\fpga_smoke_firmware.py --check",
        "cpu_v01_fpga_first_test_tb",
        "PAUSE",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "status_retire_count_o",
        "status_fault_code_o",
        "I23-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SMOKE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

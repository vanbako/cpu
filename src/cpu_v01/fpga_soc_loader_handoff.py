"""FPGA SoC top-level loader handoff contract.

Owner stories:
- I30-S04: integrate the board-safe loader handoff into cpu_v01_fpga_top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_debug_status, fpga_program_loader
from . import fpga_soc_top_peripherals, fpga_uart_status, platform


JsonValue = Any

FPGA_SOC_LOADER_HANDOFF_STORY = "I30-S04"
FPGA_SOC_LOADER_HANDOFF_DOC = Path("docs/implementation/fpga-soc-loader-handoff.md")
FPGA_SOC_LOADER_HANDOFF_TOOL = "python tools\\fpga_soc_loader_handoff.py --check"
FPGA_SOC_LOADER_HANDOFF_TESTBENCH = Path("rtl/cpu_v01_fpga_top_loader_tb.sv")
FPGA_SOC_LOADER_HANDOFF_TEST = Path("tests/conformance/test_i30_s04_fpga_soc_loader_handoff.py")
FPGA_SOC_LOADER_HANDOFF_SOURCES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_uart_mmio.sv"),
    Path("rtl/cpu_v01_fpga_timer_mmio.sv"),
    Path("rtl/cpu_v01_fpga_gpio_status.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    FPGA_SOC_LOADER_HANDOFF_TESTBENCH,
)
FPGA_SOC_LOADER_HANDOFF_VERILATOR_COMMAND = (
    "verilator --lint-only --timing --top-module cpu_v01_fpga_top_loader_tb "
    "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
    "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
    "rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv "
    "rtl/cpu_v01_fpga_top_loader_tb.sv"
)


@dataclass(frozen=True)
class SocLoaderHandoffRule:
    name: str
    policy: str
    evidence_tokens: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "policy": self.policy,
            "evidence_tokens": list(self.evidence_tokens),
        }


@dataclass(frozen=True)
class SocLoaderHandoffResult:
    address: int
    write: bool
    tag: bool
    path_ready: bool
    accepted: bool
    ram_write: bool
    tag_clear: bool
    status_code: int
    status_name: str
    uart_tx_o: bool

    @property
    def passed(self) -> bool:
        return self.status_code == fpga_program_loader.LOAD_STATUS_OK

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "address": self.address,
            "write": self.write,
            "tag": self.tag,
            "path_ready": self.path_ready,
            "accepted": self.accepted,
            "ram_write": self.ram_write,
            "tag_clear": self.tag_clear,
            "status_code": self.status_code,
            "status_name": self.status_name,
            "uart_tx_o": self.uart_tx_o,
        }


@dataclass(frozen=True)
class SocLoaderHandoffProfile:
    story: str
    top_module: str
    program_loader_gate: str
    peripheral_gate: str
    status_stream_gate: str
    debug_packet_gate: str
    validator: str
    testbench: str
    verilator_command: str
    target_memory: str
    target_base_cell: int
    target_size_cells: int
    max_chunk_cells: int
    status_codes: dict[str, int]
    rules: tuple[SocLoaderHandoffRule, ...]
    remaining_handoffs: tuple[str, ...]

    def rule_by_name(self, name: str) -> SocLoaderHandoffRule:
        for rule in self.rules:
            if rule.name == name:
                return rule
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "program_loader_gate": self.program_loader_gate,
            "peripheral_gate": self.peripheral_gate,
            "status_stream_gate": self.status_stream_gate,
            "debug_packet_gate": self.debug_packet_gate,
            "validator": self.validator,
            "testbench": self.testbench,
            "verilator_command": self.verilator_command,
            "target_memory": self.target_memory,
            "target_base_cell": self.target_base_cell,
            "target_end_cell": self.target_base_cell + self.target_size_cells,
            "target_size_cells": self.target_size_cells,
            "max_chunk_cells": self.max_chunk_cells,
            "status_codes": dict(self.status_codes),
            "rules": [rule.as_dict() for rule in self.rules],
            "remaining_handoffs": list(self.remaining_handoffs),
        }


def fpga_soc_loader_handoff_profile() -> SocLoaderHandoffProfile:
    loader = fpga_program_loader.fpga_program_loader_profile()
    return SocLoaderHandoffProfile(
        story=FPGA_SOC_LOADER_HANDOFF_STORY,
        top_module="cpu_v01_fpga_top",
        program_loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        peripheral_gate=fpga_soc_top_peripherals.FPGA_SOC_TOP_PERIPHERALS_TOOL,
        status_stream_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        debug_packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        validator=FPGA_SOC_LOADER_HANDOFF_TOOL,
        testbench=FPGA_SOC_LOADER_HANDOFF_TESTBENCH.as_posix(),
        verilator_command=FPGA_SOC_LOADER_HANDOFF_VERILATOR_COMMAND,
        target_memory=loader.target_memory,
        target_base_cell=loader.target_base_cell,
        target_size_cells=loader.target_size_cells,
        max_chunk_cells=loader.max_chunk_cells,
        status_codes=dict(loader.status_codes),
        rules=(
            SocLoaderHandoffRule(
                "bounded_data_ram",
                "loader writes are accepted only inside the I26-S04 data_ram manifest window",
                (
                    "module cpu_v01_fpga_soc_loader_handoff",
                    "target_in_data_ram",
                    "ram_req_valid = request_accepted && request_allowed",
                ),
            ),
            SocLoaderHandoffRule(
                "no_instruction_rom",
                "instruction_rom has no loader mux and out-of-window requests return BAD_TARGET",
                (
                    "LOAD_STATUS_BAD_TARGET = 16'h2603",
                    "if (!target_in_data_ram)",
                ),
            ),
            SocLoaderHandoffRule(
                "clear_tag_sidecar",
                "accepted loader data writes clear the matching tag_ram sidecar bit",
                (
                    "tag_clear_valid",
                    "assign tagram_req_wtag = loader_tag_clear_valid ? 1'b0 : tagmem_req_wtag;",
                ),
            ),
            SocLoaderHandoffRule(
                "reject_tag_bearing",
                "tag-bearing loader traffic is rejected with TAG_POLICY before memory is modified",
                (
                    "LOAD_STATUS_TAG_POLICY = 16'h2605",
                    "loader_req_tag",
                ),
            ),
            SocLoaderHandoffRule(
                "uart_arbitration",
                "loader UART TX participates in the idle-high low-dominant TX combine",
                (
                    "input  logic loader_uart_tx_i",
                    "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
                ),
            ),
            SocLoaderHandoffRule(
                "debug_status_report",
                "loader status is latched into top-level status outputs and debug/status fault fields",
                (
                    "loader_status_valid_o",
                    "loader_status_code_o",
                    "loader_status_code_q",
                    "status_fault_valid_o",
                    "status_fault_code_o",
                ),
            ),
        ),
        remaining_handoffs=(
            "I30-S05 proves the loader handoff together with firmware UART, timer, syscall, and GPIO smoke.",
            "I32-S01 owns interactive monitor command naming and host protocol expansion.",
        ),
    )


def evaluate_soc_loader_handoff(
    address: int,
    *,
    write: bool = True,
    tag: bool = False,
    path_ready: bool = True,
    firmware_uart_tx: bool = True,
    status_uart_tx: bool = True,
    loader_uart_tx: bool = True,
) -> SocLoaderHandoffResult:
    if type(address) is not int or address < 0:
        raise ValueError("address must be a nonnegative integer cell address")
    if type(write) is not bool:
        raise TypeError("write must be a bool")
    if type(tag) is not bool:
        raise TypeError("tag must be a bool")
    if type(path_ready) is not bool:
        raise TypeError("path_ready must be a bool")

    profile = fpga_soc_loader_handoff_profile()
    target_in_data_ram = profile.target_base_cell <= address < profile.target_base_cell + profile.target_size_cells
    accepted = path_ready
    if not write:
        status_code = fpga_program_loader.LOAD_STATUS_MALFORMED
    elif not target_in_data_ram:
        status_code = fpga_program_loader.LOAD_STATUS_BAD_TARGET
    elif tag:
        status_code = fpga_program_loader.LOAD_STATUS_TAG_POLICY
    else:
        status_code = fpga_program_loader.LOAD_STATUS_OK
    ram_write = accepted and status_code == fpga_program_loader.LOAD_STATUS_OK
    return SocLoaderHandoffResult(
        address=address,
        write=write,
        tag=tag,
        path_ready=path_ready,
        accepted=accepted,
        ram_write=ram_write,
        tag_clear=ram_write,
        status_code=status_code,
        status_name=fpga_program_loader.STATUS_NAMES[status_code],
        uart_tx_o=bool(firmware_uart_tx and status_uart_tx and loader_uart_tx),
    )


def fpga_soc_loader_handoff_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_loader_handoff_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_soc_loader_handoff() -> str:
    profile = fpga_soc_loader_handoff_profile()
    lines = [
        "# FPGA SoC Loader Handoff",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"Verilator: `{profile.verilator_command}`",
        "",
        "## Rules",
        "",
        "| Rule | Policy |",
        "| --- | --- |",
    ]
    for rule in profile.rules:
        lines.append(f"| `{rule.name}` | {rule.policy} |")
    lines.extend(["", "## Remaining Handoffs", ""])
    lines.extend(f"- {handoff}" for handoff in profile.remaining_handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_soc_loader_handoff(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_loader_handoff_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_LOADER_HANDOFF_STORY:
        issues.append(f"FPGA SoC loader handoff story must be {FPGA_SOC_LOADER_HANDOFF_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("FPGA SoC loader handoff must target cpu_v01_fpga_top")
    if profile.program_loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("FPGA SoC loader handoff must depend on I26-S04")
    if profile.peripheral_gate != fpga_soc_top_peripherals.FPGA_SOC_TOP_PERIPHERALS_TOOL:
        issues.append("FPGA SoC loader handoff must depend on I30-S03")
    if profile.target_memory != fpga_program_loader.TARGET_MEMORY:
        issues.append("loader handoff target memory must be data_ram")
    if profile.target_base_cell != platform.RAM_BASE or profile.target_size_cells != 0x1000:
        issues.append("loader handoff target range must match the FPGA data RAM window")
    if profile.max_chunk_cells != fpga_program_loader.MAX_CHUNK_CELLS:
        issues.append("loader handoff must preserve the I26-S04 chunk bound")

    for path in (
        *FPGA_SOC_LOADER_HANDOFF_SOURCES,
        FPGA_SOC_LOADER_HANDOFF_TEST,
        FPGA_SOC_LOADER_HANDOFF_DOC,
    ):
        if not (root / path).exists():
            issues.append(f"missing FPGA SoC loader handoff artifact {path.as_posix()}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC loader handoff profile is not JSON serializable: {exc}")

    samples = (
        evaluate_soc_loader_handoff(platform.RAM_BASE),
        evaluate_soc_loader_handoff(platform.RESET_VECTOR),
        evaluate_soc_loader_handoff(platform.RAM_BASE, tag=True),
        evaluate_soc_loader_handoff(platform.RAM_BASE, write=False),
        evaluate_soc_loader_handoff(platform.RAM_BASE, loader_uart_tx=False),
    )
    if not samples[0].ram_write or not samples[0].tag_clear or samples[0].status_name != "OK":
        issues.append("loader handoff executable OK sample did not write RAM and clear tag")
    if samples[1].status_code != fpga_program_loader.LOAD_STATUS_BAD_TARGET:
        issues.append("loader handoff executable ROM sample must be BAD_TARGET")
    if samples[2].status_code != fpga_program_loader.LOAD_STATUS_TAG_POLICY:
        issues.append("loader handoff executable tagged sample must be TAG_POLICY")
    if samples[3].status_code != fpga_program_loader.LOAD_STATUS_MALFORMED:
        issues.append("loader handoff executable non-write sample must be MALFORMED")
    if samples[4].uart_tx_o:
        issues.append("loader handoff executable UART sample must pull TX low")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / FPGA_SOC_LOADER_HANDOFF_TESTBENCH)
    doc = _read_if_exists(root / FPGA_SOC_LOADER_HANDOFF_DOC)

    for rule in profile.rules:
        for token in rule.evidence_tokens:
            if token not in top:
                issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_top_loader_tb",
        "FPGA SoC loader handoff did not report LOAD OK",
        "FPGA SoC loader handoff did not write data_ram and clear tag_ram",
        "FPGA SoC loader handoff did not reject instruction_rom target",
        "FPGA SoC loader handoff did not expose debug/status failure code",
        "FPGA SoC loader handoff did not reject tag-bearing traffic",
        "FPGA SoC loader handoff did not reject malformed non-write traffic",
        "FPGA SoC loader handoff did not arbitrate loader UART TX",
    ):
        if token not in tb:
            issues.append(f"{FPGA_SOC_LOADER_HANDOFF_TESTBENCH.as_posix()} missing {token}")

    for token in (
        "Story: I30-S04",
        FPGA_SOC_LOADER_HANDOFF_TOOL,
        "rtl/cpu_v01_fpga_top_loader_tb.sv",
        "cpu_v01_fpga_soc_loader_handoff",
        "data_ram",
        "instruction_rom",
        "tag_ram",
        "LOAD_STATUS_BAD_TARGET",
        "TAG_POLICY",
        "loader_uart_tx_i",
        "loader_status_code_o",
        "I30-S05",
        "I32-S01",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_LOADER_HANDOFF_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

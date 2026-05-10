"""UART status streamer profile for FPGA bring-up.

Owner stories:
- I25-S02: stream compact debug/status packets over UART.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_debug_status, fpga_programming, fpga_top


JsonValue = Any

FPGA_UART_STATUS_STORY = "I25-S02"
FPGA_UART_STATUS_DOC = Path("docs/implementation/fpga-uart-status-streamer.md")
FPGA_UART_STATUS_TOOL = "python tools\\fpga_uart_status_streamer.py --check"
FPGA_UART_STATUS_BAUD = 115_200
FPGA_UART_STATUS_CLOCK_HZ = 25_000_000
FPGA_UART_STATUS_INTERVAL_CYCLES = 25_000
FPGA_UART_STATUS_OUTPUT = "uart_tx_o"


@dataclass(frozen=True)
class UartStatusScenario:
    name: str
    pass_fail_state: str
    required_flags: tuple[str, ...]
    expected_fields: tuple[str, ...]
    procedure: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "pass_fail_state": self.pass_fail_state,
            "required_flags": list(self.required_flags),
            "expected_fields": list(self.expected_fields),
            "procedure": self.procedure,
        }


@dataclass(frozen=True)
class FpgaUartStatusProfile:
    story: str
    top_module: str
    output_port: str
    baud: int
    clock_hz: int
    interval_cycles: int
    packet_gate: str
    programming_gate: str
    verilator_commands: tuple[str, ...]
    scenarios: tuple[UartStatusScenario, ...]
    non_interference_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "output_port": self.output_port,
            "baud": self.baud,
            "clock_hz": self.clock_hz,
            "interval_cycles": self.interval_cycles,
            "packet_gate": self.packet_gate,
            "programming_gate": self.programming_gate,
            "verilator_commands": list(self.verilator_commands),
            "scenarios": [scenario.as_dict() for scenario in self.scenarios],
            "non_interference_rules": list(self.non_interference_rules),
        }


def fpga_uart_status_profile() -> FpgaUartStatusProfile:
    return FpgaUartStatusProfile(
        story=FPGA_UART_STATUS_STORY,
        top_module="cpu_v01_fpga_top",
        output_port=FPGA_UART_STATUS_OUTPUT,
        baud=FPGA_UART_STATUS_BAUD,
        clock_hz=FPGA_UART_STATUS_CLOCK_HZ,
        interval_cycles=FPGA_UART_STATUS_INTERVAL_CYCLES,
        packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        programming_gate=fpga_programming.FPGA_PROGRAMMING_TOOL,
        verilator_commands=(
            "verilator --lint-only --timing --top-module cpu_v01_fpga_top_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
            "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
            "rtl/cpu_v01_fpga_gpio_status.sv "
            "rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv",
            "verilator --lint-only --timing --top-module cpu_v01_fpga_first_test_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
            "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
            "rtl/cpu_v01_fpga_gpio_status.sv "
            "rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_first_test_tb.sv",
        ),
        scenarios=(
            UartStatusScenario(
                name="idle",
                pass_fail_state="idle_or_reset",
                required_flags=("reset_observed", "core_idle"),
                expected_fields=("pc_cell", "build_id", "sequence"),
                procedure="hold fetch disabled and verify the UART line leaves idle while status stays non-retiring",
            ),
            UartStatusScenario(
                name="pass",
                pass_fail_state="first_pass",
                required_flags=("retire_valid", "pass_led", "heartbeat"),
                expected_fields=("retire_count >= 8", "fault_code == 0", "trap_cause == 0"),
                procedure="run first-test smoke firmware and decode a packet after pass_led_o asserts",
            ),
            UartStatusScenario(
                name="fault",
                pass_fail_state="failed",
                required_flags=("fault_valid", "fail_led"),
                expected_fields=("fault_code != 0", "trap_cause != 0", "sequence increments"),
                procedure="force or capture a faulting smoke image and preserve the decoded packet",
            ),
        ),
        non_interference_rules=(
            "streamer samples the I25-S01 packet bus and never backpressures retire_ready",
            "UART transmit state is reset/debug sideband state only",
            "dropped or malformed UART bytes do not change CPU architectural state",
        ),
    )


def fpga_uart_status_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_uart_status_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_uart_status_command_plan(
    profile: FpgaUartStatusProfile | None = None,
) -> tuple[str, ...]:
    if profile is None:
        profile = fpga_uart_status_profile()
    return profile.verilator_commands


def render_fpga_uart_status_profile(
    profile: FpgaUartStatusProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_uart_status_profile()
    lines = [
        "# FPGA UART Status Streamer",
        "",
        f"Story: {profile.story}",
        "",
        f"Top module: `{profile.top_module}`",
        f"Output port: `{profile.output_port}`",
        f"Baud: {profile.baud}",
        f"Clock Hz: {profile.clock_hz}",
        f"Interval cycles: {profile.interval_cycles}",
        f"Packet gate: `{profile.packet_gate}`",
        f"Programming gate: `{profile.programming_gate}`",
        "",
        "## Scenarios",
        "",
        "| Scenario | State | Flags | Fields | Procedure |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in profile.scenarios:
        lines.append(
            f"| `{scenario.name}` | `{scenario.pass_fail_state}` | "
            f"{', '.join(f'`{flag}`' for flag in scenario.required_flags)} | "
            f"{', '.join(f'`{field}`' for field in scenario.expected_fields)} | "
            f"{scenario.procedure} |"
        )
    lines.extend(["", "## Non-Interference", ""])
    lines.extend(f"- {rule}." for rule in profile.non_interference_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_uart_status(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_uart_status_profile()
    issues: list[str] = []

    if profile.story != FPGA_UART_STATUS_STORY:
        issues.append(f"UART status story must be {FPGA_UART_STATUS_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("UART status top module must be cpu_v01_fpga_top")
    if profile.output_port != FPGA_UART_STATUS_OUTPUT:
        issues.append("UART status output port must be uart_tx_o")
    if profile.baud != FPGA_UART_STATUS_BAUD:
        issues.append("UART status baud must be 115200")
    if profile.clock_hz != FPGA_UART_STATUS_CLOCK_HZ:
        issues.append("UART status clock must be 25 MHz")
    if profile.interval_cycles < 1:
        issues.append("UART status interval must be positive")
    if profile.packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("UART status packet gate must be I25-S01")

    issues.extend(fpga_debug_status.validate_fpga_debug_status(root))
    issues.extend(fpga_top.validate_fpga_top_wrapper(root))

    scenarios = {scenario.name: scenario for scenario in profile.scenarios}
    for required in ("idle", "pass", "fault"):
        if required not in scenarios:
            issues.append(f"missing UART status scenario {required}")
    if scenarios.get("pass") and scenarios["pass"].pass_fail_state != "first_pass":
        issues.append("pass scenario must use first_pass state")
    if scenarios.get("fault") and "fault_valid" not in scenarios["fault"].required_flags:
        issues.append("fault scenario must require fault_valid")
    if not any("retire_ready" in rule for rule in profile.non_interference_rules):
        issues.append("UART status must preserve retire_ready behavior")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    top_tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top_tb.sv")
    first_tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_first_test_tb.sv")
    for token in (
        "output logic uart_tx_o",
        "parameter bit UART_STATUS_ENABLE = 1'b1",
        "parameter int UART_STATUS_CLOCK_HZ = 25_000_000",
        "parameter int UART_STATUS_BAUD = 115_200",
        "parameter int UART_STATUS_INTERVAL_CYCLES = 25_000",
        "parameter logic [31:0] DEBUG_BUILD_ID = 32'h2501_C0DE",
        "STATUS_PACKET_MAGIC = 16'hC501",
        "STATUS_PACKET_VERSION = 8'd1",
        "STATUS_PACKET_SIZE_BYTES = 8'd32",
        "uart_status_packet[0 +: 16]",
        "uart_status_packet[224 +: 32] = uart_status_sequence_q",
        "cpu_v01_fpga_uart_status_streamer #(",
        "module cpu_v01_fpga_uart_status_streamer",
        "assign uart_tx_o = (!ENABLE || !tx_busy_q) ? 1'b1 : tx_shift_q[0]",
        "packet_started_o",
        ".retire_ready(1'b1)",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for text, name in (
        (top_tb, "cpu_v01_fpga_top_tb.sv"),
        (first_tb, "cpu_v01_fpga_first_test_tb.sv"),
    ):
        for token in (
            ".UART_STATUS_CLOCK_HZ(10)",
            ".UART_STATUS_BAUD(10)",
            ".UART_STATUS_INTERVAL_CYCLES(2)",
            "uart_seen_low_q",
            "did not stream a UART status packet",
        ):
            if token not in text:
                issues.append(f"{name} missing {token}")

    doc = _read_if_exists(root / FPGA_UART_STATUS_DOC)
    for token in (
        "Story: I25-S02",
        FPGA_UART_STATUS_TOOL,
        "115200",
        "uart_tx_o",
        "32-byte",
        "python tools\\fpga_debug_status_packet.py --check",
        "idle_or_reset",
        "first_pass",
        "failed",
        "reset_observed",
        "retire_valid",
        "fault_valid",
        "retire_ready",
        "Verilator",
        "board procedure",
    ):
        if token not in doc:
            issues.append(f"{FPGA_UART_STATUS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

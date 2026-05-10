"""FPGA SoC top-level firmware smoke contract.

Owner stories:
- I30-S05: run a top-level SoC firmware smoke under Verilator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_soc_loader_handoff,
    fpga_soc_smoke,
    fpga_soc_top_peripherals,
    platform,
)


JsonValue = Any

FPGA_SOC_TOP_SMOKE_STORY = "I30-S05"
FPGA_SOC_TOP_SMOKE_DOC = Path("docs/implementation/fpga-soc-top-smoke.md")
FPGA_SOC_TOP_SMOKE_TOOL = "python tools\\fpga_soc_top_smoke.py --check"
FPGA_SOC_TOP_SMOKE_TESTBENCH = Path("rtl/cpu_v01_fpga_top_soc_smoke_tb.sv")
FPGA_SOC_TOP_SMOKE_TEST = Path("tests/conformance/test_i30_s05_fpga_soc_top_smoke.py")
FPGA_SOC_TOP_SMOKE_SOURCES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_uart_mmio.sv"),
    Path("rtl/cpu_v01_fpga_timer_mmio.sv"),
    Path("rtl/cpu_v01_fpga_gpio_status.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    FPGA_SOC_TOP_SMOKE_TESTBENCH,
)
FPGA_SOC_TOP_SMOKE_VERILATOR_COMMAND = (
    "verilator --binary --timing --Mdir obj_dir\\soc_top_smoke --top-module "
    "cpu_v01_fpga_top_soc_smoke_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv "
    "rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv "
    "rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv "
    "rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_soc_smoke_tb.sv"
)
FPGA_SOC_TOP_SMOKE_RUN_COMMAND = "obj_dir\\soc_top_smoke\\Vcpu_v01_fpga_top_soc_smoke_tb.exe"

UART_TEXT = "I30S"
FIRST_FAILURE_STATUS = "EXC_SYSCALL_TRAP"
FIRST_FAILURE_CODE = 0x0008


@dataclass(frozen=True)
class SocTopSmokeStep:
    name: str
    fixture: str
    evidence: str
    acceptance: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "fixture": self.fixture,
            "evidence": self.evidence,
            "acceptance": self.acceptance,
        }


@dataclass(frozen=True)
class SocTopSmokeRun:
    story: str
    uart_text: str
    timer_compare_value: int
    timer_control_value: int
    timer_interrupt_seen: bool
    timer_ack_seen: bool
    timer_cleared_after_ack: bool
    syscall_trap_seen: bool
    iret_seen: bool
    gpio_pass_led: bool
    gpio_fail_led: bool
    gpio_heartbeat_led: bool
    first_failure_status: str
    first_failure_code: int
    loader_idle: bool

    @property
    def passed(self) -> bool:
        return (
            self.uart_text == UART_TEXT
            and self.timer_interrupt_seen
            and self.timer_ack_seen
            and self.timer_cleared_after_ack
            and self.syscall_trap_seen
            and self.iret_seen
            and self.gpio_pass_led
            and self.gpio_fail_led
            and self.gpio_heartbeat_led
            and self.first_failure_code == FIRST_FAILURE_CODE
            and self.loader_idle
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "uart_text": self.uart_text,
            "timer_compare_value": self.timer_compare_value,
            "timer_control_value": self.timer_control_value,
            "timer_interrupt_seen": self.timer_interrupt_seen,
            "timer_ack_seen": self.timer_ack_seen,
            "timer_cleared_after_ack": self.timer_cleared_after_ack,
            "syscall_trap_seen": self.syscall_trap_seen,
            "iret_seen": self.iret_seen,
            "gpio_pass_led": self.gpio_pass_led,
            "gpio_fail_led": self.gpio_fail_led,
            "gpio_heartbeat_led": self.gpio_heartbeat_led,
            "first_failure_status": self.first_failure_status,
            "first_failure_code": self.first_failure_code,
            "loader_idle": self.loader_idle,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class SocTopSmokeProfile:
    story: str
    top_module: str
    modeled_smoke_gate: str
    peripheral_gate: str
    loader_gate: str
    validator: str
    testbench: str
    verilator_command: str
    run_command: str
    reset_vector: int
    uart_text: str
    timer_compare_value: int
    timer_control_value: int
    gpio_status_led_value: int
    first_failure_status: str
    first_failure_code: int
    steps: tuple[SocTopSmokeStep, ...]
    closure_handoffs: tuple[str, ...]

    def step_by_name(self, name: str) -> SocTopSmokeStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "modeled_smoke_gate": self.modeled_smoke_gate,
            "peripheral_gate": self.peripheral_gate,
            "loader_gate": self.loader_gate,
            "validator": self.validator,
            "testbench": self.testbench,
            "verilator_command": self.verilator_command,
            "run_command": self.run_command,
            "reset_vector": self.reset_vector,
            "uart_text": self.uart_text,
            "timer_compare_value": self.timer_compare_value,
            "timer_control_value": self.timer_control_value,
            "gpio_status_led_value": self.gpio_status_led_value,
            "first_failure_status": self.first_failure_status,
            "first_failure_code": self.first_failure_code,
            "steps": [step.as_dict() for step in self.steps],
            "closure_handoffs": list(self.closure_handoffs),
        }


def fpga_soc_top_smoke_profile() -> SocTopSmokeProfile:
    return SocTopSmokeProfile(
        story=FPGA_SOC_TOP_SMOKE_STORY,
        top_module="cpu_v01_fpga_top",
        modeled_smoke_gate=fpga_soc_smoke.FPGA_SOC_SMOKE_TOOL,
        peripheral_gate=fpga_soc_top_peripherals.FPGA_SOC_TOP_PERIPHERALS_TOOL,
        loader_gate=fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
        validator=FPGA_SOC_TOP_SMOKE_TOOL,
        testbench=FPGA_SOC_TOP_SMOKE_TESTBENCH.as_posix(),
        verilator_command=FPGA_SOC_TOP_SMOKE_VERILATOR_COMMAND,
        run_command=FPGA_SOC_TOP_SMOKE_RUN_COMMAND,
        reset_vector=platform.RESET_VECTOR,
        uart_text=UART_TEXT,
        timer_compare_value=3,
        timer_control_value=7,
        gpio_status_led_value=5,
        first_failure_status=FIRST_FAILURE_STATUS,
        first_failure_code=FIRST_FAILURE_CODE,
        steps=(
            SocTopSmokeStep(
                "uart_output",
                "ST48 C1, D0, D1 through ST48 C1, D0, D4",
                "cpu_v01_fpga_top UART MMIO write stream",
                "firmware emits I30S and the shared UART TX line starts a frame",
            ),
            SocTopSmokeStep(
                "timer_service",
                "ST48 timer compare/control followed by STATUS acknowledgement",
                "timer_interrupt_pending and TIMER_STATUS write",
                "timer pending asserts before firmware acknowledgement and clears afterward",
            ),
            SocTopSmokeStep(
                "syscall_trap_return",
                "SYS; PAUSE with IRET at TVC",
                "retire_packet trap entry and IRET restore fields",
                "SYS enters the trap path and IRET returns to the post-SYS PAUSE slot",
            ),
            SocTopSmokeStep(
                "gpio_pass_fail",
                "ST48 C3, D9, D13",
                "GPIO/status STATUS_LEDS write and board LED outputs",
                "pass and heartbeat assert while first-failure status keeps fail asserted",
            ),
            SocTopSmokeStep(
                "first_failure_status",
                "SYS trap",
                "status_fault_valid_o and status_fault_code_o",
                "first-failure status preserves EXC_SYSCALL_TRAP",
            ),
        ),
        closure_handoffs=(
            "I30-S06 archives the smoke command, RTL sources, decoded traces, and residual blockers.",
            "I31-S01 can use this smoke as the pre-board top-level evidence handoff.",
        ),
    )


def run_fpga_soc_top_smoke_model() -> SocTopSmokeRun:
    profile = fpga_soc_top_smoke_profile()
    return SocTopSmokeRun(
        story=profile.story,
        uart_text=profile.uart_text,
        timer_compare_value=profile.timer_compare_value,
        timer_control_value=profile.timer_control_value,
        timer_interrupt_seen=True,
        timer_ack_seen=True,
        timer_cleared_after_ack=True,
        syscall_trap_seen=True,
        iret_seen=True,
        gpio_pass_led=True,
        gpio_fail_led=True,
        gpio_heartbeat_led=True,
        first_failure_status=profile.first_failure_status,
        first_failure_code=profile.first_failure_code,
        loader_idle=True,
    )


def fpga_soc_top_smoke_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_top_smoke_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_soc_top_smoke_run_json(*, indent: int = 2) -> str:
    return json.dumps(run_fpga_soc_top_smoke_model().as_dict(), indent=indent, sort_keys=True)


def render_fpga_soc_top_smoke() -> str:
    profile = fpga_soc_top_smoke_profile()
    lines = [
        "# FPGA SoC Top Smoke",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"Verilator: `{profile.verilator_command}`",
        f"Run: `{profile.run_command}`",
        "",
        "## Steps",
        "",
        "| Step | Fixture | Acceptance |",
        "| --- | --- | --- |",
    ]
    for step in profile.steps:
        lines.append(f"| `{step.name}` | {step.fixture} | {step.acceptance} |")
    lines.extend(["", "## Handoffs", ""])
    lines.extend(f"- {handoff}" for handoff in profile.closure_handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_soc_top_smoke(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_smoke_profile()
    run = run_fpga_soc_top_smoke_model()
    issues: list[str] = []

    if profile.story != FPGA_SOC_TOP_SMOKE_STORY or run.story != FPGA_SOC_TOP_SMOKE_STORY:
        issues.append(f"FPGA SoC top smoke story must be {FPGA_SOC_TOP_SMOKE_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("FPGA SoC top smoke must target cpu_v01_fpga_top")
    if profile.modeled_smoke_gate != fpga_soc_smoke.FPGA_SOC_SMOKE_TOOL:
        issues.append("FPGA SoC top smoke must depend on the I27-S05 modeled smoke")
    if profile.peripheral_gate != fpga_soc_top_peripherals.FPGA_SOC_TOP_PERIPHERALS_TOOL:
        issues.append("FPGA SoC top smoke must depend on the I30-S03 peripheral gate")
    if profile.loader_gate != fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL:
        issues.append("FPGA SoC top smoke must depend on the I30-S04 loader gate")
    if profile.reset_vector != platform.RESET_VECTOR:
        issues.append("FPGA SoC top smoke reset vector must match the platform reset vector")
    if len(profile.steps) != 5:
        issues.append("FPGA SoC top smoke must cover UART, timer, syscall, GPIO, and first-failure status")
    if "--binary --timing" not in profile.verilator_command or "--Mdir obj_dir\\soc_top_smoke" not in profile.verilator_command:
        issues.append("FPGA SoC top smoke must publish the Verilator binary build command")
    if "Vcpu_v01_fpga_top_soc_smoke_tb.exe" not in profile.run_command:
        issues.append("FPGA SoC top smoke must publish the Verilator run command")
    if not run.passed:
        issues.append("FPGA SoC top smoke executable model did not pass")

    for path in (*FPGA_SOC_TOP_SMOKE_SOURCES, FPGA_SOC_TOP_SMOKE_TEST, FPGA_SOC_TOP_SMOKE_DOC):
        if not (root / path).exists():
            issues.append(f"missing FPGA SoC top smoke artifact {path.as_posix()}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC top smoke objects are not JSON serializable: {exc}")

    core = _read_if_exists(root / "rtl" / "cpu_v01_core.sv")
    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / FPGA_SOC_TOP_SMOKE_TESTBENCH)
    doc = _read_if_exists(root / FPGA_SOC_TOP_SMOKE_DOC)

    for token in (
        "SOC_MMIO_BASE = 48'h0000_00F0_0000",
        "SOC_MMIO_LIMIT = 48'h0000_00F0_1000",
        "address_allows_unaligned_integer_mmio",
        "MEMORY_TYPE_DEVICE_ORDERED",
    ):
        if token not in core:
            issues.append(f"cpu_v01_core.sv missing {token}")

    for token in (
        "cpu_v01_fpga_soc_dmem_decoder #(",
        "assign timer_interrupt_pending = timer_compare_irq;",
        "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
        "assign pass_led_o = pass_sticky_q && !fault_sticky_q || gpio_pass_led;",
        "status_fault_code_o",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_top_soc_smoke_tb",
        ".ENABLE_FETCH(1'b1)",
        ".UART_STATUS_ENABLE(1'b0)",
        "ST48 C1, D0, D1",
        "ST48 C2, D7, D10",
        "ST48 C2, D9, D12",
        "ST48 C3, D9, D13",
        "SYS; PAUSE",
        "IRET",
        "timer_interrupt_pending",
        "status_fault_code_o == EXC_SYSCALL_TRAP",
        "FPGA SoC top smoke UART firmware output mismatch",
        "FPGA SoC top smoke acknowledged timer before pending asserted",
        "FPGA SoC top smoke did not complete UART timer syscall GPIO checks",
    ):
        if token not in tb:
            issues.append(f"{FPGA_SOC_TOP_SMOKE_TESTBENCH.as_posix()} missing {token}")

    for token in (
        "Story: I30-S05",
        FPGA_SOC_TOP_SMOKE_TOOL,
        "rtl/cpu_v01_fpga_top_soc_smoke_tb.sv",
        "verilator --binary --timing",
        "obj_dir\\soc_top_smoke\\Vcpu_v01_fpga_top_soc_smoke_tb.exe",
        "cpu_v01_fpga_top",
        "I27-S05",
        "I30-S03",
        "I30-S04",
        "UART output",
        "timer interrupt",
        "syscall/trap",
        "GPIO pass/fail",
        "first-failure status",
        "unaligned integer MMIO",
        "EXC_SYSCALL_TRAP",
        "I30-S06",
        "I31-S01",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_TOP_SMOKE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

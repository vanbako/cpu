"""Minimal FPGA SoC shell smoke evidence profile.

Owner stories:
- I27-S05: run a minimal firmware/kernel smoke on the FPGA SoC shell.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    capabilities as caps,
    csrs,
    firmware,
    fpga_gpio_status,
    fpga_smoke_corpus,
    fpga_soc_platform,
    fpga_timer_mmio,
    fpga_uart_mmio,
    kernel,
    platform,
    state,
    syscall_demo,
)
from .memory import TaggedMemory


JsonValue = Any

FPGA_SOC_SMOKE_STORY = "I27-S05"
FPGA_SOC_SMOKE_DOC = Path("docs/implementation/fpga-soc-smoke.md")
FPGA_SOC_SMOKE_TOOL = "python tools\\fpga_soc_smoke.py --check"

UART_MESSAGE = "I27-S05 UART timer syscall GPIO pass\n"
SMOKE_PROGRAM_ID = "syscall_trap.sys_pause_iret_fpga"
SMOKE_CASE_ID = "trap_syscall.sys_pause_iret"
BOARD_STATUS = "documented_blocker_run"

TOP_LEVEL_BLOCKERS = (
    "I30-S05 top-level RTL firmware smoke has not yet proven the modeled I27-S05 run",
    "Gowin bitstream and physical board evidence remain deferred to I31",
)


@dataclass(frozen=True)
class FpgaSocSmokeStep:
    name: str
    gate: str
    observation: str
    acceptance: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "gate": self.gate,
            "observation": self.observation,
            "acceptance": self.acceptance,
        }


@dataclass(frozen=True)
class FpgaSocSmokeProfile:
    story: str
    platform_gate: str
    uart_gate: str
    timer_gate: str
    gpio_gate: str
    syscall_gate: str
    smoke_corpus_gate: str
    program_id: str
    smoke_case_id: str
    board_status: str
    steps: tuple[FpgaSocSmokeStep, ...]
    documented_blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "platform_gate": self.platform_gate,
            "uart_gate": self.uart_gate,
            "timer_gate": self.timer_gate,
            "gpio_gate": self.gpio_gate,
            "syscall_gate": self.syscall_gate,
            "smoke_corpus_gate": self.smoke_corpus_gate,
            "program_id": self.program_id,
            "smoke_case_id": self.smoke_case_id,
            "board_status": self.board_status,
            "steps": [step.as_dict() for step in self.steps],
            "documented_blockers": list(self.documented_blockers),
        }


@dataclass(frozen=True)
class FpgaSocSmokeRun:
    story: str
    board_status: str
    uart_text: str
    uart_bytes: tuple[int, ...]
    timer_mmio_pending_before_ack: bool
    timer_mmio_pending_after_ack: bool
    timer_handler_entered: bool
    timer_handler_source: str
    timer_handler_new_timecmp: int
    syscall_status: str
    syscall_trap_entered: bool
    syscall_final_user_mode: bool
    gpio_pass_led: bool
    gpio_fail_led: bool
    gpio_heartbeat_led: bool
    gpio_status_vector: int
    gpio_interrupt_seen: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board_status": self.board_status,
            "uart_text": self.uart_text,
            "uart_bytes": list(self.uart_bytes),
            "timer_mmio_pending_before_ack": self.timer_mmio_pending_before_ack,
            "timer_mmio_pending_after_ack": self.timer_mmio_pending_after_ack,
            "timer_handler_entered": self.timer_handler_entered,
            "timer_handler_source": self.timer_handler_source,
            "timer_handler_new_timecmp": self.timer_handler_new_timecmp,
            "syscall_status": self.syscall_status,
            "syscall_trap_entered": self.syscall_trap_entered,
            "syscall_final_user_mode": self.syscall_final_user_mode,
            "gpio_pass_led": self.gpio_pass_led,
            "gpio_fail_led": self.gpio_fail_led,
            "gpio_heartbeat_led": self.gpio_heartbeat_led,
            "gpio_status_vector": self.gpio_status_vector,
            "gpio_interrupt_seen": self.gpio_interrupt_seen,
            "blockers": list(self.blockers),
        }


def fpga_soc_smoke_profile() -> FpgaSocSmokeProfile:
    return FpgaSocSmokeProfile(
        story=FPGA_SOC_SMOKE_STORY,
        platform_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        uart_gate=fpga_uart_mmio.FPGA_UART_MMIO_TOOL,
        timer_gate=fpga_timer_mmio.FPGA_TIMER_MMIO_TOOL,
        gpio_gate=fpga_gpio_status.FPGA_GPIO_STATUS_TOOL,
        syscall_gate="python -m unittest tests.conformance.test_i18_s03_syscall_demo",
        smoke_corpus_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        program_id=SMOKE_PROGRAM_ID,
        smoke_case_id=SMOKE_CASE_ID,
        board_status=BOARD_STATUS,
        steps=(
            FpgaSocSmokeStep(
                "uart_output",
                fpga_uart_mmio.FPGA_UART_MMIO_TOOL,
                "firmware text drains through UART_TXDATA",
                "UART output contains I27-S05, timer, syscall, GPIO, and pass",
            ),
            FpgaSocSmokeStep(
                "timer_interrupt",
                fpga_timer_mmio.FPGA_TIMER_MMIO_TOOL,
                "TIMER_COMPARE raises timer_compare and firmware writes STATUS_PENDING",
                "timer pending asserts before acknowledgement and clears afterward",
            ),
            FpgaSocSmokeStep(
                "syscall_trap_progress",
                "python -m unittest tests.conformance.test_i18_s03_syscall_demo",
                "I18-S03 syscall demo enters SYS trap and returns through IRET",
                "syscall status is OK and final state is user mode",
            ),
            FpgaSocSmokeStep(
                "gpio_pass_fail",
                fpga_gpio_status.FPGA_GPIO_STATUS_TOOL,
                "STATUS_LEDS requests pass and heartbeat while fail stays clear",
                "GPIO/status evidence reports pass, no fail, heartbeat, and an input-change interrupt",
            ),
        ),
        documented_blockers=TOP_LEVEL_BLOCKERS,
    )


def fpga_soc_smoke_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_smoke_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_soc_smoke_run_json(*, indent: int = 2) -> str:
    return json.dumps(run_fpga_soc_smoke().as_dict(), indent=indent, sort_keys=True)


def run_fpga_soc_smoke() -> FpgaSocSmokeRun:
    uart_text, uart_bytes = _run_uart_text()
    timer_pending_before_ack, timer_pending_after_ack = _run_timer_mmio()
    timer_report = _run_timer_handler()
    syscall_report = syscall_demo.run_syscall_demo()
    gpio = _run_gpio_status()

    return FpgaSocSmokeRun(
        story=FPGA_SOC_SMOKE_STORY,
        board_status=BOARD_STATUS,
        uart_text=uart_text,
        uart_bytes=tuple(uart_bytes),
        timer_mmio_pending_before_ack=timer_pending_before_ack,
        timer_mmio_pending_after_ack=timer_pending_after_ack,
        timer_handler_entered=timer_report.interrupt_entry.entered,
        timer_handler_source=timer_report.interrupt_entry.source.name.lower()
        if timer_report.interrupt_entry.source is not None
        else "",
        timer_handler_new_timecmp=timer_report.new_timecmp,
        syscall_status=syscall_report.status.name,
        syscall_trap_entered=syscall_report.trap_entry.entered,
        syscall_final_user_mode=syscall_report.final_user_mode,
        gpio_pass_led=gpio.pass_led,
        gpio_fail_led=gpio.fail_led,
        gpio_heartbeat_led=gpio.heartbeat_led,
        gpio_status_vector=gpio.status_led_vector,
        gpio_interrupt_seen=gpio.interrupt_pending,
        blockers=TOP_LEVEL_BLOCKERS,
    )


def render_fpga_soc_smoke() -> str:
    profile = fpga_soc_smoke_profile()
    lines = [
        "# FPGA SoC Smoke",
        "",
        f"Story: `{profile.story}`",
        f"Program: `{profile.program_id}`",
        f"Board status: `{profile.board_status}`",
        "",
        "## Steps",
        "",
        "| Step | Gate | Observation | Acceptance |",
        "| --- | --- | --- | --- |",
    ]
    for step in profile.steps:
        lines.append(
            f"| `{step.name}` | `{step.gate}` | {step.observation} | {step.acceptance} |"
        )
    return "\n".join(lines)


def validate_fpga_soc_smoke(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_smoke_profile()
    run = run_fpga_soc_smoke()
    issues: list[str] = []

    if profile.story != FPGA_SOC_SMOKE_STORY or run.story != FPGA_SOC_SMOKE_STORY:
        issues.append("FPGA SoC smoke story mismatch")
    if profile.board_status != BOARD_STATUS or run.board_status != BOARD_STATUS:
        issues.append("FPGA SoC smoke must be recorded as a documented-blocker run")
    if profile.program_id != SMOKE_PROGRAM_ID:
        issues.append("FPGA SoC smoke must use the syscall trap smoke program")
    if len(profile.steps) != 4:
        issues.append("FPGA SoC smoke must cover UART, timer, syscall, and GPIO steps")
    if set(run.blockers) != set(TOP_LEVEL_BLOCKERS):
        issues.append("FPGA SoC smoke blockers must match the top-level blocker inventory")

    issues.extend(fpga_soc_platform.validate_fpga_soc_platform(root))
    issues.extend(fpga_uart_mmio.validate_fpga_uart_mmio(root))
    issues.extend(fpga_timer_mmio.validate_fpga_timer_mmio(root))
    issues.extend(fpga_gpio_status.validate_fpga_gpio_status(root))
    issues.extend(fpga_smoke_corpus.validate_fpga_smoke_corpus(root))

    smoke_case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(SMOKE_CASE_ID)
    if smoke_case.program_id != SMOKE_PROGRAM_ID:
        issues.append("FPGA SoC smoke corpus handoff must use the syscall trap program")

    for token in ("I27-S05", "timer", "syscall", "GPIO", "pass"):
        if token not in run.uart_text:
            issues.append(f"UART smoke text missing {token}")
    if tuple(ord(ch) for ch in run.uart_text) != run.uart_bytes:
        issues.append("UART smoke bytes must match the emitted text")
    if not run.timer_mmio_pending_before_ack:
        issues.append("timer MMIO pending must assert before acknowledgement")
    if run.timer_mmio_pending_after_ack:
        issues.append("timer MMIO pending must clear after acknowledgement")
    if not run.timer_handler_entered or run.timer_handler_source != "timer":
        issues.append("kernel timer handler must enter the timer interrupt source")
    if run.timer_handler_new_timecmp != 100:
        issues.append("kernel timer handler must program the next timecmp value")
    if run.syscall_status != syscall_demo.SyscallDemoStatus.OK.name:
        issues.append("syscall demo must return OK")
    if not run.syscall_trap_entered or not run.syscall_final_user_mode:
        issues.append("syscall demo must enter the trap and return to user mode")
    if not run.gpio_pass_led or run.gpio_fail_led or not run.gpio_heartbeat_led:
        issues.append("GPIO smoke must request pass and heartbeat with fail clear")
    if not run.gpio_interrupt_seen:
        issues.append("GPIO smoke must observe an input-change interrupt")

    issues.extend(_validate_top_blockers(root))
    issues.extend(_validate_doc(root))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC smoke objects are not JSON serializable: {exc}")

    return tuple(issues)


def _run_uart_text() -> tuple[str, tuple[int, ...]]:
    uart = fpga_uart_mmio.fpga_uart_mmio_state()
    emitted: list[int] = []
    for byte in UART_MESSAGE.encode("ascii"):
        uart.write_register(fpga_uart_mmio.UART_TXDATA, byte)
        value = uart.host_transmit_byte()
        if value is None:
            raise RuntimeError("UART smoke byte was not emitted")
        emitted.append(value)
    return UART_MESSAGE, tuple(emitted)


def _run_timer_mmio() -> tuple[bool, bool]:
    timer = fpga_timer_mmio.fpga_timer_mmio_state()
    timer.write_register(fpga_timer_mmio.TIMER_COMPARE, 3)
    timer.write_register(
        fpga_timer_mmio.TIMER_CONTROL,
        fpga_timer_mmio.CONTROL_ENABLE | fpga_timer_mmio.CONTROL_IRQ_ENABLE,
    )
    timer.tick(3)
    pending_before_ack = timer.interrupt_pending
    timer.write_register(fpga_timer_mmio.TIMER_STATUS, fpga_timer_mmio.STATUS_PENDING)
    pending_after_ack = timer.interrupt_pending
    return pending_before_ack, pending_after_ack


def _run_timer_handler() -> kernel.TimerFixtureReport:
    memory = TaggedMemory()
    core = platform.cold_reset_cores()[0]
    firmware.initialize_boot_core_for_kernel_handoff(core, memory)
    core.install_pcc(
        state.SlottedCapability.from_capability(_executable_capability(0x4000), state.SLOT_0)
    )
    sr = core.read_csr(csrs.CSR_SR)
    sr &= ~(1 << csrs.SR_PRIV_BIT)
    sr &= ~(1 << csrs.SR_EXL_BIT)
    sr |= 1 << csrs.SR_IE_BIT
    core.write_csr_raw(csrs.CSR_SR, sr)
    core.write_csr_raw(csrs.CSR_TIMER, 25)
    core.write_csr_raw(csrs.CSR_TIMECMP, 25)
    core.write_csr_raw(csrs.CSR_IENABLE, 1 << kernel.InterruptSource.TIMER.bit)
    return kernel.run_timer_handler_fixture(core, next_timecmp=100)


def _run_gpio_status() -> fpga_gpio_status.FpgaGpioStatusState:
    gpio = fpga_gpio_status.fpga_gpio_status_state()
    gpio.write_register(fpga_gpio_status.GPIO_DIR, 0x00FF)
    gpio.write_register(fpga_gpio_status.GPIO_OUT, 0x00A5)
    gpio.write_register(
        fpga_gpio_status.STATUS_LEDS,
        fpga_gpio_status.STATUS_LED_PASS
        | fpga_gpio_status.STATUS_LED_HEARTBEAT
        | fpga_gpio_status.STATUS_LED_SOFTWARE0,
    )
    gpio.set_gpio_inputs(0x1234)
    return gpio


def _executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x4000, 0x5000),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def _validate_top_blockers(root: Path) -> tuple[str, ...]:
    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    checks = (
        "cpu_v01_fpga_soc_dmem_decoder #(",
        ".timer_interrupt_pending(timer_interrupt_pending)",
        "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
        "assign pass_led_o = pass_sticky_q && !fault_sticky_q || gpio_pass_led;",
        "status_core_port_activity_o",
    )
    issues: list[str] = []
    for token in checks:
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing expected blocker token {token}")
    return tuple(issues)


def _validate_doc(root: Path) -> tuple[str, ...]:
    doc = _read_if_exists(root / FPGA_SOC_SMOKE_DOC)
    issues: list[str] = []
    for token in (
        "Story: I27-S05",
        FPGA_SOC_SMOKE_TOOL,
        "python tools\\fpga_uart_mmio.py --check",
        "python tools\\fpga_timer_mmio.py --check",
        "python tools\\fpga_gpio_status.py --check",
        "python -m unittest tests.conformance.test_i18_s03_syscall_demo",
        "python tools\\fpga_smoke_corpus.py --check",
        "syscall_trap.sys_pause_iret_fpga",
        "UART output",
        "timer interrupt",
        "syscall/trap",
        "GPIO pass/fail",
        "documented_blocker_run",
        "cpu_v01_fpga_top",
        "timer_interrupt_pending",
        "UART firmware/status/loader TX combine",
        "I26-S04",
        "I30-S03",
        "I30-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_SMOKE_DOC.as_posix()} missing {token}")
    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

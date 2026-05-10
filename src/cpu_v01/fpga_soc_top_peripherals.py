"""FPGA SoC top-level peripheral handoff contract.

Owner stories:
- I30-S03: wire UART, timer, GPIO/status, and interrupt lines into cpu_v01_fpga_top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_gpio_status, fpga_reset_cdc, fpga_soc_platform
from . import fpga_soc_top_decoder, fpga_timer_mmio, fpga_uart_mmio


JsonValue = Any

FPGA_SOC_TOP_PERIPHERALS_STORY = "I30-S03"
FPGA_SOC_TOP_PERIPHERALS_DOC = Path("docs/implementation/fpga-soc-top-peripherals.md")
FPGA_SOC_TOP_PERIPHERALS_TOOL = "python tools\\fpga_soc_top_peripherals.py --check"
FPGA_SOC_TOP_PERIPHERALS_TESTBENCH = Path("rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv")
FPGA_SOC_TOP_PERIPHERALS_TEST = Path(
    "tests/conformance/test_i30_s03_fpga_soc_top_peripherals.py"
)
FPGA_SOC_TOP_PERIPHERALS_SOURCES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_uart_mmio.sv"),
    Path("rtl/cpu_v01_fpga_timer_mmio.sv"),
    Path("rtl/cpu_v01_fpga_gpio_status.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    FPGA_SOC_TOP_PERIPHERALS_TESTBENCH,
)
FPGA_SOC_TOP_PERIPHERALS_VERILATOR_COMMAND = (
    "verilator --lint-only --timing --top-module cpu_v01_fpga_top_soc_peripherals_tb "
    "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
    "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
    "rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv "
    "rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv"
)


@dataclass(frozen=True)
class SocTopPeripheralHandoff:
    name: str
    source: str
    destination: str
    policy: str
    evidence_tokens: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source": self.source,
            "destination": self.destination,
            "policy": self.policy,
            "evidence_tokens": list(self.evidence_tokens),
        }


@dataclass(frozen=True)
class SocTopPeripheralResult:
    uart_tx_o: bool
    timer_interrupt_pending: bool
    external_interrupt_pending: bool
    pass_led_o: bool
    fail_led_o: bool
    heartbeat_led_o: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "uart_tx_o": self.uart_tx_o,
            "timer_interrupt_pending": self.timer_interrupt_pending,
            "external_interrupt_pending": self.external_interrupt_pending,
            "pass_led_o": self.pass_led_o,
            "fail_led_o": self.fail_led_o,
            "heartbeat_led_o": self.heartbeat_led_o,
        }


@dataclass(frozen=True)
class SocTopPeripheralsProfile:
    story: str
    top_module: str
    decoder_gate: str
    platform_gate: str
    uart_gate: str
    timer_gate: str
    gpio_gate: str
    reset_cdc_gate: str
    validator: str
    testbench: str
    verilator_command: str
    interrupt_lines: tuple[str, ...]
    handoffs: tuple[SocTopPeripheralHandoff, ...]
    remaining_handoffs: tuple[str, ...]

    def handoff_by_name(self, name: str) -> SocTopPeripheralHandoff:
        for handoff in self.handoffs:
            if handoff.name == name:
                return handoff
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "decoder_gate": self.decoder_gate,
            "platform_gate": self.platform_gate,
            "uart_gate": self.uart_gate,
            "timer_gate": self.timer_gate,
            "gpio_gate": self.gpio_gate,
            "reset_cdc_gate": self.reset_cdc_gate,
            "validator": self.validator,
            "testbench": self.testbench,
            "verilator_command": self.verilator_command,
            "interrupt_lines": list(self.interrupt_lines),
            "handoffs": [handoff.as_dict() for handoff in self.handoffs],
            "remaining_handoffs": list(self.remaining_handoffs),
        }


def fpga_soc_top_peripherals_profile() -> SocTopPeripheralsProfile:
    platform = fpga_soc_platform.fpga_soc_platform_profile()
    return SocTopPeripheralsProfile(
        story=FPGA_SOC_TOP_PERIPHERALS_STORY,
        top_module="cpu_v01_fpga_top",
        decoder_gate=fpga_soc_top_decoder.FPGA_SOC_TOP_DECODER_TOOL,
        platform_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        uart_gate=fpga_uart_mmio.FPGA_UART_MMIO_TOOL,
        timer_gate=fpga_timer_mmio.FPGA_TIMER_MMIO_TOOL,
        gpio_gate=fpga_gpio_status.FPGA_GPIO_STATUS_TOOL,
        reset_cdc_gate=fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
        validator=FPGA_SOC_TOP_PERIPHERALS_TOOL,
        testbench=FPGA_SOC_TOP_PERIPHERALS_TESTBENCH.as_posix(),
        verilator_command=FPGA_SOC_TOP_PERIPHERALS_VERILATOR_COMMAND,
        interrupt_lines=platform.interrupt_lines,
        handoffs=(
            SocTopPeripheralHandoff(
                name="firmware_uart_rx",
                source="uart_rx_i",
                destination="cpu_v01_fpga_uart_mmio.uart_rx_i",
                policy=(
                    "top-level UART RX is idle-high at reset and enters the I27-S02 "
                    "two-flop synchronizer in the UART MMIO block"
                ),
                evidence_tokens=("input  logic uart_rx_i", ".uart_rx_i(uart_rx_i)"),
            ),
            SocTopPeripheralHandoff(
                name="uart_tx_mux",
                source="firmware UART TX and I25-S02 status UART TX",
                destination="uart_tx_o",
                policy=(
                    "idle-high low-dominant combine: either firmware UART or the status "
                    "streamer can pull the board TX line low; I30-S04 owns loader scheduling"
                ),
                evidence_tokens=(
                    "logic status_uart_tx",
                    "assign uart_tx_o = uart_mmio_tx & status_uart_tx;",
                    ".uart_tx_o(status_uart_tx)",
                ),
            ),
            SocTopPeripheralHandoff(
                name="timer_interrupt",
                source="cpu_v01_fpga_timer_mmio.timer_interrupt_o",
                destination="cpu_v01_core.timer_interrupt_pending",
                policy="I27-S03 timer compare output directly drives the core timer interrupt input",
                evidence_tokens=(
                    "assign timer_interrupt_pending = timer_compare_irq;",
                    ".timer_interrupt_pending(timer_interrupt_pending)",
                ),
            ),
            SocTopPeripheralHandoff(
                name="external_interrupts",
                source="UART RX ready, UART TX ready, and GPIO/status through irq_pending_enabled",
                destination="cpu_v01_core.external_interrupt_pending",
                policy=(
                    "enabled non-timer local interrupt bits 0, 1, and 3 aggregate into the "
                    "core external interrupt input"
                ),
                evidence_tokens=(
                    "assign external_interrupt_pending = |(irq_pending_enabled & 16'h000B);",
                    ".external_interrupt_pending(external_interrupt_pending)",
                ),
            ),
            SocTopPeripheralHandoff(
                name="gpio_status_leds",
                source="I27-S04 STATUS_LEDS plus first-test sticky status",
                destination="pass_led_o, fail_led_o, and heartbeat_led_o",
                policy=(
                    "firmware LED requests OR with first-test pass/fail/heartbeat so the "
                    "original smoke indicators remain visible"
                ),
                evidence_tokens=(
                    "assign pass_led_o = pass_sticky_q && !fault_sticky_q || gpio_pass_led;",
                    "assign fail_led_o = fault_sticky_q || gpio_fail_led;",
                    "assign heartbeat_led_o = debug_retire_sequence[0] || gpio_heartbeat_led;",
                ),
            ),
            SocTopPeripheralHandoff(
                name="system_identity",
                source="DEBUG_BUILD_ID, IMAGE_SHA256, and reset_cause_q",
                destination="system_identity MMIO window",
                policy="reset cause and build/image identity remain readable through I27-S01 system_identity",
                evidence_tokens=("cpu_v01_fpga_system_identity_mmio #(", ".BUILD_ID({64'd0, DEBUG_BUILD_ID})"),
            ),
        ),
        remaining_handoffs=(
            "I30-S04 arbitrates loader traffic against firmware/status UART ownership.",
            "I30-S05 proves firmware UART output, timer service, GPIO pass/fail, and syscall progress together.",
        ),
    )


def evaluate_soc_top_peripherals(
    *,
    uart_mmio_tx: bool = True,
    status_uart_tx: bool = True,
    timer_compare_irq: bool = False,
    irq_pending_enabled: int = 0,
    pass_sticky: bool = False,
    fault_sticky: bool = False,
    retire_heartbeat: bool = False,
    gpio_pass_led: bool = False,
    gpio_fail_led: bool = False,
    gpio_heartbeat_led: bool = False,
) -> SocTopPeripheralResult:
    if type(irq_pending_enabled) is not int or irq_pending_enabled < 0:
        raise ValueError("irq_pending_enabled must be a nonnegative integer")
    return SocTopPeripheralResult(
        uart_tx_o=bool(uart_mmio_tx and status_uart_tx),
        timer_interrupt_pending=bool(timer_compare_irq),
        external_interrupt_pending=bool(irq_pending_enabled & 0x000B),
        pass_led_o=bool((pass_sticky and not fault_sticky) or gpio_pass_led),
        fail_led_o=bool(fault_sticky or gpio_fail_led),
        heartbeat_led_o=bool(retire_heartbeat or gpio_heartbeat_led),
    )


def fpga_soc_top_peripherals_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_top_peripherals_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_soc_top_peripherals() -> str:
    profile = fpga_soc_top_peripherals_profile()
    lines = [
        "# FPGA SoC Top Peripheral Handoffs",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"Verilator: `{profile.verilator_command}`",
        "",
        "## Handoffs",
        "",
        "| Handoff | Source | Destination | Policy |",
        "| --- | --- | --- | --- |",
    ]
    for handoff in profile.handoffs:
        lines.append(
            f"| `{handoff.name}` | {handoff.source} | {handoff.destination} | {handoff.policy} |"
        )
    lines.extend(["", "## Remaining Handoffs", ""])
    lines.extend(f"- {handoff}" for handoff in profile.remaining_handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_soc_top_peripherals(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_peripherals_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_TOP_PERIPHERALS_STORY:
        issues.append(f"FPGA SoC top peripherals story must be {FPGA_SOC_TOP_PERIPHERALS_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("FPGA SoC top peripherals must target cpu_v01_fpga_top")
    for gate in (
        profile.decoder_gate,
        profile.platform_gate,
        profile.uart_gate,
        profile.timer_gate,
        profile.gpio_gate,
        profile.reset_cdc_gate,
    ):
        if not gate.startswith("python tools\\"):
            issues.append(f"unexpected peripheral handoff dependency gate {gate}")

    for path in (
        *FPGA_SOC_TOP_PERIPHERALS_SOURCES,
        FPGA_SOC_TOP_PERIPHERALS_TEST,
        FPGA_SOC_TOP_PERIPHERALS_DOC,
    ):
        if not (root / path).exists():
            issues.append(f"missing FPGA SoC top peripheral artifact {path.as_posix()}")

    expected_interrupts = ("uart_rx_ready", "uart_tx_ready", "timer_compare", "gpio_status")
    if profile.interrupt_lines != expected_interrupts:
        issues.append("FPGA SoC top peripheral interrupt lines must match I27-S01 order")
    for name in (
        "firmware_uart_rx",
        "uart_tx_mux",
        "timer_interrupt",
        "external_interrupts",
        "gpio_status_leds",
        "system_identity",
    ):
        try:
            profile.handoff_by_name(name)
        except KeyError:
            issues.append(f"missing top peripheral handoff {name}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC top peripheral profile is not JSON serializable: {exc}")

    demo = evaluate_soc_top_peripherals(
        uart_mmio_tx=False,
        status_uart_tx=True,
        timer_compare_irq=True,
        irq_pending_enabled=0x0009,
        gpio_pass_led=True,
        gpio_heartbeat_led=True,
    )
    if demo.uart_tx_o or not demo.timer_interrupt_pending or not demo.external_interrupt_pending:
        issues.append("FPGA SoC top peripheral executable handoff demo did not assert expected outputs")
    if not demo.pass_led_o or not demo.heartbeat_led_o or demo.fail_led_o:
        issues.append("FPGA SoC top peripheral executable LED demo mismatch")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / FPGA_SOC_TOP_PERIPHERALS_TESTBENCH)
    doc = _read_if_exists(root / FPGA_SOC_TOP_PERIPHERALS_DOC)

    for handoff in profile.handoffs:
        for token in handoff.evidence_tokens:
            if token not in top:
                issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_top_soc_peripherals_tb",
        ".uart_rx_i(uart_rx_i)",
        "FPGA SoC top peripherals did not wire firmware UART RX",
        "FPGA SoC top peripherals UART TX mux policy mismatch",
        "FPGA SoC top peripherals did not route timer interrupt pending",
        "FPGA SoC top peripherals external interrupt aggregate mismatch",
        "FPGA SoC top peripherals GPIO pass LED mux mismatch",
        "FPGA SoC top peripherals reset-idle status projection changed",
    ):
        if token not in tb:
            issues.append(f"{FPGA_SOC_TOP_PERIPHERALS_TESTBENCH.as_posix()} missing {token}")

    for token in (
        "Story: I30-S03",
        FPGA_SOC_TOP_PERIPHERALS_TOOL,
        "rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv",
        "uart_rx_i",
        "assign uart_tx_o = uart_mmio_tx & status_uart_tx;",
        "timer_interrupt_pending",
        "external_interrupt_pending",
        "GPIO/status LEDs",
        "system_identity",
        "I30-S04",
        "I30-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_TOP_PERIPHERALS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

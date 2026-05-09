"""Minimal FPGA SoC platform profile and MMIO map.

Owner stories:
- I27-S01: define the minimal FPGA SoC platform profile and MMIO map.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_board_archive, fpga_first_test, platform


JsonValue = Any

FPGA_SOC_PLATFORM_STORY = "I27-S01"
FPGA_SOC_PLATFORM_DOC = Path("docs/implementation/fpga-soc-platform.md")
FPGA_SOC_PLATFORM_TOOL = "python tools\\fpga_soc_platform.py --check"
FPGA_SOC_PROFILE_NAME = "cpu_v01_fpga_minimal_soc"
FPGA_SOC_MMIO_BASE = platform.DEVICE_BASE
FPGA_SOC_MMIO_CELLS = platform.DEVICE_CELLS


@dataclass(frozen=True)
class FpgaSocRegister:
    name: str
    offset_cell: int
    width_bits: int
    access: str
    reset_value: int
    purpose: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("register name must not be empty")
        if type(self.offset_cell) is not int or self.offset_cell < 0:
            raise ValueError("register offset_cell must be a nonnegative int")
        if type(self.width_bits) is not int or self.width_bits <= 0 or self.width_bits > 48:
            raise ValueError("register width_bits must be in 1..48")
        if self.access not in {"ro", "wo", "rw", "w1c"}:
            raise ValueError("register access must be ro, wo, rw, or w1c")
        if type(self.reset_value) is not int or self.reset_value < 0:
            raise ValueError("register reset_value must be a nonnegative int")
        if not self.purpose:
            raise ValueError("register purpose must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "offset_cell": self.offset_cell,
            "width_bits": self.width_bits,
            "access": self.access,
            "reset_value": self.reset_value,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FpgaSocPeripheral:
    name: str
    base_cell: int
    size_cells: int
    role: str
    owner_story: str
    registers: tuple[FpgaSocRegister, ...]
    interrupt_lines: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("peripheral name must not be empty")
        object.__setattr__(self, "base_cell", platform.require_cell_address(self.base_cell) if hasattr(platform, "require_cell_address") else self.base_cell)
        if type(self.size_cells) is not int or self.size_cells <= 0:
            raise ValueError("peripheral size_cells must be positive")
        if not self.role:
            raise ValueError("peripheral role must not be empty")
        if not self.owner_story:
            raise ValueError("peripheral owner_story must not be empty")
        object.__setattr__(self, "registers", tuple(self.registers))
        object.__setattr__(self, "interrupt_lines", tuple(self.interrupt_lines))
        if not self.registers:
            raise ValueError("peripheral must expose at least one register")
        for register in self.registers:
            if not isinstance(register, FpgaSocRegister):
                raise TypeError("registers must contain FpgaSocRegister values")
            if register.offset_cell >= self.size_cells:
                raise ValueError(f"register {register.name} is outside peripheral {self.name}")

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    def contains(self, address: int) -> bool:
        return self.base_cell <= address < self.end_cell

    def register_by_name(self, name: str) -> FpgaSocRegister:
        normalized = name.upper()
        for register in self.registers:
            if register.name.upper() == normalized:
                return register
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "role": self.role,
            "owner_story": self.owner_story,
            "registers": [register.as_dict() for register in self.registers],
            "interrupt_lines": list(self.interrupt_lines),
        }


@dataclass(frozen=True)
class FpgaSocPlatformProfile:
    name: str
    story: str
    board: str
    fpga_top_module: str
    reset_vector: int
    mmio_base_cell: int
    mmio_size_cells: int
    upstream_board_gate: str
    peripherals: tuple[FpgaSocPeripheral, ...]
    interrupt_lines: tuple[str, ...]
    non_goals: tuple[str, ...]

    def peripheral_by_name(self, name: str) -> FpgaSocPeripheral:
        normalized = name.lower()
        for peripheral in self.peripherals:
            if peripheral.name.lower() == normalized:
                return peripheral
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "story": self.story,
            "board": self.board,
            "fpga_top_module": self.fpga_top_module,
            "reset_vector": self.reset_vector,
            "mmio_base_cell": self.mmio_base_cell,
            "mmio_end_cell": self.mmio_base_cell + self.mmio_size_cells,
            "mmio_size_cells": self.mmio_size_cells,
            "upstream_board_gate": self.upstream_board_gate,
            "peripherals": [peripheral.as_dict() for peripheral in self.peripherals],
            "interrupt_lines": list(self.interrupt_lines),
            "non_goals": list(self.non_goals),
        }


def fpga_soc_platform_profile() -> FpgaSocPlatformProfile:
    return FpgaSocPlatformProfile(
        name=FPGA_SOC_PROFILE_NAME,
        story=FPGA_SOC_PLATFORM_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        fpga_top_module=fpga_first_test.FPGA_TOP_MODULE,
        reset_vector=platform.RESET_VECTOR,
        mmio_base_cell=FPGA_SOC_MMIO_BASE,
        mmio_size_cells=FPGA_SOC_MMIO_CELLS,
        upstream_board_gate=fpga_first_board_archive.FPGA_ARCHIVE_TOOL,
        peripherals=(
            _uart_peripheral(),
            _timer_peripheral(),
            _gpio_status_peripheral(),
            _interrupt_controller_peripheral(),
            _system_identity_peripheral(),
        ),
        interrupt_lines=(
            "uart_rx_ready",
            "uart_tx_ready",
            "timer_compare",
            "gpio_status",
        ),
        non_goals=(
            "external_ddr_controller",
            "cache_coherent_interconnect",
            "multi_core_startup",
            "DMA_or_bus_mastering",
            "program_loader_protocol",
        ),
    )


def fpga_soc_platform_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_platform_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_soc_platform() -> str:
    profile = fpga_soc_platform_profile()
    lines = [
        "# FPGA SoC Platform",
        "",
        f"Story: `{profile.story}`",
        f"Profile: `{profile.name}`",
        f"Board: `{profile.board}`",
        f"Top: `{profile.fpga_top_module}`",
        f"MMIO: `0x{profile.mmio_base_cell:08X}`..`0x{profile.mmio_base_cell + profile.mmio_size_cells:08X}`",
        "",
        "## Peripherals",
        "",
        "| Peripheral | Base | Size | Role |",
        "| --- | --- | --- | --- |",
    ]
    for peripheral in profile.peripherals:
        lines.append(
            f"| `{peripheral.name}` | `0x{peripheral.base_cell:08X}` | "
            f"`0x{peripheral.size_cells:X}` | {peripheral.role} |"
        )
    return "\n".join(lines)


def validate_fpga_soc_platform(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_platform_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_PLATFORM_STORY:
        issues.append("FPGA SoC profile story mismatch")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("FPGA SoC board must match I23-S01")
    if profile.fpga_top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("FPGA SoC top module must match the FPGA wrapper")
    if profile.reset_vector != platform.RESET_VECTOR:
        issues.append("FPGA SoC reset vector must match the test platform")

    platform_issues = platform.validate_profile()
    issues.extend(platform_issues)
    device_region = platform.TEST_PLATFORM_PROFILE.region_by_name("platform_devices")
    if profile.mmio_base_cell != device_region.base or profile.mmio_size_cells != device_region.size_cells:
        issues.append("FPGA SoC MMIO window must equal platform_devices")
    if profile.mmio_base_cell + profile.mmio_size_cells != platform.MAILBOX_BASE:
        issues.append("FPGA SoC MMIO window must end before the secondary mailbox")

    peripheral_names = [peripheral.name for peripheral in profile.peripherals]
    if len(peripheral_names) != len(set(peripheral_names)):
        issues.append("FPGA SoC peripheral names are not unique")
    for required in ("uart", "timer", "gpio_status", "interrupt_controller", "system_identity"):
        if required not in peripheral_names:
            issues.append(f"missing FPGA SoC peripheral {required}")

    for index, peripheral in enumerate(profile.peripherals):
        if not device_region.contains(peripheral.base_cell) or peripheral.end_cell > device_region.end:
            issues.append(f"peripheral {peripheral.name} is outside platform_devices")
        for other in profile.peripherals[index + 1 :]:
            if peripheral.base_cell < other.end_cell and other.base_cell < peripheral.end_cell:
                issues.append(f"peripherals {peripheral.name} and {other.name} overlap")
        register_names = [register.name for register in peripheral.registers]
        if len(register_names) != len(set(register_names)):
            issues.append(f"{peripheral.name} register names are not unique")

    _require_registers(
        profile,
        "uart",
        ("UART_TXDATA", "UART_RXDATA", "UART_STATUS", "UART_CONTROL", "UART_BAUD_DIV"),
        issues,
    )
    _require_registers(
        profile,
        "timer",
        ("TIMER_VALUE", "TIMER_COMPARE", "TIMER_CONTROL", "TIMER_STATUS"),
        issues,
    )
    _require_registers(
        profile,
        "gpio_status",
        ("GPIO_OUT", "GPIO_IN", "GPIO_DIR", "STATUS_LEDS", "DEBUG_STATUS_SELECT"),
        issues,
    )
    _require_registers(
        profile,
        "interrupt_controller",
        ("IRQ_PENDING", "IRQ_ENABLE", "IRQ_ACK", "IRQ_FORCE"),
        issues,
    )
    _require_registers(
        profile,
        "system_identity",
        (
            "RESET_CAUSE",
            "BUILD_ID_LO",
            "BUILD_ID_HI",
            "IMAGE_SHA256_0",
            "IMAGE_SHA256_1",
            "IMAGE_SHA256_2",
            "IMAGE_SHA256_3",
            "IMAGE_SHA256_4",
            "IMAGE_SHA256_5",
        ),
        issues,
    )

    for line in ("uart_rx_ready", "uart_tx_ready", "timer_compare", "gpio_status"):
        if line not in profile.interrupt_lines:
            issues.append(f"missing interrupt line {line}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC profile is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_SOC_PLATFORM_DOC)
    for token in (
        "Story: I27-S01",
        FPGA_SOC_PLATFORM_TOOL,
        "python tools\\fpga_first_test_profile.py --check",
        "python tools\\fpga_first_board_archive.py --check",
        "platform_devices",
        "0x00F00000",
        "0x00F01000",
        "uart",
        "timer",
        "gpio_status",
        "interrupt_controller",
        "system_identity",
        "UART_TXDATA",
        "TIMER_COMPARE",
        "GPIO_OUT",
        "IRQ_PENDING",
        "RESET_CAUSE",
        "IMAGE_SHA256_0",
        "I27-S02",
        "I27-S03",
        "I27-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_PLATFORM_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _uart_peripheral() -> FpgaSocPeripheral:
    return FpgaSocPeripheral(
        name="uart",
        base_cell=FPGA_SOC_MMIO_BASE + 0x000,
        size_cells=0x100,
        role="8-bit UART TX/RX MMIO and loader command transport",
        owner_story="I27-S02",
        interrupt_lines=("uart_rx_ready", "uart_tx_ready"),
        registers=(
            FpgaSocRegister("UART_TXDATA", 0x00, 8, "wo", 0, "Write low byte to transmit FIFO."),
            FpgaSocRegister("UART_RXDATA", 0x01, 8, "ro", 0, "Read low byte from receive FIFO."),
            FpgaSocRegister("UART_STATUS", 0x02, 8, "ro", 0x01, "TX ready, RX valid, overrun, and frame error bits."),
            FpgaSocRegister("UART_CONTROL", 0x03, 8, "rw", 0, "Enable TX/RX interrupts and clear sticky errors."),
            FpgaSocRegister("UART_BAUD_DIV", 0x04, 32, "rw", 0, "Board-clock baud-rate divisor selected by firmware."),
        ),
    )


def _timer_peripheral() -> FpgaSocPeripheral:
    return FpgaSocPeripheral(
        name="timer",
        base_cell=FPGA_SOC_MMIO_BASE + 0x100,
        size_cells=0x100,
        role="single 48-bit machine timer and compare interrupt",
        owner_story="I27-S03",
        interrupt_lines=("timer_compare",),
        registers=(
            FpgaSocRegister("TIMER_VALUE", 0x00, 48, "ro", 0, "Free-running cycle counter in the SoC clock domain."),
            FpgaSocRegister("TIMER_COMPARE", 0x01, 48, "rw", 0, "Compare value that raises timer_compare when enabled."),
            FpgaSocRegister("TIMER_CONTROL", 0x02, 4, "rw", 0, "Enable, interrupt enable, one-shot, and clear controls."),
            FpgaSocRegister("TIMER_STATUS", 0x03, 4, "w1c", 0, "Sticky compare pending bit and overflow status."),
        ),
    )


def _gpio_status_peripheral() -> FpgaSocPeripheral:
    return FpgaSocPeripheral(
        name="gpio_status",
        base_cell=FPGA_SOC_MMIO_BASE + 0x200,
        size_cells=0x100,
        role="firmware-visible LEDs, board inputs, and debug-status selection",
        owner_story="I27-S04",
        interrupt_lines=("gpio_status",),
        registers=(
            FpgaSocRegister("GPIO_OUT", 0x00, 16, "rw", 0, "Firmware-controlled LED/status output bits."),
            FpgaSocRegister("GPIO_IN", 0x01, 16, "ro", 0, "Synchronized board input and strap bits."),
            FpgaSocRegister("GPIO_DIR", 0x02, 16, "rw", 0, "Direction mask for firmware-owned GPIO outputs."),
            FpgaSocRegister("STATUS_LEDS", 0x03, 8, "rw", 0, "Pass, fail, heartbeat, and software status LED override bits."),
            FpgaSocRegister("DEBUG_STATUS_SELECT", 0x04, 8, "rw", 0, "Selects which debug/status source drives probes."),
        ),
    )


def _interrupt_controller_peripheral() -> FpgaSocPeripheral:
    return FpgaSocPeripheral(
        name="interrupt_controller",
        base_cell=FPGA_SOC_MMIO_BASE + 0x300,
        size_cells=0x100,
        role="small pending/enable/ack block for FPGA-local interrupts",
        owner_story="I27-S01",
        registers=(
            FpgaSocRegister("IRQ_PENDING", 0x00, 16, "ro", 0, "Pending UART, timer, and GPIO interrupt bits."),
            FpgaSocRegister("IRQ_ENABLE", 0x01, 16, "rw", 0, "Firmware interrupt-enable mask."),
            FpgaSocRegister("IRQ_ACK", 0x02, 16, "w1c", 0, "Write-one-to-clear pending edge interrupts."),
            FpgaSocRegister("IRQ_FORCE", 0x03, 16, "wo", 0, "Simulation-only forced interrupt request mask."),
        ),
    )


def _system_identity_peripheral() -> FpgaSocPeripheral:
    return FpgaSocPeripheral(
        name="system_identity",
        base_cell=FPGA_SOC_MMIO_BASE + 0x400,
        size_cells=0x100,
        role="reset cause, build identity, and selected FPGA image hash",
        owner_story="I27-S01",
        registers=(
            FpgaSocRegister("RESET_CAUSE", 0x00, 16, "w1c", 1, "Sticky power-on, button, loader, and watchdog reset causes."),
            FpgaSocRegister("BUILD_ID_LO", 0x01, 48, "ro", 0, "Low 48 bits of the FPGA build identity."),
            FpgaSocRegister("BUILD_ID_HI", 0x02, 48, "ro", 0, "High 48 bits of the FPGA build identity."),
            FpgaSocRegister("IMAGE_SHA256_0", 0x10, 48, "ro", 0, "Bits 47:0 of the selected I26 image hash."),
            FpgaSocRegister("IMAGE_SHA256_1", 0x11, 48, "ro", 0, "Bits 95:48 of the selected I26 image hash."),
            FpgaSocRegister("IMAGE_SHA256_2", 0x12, 48, "ro", 0, "Bits 143:96 of the selected I26 image hash."),
            FpgaSocRegister("IMAGE_SHA256_3", 0x13, 48, "ro", 0, "Bits 191:144 of the selected I26 image hash."),
            FpgaSocRegister("IMAGE_SHA256_4", 0x14, 48, "ro", 0, "Bits 239:192 of the selected I26 image hash."),
            FpgaSocRegister("IMAGE_SHA256_5", 0x15, 16, "ro", 0, "Bits 255:240 of the selected I26 image hash."),
        ),
    )


def _require_registers(
    profile: FpgaSocPlatformProfile,
    peripheral_name: str,
    register_names: tuple[str, ...],
    issues: list[str],
) -> None:
    try:
        peripheral = profile.peripheral_by_name(peripheral_name)
    except KeyError:
        return
    available = {register.name for register in peripheral.registers}
    for register_name in register_names:
        if register_name not in available:
            issues.append(f"{peripheral_name} missing register {register_name}")


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

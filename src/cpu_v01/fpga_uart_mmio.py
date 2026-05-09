"""Firmware-visible FPGA UART MMIO peripheral contract.

Owner stories:
- I27-S02: integrate a simple UART TX/RX MMIO peripheral.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import fpga_debug_status, fpga_soc_platform, fpga_uart_status


JsonValue = Any

FPGA_UART_MMIO_STORY = "I27-S02"
FPGA_UART_MMIO_DOC = Path("docs/implementation/fpga-uart-mmio.md")
FPGA_UART_MMIO_TOOL = "python tools\\fpga_uart_mmio.py --check"
FPGA_UART_MMIO_BAUD = 115_200
FPGA_UART_MMIO_CLOCK_HZ = 25_000_000
FPGA_UART_MMIO_FIFO_DEPTH = 4
FPGA_UART_MMIO_DEFAULT_BAUD_DIV = max(
    1,
    (FPGA_UART_MMIO_CLOCK_HZ + (FPGA_UART_MMIO_BAUD // 2)) // FPGA_UART_MMIO_BAUD,
)

UART_TXDATA = "UART_TXDATA"
UART_RXDATA = "UART_RXDATA"
UART_STATUS = "UART_STATUS"
UART_CONTROL = "UART_CONTROL"
UART_BAUD_DIV = "UART_BAUD_DIV"

STATUS_TX_READY = 1 << 0
STATUS_TX_EMPTY = 1 << 1
STATUS_RX_VALID = 1 << 2
STATUS_RX_OVERRUN = 1 << 3
STATUS_FRAME_ERROR = 1 << 4
STATUS_TX_IRQ_PENDING = 1 << 5
STATUS_RX_IRQ_PENDING = 1 << 6
STATUS_TX_OVERRUN = 1 << 7

CONTROL_TX_IRQ_ENABLE = 1 << 0
CONTROL_RX_IRQ_ENABLE = 1 << 1
CONTROL_CLEAR_ERRORS = 1 << 2

CELL_MASK = (1 << 24) - 1
BYTE_MASK = 0xFF


@dataclass(frozen=True)
class FpgaUartMmioRegisterBinding:
    name: str
    offset_cell: int
    access: str
    width_bits: int
    reset_value: int
    purpose: str

    @property
    def absolute_cell(self) -> int:
        return fpga_uart_peripheral().base_cell + self.offset_cell

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "offset_cell": self.offset_cell,
            "absolute_cell": self.absolute_cell,
            "access": self.access,
            "width_bits": self.width_bits,
            "reset_value": self.reset_value,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FpgaUartMmioProfile:
    story: str
    soc_gate: str
    packet_gate: str
    status_stream_gate: str
    peripheral_name: str
    base_cell: int
    size_cells: int
    baud: int
    clock_hz: int
    default_baud_div: int
    fifo_depth: int
    registers: tuple[FpgaUartMmioRegisterBinding, ...]
    status_bits: dict[str, int]
    control_bits: dict[str, int]
    interrupt_lines: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    bounded_command_rules: tuple[str, ...]
    wrapper_rules: tuple[str, ...]

    def register_by_name(self, name: str) -> FpgaUartMmioRegisterBinding:
        normalized = name.upper()
        for register in self.registers:
            if register.name.upper() == normalized:
                return register
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "soc_gate": self.soc_gate,
            "packet_gate": self.packet_gate,
            "status_stream_gate": self.status_stream_gate,
            "peripheral_name": self.peripheral_name,
            "base_cell": self.base_cell,
            "size_cells": self.size_cells,
            "baud": self.baud,
            "clock_hz": self.clock_hz,
            "default_baud_div": self.default_baud_div,
            "fifo_depth": self.fifo_depth,
            "registers": [register.as_dict() for register in self.registers],
            "status_bits": dict(self.status_bits),
            "control_bits": dict(self.control_bits),
            "interrupt_lines": list(self.interrupt_lines),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "bounded_command_rules": list(self.bounded_command_rules),
            "wrapper_rules": list(self.wrapper_rules),
        }


@dataclass
class FpgaUartMmioState:
    tx_fifo: list[int] = field(default_factory=list)
    rx_fifo: list[int] = field(default_factory=list)
    control: int = 0
    baud_div: int = FPGA_UART_MMIO_DEFAULT_BAUD_DIV
    rx_overrun: bool = False
    frame_error: bool = False
    tx_overrun: bool = False
    fifo_depth: int = FPGA_UART_MMIO_FIFO_DEPTH

    def read_register(self, register_name: str) -> int:
        register = register_name.upper()
        if register == UART_RXDATA:
            if not self.rx_fifo:
                return 0
            return self.rx_fifo.pop(0) & BYTE_MASK
        if register == UART_STATUS:
            return self.status()
        if register == UART_CONTROL:
            return self.control & BYTE_MASK
        if register == UART_BAUD_DIV:
            return self.baud_div & CELL_MASK
        if register == UART_TXDATA:
            raise PermissionError("UART_TXDATA is write-only")
        raise KeyError(register_name)

    def write_register(self, register_name: str, value: int) -> None:
        register = register_name.upper()
        cell_value = value & CELL_MASK
        if register == UART_TXDATA:
            if len(self.tx_fifo) >= self.fifo_depth:
                self.tx_overrun = True
            else:
                self.tx_fifo.append(cell_value & BYTE_MASK)
            return
        if register == UART_CONTROL:
            if cell_value & CONTROL_CLEAR_ERRORS:
                self.rx_overrun = False
                self.frame_error = False
                self.tx_overrun = False
            self.control = cell_value & (CONTROL_TX_IRQ_ENABLE | CONTROL_RX_IRQ_ENABLE)
            return
        if register == UART_BAUD_DIV:
            self.baud_div = max(1, cell_value)
            return
        if register in {UART_RXDATA, UART_STATUS}:
            raise PermissionError(f"{register} is read-only")
        raise KeyError(register_name)

    def receive_byte(self, value: int, *, frame_ok: bool = True) -> None:
        if not frame_ok:
            self.frame_error = True
            return
        if len(self.rx_fifo) >= self.fifo_depth:
            self.rx_overrun = True
            return
        self.rx_fifo.append(value & BYTE_MASK)

    def host_transmit_byte(self) -> int | None:
        if not self.tx_fifo:
            return None
        return self.tx_fifo.pop(0) & BYTE_MASK

    def status(self) -> int:
        tx_ready = len(self.tx_fifo) < self.fifo_depth
        rx_valid = bool(self.rx_fifo)
        status = 0
        if tx_ready:
            status |= STATUS_TX_READY
        if not self.tx_fifo:
            status |= STATUS_TX_EMPTY
        if rx_valid:
            status |= STATUS_RX_VALID
        if self.rx_overrun:
            status |= STATUS_RX_OVERRUN
        if self.frame_error:
            status |= STATUS_FRAME_ERROR
        if self.control & CONTROL_TX_IRQ_ENABLE and tx_ready:
            status |= STATUS_TX_IRQ_PENDING
        if self.control & CONTROL_RX_IRQ_ENABLE and rx_valid:
            status |= STATUS_RX_IRQ_PENDING
        if self.tx_overrun:
            status |= STATUS_TX_OVERRUN
        return status

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "tx_fifo": list(self.tx_fifo),
            "rx_fifo": list(self.rx_fifo),
            "control": self.control,
            "baud_div": self.baud_div,
            "status": self.status(),
            "rx_overrun": self.rx_overrun,
            "frame_error": self.frame_error,
            "tx_overrun": self.tx_overrun,
            "fifo_depth": self.fifo_depth,
        }


def fpga_uart_peripheral() -> fpga_soc_platform.FpgaSocPeripheral:
    return fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("uart")


def fpga_uart_mmio_profile() -> FpgaUartMmioProfile:
    peripheral = fpga_uart_peripheral()
    return FpgaUartMmioProfile(
        story=FPGA_UART_MMIO_STORY,
        soc_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        status_stream_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        peripheral_name=peripheral.name,
        base_cell=peripheral.base_cell,
        size_cells=peripheral.size_cells,
        baud=FPGA_UART_MMIO_BAUD,
        clock_hz=FPGA_UART_MMIO_CLOCK_HZ,
        default_baud_div=FPGA_UART_MMIO_DEFAULT_BAUD_DIV,
        fifo_depth=FPGA_UART_MMIO_FIFO_DEPTH,
        registers=_register_bindings(peripheral),
        status_bits={
            "TX_READY": STATUS_TX_READY,
            "TX_EMPTY": STATUS_TX_EMPTY,
            "RX_VALID": STATUS_RX_VALID,
            "RX_OVERRUN": STATUS_RX_OVERRUN,
            "FRAME_ERROR": STATUS_FRAME_ERROR,
            "TX_IRQ_PENDING": STATUS_TX_IRQ_PENDING,
            "RX_IRQ_PENDING": STATUS_RX_IRQ_PENDING,
            "TX_OVERRUN": STATUS_TX_OVERRUN,
        },
        control_bits={
            "TX_IRQ_ENABLE": CONTROL_TX_IRQ_ENABLE,
            "RX_IRQ_ENABLE": CONTROL_RX_IRQ_ENABLE,
            "CLEAR_ERRORS": CONTROL_CLEAR_ERRORS,
        },
        interrupt_lines=peripheral.interrupt_lines,
        rtl_sources=(
            "rtl/cpu_v01_pkg.sv",
            "rtl/cpu_v01_fpga_uart_mmio.sv",
            "rtl/cpu_v01_fpga_uart_mmio_tb.sv",
        ),
        verilator_commands=(
            "verilator --lint-only --timing --top-module cpu_v01_fpga_uart_mmio_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_uart_mmio.sv "
            "rtl/cpu_v01_fpga_uart_mmio_tb.sv",
        ),
        bounded_command_rules=(
            "RX command bytes enter a four-byte FIFO and set RX_OVERRUN rather than overwriting old bytes.",
            "TX status text or packets enter a four-byte FIFO and set TX_OVERRUN when firmware writes while full.",
            "UART_CONTROL CLEAR_ERRORS clears sticky overrun and frame-error state without dropping queued bytes.",
        ),
        wrapper_rules=(
            "The peripheral decodes absolute cell addresses inside the I27-S01 uart window.",
            "The I25-S02 status streamer remains a debug sideband and is not backpressured by firmware UART traffic.",
            "A later SoC shell must arbitrate the physical UART pins before both debug/status and firmware UART TX are enabled together.",
        ),
    )


def fpga_uart_mmio_state() -> FpgaUartMmioState:
    return FpgaUartMmioState()


def fpga_uart_mmio_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_uart_mmio_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_uart_mmio_verilator_commands() -> tuple[str, ...]:
    return fpga_uart_mmio_profile().verilator_commands


def render_fpga_uart_mmio() -> str:
    profile = fpga_uart_mmio_profile()
    lines = [
        "# FPGA UART MMIO",
        "",
        f"Story: `{profile.story}`",
        f"Peripheral: `{profile.peripheral_name}` at `0x{profile.base_cell:08X}`",
        f"Default baud: `{profile.baud}`",
        f"Default baud divisor: `{profile.default_baud_div}`",
        f"FIFO depth: `{profile.fifo_depth}`",
        "",
        "## Registers",
        "",
        "| Register | Cell | Access | Width | Reset | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for register in profile.registers:
        lines.append(
            f"| `{register.name}` | `0x{register.absolute_cell:08X}` | "
            f"`{register.access}` | `{register.width_bits}` | "
            f"`0x{register.reset_value:X}` | {register.purpose} |"
        )
    return "\n".join(lines)


def validate_fpga_uart_mmio(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_uart_mmio_profile()
    issues: list[str] = []

    if profile.story != FPGA_UART_MMIO_STORY:
        issues.append("FPGA UART MMIO story mismatch")
    if profile.soc_gate != fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL:
        issues.append("FPGA UART MMIO must validate against I27-S01")
    if profile.packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("FPGA UART MMIO must preserve the I25-S01 packet gate")
    if profile.status_stream_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("FPGA UART MMIO must name the I25-S02 sideband streamer gate")
    if profile.baud != fpga_uart_status.FPGA_UART_STATUS_BAUD:
        issues.append("FPGA UART MMIO baud must match the board status UART baud")
    if profile.clock_hz != fpga_uart_status.FPGA_UART_STATUS_CLOCK_HZ:
        issues.append("FPGA UART MMIO clock must match the FPGA status clock")
    if profile.default_baud_div != 217:
        issues.append("FPGA UART MMIO default divisor must be 217 for 25 MHz / 115200")
    if profile.fifo_depth != 4:
        issues.append("FPGA UART MMIO FIFO depth must be four bytes")
    if profile.base_cell != fpga_soc_platform.FPGA_SOC_MMIO_BASE:
        issues.append("FPGA UART MMIO base must match the I27-S01 uart base")
    if set(profile.interrupt_lines) != {"uart_rx_ready", "uart_tx_ready"}:
        issues.append("FPGA UART MMIO interrupt lines must match the SoC profile")

    required_registers = (UART_TXDATA, UART_RXDATA, UART_STATUS, UART_CONTROL, UART_BAUD_DIV)
    registers = {register.name: register for register in profile.registers}
    for register in required_registers:
        if register not in registers:
            issues.append(f"missing UART MMIO register {register}")
    if registers.get(UART_TXDATA) and registers[UART_TXDATA].access != "wo":
        issues.append("UART_TXDATA must be write-only")
    if registers.get(UART_RXDATA) and registers[UART_RXDATA].access != "ro":
        issues.append("UART_RXDATA must be read-only")
    if registers.get(UART_BAUD_DIV) and registers[UART_BAUD_DIV].width_bits != 24:
        issues.append("UART_BAUD_DIV must fit one CPU cell")

    issues.extend(fpga_soc_platform.validate_fpga_soc_platform(root))
    issues.extend(_validate_model_behavior())
    issues.extend(_validate_files(root, profile))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(fpga_uart_mmio_state().as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA UART MMIO objects are not JSON serializable: {exc}")

    return tuple(issues)


def _register_bindings(
    peripheral: fpga_soc_platform.FpgaSocPeripheral,
) -> tuple[FpgaUartMmioRegisterBinding, ...]:
    return tuple(
        FpgaUartMmioRegisterBinding(
            name=register.name,
            offset_cell=register.offset_cell,
            access=register.access,
            width_bits=register.width_bits,
            reset_value=register.reset_value,
            purpose=register.purpose,
        )
        for register in peripheral.registers
    )


def _validate_model_behavior() -> tuple[str, ...]:
    state = fpga_uart_mmio_state()
    issues: list[str] = []

    if state.status() & STATUS_TX_READY == 0:
        issues.append("fresh UART state must be TX ready")
    if state.status() & STATUS_TX_EMPTY == 0:
        issues.append("fresh UART state must report TX empty")

    state.write_register(UART_TXDATA, 0x155)
    if state.host_transmit_byte() != 0x55:
        issues.append("UART TXDATA write must queue low byte for host transmission")

    state.write_register(UART_CONTROL, CONTROL_TX_IRQ_ENABLE | CONTROL_RX_IRQ_ENABLE)
    if state.status() & STATUS_TX_IRQ_PENDING == 0:
        issues.append("UART TX ready interrupt must assert when enabled and FIFO has space")

    state.receive_byte(0xA6)
    if state.status() & STATUS_RX_VALID == 0:
        issues.append("UART RX byte must set RX_VALID")
    if state.status() & STATUS_RX_IRQ_PENDING == 0:
        issues.append("UART RX ready interrupt must assert when enabled and RX byte is queued")
    if state.read_register(UART_RXDATA) != 0xA6:
        issues.append("UART RXDATA read must return the oldest RX byte")
    if state.status() & STATUS_RX_VALID:
        issues.append("UART RXDATA read must pop the RX byte")

    for value in range(state.fifo_depth + 1):
        state.receive_byte(value)
    if state.status() & STATUS_RX_OVERRUN == 0:
        issues.append("UART RX FIFO overflow must set RX_OVERRUN")
    state.receive_byte(0, frame_ok=False)
    if state.status() & STATUS_FRAME_ERROR == 0:
        issues.append("UART frame error must set FRAME_ERROR")
    state.write_register(UART_CONTROL, CONTROL_CLEAR_ERRORS)
    if state.status() & (STATUS_RX_OVERRUN | STATUS_FRAME_ERROR):
        issues.append("UART CLEAR_ERRORS must clear sticky RX errors")

    return tuple(issues)


def _validate_files(root: Path, profile: FpgaUartMmioProfile) -> tuple[str, ...]:
    issues: list[str] = []
    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing FPGA UART MMIO RTL source {source}")

    rtl = _read_if_exists(root / "rtl" / "cpu_v01_fpga_uart_mmio.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_uart_mmio_tb.sv")
    doc = _read_if_exists(root / FPGA_UART_MMIO_DOC)

    for token in (
        "module cpu_v01_fpga_uart_mmio",
        "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0000",
        "parameter int TX_FIFO_DEPTH = 4",
        "parameter int RX_FIFO_DEPTH = 4",
        "localparam cpu_v01_pkg::addr_t UART_TXDATA_OFFSET = 48'd0",
        "STATUS_TX_READY = 8'h01",
        "STATUS_RX_OVERRUN = 8'h08",
        "CONTROL_CLEAR_ERRORS_BIT = 2",
        "assign req_ready = 1'b1",
        "assign irq_rx_ready_o = control_q[CONTROL_RX_IRQ_ENABLE_BIT] && (rx_count_q != '0)",
        "assign irq_tx_ready_o = control_q[CONTROL_TX_IRQ_ENABLE_BIT] && (tx_count_q < TX_COUNT_BITS'(TX_FIFO_DEPTH))",
        "UART_TXDATA_OFFSET",
        "UART_RXDATA_OFFSET",
        "UART_STATUS_OFFSET",
        "UART_CONTROL_OFFSET",
        "UART_BAUD_DIV_OFFSET",
    ):
        if token not in rtl:
            issues.append(f"cpu_v01_fpga_uart_mmio.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_uart_mmio_tb",
        "cpu_v01_fpga_uart_mmio #(",
        "write_cell(UART_BASE + 48'd0, 24'h000055)",
        "drive_uart_byte(8'hA6)",
        "FPGA UART MMIO TX path did not pull uart_tx_o low",
        "FPGA UART MMIO RX path did not return injected byte",
        "FPGA UART MMIO RX overrun bit did not set",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fpga_uart_mmio_tb.sv missing {token}")

    for token in (
        "Story: I27-S02",
        FPGA_UART_MMIO_TOOL,
        "python tools\\fpga_soc_platform.py --check",
        "python tools\\fpga_debug_status_packet.py --check",
        "python tools\\fpga_uart_status_streamer.py --check",
        "rtl/cpu_v01_fpga_uart_mmio.sv",
        "rtl/cpu_v01_fpga_uart_mmio_tb.sv",
        "UART_TXDATA",
        "UART_RXDATA",
        "UART_STATUS",
        "UART_CONTROL",
        "UART_BAUD_DIV",
        "TX_READY",
        "RX_VALID",
        "RX_OVERRUN",
        "FRAME_ERROR",
        "uart_rx_ready",
        "uart_tx_ready",
        "bounded commands",
        "I26-S04",
        "I25-S02",
    ):
        if token not in doc:
            issues.append(f"{FPGA_UART_MMIO_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

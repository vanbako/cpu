"""Firmware-visible FPGA timer MMIO peripheral contract.

Owner stories:
- I27-S03: add a timer and interrupt source for FPGA firmware.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_soc_platform, kernel


JsonValue = Any

FPGA_TIMER_MMIO_STORY = "I27-S03"
FPGA_TIMER_MMIO_DOC = Path("docs/implementation/fpga-timer-mmio.md")
FPGA_TIMER_MMIO_TOOL = "python tools\\fpga_timer_mmio.py --check"
KERNEL_TIMER_GATE = "python -m unittest tests.conformance.test_i14_s02_kernel_handlers"
CORE_CONTROL_TRAP_GATE = "python tools\\rtl_core_control_trap.py --check"

TIMER_VALUE = "TIMER_VALUE"
TIMER_COMPARE = "TIMER_COMPARE"
TIMER_CONTROL = "TIMER_CONTROL"
TIMER_STATUS = "TIMER_STATUS"

CONTROL_ENABLE = 1 << 0
CONTROL_IRQ_ENABLE = 1 << 1
CONTROL_ONESHOT = 1 << 2
CONTROL_CLEAR_VALUE = 1 << 3

STATUS_PENDING = 1 << 0
STATUS_OVERFLOW = 1 << 1

CELL_MASK = (1 << 24) - 1
TIMER_MASK = (1 << 48) - 1


@dataclass(frozen=True)
class FpgaTimerRegisterBinding:
    name: str
    offset_cell: int
    access: str
    width_bits: int
    reset_value: int
    purpose: str

    @property
    def absolute_cell(self) -> int:
        return fpga_timer_peripheral().base_cell + self.offset_cell

    @property
    def cells(self) -> int:
        return 2 if self.width_bits > 24 else 1

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "offset_cell": self.offset_cell,
            "absolute_cell": self.absolute_cell,
            "access": self.access,
            "width_bits": self.width_bits,
            "cells": self.cells,
            "reset_value": self.reset_value,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FpgaTimerMmioProfile:
    story: str
    soc_gate: str
    kernel_timer_gate: str
    core_control_trap_gate: str
    peripheral_name: str
    base_cell: int
    size_cells: int
    counter_bits: int
    interrupt_line: str
    interrupt_source: str
    interrupt_bit: int
    interrupt_cause_value: int
    registers: tuple[FpgaTimerRegisterBinding, ...]
    control_bits: dict[str, int]
    status_bits: dict[str, int]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    firmware_rules: tuple[str, ...]
    non_interference_rules: tuple[str, ...]

    def register_by_name(self, name: str) -> FpgaTimerRegisterBinding:
        normalized = name.upper()
        for register in self.registers:
            if register.name.upper() == normalized:
                return register
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "soc_gate": self.soc_gate,
            "kernel_timer_gate": self.kernel_timer_gate,
            "core_control_trap_gate": self.core_control_trap_gate,
            "peripheral_name": self.peripheral_name,
            "base_cell": self.base_cell,
            "size_cells": self.size_cells,
            "counter_bits": self.counter_bits,
            "interrupt_line": self.interrupt_line,
            "interrupt_source": self.interrupt_source,
            "interrupt_bit": self.interrupt_bit,
            "interrupt_cause_value": self.interrupt_cause_value,
            "registers": [register.as_dict() for register in self.registers],
            "control_bits": dict(self.control_bits),
            "status_bits": dict(self.status_bits),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "firmware_rules": list(self.firmware_rules),
            "non_interference_rules": list(self.non_interference_rules),
        }


@dataclass
class FpgaTimerMmioState:
    value: int = 0
    compare: int = 0
    control: int = 0
    status: int = 0

    def tick(self, cycles: int = 1) -> None:
        if cycles < 0:
            raise ValueError("cycles must be nonnegative")
        for _ in range(cycles):
            if not self.control & CONTROL_ENABLE:
                continue
            old_value = self.value
            self.value = (self.value + 1) & TIMER_MASK
            if self.value < old_value:
                self.status |= STATUS_OVERFLOW
            if self.value >= self.compare:
                self.status |= STATUS_PENDING
                if self.control & CONTROL_ONESHOT:
                    self.control &= ~CONTROL_ENABLE

    def read_register(self, register_name: str) -> int:
        register = register_name.upper()
        if register == TIMER_VALUE:
            return self.value & TIMER_MASK
        if register == TIMER_COMPARE:
            return self.compare & TIMER_MASK
        if register == TIMER_CONTROL:
            return self.control & 0x7
        if register == TIMER_STATUS:
            return self.status & 0x3
        raise KeyError(register_name)

    def write_register(self, register_name: str, value: int) -> None:
        register = register_name.upper()
        if register == TIMER_COMPARE:
            self.compare = value & TIMER_MASK
            return
        if register == TIMER_CONTROL:
            if value & CONTROL_CLEAR_VALUE:
                self.value = 0
                self.status = 0
            self.control = value & (CONTROL_ENABLE | CONTROL_IRQ_ENABLE | CONTROL_ONESHOT)
            return
        if register == TIMER_STATUS:
            self.status &= ~(value & (STATUS_PENDING | STATUS_OVERFLOW))
            return
        if register == TIMER_VALUE:
            raise PermissionError("TIMER_VALUE is read-only")
        raise KeyError(register_name)

    @property
    def interrupt_pending(self) -> bool:
        return bool((self.control & CONTROL_IRQ_ENABLE) and (self.status & STATUS_PENDING))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "value": self.value,
            "compare": self.compare,
            "control": self.control,
            "status": self.status,
            "interrupt_pending": self.interrupt_pending,
        }


def fpga_timer_peripheral() -> fpga_soc_platform.FpgaSocPeripheral:
    return fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("timer")


def fpga_timer_mmio_profile() -> FpgaTimerMmioProfile:
    peripheral = fpga_timer_peripheral()
    timer_source = kernel.InterruptSource.TIMER
    return FpgaTimerMmioProfile(
        story=FPGA_TIMER_MMIO_STORY,
        soc_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        kernel_timer_gate=KERNEL_TIMER_GATE,
        core_control_trap_gate=CORE_CONTROL_TRAP_GATE,
        peripheral_name=peripheral.name,
        base_cell=peripheral.base_cell,
        size_cells=peripheral.size_cells,
        counter_bits=48,
        interrupt_line="timer_compare",
        interrupt_source=timer_source.name.lower(),
        interrupt_bit=timer_source.bit,
        interrupt_cause_value=timer_source.cause_value,
        registers=_register_bindings(peripheral),
        control_bits={
            "ENABLE": CONTROL_ENABLE,
            "IRQ_ENABLE": CONTROL_IRQ_ENABLE,
            "ONESHOT": CONTROL_ONESHOT,
            "CLEAR_VALUE": CONTROL_CLEAR_VALUE,
        },
        status_bits={
            "PENDING": STATUS_PENDING,
            "OVERFLOW": STATUS_OVERFLOW,
        },
        rtl_sources=(
            "rtl/cpu_v01_pkg.sv",
            "rtl/cpu_v01_fpga_timer_mmio.sv",
            "rtl/cpu_v01_fpga_timer_mmio_tb.sv",
        ),
        verilator_commands=(
            "verilator --lint-only --timing --top-module cpu_v01_fpga_timer_mmio_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_timer_mmio.sv "
            "rtl/cpu_v01_fpga_timer_mmio_tb.sv",
        ),
        firmware_rules=(
            "Firmware writes TIMER_COMPARE as a two-cell 48-bit value before enabling the timer.",
            "Firmware acknowledges timer_compare by writing STATUS_PENDING to TIMER_STATUS.",
            "One-shot mode clears ENABLE after the first pending compare event.",
        ),
        non_interference_rules=(
            "The timer interrupt output is a level derived from TIMER_STATUS and TIMER_CONTROL.",
            "Acknowledgement clears only the timer pending bit and does not change UART or GPIO state.",
            "The first-test pass/fail LEDs remain driven by the existing retire/fault path until I27-S05 wires handler progress.",
        ),
    )


def fpga_timer_mmio_state() -> FpgaTimerMmioState:
    return FpgaTimerMmioState()


def fpga_timer_mmio_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_timer_mmio_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_timer_mmio_verilator_commands() -> tuple[str, ...]:
    return fpga_timer_mmio_profile().verilator_commands


def render_fpga_timer_mmio() -> str:
    profile = fpga_timer_mmio_profile()
    lines = [
        "# FPGA Timer MMIO",
        "",
        f"Story: `{profile.story}`",
        f"Peripheral: `{profile.peripheral_name}` at `0x{profile.base_cell:08X}`",
        f"Interrupt: `{profile.interrupt_line}` maps to `{profile.interrupt_source}`",
        "",
        "## Registers",
        "",
        "| Register | Cell | Access | Width | Cells | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for register in profile.registers:
        lines.append(
            f"| `{register.name}` | `0x{register.absolute_cell:08X}` | "
            f"`{register.access}` | `{register.width_bits}` | "
            f"`{register.cells}` | {register.purpose} |"
        )
    return "\n".join(lines)


def validate_fpga_timer_mmio(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_timer_mmio_profile()
    issues: list[str] = []

    if profile.story != FPGA_TIMER_MMIO_STORY:
        issues.append("FPGA timer MMIO story mismatch")
    if profile.soc_gate != fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL:
        issues.append("FPGA timer MMIO must validate against I27-S01")
    if profile.kernel_timer_gate != KERNEL_TIMER_GATE:
        issues.append("FPGA timer MMIO must name the I14-S02 timer handler gate")
    if profile.core_control_trap_gate != CORE_CONTROL_TRAP_GATE:
        issues.append("FPGA timer MMIO must name the I22-S05 control/trap gate")
    if profile.base_cell != fpga_soc_platform.FPGA_SOC_MMIO_BASE + 0x100:
        issues.append("FPGA timer MMIO base must match the I27-S01 timer base")
    if profile.interrupt_line != "timer_compare":
        issues.append("FPGA timer MMIO interrupt line must be timer_compare")
    if profile.interrupt_bit != kernel.InterruptSource.TIMER.bit:
        issues.append("FPGA timer interrupt bit must match the kernel timer source")
    if profile.counter_bits != 48:
        issues.append("FPGA timer counter must be 48 bits")

    registers = {register.name: register for register in profile.registers}
    for register in (TIMER_VALUE, TIMER_COMPARE, TIMER_CONTROL, TIMER_STATUS):
        if register not in registers:
            issues.append(f"missing FPGA timer register {register}")
    if registers.get(TIMER_VALUE) and registers[TIMER_VALUE].cells != 2:
        issues.append("TIMER_VALUE must be read as two CPU cells")
    if registers.get(TIMER_COMPARE) and registers[TIMER_COMPARE].access != "rw":
        issues.append("TIMER_COMPARE must be writable")
    if registers.get(TIMER_STATUS) and registers[TIMER_STATUS].access != "w1c":
        issues.append("TIMER_STATUS must be write-one-to-clear")

    issues.extend(fpga_soc_platform.validate_fpga_soc_platform(root))
    issues.extend(_validate_model_behavior())
    issues.extend(_validate_files(root, profile))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(fpga_timer_mmio_state().as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA timer MMIO objects are not JSON serializable: {exc}")

    return tuple(issues)


def _register_bindings(
    peripheral: fpga_soc_platform.FpgaSocPeripheral,
) -> tuple[FpgaTimerRegisterBinding, ...]:
    return tuple(
        FpgaTimerRegisterBinding(
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
    state = fpga_timer_mmio_state()
    issues: list[str] = []

    state.write_register(TIMER_COMPARE, 3)
    state.write_register(TIMER_CONTROL, CONTROL_ENABLE | CONTROL_IRQ_ENABLE)
    state.tick(2)
    if state.interrupt_pending:
        issues.append("timer interrupt must not assert before compare")
    state.tick(1)
    if not state.interrupt_pending:
        issues.append("timer interrupt must assert at compare")
    state.write_register(TIMER_STATUS, STATUS_PENDING)
    if state.interrupt_pending:
        issues.append("timer acknowledgement must clear interrupt pending")

    state.write_register(TIMER_COMPARE, state.value + 2)
    state.write_register(TIMER_CONTROL, CONTROL_ENABLE | CONTROL_IRQ_ENABLE | CONTROL_ONESHOT)
    state.tick(2)
    if not state.status & STATUS_PENDING:
        issues.append("one-shot timer must set pending at compare")
    if state.control & CONTROL_ENABLE:
        issues.append("one-shot timer must clear enable after compare")

    state.value = TIMER_MASK
    state.write_register(TIMER_CONTROL, CONTROL_ENABLE)
    state.tick(1)
    if not state.status & STATUS_OVERFLOW:
        issues.append("timer wrap must set overflow status")
    state.write_register(TIMER_CONTROL, CONTROL_CLEAR_VALUE)
    if state.value != 0 or state.status != 0:
        issues.append("timer clear-value control must reset value and status")

    return tuple(issues)


def _validate_files(root: Path, profile: FpgaTimerMmioProfile) -> tuple[str, ...]:
    issues: list[str] = []
    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing FPGA timer MMIO RTL source {source}")

    rtl = _read_if_exists(root / "rtl" / "cpu_v01_fpga_timer_mmio.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_timer_mmio_tb.sv")
    doc = _read_if_exists(root / FPGA_TIMER_MMIO_DOC)

    for token in (
        "module cpu_v01_fpga_timer_mmio",
        "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0100",
        "localparam cpu_v01_pkg::addr_t TIMER_VALUE_OFFSET = 48'd0",
        "localparam logic [3:0] CONTROL_ENABLE = 4'h1",
        "localparam logic [3:0] STATUS_PENDING = 4'h1",
        "assign req_ready = 1'b1",
        "assign timer_interrupt_o = control_q[CONTROL_IRQ_ENABLE_BIT] && status_q[STATUS_PENDING_BIT]",
        "pack_timer_value",
        "unpack_timer_value",
        "timer_value_q <= timer_value_q + 48'd1",
    ):
        if token not in rtl:
            issues.append(f"cpu_v01_fpga_timer_mmio.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_timer_mmio_tb",
        "cpu_v01_fpga_timer_mmio #(",
        "write_48(TIMER_BASE + 48'd1, 48'd3)",
        "FPGA timer MMIO did not raise timer_interrupt_o",
        "FPGA timer MMIO acknowledgement did not clear interrupt",
        "FPGA timer MMIO clear-value control did not reset value",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fpga_timer_mmio_tb.sv missing {token}")

    for token in (
        "Story: I27-S03",
        FPGA_TIMER_MMIO_TOOL,
        "python tools\\fpga_soc_platform.py --check",
        KERNEL_TIMER_GATE,
        CORE_CONTROL_TRAP_GATE,
        "rtl/cpu_v01_fpga_timer_mmio.sv",
        "rtl/cpu_v01_fpga_timer_mmio_tb.sv",
        "TIMER_VALUE",
        "TIMER_COMPARE",
        "TIMER_CONTROL",
        "TIMER_STATUS",
        "ENABLE",
        "IRQ_ENABLE",
        "ONESHOT",
        "PENDING",
        "OVERFLOW",
        "timer_compare",
        "STATUS_PENDING",
        "I27-S05",
        "first-test pass/fail",
    ):
        if token not in doc:
            issues.append(f"{FPGA_TIMER_MMIO_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

"""Firmware-visible FPGA GPIO/status MMIO peripheral contract.

Owner stories:
- I27-S04: add GPIO/status MMIO registers for LEDs and diagnostics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_smoke, fpga_soc_platform


JsonValue = Any

FPGA_GPIO_STATUS_STORY = "I27-S04"
FPGA_GPIO_STATUS_DOC = Path("docs/implementation/fpga-gpio-status.md")
FPGA_GPIO_STATUS_TOOL = "python tools\\fpga_gpio_status.py --check"
SMOKE_FIRMWARE_GATE = "python tools\\fpga_smoke_firmware.py --check"

GPIO_OUT = "GPIO_OUT"
GPIO_IN = "GPIO_IN"
GPIO_DIR = "GPIO_DIR"
STATUS_LEDS = "STATUS_LEDS"
DEBUG_STATUS_SELECT = "DEBUG_STATUS_SELECT"

STATUS_LED_PASS = 1 << 0
STATUS_LED_FAIL = 1 << 1
STATUS_LED_HEARTBEAT = 1 << 2
STATUS_LED_SOFTWARE0 = 1 << 3
STATUS_LED_SOFTWARE1 = 1 << 4
STATUS_LED_SOFTWARE2 = 1 << 5
STATUS_LED_SOFTWARE3 = 1 << 6
STATUS_LED_RESERVED = 1 << 7

DEBUG_SELECT_SOFTWARE_FORCE_IRQ = 1 << 7
GPIO_MASK = 0xFFFF
CELL_MASK = (1 << 24) - 1


@dataclass(frozen=True)
class FpgaGpioRegisterBinding:
    name: str
    offset_cell: int
    access: str
    width_bits: int
    reset_value: int
    purpose: str

    @property
    def absolute_cell(self) -> int:
        return fpga_gpio_peripheral().base_cell + self.offset_cell

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
class FpgaGpioStatusProfile:
    story: str
    soc_gate: str
    smoke_firmware_gate: str
    peripheral_name: str
    base_cell: int
    size_cells: int
    gpio_width: int
    interrupt_line: str
    registers: tuple[FpgaGpioRegisterBinding, ...]
    status_led_bits: dict[str, int]
    debug_select_bits: dict[str, int]
    diagnostic_handoff_registers: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    firmware_rules: tuple[str, ...]
    non_interference_rules: tuple[str, ...]

    def register_by_name(self, name: str) -> FpgaGpioRegisterBinding:
        normalized = name.upper()
        for register in self.registers:
            if register.name.upper() == normalized:
                return register
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "soc_gate": self.soc_gate,
            "smoke_firmware_gate": self.smoke_firmware_gate,
            "peripheral_name": self.peripheral_name,
            "base_cell": self.base_cell,
            "size_cells": self.size_cells,
            "gpio_width": self.gpio_width,
            "interrupt_line": self.interrupt_line,
            "registers": [register.as_dict() for register in self.registers],
            "status_led_bits": dict(self.status_led_bits),
            "debug_select_bits": dict(self.debug_select_bits),
            "diagnostic_handoff_registers": list(self.diagnostic_handoff_registers),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "firmware_rules": list(self.firmware_rules),
            "non_interference_rules": list(self.non_interference_rules),
        }


@dataclass
class FpgaGpioStatusState:
    gpio_out: int = 0
    gpio_dir: int = 0
    gpio_in: int = 0
    status_leds: int = 0
    debug_status_select: int = 0
    gpio_changed: bool = False

    def read_register(self, register_name: str) -> int:
        register = register_name.upper()
        if register == GPIO_OUT:
            return self.gpio_out & GPIO_MASK
        if register == GPIO_IN:
            value = self.gpio_in & GPIO_MASK
            self.gpio_changed = False
            return value
        if register == GPIO_DIR:
            return self.gpio_dir & GPIO_MASK
        if register == STATUS_LEDS:
            return self.status_leds & 0xFF
        if register == DEBUG_STATUS_SELECT:
            return self.debug_status_select & 0xFF
        raise KeyError(register_name)

    def write_register(self, register_name: str, value: int) -> None:
        register = register_name.upper()
        cell_value = value & CELL_MASK
        if register == GPIO_OUT:
            self.gpio_out = cell_value & GPIO_MASK
            return
        if register == GPIO_DIR:
            self.gpio_dir = cell_value & GPIO_MASK
            return
        if register == STATUS_LEDS:
            self.status_leds = cell_value & 0xFF
            return
        if register == DEBUG_STATUS_SELECT:
            self.debug_status_select = cell_value & 0xFF
            return
        if register == GPIO_IN:
            raise PermissionError("GPIO_IN is read-only")
        raise KeyError(register_name)

    def set_gpio_inputs(self, value: int) -> None:
        next_value = value & GPIO_MASK
        if next_value != self.gpio_in:
            self.gpio_changed = True
        self.gpio_in = next_value

    @property
    def gpio_outputs(self) -> int:
        return self.gpio_out & self.gpio_dir & GPIO_MASK

    @property
    def pass_led(self) -> bool:
        return bool(self.status_leds & STATUS_LED_PASS)

    @property
    def fail_led(self) -> bool:
        return bool(self.status_leds & STATUS_LED_FAIL)

    @property
    def heartbeat_led(self) -> bool:
        return bool(self.status_leds & STATUS_LED_HEARTBEAT)

    @property
    def status_led_vector(self) -> int:
        return (self.status_leds >> 3) & 0xF

    @property
    def interrupt_pending(self) -> bool:
        return self.gpio_changed or bool(self.debug_status_select & DEBUG_SELECT_SOFTWARE_FORCE_IRQ)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "gpio_out": self.gpio_out,
            "gpio_dir": self.gpio_dir,
            "gpio_in": self.gpio_in,
            "gpio_outputs": self.gpio_outputs,
            "status_leds": self.status_leds,
            "debug_status_select": self.debug_status_select,
            "gpio_changed": self.gpio_changed,
            "pass_led": self.pass_led,
            "fail_led": self.fail_led,
            "heartbeat_led": self.heartbeat_led,
            "status_led_vector": self.status_led_vector,
            "interrupt_pending": self.interrupt_pending,
        }


def fpga_gpio_peripheral() -> fpga_soc_platform.FpgaSocPeripheral:
    return fpga_soc_platform.fpga_soc_platform_profile().peripheral_by_name("gpio_status")


def fpga_gpio_status_profile() -> FpgaGpioStatusProfile:
    peripheral = fpga_gpio_peripheral()
    return FpgaGpioStatusProfile(
        story=FPGA_GPIO_STATUS_STORY,
        soc_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        smoke_firmware_gate=SMOKE_FIRMWARE_GATE,
        peripheral_name=peripheral.name,
        base_cell=peripheral.base_cell,
        size_cells=peripheral.size_cells,
        gpio_width=16,
        interrupt_line="gpio_status",
        registers=_register_bindings(peripheral),
        status_led_bits={
            "PASS": STATUS_LED_PASS,
            "FAIL": STATUS_LED_FAIL,
            "HEARTBEAT": STATUS_LED_HEARTBEAT,
            "SOFTWARE0": STATUS_LED_SOFTWARE0,
            "SOFTWARE1": STATUS_LED_SOFTWARE1,
            "SOFTWARE2": STATUS_LED_SOFTWARE2,
            "SOFTWARE3": STATUS_LED_SOFTWARE3,
            "RESERVED": STATUS_LED_RESERVED,
        },
        debug_select_bits={
            "SOFTWARE_FORCE_IRQ": DEBUG_SELECT_SOFTWARE_FORCE_IRQ,
        },
        diagnostic_handoff_registers=(
            "RESET_CAUSE",
            "BUILD_ID_LO",
            "BUILD_ID_HI",
            "IMAGE_SHA256_0",
        ),
        rtl_sources=(
            "rtl/cpu_v01_pkg.sv",
            "rtl/cpu_v01_fpga_gpio_status.sv",
            "rtl/cpu_v01_fpga_gpio_status_tb.sv",
        ),
        verilator_commands=(
            "verilator --lint-only --timing --top-module cpu_v01_fpga_gpio_status_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_gpio_status.sv "
            "rtl/cpu_v01_fpga_gpio_status_tb.sv",
        ),
        firmware_rules=(
            "Firmware writes GPIO_DIR before relying on GPIO_OUT-driven pins.",
            "STATUS_LEDS bit 0, bit 1, and bit 2 drive pass, fail, and heartbeat outputs.",
            "Firmware reads GPIO_IN to observe board inputs and clear the GPIO changed interrupt.",
            "Reset cause, build ID, and image hash diagnostics remain in the I27-S01 system_identity window.",
        ),
        non_interference_rules=(
            "GPIO/status writes do not modify the retire-driven first-test pass/fail latches until a later top-level mux is added.",
            "Debug-status selection only changes exported probe/status source selection.",
            "GPIO input change interrupt is local to gpio_status and does not acknowledge UART or timer sources.",
        ),
    )


def fpga_gpio_status_state() -> FpgaGpioStatusState:
    return FpgaGpioStatusState()


def fpga_gpio_status_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_gpio_status_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_gpio_status_verilator_commands() -> tuple[str, ...]:
    return fpga_gpio_status_profile().verilator_commands


def render_fpga_gpio_status() -> str:
    profile = fpga_gpio_status_profile()
    lines = [
        "# FPGA GPIO Status",
        "",
        f"Story: `{profile.story}`",
        f"Peripheral: `{profile.peripheral_name}` at `0x{profile.base_cell:08X}`",
        f"Interrupt: `{profile.interrupt_line}`",
        "",
        "## Registers",
        "",
        "| Register | Cell | Access | Width | Purpose |",
        "| --- | --- | --- | --- | --- |",
    ]
    for register in profile.registers:
        lines.append(
            f"| `{register.name}` | `0x{register.absolute_cell:08X}` | "
            f"`{register.access}` | `{register.width_bits}` | {register.purpose} |"
        )
    return "\n".join(lines)


def validate_fpga_gpio_status(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_gpio_status_profile()
    issues: list[str] = []

    if profile.story != FPGA_GPIO_STATUS_STORY:
        issues.append("FPGA GPIO/status story mismatch")
    if profile.soc_gate != fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL:
        issues.append("FPGA GPIO/status must validate against I27-S01")
    if profile.smoke_firmware_gate != SMOKE_FIRMWARE_GATE:
        issues.append("FPGA GPIO/status must name the I23-S04 smoke firmware gate")
    if profile.base_cell != fpga_soc_platform.FPGA_SOC_MMIO_BASE + 0x200:
        issues.append("FPGA GPIO/status base must match the I27-S01 gpio_status base")
    if profile.interrupt_line != "gpio_status":
        issues.append("FPGA GPIO/status interrupt line must be gpio_status")
    if profile.gpio_width != 16:
        issues.append("FPGA GPIO/status GPIO width must be 16")

    registers = {register.name: register for register in profile.registers}
    for register in (GPIO_OUT, GPIO_IN, GPIO_DIR, STATUS_LEDS, DEBUG_STATUS_SELECT):
        if register not in registers:
            issues.append(f"missing GPIO/status register {register}")
    if registers.get(GPIO_IN) and registers[GPIO_IN].access != "ro":
        issues.append("GPIO_IN must be read-only")
    if registers.get(STATUS_LEDS) and registers[STATUS_LEDS].width_bits != 8:
        issues.append("STATUS_LEDS must be 8 bits")
    for diagnostic in profile.diagnostic_handoff_registers:
        if diagnostic not in {
            register.name
            for register in fpga_soc_platform.fpga_soc_platform_profile()
            .peripheral_by_name("system_identity")
            .registers
        }:
            issues.append(f"missing system_identity diagnostic handoff {diagnostic}")

    issues.extend(fpga_soc_platform.validate_fpga_soc_platform(root))
    issues.extend(fpga_smoke.validate_fpga_smoke_firmware(root))
    issues.extend(_validate_model_behavior())
    issues.extend(_validate_files(root, profile))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(fpga_gpio_status_state().as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA GPIO/status objects are not JSON serializable: {exc}")

    return tuple(issues)


def _register_bindings(
    peripheral: fpga_soc_platform.FpgaSocPeripheral,
) -> tuple[FpgaGpioRegisterBinding, ...]:
    return tuple(
        FpgaGpioRegisterBinding(
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
    state = fpga_gpio_status_state()
    issues: list[str] = []

    state.write_register(GPIO_DIR, 0x00FF)
    state.write_register(GPIO_OUT, 0xA5A5)
    if state.gpio_outputs != 0x00A5:
        issues.append("GPIO_OUT must be masked by GPIO_DIR")

    state.write_register(STATUS_LEDS, STATUS_LED_PASS | STATUS_LED_HEARTBEAT | STATUS_LED_SOFTWARE1)
    if not state.pass_led or state.fail_led or not state.heartbeat_led:
        issues.append("STATUS_LEDS must drive pass/fail/heartbeat outputs")
    if state.status_led_vector != 0x2:
        issues.append("STATUS_LEDS software vector must use bits 6:3")

    state.set_gpio_inputs(0x1234)
    if not state.interrupt_pending:
        issues.append("GPIO input changes must set gpio_status interrupt")
    if state.read_register(GPIO_IN) != 0x1234:
        issues.append("GPIO_IN must read synchronized input value")
    if state.interrupt_pending:
        issues.append("GPIO_IN read must clear changed interrupt when no force bit is set")

    state.write_register(DEBUG_STATUS_SELECT, DEBUG_SELECT_SOFTWARE_FORCE_IRQ)
    if not state.interrupt_pending:
        issues.append("DEBUG_STATUS_SELECT software force must assert interrupt")
    state.write_register(DEBUG_STATUS_SELECT, 0)
    if state.interrupt_pending:
        issues.append("clearing DEBUG_STATUS_SELECT force bit must clear forced interrupt")

    return tuple(issues)


def _validate_files(root: Path, profile: FpgaGpioStatusProfile) -> tuple[str, ...]:
    issues: list[str] = []
    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing FPGA GPIO/status RTL source {source}")

    rtl = _read_if_exists(root / "rtl" / "cpu_v01_fpga_gpio_status.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_gpio_status_tb.sv")
    doc = _read_if_exists(root / FPGA_GPIO_STATUS_DOC)

    for token in (
        "module cpu_v01_fpga_gpio_status",
        "parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0200",
        "localparam cpu_v01_pkg::addr_t GPIO_OUT_OFFSET = 48'd0",
        "localparam logic [7:0] STATUS_LED_PASS = 8'h01",
        "localparam int DEBUG_SELECT_FORCE_IRQ_BIT = 7",
        "assign req_ready = 1'b1",
        "assign gpio_out_o = gpio_out_q & gpio_dir_q",
        "assign gpio_status_irq_o = gpio_changed_q || debug_status_select_q[DEBUG_SELECT_FORCE_IRQ_BIT]",
        "gpio_changed_q <= 1'b0",
    ):
        if token not in rtl:
            issues.append(f"cpu_v01_fpga_gpio_status.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_gpio_status_tb",
        "cpu_v01_fpga_gpio_status #(",
        "write_cell(GPIO_BASE + 48'd0, 24'h00A5A5)",
        "FPGA GPIO/status output mask mismatch",
        "FPGA GPIO/status LEDs did not follow STATUS_LEDS",
        "FPGA GPIO/status input change did not assert interrupt",
        "FPGA GPIO/status DEBUG_STATUS_SELECT force did not assert interrupt",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fpga_gpio_status_tb.sv missing {token}")

    for token in (
        "Story: I27-S04",
        FPGA_GPIO_STATUS_TOOL,
        "python tools\\fpga_soc_platform.py --check",
        SMOKE_FIRMWARE_GATE,
        "rtl/cpu_v01_fpga_gpio_status.sv",
        "rtl/cpu_v01_fpga_gpio_status_tb.sv",
        "GPIO_OUT",
        "GPIO_IN",
        "GPIO_DIR",
        "STATUS_LEDS",
        "DEBUG_STATUS_SELECT",
        "PASS",
        "FAIL",
        "HEARTBEAT",
        "gpio_status",
        "RESET_CAUSE",
        "BUILD_ID_LO",
        "I27-S05",
        "first-test pass/fail",
    ):
        if token not in doc:
            issues.append(f"{FPGA_GPIO_STATUS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

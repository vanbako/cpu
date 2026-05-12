"""FPGA SoC top-level data/MMIO decoder contract.

Owner stories:
- I30-S02: replace the direct data-RAM path with a top-level data/MMIO decoder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_gpio_status, fpga_soc_platform, fpga_soc_top_closure
from . import fpga_timer_mmio, fpga_uart_mmio, platform
from . import fpga_video_display


JsonValue = Any

FPGA_SOC_TOP_DECODER_STORY = "I30-S02"
FPGA_SOC_TOP_DECODER_DOC = Path("docs/implementation/fpga-soc-top-decoder.md")
FPGA_SOC_TOP_DECODER_TOOL = "python tools\\fpga_soc_top_decoder.py --check"
FPGA_SOC_TOP_DECODER_TESTBENCH = Path("rtl/cpu_v01_fpga_top_soc_decoder_tb.sv")
FPGA_SOC_TOP_DECODER_TEST = Path("tests/conformance/test_i30_s02_fpga_soc_top_decoder.py")
FPGA_SOC_TOP_DECODER_SOURCES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_uart_mmio.sv"),
    Path("rtl/cpu_v01_fpga_timer_mmio.sv"),
    Path("rtl/cpu_v01_fpga_gpio_status.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    FPGA_SOC_TOP_DECODER_TESTBENCH,
)
FPGA_SOC_TOP_DECODER_VERILATOR_COMMAND = (
    "verilator --lint-only --timing --top-module cpu_v01_fpga_top_soc_decoder_tb "
    "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_memories.sv "
    "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
    "rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv "
    "rtl/cpu_v01_fpga_top_soc_decoder_tb.sv"
)

CELL_MASK = (1 << 24) - 1
MAX_DMEM_TRANSFER_CELLS = 4


@dataclass(frozen=True)
class SocTopDecodeWindow:
    target: str
    base_cell: int
    size_cells: int
    source: str
    tag_sidecar: bool

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    def contains_start(self, address: int) -> bool:
        return self.base_cell <= address < self.end_cell

    def contains_transfer(self, address: int, len_cells: int) -> bool:
        if len_cells <= 0:
            return False
        return self.base_cell <= address and address + len_cells <= self.end_cell

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "target": self.target,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "source": self.source,
            "tag_sidecar": self.tag_sidecar,
        }


@dataclass(frozen=True)
class SocTopDecodeResult:
    address: int
    len_cells: int
    write: bool
    target: str
    response: str
    fault_on_read: bool
    tag_sidecar: bool
    note: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "address": self.address,
            "len_cells": self.len_cells,
            "write": self.write,
            "target": self.target,
            "response": self.response,
            "fault_on_read": self.fault_on_read,
            "tag_sidecar": self.tag_sidecar,
            "note": self.note,
        }


@dataclass(frozen=True)
class SocTopDecoderProfile:
    story: str
    top_module: str
    closure_gate: str
    platform_gate: str
    uart_gate: str
    timer_gate: str
    gpio_gate: str
    video_gate: str
    validator: str
    testbench: str
    verilator_command: str
    windows: tuple[SocTopDecodeWindow, ...]
    reserved_fault_policy: str
    tag_policy: str
    remaining_handoffs: tuple[str, ...]

    def window_by_target(self, target: str) -> SocTopDecodeWindow:
        for window in self.windows:
            if window.target == target:
                return window
        raise KeyError(target)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "closure_gate": self.closure_gate,
            "platform_gate": self.platform_gate,
            "uart_gate": self.uart_gate,
            "timer_gate": self.timer_gate,
            "gpio_gate": self.gpio_gate,
            "video_gate": self.video_gate,
            "validator": self.validator,
            "testbench": self.testbench,
            "verilator_command": self.verilator_command,
            "windows": [window.as_dict() for window in self.windows],
            "reserved_fault_policy": self.reserved_fault_policy,
            "tag_policy": self.tag_policy,
            "remaining_handoffs": list(self.remaining_handoffs),
        }


def fpga_soc_top_decoder_profile() -> SocTopDecoderProfile:
    soc = fpga_soc_platform.fpga_soc_platform_profile()
    return SocTopDecoderProfile(
        story=FPGA_SOC_TOP_DECODER_STORY,
        top_module="cpu_v01_fpga_top",
        closure_gate=fpga_soc_top_closure.FPGA_SOC_TOP_CLOSURE_TOOL,
        platform_gate=fpga_soc_platform.FPGA_SOC_PLATFORM_TOOL,
        uart_gate=fpga_uart_mmio.FPGA_UART_MMIO_TOOL,
        timer_gate=fpga_timer_mmio.FPGA_TIMER_MMIO_TOOL,
        gpio_gate=fpga_gpio_status.FPGA_GPIO_STATUS_TOOL,
        video_gate=fpga_video_display.FPGA_VIDEO_DISPLAY_TOOL,
        validator=FPGA_SOC_TOP_DECODER_TOOL,
        testbench=FPGA_SOC_TOP_DECODER_TESTBENCH.as_posix(),
        verilator_command=FPGA_SOC_TOP_DECODER_VERILATOR_COMMAND,
        windows=(
            SocTopDecodeWindow(
                "data_ram",
                platform.RAM_BASE,
                0x1000,
                "I23-S03 BRAM data adapter",
                True,
            ),
            *(
                SocTopDecodeWindow(
                    peripheral.name,
                    peripheral.base_cell,
                    peripheral.size_cells,
                    peripheral.owner_story,
                    False,
                )
                for peripheral in soc.peripherals
            ),
            SocTopDecodeWindow(
                fpga_video_display.fpga_video_display_profile().mmio.name,
                fpga_video_display.FPGA_VIDEO_MMIO_BASE,
                fpga_video_display.FPGA_VIDEO_MMIO_CELLS,
                "I35-S04 video MMIO integration",
                False,
            ),
        ),
        reserved_fault_policy=(
            "Reads outside data_ram and the I27-S01 MMIO peripheral windows return "
            "EXC_ACCESS_FAULT; writes are accepted as deterministic no-ops because "
            "the current core data-write channel has no write-response fault phase."
        ),
        tag_policy=(
            "tag_ram request valid is gated by the data_ram window; non-RAM tag reads "
            "return an invalid tag and non-RAM tag writes are suppressed."
        ),
        remaining_handoffs=(
            "I30-S03 wires firmware UART TX/RX, timer interrupt delivery, and GPIO/status LED ownership.",
            "I35-S04 wires video_display control/status MMIO and video_vblank interrupt routing.",
            "I30-S04 arbitrates loader traffic against firmware/status UART ownership.",
            "I30-S05 proves the integrated top with a firmware smoke.",
        ),
    )


def fpga_soc_top_decoder_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_top_decoder_profile().as_dict(), indent=indent, sort_keys=True)


def decode_soc_top_address(address: int, *, len_cells: int = 1, write: bool = False) -> SocTopDecodeResult:
    if type(address) is not int or address < 0:
        raise ValueError("address must be a nonnegative integer cell address")
    if type(len_cells) is not int:
        raise TypeError("len_cells must be an int")
    if type(write) is not bool:
        raise TypeError("write must be a bool")

    profile = fpga_soc_top_decoder_profile()
    if len_cells <= 0 or len_cells > MAX_DMEM_TRANSFER_CELLS:
        return SocTopDecodeResult(
            address,
            len_cells,
            write,
            "fault",
            "no_response" if write else "EXC_ACCESS_FAULT",
            not write,
            False,
            "invalid transfer length",
        )

    data_ram = profile.window_by_target("data_ram")
    if data_ram.contains_start(address):
        if not data_ram.contains_transfer(address, len_cells):
            return SocTopDecodeResult(
                address,
                len_cells,
                write,
                "fault",
                "no_response" if write else "EXC_ACCESS_FAULT",
                not write,
                False,
                "data RAM transfer crosses the BRAM window",
            )
        return SocTopDecodeResult(
            address,
            len_cells,
            write,
            data_ram.target,
            "write_accepted" if write else "data_response",
            False,
            data_ram.tag_sidecar,
            "RAM access is forwarded to cpu_v01_fpga_data_ram",
        )

    for window in profile.windows:
        if window.target == "data_ram":
            continue
        if window.contains_start(address):
            return SocTopDecodeResult(
                address,
                len_cells,
                write,
                window.target,
                "write_accepted" if write else "mmio_response_or_register_fault",
                False,
                False,
                f"MMIO access is forwarded to {window.target}",
            )

    return SocTopDecodeResult(
        address,
        len_cells,
        write,
        "fault",
        "no_response" if write else "EXC_ACCESS_FAULT",
        not write,
        False,
        "reserved or unmapped top-level window",
    )


def render_fpga_soc_top_decoder() -> str:
    profile = fpga_soc_top_decoder_profile()
    lines = [
        "# FPGA SoC Top Data/MMIO Decoder",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"Verilator: `{profile.verilator_command}`",
        "",
        "## Decode Windows",
        "",
        "| Target | Base | End | Tag sidecar | Source |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for window in profile.windows:
        lines.append(
            f"| `{window.target}` | `0x{window.base_cell:08X}` | "
            f"`0x{window.end_cell:08X}` | {window.tag_sidecar} | {window.source} |"
        )
    lines.extend(
        [
            "",
            "## Policies",
            "",
            f"- Reserved/fault windows: {profile.reserved_fault_policy}",
            f"- Tag sidecar: {profile.tag_policy}",
            "",
            "## Handoffs",
            "",
        ]
    )
    lines.extend(f"- {handoff}" for handoff in profile.remaining_handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_soc_top_decoder(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_decoder_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_TOP_DECODER_STORY:
        issues.append(f"FPGA SoC top decoder story must be {FPGA_SOC_TOP_DECODER_STORY}")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("FPGA SoC top decoder must target cpu_v01_fpga_top")
    for gate in (
        profile.closure_gate,
        profile.platform_gate,
        profile.uart_gate,
        profile.timer_gate,
        profile.gpio_gate,
        profile.video_gate,
    ):
        if not gate.startswith("python tools\\"):
            issues.append(f"unexpected decoder dependency gate {gate}")

    for path in (*FPGA_SOC_TOP_DECODER_SOURCES, FPGA_SOC_TOP_DECODER_TEST, FPGA_SOC_TOP_DECODER_DOC):
        if not (root / path).exists():
            issues.append(f"missing FPGA SoC top decoder artifact {path.as_posix()}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC top decoder profile is not JSON serializable: {exc}")

    window_targets = [window.target for window in profile.windows]
    expected_targets = (
        "data_ram",
        "uart",
        "timer",
        "gpio_status",
        "interrupt_controller",
        "system_identity",
        "video_display",
    )
    for target in expected_targets:
        if target not in window_targets:
            issues.append(f"missing decoder window {target}")
    if len(window_targets) != len(set(window_targets)):
        issues.append("decoder windows must have unique targets")

    data_ram = profile.window_by_target("data_ram")
    if data_ram.base_cell != platform.RAM_BASE or data_ram.size_cells != 0x1000:
        issues.append("data_ram decoder window must match the FPGA BRAM top slice")
    if not data_ram.tag_sidecar:
        issues.append("data_ram decoder window must keep tag sidecar enabled")
    for window in profile.windows:
        if window.target != "data_ram" and window.tag_sidecar:
            issues.append(f"{window.target} must not enable tag sidecar")

    samples = {
        platform.RAM_BASE: "data_ram",
        0x00F0_0002: "uart",
        0x00F0_0101: "timer",
        0x00F0_0200: "gpio_status",
        0x00F0_0300: "interrupt_controller",
        0x00F0_0401: "system_identity",
        0x00F0_0500: "video_display",
        0x00F0_0600: "fault",
    }
    for address, target in samples.items():
        result = decode_soc_top_address(address, len_cells=1)
        if result.target != target:
            issues.append(f"decode sample 0x{address:08X} expected {target}, got {result.target}")

    if not decode_soc_top_address(0x00F0_0600, len_cells=1).fault_on_read:
        issues.append("reserved window reads must fault")
    if decode_soc_top_address(0x00F0_0000, len_cells=1).tag_sidecar:
        issues.append("MMIO windows must not expose tag sidecar")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / FPGA_SOC_TOP_DECODER_TESTBENCH)
    doc = _read_if_exists(root / FPGA_SOC_TOP_DECODER_DOC)

    for token in (
        "module cpu_v01_fpga_soc_dmem_decoder",
        "cpu_v01_fpga_soc_dmem_decoder #(",
        "ram_req_valid",
        "uart_req_valid",
        "timer_req_valid",
        "gpio_req_valid",
        "video_req_valid",
        "irq_req_valid",
        "identity_req_valid",
        "fault_rsp_valid_q",
        "tagmem_req_in_data_ram",
        "tagmem_bypass_rsp_valid_q",
        "cpu_v01_fpga_uart_mmio",
        "cpu_v01_fpga_timer_mmio",
        "cpu_v01_fpga_gpio_status",
        "module cpu_v01_fpga_video_mmio",
        "module cpu_v01_fpga_irq_mmio",
        "module cpu_v01_fpga_system_identity_mmio",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_top_soc_decoder_tb",
        "cpu_v01_fpga_soc_dmem_decoder #(",
        "FPGA SoC top decoder did not route RAM read/write traffic",
        "FPGA SoC top decoder UART status read mismatch",
        "FPGA SoC top decoder timer compare readback mismatch",
        "FPGA SoC top decoder GPIO/status readback mismatch",
        "FPGA SoC top decoder video control readback mismatch",
        "FPGA SoC top decoder interrupt-controller pending read mismatch",
        "FPGA SoC top decoder system identity build-id mismatch",
        "FPGA SoC top decoder reserved window did not fault",
        "FPGA SoC top decoder invalid length did not fault",
    ):
        if token not in tb:
            issues.append(f"{FPGA_SOC_TOP_DECODER_TESTBENCH.as_posix()} missing {token}")

    for token in (
        "Story: I30-S02",
        FPGA_SOC_TOP_DECODER_TOOL,
        "rtl/cpu_v01_fpga_top_soc_decoder_tb.sv",
        "cpu_v01_fpga_soc_dmem_decoder",
        "data_ram",
        "uart",
        "timer",
        "gpio_status",
        "video_display",
        "interrupt_controller",
        "system_identity",
        "EXC_ACCESS_FAULT",
        "tag_ram",
        "I30-S03",
        "I30-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_TOP_DECODER_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

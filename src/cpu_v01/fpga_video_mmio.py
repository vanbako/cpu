"""FPGA video MMIO and vblank interrupt integration profile.

Owner stories:
- I35-S04: integrate video control/status MMIO and vblank interrupt routing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import fpga_soc_top_decoder, fpga_soc_top_peripherals
from . import fpga_video_display, fpga_video_output


JsonValue = Any

FPGA_VIDEO_MMIO_STORY = "I35-S04"
FPGA_VIDEO_MMIO_DOC = Path("docs/implementation/fpga-video-mmio-irq.md")
FPGA_VIDEO_MMIO_TOOL = "python tools\\fpga_video_mmio.py --check"
FPGA_VIDEO_MMIO_TESTBENCH = Path("rtl/cpu_v01_fpga_video_mmio_tb.sv")
FPGA_VIDEO_MMIO_TEST = Path("tests/conformance/test_i35_s04_fpga_video_mmio.py")
FPGA_VIDEO_MMIO_VERILATOR_COMMAND = (
    "verilator --lint-only --timing --top-module cpu_v01_fpga_video_mmio_tb "
    "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
    "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
    "rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv "
    "rtl/cpu_v01_fpga_video_mmio_tb.sv"
)

VIDEO_CONTROL_SCANOUT_ENABLE = 0x0001
VIDEO_CONTROL_OUTPUT_ENABLE = 0x0002
VIDEO_STATUS_SCANOUT_ENABLED = 0x0001
VIDEO_STATUS_IN_VBLANK = 0x0002
VIDEO_STATUS_UNDERFLOW_PENDING = 0x0004
VIDEO_STATUS_MODE_VALID = 0x0008
VIDEO_STATUS_VBLANK_PENDING = 0x0010
VIDEO_IRQ_VBLANK = 0x0001
VIDEO_IRQ_UNDERFLOW = 0x0002
VIDEO_IRQ_CONTROLLER_BIT = 4
VIDEO_IRQ_CONTROLLER_MASK = 1 << VIDEO_IRQ_CONTROLLER_BIT
VIDEO_EXTERNAL_IRQ_MASK = 0x001B


@dataclass(frozen=True)
class VideoMmioBehavior:
    register: str
    behavior: str
    evidence_tokens: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "register": self.register,
            "behavior": self.behavior,
            "evidence_tokens": list(self.evidence_tokens),
        }


@dataclass(frozen=True)
class VideoMmioProfile:
    story: str
    display_gate: str
    output_gate: str
    decoder_gate: str
    peripheral_gate: str
    validator: str
    mmio_base_cell: int
    mmio_end_cell: int
    irq_line: str
    irq_bit: int
    irq_controller_mask: int
    external_irq_mask: int
    rtl_module: str
    testbench: str
    verilator_command: str
    register_behaviors: tuple[VideoMmioBehavior, ...]
    top_handoffs: tuple[str, ...]
    deferred_handoffs: tuple[str, ...]

    def behavior_by_register(self, register: str) -> VideoMmioBehavior:
        normalized = register.upper()
        for behavior in self.register_behaviors:
            if behavior.register.upper() == normalized:
                return behavior
        raise KeyError(register)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "display_gate": self.display_gate,
            "output_gate": self.output_gate,
            "decoder_gate": self.decoder_gate,
            "peripheral_gate": self.peripheral_gate,
            "validator": self.validator,
            "mmio_base_cell": self.mmio_base_cell,
            "mmio_end_cell": self.mmio_end_cell,
            "irq_line": self.irq_line,
            "irq_bit": self.irq_bit,
            "irq_controller_mask": self.irq_controller_mask,
            "external_irq_mask": self.external_irq_mask,
            "rtl_module": self.rtl_module,
            "testbench": self.testbench,
            "verilator_command": self.verilator_command,
            "register_behaviors": [behavior.as_dict() for behavior in self.register_behaviors],
            "top_handoffs": list(self.top_handoffs),
            "deferred_handoffs": list(self.deferred_handoffs),
        }


@dataclass(frozen=True)
class VideoMmioState:
    control: int = 0
    mode: int = 0
    irq_enable: int = 0
    irq_pending: int = 0
    frame_count: int = 0
    line_count: int = 0
    pixel_count: int = 0
    test_pattern: int = 1
    bg_color: int = 0
    underflow_count: int = 0
    fb_master_status: int = 0
    vblank: bool = False

    @property
    def scanout_enabled(self) -> bool:
        return bool(self.control & VIDEO_CONTROL_SCANOUT_ENABLE)

    @property
    def output_enabled(self) -> bool:
        return bool(self.control & VIDEO_CONTROL_OUTPUT_ENABLE)

    @property
    def mode_valid(self) -> bool:
        return self.mode == 0

    @property
    def irq_asserted(self) -> bool:
        return bool(self.irq_enable & self.irq_pending)

    @property
    def status(self) -> int:
        status = 0
        if self.scanout_enabled:
            status |= VIDEO_STATUS_SCANOUT_ENABLED
        if self.vblank:
            status |= VIDEO_STATUS_IN_VBLANK
        if self.irq_pending & VIDEO_IRQ_UNDERFLOW:
            status |= VIDEO_STATUS_UNDERFLOW_PENDING
        if self.mode_valid:
            status |= VIDEO_STATUS_MODE_VALID
        if self.irq_pending & VIDEO_IRQ_VBLANK:
            status |= VIDEO_STATUS_VBLANK_PENDING
        return status

    def write(self, offset_cell: int, value: int) -> "VideoMmioState":
        if offset_cell == 0x00:
            return replace(self, control=value & 0xFFFF)
        if offset_cell == 0x01:
            return replace(self, mode=value & 0xFFFF)
        if offset_cell == 0x03:
            return replace(self, irq_enable=value & 0xFFFF)
        if offset_cell == 0x04:
            return replace(self, irq_pending=self.irq_pending & ~(value & 0xFFFF))
        if offset_cell == 0x08:
            return replace(self, test_pattern=value & 0xF)
        if offset_cell == 0x09:
            return replace(self, bg_color=value & 0xFFFFFF)
        return self

    def tick(
        self,
        *,
        vblank: bool,
        underflow_pulse: bool = False,
        frame_count: int | None = None,
        line_count: int | None = None,
        pixel_count: int | None = None,
        fb_master_status: int | None = None,
    ) -> "VideoMmioState":
        pending = self.irq_pending
        underflow_count = self.underflow_count
        if vblank and not self.vblank:
            pending |= VIDEO_IRQ_VBLANK
        if underflow_pulse:
            pending |= VIDEO_IRQ_UNDERFLOW
            underflow_count = (underflow_count + 1) & ((1 << 48) - 1)
        return replace(
            self,
            irq_pending=pending,
            underflow_count=underflow_count,
            vblank=vblank,
            frame_count=self.frame_count if frame_count is None else frame_count & ((1 << 48) - 1),
            line_count=self.line_count if line_count is None else line_count & 0xFFFF,
            pixel_count=self.pixel_count if pixel_count is None else pixel_count & 0xFFFF,
            fb_master_status=(
                self.fb_master_status if fb_master_status is None else fb_master_status & 0xFFFF
            ),
        )

    def read(self, offset_cell: int) -> int:
        if offset_cell == 0x00:
            return self.control
        if offset_cell == 0x01:
            return self.mode
        if offset_cell == 0x02:
            return self.status
        if offset_cell == 0x03:
            return self.irq_enable
        if offset_cell == 0x04:
            return self.irq_pending
        if offset_cell == 0x05:
            return self.frame_count
        if offset_cell == 0x06:
            return self.line_count
        if offset_cell == 0x07:
            return self.pixel_count
        if offset_cell == 0x08:
            return self.test_pattern
        if offset_cell == 0x09:
            return self.bg_color
        if offset_cell == 0x0A:
            return self.underflow_count
        if offset_cell == 0x0B:
            return self.fb_master_status
        raise KeyError(offset_cell)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "control": self.control,
            "mode": self.mode,
            "irq_enable": self.irq_enable,
            "irq_pending": self.irq_pending,
            "frame_count": self.frame_count,
            "line_count": self.line_count,
            "pixel_count": self.pixel_count,
            "test_pattern": self.test_pattern,
            "bg_color": self.bg_color,
            "underflow_count": self.underflow_count,
            "fb_master_status": self.fb_master_status,
            "vblank": self.vblank,
            "status": self.status,
            "scanout_enabled": self.scanout_enabled,
            "output_enabled": self.output_enabled,
            "mode_valid": self.mode_valid,
            "irq_asserted": self.irq_asserted,
        }


@dataclass(frozen=True)
class VideoMmioIrqDemo:
    after_program: VideoMmioState
    after_vblank: VideoMmioState
    after_ack: VideoMmioState
    irq_controller_mask: int
    external_irq_mask: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "after_program": self.after_program.as_dict(),
            "after_vblank": self.after_vblank.as_dict(),
            "after_ack": self.after_ack.as_dict(),
            "irq_controller_mask": self.irq_controller_mask,
            "external_irq_mask": self.external_irq_mask,
        }


def fpga_video_mmio_profile() -> VideoMmioProfile:
    display = fpga_video_display.fpga_video_display_profile()
    return VideoMmioProfile(
        story=FPGA_VIDEO_MMIO_STORY,
        display_gate=fpga_video_display.FPGA_VIDEO_DISPLAY_TOOL,
        output_gate=fpga_video_output.FPGA_VIDEO_OUTPUT_TOOL,
        decoder_gate=fpga_soc_top_decoder.FPGA_SOC_TOP_DECODER_TOOL,
        peripheral_gate=fpga_soc_top_peripherals.FPGA_SOC_TOP_PERIPHERALS_TOOL,
        validator=FPGA_VIDEO_MMIO_TOOL,
        mmio_base_cell=display.mmio.base_cell,
        mmio_end_cell=display.mmio.end_cell,
        irq_line=display.mmio.interrupt_line,
        irq_bit=display.mmio.interrupt_bit,
        irq_controller_mask=VIDEO_IRQ_CONTROLLER_MASK,
        external_irq_mask=VIDEO_EXTERNAL_IRQ_MASK,
        rtl_module="cpu_v01_fpga_video_mmio",
        testbench=FPGA_VIDEO_MMIO_TESTBENCH.as_posix(),
        verilator_command=FPGA_VIDEO_MMIO_VERILATOR_COMMAND,
        register_behaviors=_register_behaviors(),
        top_handoffs=(
            "cpu_v01_fpga_soc_dmem_decoder routes the video_display window at 0x00F00500",
            "cpu_v01_fpga_top instantiates cpu_v01_fpga_video_mmio",
            "video_vblank_irq drives interrupt-controller bit 4",
            "external_interrupt_pending includes enabled video_vblank through mask 16'h001B",
        ),
        deferred_handoffs=(
            "I35-S05 proves combined scanout/MMIO/vblank timing in simulation and reports",
            "I35-S06 captures board-visible scanout and vblank evidence",
            "I36-S04 consumes vblank for atomic plane descriptor updates",
        ),
    )


def initial_video_mmio_state() -> VideoMmioState:
    return VideoMmioState()


def simulate_video_mmio_irq_demo() -> VideoMmioIrqDemo:
    state = initial_video_mmio_state()
    state = state.write(0x00, VIDEO_CONTROL_SCANOUT_ENABLE | VIDEO_CONTROL_OUTPUT_ENABLE)
    state = state.write(0x08, 0x2)
    state = state.write(0x09, 0x123456)
    state = state.write(0x03, VIDEO_IRQ_VBLANK)
    after_program = state
    after_vblank = state.tick(vblank=True, frame_count=7, line_count=720, pixel_count=0)
    after_ack = after_vblank.write(0x04, VIDEO_IRQ_VBLANK)
    return VideoMmioIrqDemo(
        after_program=after_program,
        after_vblank=after_vblank,
        after_ack=after_ack,
        irq_controller_mask=VIDEO_IRQ_CONTROLLER_MASK,
        external_irq_mask=VIDEO_EXTERNAL_IRQ_MASK,
    )


def fpga_video_mmio_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_video_mmio_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_video_mmio() -> str:
    profile = fpga_video_mmio_profile()
    lines = [
        "# FPGA Video MMIO And IRQ",
        "",
        f"Story: `{profile.story}`",
        f"Validator: `{profile.validator}`",
        f"MMIO: `0x{profile.mmio_base_cell:08X}`..`0x{profile.mmio_end_cell:08X}`",
        f"IRQ: `{profile.irq_line}` bit `{profile.irq_bit}`",
        "",
        "## Registers",
        "",
        "| Register | Behavior |",
        "| --- | --- |",
    ]
    for behavior in profile.register_behaviors:
        lines.append(f"| `{behavior.register}` | {behavior.behavior} |")
    return "\n".join(lines)


def validate_fpga_video_mmio(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_video_mmio_profile()
    issues: list[str] = []

    display_issues = fpga_video_display.validate_fpga_video_display(root)
    issues.extend(f"I35-S01 prerequisite: {issue}" for issue in display_issues)
    output_issues = fpga_video_output.validate_fpga_video_output(root)
    issues.extend(f"I35-S03 prerequisite: {issue}" for issue in output_issues)
    decoder_issues = fpga_soc_top_decoder.validate_fpga_soc_top_decoder(root)
    issues.extend(f"I30-S02 prerequisite: {issue}" for issue in decoder_issues)
    peripheral_issues = fpga_soc_top_peripherals.validate_fpga_soc_top_peripherals(root)
    issues.extend(f"I30-S03 prerequisite: {issue}" for issue in peripheral_issues)

    if profile.story != FPGA_VIDEO_MMIO_STORY:
        issues.append(f"video MMIO story must be {FPGA_VIDEO_MMIO_STORY}")
    if profile.mmio_base_cell != 0x00F0_0500 or profile.mmio_end_cell != 0x00F0_0600:
        issues.append("video MMIO window must be 0x00F00500..0x00F00600")
    if profile.irq_line != "video_vblank" or profile.irq_bit != VIDEO_IRQ_CONTROLLER_BIT:
        issues.append("video MMIO interrupt must be video_vblank bit 4")
    if profile.irq_controller_mask != 0x0010:
        issues.append("video interrupt-controller mask must be bit 4")
    if profile.external_irq_mask != 0x001B:
        issues.append("external interrupt mask must include UART, GPIO, and video bits")

    for register in (
        "VIDEO_CONTROL",
        "VIDEO_MODE",
        "VIDEO_STATUS",
        "VIDEO_IRQ_ENABLE",
        "VIDEO_IRQ_ACK",
        "VIDEO_FRAME_COUNT",
        "VIDEO_LINE_COUNT",
        "VIDEO_PIXEL_COUNT",
        "VIDEO_TEST_PATTERN",
        "VIDEO_BG_COLOR",
        "VIDEO_UNDERFLOW_COUNT",
        "VIDEO_FB_MASTER_STATUS",
    ):
        try:
            profile.behavior_by_register(register)
        except KeyError:
            issues.append(f"missing video MMIO behavior for {register}")

    demo = simulate_video_mmio_irq_demo()
    if not demo.after_program.scanout_enabled or not demo.after_program.output_enabled:
        issues.append("video MMIO demo did not enable scanout/output")
    if demo.after_program.test_pattern != 2 or demo.after_program.bg_color != 0x123456:
        issues.append("video MMIO demo did not program pattern/background")
    if not demo.after_vblank.irq_asserted or not (demo.after_vblank.status & VIDEO_STATUS_VBLANK_PENDING):
        issues.append("video MMIO demo did not assert vblank pending IRQ")
    if demo.after_ack.irq_asserted or demo.after_ack.irq_pending != 0:
        issues.append("video MMIO demo acknowledgement did not clear pending IRQ")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / FPGA_VIDEO_MMIO_TESTBENCH)
    decoder_tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top_soc_decoder_tb.sv")
    peripheral_tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top_soc_peripherals_tb.sv")
    doc = _read_if_exists(root / FPGA_VIDEO_MMIO_DOC)

    for token in (
        "module cpu_v01_fpga_video_mmio",
        "VIDEO_CONTROL_OFFSET",
        "VIDEO_IRQ_ENABLE_OFFSET",
        "vblank_pending_q",
        "underflow_count_q",
        "assign video_vblank_irq_o = |(irq_enable_q & irq_pending_q);",
        "TARGET_VIDEO",
        "VIDEO_BASE = 48'h0000_00F0_0500",
        "video_req_valid",
        ".video_req_valid(video_req_valid)",
        "cpu_v01_fpga_video_mmio firmware_video",
        "video_vblank_irq",
        "assign irq_sources = {",
        "assign external_interrupt_pending = |(irq_pending_enabled & 16'h001B);",
    ):
        if token not in top:
            issues.append(f"rtl/cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_video_mmio_tb",
        "cpu_v01_fpga_video_mmio dut",
        "FPGA video MMIO did not enable scanout outputs",
        "FPGA video MMIO did not report vblank status",
        "FPGA video MMIO did not raise video_vblank_irq_o",
        "FPGA video MMIO acknowledgement did not clear vblank IRQ",
        "FPGA video MMIO frame count readback mismatch",
        "FPGA video MMIO underflow count mismatch",
    ):
        if token not in tb:
            issues.append(f"{FPGA_VIDEO_MMIO_TESTBENCH.as_posix()} missing {token}")

    for token in (
        "VIDEO_BASE",
        "video_req_valid",
        "FPGA SoC top decoder video control readback mismatch",
    ):
        if token not in decoder_tb:
            issues.append(f"rtl/cpu_v01_fpga_top_soc_decoder_tb.sv missing {token}")
    for token in (
        "video_vblank_irq",
        "16'h001B",
        "FPGA SoC top peripherals video vblank external interrupt mismatch",
    ):
        if token not in peripheral_tb:
            issues.append(f"rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv missing {token}")

    for token in (
        "Story: I35-S04",
        FPGA_VIDEO_MMIO_TOOL,
        "0x00F00500",
        "VIDEO_CONTROL",
        "VIDEO_STATUS",
        "VIDEO_IRQ_ENABLE",
        "VIDEO_IRQ_ACK",
        "VIDEO_FRAME_COUNT",
        "VIDEO_LINE_COUNT",
        "VIDEO_PIXEL_COUNT",
        "VIDEO_UNDERFLOW_COUNT",
        "VIDEO_FB_MASTER_STATUS",
        "video_vblank",
        "bit 4",
        "16'h001B",
        "cpu_v01_fpga_video_mmio",
        "cpu_v01_fpga_soc_dmem_decoder",
        "I35-S05",
        "I36-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_VIDEO_MMIO_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(demo.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"video MMIO profile/demo is not JSON serializable: {exc}")

    return tuple(issues)


def _register_behaviors() -> tuple[VideoMmioBehavior, ...]:
    return (
        VideoMmioBehavior(
            "VIDEO_CONTROL",
            "rw bit 0 enables scanout and bit 1 enables visible output",
            ("VIDEO_CONTROL_OFFSET", "video_scanout_enable_o", "video_output_enable_o"),
        ),
        VideoMmioBehavior(
            "VIDEO_MODE",
            "rw timing mode selector; mode 0 is the supported 720p mode",
            ("VIDEO_MODE_OFFSET", "video_mode_o"),
        ),
        VideoMmioBehavior(
            "VIDEO_STATUS",
            "ro scanout-enabled, in-vblank, underflow-pending, mode-valid, and vblank-pending bits",
            ("VIDEO_STATUS_OFFSET", "video_status"),
        ),
        VideoMmioBehavior(
            "VIDEO_IRQ_ENABLE",
            "rw bit 0 enables vblank IRQ and bit 1 enables underflow IRQ",
            ("VIDEO_IRQ_ENABLE_OFFSET", "irq_enable_q"),
        ),
        VideoMmioBehavior(
            "VIDEO_IRQ_ACK",
            "w1c clears sticky vblank and underflow pending bits",
            ("VIDEO_IRQ_ACK_OFFSET", "irq_pending_q"),
        ),
        VideoMmioBehavior(
            "VIDEO_FRAME_COUNT",
            "ro 48-bit frame counter snapshot from scanout",
            ("VIDEO_FRAME_COUNT_OFFSET", "video_frame_count_i"),
        ),
        VideoMmioBehavior(
            "VIDEO_LINE_COUNT",
            "ro scanout line counter snapshot",
            ("VIDEO_LINE_COUNT_OFFSET", "video_line_count_i"),
        ),
        VideoMmioBehavior(
            "VIDEO_PIXEL_COUNT",
            "ro scanout pixel counter snapshot",
            ("VIDEO_PIXEL_COUNT_OFFSET", "video_pixel_count_i"),
        ),
        VideoMmioBehavior(
            "VIDEO_TEST_PATTERN",
            "rw test-pattern selector driven toward the output boundary",
            ("VIDEO_TEST_PATTERN_OFFSET", "video_test_pattern_o"),
        ),
        VideoMmioBehavior(
            "VIDEO_BG_COLOR",
            "rw 24-bit background RGB driven toward the output boundary",
            ("VIDEO_BG_COLOR_OFFSET", "video_bg_color_o"),
        ),
        VideoMmioBehavior(
            "VIDEO_UNDERFLOW_COUNT",
            "ro 48-bit sticky counter incremented by underflow pulses",
            ("VIDEO_UNDERFLOW_COUNT_OFFSET", "underflow_count_q"),
        ),
        VideoMmioBehavior(
            "VIDEO_FB_MASTER_STATUS",
            "ro framebuffer/read-master status snapshot for later compositor fetch",
            ("VIDEO_FB_MASTER_STATUS_OFFSET", "video_fb_master_status_i"),
        ),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

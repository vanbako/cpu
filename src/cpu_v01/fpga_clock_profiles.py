"""FPGA clock, PLL, and build-frequency profiles.

Owner stories:
- I28-S01: define FPGA clock, PLL, and build-frequency profiles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_constraints,
    fpga_first_test,
    fpga_gowin_build,
    fpga_synthesis,
    fpga_uart_mmio,
    fpga_uart_status,
)


JsonValue = Any

FPGA_CLOCK_PROFILES_STORY = "I28-S01"
FPGA_CLOCK_PROFILES_DOC = Path("docs/implementation/fpga-clock-profiles.md")
FPGA_CLOCK_PROFILES_TOOL = "python tools\\fpga_clock_profiles.py --check"
DEBUG_PROFILE_ID = "debug_direct_25mhz"
RELEASE_PROFILE_ID = "release_pll_25mhz"
BOARD_CLOCK_HZ = 25_000_000
BOARD_CLOCK_PERIOD_NS = 40.000


@dataclass(frozen=True)
class FpgaPllSetting:
    mode: str
    primitive: str
    status: str
    input_clock: str
    output_clock: str
    input_hz: int
    output_hz: int
    input_divide: int
    feedback_multiply: int
    output_divide: int
    phase_degrees: float
    duty_cycle_percent: float
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "mode": self.mode,
            "primitive": self.primitive,
            "status": self.status,
            "input_clock": self.input_clock,
            "output_clock": self.output_clock,
            "input_hz": self.input_hz,
            "output_hz": self.output_hz,
            "input_divide": self.input_divide,
            "feedback_multiply": self.feedback_multiply,
            "output_divide": self.output_divide,
            "phase_degrees": self.phase_degrees,
            "duty_cycle_percent": self.duty_cycle_percent,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FpgaGeneratedClock:
    name: str
    source: str
    hz: int
    sdc_name: str
    generation: str
    drives: tuple[str, ...]

    @property
    def period_ns(self) -> float:
        return 1_000_000_000.0 / self.hz

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "source": self.source,
            "hz": self.hz,
            "period_ns": round(self.period_ns, 3),
            "sdc_name": self.sdc_name,
            "generation": self.generation,
            "drives": list(self.drives),
        }


@dataclass(frozen=True)
class FpgaClockProfile:
    profile_id: str
    role: str
    status: str
    selected_for_current_build: bool
    source_clock: str
    source_hz: int
    pll: FpgaPllSetting
    generated_clocks: tuple[FpgaGeneratedClock, ...]
    sdc_constraints: tuple[str, ...]
    minimum_slack_ns: float
    target_slack_ns: float
    report_gate: str
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "profile_id": self.profile_id,
            "role": self.role,
            "status": self.status,
            "selected_for_current_build": self.selected_for_current_build,
            "source_clock": self.source_clock,
            "source_hz": self.source_hz,
            "source_period_ns": round(1_000_000_000.0 / self.source_hz, 3),
            "pll": self.pll.as_dict(),
            "generated_clocks": [clock.as_dict() for clock in self.generated_clocks],
            "sdc_constraints": list(self.sdc_constraints),
            "minimum_slack_ns": self.minimum_slack_ns,
            "target_slack_ns": self.target_slack_ns,
            "report_gate": self.report_gate,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FpgaClockProfileSet:
    story: str
    board: str
    device: str
    package: str
    top_module: str
    board_clock: str
    board_clock_hz: int
    board_clock_period_ns: float
    default_profile_id: str
    release_profile_id: str
    constraints_gate: str
    gowin_gate: str
    timing_sdc_path: Path
    profiles: tuple[FpgaClockProfile, ...]
    blockers: tuple[str, ...]

    def profile_by_id(self, profile_id: str) -> FpgaClockProfile:
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        raise KeyError(f"unknown FPGA clock profile {profile_id!r}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "device": self.device,
            "package": self.package,
            "top_module": self.top_module,
            "board_clock": self.board_clock,
            "board_clock_hz": self.board_clock_hz,
            "board_clock_period_ns": self.board_clock_period_ns,
            "default_profile_id": self.default_profile_id,
            "release_profile_id": self.release_profile_id,
            "constraints_gate": self.constraints_gate,
            "gowin_gate": self.gowin_gate,
            "timing_sdc_path": self.timing_sdc_path.as_posix(),
            "profiles": [profile.as_dict() for profile in self.profiles],
            "blockers": list(self.blockers),
        }


def fpga_clock_profile_set() -> FpgaClockProfileSet:
    return FpgaClockProfileSet(
        story=FPGA_CLOCK_PROFILES_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        package=fpga_first_test.TARGET_IDE_PACKAGE,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        board_clock="board_clk_i",
        board_clock_hz=BOARD_CLOCK_HZ,
        board_clock_period_ns=BOARD_CLOCK_PERIOD_NS,
        default_profile_id=DEBUG_PROFILE_ID,
        release_profile_id=RELEASE_PROFILE_ID,
        constraints_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        gowin_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        timing_sdc_path=fpga_synthesis.FPGA_SYNTHESIS_TIMING_FILE,
        profiles=(
            _debug_direct_profile(),
            _release_pll_profile(),
        ),
        blockers=(
            "I24-S01 identity evidence and I24-S02 pin evidence are still blocked",
            "cpu_v01_fpga_top currently clocks the core directly from board_clk_i",
            "the release PLL wrapper and generated-clock SDC must be added before selecting release_pll_25mhz",
            "I28-S03 and I28-S04 must audit real Gowin timing reports before raising the default frequency",
        ),
    )


def fpga_clock_profiles_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_clock_profile_set().as_dict(), indent=indent, sort_keys=True)


def fpga_clock_profile_ids() -> tuple[str, ...]:
    return tuple(profile.profile_id for profile in fpga_clock_profile_set().profiles)


def fpga_clock_command_plan() -> tuple[str, ...]:
    return (
        fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        FPGA_CLOCK_PROFILES_TOOL,
        f"python tools\\fpga_clock_profiles.py --sdc {DEBUG_PROFILE_ID}",
        f"python tools\\fpga_clock_profiles.py --sdc {RELEASE_PROFILE_ID}",
    )


def clock_profile_sdc(profile_id: str = DEBUG_PROFILE_ID) -> str:
    profile = fpga_clock_profile_set().profile_by_id(profile_id)
    return "\n".join(profile.sdc_constraints) + "\n"


def render_fpga_clock_profiles(profile_set: FpgaClockProfileSet | None = None) -> str:
    if profile_set is None:
        profile_set = fpga_clock_profile_set()
    lines = [
        "# FPGA Clock Profiles",
        "",
        f"Story: {profile_set.story}",
        "",
        f"Board: `{profile_set.board}`",
        f"Device: `{profile_set.device}`",
        f"Package: `{profile_set.package}`",
        f"Top module: `{profile_set.top_module}`",
        f"Board clock: `{profile_set.board_clock}` at {profile_set.board_clock_hz} Hz",
        f"Default profile: `{profile_set.default_profile_id}`",
        f"Release profile: `{profile_set.release_profile_id}`",
        f"Timing SDC: `{profile_set.timing_sdc_path.as_posix()}`",
        "",
        "## Profiles",
        "",
        "| Profile | Role | Status | Current | PLL | Generated clocks | Slack policy |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for profile in profile_set.profiles:
        clocks = ", ".join(
            f"`{clock.name}` {clock.hz} Hz" for clock in profile.generated_clocks
        )
        lines.append(
            f"| `{profile.profile_id}` | {profile.role} | {profile.status} | "
            f"{'yes' if profile.selected_for_current_build else 'no'} | "
            f"{profile.pll.mode} / {profile.pll.primitive} | {clocks} | "
            f"minimum {profile.minimum_slack_ns:.3f} ns, target {profile.target_slack_ns:.3f} ns |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile_set.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_clock_profiles(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile_set = fpga_clock_profile_set()
    issues: list[str] = []

    if profile_set.story != FPGA_CLOCK_PROFILES_STORY:
        issues.append(f"clock profiles story must be {FPGA_CLOCK_PROFILES_STORY}")
    if profile_set.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("clock profiles board must match the first-test profile")
    if profile_set.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("clock profiles device must match the first-test profile")
    if profile_set.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("clock profiles top module must match the FPGA top profile")
    if profile_set.board_clock_hz != fpga_synthesis.FPGA_SYNTHESIS_TARGET_CLOCK_HZ:
        issues.append("default board clock must match the I23-S05 synthesis target")
    if profile_set.board_clock_hz != fpga_uart_status.FPGA_UART_STATUS_CLOCK_HZ:
        issues.append("default board clock must match the I25-S02 UART status clock")
    if profile_set.board_clock_hz != fpga_uart_mmio.FPGA_UART_MMIO_CLOCK_HZ:
        issues.append("default board clock must match the I27-S02 UART MMIO clock")
    if profile_set.board_clock_period_ns != fpga_constraints.fpga_constraints_overlay().clock_period_ns:
        issues.append("board clock period must match the I24-S02 SDC overlay")

    profile_ids = {profile.profile_id for profile in profile_set.profiles}
    for required in (DEBUG_PROFILE_ID, RELEASE_PROFILE_ID):
        if required not in profile_ids:
            issues.append(f"missing clock profile {required}")

    debug = profile_set.profile_by_id(DEBUG_PROFILE_ID)
    release = profile_set.profile_by_id(RELEASE_PROFILE_ID)
    if not debug.selected_for_current_build:
        issues.append("debug profile must be selected for the current build")
    if debug.pll.primitive != "none" or debug.pll.output_hz != BOARD_CLOCK_HZ:
        issues.append("debug profile must use direct 25 MHz board clocking")
    if release.selected_for_current_build:
        issues.append("release PLL profile must stay unselected until RTL and timing evidence exist")
    if release.pll.primitive != "Gowin rPLL":
        issues.append("release profile must name the Gowin rPLL primitive")
    if release.pll.output_hz != BOARD_CLOCK_HZ:
        issues.append("release profile must preserve the current 25 MHz default frequency")
    if "blocked" not in release.status:
        issues.append("release profile must record the current blocker status")

    for profile in profile_set.profiles:
        if profile.source_clock != "board_clk_i":
            issues.append(f"{profile.profile_id} must use board_clk_i as source")
        if profile.minimum_slack_ns < 0 or profile.target_slack_ns < profile.minimum_slack_ns:
            issues.append(f"{profile.profile_id} has an invalid slack policy")
        if not profile.generated_clocks:
            issues.append(f"{profile.profile_id} must name generated clocks")
        if not any("create_clock" in line for line in profile.sdc_constraints):
            issues.append(f"{profile.profile_id} must include a create_clock SDC line")
        if not any("board_reset_n_i" in line for line in profile.sdc_constraints):
            issues.append(f"{profile.profile_id} must keep the async reset false path")

    existing_sdc = _read_if_exists(root / profile_set.timing_sdc_path)
    for token in (
        "create_clock -name board_clk_i -period 40.000",
        "set_false_path -from [get_ports {board_reset_n_i}]",
    ):
        if token not in existing_sdc:
            issues.append(f"{profile_set.timing_sdc_path.as_posix()} missing {token}")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    for token in (
        "input  logic board_clk_i",
        "always_ff @(posedge board_clk_i",
        ".clk(board_clk_i)",
        "parameter int UART_STATUS_CLOCK_HZ = 25_000_000",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing current clock token {token}")

    doc = _read_if_exists(root / FPGA_CLOCK_PROFILES_DOC)
    for token in (
        "Story: I28-S01",
        FPGA_CLOCK_PROFILES_TOOL,
        DEBUG_PROFILE_ID,
        RELEASE_PROFILE_ID,
        "board_clk_i",
        "25 MHz",
        "Gowin rPLL",
        "create_clock",
        "create_generated_clock",
        "minimum slack",
        "target slack",
        "I28-S03",
        "I28-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_CLOCK_PROFILES_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile_set.as_dict(), sort_keys=True)
        clock_profile_sdc(DEBUG_PROFILE_ID)
        clock_profile_sdc(RELEASE_PROFILE_ID)
    except (KeyError, TypeError) as exc:
        issues.append(f"FPGA clock profiles are not serializable/renderable: {exc}")

    return tuple(issues)


def _debug_direct_profile() -> FpgaClockProfile:
    return FpgaClockProfile(
        profile_id=DEBUG_PROFILE_ID,
        role="debug",
        status="current_direct_board_clock",
        selected_for_current_build=True,
        source_clock="board_clk_i",
        source_hz=BOARD_CLOCK_HZ,
        pll=FpgaPllSetting(
            mode="direct",
            primitive="none",
            status="implemented_in_cpu_v01_fpga_top",
            input_clock="board_clk_i",
            output_clock="board_clk_i",
            input_hz=BOARD_CLOCK_HZ,
            output_hz=BOARD_CLOCK_HZ,
            input_divide=1,
            feedback_multiply=1,
            output_divide=1,
            phase_degrees=0.0,
            duty_cycle_percent=50.0,
            notes=(
                "cpu_v01_fpga_top clocks the core, BRAM adapters, UART status, and first SoC MMIO blocks directly from board_clk_i",
                "this profile is the only selectable profile until release PLL RTL exists",
            ),
        ),
        generated_clocks=(
            FpgaGeneratedClock(
                name="core_clk",
                source="board_clk_i",
                hz=BOARD_CLOCK_HZ,
                sdc_name="board_clk_i",
                generation="direct",
                drives=("cpu_v01_core", "cpu_v01_fpga_imem_rom", "cpu_v01_fpga_data_ram"),
            ),
            FpgaGeneratedClock(
                name="uart_status_clk",
                source="board_clk_i",
                hz=BOARD_CLOCK_HZ,
                sdc_name="board_clk_i",
                generation="direct",
                drives=("cpu_v01_fpga_uart_status_streamer", "cpu_v01_fpga_uart_mmio"),
            ),
            FpgaGeneratedClock(
                name="timer_gpio_clk",
                source="board_clk_i",
                hz=BOARD_CLOCK_HZ,
                sdc_name="board_clk_i",
                generation="direct",
                drives=("cpu_v01_fpga_timer_mmio", "cpu_v01_fpga_gpio_status"),
            ),
        ),
        sdc_constraints=(
            "# CPU v0.1 I28-S01 debug_direct_25mhz timing constraints.",
            "create_clock -name board_clk_i -period 40.000 [get_ports {board_clk_i}]",
            "set_false_path -from [get_ports {board_reset_n_i}]",
        ),
        minimum_slack_ns=0.000,
        target_slack_ns=1.000,
        report_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        notes=(
            "debug and first board bring-up use the existing I24-S02 SDC",
            "UART divisors stay at the existing 25 MHz defaults",
        ),
    )


def _release_pll_profile() -> FpgaClockProfile:
    return FpgaClockProfile(
        profile_id=RELEASE_PROFILE_ID,
        role="release",
        status="blocked_until_pll_wrapper_and_timing_reports",
        selected_for_current_build=False,
        source_clock="board_clk_i",
        source_hz=BOARD_CLOCK_HZ,
        pll=FpgaPllSetting(
            mode="pll_1x_global_clock",
            primitive="Gowin rPLL",
            status="planned_not_instantiated",
            input_clock="board_clk_i",
            output_clock="cpu_clk",
            input_hz=BOARD_CLOCK_HZ,
            output_hz=BOARD_CLOCK_HZ,
            input_divide=1,
            feedback_multiply=1,
            output_divide=1,
            phase_degrees=0.0,
            duty_cycle_percent=50.0,
            notes=(
                "logical 1:1 release setting; vendor primitive generics must be emitted by a later checked PLL wrapper",
                "do not select this profile until generated-clock SDC and Gowin reports prove nonnegative slack",
            ),
        ),
        generated_clocks=(
            FpgaGeneratedClock(
                name="cpu_clk",
                source="board_clk_i",
                hz=BOARD_CLOCK_HZ,
                sdc_name="cpu_clk",
                generation="Gowin rPLL 1x",
                drives=("cpu_v01_core", "fpga_bram_adapters", "fpga_soc_mmio_shell"),
            ),
            FpgaGeneratedClock(
                name="uart_timer_gpio_clk",
                source="cpu_clk",
                hz=BOARD_CLOCK_HZ,
                sdc_name="cpu_clk",
                generation="shared release SoC clock",
                drives=("UART status", "UART MMIO", "timer MMIO", "GPIO/status MMIO"),
            ),
        ),
        sdc_constraints=(
            "# CPU v0.1 I28-S01 release_pll_25mhz timing constraints.",
            "create_clock -name board_clk_i -period 40.000 [get_ports {board_clk_i}]",
            "# Enable after a checked PLL wrapper instantiates u_clock_pll.",
            "create_generated_clock -name cpu_clk -source [get_ports {board_clk_i}] -divide_by 1 [get_pins {u_clock_pll/clkout}]",
            "set_false_path -from [get_ports {board_reset_n_i}]",
        ),
        minimum_slack_ns=0.000,
        target_slack_ns=1.500,
        report_gate="python tools\\fpga_gowin_build.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
        notes=(
            "release keeps the 25 MHz default until I28-S04 records a higher passing frequency",
            "the generated-clock constraint is a template and must not be copied into the active SDC before the PLL wrapper exists",
        ),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

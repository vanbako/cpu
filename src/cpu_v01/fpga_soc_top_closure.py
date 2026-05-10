"""FPGA SoC top-level closure plan.

Owner stories:
- I30-S01: publish the FPGA SoC top-level closure plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_debug_evidence, fpga_program_loader, fpga_soc_smoke


JsonValue = Any

FPGA_SOC_TOP_CLOSURE_STORY = "I30-S01"
FPGA_SOC_TOP_CLOSURE_DOC = Path("docs/implementation/fpga-soc-top-closure.md")
FPGA_SOC_TOP_CLOSURE_TOOL = "python tools\\fpga_soc_top_closure.py --check"


@dataclass(frozen=True)
class SocTopClosureShortcut:
    shortcut_id: str
    current_shortcut: str
    rtl_token: str
    risk: str
    owner_story: str
    rtl_change: str
    testbench: str
    validator: str
    board_evidence_handoff: str
    closure_criteria: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "shortcut_id": self.shortcut_id,
            "current_shortcut": self.current_shortcut,
            "rtl_token": self.rtl_token,
            "risk": self.risk,
            "owner_story": self.owner_story,
            "rtl_change": self.rtl_change,
            "testbench": self.testbench,
            "validator": self.validator,
            "board_evidence_handoff": self.board_evidence_handoff,
            "closure_criteria": list(self.closure_criteria),
        }


@dataclass(frozen=True)
class SocTopClosureProfile:
    story: str
    top_module: str
    soc_smoke_gate: str
    program_loader_gate: str
    debug_evidence_gate: str
    shortcuts: tuple[SocTopClosureShortcut, ...]
    sequence: tuple[str, ...]
    non_goals: tuple[str, ...]

    def shortcut_by_id(self, shortcut_id: str) -> SocTopClosureShortcut:
        for shortcut in self.shortcuts:
            if shortcut.shortcut_id == shortcut_id:
                return shortcut
        raise KeyError(shortcut_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "top_module": self.top_module,
            "soc_smoke_gate": self.soc_smoke_gate,
            "program_loader_gate": self.program_loader_gate,
            "debug_evidence_gate": self.debug_evidence_gate,
            "shortcuts": [shortcut.as_dict() for shortcut in self.shortcuts],
            "sequence": list(self.sequence),
            "non_goals": list(self.non_goals),
        }


def fpga_soc_top_closure_profile() -> SocTopClosureProfile:
    return SocTopClosureProfile(
        story=FPGA_SOC_TOP_CLOSURE_STORY,
        top_module="cpu_v01_fpga_top",
        soc_smoke_gate=fpga_soc_smoke.FPGA_SOC_SMOKE_TOOL,
        program_loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        debug_evidence_gate=fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        shortcuts=(
            SocTopClosureShortcut(
                shortcut_id="data_mmio_decoder_bypass",
                current_shortcut=(
                    "cpu_v01_fpga_top connects core dmem requests directly to "
                    "cpu_v01_fpga_data_ram"
                ),
                rtl_token="cpu_v01_fpga_data_ram #(",
                risk=(
                    "firmware cannot reach UART, timer, GPIO/status, or system identity MMIO, "
                    "and reserved windows cannot fault deterministically"
                ),
                owner_story="I30-S02",
                rtl_change=(
                    "replace the direct RAM path with a top-level data/MMIO decoder that "
                    "routes RAM, UART, timer, GPIO/status, system identity, and reserved faults"
                ),
                testbench="rtl/cpu_v01_fpga_top_soc_decoder_tb.sv",
                validator="python tools\\fpga_soc_top_decoder.py --check",
                board_evidence_handoff="I30-S05 integrated firmware smoke and I30-S06 closure archive",
                closure_criteria=(
                    "data_ram receives only decoded RAM-window accesses",
                    "MMIO requests reach every I27-S01 peripheral window",
                    "reserved or malformed accesses return deterministic fault status",
                    "tag_ram sidecar updates remain paired with data_ram writes",
                ),
            ),
            SocTopClosureShortcut(
                shortcut_id="timer_interrupt_tied_off",
                current_shortcut="cpu_v01_fpga_top ties timer_interrupt_pending to 1'b0",
                rtl_token=".timer_interrupt_pending(1'b0)",
                risk="firmware timer interrupts cannot be observed by the integrated CPU top",
                owner_story="I30-S03",
                rtl_change=(
                    "wire the I27-S03 timer compare/acknowledge path into the core interrupt "
                    "inputs and expose deterministic pending status"
                ),
                testbench="rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv",
                validator="python tools\\fpga_soc_top_peripherals.py --check",
                board_evidence_handoff="I30-S05 timer-interrupt smoke and I30-S06 closure archive",
                closure_criteria=(
                    "timer_compare can assert timer_interrupt_pending",
                    "firmware acknowledgement clears the pending source",
                    "timer interrupt evidence names the I27-S03 register path",
                ),
            ),
            SocTopClosureShortcut(
                shortcut_id="uart_pin_mux_missing",
                current_shortcut=(
                    "cpu_v01_fpga_top drives uart_tx_o only from the I25-S02 status streamer "
                    "and has no firmware UART RX input"
                ),
                rtl_token=".uart_tx_o(uart_tx_o)",
                risk="firmware UART output, loader traffic, and debug/status packets cannot share the board UART safely",
                owner_story="I30-S03",
                rtl_change=(
                    "instantiate the I27-S02 UART MMIO block, add top-level UART RX, and "
                    "define a firmware/status TX mux policy"
                ),
                testbench="rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv",
                validator="python tools\\fpga_soc_top_peripherals.py --check",
                board_evidence_handoff="I30-S05 UART smoke, I30-S06 closure archive, and I30-S04 loader arbitration",
                closure_criteria=(
                    "top-level ports include firmware UART RX and a selected TX owner",
                    "status streamer packets remain available for debug evidence",
                    "firmware UART output is bounded by the I27-S02 FIFO rules",
                ),
            ),
            SocTopClosureShortcut(
                shortcut_id="gpio_status_led_mux_missing",
                current_shortcut=(
                    "cpu_v01_fpga_top drives LEDs only from first-test sticky pass/fail and "
                    "retire heartbeat state"
                ),
                rtl_token="assign pass_led_o = pass_sticky_q && !fault_sticky_q;",
                risk="firmware-visible GPIO/status LED requests cannot be observed at the integrated top",
                owner_story="I30-S03",
                rtl_change=(
                    "wire the I27-S04 GPIO/status peripheral to pass/fail/heartbeat LEDs and "
                    "input-change interrupt status"
                ),
                testbench="rtl/cpu_v01_fpga_top_soc_peripherals_tb.sv",
                validator="python tools\\fpga_soc_top_peripherals.py --check",
                board_evidence_handoff="I30-S05 GPIO pass/fail smoke and I30-S06 closure archive",
                closure_criteria=(
                    "firmware STATUS_LEDS can request pass, fail, and heartbeat outputs",
                    "first-test sticky status remains available as a debug source",
                    "GPIO input-change interrupt evidence is visible in the smoke run",
                ),
            ),
            SocTopClosureShortcut(
                shortcut_id="loader_handoff_absent",
                current_shortcut=(
                    "cpu_v01_fpga_top has only debug_halt_request_i for external control and no "
                    "bounded I26-S04 loader handoff"
                ),
                rtl_token="debug_halt_request_i",
                risk="board program loading would require rebuilds or ad hoc host writes instead of a bounded loader path",
                owner_story="I30-S04",
                rtl_change=(
                    "connect the I26-S04 loader handoff to the SoC shell with protected memory "
                    "bounds, tag-policy preservation, and UART/debug status reporting"
                ),
                testbench="rtl/cpu_v01_fpga_top_loader_tb.sv",
                validator="python tools\\fpga_soc_loader_handoff.py --check",
                board_evidence_handoff="I30-S05 loader smoke, I30-S06 closure archive, and I32-S01 monitor profile",
                closure_criteria=(
                    "loader traffic cannot write instruction_rom or create valid tag sidecars",
                    "malformed images report failure over UART/debug status",
                    "loader UART ownership is cleanly arbitrated with firmware/status output",
                ),
            ),
            SocTopClosureShortcut(
                shortcut_id="top_smoke_evidence_missing",
                current_shortcut=(
                    "I27-S05 is a documented_blocker_run rather than an RTL top-level firmware smoke"
                ),
                rtl_token="status_core_port_activity_o",
                risk="the integrated top cannot yet prove UART, timer, syscall/trap, GPIO, and first-failure status together",
                owner_story="I30-S05",
                rtl_change=(
                    "run the integrated top with a firmware fixture after I30-S02/I30-S03 "
                    "remove the decoder and peripheral shortcuts"
                ),
                testbench="rtl/cpu_v01_fpga_top_soc_smoke_tb.sv",
                validator="python tools\\fpga_soc_top_smoke.py --check",
                board_evidence_handoff="I30-S06 closure archive and I31-S01 first-pass build bundle",
                closure_criteria=(
                    "integrated top emits UART output",
                    "timer interrupt is serviced",
                    "syscall/trap return progresses",
                    "GPIO pass/fail and first-failure status are captured",
                ),
            ),
        ),
        sequence=(
            "I30-S02 data/MMIO decoder",
            "I30-S03 UART/timer/GPIO/status and interrupt wiring",
            "I30-S04 board-safe loader handoff",
            "I30-S05 top-level SoC firmware smoke under Verilator",
            "I30-S06 closure evidence archive",
        ),
        non_goals=(
            "new peripherals outside the I27-S01 minimal SoC map",
            "external DDR closure from I29",
            "physical board pass claims before I31",
            "interactive monitor expansion before I32-S01",
        ),
    )


def fpga_soc_top_closure_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_soc_top_closure_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_soc_top_closure() -> str:
    profile = fpga_soc_top_closure_profile()
    lines = [
        "# FPGA SoC Top-Level Closure",
        "",
        f"Story: `{profile.story}`",
        f"Top module: `{profile.top_module}`",
        f"SoC smoke gate: `{profile.soc_smoke_gate}`",
        f"Loader gate: `{profile.program_loader_gate}`",
        f"Debug evidence gate: `{profile.debug_evidence_gate}`",
        "",
        "## Matrix",
        "",
        "| Shortcut | Owner | Testbench | Validator | Handoff |",
        "| --- | --- | --- | --- | --- |",
    ]
    for shortcut in profile.shortcuts:
        lines.append(
            f"| `{shortcut.shortcut_id}` | `{shortcut.owner_story}` | "
            f"`{shortcut.testbench}` | `{shortcut.validator}` | "
            f"{shortcut.board_evidence_handoff} |"
        )
    return "\n".join(lines)


def validate_fpga_soc_top_closure(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_closure_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_TOP_CLOSURE_STORY:
        issues.append("FPGA SoC top closure story mismatch")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("FPGA SoC top closure must target cpu_v01_fpga_top")
    if profile.soc_smoke_gate != fpga_soc_smoke.FPGA_SOC_SMOKE_TOOL:
        issues.append("FPGA SoC top closure must validate against I27-S05")
    if profile.program_loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("FPGA SoC top closure must validate against I26-S04")
    if profile.debug_evidence_gate != fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL:
        issues.append("FPGA SoC top closure must validate against I25-S05")

    issues.extend(fpga_soc_smoke.validate_fpga_soc_smoke(root))
    issues.extend(fpga_program_loader.validate_fpga_program_loader(root))
    issues.extend(fpga_debug_evidence.validate_fpga_debug_evidence(root))
    issues.extend(_validate_shortcut_matrix(root, profile))
    issues.extend(_validate_doc(root))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA SoC top closure profile is not JSON serializable: {exc}")

    return tuple(issues)


def _validate_shortcut_matrix(root: Path, profile: SocTopClosureProfile) -> tuple[str, ...]:
    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    issues: list[str] = []

    shortcut_ids = [shortcut.shortcut_id for shortcut in profile.shortcuts]
    if len(shortcut_ids) != len(set(shortcut_ids)):
        issues.append("FPGA SoC top closure shortcut IDs must be unique")
    if len(profile.shortcuts) < 5:
        issues.append("FPGA SoC top closure matrix must cover all current top-level shortcuts")

    owners = {shortcut.owner_story for shortcut in profile.shortcuts}
    for story in ("I30-S02", "I30-S03", "I30-S04", "I30-S05"):
        if story not in owners:
            issues.append(f"FPGA SoC top closure matrix missing owner {story}")

    for item in ("I30-S02", "I30-S03", "I30-S04", "I30-S05", "I30-S06"):
        if not any(item in step for step in profile.sequence):
            issues.append(f"FPGA SoC top closure sequence missing {item}")

    matrix_text = " ".join(
        " ".join(
            (
                shortcut.current_shortcut,
                shortcut.risk,
                shortcut.rtl_change,
                shortcut.board_evidence_handoff,
            )
        )
        for shortcut in profile.shortcuts
    )
    for token in (
        "dmem",
        "MMIO decoder",
        "timer_interrupt_pending",
        "UART",
        "GPIO/status",
        "loader",
        "documented_blocker_run",
    ):
        if token not in matrix_text:
            issues.append(f"FPGA SoC top closure matrix missing {token}")

    for shortcut in profile.shortcuts:
        if shortcut.rtl_token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing shortcut token {shortcut.rtl_token}")
        if not shortcut.owner_story.startswith("I30-S"):
            issues.append(f"{shortcut.shortcut_id}: owner story must be an I30 story")
        if not shortcut.testbench.startswith("rtl/") or not shortcut.testbench.endswith(".sv"):
            issues.append(f"{shortcut.shortcut_id}: testbench must be an RTL SystemVerilog path")
        if not shortcut.validator.startswith("python tools\\") or not shortcut.validator.endswith("--check"):
            issues.append(f"{shortcut.shortcut_id}: validator must be a Python check command")
        if not shortcut.board_evidence_handoff:
            issues.append(f"{shortcut.shortcut_id}: board evidence handoff must not be empty")
        if not shortcut.closure_criteria:
            issues.append(f"{shortcut.shortcut_id}: closure criteria must not be empty")

    return tuple(issues)


def _validate_doc(root: Path) -> tuple[str, ...]:
    doc = _read_if_exists(root / FPGA_SOC_TOP_CLOSURE_DOC)
    issues: list[str] = []
    for token in (
        "Story: I30-S01",
        FPGA_SOC_TOP_CLOSURE_TOOL,
        "python tools\\fpga_soc_smoke.py --check",
        "python tools\\fpga_program_loader.py --check",
        "python tools\\fpga_debug_evidence.py --check",
        "cpu_v01_fpga_top",
        "data_mmio_decoder_bypass",
        "timer_interrupt_tied_off",
        "uart_pin_mux_missing",
        "gpio_status_led_mux_missing",
        "loader_handoff_absent",
        "top_smoke_evidence_missing",
        "I30-S02",
        "I30-S03",
        "I30-S04",
        "I30-S05",
        "I30-S06",
        "rtl/cpu_v01_fpga_top_soc_decoder_tb.sv",
        "python tools\\fpga_soc_top_decoder.py --check",
        "board-evidence handoff",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_TOP_CLOSURE_DOC.as_posix()} missing {token}")
    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

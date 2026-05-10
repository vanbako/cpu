"""FPGA reset and clock-domain crossing audit profile.

Owner stories:
- I28-S02: audit reset and CDC handling in the FPGA wrapper and debug paths.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_clock_profiles, fpga_top, fpga_uart_status


JsonValue = Any

FPGA_RESET_CDC_STORY = "I28-S02"
FPGA_RESET_CDC_DOC = Path("docs/implementation/fpga-reset-cdc-audit.md")
FPGA_RESET_CDC_TOOL = "python tools\\fpga_reset_cdc.py --check"
FPGA_TOP_GATE = "python tools\\fpga_top_wrapper.py --check"


@dataclass(frozen=True)
class ResetCdcItem:
    name: str
    kind: str
    source: str
    destination: str
    clock_domain: str
    handling: str
    status: str
    evidence_tokens: tuple[str, ...]
    risk: str
    required_action: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "destination": self.destination,
            "clock_domain": self.clock_domain,
            "handling": self.handling,
            "status": self.status,
            "evidence_tokens": list(self.evidence_tokens),
            "risk": self.risk,
            "required_action": self.required_action,
        }


@dataclass(frozen=True)
class ResetCdcProfile:
    story: str
    clock_profile_gate: str
    top_wrapper_gate: str
    uart_status_gate: str
    current_clock_profile: str
    release_clock_profile: str
    lint_commands: tuple[str, ...]
    items: tuple[ResetCdcItem, ...]
    open_issues: tuple[str, ...]
    handoffs: tuple[str, ...]

    def item_by_name(self, name: str) -> ResetCdcItem:
        for item in self.items:
            if item.name == name:
                return item
        raise KeyError(f"unknown reset/CDC item {name!r}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "clock_profile_gate": self.clock_profile_gate,
            "top_wrapper_gate": self.top_wrapper_gate,
            "uart_status_gate": self.uart_status_gate,
            "current_clock_profile": self.current_clock_profile,
            "release_clock_profile": self.release_clock_profile,
            "lint_commands": list(self.lint_commands),
            "items": [item.as_dict() for item in self.items],
            "open_issues": list(self.open_issues),
            "handoffs": list(self.handoffs),
        }


def fpga_reset_cdc_profile() -> ResetCdcProfile:
    return ResetCdcProfile(
        story=FPGA_RESET_CDC_STORY,
        clock_profile_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        top_wrapper_gate=FPGA_TOP_GATE,
        uart_status_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        current_clock_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        release_clock_profile=fpga_clock_profiles.RELEASE_PROFILE_ID,
        lint_commands=(
            fpga_top.fpga_top_verilator_command(),
            "verilator --lint-only --timing --top-module cpu_v01_fpga_top_tb "
            "rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv "
            "rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv "
            "rtl/cpu_v01_fpga_gpio_status.sv "
            "rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_tb.sv",
        ),
        items=(
            ResetCdcItem(
                name="board_clk_i",
                kind="source_clock",
                source="board input",
                destination="cpu_v01_fpga_top current clock domain",
                clock_domain="board_clk_i",
                handling="single current domain constrained by I24-S02 and named by I28-S01",
                status="implemented_current_domain",
                evidence_tokens=(
                    "input  logic board_clk_i",
                    "always_ff @(posedge board_clk_i",
                    ".clk(board_clk_i)",
                ),
                risk="unconstrained clock or wrong pin would stop all status evidence",
                required_action="keep board_clk_i constrained and audited by Gowin reports",
            ),
            ResetCdcItem(
                name="board_reset_n_i",
                kind="async_reset_input",
                source="active-low board reset input",
                destination="reset_sync_q then core_rst_n",
                clock_domain="board_clk_i",
                handling="async assert and synchronized release through RESET_SYNC_STAGES",
                status="implemented_two_stage_sync_release",
                evidence_tokens=(
                    "parameter int RESET_SYNC_STAGES = 2",
                    "always_ff @(posedge board_clk_i or negedge board_reset_n_i)",
                    "reset_sync_q <= {reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1}",
                    "assign core_rst_n = reset_sync_q[RESET_SYNC_STAGES-1]",
                ),
                risk="reset release metastability would corrupt first retire and UART status",
                required_action="preserve at least two stages and false-path the async input",
            ),
            ResetCdcItem(
                name="core_rst_n",
                kind="synchronized_reset",
                source="reset_sync_q",
                destination="core, BRAM adapters, UART status streamer, and status flops",
                clock_domain="board_clk_i",
                handling="fanout reset inside the current board clock domain",
                status="implemented_same_domain_fanout",
                evidence_tokens=(
                    ".rst_n(core_rst_n)",
                    "always_ff @(posedge board_clk_i or negedge core_rst_n)",
                    ".rst_n(core_rst_n)",
                ),
                risk="mixed reset domains would make debug/status evidence ambiguous",
                required_action="gate any future PLL domain reset with synchronized release and lock evidence",
            ),
            ResetCdcItem(
                name="debug_halt_request_i",
                kind="async_debug_input",
                source="board, probe, or testbench debug request",
                destination="cpu_v01_core.debug_halt_request",
                clock_domain="board_clk_i",
                handling="currently passed through as a documented open issue",
                status="documented_open_issue",
                evidence_tokens=(
                    "input  logic debug_halt_request_i",
                    ".debug_halt_request(debug_halt_request_i)",
                ),
                risk="a board-driven halt request can be asynchronous to board_clk_i",
                required_action="tie low for first board smoke or add a two-flop synchronizer before board use",
            ),
            ResetCdcItem(
                name="uart_tx_o",
                kind="shared_uart_output",
                source="cpu_v01_fpga_uart_status_streamer, cpu_v01_fpga_uart_mmio, and loader_uart_tx_i",
                destination="board UART or PMOD output",
                clock_domain="board_clk_i",
                handling="idle-high firmware/status/loader TX combine in the same current clock domain",
                status="implemented_same_domain_output",
                evidence_tokens=(
                    "cpu_v01_fpga_uart_status_streamer #(",
                    ".clk(board_clk_i)",
                    "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
                ),
                risk="UART baud changes must follow the selected clock profile",
                required_action="recompute UART divisors when a non-25 MHz profile is selected",
            ),
            ResetCdcItem(
                name="uart_rx_i",
                kind="async_uart_input",
                source="board UART RX input",
                destination="cpu_v01_fpga_uart_mmio RX sampler",
                clock_domain="board_clk_i",
                handling="two-flop input synchronizer inside the UART MMIO block before RX sampling",
                status="implemented_two_stage_sync",
                evidence_tokens=(
                    "input  logic uart_rx_i",
                    ".uart_rx_i(uart_rx_i)",
                    "uart_rx_meta_q <= uart_rx_i",
                    "uart_rx_sync_q <= uart_rx_meta_q",
                ),
                risk="board UART RX is asynchronous to board_clk_i and can metastabilize without the synchronizer",
                required_action="preserve the two-stage RX synchronizer when changing UART or loader ingress",
            ),
            ResetCdcItem(
                name="loader_handoff_inputs",
                kind="external_loader_control",
                source="I26-S04 loader transport or testbench",
                destination="cpu_v01_fpga_soc_loader_handoff",
                clock_domain="board_clk_i",
                handling="sampled in the board clock domain after the external monitor presents stable request signals",
                status="documented_synchronous_boundary",
                evidence_tokens=(
                    "input  logic loader_req_valid_i",
                    ".loader_req_valid(loader_req_valid_i)",
                    "cpu_v01_fpga_soc_loader_handoff #(",
                ),
                risk="an asynchronous host bridge can metastabilize loader request or status handoff signals",
                required_action="synchronize future UART/JTAG monitor command outputs before driving loader_req_*",
            ),
            ResetCdcItem(
                name="status_debug_outputs",
                kind="debug_status_outputs",
                source="cpu_v01_core and wrapper sticky status",
                destination="LEDs, probes, and status pins",
                clock_domain="board_clk_i",
                handling="output-only projections from the current clock domain",
                status="implemented_same_domain_outputs",
                evidence_tokens=(
                    "assign heartbeat_led_o = debug_retire_sequence[0]",
                    "assign status_retire_count_o = debug_retire_sequence[31:0]",
                    "assign debug_pcc_cursor_low_o = debug_pcc.payload.cursor[31:0]",
                ),
                risk="external probes must sample with board_clk_i or through a tool-owned analyzer clock",
                required_action="keep I25-S03 probes on board_clk_i until release PLL clocks are implemented",
            ),
            ResetCdcItem(
                name="release_pll_domain",
                kind="generated_clock_domain",
                source=fpga_clock_profiles.RELEASE_PROFILE_ID,
                destination="future cpu_clk domain",
                clock_domain="cpu_clk",
                handling="blocked generated clock from I28-S01; no active RTL domain yet",
                status="blocked_until_pll_wrapper",
                evidence_tokens=(
                    "release_pll_25mhz",
                    "create_generated_clock",
                    "u_clock_pll/clkout",
                ),
                risk="PLL lock, reset release, and debug crossings are not yet proven",
                required_action="add PLL lock/reset sequencing and generated-clock SDC before selecting release profile",
            ),
        ),
        open_issues=(
            "debug_halt_request_i is raw in cpu_v01_fpga_top and must be tied low or synchronized before board use",
            "release_pll_25mhz has no RTL PLL wrapper, lock signal, or active generated-clock SDC yet",
            "external loader transports must synchronize command outputs before driving loader handoff inputs",
        ),
        handoffs=(
            "I28-S03 should flag unconstrained generated clocks and missing reset/clock report evidence",
            "I28-S04 should keep frequency sweeps on debug_direct_25mhz until release PLL reset handling is implemented",
            "I28-S05 should include the selected clock profile and reset/CDC audit in the reproducible build profile",
        ),
    )


def fpga_reset_cdc_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_reset_cdc_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_reset_cdc_command_plan() -> tuple[str, ...]:
    profile = fpga_reset_cdc_profile()
    return (
        profile.clock_profile_gate,
        profile.top_wrapper_gate,
        profile.uart_status_gate,
        *profile.lint_commands,
        FPGA_RESET_CDC_TOOL,
    )


def render_fpga_reset_cdc(profile: ResetCdcProfile | None = None) -> str:
    if profile is None:
        profile = fpga_reset_cdc_profile()
    lines = [
        "# FPGA Reset CDC Audit",
        "",
        f"Story: {profile.story}",
        f"Current profile: `{profile.current_clock_profile}`",
        f"Release profile: `{profile.release_clock_profile}`",
        "",
        "## Items",
        "",
        "| Item | Kind | Domain | Status | Handling | Required action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in profile.items:
        lines.append(
            f"| `{item.name}` | {item.kind} | `{item.clock_domain}` | {item.status} | "
            f"{item.handling} | {item.required_action} |"
        )
    lines.extend(["", "## Open Issues", ""])
    lines.extend(f"- {issue}." for issue in profile.open_issues)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_reset_cdc(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_reset_cdc_profile()
    issues: list[str] = []

    if profile.story != FPGA_RESET_CDC_STORY:
        issues.append(f"reset/CDC story must be {FPGA_RESET_CDC_STORY}")
    if profile.clock_profile_gate != fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL:
        issues.append("reset/CDC audit must depend on I28-S01 clock profiles")
    if profile.top_wrapper_gate != FPGA_TOP_GATE:
        issues.append("reset/CDC audit must depend on I23-S02 top wrapper")
    if profile.current_clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("reset/CDC audit must use the debug direct current profile")
    if profile.release_clock_profile != fpga_clock_profiles.RELEASE_PROFILE_ID:
        issues.append("reset/CDC audit must name the blocked release PLL profile")

    issues.extend(fpga_clock_profiles.validate_fpga_clock_profiles(root))
    issues.extend(fpga_top.validate_fpga_top_wrapper(root))
    issues.extend(fpga_uart_status.validate_fpga_uart_status(root))

    item_names = {item.name for item in profile.items}
    for required in (
        "board_clk_i",
        "board_reset_n_i",
        "core_rst_n",
        "debug_halt_request_i",
        "uart_tx_o",
        "uart_rx_i",
        "loader_handoff_inputs",
        "status_debug_outputs",
        "release_pll_domain",
    ):
        if required not in item_names:
            issues.append(f"missing reset/CDC item {required}")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    uart_mmio = _read_if_exists(root / "rtl" / "cpu_v01_fpga_uart_mmio.sv")
    clock_doc = _read_if_exists(root / fpga_clock_profiles.FPGA_CLOCK_PROFILES_DOC)
    for item in profile.items:
        if item.name == "release_pll_domain":
            haystack = clock_doc
        elif item.name == "uart_rx_i":
            haystack = top + "\n" + uart_mmio
        else:
            haystack = top
        for token in item.evidence_tokens:
            if token not in haystack:
                issues.append(f"{item.name} missing evidence token {token}")
        if item.status == "documented_open_issue" and item.name not in " ".join(profile.open_issues):
            issues.append(f"{item.name} open issue must be named explicitly")

    debug_halt = profile.item_by_name("debug_halt_request_i")
    if debug_halt.status != "documented_open_issue":
        issues.append("debug_halt_request_i must remain a documented open issue")
    release = profile.item_by_name("release_pll_domain")
    if "blocked" not in release.status:
        issues.append("release PLL domain must remain blocked until RTL exists")
    uart_rx = profile.item_by_name("uart_rx_i")
    if uart_rx.status != "implemented_two_stage_sync":
        issues.append("uart_rx_i must be audited as an implemented two-stage synchronizer")

    doc = _read_if_exists(root / FPGA_RESET_CDC_DOC)
    for token in (
        "Story: I28-S02",
        FPGA_RESET_CDC_TOOL,
        "python tools\\fpga_clock_profiles.py --check",
        "python tools\\fpga_top_wrapper.py --check",
        "python tools\\fpga_uart_status_streamer.py --check",
        "board_reset_n_i",
        "RESET_SYNC_STAGES",
        "core_rst_n",
        "debug_halt_request_i",
        "documented_open_issue",
        "uart_tx_o",
        "uart_rx_i",
        "loader handoff inputs",
        "status_debug_outputs",
        "release_pll_25mhz",
        "create_generated_clock",
        "I28-S03",
        "I28-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RESET_CDC_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA reset/CDC profile is not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

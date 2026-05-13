"""FPGA CPU/compositor memory arbitration profile and fixture.

Owner stories:
- I36-S08: integrate CPU and compositor memory arbitration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_compositor_fetch,
    fpga_ddr_wrapper,
    fpga_soc_top_decoder,
    fpga_video_mmio,
)


JsonValue = Any

FPGA_COMPOSITOR_ARBITER_STORY = "I36-S08"
FPGA_COMPOSITOR_ARBITER_DOC = Path("docs/implementation/fpga-compositor-arbiter.md")
FPGA_COMPOSITOR_ARBITER_TOOL = "python tools\\fpga_compositor_arbiter.py --check"
FPGA_COMPOSITOR_ARBITER_RTL = Path("rtl/cpu_v01_fpga_compositor_mem_arbiter.sv")
FPGA_COMPOSITOR_ARBITER_TB = Path("rtl/cpu_v01_fpga_compositor_mem_arbiter_tb.sv")

OWNER_NONE = "none"
OWNER_CPU = "cpu"
OWNER_VIDEO = "video"
VIDEO_STALL_UNDERFLOW_CYCLES = 2


@dataclass(frozen=True)
class ArbitrationRequest:
    source: str
    addr_cell: int
    write: bool
    wdata: int = 0
    mmio: bool = False
    len_cells: int = 1

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "source": self.source,
            "addr_cell": self.addr_cell,
            "write": self.write,
            "wdata": self.wdata,
            "mmio": self.mmio,
            "len_cells": self.len_cells,
        }


@dataclass(frozen=True)
class ArbitrationStep:
    cycle: int
    grant: str
    cpu_ready: bool
    video_ready: bool
    memory_request: ArbitrationRequest | None
    cpu_response_valid: bool
    cpu_fault: bool
    video_response_valid: bool
    video_error: bool
    descriptor_update_seen: bool
    video_starved: bool
    underflow_event: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "cycle": self.cycle,
            "grant": self.grant,
            "cpu_ready": self.cpu_ready,
            "video_ready": self.video_ready,
            "memory_request": None if self.memory_request is None else self.memory_request.as_dict(),
            "cpu_response_valid": self.cpu_response_valid,
            "cpu_fault": self.cpu_fault,
            "video_response_valid": self.video_response_valid,
            "video_error": self.video_error,
            "descriptor_update_seen": self.descriptor_update_seen,
            "video_starved": self.video_starved,
            "underflow_event": self.underflow_event,
        }


@dataclass(frozen=True)
class ArbitrationRun:
    steps: tuple[ArbitrationStep, ...]
    cpu_grant_count: int
    video_grant_count: int
    video_starvation_count: int
    video_underflow_count: int
    descriptor_update_count: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "steps": [step.as_dict() for step in self.steps],
            "cpu_grant_count": self.cpu_grant_count,
            "video_grant_count": self.video_grant_count,
            "video_starvation_count": self.video_starvation_count,
            "video_underflow_count": self.video_underflow_count,
            "descriptor_update_count": self.descriptor_update_count,
        }


@dataclass
class ArbitrationState:
    cpu_grant_count: int = 0
    video_grant_count: int = 0
    video_starvation_count: int = 0
    video_underflow_count: int = 0
    descriptor_update_count: int = 0
    video_wait_cycles: int = 0
    cycle: int = 0

    def step(
        self,
        *,
        cpu_request: ArbitrationRequest | None = None,
        video_request: ArbitrationRequest | None = None,
        memory_ready: bool = True,
        memory_error: bool = False,
        descriptor_update: bool = False,
    ) -> ArbitrationStep:
        if cpu_request is not None and cpu_request.source != OWNER_CPU:
            raise ValueError("cpu_request source must be cpu")
        if video_request is not None and video_request.source != OWNER_VIDEO:
            raise ValueError("video_request source must be video")

        grant = OWNER_NONE
        memory_request: ArbitrationRequest | None = None
        cpu_ready = False
        video_ready = False
        cpu_response_valid = False
        cpu_fault = False
        video_response_valid = False
        video_error = False
        video_starved = False
        underflow_event = False

        if descriptor_update:
            self.descriptor_update_count += 1

        if memory_ready and cpu_request is not None:
            grant = OWNER_CPU
            memory_request = cpu_request
            cpu_ready = True
            self.cpu_grant_count += 1
            cpu_response_valid = True
            cpu_fault = memory_error
        elif memory_ready and video_request is not None:
            grant = OWNER_VIDEO
            memory_request = video_request
            video_ready = True
            self.video_grant_count += 1
            video_response_valid = True
            video_error = memory_error
            self.video_wait_cycles = 0
            if memory_error:
                self.video_underflow_count += 1
                underflow_event = True

        if video_request is not None and not video_ready:
            video_starved = True
            self.video_starvation_count += 1
            self.video_wait_cycles += 1
            if self.video_wait_cycles >= VIDEO_STALL_UNDERFLOW_CYCLES:
                self.video_underflow_count += 1
                underflow_event = True
                self.video_wait_cycles = 0
        elif video_ready:
            self.video_wait_cycles = 0

        step = ArbitrationStep(
            cycle=self.cycle,
            grant=grant,
            cpu_ready=cpu_ready,
            video_ready=video_ready,
            memory_request=memory_request,
            cpu_response_valid=cpu_response_valid,
            cpu_fault=cpu_fault,
            video_response_valid=video_response_valid,
            video_error=video_error,
            descriptor_update_seen=descriptor_update,
            video_starved=video_starved,
            underflow_event=underflow_event,
        )
        self.cycle += 1
        return step


@dataclass(frozen=True)
class CompositorArbiterProfile:
    story: str
    fetch_gate: str
    decoder_gate: str
    ddr_wrapper_gate: str
    video_mmio_gate: str
    validator: str
    arbiter_module: str
    testbench_module: str
    arbitration_policy: str
    request_sources: tuple[str, ...]
    response_rules: tuple[str, ...]
    counters: tuple[str, ...]
    rtl_sources: tuple[str, ...]
    verilator_commands: tuple[str, ...]
    handoffs: tuple[str, ...]
    non_goals: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "fetch_gate": self.fetch_gate,
            "decoder_gate": self.decoder_gate,
            "ddr_wrapper_gate": self.ddr_wrapper_gate,
            "video_mmio_gate": self.video_mmio_gate,
            "validator": self.validator,
            "arbiter_module": self.arbiter_module,
            "testbench_module": self.testbench_module,
            "arbitration_policy": self.arbitration_policy,
            "request_sources": list(self.request_sources),
            "response_rules": list(self.response_rules),
            "counters": list(self.counters),
            "rtl_sources": list(self.rtl_sources),
            "verilator_commands": list(self.verilator_commands),
            "handoffs": list(self.handoffs),
            "non_goals": list(self.non_goals),
        }


def fpga_compositor_arbiter_profile() -> CompositorArbiterProfile:
    return CompositorArbiterProfile(
        story=FPGA_COMPOSITOR_ARBITER_STORY,
        fetch_gate=fpga_compositor_fetch.FPGA_COMPOSITOR_FETCH_TOOL,
        decoder_gate=fpga_soc_top_decoder.FPGA_SOC_TOP_DECODER_TOOL,
        ddr_wrapper_gate=fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        video_mmio_gate=fpga_video_mmio.FPGA_VIDEO_MMIO_TOOL,
        validator=FPGA_COMPOSITOR_ARBITER_TOOL,
        arbiter_module="cpu_v01_fpga_compositor_mem_arbiter",
        testbench_module="cpu_v01_fpga_compositor_mem_arbiter_tb",
        arbitration_policy=(
            "single-outstanding CPU-first arbitration: CPU data/MMIO requests keep ordering and win "
            "same-cycle contention; compositor reads receive deterministic backpressure and visible "
            "starvation/underflow counters"
        ),
        request_sources=("cpu_data_mmio", "compositor_scanout_read"),
        response_rules=(
            "CPU responses return in issue order and memory errors become CPU fault responses",
            "compositor responses preserve read data and convert memory errors or bounded stalls into underflow accounting",
            "descriptor_update pulses are counted while arbitration continues to avoid hiding vblank descriptor changes",
        ),
        counters=(
            "cpu_grant_count",
            "video_grant_count",
            "video_starvation_count",
            "video_underflow_count",
            "descriptor_update_count",
        ),
        rtl_sources=(FPGA_COMPOSITOR_ARBITER_RTL.as_posix(), FPGA_COMPOSITOR_ARBITER_TB.as_posix()),
        verilator_commands=fpga_compositor_arbiter_verilator_commands(),
        handoffs=(
            "future top-level integration can insert cpu_v01_fpga_compositor_mem_arbiter between I30-S02 decoder traffic and the I29-S02 DDR adapter",
            "I36-S06/I36-S07 evidence consumes video_starvation_count and video_underflow_count for board triage",
            "later cache/coherency work may replace CPU-first policy only with new ordering evidence",
        ),
        non_goals=(
            "cache_coherent_graphics",
            "multi_outstanding_ddr_scheduler",
            "new_firmware_visible_register_map",
            "physical_board_bandwidth_claim",
        ),
    )


def fpga_compositor_arbiter_verilator_commands() -> tuple[str, ...]:
    return (
        "verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_mem_arbiter_tb "
        "rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_mem_arbiter.sv "
        "rtl/cpu_v01_fpga_compositor_mem_arbiter_tb.sv",
    )


def simulate_arbitration_demo() -> ArbitrationRun:
    state = ArbitrationState()
    steps = [
        state.step(
            cpu_request=ArbitrationRequest(
                OWNER_CPU,
                addr_cell=0x0001_0000,
                write=True,
                wdata=0x1234,
                mmio=False,
            ),
            video_request=ArbitrationRequest(
                OWNER_VIDEO,
                addr_cell=0x0110_0000,
                write=False,
                len_cells=1,
            ),
            descriptor_update=True,
        ),
        state.step(
            video_request=ArbitrationRequest(
                OWNER_VIDEO,
                addr_cell=0x0110_0000,
                write=False,
                len_cells=1,
            ),
        ),
        state.step(
            cpu_request=ArbitrationRequest(
                OWNER_CPU,
                addr_cell=0x00F0_0500,
                write=False,
                mmio=True,
            ),
            memory_error=True,
        ),
        state.step(
            video_request=ArbitrationRequest(
                OWNER_VIDEO,
                addr_cell=0x0110_0001,
                write=False,
                len_cells=1,
            ),
            memory_ready=False,
        ),
        state.step(
            video_request=ArbitrationRequest(
                OWNER_VIDEO,
                addr_cell=0x0110_0001,
                write=False,
                len_cells=1,
            ),
            memory_ready=False,
        ),
    ]
    return ArbitrationRun(
        steps=tuple(steps),
        cpu_grant_count=state.cpu_grant_count,
        video_grant_count=state.video_grant_count,
        video_starvation_count=state.video_starvation_count,
        video_underflow_count=state.video_underflow_count,
        descriptor_update_count=state.descriptor_update_count,
    )


def fpga_compositor_arbiter_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_compositor_arbiter_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_compositor_arbiter_demo_json(*, indent: int = 2) -> str:
    return json.dumps(simulate_arbitration_demo().as_dict(), indent=indent, sort_keys=True)


def render_fpga_compositor_arbiter(profile: CompositorArbiterProfile | None = None) -> str:
    if profile is None:
        profile = fpga_compositor_arbiter_profile()
    lines = [
        "# FPGA Compositor Memory Arbiter",
        "",
        f"Story: `{profile.story}`",
        f"Module: `{profile.arbiter_module}`",
        "",
        "## Policy",
        "",
        profile.arbitration_policy,
        "",
        "## Counters",
        "",
    ]
    lines.extend(f"- `{counter}`" for counter in profile.counters)
    return "\n".join(lines)


def validate_fpga_compositor_arbiter(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_compositor_arbiter_profile()
    issues: list[str] = []

    issues.extend(
        f"I36-S02 prerequisite: {issue}"
        for issue in fpga_compositor_fetch.validate_fpga_compositor_fetch(root)
    )
    issues.extend(
        f"I30-S02 prerequisite: {issue}"
        for issue in fpga_soc_top_decoder.validate_fpga_soc_top_decoder(root)
    )
    issues.extend(
        f"I29-S02 prerequisite: {issue}"
        for issue in fpga_ddr_wrapper.validate_fpga_ddr_wrapper(root)
    )
    issues.extend(
        f"I35-S04 prerequisite: {issue}"
        for issue in fpga_video_mmio.validate_fpga_video_mmio(root)
    )

    if profile.story != FPGA_COMPOSITOR_ARBITER_STORY:
        issues.append(f"compositor arbiter story must be {FPGA_COMPOSITOR_ARBITER_STORY}")
    if profile.fetch_gate != fpga_compositor_fetch.FPGA_COMPOSITOR_FETCH_TOOL:
        issues.append("compositor arbiter must depend on I36-S02 fetch")
    if profile.decoder_gate != fpga_soc_top_decoder.FPGA_SOC_TOP_DECODER_TOOL:
        issues.append("compositor arbiter must depend on I30-S02 decoder")
    if profile.ddr_wrapper_gate != fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL:
        issues.append("compositor arbiter must depend on I29-S02 DDR wrapper")
    if profile.video_mmio_gate != fpga_video_mmio.FPGA_VIDEO_MMIO_TOOL:
        issues.append("compositor arbiter must depend on I35-S04 video MMIO")
    for token in ("CPU-first", "single-outstanding", "starvation/underflow"):
        if token not in profile.arbitration_policy:
            issues.append(f"arbitration policy missing {token}")
    for counter in (
        "cpu_grant_count",
        "video_grant_count",
        "video_starvation_count",
        "video_underflow_count",
        "descriptor_update_count",
    ):
        if counter not in profile.counters:
            issues.append(f"missing arbiter counter {counter}")

    demo = simulate_arbitration_demo()
    if demo.steps[0].grant != OWNER_CPU or not demo.steps[0].video_starved:
        issues.append("simultaneous CPU/video request must grant CPU and starve video")
    if demo.steps[1].grant != OWNER_VIDEO or not demo.steps[1].video_response_valid:
        issues.append("video request must be granted after CPU request completes")
    if not demo.steps[2].cpu_fault:
        issues.append("CPU memory error must be returned as a CPU fault response")
    if demo.video_starvation_count < 3:
        issues.append("demo must expose video starvation count")
    if demo.video_underflow_count < 1:
        issues.append("bounded video stall must increment underflow count")
    if demo.descriptor_update_count != 1:
        issues.append("descriptor update pulse must be counted during arbitration")

    for source in profile.rtl_sources:
        if not (root / source).exists():
            issues.append(f"missing RTL source {source}")
    rtl = _read_if_exists(root / FPGA_COMPOSITOR_ARBITER_RTL)
    tb = _read_if_exists(root / FPGA_COMPOSITOR_ARBITER_TB)
    for token in (
        "module cpu_v01_fpga_compositor_mem_arbiter",
        "CPU_FIRST_SINGLE_OUTSTANDING",
        "cpu_req_mmio_i",
        "video_req_valid_i",
        "descriptor_update_i",
        "assign cpu_req_ready_o =",
        "assign video_req_ready_o =",
        "assign mem_req_owner_o =",
        "video_starvation_count_o",
        "video_underflow_count_o",
        "descriptor_update_count_o",
        "cpu_rsp_fault_o <= mem_rsp_error_i",
        "video_rsp_error_o <= mem_rsp_error_i",
    ):
        if token not in rtl:
            issues.append(f"{FPGA_COMPOSITOR_ARBITER_RTL.as_posix()} missing {token}")
    for token in (
        "module cpu_v01_fpga_compositor_mem_arbiter_tb",
        "cpu_v01_fpga_compositor_mem_arbiter dut",
        "compositor arbiter did not grant CPU before video",
        "compositor arbiter did not route video response",
        "compositor arbiter did not preserve CPU fault response",
        "compositor arbiter did not expose video starvation counter",
        "compositor arbiter did not count descriptor update",
        "compositor arbiter did not report underflow after bounded video stall",
    ):
        if token not in tb:
            issues.append(f"{FPGA_COMPOSITOR_ARBITER_TB.as_posix()} missing {token}")

    doc = _read_if_exists(root / FPGA_COMPOSITOR_ARBITER_DOC)
    for token in (
        "Story: I36-S08",
        FPGA_COMPOSITOR_ARBITER_TOOL,
        "python tools\\fpga_compositor_fetch.py --check",
        "python tools\\fpga_soc_top_decoder.py --check",
        "python tools\\fpga_ddr_wrapper.py --check",
        "python tools\\fpga_video_mmio.py --check",
        "cpu_v01_fpga_compositor_mem_arbiter",
        "CPU-first",
        "single-outstanding",
        "video_starvation_count",
        "video_underflow_count",
        "descriptor_update_count",
        "CPU fault responses",
        "simultaneous CPU writes",
        "descriptor updates",
        "scanout fetches",
        "I36-S06",
        "I36-S07",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_COMPOSITOR_ARBITER_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(demo.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"compositor arbiter objects are not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

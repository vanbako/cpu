"""FPGA first-test bring-up profile for CPU v0.1.

Owner stories:
- I23-S01: FPGA first-test boundary and target profile.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import cells, platform


JsonValue = Any

FPGA_FIRST_TEST_DOC = Path("docs/implementation/fpga-first-test-plan.md")
FPGA_FIRST_TEST_STORY = "I23-S01"
PROFILE_NAME = "cpu_v01_fpga_first_test_bram_smoke"
FPGA_TOP_MODULE = "cpu_v01_fpga_top"
CORE_TOP_MODULE = "cpu_v01_core"
IMAGE_FORMAT_NAME = "hex24-cells-v1"
TARGET_BOARD_NAME = "Sipeed Tang Mega 138K Dock"
TARGET_BOARD_VENDOR = "Sipeed"
TARGET_BOARD_VARIANT = "Tang Mega 138K Dock (non-Pro)"
TARGET_FPGA_DEVICE = "GW5AST-LV138PG484A"
TARGET_IDE_PACKAGE = "PBG484A"
TARGET_DEVICE_VERSION = "B/C, verify on board or JTAG scan"
TARGET_CONSTRAINT_SOURCE = "Sipeed All PIN Constraints package for Tang Mega 138K"


@dataclass(frozen=True)
class FpgaBoardTarget:
    name: str
    vendor: str
    variant: str
    fpga_device: str
    ide_package: str
    device_version: str
    programming_interfaces: tuple[str, ...]
    observation_interfaces: tuple[str, ...]
    constraint_source: str
    source_urls: tuple[str, ...]
    open_items: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "variant": self.variant,
            "fpga_device": self.fpga_device,
            "ide_package": self.ide_package,
            "device_version": self.device_version,
            "programming_interfaces": list(self.programming_interfaces),
            "observation_interfaces": list(self.observation_interfaces),
            "constraint_source": self.constraint_source,
            "source_urls": list(self.source_urls),
            "open_items": list(self.open_items),
        }


@dataclass(frozen=True)
class FpgaClockResetProfile:
    board_class: str
    input_clock: str
    input_reset: str
    reset_polarity: str
    reset_sync_stages: int
    maximum_core_clock_hz: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "board_class": self.board_class,
            "input_clock": self.input_clock,
            "input_reset": self.input_reset,
            "reset_polarity": self.reset_polarity,
            "reset_sync_stages": self.reset_sync_stages,
            "maximum_core_clock_hz": self.maximum_core_clock_hz,
        }


@dataclass(frozen=True)
class FpgaMemoryRegion:
    name: str
    kind: str
    address_space: str
    base_cell: int
    size_cells: int
    port: str
    initialization: str
    tag_policy: str

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.size_cells

    def contains(self, address: int) -> bool:
        return self.base_cell <= address < self.end_cell

    def overlaps(self, other: "FpgaMemoryRegion") -> bool:
        if self.address_space != other.address_space:
            return False
        return self.base_cell < other.end_cell and other.base_cell < self.end_cell

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "kind": self.kind,
            "address_space": self.address_space,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "size_cells": self.size_cells,
            "port": self.port,
            "initialization": self.initialization,
            "tag_policy": self.tag_policy,
        }


@dataclass(frozen=True)
class FpgaImageFormat:
    name: str
    cell_bits: int
    rom_init_file: str
    data_init_file: str
    line_format: str
    source_fixture: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "cell_bits": self.cell_bits,
            "rom_init_file": self.rom_init_file,
            "data_init_file": self.data_init_file,
            "line_format": self.line_format,
            "source_fixture": self.source_fixture,
        }


@dataclass(frozen=True)
class FpgaObservationSignal:
    name: str
    width: int
    source: str
    required: bool
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "width": self.width,
            "source": self.source,
            "required": self.required,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FpgaBuildFlow:
    name: str
    toolchain_profile: str
    required_steps: tuple[str, ...]
    required_constraints: tuple[str, ...]
    failure_conditions: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "toolchain_profile": self.toolchain_profile,
            "required_steps": list(self.required_steps),
            "required_constraints": list(self.required_constraints),
            "failure_conditions": list(self.failure_conditions),
        }


@dataclass(frozen=True)
class FpgaFirstTestProfile:
    name: str
    story: str
    fpga_top_module: str
    core_top_module: str
    target_board: FpgaBoardTarget
    clock_reset: FpgaClockResetProfile
    memories: tuple[FpgaMemoryRegion, ...]
    image_format: FpgaImageFormat
    observations: tuple[FpgaObservationSignal, ...]
    build_flow: FpgaBuildFlow
    non_goals: tuple[str, ...]

    def memory_by_name(self, name: str) -> FpgaMemoryRegion:
        normalized = name.lower()
        for memory in self.memories:
            if memory.name.lower() == normalized:
                return memory
        raise KeyError(f"unknown FPGA first-test memory {name!r}")

    def observation_by_name(self, name: str) -> FpgaObservationSignal:
        normalized = name.lower()
        for observation in self.observations:
            if observation.name.lower() == normalized:
                return observation
        raise KeyError(f"unknown FPGA first-test observation {name!r}")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "story": self.story,
            "fpga_top_module": self.fpga_top_module,
            "core_top_module": self.core_top_module,
            "target_board": self.target_board.as_dict(),
            "clock_reset": self.clock_reset.as_dict(),
            "memories": [memory.as_dict() for memory in self.memories],
            "image_format": self.image_format.as_dict(),
            "observations": [observation.as_dict() for observation in self.observations],
            "build_flow": self.build_flow.as_dict(),
            "non_goals": list(self.non_goals),
        }


FPGA_FIRST_TEST_PROFILE = FpgaFirstTestProfile(
    name=PROFILE_NAME,
    story=FPGA_FIRST_TEST_STORY,
    fpga_top_module=FPGA_TOP_MODULE,
    core_top_module=CORE_TOP_MODULE,
    target_board=FpgaBoardTarget(
        name=TARGET_BOARD_NAME,
        vendor=TARGET_BOARD_VENDOR,
        variant=TARGET_BOARD_VARIANT,
        fpga_device=TARGET_FPGA_DEVICE,
        ide_package=TARGET_IDE_PACKAGE,
        device_version=TARGET_DEVICE_VERSION,
        programming_interfaces=(
            "onboard_usb_jtag_uart",
            "gowin_programmer_gao_bridge_5a_or_arora_v_flash",
            "openfpgaloader_tangmega138k_pending_device_scan",
        ),
        observation_interfaces=(
            "pmod_led_x8",
            "usb_uart",
            "gowin_gao_ila",
        ),
        constraint_source=TARGET_CONSTRAINT_SOURCE,
        source_urls=(
            "https://wiki.sipeed.com/hardware/en/tang/tang-mega-138k/mega-138k",
            "https://wiki.sipeed.com/hardware/zh/tang/tang-mega-138k/mega-138k",
            "https://github.com/sipeed/TangMega-138K-example",
            "https://trabucayre.github.io/openFPGALoader/compatibility/board.html",
        ),
        open_items=(
            "confirm actual SOM device/package by board marking or JTAG scan",
            "extract board_clk_i, board_reset_n_i, and LED pins from Sipeed constraints",
            "verify LED polarity and IO standard before first programming",
        ),
    ),
    clock_reset=FpgaClockResetProfile(
        board_class="single-board FPGA with one free-running clock, pushbutton reset, BRAM, and at least one LED",
        input_clock="board_clk_i",
        input_reset="board_reset_n_i",
        reset_polarity="active_low_async_input_sync_release",
        reset_sync_stages=2,
        maximum_core_clock_hz=25_000_000,
    ),
    memories=(
        FpgaMemoryRegion(
            name="instruction_rom",
            kind="rom",
            address_space="instruction",
            base_cell=platform.RESET_VECTOR,
            size_cells=0x400,
            port="imem",
            initialization="build/fpga/first_test_rom.mem",
            tag_policy="no_tags",
        ),
        FpgaMemoryRegion(
            name="data_ram",
            kind="ram",
            address_space="data",
            base_cell=platform.RAM_BASE,
            size_cells=0x1000,
            port="dmem",
            initialization="zero_or_first_test_data_image",
            tag_policy="payload_only",
        ),
        FpgaMemoryRegion(
            name="tag_ram",
            kind="tag_sidecar",
            address_space="tag",
            base_cell=platform.RAM_BASE,
            size_cells=0x1000,
            port="tagmem",
            initialization="reset_clear",
            tag_policy="integer_store_clears_matching_slot",
        ),
    ),
    image_format=FpgaImageFormat(
        name=IMAGE_FORMAT_NAME,
        cell_bits=cells.CELL_BITS,
        rom_init_file="build/fpga/first_test_rom.mem",
        data_init_file="build/fpga/first_test_data.mem",
        line_format="one 6-hex-digit 24-bit cell per line in ascending cell address order",
        source_fixture="tiny_rom_reset_smoke",
    ),
    observations=(
        FpgaObservationSignal(
            name="pass_led",
            width=1,
            source="first_test_status.pass",
            required=True,
            purpose="Visible successful completion without a debugger.",
        ),
        FpgaObservationSignal(
            name="fail_led",
            width=1,
            source="first_test_status.fail",
            required=True,
            purpose="Visible trapped or failed completion without a debugger.",
        ),
        FpgaObservationSignal(
            name="heartbeat_led",
            width=1,
            source="debug_retire_sequence",
            required=True,
            purpose="Shows that clock/reset and retire observation are alive.",
        ),
        FpgaObservationSignal(
            name="fault_code_probe",
            width=16,
            source="retire_packet.fault.cause",
            required=False,
            purpose="UART or ILA fault triage signal.",
        ),
        FpgaObservationSignal(
            name="retire_count_probe",
            width=32,
            source="debug_retire_sequence",
            required=False,
            purpose="UART or ILA retire progress signal.",
        ),
    ),
    build_flow=FpgaBuildFlow(
        name="first_test_synth_place_route",
        toolchain_profile="vendor FPGA flow selected by board overlay",
        required_steps=(
            "lint_or_elaborate_cpu_v01_fpga_top",
            "synthesize_bram_smoke_design",
            "place_and_route_with_board_constraints",
            "report_timing_and_utilization",
        ),
        required_constraints=(
            "board_clk_i_clock_period",
            "board_reset_n_i_synchronizer_path",
            "status_led_pin_assignments",
            "no_unconstrained_paths",
        ),
        failure_conditions=(
            "missing_cpu_v01_core_or_memory_black_box",
            "unconstrained_clock_or_reset",
            "negative_timing_slack_at_first_test_clock",
            "missing_pass_fail_observation_pin",
        ),
    ),
    non_goals=(
        "external_dram_controller",
        "general_mmio_peripheral_set",
        "bootloader_or_program_download_protocol",
        "multicore_startup",
        "fabric_links_or_switches",
        "cache_hierarchy_performance_tuning",
        "long_running_firmware_or_kernel_workload",
    ),
)


def fpga_first_test_profile_json(*, indent: int = 2) -> str:
    return json.dumps(
        FPGA_FIRST_TEST_PROFILE.as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_test_profile(profile: FpgaFirstTestProfile = FPGA_FIRST_TEST_PROFILE) -> str:
    lines = [
        "# FPGA First-Test Profile",
        "",
        f"Profile: `{profile.name}`",
        f"Story: `{profile.story}`",
        f"FPGA top: `{profile.fpga_top_module}`",
        f"Core under test: `{profile.core_top_module}`",
        "",
        "## Target Board",
        "",
        f"- Board: `{profile.target_board.name}`.",
        f"- Vendor: `{profile.target_board.vendor}`.",
        f"- Variant: {profile.target_board.variant}.",
        f"- FPGA device: `{profile.target_board.fpga_device}`.",
        f"- IDE package: `{profile.target_board.ide_package}`.",
        f"- Device version: {profile.target_board.device_version}.",
        f"- Constraint source: {profile.target_board.constraint_source}.",
        "- Programming interfaces: "
        + ", ".join(f"`{interface}`" for interface in profile.target_board.programming_interfaces)
        + ".",
        "- Observation interfaces: "
        + ", ".join(f"`{interface}`" for interface in profile.target_board.observation_interfaces)
        + ".",
        "- Open items: "
        + ", ".join(profile.target_board.open_items)
        + ".",
        "",
        "## Clock And Reset",
        "",
        f"- Board class: {profile.clock_reset.board_class}.",
        f"- Clock input: `{profile.clock_reset.input_clock}`.",
        f"- Reset input: `{profile.clock_reset.input_reset}` ({profile.clock_reset.reset_polarity}).",
        f"- Reset synchronizer stages: {profile.clock_reset.reset_sync_stages}.",
        f"- First-test core clock limit: {profile.clock_reset.maximum_core_clock_hz} Hz.",
        "",
        "## Memories",
        "",
        "| Name | Kind | Address space | Base cell | Size cells | Port | Initialization | Tag policy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for memory in profile.memories:
        lines.append(
            f"| `{memory.name}` | `{memory.kind}` | `{memory.address_space}` | "
            f"`0x{memory.base_cell:012X}` | `{memory.size_cells}` | `{memory.port}` | "
            f"`{memory.initialization}` | `{memory.tag_policy}` |"
        )

    lines.extend(
        [
            "",
            "## Image Format",
            "",
            f"- Format: `{profile.image_format.name}`.",
            f"- Cell width: {profile.image_format.cell_bits} bits.",
            f"- ROM image: `{profile.image_format.rom_init_file}`.",
            f"- Data image: `{profile.image_format.data_init_file}`.",
            f"- Line format: {profile.image_format.line_format}.",
            f"- Source fixture: `{profile.image_format.source_fixture}`.",
            "",
            "## Observation Signals",
            "",
            "| Signal | Width | Required | Source | Purpose |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for observation in profile.observations:
        lines.append(
            f"| `{observation.name}` | {observation.width} | "
            f"{'yes' if observation.required else 'no'} | "
            f"`{observation.source}` | {observation.purpose} |"
        )

    lines.extend(
        [
            "",
            "## Build Flow",
            "",
            f"- Flow: `{profile.build_flow.name}`.",
            f"- Toolchain profile: {profile.build_flow.toolchain_profile}.",
            "- Required steps: "
            + ", ".join(f"`{step}`" for step in profile.build_flow.required_steps)
            + ".",
            "- Required constraints: "
            + ", ".join(f"`{constraint}`" for constraint in profile.build_flow.required_constraints)
            + ".",
            "- Failure conditions: "
            + ", ".join(
                f"`{condition}`"
                for condition in profile.build_flow.failure_conditions
            )
            + ".",
            "",
            "## Non-Goals",
            "",
        ]
    )
    lines.extend(f"- `{non_goal}`" for non_goal in profile.non_goals)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_test_profile(
    profile: FpgaFirstTestProfile = FPGA_FIRST_TEST_PROFILE,
    root: Path | None = None,
) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    if profile.name != PROFILE_NAME:
        issues.append(f"profile name must be {PROFILE_NAME}")
    if profile.story != FPGA_FIRST_TEST_STORY:
        issues.append(f"profile story must be {FPGA_FIRST_TEST_STORY}")
    if profile.fpga_top_module != FPGA_TOP_MODULE:
        issues.append(f"FPGA top module must be {FPGA_TOP_MODULE}")
    if profile.core_top_module != CORE_TOP_MODULE:
        issues.append(f"core top module must be {CORE_TOP_MODULE}")

    target_board = profile.target_board
    if target_board.name != TARGET_BOARD_NAME:
        issues.append(f"target board must be {TARGET_BOARD_NAME}")
    if target_board.vendor != TARGET_BOARD_VENDOR:
        issues.append(f"target board vendor must be {TARGET_BOARD_VENDOR}")
    if target_board.fpga_device != TARGET_FPGA_DEVICE:
        issues.append(f"target FPGA device must be {TARGET_FPGA_DEVICE}")
    if target_board.ide_package != TARGET_IDE_PACKAGE:
        issues.append(f"target IDE package must be {TARGET_IDE_PACKAGE}")
    if "JTAG" not in target_board.device_version:
        issues.append("target device version must require board or JTAG verification")
    if "All PIN Constraints" not in target_board.constraint_source:
        issues.append("target board must name the Sipeed pin-constraint source")
    if "onboard_usb_jtag_uart" not in target_board.programming_interfaces:
        issues.append("target board must include onboard USB JTAG/UART programming")
    if "pmod_led_x8" not in target_board.observation_interfaces:
        issues.append("target board must include the PMOD LED observation path")
    if not target_board.source_urls:
        issues.append("target board must record source URLs")
    if not target_board.open_items:
        issues.append("target board must record open verification items")

    clock_reset = profile.clock_reset
    if not clock_reset.board_class:
        issues.append("board class must be documented")
    if clock_reset.input_clock != "board_clk_i":
        issues.append("input clock must be board_clk_i")
    if clock_reset.input_reset != "board_reset_n_i":
        issues.append("input reset must be board_reset_n_i")
    if "sync_release" not in clock_reset.reset_polarity:
        issues.append("reset polarity must require synchronized release")
    if clock_reset.reset_sync_stages < 2:
        issues.append("reset synchronizer must have at least two stages")
    if clock_reset.maximum_core_clock_hz <= 0:
        issues.append("maximum first-test core clock must be positive")

    memories = {memory.name: memory for memory in profile.memories}
    for required in ("instruction_rom", "data_ram", "tag_ram"):
        if required not in memories:
            issues.append(f"missing FPGA first-test memory {required}")

    instruction_rom = memories.get("instruction_rom")
    if instruction_rom is not None:
        if instruction_rom.kind != "rom" or instruction_rom.port != "imem":
            issues.append("instruction_rom must be a ROM on the instruction-memory port")
        if not instruction_rom.contains(platform.RESET_VECTOR):
            issues.append("instruction_rom must contain the reset vector")
        if not instruction_rom.initialization.endswith(".mem"):
            issues.append("instruction_rom must name a memory initialization file")

    data_ram = memories.get("data_ram")
    tag_ram = memories.get("tag_ram")
    if data_ram is not None and tag_ram is not None:
        if data_ram.port != "dmem":
            issues.append("data_ram must use the data-memory port")
        if tag_ram.port != "tagmem":
            issues.append("tag_ram must use the tag-memory port")
        if data_ram.base_cell != tag_ram.base_cell or data_ram.size_cells != tag_ram.size_cells:
            issues.append("tag_ram must sidecar the data_ram address range")
        if "integer_store_clears" not in tag_ram.tag_policy:
            issues.append("tag_ram must document integer-store tag clearing")

    for index, memory in enumerate(profile.memories):
        if memory.size_cells <= 0:
            issues.append(f"{memory.name} must have a positive size")
        for other in profile.memories[index + 1 :]:
            if memory.overlaps(other):
                issues.append(f"{memory.name} overlaps {other.name} in {memory.address_space}")

    image_format = profile.image_format
    if image_format.name != IMAGE_FORMAT_NAME:
        issues.append(f"image format must be {IMAGE_FORMAT_NAME}")
    if image_format.cell_bits != cells.CELL_BITS:
        issues.append(f"image format must use {cells.CELL_BITS}-bit cells")
    if (
        instruction_rom is not None
        and image_format.rom_init_file != instruction_rom.initialization
    ):
        issues.append("ROM image file must match instruction_rom initialization")
    if "6-hex-digit" not in image_format.line_format:
        issues.append("image format must specify one 6-hex-digit cell per line")

    observations = {observation.name: observation for observation in profile.observations}
    for required in ("pass_led", "fail_led", "heartbeat_led"):
        observation = observations.get(required)
        if observation is None:
            issues.append(f"missing required observation {required}")
        elif not observation.required:
            issues.append(f"{required} must be required")
    if observations.get("pass_led") and observations["pass_led"].width != 1:
        issues.append("pass_led must be one bit wide")
    if observations.get("fail_led") and observations["fail_led"].width != 1:
        issues.append("fail_led must be one bit wide")

    build_flow = profile.build_flow
    for step in (
        "lint_or_elaborate_cpu_v01_fpga_top",
        "synthesize_bram_smoke_design",
        "place_and_route_with_board_constraints",
        "report_timing_and_utilization",
    ):
        if step not in build_flow.required_steps:
            issues.append(f"build flow missing step {step}")
    for constraint in (
        "board_clk_i_clock_period",
        "board_reset_n_i_synchronizer_path",
        "no_unconstrained_paths",
    ):
        if constraint not in build_flow.required_constraints:
            issues.append(f"build flow missing constraint {constraint}")
    for failure in (
        "missing_cpu_v01_core_or_memory_black_box",
        "unconstrained_clock_or_reset",
        "negative_timing_slack_at_first_test_clock",
    ):
        if failure not in build_flow.failure_conditions:
            issues.append(f"build flow missing failure condition {failure}")

    for non_goal in (
        "external_dram_controller",
        "general_mmio_peripheral_set",
        "multicore_startup",
        "fabric_links_or_switches",
        "long_running_firmware_or_kernel_workload",
    ):
        if non_goal not in profile.non_goals:
            issues.append(f"profile missing non-goal {non_goal}")

    doc = _read_if_exists(root / FPGA_FIRST_TEST_DOC)
    for token in (
        "Story: I23-S01",
        "python tools\\fpga_first_test_profile.py --check",
        PROFILE_NAME,
        FPGA_TOP_MODULE,
        CORE_TOP_MODULE,
        IMAGE_FORMAT_NAME,
        TARGET_BOARD_NAME,
        TARGET_FPGA_DEVICE,
        TARGET_IDE_PACKAGE,
        "All PIN Constraints",
        "board_clk_i",
        "board_reset_n_i",
        "instruction_rom",
        "data_ram",
        "tag_ram",
        "pass_led",
        "fail_led",
        "external DRAM",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_TEST_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

"""Board-safe FPGA program loader profile and executable model.

Owner stories:
- I26-S04: add a board-safe UART or JTAG-assisted program load path.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import (
    cells,
    fpga_bram_images,
    fpga_debug_status,
    fpga_first_test,
    fpga_program_manifest,
    fpga_uart_mmio,
    fpga_uart_status,
    platform,
)


JsonValue = Any

FPGA_PROGRAM_LOADER_STORY = "I26-S04"
FPGA_PROGRAM_LOADER_DOC = Path("docs/implementation/fpga-program-loader.md")
FPGA_PROGRAM_LOADER_TOOL = "python tools\\fpga_program_loader.py --check"
FPGA_PROGRAM_LOADER_EVIDENCE = Path("docs/implementation/evidence/i26_s04_program_loader.txt")

TRANSPORT_UART_MMIO = "uart_mmio"
TRANSPORT_JTAG_ASSISTED = "jtag_assisted"
TARGET_MEMORY = "data_ram"
TAG_MEMORY = "tag_ram"
MAX_CHUNK_CELLS = 16
LOADER_BUILD_ID = 0x2604_C0DE

LOAD_STATUS_OK = 0x0000
LOAD_STATUS_BAD_PROGRAM = 0x2601
LOAD_STATUS_BAD_HASH = 0x2602
LOAD_STATUS_BAD_TARGET = 0x2603
LOAD_STATUS_BOUNDS = 0x2604
LOAD_STATUS_TAG_POLICY = 0x2605
LOAD_STATUS_OVERRUN = 0x2606
LOAD_STATUS_MALFORMED = 0x2607

STATUS_NAMES = {
    LOAD_STATUS_OK: "OK",
    LOAD_STATUS_BAD_PROGRAM: "BAD_PROGRAM",
    LOAD_STATUS_BAD_HASH: "BAD_HASH",
    LOAD_STATUS_BAD_TARGET: "BAD_TARGET",
    LOAD_STATUS_BOUNDS: "BOUNDS",
    LOAD_STATUS_TAG_POLICY: "TAG_POLICY",
    LOAD_STATUS_OVERRUN: "OVERRUN",
    LOAD_STATUS_MALFORMED: "MALFORMED",
}


@dataclass(frozen=True)
class FpgaProgramLoadPlan:
    program_id: str
    source_case_id: str
    manifest_image_sha256: str
    ram_image_sha256: str
    tag_image_sha256: str
    target_memory: str
    base_cell: int
    cell_count: int
    max_chunk_cells: int
    source_sections: tuple[str, ...]

    @property
    def end_cell(self) -> int:
        return self.base_cell + self.cell_count

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "tag_image_sha256": self.tag_image_sha256,
            "target_memory": self.target_memory,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "cell_count": self.cell_count,
            "max_chunk_cells": self.max_chunk_cells,
            "source_sections": list(self.source_sections),
        }


@dataclass(frozen=True)
class FpgaProgramLoaderProfile:
    story: str
    bram_image_gate: str
    uart_mmio_gate: str
    status_stream_gate: str
    debug_packet_gate: str
    evidence_path: Path
    transports: tuple[str, ...]
    target_memory: str
    target_base_cell: int
    target_size_cells: int
    max_chunk_cells: int
    tag_policy: str
    command_sequence: tuple[str, ...]
    status_codes: dict[str, int]
    plans: tuple[FpgaProgramLoadPlan, ...]
    blockers: tuple[str, ...]

    def plan_by_program_id(self, program_id: str) -> FpgaProgramLoadPlan:
        for plan in self.plans:
            if plan.program_id == program_id:
                return plan
        raise KeyError(program_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "bram_image_gate": self.bram_image_gate,
            "uart_mmio_gate": self.uart_mmio_gate,
            "status_stream_gate": self.status_stream_gate,
            "debug_packet_gate": self.debug_packet_gate,
            "evidence_path": self.evidence_path.as_posix(),
            "transports": list(self.transports),
            "target_memory": self.target_memory,
            "target_base_cell": self.target_base_cell,
            "target_end_cell": self.target_base_cell + self.target_size_cells,
            "target_size_cells": self.target_size_cells,
            "max_chunk_cells": self.max_chunk_cells,
            "tag_policy": self.tag_policy,
            "command_sequence": list(self.command_sequence),
            "status_codes": dict(self.status_codes),
            "plans": [plan.as_dict() for plan in self.plans],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ProgramLoadRequest:
    program_id: str
    target_memory: str
    base_cell: int
    payload_cells: tuple[int, ...]
    tag_bits: tuple[int, ...]
    manifest_image_sha256: str
    ram_image_sha256: str
    transport: str = TRANSPORT_UART_MMIO
    max_observed_chunk_cells: int = MAX_CHUNK_CELLS

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_cell", cells.require_cell_address(self.base_cell))
        object.__setattr__(
            self,
            "payload_cells",
            tuple(cells.require_cell_value(value) for value in self.payload_cells),
        )
        object.__setattr__(self, "tag_bits", tuple(int(value) for value in self.tag_bits))
        if type(self.max_observed_chunk_cells) is not int:
            raise TypeError("max_observed_chunk_cells must be an int")

    @property
    def end_cell(self) -> int:
        return self.base_cell + len(self.payload_cells)

    @property
    def payload_sha256(self) -> str:
        return _sha256(_hex24_lines(self.payload_cells))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "target_memory": self.target_memory,
            "base_cell": self.base_cell,
            "end_cell": self.end_cell,
            "cell_count": len(self.payload_cells),
            "tag_count": len(self.tag_bits),
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "payload_sha256": self.payload_sha256,
            "transport": self.transport,
            "max_observed_chunk_cells": self.max_observed_chunk_cells,
        }


@dataclass(frozen=True)
class ProgramLoadStatusReport:
    status_code: int
    status_name: str
    success: bool
    uart_message: str
    uart_bytes: tuple[int, ...]
    debug_packet: fpga_debug_status.DebugStatusPacket

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status_code": self.status_code,
            "status_name": self.status_name,
            "success": self.success,
            "uart_message": self.uart_message,
            "uart_bytes": list(self.uart_bytes),
            "debug_packet": self.debug_packet.as_dict(),
        }


@dataclass(frozen=True)
class ProgramLoadResult:
    status: str
    program_id: str
    installed_cells: int
    first_loaded_cell: int | None
    last_loaded_cell: int | None
    issues: tuple[str, ...]
    report: ProgramLoadStatusReport

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "program_id": self.program_id,
            "installed_cells": self.installed_cells,
            "first_loaded_cell": self.first_loaded_cell,
            "last_loaded_cell": self.last_loaded_cell,
            "issues": list(self.issues),
            "report": self.report.as_dict(),
        }


@dataclass
class FpgaProgramLoaderState:
    data_ram: list[int]
    tag_ram: list[int]
    loaded_program_id: str = ""
    sequence: int = 0
    last_report: ProgramLoadStatusReport | None = None
    accepted_transports: tuple[str, ...] = (TRANSPORT_UART_MMIO, TRANSPORT_JTAG_ASSISTED)

    def install(self, request: ProgramLoadRequest) -> ProgramLoadResult:
        self.sequence += 1
        status_code, issues = audit_program_load_request(request)
        if issues:
            report = make_status_report(status_code, request.program_id, 0, self.sequence)
            self.last_report = report
            return ProgramLoadResult(
                status="failed",
                program_id=request.program_id,
                installed_cells=0,
                first_loaded_cell=None,
                last_loaded_cell=None,
                issues=issues,
                report=report,
            )

        target = _target_region()
        offset = request.base_cell - target.base_cell
        self.data_ram[offset : offset + len(request.payload_cells)] = list(request.payload_cells)
        self.tag_ram[offset : offset + len(request.tag_bits)] = [0 for _ in request.tag_bits]
        self.loaded_program_id = request.program_id

        report = make_status_report(
            LOAD_STATUS_OK,
            request.program_id,
            len(request.payload_cells),
            self.sequence,
        )
        self.last_report = report
        return ProgramLoadResult(
            status="passed",
            program_id=request.program_id,
            installed_cells=len(request.payload_cells),
            first_loaded_cell=request.base_cell,
            last_loaded_cell=request.end_cell - 1 if request.payload_cells else None,
            issues=(),
            report=report,
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "loaded_program_id": self.loaded_program_id,
            "sequence": self.sequence,
            "data_ram_cells": len(self.data_ram),
            "tag_ram_cells": len(self.tag_ram),
            "tag_bits_set": sum(1 for value in self.tag_ram if value != 0),
            "last_report": None if self.last_report is None else self.last_report.as_dict(),
        }


def fpga_program_loader_profile() -> FpgaProgramLoaderProfile:
    target = _target_region()
    return FpgaProgramLoaderProfile(
        story=FPGA_PROGRAM_LOADER_STORY,
        bram_image_gate=fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        uart_mmio_gate=fpga_uart_mmio.FPGA_UART_MMIO_TOOL,
        status_stream_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        debug_packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        evidence_path=FPGA_PROGRAM_LOADER_EVIDENCE,
        transports=(TRANSPORT_UART_MMIO, TRANSPORT_JTAG_ASSISTED),
        target_memory=TARGET_MEMORY,
        target_base_cell=target.base_cell,
        target_size_cells=target.size_cells,
        max_chunk_cells=MAX_CHUNK_CELLS,
        tag_policy="loader writes only untyped data cells and clears matching tag sidecar bits",
        command_sequence=(
            "LOAD_BEGIN program_id manifest_image_sha256 ram_image_sha256 target_memory base_cell cell_count",
            "LOAD_CHUNK chunk_index payload_cells up_to_16 tag_bits_all_zero",
            "LOAD_COMMIT payload_sha256",
            "LOAD_ABORT status_code",
        ),
        status_codes={name: code for code, name in STATUS_NAMES.items()},
        plans=tuple(_plan_for_entry(entry) for entry in fpga_program_manifest.fpga_program_manifest_entries()),
        blockers=(
            "I30-S04 must integrate this loader handoff into the SoC top before firmware can use it on board",
            "I32-S01 owns the later interactive monitor command naming and host protocol expansion",
            "JTAG-assisted transport remains a bounded profile until a board scan and bridge command path are captured",
        ),
    )


def fpga_program_loader_state() -> FpgaProgramLoaderState:
    target = _target_region()
    tag_target = _tag_region()
    return FpgaProgramLoaderState(
        data_ram=[0 for _ in range(target.size_cells)],
        tag_ram=[0 for _ in range(tag_target.size_cells)],
    )


def program_load_request_for_program(program_id: str) -> ProgramLoadRequest:
    entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(program_id)
    data_image = _image_by_memory(entry, TARGET_MEMORY)
    return ProgramLoadRequest(
        program_id=entry.program_id,
        target_memory=TARGET_MEMORY,
        base_cell=_target_region().base_cell,
        payload_cells=entry.materialized_cells(TARGET_MEMORY),
        tag_bits=entry.materialized_cells(TAG_MEMORY),
        manifest_image_sha256=entry.image_sha256,
        ram_image_sha256=data_image.image_sha256,
        transport=TRANSPORT_UART_MMIO,
        max_observed_chunk_cells=MAX_CHUNK_CELLS,
    )


def install_manifest_program(
    program_id: str,
    state: FpgaProgramLoaderState | None = None,
) -> ProgramLoadResult:
    if state is None:
        state = fpga_program_loader_state()
    return state.install(program_load_request_for_program(program_id))


def audit_program_load_request(request: ProgramLoadRequest) -> tuple[int, tuple[str, ...]]:
    profile = fpga_program_loader_profile()
    issues: list[str] = []
    status_code = LOAD_STATUS_OK

    try:
        plan = profile.plan_by_program_id(request.program_id)
    except KeyError:
        plan = None
        issues.append("program_id is not in the I26-S01 manifest")
        status_code = LOAD_STATUS_BAD_PROGRAM

    if request.transport not in profile.transports:
        issues.append("transport must be uart_mmio or jtag_assisted")
        status_code = _first_error(status_code, LOAD_STATUS_MALFORMED)
    if request.target_memory != TARGET_MEMORY:
        issues.append("loader may only write the bounded data_ram window")
        status_code = _first_error(status_code, LOAD_STATUS_BAD_TARGET)
    if not request.payload_cells:
        issues.append("payload_cells must not be empty")
        status_code = _first_error(status_code, LOAD_STATUS_MALFORMED)
    if len(request.payload_cells) != len(request.tag_bits):
        issues.append("tag_bits must have one entry per payload cell")
        status_code = _first_error(status_code, LOAD_STATUS_TAG_POLICY)
    if request.max_observed_chunk_cells <= 0 or request.max_observed_chunk_cells > profile.max_chunk_cells:
        issues.append("observed command chunk exceeds the bounded LOAD_CHUNK size")
        status_code = _first_error(status_code, LOAD_STATUS_OVERRUN)

    target = _target_region()
    if request.base_cell < target.base_cell or request.end_cell > target.end_cell:
        issues.append("payload range is outside the bounded data_ram window")
        status_code = _first_error(status_code, LOAD_STATUS_BOUNDS)
    if len(request.payload_cells) > profile.target_size_cells:
        issues.append("payload exceeds the maximum RAM image size")
        status_code = _first_error(status_code, LOAD_STATUS_BOUNDS)
    if any(bit != 0 for bit in request.tag_bits):
        issues.append("loader rejects tag-bearing images and only clears tag sidecar bits")
        status_code = _first_error(status_code, LOAD_STATUS_TAG_POLICY)

    if plan is not None:
        if request.manifest_image_sha256 != plan.manifest_image_sha256:
            issues.append("manifest_image_sha256 does not match the selected program")
            status_code = _first_error(status_code, LOAD_STATUS_BAD_HASH)
        if request.ram_image_sha256 != plan.ram_image_sha256:
            issues.append("ram_image_sha256 does not match the selected program")
            status_code = _first_error(status_code, LOAD_STATUS_BAD_HASH)
        if request.payload_sha256 != plan.ram_image_sha256:
            issues.append("payload cells do not hash to the selected RAM image")
            status_code = _first_error(status_code, LOAD_STATUS_BAD_HASH)
        if request.base_cell != plan.base_cell or len(request.payload_cells) != plan.cell_count:
            issues.append("payload must cover the selected bounded RAM image")
            status_code = _first_error(status_code, LOAD_STATUS_BOUNDS)

    return status_code, tuple(issues)


def make_status_report(
    status_code: int,
    program_id: str,
    installed_cells: int,
    sequence: int,
) -> ProgramLoadStatusReport:
    success = status_code == LOAD_STATUS_OK
    status_name = STATUS_NAMES.get(status_code, "UNKNOWN")
    if success:
        uart_message = f"I26-S04 LOAD OK program={program_id} cells={installed_cells}\n"
        flags = fpga_debug_status.debug_status_flag_mask("reset_observed", "core_idle", "heartbeat")
        pass_fail_state = 1
        packet_fault_code = 0
    else:
        uart_message = f"I26-S04 LOAD ERR status={status_name} program={program_id}\n"
        flags = fpga_debug_status.debug_status_flag_mask(
            "reset_observed",
            "fault_valid",
            "heartbeat",
        )
        pass_fail_state = 4
        packet_fault_code = status_code

    packet = fpga_debug_status.DebugStatusPacket(
        flags=flags,
        slot=0,
        pass_fail_state=pass_fail_state,
        pc_cell=platform.RESET_VECTOR,
        retire_count=0,
        fault_code=packet_fault_code,
        trap_cause=0,
        build_id=LOADER_BUILD_ID,
        sequence=sequence,
    )
    issues = fpga_debug_status.validate_debug_status_packet(packet)
    if issues:
        raise ValueError("; ".join(issues))

    return ProgramLoadStatusReport(
        status_code=status_code,
        status_name=status_name,
        success=success,
        uart_message=uart_message,
        uart_bytes=stream_status_uart_bytes(uart_message),
        debug_packet=packet,
    )


def stream_status_uart_bytes(message: str) -> tuple[int, ...]:
    """Queue and drain UART status text without overflowing the I27-S02 TX FIFO."""
    state = fpga_uart_mmio.fpga_uart_mmio_state()
    emitted: list[int] = []
    for byte in message.encode("ascii"):
        while state.status() & fpga_uart_mmio.STATUS_TX_READY == 0:
            drained = state.host_transmit_byte()
            if drained is not None:
                emitted.append(drained)
        state.write_register(fpga_uart_mmio.UART_TXDATA, byte)
        drained = state.host_transmit_byte()
        if drained is not None:
            emitted.append(drained)
    while True:
        drained = state.host_transmit_byte()
        if drained is None:
            break
        emitted.append(drained)
    return tuple(emitted)


def rejection_fixture_results() -> tuple[ProgramLoadResult, ...]:
    good = program_load_request_for_program("relocation.branch_call_data_fpga")
    fixtures = (
        replace(good, program_id="missing.program"),
        replace(good, manifest_image_sha256="0" * 64),
        replace(good, target_memory="instruction_rom"),
        replace(good, base_cell=_target_region().end_cell - 1),
        replace(good, tag_bits=(1,) + good.tag_bits[1:]),
        replace(good, max_observed_chunk_cells=MAX_CHUNK_CELLS + 1),
    )
    return tuple(fpga_program_loader_state().install(request) for request in fixtures)


def fpga_program_loader_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_program_loader_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_program_loader() -> str:
    profile = fpga_program_loader_profile()
    lines = [
        "# FPGA Program Loader",
        "",
        f"Story: `{profile.story}`",
        f"BRAM image gate: `{profile.bram_image_gate}`",
        f"UART MMIO gate: `{profile.uart_mmio_gate}`",
        f"Status stream gate: `{profile.status_stream_gate}`",
        f"Debug packet gate: `{profile.debug_packet_gate}`",
        "",
        "## Load Plans",
        "",
    ]
    for plan in profile.plans:
        lines.extend(
            (
                f"### `{plan.program_id}`",
                "",
                f"- Target: `{plan.target_memory}` `0x{plan.base_cell:08X}`..`0x{plan.end_cell:08X}`.",
                f"- Cells: `{plan.cell_count}`.",
                f"- RAM hash: `{plan.ram_image_sha256}`.",
                f"- Tag hash: `{plan.tag_image_sha256}`.",
                "",
            )
        )
    return "\n".join(lines)


def validate_fpga_program_loader(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_program_loader_profile()
    issues: list[str] = []

    if profile.story != FPGA_PROGRAM_LOADER_STORY:
        issues.append("FPGA program loader story mismatch")
    if profile.bram_image_gate != fpga_bram_images.FPGA_BRAM_IMAGES_TOOL:
        issues.append("FPGA program loader must validate against I26-S02")
    if profile.uart_mmio_gate != fpga_uart_mmio.FPGA_UART_MMIO_TOOL:
        issues.append("FPGA program loader must validate against I27-S02")
    if profile.status_stream_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("FPGA program loader must name the I25-S02 status stream gate")
    if profile.debug_packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("FPGA program loader must name the I25-S01 debug packet gate")
    if set(profile.transports) != {TRANSPORT_UART_MMIO, TRANSPORT_JTAG_ASSISTED}:
        issues.append("loader transports must include UART MMIO and JTAG-assisted modes")
    if profile.target_memory != TARGET_MEMORY:
        issues.append("loader target must be data_ram")
    if profile.max_chunk_cells != MAX_CHUNK_CELLS:
        issues.append("loader max chunk size must be 16 cells")
    if "clears matching tag" not in profile.tag_policy:
        issues.append("loader tag policy must clear matching tag sidecar bits")

    issues.extend(fpga_bram_images.validate_fpga_bram_images(root))
    issues.extend(fpga_uart_mmio.validate_fpga_uart_mmio(root))

    target = _target_region()
    if target.kind != "ram":
        issues.append("loader target region must be RAM")
    if profile.target_base_cell != target.base_cell or profile.target_size_cells != target.size_cells:
        issues.append("loader target range must match the FPGA data RAM")

    program_ids = [plan.program_id for plan in profile.plans]
    if len(program_ids) != len(set(program_ids)):
        issues.append("loader plan program IDs are not unique")
    for plan in profile.plans:
        if plan.target_memory != TARGET_MEMORY:
            issues.append(f"{plan.program_id}: loader plan target must be data_ram")
        if plan.base_cell != target.base_cell or plan.cell_count != target.size_cells:
            issues.append(f"{plan.program_id}: loader plan must cover the bounded data RAM image")
        if plan.max_chunk_cells != MAX_CHUNK_CELLS:
            issues.append(f"{plan.program_id}: loader plan chunk size mismatch")
        for hash_name, digest in (
            ("manifest_image_sha256", plan.manifest_image_sha256),
            ("ram_image_sha256", plan.ram_image_sha256),
            ("tag_image_sha256", plan.tag_image_sha256),
        ):
            if len(digest) != 64:
                issues.append(f"{plan.program_id}: {hash_name} must be a SHA-256 digest")

    state = fpga_program_loader_state()
    result = state.install(program_load_request_for_program("relocation.branch_call_data_fpga"))
    if not result.passed:
        issues.append("known-good relocation RAM image must install successfully")
    if result.report.uart_bytes != tuple(result.report.uart_message.encode("ascii")):
        issues.append("UART status report bytes must match the ASCII status message")
    if any(state.tag_ram):
        issues.append("successful loader install must preserve clear tag policy")
    data_section = _relocation_data_section()
    if data_section is not None:
        offset = data_section.base_cell - target.base_cell
        observed = tuple(state.data_ram[offset : offset + data_section.cell_count])
        if observed != data_section.payload_cells:
            issues.append("relocation data payload was not installed at the expected RAM offset")

    for rejection in rejection_fixture_results():
        if rejection.passed:
            issues.append("malformed loader fixture unexpectedly passed")
        if rejection.report.success:
            issues.append("malformed loader fixture reported success")
        if rejection.report.debug_packet.pass_fail_state != 4:
            issues.append("malformed loader fixture must report blocked debug status")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(result.as_dict(), sort_keys=True)
        json.dumps(state.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA program loader objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_PROGRAM_LOADER_DOC)
    for token in (
        "Story: I26-S04",
        FPGA_PROGRAM_LOADER_TOOL,
        "python tools\\fpga_bram_images.py --check",
        "python tools\\fpga_uart_mmio.py --check",
        "python tools\\fpga_uart_status_streamer.py --check",
        "python tools\\fpga_debug_status_packet.py --check",
        "bounded RAM image",
        "data_ram",
        "tag_ram",
        "LOAD_BEGIN",
        "LOAD_CHUNK",
        "LOAD_COMMIT",
        "BAD_HASH",
        "TAG_POLICY",
        "python tools\\fpga_program_loader.py --run",
        "python tools\\fpga_program_loader.py --rejections",
        "I30-S04",
        "I32-S01",
    ):
        if token not in doc:
            issues.append(f"{FPGA_PROGRAM_LOADER_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _plan_for_entry(entry: fpga_program_manifest.FpgaProgramManifestEntry) -> FpgaProgramLoadPlan:
    data_image = _image_by_memory(entry, TARGET_MEMORY)
    tag_image = _image_by_memory(entry, TAG_MEMORY)
    target = _target_region()
    return FpgaProgramLoadPlan(
        program_id=entry.program_id,
        source_case_id=entry.source_case_id,
        manifest_image_sha256=entry.image_sha256,
        ram_image_sha256=data_image.image_sha256,
        tag_image_sha256=tag_image.image_sha256,
        target_memory=TARGET_MEMORY,
        base_cell=target.base_cell,
        cell_count=target.size_cells,
        max_chunk_cells=MAX_CHUNK_CELLS,
        source_sections=tuple(section.source_section for section in entry.sections if section.target_memory == TARGET_MEMORY),
    )


def _image_by_memory(
    entry: fpga_program_manifest.FpgaProgramManifestEntry,
    memory_name: str,
) -> fpga_program_manifest.FpgaProgramMemoryImage:
    for image in entry.memory_images():
        if image.memory_name == memory_name:
            return image
    raise KeyError(memory_name)


def _target_region() -> fpga_first_test.FpgaMemoryRegion:
    return fpga_first_test.FPGA_FIRST_TEST_PROFILE.memory_by_name(TARGET_MEMORY)


def _tag_region() -> fpga_first_test.FpgaMemoryRegion:
    return fpga_first_test.FPGA_FIRST_TEST_PROFILE.memory_by_name(TAG_MEMORY)


def _relocation_data_section() -> fpga_program_manifest.FpgaProgramSectionBinding | None:
    entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(
        "relocation.branch_call_data_fpga"
    )
    for section in entry.sections:
        if section.target_memory == TARGET_MEMORY:
            return section
    return None


def _first_error(current: int, candidate: int) -> int:
    if current == LOAD_STATUS_OK:
        return candidate
    return current


def _hex24_lines(values: tuple[int, ...]) -> str:
    return "".join(f"{value:06x}\n" for value in values)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

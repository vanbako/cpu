"""ROM monitor and trap-shell firmware fixtures for FPGA sessions.

Owner stories:
- I32-S02: add ROM monitor and trap-shell firmware fixtures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import (
    capabilities as caps,
    csrs,
    firmware,
    fpga_debug_status,
    fpga_first_test,
    fpga_monitor_profile,
    fpga_program_loader,
    fpga_uart_status,
    kernel,
    platform,
    state as cpu_state,
)
from .instructions import CapCause, ExceptionCause, FaultCapIndex
from .memory import TaggedMemory


JsonValue = Any

FPGA_MONITOR_FIRMWARE_STORY = "I32-S02"
FPGA_MONITOR_FIRMWARE_DOC = Path("docs/implementation/fpga-monitor-firmware-fixtures.md")
FPGA_MONITOR_FIRMWARE_TOOL = "python tools\\fpga_monitor_firmware.py --check"
FPGA_MONITOR_FIRMWARE_STATUS = "rom_monitor_trap_shell_fixtures"
KERNEL_HANDLER_GATE = "python -m unittest tests.conformance.test_i14_s02_kernel_handlers"
MONITOR_FIRMWARE_BUILD_ID = 0x3202_C0DE
MAX_MONITOR_COMMANDS = 8

STATE_ROM_MONITOR_IDLE = "rom_monitor_idle"
STATE_SAFE_IDLE = "safe_idle"
STATE_TRAP_SHELL_IDLE = "trap_shell_idle"
STATE_PROGRAM_RUNNING = "program_running"

FIXTURE_LOAD_RESUME_OK = "rom_monitor.load_resume_ok"
FIXTURE_REJECT_BAD_HASH = "rom_monitor.reject_bad_hash"
FIXTURE_TRAP_SHELL_BAD_COMMAND = "trap_shell.bad_command_idle"


@dataclass(frozen=True)
class MonitorFirmwareCommandRequest:
    command_name: str
    reason: str = ""
    program_id: str = ""
    entry_cell: int = platform.RESET_VECTOR
    target_memory: str = fpga_program_loader.TARGET_MEMORY
    base_cell: int = platform.RAM_BASE
    cell_count: int = 0
    manifest_image_sha256: str = ""
    ram_image_sha256: str = ""
    tag_bits_all_zero: bool = True
    payload_cells: tuple[int, ...] = ()
    transport: str = fpga_monitor_profile.TRANSPORT_UART

    def __post_init__(self) -> None:
        if not self.command_name:
            raise ValueError("command_name must not be empty")
        object.__setattr__(self, "entry_cell", int(self.entry_cell))
        object.__setattr__(self, "base_cell", int(self.base_cell))
        object.__setattr__(self, "cell_count", int(self.cell_count))
        object.__setattr__(self, "payload_cells", tuple(int(value) for value in self.payload_cells))
        if type(self.tag_bits_all_zero) is not bool:
            raise TypeError("tag_bits_all_zero must be a bool")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "command_name": self.command_name,
            "reason": self.reason,
            "program_id": self.program_id,
            "entry_cell": self.entry_cell,
            "target_memory": self.target_memory,
            "base_cell": self.base_cell,
            "cell_count": self.cell_count,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "tag_bits_all_zero": self.tag_bits_all_zero,
            "payload_cells": list(self.payload_cells),
            "transport": self.transport,
        }


@dataclass(frozen=True)
class MonitorFirmwareFixtureSpec:
    fixture_id: str
    description: str
    commands: tuple[MonitorFirmwareCommandRequest, ...]
    expected_final_state: str
    expected_status_sequence: tuple[str, ...]
    expected_loader_status_sequence: tuple[str, ...] = ()
    expected_loaded_program_id: str = ""
    expect_no_memory_mutation: bool = False
    expect_trap_shell: bool = False
    expect_trap_restore: bool = False

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "fixture_id": self.fixture_id,
            "description": self.description,
            "commands": [command.as_dict() for command in self.commands],
            "expected_final_state": self.expected_final_state,
            "expected_status_sequence": list(self.expected_status_sequence),
            "expected_loader_status_sequence": list(self.expected_loader_status_sequence),
            "expected_loaded_program_id": self.expected_loaded_program_id,
            "expect_no_memory_mutation": self.expect_no_memory_mutation,
            "expect_trap_shell": self.expect_trap_shell,
            "expect_trap_restore": self.expect_trap_restore,
        }


@dataclass(frozen=True)
class MonitorFirmwareSnapshot:
    monitor_state: str
    halted: bool
    trap_shell_active: bool
    pc_cell: int
    loaded_program_id: str
    data_ram_checksum: int
    tag_bits_set: int
    sequence: int

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "monitor_state": self.monitor_state,
            "halted": self.halted,
            "trap_shell_active": self.trap_shell_active,
            "pc_cell": self.pc_cell,
            "loaded_program_id": self.loaded_program_id,
            "data_ram_checksum": self.data_ram_checksum,
            "tag_bits_set": self.tag_bits_set,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class MonitorFirmwareStatusReport:
    command_name: str
    status_code: int
    status_name: str
    loader_status_code: int | None
    loader_status_name: str
    uart_message: str
    uart_bytes: tuple[int, ...]
    debug_packet: fpga_debug_status.DebugStatusPacket

    @property
    def success(self) -> bool:
        return self.status_code == fpga_monitor_profile.STATUS_OK

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "command_name": self.command_name,
            "status_code": self.status_code,
            "status_name": self.status_name,
            "loader_status_code": self.loader_status_code,
            "loader_status_name": self.loader_status_name,
            "uart_message": self.uart_message,
            "uart_bytes": list(self.uart_bytes),
            "debug_packet": self.debug_packet.as_dict(),
        }


@dataclass(frozen=True)
class MonitorFirmwareCommandResult:
    request: MonitorFirmwareCommandRequest
    state_before: MonitorFirmwareSnapshot
    state_after: MonitorFirmwareSnapshot
    installed_cells: int
    issues: tuple[str, ...]
    report: MonitorFirmwareStatusReport

    @property
    def passed(self) -> bool:
        return self.report.success

    @property
    def status_name(self) -> str:
        return self.report.status_name

    @property
    def loader_status_name(self) -> str:
        return self.report.loader_status_name

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "request": self.request.as_dict(),
            "state_before": self.state_before.as_dict(),
            "state_after": self.state_after.as_dict(),
            "installed_cells": self.installed_cells,
            "issues": list(self.issues),
            "report": self.report.as_dict(),
        }


@dataclass(frozen=True)
class TrapShellRestoreReport:
    entered_trap_shell: bool
    restored_epcc_cell: int
    restored_epcc_slot: int
    final_pcc_cell: int
    final_pcc_slot: int
    final_sr: int
    iret_normal_retire: bool

    @property
    def passed(self) -> bool:
        return (
            self.entered_trap_shell
            and self.iret_normal_retire
            and self.final_pcc_cell == self.restored_epcc_cell
            and self.final_pcc_slot == self.restored_epcc_slot
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "entered_trap_shell": self.entered_trap_shell,
            "restored_epcc_cell": self.restored_epcc_cell,
            "restored_epcc_slot": self.restored_epcc_slot,
            "final_pcc_cell": self.final_pcc_cell,
            "final_pcc_slot": self.final_pcc_slot,
            "final_sr": self.final_sr,
            "iret_normal_retire": self.iret_normal_retire,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class MonitorFirmwareFixtureRun:
    fixture_id: str
    description: str
    expected_final_state: str
    command_results: tuple[MonitorFirmwareCommandResult, ...]
    initial_snapshot: MonitorFirmwareSnapshot
    final_snapshot: MonitorFirmwareSnapshot
    trap_shell_restore: TrapShellRestoreReport | None
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "fixture_id": self.fixture_id,
            "description": self.description,
            "expected_final_state": self.expected_final_state,
            "passed": self.passed,
            "command_results": [result.as_dict() for result in self.command_results],
            "initial_snapshot": self.initial_snapshot.as_dict(),
            "final_snapshot": self.final_snapshot.as_dict(),
            "trap_shell_restore": None
            if self.trap_shell_restore is None
            else self.trap_shell_restore.as_dict(),
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class MonitorFirmwareProfile:
    story: str
    status: str
    board: str
    command_profile_gate: str
    program_loader_gate: str
    uart_status_gate: str
    debug_packet_gate: str
    kernel_handler_gate: str
    max_commands: int
    rom_entry_cell: int
    trap_shell_entry_cell: int
    allowed_entry_memory: str
    fixtures: tuple[MonitorFirmwareFixtureSpec, ...]
    non_corruption_rules: tuple[str, ...]
    handoffs: tuple[str, ...]

    def fixture_by_id(self, fixture_id: str) -> MonitorFirmwareFixtureSpec:
        for fixture in self.fixtures:
            if fixture.fixture_id == fixture_id:
                return fixture
        raise KeyError(fixture_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "command_profile_gate": self.command_profile_gate,
            "program_loader_gate": self.program_loader_gate,
            "uart_status_gate": self.uart_status_gate,
            "debug_packet_gate": self.debug_packet_gate,
            "kernel_handler_gate": self.kernel_handler_gate,
            "max_commands": self.max_commands,
            "rom_entry_cell": self.rom_entry_cell,
            "trap_shell_entry_cell": self.trap_shell_entry_cell,
            "allowed_entry_memory": self.allowed_entry_memory,
            "fixtures": [fixture.as_dict() for fixture in self.fixtures],
            "non_corruption_rules": list(self.non_corruption_rules),
            "handoffs": list(self.handoffs),
        }


@dataclass
class MonitorFirmwareState:
    monitor_state: str = STATE_ROM_MONITOR_IDLE
    halted: bool = True
    trap_shell_active: bool = False
    pc_cell: int = platform.RESET_VECTOR
    sequence: int = 0
    loader_state: fpga_program_loader.FpgaProgramLoaderState = field(
        default_factory=fpga_program_loader.fpga_program_loader_state
    )
    last_report: MonitorFirmwareStatusReport | None = None

    def snapshot(self) -> MonitorFirmwareSnapshot:
        return MonitorFirmwareSnapshot(
            monitor_state=self.monitor_state,
            halted=self.halted,
            trap_shell_active=self.trap_shell_active,
            pc_cell=self.pc_cell,
            loaded_program_id=self.loader_state.loaded_program_id,
            data_ram_checksum=_data_ram_checksum(self.loader_state.data_ram),
            tag_bits_set=sum(1 for value in self.loader_state.tag_ram if value != 0),
            sequence=self.sequence,
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "monitor_state": self.monitor_state,
            "halted": self.halted,
            "trap_shell_active": self.trap_shell_active,
            "pc_cell": self.pc_cell,
            "sequence": self.sequence,
            "loader_state": self.loader_state.as_dict(),
            "last_report": None if self.last_report is None else self.last_report.as_dict(),
        }


def fpga_monitor_firmware_profile() -> MonitorFirmwareProfile:
    instruction_rom = fpga_first_test.FPGA_FIRST_TEST_PROFILE.memory_by_name("instruction_rom")
    return MonitorFirmwareProfile(
        story=FPGA_MONITOR_FIRMWARE_STORY,
        status=FPGA_MONITOR_FIRMWARE_STATUS,
        board=fpga_first_test.TARGET_BOARD_NAME,
        command_profile_gate=fpga_monitor_profile.FPGA_MONITOR_PROFILE_TOOL,
        program_loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        uart_status_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        debug_packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        kernel_handler_gate=KERNEL_HANDLER_GATE,
        max_commands=MAX_MONITOR_COMMANDS,
        rom_entry_cell=platform.RESET_VECTOR,
        trap_shell_entry_cell=firmware.ROM_TRAP_VECTOR_CELL,
        allowed_entry_memory=instruction_rom.name,
        fixtures=_fixture_specs(),
        non_corruption_rules=(
            "frame parse, unsupported command, bad metadata, and tag-policy failures report status before memory writes",
            "accepted LOAD_IMAGE traffic delegates all data_ram writes and tag_ram clearing to I26-S04",
            "trap-shell resume restores the I14-S02 software trap frame and returns through IRET",
            "safe idle and trap-shell idle keep the monitor halted until an explicit valid RESUME",
        ),
        handoffs=(
            "I32-S03 consumes LOAD_IMAGE and RESUME fixtures for multi-program sessions",
            "I32-S04 extends READ_STATUS and READ_MEMORY into replayable debug snapshots",
            "RTL or ROM assembly can replace this Python fixture only after preserving the same command and safety outcomes",
        ),
    )


def fpga_monitor_firmware_state() -> MonitorFirmwareState:
    return MonitorFirmwareState()


def run_monitor_firmware_stream(
    commands: tuple[MonitorFirmwareCommandRequest, ...],
    state: MonitorFirmwareState | None = None,
) -> tuple[MonitorFirmwareState, tuple[MonitorFirmwareCommandResult, ...]]:
    if state is None:
        state = fpga_monitor_firmware_state()
    if len(commands) > MAX_MONITOR_COMMANDS:
        result = _bounded_stream_failure(state, len(commands))
        return state, (result,)
    results = tuple(execute_monitor_command(state, command) for command in commands)
    return state, results


def execute_monitor_command(
    state: MonitorFirmwareState,
    request: MonitorFirmwareCommandRequest,
) -> MonitorFirmwareCommandResult:
    if not isinstance(state, MonitorFirmwareState):
        raise TypeError("state must be a MonitorFirmwareState")
    if not isinstance(request, MonitorFirmwareCommandRequest):
        raise TypeError("request must be a MonitorFirmwareCommandRequest")

    before = state.snapshot()
    state.sequence += 1
    audit_cell_count = _audit_cell_count(request)
    audit = fpga_monitor_profile.audit_monitor_command(
        request.command_name,
        transport=request.transport,
        target_memory=request.target_memory,
        cell_count=audit_cell_count,
        halted=state.halted,
        tag_bits_all_zero=request.tag_bits_all_zero,
    )
    status_code = audit.status_code
    issues = list(audit.issues)
    loader_result: fpga_program_loader.ProgramLoadResult | None = None
    loader_status_code: int | None = None
    installed_cells = 0

    if status_code == fpga_monitor_profile.STATUS_OK:
        command = request.command_name
        if command == fpga_monitor_profile.COMMAND_HELLO:
            pass
        elif command == fpga_monitor_profile.COMMAND_HALT:
            state.halted = True
            state.trap_shell_active = request.reason == "trap"
            state.monitor_state = (
                STATE_TRAP_SHELL_IDLE if state.trap_shell_active else STATE_ROM_MONITOR_IDLE
            )
            state.pc_cell = (
                firmware.ROM_TRAP_VECTOR_CELL if state.trap_shell_active else platform.RESET_VECTOR
            )
        elif command == fpga_monitor_profile.COMMAND_LOAD_IMAGE:
            try:
                loader_request = _loader_request_from_monitor_command(request)
            except (KeyError, ValueError) as exc:
                status_code = fpga_monitor_profile.STATUS_LOADER_ERROR
                issues.append(str(exc))
            else:
                loader_result = state.loader_state.install(loader_request)
                loader_status_code = loader_result.report.status_code
                installed_cells = loader_result.installed_cells
                if not loader_result.passed:
                    status_code = fpga_monitor_profile.STATUS_LOADER_ERROR
                    issues.extend(loader_result.issues)
                    _enter_safe_idle_after_error(state)
        elif command == fpga_monitor_profile.COMMAND_READ_STATUS:
            pass
        elif command == fpga_monitor_profile.COMMAND_READ_MEMORY:
            pass
        elif command == fpga_monitor_profile.COMMAND_WRITE_MEMORY:
            write_status, write_issues = _apply_write_memory(state, request)
            if write_status != fpga_monitor_profile.STATUS_OK:
                status_code = write_status
                issues.extend(write_issues)
                _enter_safe_idle_after_error(state)
        elif command == fpga_monitor_profile.COMMAND_RESUME:
            if not _entry_cell_allowed(request.entry_cell):
                status_code = fpga_monitor_profile.STATUS_BAD_ADDRESS
                issues.append("RESUME entry_cell is outside instruction_rom")
                _enter_safe_idle_after_error(state)
            else:
                state.halted = False
                state.trap_shell_active = False
                state.monitor_state = STATE_PROGRAM_RUNNING
                state.pc_cell = request.entry_cell

    if status_code != fpga_monitor_profile.STATUS_OK:
        _enter_safe_idle_after_error(state)
    report = _make_monitor_status_report(
        request.command_name,
        status_code,
        state,
        loader_status_code=loader_status_code,
    )
    state.last_report = report
    after = state.snapshot()
    return MonitorFirmwareCommandResult(
        request=request,
        state_before=before,
        state_after=after,
        installed_cells=installed_cells,
        issues=tuple(issues),
        report=report,
    )


def run_monitor_firmware_fixture(fixture_id: str) -> MonitorFirmwareFixtureRun:
    spec = fpga_monitor_firmware_profile().fixture_by_id(fixture_id)
    state = fpga_monitor_firmware_state()
    initial = state.snapshot()
    state, results = run_monitor_firmware_stream(spec.commands, state)
    trap_shell_restore = run_trap_shell_restore_fixture() if spec.expect_trap_restore else None
    final = state.snapshot()
    issues = _fixture_issues(spec, results, initial, final, trap_shell_restore)
    return MonitorFirmwareFixtureRun(
        fixture_id=spec.fixture_id,
        description=spec.description,
        expected_final_state=spec.expected_final_state,
        command_results=results,
        initial_snapshot=initial,
        final_snapshot=final,
        trap_shell_restore=trap_shell_restore,
        issues=tuple(issues),
    )


def run_monitor_firmware_fixtures() -> tuple[MonitorFirmwareFixtureRun, ...]:
    return tuple(
        run_monitor_firmware_fixture(spec.fixture_id)
        for spec in fpga_monitor_firmware_profile().fixtures
    )


def run_trap_shell_restore_fixture() -> TrapShellRestoreReport:
    core = _prepared_kernel_core()
    restored = cpu_state.SlottedCapability.from_capability(
        _executable_capability(0x4010),
        cpu_state.SLOT_1,
    )
    frame = kernel.SoftwareTrapFrame(
        epcc=restored,
        sr=(1 << csrs.SR_PRIV_BIT) | (1 << csrs.SR_EXL_BIT),
        cause=int(ExceptionCause.SYSCALL_TRAP),
        tval=0,
        capcause=CapCause.NONE,
        fault_cap_idx=FaultCapIndex.NONE,
    )
    kernel.restore_frame_for_iret(core, frame)
    result = kernel.execute_iret(core)
    return TrapShellRestoreReport(
        entered_trap_shell=True,
        restored_epcc_cell=restored.payload.cursor,
        restored_epcc_slot=restored.slot,
        final_pcc_cell=core.pcc.payload.cursor,
        final_pcc_slot=core.pcc.slot,
        final_sr=core.read_csr(csrs.CSR_SR),
        iret_normal_retire=result.is_normal_retire,
    )


def fpga_monitor_firmware_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_monitor_firmware_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_monitor_firmware_run_json(*, indent: int = 2) -> str:
    return json.dumps(
        [run.as_dict() for run in run_monitor_firmware_fixtures()],
        indent=indent,
        sort_keys=True,
    )


def render_fpga_monitor_firmware(profile: MonitorFirmwareProfile | None = None) -> str:
    if profile is None:
        profile = fpga_monitor_firmware_profile()
    lines = [
        "# FPGA Monitor Firmware Fixtures",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Board: `{profile.board}`",
        f"Command profile gate: `{profile.command_profile_gate}`",
        f"Program loader gate: `{profile.program_loader_gate}`",
        f"UART status gate: `{profile.uart_status_gate}`",
        f"Debug packet gate: `{profile.debug_packet_gate}`",
        f"Kernel handler gate: `{profile.kernel_handler_gate}`",
        f"Max commands: `{profile.max_commands}`",
        "",
        "## Fixtures",
        "",
        "| Fixture | Final state | Status sequence | Loader statuses |",
        "| --- | --- | --- | --- |",
    ]
    for fixture in profile.fixtures:
        lines.append(
            f"| `{fixture.fixture_id}` | `{fixture.expected_final_state}` | "
            f"{', '.join(f'`{status}`' for status in fixture.expected_status_sequence)} | "
            f"{', '.join(f'`{status}`' for status in fixture.expected_loader_status_sequence) or '-'} |"
        )
    lines.extend(["", "## Non-Corruption Rules", ""])
    lines.extend(f"- {rule}." for rule in profile.non_corruption_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_monitor_firmware(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_firmware_profile()
    issues: list[str] = []

    if profile.story != FPGA_MONITOR_FIRMWARE_STORY:
        issues.append(f"monitor firmware story must be {FPGA_MONITOR_FIRMWARE_STORY}")
    if profile.status != FPGA_MONITOR_FIRMWARE_STATUS:
        issues.append("monitor firmware status must remain fixture-defined")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("monitor firmware board must match first-test target")
    if profile.command_profile_gate != fpga_monitor_profile.FPGA_MONITOR_PROFILE_TOOL:
        issues.append("monitor firmware must depend on I32-S01 command profile")
    if profile.program_loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("monitor firmware must depend on I26-S04 loader")
    if profile.uart_status_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("monitor firmware must depend on I25-S02 UART status")
    if profile.debug_packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("monitor firmware must depend on I25-S01 debug packet")
    if profile.kernel_handler_gate != KERNEL_HANDLER_GATE:
        issues.append("monitor firmware must name the I14-S02 kernel handler gate")
    if profile.max_commands != MAX_MONITOR_COMMANDS:
        issues.append("monitor firmware command stream bound changed unexpectedly")
    if profile.rom_entry_cell != platform.RESET_VECTOR:
        issues.append("monitor firmware ROM entry must be the reset vector")
    if profile.trap_shell_entry_cell != firmware.ROM_TRAP_VECTOR_CELL:
        issues.append("monitor firmware trap shell must use the ROM trap vector cell")

    issues.extend(fpga_monitor_profile.validate_fpga_monitor_profile(root))
    issues.extend(fpga_uart_status.validate_fpga_uart_status(root))

    fixture_ids = {fixture.fixture_id for fixture in profile.fixtures}
    for fixture_id in (
        FIXTURE_LOAD_RESUME_OK,
        FIXTURE_REJECT_BAD_HASH,
        FIXTURE_TRAP_SHELL_BAD_COMMAND,
    ):
        if fixture_id not in fixture_ids:
            issues.append(f"missing monitor firmware fixture {fixture_id}")
    for fixture in profile.fixtures:
        if len(fixture.commands) > profile.max_commands:
            issues.append(f"{fixture.fixture_id}: command stream exceeds monitor bound")
        if not fixture.expected_status_sequence:
            issues.append(f"{fixture.fixture_id}: expected status sequence is empty")

    for run in run_monitor_firmware_fixtures():
        if not run.passed:
            issues.append(f"{run.fixture_id}: {'; '.join(run.issues)}")
        for result in run.command_results:
            packet_issues = fpga_debug_status.validate_debug_status_packet(
                result.report.debug_packet
            )
            if packet_issues:
                issues.append(
                    f"{run.fixture_id}:{result.request.command_name}: invalid debug packet "
                    + "; ".join(packet_issues)
                )

    state, bounded = run_monitor_firmware_stream(
        tuple(
            MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HELLO)
            for _ in range(MAX_MONITOR_COMMANDS + 1)
        )
    )
    if state.sequence != 1:
        issues.append("overlong command stream should report one bounded failure")
    if bounded[0].status_name != "BAD_LENGTH":
        issues.append("overlong command stream must fail BAD_LENGTH")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps([run.as_dict() for run in run_monitor_firmware_fixtures()], sort_keys=True)
    except TypeError as exc:
        issues.append(f"monitor firmware objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_MONITOR_FIRMWARE_DOC)
    for token in (
        "Story: I32-S02",
        FPGA_MONITOR_FIRMWARE_TOOL,
        fpga_monitor_profile.FPGA_MONITOR_PROFILE_TOOL,
        fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        fpga_uart_status.FPGA_UART_STATUS_TOOL,
        fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        KERNEL_HANDLER_GATE,
        "rom_monitor.load_resume_ok",
        "rom_monitor.reject_bad_hash",
        "trap_shell.bad_command_idle",
        "LOAD_IMAGE",
        "BAD_HASH",
        "LOADER_ERROR",
        "safe_idle",
        "trap_shell_idle",
        "tag_ram",
        "I32-S03",
        "I32-S04",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MONITOR_FIRMWARE_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _fixture_specs() -> tuple[MonitorFirmwareFixtureSpec, ...]:
    good_request = fpga_program_loader.program_load_request_for_program(
        "relocation.branch_call_data_fpga"
    )
    return (
        MonitorFirmwareFixtureSpec(
            fixture_id=FIXTURE_LOAD_RESUME_OK,
            description="HELLO, halt, load a manifest-backed image, read status, and resume from ROM",
            commands=(
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HELLO),
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HALT, reason="host"),
                MonitorFirmwareCommandRequest(
                    fpga_monitor_profile.COMMAND_LOAD_IMAGE,
                    program_id=good_request.program_id,
                    cell_count=fpga_program_loader.MAX_CHUNK_CELLS,
                ),
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_READ_STATUS),
                MonitorFirmwareCommandRequest(
                    fpga_monitor_profile.COMMAND_RESUME,
                    entry_cell=platform.RESET_VECTOR,
                ),
            ),
            expected_final_state=STATE_PROGRAM_RUNNING,
            expected_status_sequence=("OK", "OK", "OK", "OK", "OK"),
            expected_loader_status_sequence=("OK",),
            expected_loaded_program_id=good_request.program_id,
        ),
        MonitorFirmwareFixtureSpec(
            fixture_id=FIXTURE_REJECT_BAD_HASH,
            description="reject stale image metadata before mutating RAM or tag sidecar state",
            commands=(
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HELLO),
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HALT, reason="host"),
                MonitorFirmwareCommandRequest(
                    fpga_monitor_profile.COMMAND_LOAD_IMAGE,
                    program_id=good_request.program_id,
                    cell_count=fpga_program_loader.MAX_CHUNK_CELLS,
                    manifest_image_sha256="0" * 64,
                ),
            ),
            expected_final_state=STATE_SAFE_IDLE,
            expected_status_sequence=("OK", "OK", "LOADER_ERROR"),
            expected_loader_status_sequence=("BAD_HASH",),
            expect_no_memory_mutation=True,
        ),
        MonitorFirmwareFixtureSpec(
            fixture_id=FIXTURE_TRAP_SHELL_BAD_COMMAND,
            description="enter trap shell, reject an unsupported command, and remain idle for inspection",
            commands=(
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_HALT, reason="trap"),
                MonitorFirmwareCommandRequest("NOPE"),
                MonitorFirmwareCommandRequest(fpga_monitor_profile.COMMAND_READ_STATUS),
            ),
            expected_final_state=STATE_TRAP_SHELL_IDLE,
            expected_status_sequence=("OK", "BAD_COMMAND", "OK"),
            expect_no_memory_mutation=True,
            expect_trap_shell=True,
            expect_trap_restore=True,
        ),
    )


def _fixture_issues(
    spec: MonitorFirmwareFixtureSpec,
    results: tuple[MonitorFirmwareCommandResult, ...],
    initial: MonitorFirmwareSnapshot,
    final: MonitorFirmwareSnapshot,
    trap_shell_restore: TrapShellRestoreReport | None,
) -> list[str]:
    issues: list[str] = []
    status_sequence = tuple(result.status_name for result in results)
    loader_status_sequence = tuple(
        result.loader_status_name for result in results if result.loader_status_name
    )
    if status_sequence != spec.expected_status_sequence:
        issues.append(
            f"status sequence {status_sequence!r} did not match {spec.expected_status_sequence!r}"
        )
    if loader_status_sequence != spec.expected_loader_status_sequence:
        issues.append(
            "loader status sequence "
            f"{loader_status_sequence!r} did not match {spec.expected_loader_status_sequence!r}"
        )
    if final.monitor_state != spec.expected_final_state:
        issues.append(
            f"final state {final.monitor_state!r} did not match {spec.expected_final_state!r}"
        )
    if spec.expected_loaded_program_id and final.loaded_program_id != spec.expected_loaded_program_id:
        issues.append("expected loaded program was not installed")
    if spec.expect_no_memory_mutation:
        if final.loaded_program_id != initial.loaded_program_id:
            issues.append("failed fixture changed loaded_program_id")
        if final.data_ram_checksum != initial.data_ram_checksum:
            issues.append("failed fixture mutated data_ram")
        if final.tag_bits_set != initial.tag_bits_set:
            issues.append("failed fixture mutated tag_ram")
    if spec.expect_trap_shell and not final.trap_shell_active:
        issues.append("trap shell fixture did not remain trap-shell active")
    if spec.expect_trap_restore:
        if trap_shell_restore is None:
            issues.append("trap shell restore report is missing")
        elif not trap_shell_restore.passed:
            issues.append("trap shell restore did not return through IRET")
    if final.tag_bits_set != 0:
        issues.append("monitor fixture left tag_ram bits set")
    return issues


def _bounded_stream_failure(
    state: MonitorFirmwareState,
    command_count: int,
) -> MonitorFirmwareCommandResult:
    before = state.snapshot()
    state.sequence += 1
    state.monitor_state = STATE_SAFE_IDLE
    state.halted = True
    state.trap_shell_active = False
    report = _make_monitor_status_report(
        "COMMAND_STREAM",
        fpga_monitor_profile.STATUS_BAD_LENGTH,
        state,
    )
    state.last_report = report
    after = state.snapshot()
    return MonitorFirmwareCommandResult(
        request=MonitorFirmwareCommandRequest("COMMAND_STREAM", cell_count=command_count),
        state_before=before,
        state_after=after,
        installed_cells=0,
        issues=("command stream exceeds bounded ROM monitor limit",),
        report=report,
    )


def _loader_request_from_monitor_command(
    request: MonitorFirmwareCommandRequest,
) -> fpga_program_loader.ProgramLoadRequest:
    if not request.program_id:
        raise ValueError("LOAD_IMAGE requires program_id")
    loader_request = fpga_program_loader.program_load_request_for_program(request.program_id)
    manifest_hash = request.manifest_image_sha256 or loader_request.manifest_image_sha256
    ram_hash = request.ram_image_sha256 or loader_request.ram_image_sha256
    tag_bits = loader_request.tag_bits
    if not request.tag_bits_all_zero and tag_bits:
        tag_bits = (1,) + tag_bits[1:]
    return replace(
        loader_request,
        target_memory=request.target_memory,
        manifest_image_sha256=manifest_hash,
        ram_image_sha256=ram_hash,
        transport=fpga_program_loader.TRANSPORT_UART_MMIO,
        max_observed_chunk_cells=request.cell_count or fpga_program_loader.MAX_CHUNK_CELLS,
        tag_bits=tag_bits,
    )


def _apply_write_memory(
    state: MonitorFirmwareState,
    request: MonitorFirmwareCommandRequest,
) -> tuple[int, tuple[str, ...]]:
    loader_profile = fpga_program_loader.fpga_program_loader_profile()
    if request.target_memory != fpga_program_loader.TARGET_MEMORY:
        return fpga_monitor_profile.STATUS_WRITE_PROTECTED, ("WRITE_MEMORY target is protected",)
    if request.base_cell < loader_profile.target_base_cell:
        return fpga_monitor_profile.STATUS_BAD_ADDRESS, ("WRITE_MEMORY base_cell is before data_ram",)
    if request.base_cell + request.cell_count > loader_profile.target_base_cell + loader_profile.target_size_cells:
        return fpga_monitor_profile.STATUS_BAD_ADDRESS, ("WRITE_MEMORY range exceeds data_ram",)
    payload = request.payload_cells or tuple(0 for _ in range(request.cell_count))
    if len(payload) != request.cell_count:
        return fpga_monitor_profile.STATUS_BAD_LENGTH, ("payload_cells length must match cell_count",)
    offset = request.base_cell - loader_profile.target_base_cell
    state.loader_state.data_ram[offset : offset + request.cell_count] = list(payload)
    state.loader_state.tag_ram[offset : offset + request.cell_count] = [
        0 for _ in range(request.cell_count)
    ]
    return fpga_monitor_profile.STATUS_OK, ()


def _make_monitor_status_report(
    command_name: str,
    status_code: int,
    state: MonitorFirmwareState,
    *,
    loader_status_code: int | None = None,
) -> MonitorFirmwareStatusReport:
    status_name = fpga_monitor_profile.STATUS_NAMES[status_code]
    loader_status_name = ""
    if loader_status_code is not None:
        loader_status_name = fpga_program_loader.STATUS_NAMES.get(loader_status_code, "UNKNOWN")
    if status_code == fpga_monitor_profile.STATUS_OK:
        uart_message = (
            f"I32-S02 MONITOR OK command={command_name} state={state.monitor_state}\n"
        )
    else:
        loader_suffix = f" loader={loader_status_name}" if loader_status_name else ""
        uart_message = (
            f"I32-S02 MONITOR ERR command={command_name} status={status_name}"
            f"{loader_suffix} state={state.monitor_state}\n"
        )
    packet = _monitor_debug_packet(status_code, state)
    return MonitorFirmwareStatusReport(
        command_name=command_name,
        status_code=status_code,
        status_name=status_name,
        loader_status_code=loader_status_code,
        loader_status_name=loader_status_name,
        uart_message=uart_message,
        uart_bytes=fpga_program_loader.stream_status_uart_bytes(uart_message),
        debug_packet=packet,
    )


def _monitor_debug_packet(
    status_code: int,
    state: MonitorFirmwareState,
) -> fpga_debug_status.DebugStatusPacket:
    flag_names = ["reset_observed", "heartbeat"]
    if state.halted:
        flag_names.append("core_idle")
    if status_code != fpga_monitor_profile.STATUS_OK:
        flag_names.append("fault_valid")
    flags = fpga_debug_status.debug_status_flag_mask(*flag_names)
    if status_code != fpga_monitor_profile.STATUS_OK:
        pass_fail_state = 4
    elif state.monitor_state == STATE_PROGRAM_RUNNING:
        pass_fail_state = 1
    else:
        pass_fail_state = 0
    packet = fpga_debug_status.DebugStatusPacket(
        flags=flags,
        slot=0,
        pass_fail_state=pass_fail_state,
        pc_cell=state.pc_cell,
        retire_count=0,
        fault_code=0 if status_code == fpga_monitor_profile.STATUS_OK else status_code,
        trap_cause=0,
        build_id=MONITOR_FIRMWARE_BUILD_ID,
        sequence=state.sequence,
    )
    issues = fpga_debug_status.validate_debug_status_packet(packet)
    if issues:
        raise ValueError("; ".join(issues))
    return packet


def _enter_safe_idle_after_error(state: MonitorFirmwareState) -> None:
    state.halted = True
    if state.trap_shell_active or state.monitor_state == STATE_TRAP_SHELL_IDLE:
        state.trap_shell_active = True
        state.monitor_state = STATE_TRAP_SHELL_IDLE
        state.pc_cell = firmware.ROM_TRAP_VECTOR_CELL
    else:
        state.trap_shell_active = False
        state.monitor_state = STATE_SAFE_IDLE
        state.pc_cell = platform.RESET_VECTOR


def _audit_cell_count(request: MonitorFirmwareCommandRequest) -> int:
    if request.command_name in {
        fpga_monitor_profile.COMMAND_LOAD_IMAGE,
        fpga_monitor_profile.COMMAND_READ_MEMORY,
        fpga_monitor_profile.COMMAND_WRITE_MEMORY,
    }:
        return request.cell_count or fpga_program_loader.MAX_CHUNK_CELLS
    return request.cell_count


def _entry_cell_allowed(entry_cell: int) -> bool:
    instruction_rom = fpga_first_test.FPGA_FIRST_TEST_PROFILE.memory_by_name("instruction_rom")
    return instruction_rom.contains(entry_cell)


def _data_ram_checksum(data_ram: list[int]) -> int:
    checksum = 0
    for index, value in enumerate(data_ram):
        checksum = (checksum + ((index + 1) * (value & 0xFFFFFF))) & 0xFFFFFFFF
    return checksum


def _prepared_kernel_core() -> cpu_state.CoreState:
    memory = TaggedMemory()
    core = platform.cold_reset_cores()[0]
    firmware.initialize_boot_core_for_kernel_handoff(core, memory)
    core.install_pcc(
        cpu_state.SlottedCapability.from_capability(
            _executable_capability(0x4000),
            cpu_state.SLOT_0,
        )
    )
    sr = core.read_csr(csrs.CSR_SR)
    sr &= ~(1 << csrs.SR_PRIV_BIT)
    sr &= ~(1 << csrs.SR_EXL_BIT)
    sr &= ~(1 << csrs.SR_IE_BIT)
    core.write_csr_raw(csrs.CSR_SR, sr)
    return core


def _executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x4000, 0x5000),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

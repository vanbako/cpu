"""Interactive FPGA monitor command and transport profile.

Owner stories:
- I32-S01: define the interactive monitor command and transport profile.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_program_loader, fpga_soc_loader_handoff, platform


JsonValue = Any

FPGA_MONITOR_PROFILE_STORY = "I32-S01"
FPGA_MONITOR_PROFILE_DOC = Path("docs/implementation/fpga-monitor-command-profile.md")
FPGA_MONITOR_PROFILE_TOOL = "python tools\\fpga_monitor_profile.py --check"
FPGA_MONITOR_PROFILE_STATUS = "monitor_command_profile_defined"

TRANSPORT_UART = "uart_mmio_monitor"
TRANSPORT_JTAG = "jtag_assisted_monitor"

COMMAND_HELLO = "HELLO"
COMMAND_HALT = "HALT"
COMMAND_RESUME = "RESUME"
COMMAND_LOAD_IMAGE = "LOAD_IMAGE"
COMMAND_READ_STATUS = "READ_STATUS"
COMMAND_READ_MEMORY = "READ_MEMORY"
COMMAND_WRITE_MEMORY = "WRITE_MEMORY"

STATUS_OK = 0x0000
STATUS_BAD_COMMAND = 0x3201
STATUS_BAD_LENGTH = 0x3202
STATUS_UNSUPPORTED_TRANSPORT = 0x3203
STATUS_NOT_HALTED = 0x3204
STATUS_BUSY = 0x3205
STATUS_BAD_ADDRESS = 0x3206
STATUS_WRITE_PROTECTED = 0x3207
STATUS_TAG_POLICY = 0x3208
STATUS_LOADER_ERROR = 0x3209
STATUS_TIMEOUT = 0x320A

STATUS_NAMES = {
    STATUS_OK: "OK",
    STATUS_BAD_COMMAND: "BAD_COMMAND",
    STATUS_BAD_LENGTH: "BAD_LENGTH",
    STATUS_UNSUPPORTED_TRANSPORT: "UNSUPPORTED_TRANSPORT",
    STATUS_NOT_HALTED: "NOT_HALTED",
    STATUS_BUSY: "BUSY",
    STATUS_BAD_ADDRESS: "BAD_ADDRESS",
    STATUS_WRITE_PROTECTED: "WRITE_PROTECTED",
    STATUS_TAG_POLICY: "TAG_POLICY",
    STATUS_LOADER_ERROR: "LOADER_ERROR",
    STATUS_TIMEOUT: "TIMEOUT",
}


@dataclass(frozen=True)
class MonitorTransport:
    name: str
    framing: str
    status: str
    owner_gate: str
    assumptions: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "framing": self.framing,
            "status": self.status,
            "owner_gate": self.owner_gate,
            "assumptions": list(self.assumptions),
        }


@dataclass(frozen=True)
class MonitorCommand:
    name: str
    opcode: int
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]
    allowed_transports: tuple[str, ...]
    requires_halted: bool
    memory_policy: str
    status_codes: tuple[str, ...]
    handoff: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "opcode": self.opcode,
            "request_fields": list(self.request_fields),
            "response_fields": list(self.response_fields),
            "allowed_transports": list(self.allowed_transports),
            "requires_halted": self.requires_halted,
            "memory_policy": self.memory_policy,
            "status_codes": list(self.status_codes),
            "handoff": self.handoff,
        }


@dataclass(frozen=True)
class MonitorMemoryPolicy:
    read_memories: tuple[str, ...]
    write_memories: tuple[str, ...]
    write_requires_halted: bool
    max_transfer_cells: int
    tag_policy: str
    protected_memories: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "read_memories": list(self.read_memories),
            "write_memories": list(self.write_memories),
            "write_requires_halted": self.write_requires_halted,
            "max_transfer_cells": self.max_transfer_cells,
            "tag_policy": self.tag_policy,
            "protected_memories": list(self.protected_memories),
        }


@dataclass(frozen=True)
class FpgaMonitorProfile:
    story: str
    status: str
    board: str
    loader_gate: str
    soc_loader_gate: str
    transports: tuple[MonitorTransport, ...]
    commands: tuple[MonitorCommand, ...]
    memory_policy: MonitorMemoryPolicy
    status_codes: dict[str, int]
    frame_rules: tuple[str, ...]
    blockers: tuple[str, ...]

    def command_by_name(self, name: str) -> MonitorCommand:
        for command in self.commands:
            if command.name == name:
                return command
        raise KeyError(name)

    def transport_by_name(self, name: str) -> MonitorTransport:
        for transport in self.transports:
            if transport.name == name:
                return transport
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "loader_gate": self.loader_gate,
            "soc_loader_gate": self.soc_loader_gate,
            "transports": [transport.as_dict() for transport in self.transports],
            "commands": [command.as_dict() for command in self.commands],
            "memory_policy": self.memory_policy.as_dict(),
            "status_codes": dict(self.status_codes),
            "frame_rules": list(self.frame_rules),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class MonitorCommandAudit:
    command: str
    transport: str
    target_memory: str
    cell_count: int
    halted: bool
    status_code: int
    status_name: str
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status_code == STATUS_OK

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "command": self.command,
            "transport": self.transport,
            "target_memory": self.target_memory,
            "cell_count": self.cell_count,
            "halted": self.halted,
            "status_code": self.status_code,
            "status_name": self.status_name,
            "issues": list(self.issues),
        }


def fpga_monitor_profile() -> FpgaMonitorProfile:
    transports = (TRANSPORT_UART, TRANSPORT_JTAG)
    return FpgaMonitorProfile(
        story=FPGA_MONITOR_PROFILE_STORY,
        status=FPGA_MONITOR_PROFILE_STATUS,
        board=fpga_first_test.TARGET_BOARD_NAME,
        loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        soc_loader_gate=fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
        transports=(
            MonitorTransport(
                name=TRANSPORT_UART,
                framing="COBS-or-length-prefixed binary frame over I27-S02 UART bytes with command CRC",
                status="primary interactive transport after UART ownership is handed to monitor firmware",
                owner_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
                assumptions=(
                    "host drains responses before sending another command",
                    "RX overrun or frame CRC failure aborts the command before state changes",
                ),
            ),
            MonitorTransport(
                name=TRANSPORT_JTAG,
                framing="same command payload through a bounded JTAG-assisted bridge",
                status="reserved until board bridge evidence exists",
                owner_gate=fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
                assumptions=(
                    "bridge output is synchronized before driving loader or monitor request signals",
                    "JTAG transport uses the same status codes and memory policy as UART",
                ),
            ),
        ),
        commands=(
            MonitorCommand(
                COMMAND_HELLO,
                0x01,
                ("protocol_version", "host_nonce"),
                ("protocol_version", "build_id", "capabilities", "status_code"),
                transports,
                False,
                "no memory access",
                ("OK", "BAD_LENGTH", "UNSUPPORTED_TRANSPORT", "TIMEOUT"),
                "establish host/board protocol version before any stateful command",
            ),
            MonitorCommand(
                COMMAND_HALT,
                0x02,
                ("reason", "timeout_cycles"),
                ("halt_state", "status_packet", "status_code"),
                transports,
                False,
                "requests safe monitor halt or trap-shell idle state",
                ("OK", "BUSY", "TIMEOUT", "UNSUPPORTED_TRANSPORT"),
                "I32-S02 implements the firmware halt point without corrupting architectural state",
            ),
            MonitorCommand(
                COMMAND_RESUME,
                0x03,
                ("resume_mode", "entry_cell"),
                ("running_state", "status_code"),
                transports,
                True,
                "no direct memory access",
                ("OK", "NOT_HALTED", "BAD_ADDRESS", "UNSUPPORTED_TRANSPORT"),
                "I32-S02 resumes from monitor firmware or trap shell",
            ),
            MonitorCommand(
                COMMAND_LOAD_IMAGE,
                0x04,
                ("program_id", "manifest_image_sha256", "ram_image_sha256", "cell_count"),
                ("loader_status", "loaded_cells", "status_packet", "status_code"),
                transports,
                True,
                "delegates bounded data_ram installation to I26-S04",
                ("OK", "NOT_HALTED", "BAD_LENGTH", "LOADER_ERROR", "TAG_POLICY"),
                "uses I26-S04 loader protocol and I30-S04 SoC handoff",
            ),
            MonitorCommand(
                COMMAND_READ_STATUS,
                0x05,
                ("selector",),
                ("status_packet", "loader_status", "monitor_state", "status_code"),
                transports,
                False,
                "reads status/debug records only",
                ("OK", "BAD_LENGTH", "UNSUPPORTED_TRANSPORT", "TIMEOUT"),
                "feeds I32-S04 snapshot and replay handoff",
            ),
            MonitorCommand(
                COMMAND_READ_MEMORY,
                0x06,
                ("target_memory", "base_cell", "cell_count"),
                ("payload_cells", "status_code"),
                transports,
                True,
                "reads bounded instruction_rom or data_ram cells, not tag sidecar provenance",
                ("OK", "NOT_HALTED", "BAD_ADDRESS", "BAD_LENGTH", "UNSUPPORTED_TRANSPORT"),
                "I32-S04 extends this into structured debug snapshots",
            ),
            MonitorCommand(
                COMMAND_WRITE_MEMORY,
                0x07,
                ("target_memory", "base_cell", "payload_cells", "tag_bits_all_zero"),
                ("written_cells", "status_code"),
                transports,
                True,
                "writes only bounded untagged data_ram cells through the loader policy",
                ("OK", "NOT_HALTED", "BAD_ADDRESS", "BAD_LENGTH", "WRITE_PROTECTED", "TAG_POLICY"),
                "delegates side effects to I26-S04/I30-S04 write policy",
            ),
        ),
        memory_policy=MonitorMemoryPolicy(
            read_memories=("instruction_rom", "data_ram"),
            write_memories=(fpga_program_loader.TARGET_MEMORY,),
            write_requires_halted=True,
            max_transfer_cells=fpga_program_loader.MAX_CHUNK_CELLS,
            tag_policy="host commands cannot create valid tags; write commands require tag_bits_all_zero",
            protected_memories=("instruction_rom", "tag_ram", "mmio", "status_registers"),
        ),
        status_codes={name: code for code, name in STATUS_NAMES.items()},
        frame_rules=(
            "each request carries magic, protocol_version, sequence, opcode, payload_length, payload, and crc32",
            "responses echo sequence and opcode and carry status_code plus command-specific payload",
            "commands that mutate memory require the monitor to be halted",
            "frame parse, CRC, unsupported transport, and bounds failures return status before mutating state",
            "LOAD_IMAGE and WRITE_MEMORY reuse the I26-S04 data_ram bounds and tag-clear policy",
        ),
        blockers=(
            "I32-S02 must implement ROM monitor and trap-shell firmware against these command names",
            "I32-S03 must use LOAD_IMAGE and RESUME for multi-program board sessions",
            "I32-S04 must extend READ_STATUS and READ_MEMORY into replayable debug snapshots",
        ),
    )


def audit_monitor_command(
    command_name: str,
    *,
    transport: str = TRANSPORT_UART,
    target_memory: str = "",
    cell_count: int = 0,
    halted: bool = True,
    tag_bits_all_zero: bool = True,
    busy: bool = False,
) -> MonitorCommandAudit:
    profile = fpga_monitor_profile()
    issues: list[str] = []
    status_code = STATUS_OK

    try:
        command = profile.command_by_name(command_name)
    except KeyError:
        return _command_audit(
            command_name,
            transport,
            target_memory,
            cell_count,
            halted,
            STATUS_BAD_COMMAND,
            ("unknown monitor command",),
        )

    if transport not in {entry.name for entry in profile.transports}:
        issues.append("transport is not supported by the monitor profile")
        status_code = _first_error(status_code, STATUS_UNSUPPORTED_TRANSPORT)
    elif transport not in command.allowed_transports:
        issues.append("command is not allowed on the selected transport")
        status_code = _first_error(status_code, STATUS_UNSUPPORTED_TRANSPORT)

    if command.requires_halted and not halted:
        issues.append(f"{command.name} requires the monitor to be halted")
        status_code = _first_error(status_code, STATUS_NOT_HALTED)
    if busy:
        issues.append("monitor is busy with a prior command")
        status_code = _first_error(status_code, STATUS_BUSY)

    if command.name in {COMMAND_LOAD_IMAGE, COMMAND_READ_MEMORY, COMMAND_WRITE_MEMORY}:
        if cell_count <= 0 or cell_count > profile.memory_policy.max_transfer_cells:
            issues.append("cell_count must be between 1 and the maximum transfer size")
            status_code = _first_error(status_code, STATUS_BAD_LENGTH)

    if command.name == COMMAND_LOAD_IMAGE:
        target = target_memory or fpga_program_loader.TARGET_MEMORY
        if target != fpga_program_loader.TARGET_MEMORY:
            issues.append("LOAD_IMAGE may only target data_ram through the loader policy")
            status_code = _first_error(status_code, STATUS_LOADER_ERROR)
    elif command.name == COMMAND_READ_MEMORY:
        if target_memory not in profile.memory_policy.read_memories:
            issues.append("READ_MEMORY target is not readable by the monitor profile")
            status_code = _first_error(status_code, STATUS_BAD_ADDRESS)
    elif command.name == COMMAND_WRITE_MEMORY:
        if target_memory not in profile.memory_policy.write_memories:
            issues.append("WRITE_MEMORY target is write-protected")
            status_code = _first_error(status_code, STATUS_WRITE_PROTECTED)
        if not tag_bits_all_zero:
            issues.append("WRITE_MEMORY cannot create valid tags")
            status_code = _first_error(status_code, STATUS_TAG_POLICY)

    return _command_audit(
        command.name,
        transport,
        target_memory,
        cell_count,
        halted,
        status_code,
        tuple(issues),
    )


def fpga_monitor_profile_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_monitor_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_monitor_profile(profile: FpgaMonitorProfile | None = None) -> str:
    if profile is None:
        profile = fpga_monitor_profile()
    lines = [
        "# FPGA Monitor Command Profile",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Board: `{profile.board}`",
        f"Loader gate: `{profile.loader_gate}`",
        f"SoC loader gate: `{profile.soc_loader_gate}`",
        "",
        "## Commands",
        "",
        "| Command | Opcode | Requires halted | Memory policy |",
        "| --- | --- | --- | --- |",
    ]
    for command in profile.commands:
        lines.append(
            f"| `{command.name}` | `0x{command.opcode:02X}` | "
            f"{'yes' if command.requires_halted else 'no'} | {command.memory_policy} |"
        )
    lines.extend(["", "## Status Codes", ""])
    lines.extend(f"- `{name}` = `0x{code:04X}`." for name, code in profile.status_codes.items())
    lines.extend(["", "## Frame Rules", ""])
    lines.extend(f"- {rule}." for rule in profile.frame_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_monitor_profile(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_profile()
    issues: list[str] = []

    if profile.story != FPGA_MONITOR_PROFILE_STORY:
        issues.append(f"monitor profile story must be {FPGA_MONITOR_PROFILE_STORY}")
    if profile.status != FPGA_MONITOR_PROFILE_STATUS:
        issues.append("monitor profile status must remain defined")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("monitor profile board must match first-test target")
    if profile.loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("monitor profile must depend on I26-S04 loader")
    if profile.soc_loader_gate != fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL:
        issues.append("monitor profile must depend on I30-S04 loader handoff")

    issues.extend(fpga_program_loader.validate_fpga_program_loader(root))
    issues.extend(fpga_soc_loader_handoff.validate_fpga_soc_loader_handoff(root))

    transport_names = {transport.name for transport in profile.transports}
    for transport in (TRANSPORT_UART, TRANSPORT_JTAG):
        if transport not in transport_names:
            issues.append(f"missing monitor transport {transport}")

    command_names = {command.name for command in profile.commands}
    for command in (
        COMMAND_HELLO,
        COMMAND_HALT,
        COMMAND_RESUME,
        COMMAND_LOAD_IMAGE,
        COMMAND_READ_STATUS,
        COMMAND_READ_MEMORY,
        COMMAND_WRITE_MEMORY,
    ):
        if command not in command_names:
            issues.append(f"missing monitor command {command}")

    opcodes = [command.opcode for command in profile.commands]
    if len(opcodes) != len(set(opcodes)):
        issues.append("monitor command opcodes must be unique")
    for command in profile.commands:
        if not command.request_fields:
            issues.append(f"{command.name} must name request fields")
        if not command.response_fields:
            issues.append(f"{command.name} must name response fields")
        if not command.allowed_transports:
            issues.append(f"{command.name} must name allowed transports")
        if "OK" not in command.status_codes:
            issues.append(f"{command.name} must include OK status")

    if "instruction_rom" not in profile.memory_policy.read_memories:
        issues.append("monitor profile must allow bounded instruction_rom reads")
    if fpga_program_loader.TARGET_MEMORY not in profile.memory_policy.read_memories:
        issues.append("monitor profile must allow bounded data_ram reads")
    if profile.memory_policy.write_memories != (fpga_program_loader.TARGET_MEMORY,):
        issues.append("monitor profile must only allow data_ram writes")
    if profile.memory_policy.max_transfer_cells != fpga_program_loader.MAX_CHUNK_CELLS:
        issues.append("monitor profile must reuse the I26-S04 transfer bound")
    if "tag_bits_all_zero" not in profile.memory_policy.tag_policy:
        issues.append("monitor profile must prohibit host tag creation")

    expected_statuses = {
        "OK",
        "BAD_COMMAND",
        "BAD_LENGTH",
        "UNSUPPORTED_TRANSPORT",
        "NOT_HALTED",
        "BUSY",
        "BAD_ADDRESS",
        "WRITE_PROTECTED",
        "TAG_POLICY",
        "LOADER_ERROR",
        "TIMEOUT",
    }
    if expected_statuses - set(profile.status_codes):
        issues.append("monitor status code set is incomplete")

    if not audit_monitor_command(COMMAND_HELLO, halted=False).passed:
        issues.append("HELLO should be valid before halt")
    if audit_monitor_command(COMMAND_LOAD_IMAGE, halted=False, cell_count=1).status_code != STATUS_NOT_HALTED:
        issues.append("LOAD_IMAGE must require halted monitor state")
    if not audit_monitor_command(
        COMMAND_WRITE_MEMORY,
        target_memory=fpga_program_loader.TARGET_MEMORY,
        cell_count=1,
        halted=True,
    ).passed:
        issues.append("WRITE_MEMORY data_ram sample should pass while halted")
    if audit_monitor_command(
        COMMAND_WRITE_MEMORY,
        target_memory="instruction_rom",
        cell_count=1,
        halted=True,
    ).status_code != STATUS_WRITE_PROTECTED:
        issues.append("WRITE_MEMORY instruction_rom sample must be write-protected")
    if audit_monitor_command(
        COMMAND_WRITE_MEMORY,
        target_memory=fpga_program_loader.TARGET_MEMORY,
        cell_count=1,
        halted=True,
        tag_bits_all_zero=False,
    ).status_code != STATUS_TAG_POLICY:
        issues.append("WRITE_MEMORY tag-bearing sample must fail tag policy")
    if not audit_monitor_command(
        COMMAND_READ_MEMORY,
        target_memory="instruction_rom",
        cell_count=1,
        halted=True,
    ).passed:
        issues.append("READ_MEMORY instruction_rom sample should pass while halted")
    if audit_monitor_command("NOPE").status_code != STATUS_BAD_COMMAND:
        issues.append("unknown monitor command must fail BAD_COMMAND")

    doc = _read_if_exists(root / FPGA_MONITOR_PROFILE_DOC)
    for token in (
        "Story: I32-S01",
        FPGA_MONITOR_PROFILE_TOOL,
        fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
        "uart_mmio_monitor",
        "jtag_assisted_monitor",
        "HELLO",
        "HALT",
        "RESUME",
        "LOAD_IMAGE",
        "READ_STATUS",
        "READ_MEMORY",
        "WRITE_MEMORY",
        "BAD_COMMAND",
        "NOT_HALTED",
        "WRITE_PROTECTED",
        "TAG_POLICY",
        "data_ram",
        "instruction_rom",
        "tag_bits_all_zero",
        "I32-S02",
        "I32-S04",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MONITOR_PROFILE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(audit_monitor_command(COMMAND_HELLO).as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"monitor profile objects are not JSON serializable: {exc}")

    return tuple(issues)


def _command_audit(
    command: str,
    transport: str,
    target_memory: str,
    cell_count: int,
    halted: bool,
    status_code: int,
    issues: tuple[str, ...],
) -> MonitorCommandAudit:
    return MonitorCommandAudit(
        command=command,
        transport=transport,
        target_memory=target_memory,
        cell_count=cell_count,
        halted=halted,
        status_code=status_code,
        status_name=STATUS_NAMES[status_code],
        issues=issues,
    )


def _first_error(current: int, candidate: int) -> int:
    if current == STATUS_OK:
        return candidate
    return current


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

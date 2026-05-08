"""Compact FPGA debug/status packet contract.

Owner stories:
- I25-S01: define the FPGA debug/status packet for board bring-up.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_programming, fpga_smoke


JsonValue = Any

FPGA_DEBUG_STATUS_STORY = "I25-S01"
FPGA_DEBUG_STATUS_DOC = Path("docs/implementation/fpga-debug-status-packet.md")
FPGA_DEBUG_STATUS_TOOL = "python tools\\fpga_debug_status_packet.py --check"
STATUS_PACKET_MAGIC = 0xC501
STATUS_PACKET_VERSION = 1
STATUS_PACKET_SIZE_BYTES = 32
STATUS_PACKET_STRUCT = struct.Struct("<HBBHBBQIHHII")


@dataclass(frozen=True)
class DebugStatusFlag:
    name: str
    bit: int
    source: str
    meaning: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "bit": self.bit,
            "mask": 1 << self.bit,
            "source": self.source,
            "meaning": self.meaning,
        }


@dataclass(frozen=True)
class DebugStatusField:
    name: str
    offset: int
    width_bits: int
    source: str
    meaning: str
    architectural_effect: str

    @property
    def width_bytes(self) -> int:
        return self.width_bits // 8

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "offset": self.offset,
            "width_bits": self.width_bits,
            "source": self.source,
            "meaning": self.meaning,
            "architectural_effect": self.architectural_effect,
        }


@dataclass(frozen=True)
class FpgaDebugStatusProfile:
    story: str
    board: str
    packet_size_bytes: int
    magic: int
    version: int
    byte_order: str
    fields: tuple[DebugStatusField, ...]
    flags: tuple[DebugStatusFlag, ...]
    pass_fail_states: dict[int, str]
    non_interference_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "packet_size_bytes": self.packet_size_bytes,
            "magic": self.magic,
            "version": self.version,
            "byte_order": self.byte_order,
            "fields": [field.as_dict() for field in self.fields],
            "flags": [flag.as_dict() for flag in self.flags],
            "pass_fail_states": {str(key): value for key, value in self.pass_fail_states.items()},
            "non_interference_rules": list(self.non_interference_rules),
        }


@dataclass(frozen=True)
class DebugStatusPacket:
    flags: int
    slot: int
    pass_fail_state: int
    pc_cell: int
    retire_count: int
    fault_code: int
    trap_cause: int
    build_id: int
    sequence: int
    magic: int = STATUS_PACKET_MAGIC
    version: int = STATUS_PACKET_VERSION
    packet_size: int = STATUS_PACKET_SIZE_BYTES

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "magic": self.magic,
            "version": self.version,
            "packet_size": self.packet_size,
            "flags": self.flags,
            "slot": self.slot,
            "pass_fail_state": self.pass_fail_state,
            "pc_cell": self.pc_cell,
            "retire_count": self.retire_count,
            "fault_code": self.fault_code,
            "trap_cause": self.trap_cause,
            "build_id": self.build_id,
            "sequence": self.sequence,
        }


def fpga_debug_status_profile() -> FpgaDebugStatusProfile:
    return FpgaDebugStatusProfile(
        story=FPGA_DEBUG_STATUS_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        packet_size_bytes=STATUS_PACKET_SIZE_BYTES,
        magic=STATUS_PACKET_MAGIC,
        version=STATUS_PACKET_VERSION,
        byte_order="little_endian",
        fields=(
            DebugStatusField("magic", 0, 16, "constant 0xC501", "packet resynchronization marker", "none"),
            DebugStatusField("version", 2, 8, "constant 1", "packet format version", "none"),
            DebugStatusField("packet_size", 3, 8, "constant 32", "packet size in bytes", "none"),
            DebugStatusField("flags", 4, 16, "status flags", "reset, retire, fault, pass/fail, and heartbeat bits", "none"),
            DebugStatusField("slot", 6, 8, "retire_packet.slot", "slot within the current fetch group", "none"),
            DebugStatusField("pass_fail_state", 7, 8, "pass_led_o/fail_led_o state machine", "idle, running, first_pass, failed, or blocked", "none"),
            DebugStatusField("pc_cell", 8, 64, "retire_packet.pc or debug_pcc.cursor", "zero-extended cell PC", "none"),
            DebugStatusField("retire_count", 16, 32, "debug_retire_sequence[31:0]", "retire progress counter", "none"),
            DebugStatusField("fault_code", 20, 16, "status_fault_code_o", "sticky first fault code", "none"),
            DebugStatusField("trap_cause", 22, 16, "retire_packet.fault.cause", "trap cause for the sampled retire point", "none"),
            DebugStatusField("build_id", 24, 32, "first-test build identity register", "software-visible build identity", "none"),
            DebugStatusField("sequence", 28, 32, "debug packet counter", "monotonic packet sequence for drop detection", "none"),
        ),
        flags=(
            DebugStatusFlag("reset_asserted", 0, "board_reset_n_i/core_rst_n", "reset is currently asserted"),
            DebugStatusFlag("reset_observed", 1, "status_reset_observed_o", "core reset observation has occurred"),
            DebugStatusFlag("core_idle", 2, "status_core_idle_o", "core reports idle"),
            DebugStatusFlag("retire_valid", 3, "status_retire_valid_o", "sample includes a retire observation"),
            DebugStatusFlag("fault_valid", 4, "status_fault_valid_o", "sticky fault observation is set"),
            DebugStatusFlag("pass_led", 5, "pass_led_o", "first-test pass LED is asserted"),
            DebugStatusFlag("fail_led", 6, "fail_led_o", "first-test fail LED is asserted"),
            DebugStatusFlag("heartbeat", 7, "heartbeat_led_o", "heartbeat observation is high in this sample"),
        ),
        pass_fail_states={
            0: "idle_or_reset",
            1: "running",
            2: "first_pass",
            3: "failed",
            4: "blocked",
        },
        non_interference_rules=(
            "packet generation samples existing debug and retire observation signals only",
            "packet generation must not deassert retire_ready or backpressure architectural retire behavior",
            "UART or ILA consumers may drop packets without changing CPU state",
            "build_id and sequence are debug metadata and are not architectural registers",
        ),
    )


def debug_status_flag_mask(*names: str) -> int:
    flags = {flag.name: flag for flag in fpga_debug_status_profile().flags}
    mask = 0
    for name in names:
        try:
            flag = flags[name]
        except KeyError as exc:
            raise ValueError(f"unknown debug status flag {name!r}") from exc
        mask |= 1 << flag.bit
    return mask


def example_debug_status_packet() -> DebugStatusPacket:
    return DebugStatusPacket(
        flags=debug_status_flag_mask("reset_observed", "retire_valid", "pass_led", "heartbeat"),
        slot=0,
        pass_fail_state=2,
        pc_cell=0x1008,
        retire_count=8,
        fault_code=0,
        trap_cause=0,
        build_id=0x2501C0DE,
        sequence=1,
    )


def validate_debug_status_packet(packet: DebugStatusPacket) -> tuple[str, ...]:
    profile = fpga_debug_status_profile()
    issues: list[str] = []
    max_flag_mask = 0
    for flag in profile.flags:
        max_flag_mask |= 1 << flag.bit

    if packet.magic != STATUS_PACKET_MAGIC:
        issues.append("magic must be 0xC501")
    if packet.version != STATUS_PACKET_VERSION:
        issues.append("version must be 1")
    if packet.packet_size != STATUS_PACKET_SIZE_BYTES:
        issues.append("packet_size must be 32")
    if packet.flags & ~max_flag_mask:
        issues.append("flags contain reserved bits")
    if not 0 <= packet.slot <= 3:
        issues.append("slot must be in range 0..3")
    if packet.pass_fail_state not in profile.pass_fail_states:
        issues.append("pass_fail_state is not defined")
    for name, value, bits in (
        ("pc_cell", packet.pc_cell, 64),
        ("retire_count", packet.retire_count, 32),
        ("fault_code", packet.fault_code, 16),
        ("trap_cause", packet.trap_cause, 16),
        ("build_id", packet.build_id, 32),
        ("sequence", packet.sequence, 32),
    ):
        if not 0 <= value < (1 << bits):
            issues.append(f"{name} must fit in {bits} bits")
    return tuple(issues)


def encode_debug_status_packet(packet: DebugStatusPacket) -> bytes:
    issues = validate_debug_status_packet(packet)
    if issues:
        raise ValueError("; ".join(issues))
    return STATUS_PACKET_STRUCT.pack(
        packet.magic,
        packet.version,
        packet.packet_size,
        packet.flags,
        packet.slot,
        packet.pass_fail_state,
        packet.pc_cell,
        packet.retire_count,
        packet.fault_code,
        packet.trap_cause,
        packet.build_id,
        packet.sequence,
    )


def decode_debug_status_packet(payload: bytes) -> DebugStatusPacket:
    if len(payload) != STATUS_PACKET_SIZE_BYTES:
        raise ValueError("debug status packet must be exactly 32 bytes")
    (
        magic,
        version,
        packet_size,
        flags,
        slot,
        pass_fail_state,
        pc_cell,
        retire_count,
        fault_code,
        trap_cause,
        build_id,
        sequence,
    ) = STATUS_PACKET_STRUCT.unpack(payload)
    packet = DebugStatusPacket(
        magic=magic,
        version=version,
        packet_size=packet_size,
        flags=flags,
        slot=slot,
        pass_fail_state=pass_fail_state,
        pc_cell=pc_cell,
        retire_count=retire_count,
        fault_code=fault_code,
        trap_cause=trap_cause,
        build_id=build_id,
        sequence=sequence,
    )
    issues = validate_debug_status_packet(packet)
    if issues:
        raise ValueError("; ".join(issues))
    return packet


def fpga_debug_status_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_debug_status_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_debug_status_profile(
    profile: FpgaDebugStatusProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_debug_status_profile()
    lines = [
        "# FPGA Debug Status Packet",
        "",
        f"Story: {profile.story}",
        "",
        f"Board: `{profile.board}`",
        f"Packet size: {profile.packet_size_bytes} bytes",
        f"Magic: `0x{profile.magic:04X}`",
        f"Version: {profile.version}",
        f"Byte order: `{profile.byte_order}`",
        "",
        "## Fields",
        "",
        "| Field | Offset | Width | Source | Meaning | Architectural effect |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for field in profile.fields:
        lines.append(
            f"| `{field.name}` | {field.offset} | {field.width_bits} | "
            f"`{field.source}` | {field.meaning} | {field.architectural_effect} |"
        )
    lines.extend(["", "## Flags", "", "| Flag | Bit | Source | Meaning |", "| --- | --- | --- | --- |"])
    for flag in profile.flags:
        lines.append(f"| `{flag.name}` | {flag.bit} | `{flag.source}` | {flag.meaning} |")
    lines.extend(["", "## Pass/Fail States", "", "| Value | State |", "| --- | --- |"])
    for value, name in sorted(profile.pass_fail_states.items()):
        lines.append(f"| {value} | `{name}` |")
    lines.extend(["", "## Non-Interference", ""])
    lines.extend(f"- {rule}." for rule in profile.non_interference_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_debug_status(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_debug_status_profile()
    issues: list[str] = []

    if profile.story != FPGA_DEBUG_STATUS_STORY:
        issues.append(f"debug status story must be {FPGA_DEBUG_STATUS_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("debug status board must match first-test profile")
    if profile.packet_size_bytes != STATUS_PACKET_SIZE_BYTES:
        issues.append("debug status packet must be 32 bytes")
    if profile.magic != STATUS_PACKET_MAGIC:
        issues.append("debug status magic must be 0xC501")
    if profile.version != STATUS_PACKET_VERSION:
        issues.append("debug status version must be 1")
    if profile.byte_order != "little_endian":
        issues.append("debug status packet must be little-endian")
    if STATUS_PACKET_STRUCT.size != STATUS_PACKET_SIZE_BYTES:
        issues.append("debug status struct packing must be 32 bytes")

    issues.extend(fpga_smoke.validate_fpga_smoke_firmware(root))
    issues.extend(fpga_programming.validate_fpga_programming(root))

    fields = {field.name: field for field in profile.fields}
    expected_offsets = {
        "magic": 0,
        "version": 2,
        "packet_size": 3,
        "flags": 4,
        "slot": 6,
        "pass_fail_state": 7,
        "pc_cell": 8,
        "retire_count": 16,
        "fault_code": 20,
        "trap_cause": 22,
        "build_id": 24,
        "sequence": 28,
    }
    for name, offset in expected_offsets.items():
        field = fields.get(name)
        if field is None:
            issues.append(f"missing debug status field {name}")
        elif field.offset != offset:
            issues.append(f"{name} offset must be {offset}")
        elif field.width_bits % 8 != 0:
            issues.append(f"{name} width must be byte-aligned")

    flag_names = {flag.name for flag in profile.flags}
    for name in (
        "reset_asserted",
        "reset_observed",
        "core_idle",
        "retire_valid",
        "fault_valid",
        "pass_led",
        "fail_led",
        "heartbeat",
    ):
        if name not in flag_names:
            issues.append(f"missing debug status flag {name}")

    if profile.pass_fail_states.get(2) != "first_pass":
        issues.append("pass/fail state 2 must be first_pass")
    if profile.pass_fail_states.get(3) != "failed":
        issues.append("pass/fail state 3 must be failed")
    if not any("retire behavior" in rule for rule in profile.non_interference_rules):
        issues.append("debug status must state it does not change retire behavior")

    example = example_debug_status_packet()
    try:
        encoded = encode_debug_status_packet(example)
        decoded = decode_debug_status_packet(encoded)
        if decoded != example:
            issues.append("debug status example must round-trip through encode/decode")
    except ValueError as exc:
        issues.append(f"debug status example packet failed validation: {exc}")

    doc = _read_if_exists(root / FPGA_DEBUG_STATUS_DOC)
    for token in (
        "Story: I25-S01",
        FPGA_DEBUG_STATUS_TOOL,
        "32 bytes",
        "0xC501",
        "little-endian",
        "reset_asserted",
        "reset_observed",
        "pc_cell",
        "slot",
        "retire_count",
        "fault_code",
        "trap_cause",
        "pass_fail_state",
        "build_id",
        "sequence",
        "first_pass",
        "retire behavior",
        "I25-S02",
        "I25-S03",
    ):
        if token not in doc:
            issues.append(f"{FPGA_DEBUG_STATUS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

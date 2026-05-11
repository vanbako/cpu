"""Tang Retro Console 60K SOM SRAM programming and smoke observation gate.

Owner stories:
- I34-S04: program the Retro Console 60K SRAM and capture smoke observations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_debug_status,
    fpga_probe_bundles,
    fpga_retro_console_gowin,
    fpga_retro_console_identity,
    fpga_uart_status,
)


JsonValue = Any

FPGA_RETRO_CONSOLE_PROGRAMMING_STORY = "I34-S04"
FPGA_RETRO_CONSOLE_PROGRAMMING_DOC = Path(
    "docs/implementation/fpga-retro-console-programming.md"
)
FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL = (
    "python tools\\fpga_retro_console_programming.py --check"
)
FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE = Path(
    "docs/implementation/evidence/i34_s04_retro_console_programming.txt"
)
RETRO_CONSOLE_PROGRAMMING_STATUS = "blocked_until_retro_console_sram_observation"
RETRO_CONSOLE_PROGRAMMING_RESULT = "retro_console_sram_observation_captured"

OBSERVED = "observed"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_CAPTURE = "needs_capture"

BOARD_RESULT_SMOKE_PASS = "retro_console_smoke_pass"
BOARD_RESULT_FAILURE = "failure_observed"


@dataclass(frozen=True)
class RetroConsoleProgrammingField:
    name: str
    required: bool
    description: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class RetroConsoleProgrammingProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    gowin_gate: str
    identity_gate: str
    uart_status_gate: str
    probe_gate: str
    required_mode: str
    minimum_observation_seconds: int
    required_fields: tuple[RetroConsoleProgrammingField, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def field_by_name(self, name: str) -> RetroConsoleProgrammingField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "board": self.board,
            "gowin_gate": self.gowin_gate,
            "identity_gate": self.identity_gate,
            "uart_status_gate": self.uart_status_gate,
            "probe_gate": self.probe_gate,
            "required_mode": self.required_mode,
            "minimum_observation_seconds": self.minimum_observation_seconds,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class RetroConsoleProgrammingRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RetroConsoleProgrammingAudit:
    status: str
    message: str
    evidence_path: str
    gowin_status: str
    board_result: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    observation_issues: tuple[str, ...]
    packet_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == OBSERVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "gowin_status": self.gowin_status,
            "board_result": self.board_result,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "observation_issues": list(self.observation_issues),
            "packet_issues": list(self.packet_issues),
            "actions": list(self.actions),
        }


def fpga_retro_console_programming_profile() -> RetroConsoleProgrammingProfile:
    return RetroConsoleProgrammingProfile(
        story=FPGA_RETRO_CONSOLE_PROGRAMMING_STORY,
        status=RETRO_CONSOLE_PROGRAMMING_STATUS,
        evidence_path=FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE,
        board=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD,
        gowin_gate=fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        identity_gate=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        uart_status_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        probe_gate=fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        required_mode="SRAM",
        minimum_observation_seconds=10,
        required_fields=(
            RetroConsoleProgrammingField("story", True, "Must be I34-S04."),
            RetroConsoleProgrammingField("programmed_at", True, "Local programming timestamp."),
            RetroConsoleProgrammingField("repository_commit", True, "Repository commit used for the board run."),
            RetroConsoleProgrammingField("board", True, "Physical board name."),
            RetroConsoleProgrammingField("retro_console_gowin", True, "I34-S03 Gowin evidence path."),
            RetroConsoleProgrammingField("bitstream_path", True, "Exact Retro Console .fs bitstream path."),
            RetroConsoleProgrammingField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            RetroConsoleProgrammingField("programming_tool", True, "Gowin Programmer or approved equivalent."),
            RetroConsoleProgrammingField("programming_mode", True, "Must be SRAM."),
            RetroConsoleProgrammingField("programming_result", True, "Must be success."),
            RetroConsoleProgrammingField("programming_log", True, "Captured programming log path."),
            RetroConsoleProgrammingField("reset_released", True, "yes after board reset release."),
            RetroConsoleProgrammingField("reset_observation", True, "Reset release log, photo, or probe path."),
            RetroConsoleProgrammingField("observation_duration_s", True, "Observation duration after reset release."),
            RetroConsoleProgrammingField("heartbeat_observed", True, "yes when heartbeat toggled."),
            RetroConsoleProgrammingField("pass_output_observed", True, "yes or no."),
            RetroConsoleProgrammingField("fail_output_observed", True, "yes or no."),
            RetroConsoleProgrammingField("board_result", True, "retro_console_smoke_pass or failure_observed."),
            RetroConsoleProgrammingField("uart_log", False, "Raw UART/status capture log path or none."),
            RetroConsoleProgrammingField("uart_status_packet_hex", False, "Captured 32-byte I25-S01 packet hex or none."),
            RetroConsoleProgrammingField("decoded_status_packet", False, "Decoded packet record path, transcript, or none."),
            RetroConsoleProgrammingField("probe_capture", False, "GAO/ILA/probe capture path or none."),
            RetroConsoleProgrammingField("status_retire_count", True, "Decoded retire count or probe-derived count."),
            RetroConsoleProgrammingField("status_fault_code", True, "Decoded fault code or probe-derived code."),
            RetroConsoleProgrammingField("pass_fail_state", True, "Decoded or observed pass/fail state."),
            RetroConsoleProgrammingField("primary_138k_claim", True, "Must be no."),
            RetroConsoleProgrammingField("retest_commands", True, "Commands to rerun gates and recapture evidence."),
        ),
        retest_commands=(
            fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
            fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
            fpga_uart_status.FPGA_UART_STATUS_TOOL,
            fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        ),
        blockers=(
            "I34-S03 Gowin evidence must pass before SRAM programming can close",
            "programming must use SRAM mode and the exact I34-S03 bitstream SHA-256",
            "reset release, heartbeat, pass/fail output, and UART or probe evidence are required",
            "the record must carry primary_138k_claim=no and must not claim the 138K first-pass board",
        ),
        handoffs=(
            "I34-S05 consumes failure_observed captures for replay classification",
            "I34-S06 consumes pass or blocker evidence while keeping the Tang Mega Dock with 138K SOM path active",
        ),
    )


def retro_console_programming_template(
    profile: RetroConsoleProgrammingProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_programming_profile()
    packet = fpga_debug_status.example_debug_status_packet()
    packet_hex = fpga_debug_status.encode_debug_status_packet(packet).hex()
    retest_commands = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "programmed_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"retro_console_gowin={fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE.as_posix()}",
            "bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs",
            "bitstream_sha256=",
            "programming_tool=Gowin Programmer",
            "programming_mode=SRAM",
            "programming_result=success",
            "programming_log=docs/implementation/evidence/i34_s04_programming.log",
            "reset_released=yes",
            "reset_observation=docs/implementation/evidence/i34_s04_reset_release.txt",
            "observation_duration_s=10",
            "heartbeat_observed=yes",
            "pass_output_observed=yes",
            "fail_output_observed=no",
            f"board_result={BOARD_RESULT_SMOKE_PASS}",
            "uart_log=docs/implementation/evidence/i34_s04_uart.log",
            f"uart_status_packet_hex={packet_hex}",
            "decoded_status_packet=docs/implementation/evidence/i34_s04_status_packet.json",
            "probe_capture=none",
            f"status_retire_count={packet.retire_count}",
            f"status_fault_code={packet.fault_code}",
            "pass_fail_state=first_pass",
            "primary_138k_claim=no",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_retro_console_programming(text: str) -> RetroConsoleProgrammingRecord:
    fields: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} is not key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {line_number} has an empty key")
        fields[key] = value.strip()
    return RetroConsoleProgrammingRecord(fields)


def audit_retro_console_programming(
    record: RetroConsoleProgrammingRecord,
    *,
    gowin_audit: fpga_retro_console_gowin.RetroConsoleGowinAudit | None = None,
    evidence_path: str = "<inline>",
    profile: RetroConsoleProgrammingProfile | None = None,
) -> RetroConsoleProgrammingAudit:
    if profile is None:
        profile = fpga_retro_console_programming_profile()
    if gowin_audit is not None and not gowin_audit.passed:
        return RetroConsoleProgrammingAudit(
            status=BLOCKED,
            message="Retro Console programming is blocked until I34-S03 Gowin evidence passes.",
            evidence_path=evidence_path,
            gowin_status=gowin_audit.status,
            board_result=record.value("board_result"),
            missing_fields=(),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=("complete I34-S03 Gowin evidence before programming SRAM",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I34-S04")

    link_issues = _link_issues(record, profile, gowin_audit)
    observation_issues = _observation_issues(record, profile)
    packet, packet_issues = _decode_packet(record.value("uart_status_packet_hex"))
    observation_issues.extend(_packet_consistency_issues(record, packet))
    observation_issues.extend(_board_result_issues(record))

    if missing_fields:
        return _audit(
            INVALID,
            "Retro Console programming evidence is incomplete or malformed.",
            evidence_path,
            record,
            gowin_audit,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            observation_issues=tuple(observation_issues),
            packet_issues=tuple(packet_issues),
            actions=("complete all required I34-S04 observation fields", "rerun the programming audit"),
        )
    if link_issues or packet_issues:
        return _audit(
            INVALID,
            "Retro Console programming links or UART packet are invalid.",
            evidence_path,
            record,
            gowin_audit,
            link_issues=tuple(link_issues),
            observation_issues=tuple(observation_issues),
            packet_issues=tuple(packet_issues),
            actions=("fix bitstream identity, evidence links, 138K claim guard, or UART packet decode",),
        )
    if observation_issues:
        return _audit(
            NEEDS_CAPTURE,
            "Retro Console programming needs more complete smoke observation evidence.",
            evidence_path,
            record,
            gowin_audit,
            observation_issues=tuple(observation_issues),
            actions=("recapture reset, heartbeat, pass/fail, UART, or probe observations",),
        )

    actions = (
        ("hand the Retro Console failure capture to I34-S05 replay classification",)
        if record.value("board_result") == BOARD_RESULT_FAILURE
        else ("hand the Retro Console smoke observation to I34-S06 archive evidence",)
    )
    return _audit(
        OBSERVED,
        "Retro Console SRAM programming and smoke observation evidence is captured.",
        evidence_path,
        record,
        gowin_audit,
        actions=actions,
    )


def load_retro_console_programming_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    gowin_evidence_path: Path | None = None,
) -> RetroConsoleProgrammingAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_programming_profile()
    relative_path = evidence_path or profile.evidence_path
    gowin_audit = fpga_retro_console_gowin.load_retro_console_gowin_audit(
        root,
        gowin_evidence_path,
    )
    path = root / relative_path
    if not path.exists():
        return RetroConsoleProgrammingAudit(
            status=BLOCKED,
            message="No Retro Console SRAM programming observation has been captured yet.",
            evidence_path=relative_path.as_posix(),
            gowin_status=gowin_audit.status,
            board_result="",
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the programming template",
                "capture programming log, reset release, heartbeat, pass/fail, UART or probe evidence, and bitstream identity",
            ),
        )
    try:
        record = parse_retro_console_programming(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return RetroConsoleProgrammingAudit(
            status=INVALID,
            message="Retro Console programming evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            gowin_status=gowin_audit.status,
            board_result="",
            missing_fields=(str(exc),),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=("fix the key=value evidence record", "rerun the I34-S04 audit"),
        )
    return audit_retro_console_programming(
        record,
        gowin_audit=gowin_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_retro_console_programming_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_retro_console_programming_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_retro_console_programming(
    profile: RetroConsoleProgrammingProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_programming_profile()
    lines = [
        "# FPGA Retro Console Programming",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        f"Required mode: `{profile.required_mode}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |")
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_retro_console_programming(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_programming_profile()
    issues: list[str] = []

    if profile.story != FPGA_RETRO_CONSOLE_PROGRAMMING_STORY:
        issues.append(f"Retro Console programming story must be {FPGA_RETRO_CONSOLE_PROGRAMMING_STORY}")
    if profile.status != RETRO_CONSOLE_PROGRAMMING_STATUS:
        issues.append("Retro Console programming profile must remain blocked until board observation exists")
    if profile.board != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD:
        issues.append("Retro Console programming board must match I34-S01")
    if profile.required_mode != "SRAM":
        issues.append("Retro Console programming must require SRAM mode")
    if profile.minimum_observation_seconds < 10:
        issues.append("Retro Console programming observation duration must be at least 10 seconds")
    if profile.gowin_gate != fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL:
        issues.append("Retro Console programming must depend on I34-S03")
    if profile.identity_gate != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL:
        issues.append("Retro Console programming must depend on I34-S01 identity")
    if profile.uart_status_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("Retro Console programming must depend on I25-S02 UART status")
    if profile.probe_gate != fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL:
        issues.append("Retro Console programming must reference I25-S03 probe bundles")

    for check_issues in (
        fpga_retro_console_gowin.validate_fpga_retro_console_gowin(root),
        fpga_uart_status.validate_fpga_uart_status(root),
        fpga_probe_bundles.validate_fpga_probe_bundles(root),
    ):
        issues.extend(check_issues)

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "programmed_at",
        "repository_commit",
        "board",
        "retro_console_gowin",
        "bitstream_path",
        "bitstream_sha256",
        "programming_log",
        "reset_released",
        "reset_observation",
        "heartbeat_observed",
        "pass_output_observed",
        "fail_output_observed",
        "board_result",
        "status_retire_count",
        "status_fault_code",
        "pass_fail_state",
        "primary_138k_claim",
        "retest_commands",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing Retro Console programming field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    for optional in ("uart_log", "uart_status_packet_hex", "decoded_status_packet", "probe_capture"):
        if fields.get(optional) and fields[optional].required:
            issues.append(f"{optional} must remain optional")

    passed_gowin = fpga_retro_console_gowin.RetroConsoleGowinAudit(
        status=fpga_retro_console_gowin.GOWIN_PASS,
        message="passed",
        evidence_path=fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE.as_posix(),
        identity_status="alternate_target_verified",
        constraints_status="confirmed",
        report_status="passed",
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=("build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs",),
        actions=(),
    )
    complete_record = parse_retro_console_programming(
        retro_console_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-11T23:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
    )
    if not audit_retro_console_programming(complete_record, gowin_audit=passed_gowin).passed:
        issues.append("complete Retro Console programming evidence must audit as observed")

    packet_hex = fpga_debug_status.encode_debug_status_packet(
        fpga_debug_status.example_debug_status_packet()
    ).hex()
    no_uart_or_probe = parse_retro_console_programming(
        retro_console_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-11T23:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("uart_log=docs/implementation/evidence/i34_s04_uart.log", "uart_log=none")
        .replace(f"uart_status_packet_hex={packet_hex}", "uart_status_packet_hex=none")
    )
    if audit_retro_console_programming(no_uart_or_probe, gowin_audit=passed_gowin).status != NEEDS_CAPTURE:
        issues.append("Retro Console programming must require UART or probe evidence")

    default_audit = load_retro_console_programming_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default Retro Console programming audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_RETRO_CONSOLE_PROGRAMMING_DOC)
    for token in (
        "Story: I34-S04",
        FPGA_RETRO_CONSOLE_PROGRAMMING_TOOL,
        FPGA_RETRO_CONSOLE_PROGRAMMING_EVIDENCE.as_posix(),
        fpga_retro_console_gowin.FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        fpga_uart_status.FPGA_UART_STATUS_TOOL,
        fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        "Sipeed Tang Retro Console with 60K SOM",
        "programming_log",
        "reset_released",
        "heartbeat_observed",
        "pass_output_observed",
        "fail_output_observed",
        "uart_status_packet_hex",
        "probe_capture",
        "bitstream_sha256",
        "primary_138k_claim=no",
        BOARD_RESULT_SMOKE_PASS,
        BOARD_RESULT_FAILURE,
        "not claim a Tang Mega Dock with 138K SOM pass",
        "I34-S05",
        "I34-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RETRO_CONSOLE_PROGRAMMING_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"Retro Console programming objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: RetroConsoleProgrammingRecord,
    gowin_audit: fpga_retro_console_gowin.RetroConsoleGowinAudit | None,
    *,
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    observation_issues: tuple[str, ...] = (),
    packet_issues: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> RetroConsoleProgrammingAudit:
    return RetroConsoleProgrammingAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        gowin_status=gowin_audit.status if gowin_audit is not None else "not_checked",
        board_result=record.value("board_result"),
        missing_fields=missing_fields,
        link_issues=link_issues,
        observation_issues=observation_issues,
        packet_issues=packet_issues,
        actions=actions,
    )


def _link_issues(
    record: RetroConsoleProgrammingRecord,
    profile: RetroConsoleProgrammingProfile,
    gowin_audit: fpga_retro_console_gowin.RetroConsoleGowinAudit | None,
) -> list[str]:
    issues: list[str] = []
    expected_values = {
        "board": profile.board,
        "programming_mode": profile.required_mode,
        "primary_138k_claim": "no",
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            issues.append(f"{field} must be {expected}")
    if record.value("retro_console_gowin") and "i34_s03" not in record.value("retro_console_gowin").lower():
        issues.append("retro_console_gowin must reference I34-S03 evidence")
    if record.value("bitstream_path"):
        if not record.value("bitstream_path").endswith(".fs"):
            issues.append("bitstream_path must name a .fs file")
        if "tang_60k_retro_console" not in record.value("bitstream_path"):
            issues.append("bitstream_path must reference the Retro Console 60K build root")
        if "tang_mega_138k" in record.value("bitstream_path"):
            issues.append("bitstream_path must not reference the Tang Mega 138K build root")
    if gowin_audit is not None and gowin_audit.bitstreams and record.value("bitstream_path"):
        if record.value("bitstream_path") not in gowin_audit.bitstreams:
            issues.append("bitstream_path must match an I34-S03 audited bitstream")
    sha = record.value("bitstream_sha256")
    if sha and not _is_sha256_hex(sha):
        issues.append("bitstream_sha256 must be a 64-character hex digest")
    return issues


def _observation_issues(
    record: RetroConsoleProgrammingRecord,
    profile: RetroConsoleProgrammingProfile,
) -> list[str]:
    issues: list[str] = []
    if record.value("programming_result").lower() != "success":
        issues.append("programming_result must be success")
    if record.value("reset_released").lower() != "yes":
        issues.append("reset_released must be yes")
    _check_minimum_int(record, "observation_duration_s", profile.minimum_observation_seconds, issues)
    if record.value("heartbeat_observed").lower() != "yes":
        issues.append("heartbeat_observed must be yes")
    for field in ("pass_output_observed", "fail_output_observed"):
        value = record.value(field).lower()
        if value and value not in {"yes", "no"}:
            issues.append(f"{field} must be yes or no")
    board_result = record.value("board_result")
    if board_result and board_result not in {BOARD_RESULT_SMOKE_PASS, BOARD_RESULT_FAILURE}:
        issues.append("board_result must be retro_console_smoke_pass or failure_observed")
    if not _has_uart_or_probe(record):
        issues.append("UART status packet or probe_capture evidence is required")

    retire_count = _parse_int(record.value("status_retire_count"))
    fault_code = _parse_int(record.value("status_fault_code"))
    if record.value("status_retire_count") and retire_count is None:
        issues.append("status_retire_count must be numeric")
    if record.value("status_fault_code") and fault_code is None:
        issues.append("status_fault_code must be numeric")
    return issues


def _packet_consistency_issues(
    record: RetroConsoleProgrammingRecord,
    packet: fpga_debug_status.DebugStatusPacket | None,
) -> list[str]:
    if packet is None:
        return []
    issues: list[str] = []
    retire_count = _parse_int(record.value("status_retire_count"))
    fault_code = _parse_int(record.value("status_fault_code"))
    state_name = fpga_debug_status.fpga_debug_status_profile().pass_fail_states[packet.pass_fail_state]
    if record.value("pass_fail_state") and record.value("pass_fail_state") != state_name:
        issues.append("pass_fail_state must match decoded UART status packet")
    if retire_count is not None and retire_count != packet.retire_count:
        issues.append("status_retire_count must match decoded UART status packet")
    if fault_code is not None and fault_code != packet.fault_code:
        issues.append("status_fault_code must match decoded UART status packet")
    return issues


def _board_result_issues(record: RetroConsoleProgrammingRecord) -> list[str]:
    issues: list[str] = []
    board_result = record.value("board_result")
    retire_count = _parse_int(record.value("status_retire_count"))
    fault_code = _parse_int(record.value("status_fault_code"))
    if board_result == BOARD_RESULT_SMOKE_PASS:
        if record.value("pass_output_observed").lower() != "yes":
            issues.append("retro_console_smoke_pass requires pass_output_observed=yes")
        if record.value("fail_output_observed").lower() != "no":
            issues.append("retro_console_smoke_pass requires fail_output_observed=no")
        if record.value("pass_fail_state") != "first_pass":
            issues.append("retro_console_smoke_pass requires pass_fail_state=first_pass")
        if retire_count is not None and retire_count < 8:
            issues.append("retro_console_smoke_pass requires status_retire_count at least 8")
        if fault_code not in (None, 0):
            issues.append("retro_console_smoke_pass requires status_fault_code=0")
    elif board_result == BOARD_RESULT_FAILURE:
        failure_signals = (
            record.value("fail_output_observed").lower() == "yes",
            record.value("pass_fail_state") == "failed",
            fault_code is not None and fault_code != 0,
        )
        if not any(failure_signals):
            issues.append("failure_observed requires fail output, failed packet state, or nonzero fault code")
    return issues


def _decode_packet(value: str) -> tuple[fpga_debug_status.DebugStatusPacket | None, list[str]]:
    if not value or value.lower() == "none":
        return None, []
    compact = "".join(value.split())
    if len(compact) != 64:
        return None, ["uart_status_packet_hex must encode exactly 32 bytes"]
    try:
        payload = bytes.fromhex(compact)
    except ValueError:
        return None, ["uart_status_packet_hex must be hexadecimal"]
    try:
        return fpga_debug_status.decode_debug_status_packet(payload), []
    except ValueError as exc:
        return None, [f"uart_status_packet_hex did not decode as I25-S01 packet: {exc}"]


def _has_uart_or_probe(record: RetroConsoleProgrammingRecord) -> bool:
    packet = record.value("uart_status_packet_hex").strip().lower()
    uart_log = record.value("uart_log").strip().lower()
    probe = record.value("probe_capture").strip().lower()
    has_uart = packet not in {"", "none", "n/a", "na", "-", "missing"} and uart_log not in {"", "none", "n/a", "na", "-", "missing"}
    has_probe = probe not in {"", "none", "n/a", "na", "-", "missing"}
    return has_uart or has_probe


def _check_minimum_int(
    record: RetroConsoleProgrammingRecord,
    key: str,
    minimum: int,
    issues: list[str],
) -> None:
    value = record.value(key)
    if not value:
        return
    parsed = _parse_int(value)
    if parsed is None:
        issues.append(f"{key} must be numeric")
    elif parsed < minimum:
        issues.append(f"{key} must be at least {minimum}")


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

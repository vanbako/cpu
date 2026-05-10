"""First integrated CPU SRAM programming and observation evidence gate.

Owner stories:
- I31-S03: program SRAM and capture first integrated CPU observations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_debug_status,
    fpga_first_pass_gowin,
    fpga_first_test,
    fpga_probe_bundles,
    fpga_programming,
    fpga_uart_status,
)


JsonValue = Any

FPGA_FIRST_PASS_PROGRAMMING_STORY = "I31-S03"
FPGA_FIRST_PASS_PROGRAMMING_DOC = Path(
    "docs/implementation/fpga-first-pass-programming.md"
)
FPGA_FIRST_PASS_PROGRAMMING_TOOL = "python tools\\fpga_first_pass_programming.py --check"
FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE = Path(
    "docs/implementation/evidence/i31_s03_integrated_cpu_programming.txt"
)
FIRST_PASS_PROGRAMMING_PROFILE_STATUS = "blocked_until_sram_observation"
FIRST_PASS_PROGRAMMING_RESULT = "integrated_cpu_observation_captured"

OBSERVED = "observed"
BLOCKED = "blocked"
INVALID = "invalid"
NEEDS_CAPTURE = "needs_capture"

BOARD_RESULT_FIRST_PASS = "first_pass"
BOARD_RESULT_FAILURE = "failure_observed"


@dataclass(frozen=True)
class FirstPassProgrammingField:
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
class FirstPassProgrammingProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    top_module: str
    selected_image: str
    gowin_gate: str
    base_programming_gate: str
    uart_status_gate: str
    probe_gate: str
    required_mode: str
    minimum_observation_seconds: int
    required_fields: tuple[FirstPassProgrammingField, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> FirstPassProgrammingField:
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
            "top_module": self.top_module,
            "selected_image": self.selected_image,
            "gowin_gate": self.gowin_gate,
            "base_programming_gate": self.base_programming_gate,
            "uart_status_gate": self.uart_status_gate,
            "probe_gate": self.probe_gate,
            "required_mode": self.required_mode,
            "minimum_observation_seconds": self.minimum_observation_seconds,
            "required_fields": [field.as_dict() for field in self.required_fields],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstPassProgrammingRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstPassProgrammingAudit:
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


def fpga_first_pass_programming_profile() -> FirstPassProgrammingProfile:
    gowin = fpga_first_pass_gowin.fpga_first_pass_gowin_profile()
    return FirstPassProgrammingProfile(
        story=FPGA_FIRST_PASS_PROGRAMMING_STORY,
        status=FIRST_PASS_PROGRAMMING_PROFILE_STATUS,
        evidence_path=FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        top_module=gowin.top_module,
        selected_image=gowin.selected_image,
        gowin_gate=fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_TOOL,
        base_programming_gate=fpga_programming.FPGA_PROGRAMMING_TOOL,
        uart_status_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        probe_gate=fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        required_mode="SRAM",
        minimum_observation_seconds=10,
        required_fields=(
            FirstPassProgrammingField("story", True, "Must be I31-S03."),
            FirstPassProgrammingField("programmed_at", True, "Local programming timestamp."),
            FirstPassProgrammingField("repository_commit", True, "Repository commit used for the board run."),
            FirstPassProgrammingField("board", True, "Physical board name."),
            FirstPassProgrammingField("first_pass_gowin", True, "I31-S02 Gowin evidence path."),
            FirstPassProgrammingField("top_module", True, "Must be cpu_v01_fpga_top."),
            FirstPassProgrammingField("selected_image", True, "Must be builtin.first_test_pause_stream."),
            FirstPassProgrammingField("bitstream_path", True, "Exact .fs bitstream path."),
            FirstPassProgrammingField("bitstream_sha256", True, "SHA-256 of the programmed bitstream."),
            FirstPassProgrammingField("programming_tool", True, "Gowin Programmer or approved equivalent."),
            FirstPassProgrammingField("programming_mode", True, "Must be SRAM."),
            FirstPassProgrammingField("programming_result", True, "Must be success."),
            FirstPassProgrammingField("programming_log", True, "Captured programming log path."),
            FirstPassProgrammingField("reset_released", True, "yes after board reset release."),
            FirstPassProgrammingField("reset_observation", True, "Reset release log, photo, or probe path."),
            FirstPassProgrammingField("observation_duration_s", True, "Observation duration after reset release."),
            FirstPassProgrammingField("heartbeat_observed", True, "yes when heartbeat toggled."),
            FirstPassProgrammingField("pass_led_observed", True, "yes or no."),
            FirstPassProgrammingField("fail_led_observed", True, "yes or no."),
            FirstPassProgrammingField("board_result", True, "first_pass or failure_observed."),
            FirstPassProgrammingField("uart_log", True, "Raw UART/status capture log path."),
            FirstPassProgrammingField("uart_status_packet_hex", True, "Captured 32-byte I25-S01 packet hex."),
            FirstPassProgrammingField("decoded_status_packet", True, "Decoded packet record path or transcript."),
            FirstPassProgrammingField("status_retire_count", True, "Decoded retire count."),
            FirstPassProgrammingField("status_fault_code", True, "Decoded fault code."),
            FirstPassProgrammingField("pass_fail_state", True, "Decoded packet pass/fail state."),
            FirstPassProgrammingField("probe_capture", False, "Optional GAO/ILA/probe capture path or none."),
            FirstPassProgrammingField("retest_commands", True, "Commands to rerun gates and recapture evidence."),
        ),
        retest_commands=(
            fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_TOOL,
            fpga_programming.FPGA_PROGRAMMING_TOOL,
            fpga_uart_status.FPGA_UART_STATUS_TOOL,
            fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        ),
        blockers=(
            "I31-S02 Gowin evidence must pass before SRAM programming can close",
            "programming must use SRAM mode and the exact I31-S02 bitstream SHA-256",
            "reset release, heartbeat, pass/fail LEDs, and UART/status packet evidence are required",
            "failure observations must carry enough UART or probe evidence for I31-S04 replay classification",
        ),
    )


def first_pass_programming_template(
    profile: FirstPassProgrammingProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_programming_profile()
    packet = fpga_debug_status.example_debug_status_packet()
    packet_hex = fpga_debug_status.encode_debug_status_packet(packet).hex()
    retest_commands = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "programmed_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"first_pass_gowin={fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_EVIDENCE.as_posix()}",
            f"top_module={profile.top_module}",
            f"selected_image={profile.selected_image}",
            "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
            "bitstream_sha256=",
            "programming_tool=Gowin Programmer",
            "programming_mode=SRAM",
            "programming_result=success",
            "programming_log=docs/implementation/evidence/i31_s03_programming.log",
            "reset_released=yes",
            "reset_observation=docs/implementation/evidence/i31_s03_reset_release.txt",
            "observation_duration_s=10",
            "heartbeat_observed=yes",
            "pass_led_observed=yes",
            "fail_led_observed=no",
            f"board_result={BOARD_RESULT_FIRST_PASS}",
            "uart_log=docs/implementation/evidence/i31_s03_uart.log",
            f"uart_status_packet_hex={packet_hex}",
            "decoded_status_packet=docs/implementation/evidence/i31_s03_status_packet.json",
            f"status_retire_count={packet.retire_count}",
            f"status_fault_code={packet.fault_code}",
            "pass_fail_state=first_pass",
            "probe_capture=none",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_first_pass_programming(text: str) -> FirstPassProgrammingRecord:
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
    return FirstPassProgrammingRecord(fields)


def audit_first_pass_programming(
    record: FirstPassProgrammingRecord,
    *,
    gowin_audit: fpga_first_pass_gowin.FirstPassGowinAudit | None = None,
    evidence_path: str = "<inline>",
    profile: FirstPassProgrammingProfile | None = None,
) -> FirstPassProgrammingAudit:
    if profile is None:
        profile = fpga_first_pass_programming_profile()
    if gowin_audit is not None and not gowin_audit.passed:
        return FirstPassProgrammingAudit(
            status=BLOCKED,
            message="Integrated CPU programming is blocked until I31-S02 Gowin evidence passes.",
            evidence_path=evidence_path,
            gowin_status=gowin_audit.status,
            board_result=record.value("board_result"),
            missing_fields=(),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=("complete I31-S02 Gowin evidence before programming SRAM",),
        )

    required = tuple(field.name for field in profile.required_fields if field.required)
    missing_fields = [field for field in required if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I31-S03")

    link_issues: list[str] = []
    expected_values = {
        "board": profile.board,
        "top_module": profile.top_module,
        "selected_image": profile.selected_image,
        "programming_mode": profile.required_mode,
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            link_issues.append(f"{field} must be {expected}")
    if record.value("first_pass_gowin") and "i31_s02" not in record.value("first_pass_gowin").lower():
        link_issues.append("first_pass_gowin must reference I31-S02 evidence")
    if record.value("bitstream_path") and not record.value("bitstream_path").endswith(".fs"):
        link_issues.append("bitstream_path must name a .fs file")
    if gowin_audit is not None and gowin_audit.bitstreams and record.value("bitstream_path"):
        if record.value("bitstream_path") not in gowin_audit.bitstreams:
            link_issues.append("bitstream_path must match an I31-S02 audited bitstream")
    sha = record.value("bitstream_sha256")
    if sha and not _is_sha256_hex(sha):
        link_issues.append("bitstream_sha256 must be a 64-character hex digest")

    observation_issues: list[str] = []
    if record.value("programming_result").lower() != "success":
        observation_issues.append("programming_result must be success")
    if record.value("reset_released").lower() != "yes":
        observation_issues.append("reset_released must be yes")
    _check_minimum_int(record, "observation_duration_s", profile.minimum_observation_seconds, observation_issues)
    if record.value("heartbeat_observed").lower() != "yes":
        observation_issues.append("heartbeat_observed must be yes")
    for field in ("pass_led_observed", "fail_led_observed"):
        value = record.value(field).lower()
        if value and value not in {"yes", "no"}:
            observation_issues.append(f"{field} must be yes or no")
    board_result = record.value("board_result")
    if board_result and board_result not in {BOARD_RESULT_FIRST_PASS, BOARD_RESULT_FAILURE}:
        observation_issues.append("board_result must be first_pass or failure_observed")

    retire_count = _parse_int(record.value("status_retire_count"))
    fault_code = _parse_int(record.value("status_fault_code"))
    if record.value("status_retire_count") and retire_count is None:
        observation_issues.append("status_retire_count must be numeric")
    if record.value("status_fault_code") and fault_code is None:
        observation_issues.append("status_fault_code must be numeric")

    packet, packet_issues = _decode_packet(record.value("uart_status_packet_hex"))
    if packet is not None:
        state_name = fpga_debug_status.fpga_debug_status_profile().pass_fail_states[packet.pass_fail_state]
        if record.value("pass_fail_state") and record.value("pass_fail_state") != state_name:
            packet_issues.append("pass_fail_state must match decoded UART status packet")
        if retire_count is not None and retire_count != packet.retire_count:
            packet_issues.append("status_retire_count must match decoded UART status packet")
        if fault_code is not None and fault_code != packet.fault_code:
            packet_issues.append("status_fault_code must match decoded UART status packet")

    if board_result == BOARD_RESULT_FIRST_PASS:
        if record.value("pass_led_observed").lower() != "yes":
            observation_issues.append("first_pass requires pass_led_observed=yes")
        if record.value("fail_led_observed").lower() != "no":
            observation_issues.append("first_pass requires fail_led_observed=no")
        if record.value("pass_fail_state") != "first_pass":
            observation_issues.append("first_pass requires pass_fail_state=first_pass")
        if retire_count is not None and retire_count < 8:
            observation_issues.append("first_pass requires status_retire_count at least 8")
        if fault_code not in (None, 0):
            observation_issues.append("first_pass requires status_fault_code=0")
    elif board_result == BOARD_RESULT_FAILURE:
        failure_signals = (
            record.value("fail_led_observed").lower() == "yes",
            record.value("pass_fail_state") == "failed",
            fault_code is not None and fault_code != 0,
        )
        if not any(failure_signals):
            observation_issues.append("failure_observed requires fail LED, failed packet state, or nonzero fault code")

    if missing_fields:
        return FirstPassProgrammingAudit(
            status=INVALID,
            message="Integrated CPU programming evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            gowin_status=gowin_audit.status if gowin_audit is not None else "not_checked",
            board_result=board_result,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            observation_issues=tuple(observation_issues),
            packet_issues=tuple(packet_issues),
            actions=("complete all required programming observation fields", "rerun the I31-S03 audit"),
        )
    if link_issues or packet_issues:
        return FirstPassProgrammingAudit(
            status=INVALID,
            message="Integrated CPU programming evidence links or UART packet are invalid.",
            evidence_path=evidence_path,
            gowin_status=gowin_audit.status if gowin_audit is not None else "not_checked",
            board_result=board_result,
            missing_fields=(),
            link_issues=tuple(link_issues),
            observation_issues=tuple(observation_issues),
            packet_issues=tuple(packet_issues),
            actions=("fix bitstream identity, evidence links, or UART packet decode",),
        )
    if observation_issues:
        return FirstPassProgrammingAudit(
            status=NEEDS_CAPTURE,
            message="Integrated CPU programming needs more complete board observation evidence.",
            evidence_path=evidence_path,
            gowin_status=gowin_audit.status if gowin_audit is not None else "not_checked",
            board_result=board_result,
            missing_fields=(),
            link_issues=(),
            observation_issues=tuple(observation_issues),
            packet_issues=(),
            actions=("recapture reset, LED, UART, or probe observations",),
        )

    actions = (
        ("hand the failure capture to I31-S04 replay classification",)
        if board_result == BOARD_RESULT_FAILURE
        else ("hand the first-pass observation to I31-S05 archive evidence",)
    )
    return FirstPassProgrammingAudit(
        status=OBSERVED,
        message="Integrated CPU SRAM programming and observation evidence is captured.",
        evidence_path=evidence_path,
        gowin_status=gowin_audit.status if gowin_audit is not None else "not_checked",
        board_result=board_result,
        missing_fields=(),
        link_issues=(),
        observation_issues=(),
        packet_issues=(),
        actions=actions,
    )


def load_first_pass_programming_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    gowin_evidence_path: Path | None = None,
) -> FirstPassProgrammingAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_programming_profile()
    relative_path = evidence_path or profile.evidence_path
    gowin_audit = fpga_first_pass_gowin.load_first_pass_gowin_audit(root, gowin_evidence_path)
    path = root / relative_path
    if not path.exists():
        return FirstPassProgrammingAudit(
            status=BLOCKED,
            message="No integrated CPU SRAM programming observation has been captured yet.",
            evidence_path=relative_path.as_posix(),
            gowin_status=gowin_audit.status,
            board_result="",
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the programming template",
                "capture programming log, reset release, LEDs, UART packet, and optional probes",
            ),
        )
    try:
        record = parse_first_pass_programming(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return FirstPassProgrammingAudit(
            status=INVALID,
            message="Integrated CPU programming evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            gowin_status=gowin_audit.status,
            board_result="",
            missing_fields=(str(exc),),
            link_issues=(),
            observation_issues=(),
            packet_issues=(),
            actions=("fix the key=value evidence record", "rerun the I31-S03 audit"),
        )
    return audit_first_pass_programming(
        record,
        gowin_audit=gowin_audit,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_first_pass_programming_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_programming_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_programming(
    profile: FirstPassProgrammingProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_programming_profile()
    lines = [
        "# FPGA First-Pass Programming",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Top module: `{profile.top_module}`",
        f"Selected image: `{profile.selected_image}`",
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


def validate_fpga_first_pass_programming(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_programming_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_PROGRAMMING_STORY:
        issues.append(f"first-pass programming story must be {FPGA_FIRST_PASS_PROGRAMMING_STORY}")
    if profile.status != FIRST_PASS_PROGRAMMING_PROFILE_STATUS:
        issues.append("first-pass programming profile must remain blocked until board observation exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("first-pass programming board must match first-test target")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("first-pass programming top must be cpu_v01_fpga_top")
    if profile.required_mode != "SRAM":
        issues.append("first-pass programming must require SRAM mode")
    if profile.minimum_observation_seconds < 10:
        issues.append("first-pass programming observation duration must be at least 10 seconds")
    if profile.gowin_gate != fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_TOOL:
        issues.append("first-pass programming must depend on I31-S02")
    if profile.base_programming_gate != fpga_programming.FPGA_PROGRAMMING_TOOL:
        issues.append("first-pass programming must reuse I24-S04 programming policy")
    if profile.uart_status_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("first-pass programming must depend on I25-S02 UART status")
    if profile.probe_gate != fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL:
        issues.append("first-pass programming must reference I25-S03 probe bundles")

    for check_issues in (
        fpga_first_pass_gowin.validate_fpga_first_pass_gowin(root),
        fpga_programming.validate_fpga_programming(root),
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
        "first_pass_gowin",
        "bitstream_path",
        "bitstream_sha256",
        "programming_log",
        "reset_released",
        "reset_observation",
        "heartbeat_observed",
        "pass_led_observed",
        "fail_led_observed",
        "board_result",
        "uart_log",
        "uart_status_packet_hex",
        "decoded_status_packet",
        "status_retire_count",
        "status_fault_code",
        "pass_fail_state",
        "retest_commands",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing first-pass programming field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    if fields.get("probe_capture") and fields["probe_capture"].required:
        issues.append("probe_capture must remain optional")

    passed_gowin = fpga_first_pass_gowin.FirstPassGowinAudit(
        status=fpga_first_pass_gowin.GOWIN_PASS,
        message="passed",
        evidence_path=fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_EVIDENCE.as_posix(),
        bundle_status=fpga_first_pass_gowin.fpga_first_pass_bundle.BUNDLE_FROZEN,
        report_status=fpga_first_pass_gowin.fpga_gowin_reports.GOWIN_REPORTS_PASSED,
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=("build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",),
        actions=(),
    )
    complete_record = parse_first_pass_programming(
        first_pass_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
    )
    if not audit_first_pass_programming(complete_record, gowin_audit=passed_gowin).passed:
        issues.append("complete first-pass programming evidence must audit as observed")

    bad_packet = parse_first_pass_programming(
        first_pass_programming_template()
        .replace("programmed_at=", "programmed_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("uart_status_packet_hex=", "uart_status_packet_hex=bad")
    )
    if audit_first_pass_programming(bad_packet, gowin_audit=passed_gowin).status != INVALID:
        issues.append("malformed UART status packet must invalidate first-pass programming evidence")

    default_audit = load_first_pass_programming_audit(root)
    if default_audit.status != BLOCKED:
        issues.append("default first-pass programming audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_PROGRAMMING_DOC)
    for token in (
        "Story: I31-S03",
        FPGA_FIRST_PASS_PROGRAMMING_TOOL,
        FPGA_FIRST_PASS_PROGRAMMING_EVIDENCE.as_posix(),
        fpga_first_pass_gowin.FPGA_FIRST_PASS_GOWIN_TOOL,
        fpga_programming.FPGA_PROGRAMMING_TOOL,
        fpga_uart_status.FPGA_UART_STATUS_TOOL,
        fpga_probe_bundles.FPGA_PROBE_BUNDLES_TOOL,
        "programming_log",
        "reset_released",
        "heartbeat_observed",
        "pass_led_observed",
        "fail_led_observed",
        "uart_status_packet_hex",
        "decoded_status_packet",
        "probe_capture",
        "bitstream_sha256",
        "first_pass",
        "failure_observed",
        "I31-S04",
        "I31-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_PROGRAMMING_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass programming objects are not JSON serializable: {exc}")

    return tuple(issues)


def _decode_packet(value: str) -> tuple[fpga_debug_status.DebugStatusPacket | None, list[str]]:
    if not value:
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


def _check_minimum_int(
    record: FirstPassProgrammingRecord,
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

"""Tang 138K Retro Console first-target identity gate.

Owner stories:
- I34-S01: verify Retro Console identity and select it as first physical CPU target.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test


JsonValue = Any

FPGA_RETRO_CONSOLE_IDENTITY_STORY = "I34-S01"
FPGA_RETRO_CONSOLE_IDENTITY_DOC = Path(
    "docs/implementation/fpga-retro-console-identity.md"
)
FPGA_RETRO_CONSOLE_IDENTITY_TOOL = "python tools\\fpga_retro_console_identity.py --check"
FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE = Path(
    "docs/implementation/evidence/i34_s01_retro_console_identity.txt"
)
FPGA_RETRO_CONSOLE_BOARD = "Sipeed Tang 138K Retro Console"
RETRO_CONSOLE_SELECTION_STATUS = "retro_console_selected_pending_scan"

AUDIT_STATUS_SELECTED = "selected_first_target"
AUDIT_STATUS_BLOCKED = "blocked"
AUDIT_STATUS_INVALID = "invalid"

FIRST_TEST_PROFILE_GATE = "python tools\\fpga_first_test_profile.py --check"
BOARD_BRINGUP_RUNBOOK_GATE = (
    "python -m unittest tests.conformance.test_i23_s06_fpga_board_bringup"
)


@dataclass(frozen=True)
class RetroConsoleEvidenceField:
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
class RetroConsoleInterface:
    name: str
    required: bool
    evidence: str
    blocker_if_missing: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "evidence": self.evidence,
            "blocker_if_missing": self.blocker_if_missing,
        }


@dataclass(frozen=True)
class RetroConsoleIdentityProfile:
    story: str
    status: str
    board: str
    previous_first_board: str
    selected_first_target: bool
    selection_reason: str
    first_test_profile_gate: str
    board_bringup_runbook_gate: str
    evidence_path: Path
    required_fields: tuple[RetroConsoleEvidenceField, ...]
    programming_paths: tuple[RetroConsoleInterface, ...]
    clock_reset_sources: tuple[RetroConsoleInterface, ...]
    visible_outputs: tuple[RetroConsoleInterface, ...]
    debug_access: tuple[RetroConsoleInterface, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "previous_first_board": self.previous_first_board,
            "selected_first_target": self.selected_first_target,
            "selection_reason": self.selection_reason,
            "first_test_profile_gate": self.first_test_profile_gate,
            "board_bringup_runbook_gate": self.board_bringup_runbook_gate,
            "evidence_path": self.evidence_path.as_posix(),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "programming_paths": [item.as_dict() for item in self.programming_paths],
            "clock_reset_sources": [item.as_dict() for item in self.clock_reset_sources],
            "visible_outputs": [item.as_dict() for item in self.visible_outputs],
            "debug_access": [item.as_dict() for item in self.debug_access],
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class RetroConsoleIdentityRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RetroConsoleIdentityAudit:
    status: str
    message: str
    evidence_path: str
    observed_device: str
    observed_package: str
    observed_device_version: str
    gowin_part: str
    programming_path: str
    selected_first_target: str
    issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def selected(self) -> bool:
        return self.status == AUDIT_STATUS_SELECTED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "observed_device": self.observed_device,
            "observed_package": self.observed_package,
            "observed_device_version": self.observed_device_version,
            "gowin_part": self.gowin_part,
            "programming_path": self.programming_path,
            "selected_first_target": self.selected_first_target,
            "issues": list(self.issues),
            "actions": list(self.actions),
        }


def retro_console_identity_profile() -> RetroConsoleIdentityProfile:
    return RetroConsoleIdentityProfile(
        story=FPGA_RETRO_CONSOLE_IDENTITY_STORY,
        status=RETRO_CONSOLE_SELECTION_STATUS,
        board=FPGA_RETRO_CONSOLE_BOARD,
        previous_first_board=fpga_first_test.TARGET_BOARD_NAME,
        selected_first_target=True,
        selection_reason=(
            "Use the available Tang 138K Retro Console before the Tang Mega 138K Dock, "
            "while keeping the Dock path as a fallback board target."
        ),
        first_test_profile_gate=FIRST_TEST_PROFILE_GATE,
        board_bringup_runbook_gate=BOARD_BRINGUP_RUNBOOK_GATE,
        evidence_path=FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE,
        required_fields=(
            RetroConsoleEvidenceField(
                "story",
                True,
                "Must be I34-S01 so this record cannot be reused for the Dock identity gate.",
            ),
            RetroConsoleEvidenceField(
                "board",
                True,
                "Human-readable board name from the Retro Console board under test.",
            ),
            RetroConsoleEvidenceField(
                "source",
                True,
                "board_marking, programmer_jtag_scan, vendor_schematic, or a combination.",
            ),
            RetroConsoleEvidenceField(
                "observed_device",
                True,
                "Exact FPGA device string from marking, vendor file, or programmer scan.",
            ),
            RetroConsoleEvidenceField(
                "observed_package",
                True,
                "Exact package string from marking, vendor file, or programmer scan.",
            ),
            RetroConsoleEvidenceField(
                "observed_device_version",
                True,
                "Gowin Device Version selected for the build, normally B or C.",
            ),
            RetroConsoleEvidenceField(
                "gowin_part",
                True,
                "The full Gowin target part/package string to hand to I34-S02/I34-S03.",
            ),
            RetroConsoleEvidenceField(
                "programming_path",
                True,
                "SRAM programming route, cable, and tool used or planned for this board.",
            ),
            RetroConsoleEvidenceField(
                "clock_sources",
                True,
                "Verified board clock source names and frequencies visible to constraints.",
            ),
            RetroConsoleEvidenceField(
                "reset_sources",
                True,
                "Reset button, power-on reset, or other reset source selected for first test.",
            ),
            RetroConsoleEvidenceField(
                "visible_outputs",
                True,
                "LED, display, PMOD, or probe pins available for pass/fail/heartbeat.",
            ),
            RetroConsoleEvidenceField(
                "uart_debug_access",
                True,
                "UART/JTAG/debug path available for status packets or monitor traffic.",
            ),
            RetroConsoleEvidenceField(
                "selected_first_target",
                True,
                "Must be yes to record the Retro Console as the active first physical CPU target.",
            ),
            RetroConsoleEvidenceField(
                "supersedes_board",
                True,
                "Must name the Tang Mega 138K Dock as the board being deferred.",
            ),
            RetroConsoleEvidenceField(
                "observed_tool",
                True,
                "Tool or physical method used to capture the identity evidence.",
            ),
            RetroConsoleEvidenceField(
                "observed_at",
                True,
                "Local date/time when the board identity was captured.",
            ),
            RetroConsoleEvidenceField(
                "evidence_notes",
                False,
                "Photo, screenshot, raw scan log path, or pinout caveats.",
            ),
        ),
        programming_paths=(
            RetroConsoleInterface(
                "gowin_programmer_sram",
                True,
                "Gowin Programmer can see the Retro Console FPGA and accepts SRAM programming.",
                "I34-S04 cannot start without a verified SRAM programming path.",
            ),
            RetroConsoleInterface(
                "openfpgaloader_detect",
                False,
                "Optional independent JTAG detect output when cable support is available.",
                "Use Gowin Programmer evidence if openFPGALoader does not support the board.",
            ),
        ),
        clock_reset_sources=(
            RetroConsoleInterface(
                "clock_sources",
                True,
                "Named oscillator or board clock frequency to constrain in I34-S02.",
                "Do not create the Retro Console SDC until clock source and frequency are known.",
            ),
            RetroConsoleInterface(
                "reset_sources",
                True,
                "Reset button, power-on reset, or selected input that can release cpu_v01_fpga_top.",
                "Do not assume board_reset_n_i from the Dock constraints.",
            ),
        ),
        visible_outputs=(
            RetroConsoleInterface(
                "heartbeat_output",
                True,
                "A physical LED, display element, PMOD pin, or probe signal for heartbeat.",
                "I34-S04 needs at least heartbeat visibility to distinguish reset from CPU failure.",
            ),
            RetroConsoleInterface(
                "pass_fail_outputs",
                True,
                "Physical LED, display element, PMOD pins, or probes for pass and fail status.",
                "I34-S02 must map pass/fail without assuming Dock LED names.",
            ),
        ),
        debug_access=(
            RetroConsoleInterface(
                "uart_status",
                True,
                "UART, USB-UART, JTAG UART, or equivalent status path for packets/logs.",
                "I32 monitor work cannot run on the board without an audited status path.",
            ),
            RetroConsoleInterface(
                "probe_or_ila",
                False,
                "Optional GAO/ILA or external probe path for first-failure captures.",
                "I34-S05 can use UART replay data if probes are unavailable.",
            ),
        ),
        blockers=(
            "actual Retro Console device/package has not been captured in repository evidence",
            "I34-S02 must not assume Tang Mega 138K Dock pin names or package details",
            "I31/I32 board evidence should prefer Retro Console only after this audit is selected",
        ),
        handoffs=(
            "I34-S02 consumes observed device/package, clock/reset, visible output, and UART/debug fields",
            "I34-S03 consumes the Gowin part and programming target from this evidence",
            "I34-S06 decides whether I31/I32 continue on Retro Console first or fall back to the Dock",
        ),
    )


def identity_template(profile: RetroConsoleIdentityProfile | None = None) -> str:
    if profile is None:
        profile = retro_console_identity_profile()
    return "\n".join(
        (
            f"story={profile.story}",
            f"board={profile.board}",
            "source=",
            "observed_device=",
            "observed_package=",
            "observed_device_version=",
            "gowin_part=",
            "programming_path=",
            "clock_sources=",
            "reset_sources=",
            "visible_outputs=",
            "uart_debug_access=",
            "selected_first_target=yes",
            f"supersedes_board={profile.previous_first_board}",
            "observed_tool=",
            "observed_at=",
            "evidence_notes=",
            "",
        )
    )


def parse_identity_record(text: str) -> RetroConsoleIdentityRecord:
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
    return RetroConsoleIdentityRecord(fields)


def audit_identity_record(
    record: RetroConsoleIdentityRecord,
    *,
    evidence_path: str = "<inline>",
    profile: RetroConsoleIdentityProfile | None = None,
) -> RetroConsoleIdentityAudit:
    if profile is None:
        profile = retro_console_identity_profile()
    issues: list[str] = []

    for field in profile.required_fields:
        if field.required and not record.value(field.name):
            issues.append(f"missing required field {field.name}")

    if record.value("story") and record.value("story") != profile.story:
        issues.append(f"story must be {profile.story}")
    if record.value("board") and record.value("board") != profile.board:
        issues.append(f"board must be {profile.board}")
    if record.value("selected_first_target").lower() not in {"yes", "true", "1"}:
        issues.append("selected_first_target must be yes")
    if profile.previous_first_board not in record.value("supersedes_board"):
        issues.append(f"supersedes_board must name {profile.previous_first_board}")

    observed_device = record.value("observed_device")
    observed_package = record.value("observed_package")
    observed_device_version = record.value("observed_device_version")
    gowin_part = record.value("gowin_part")
    programming_path = record.value("programming_path")
    selected_first_target = record.value("selected_first_target")

    if issues:
        return RetroConsoleIdentityAudit(
            status=AUDIT_STATUS_INVALID,
            message="Retro Console identity record is incomplete or malformed.",
            evidence_path=evidence_path,
            observed_device=observed_device,
            observed_package=observed_package,
            observed_device_version=observed_device_version,
            gowin_part=gowin_part,
            programming_path=programming_path,
            selected_first_target=selected_first_target,
            issues=tuple(issues),
            actions=(
                "capture Retro Console board marking or programmer scan again",
                "fill every required first-target handoff field",
                "rerun python tools\\fpga_retro_console_identity.py --audit-evidence",
            ),
        )

    return RetroConsoleIdentityAudit(
        status=AUDIT_STATUS_SELECTED,
        message="Retro Console identity is complete enough to start I34-S02 constraints.",
        evidence_path=evidence_path,
        observed_device=observed_device,
        observed_package=observed_package,
        observed_device_version=observed_device_version,
        gowin_part=gowin_part,
        programming_path=programming_path,
        selected_first_target=selected_first_target,
        issues=(),
        actions=(
            "use this record as the I34-S02 CST/SDC source of truth",
            "carry gowin_part and programming_path into I34-S03/I34-S04 evidence",
            "keep the Tang Mega 138K Dock path as fallback until I34-S06 archive closes",
        ),
    )


def load_identity_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> RetroConsoleIdentityAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = retro_console_identity_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return RetroConsoleIdentityAudit(
            status=AUDIT_STATUS_BLOCKED,
            message="No Retro Console identity evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            observed_device="",
            observed_package="",
            observed_device_version="",
            gowin_part="",
            programming_path="",
            selected_first_target="",
            issues=("missing Retro Console board marking or programmer scan evidence",),
            actions=(
                f"create {relative_path.as_posix()} from the identity template",
                "record board marking, programmer scan, clock/reset, outputs, and debug access",
                "rerun python tools\\fpga_retro_console_identity.py --audit-evidence",
            ),
        )
    try:
        record = parse_identity_record(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return RetroConsoleIdentityAudit(
            status=AUDIT_STATUS_INVALID,
            message="Retro Console identity record could not be parsed.",
            evidence_path=relative_path.as_posix(),
            observed_device="",
            observed_package="",
            observed_device_version="",
            gowin_part="",
            programming_path="",
            selected_first_target="",
            issues=(str(exc),),
            actions=("fix the key=value evidence record", "rerun the identity audit"),
        )
    return audit_identity_record(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_retro_console_identity_json(*, indent: int = 2) -> str:
    return json.dumps(
        retro_console_identity_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_retro_console_identity(
    profile: RetroConsoleIdentityProfile | None = None,
) -> str:
    if profile is None:
        profile = retro_console_identity_profile()
    lines = [
        "# FPGA Retro Console Identity",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Board: `{profile.board}`",
        f"Previous first board: `{profile.previous_first_board}`",
        f"Selected first target: `{profile.selected_first_target}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"First-test profile gate: `{profile.first_test_profile_gate}`",
        f"Board bring-up runbook gate: `{profile.board_bringup_runbook_gate}`",
        "",
        "## Required Evidence Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |"
        )
    lines.extend(["", "## Programming Paths", ""])
    lines.extend(_render_interface_table(profile.programming_paths))
    lines.extend(["", "## Clock And Reset", ""])
    lines.extend(_render_interface_table(profile.clock_reset_sources))
    lines.extend(["", "## Visible Outputs", ""])
    lines.extend(_render_interface_table(profile.visible_outputs))
    lines.extend(["", "## Debug Access", ""])
    lines.extend(_render_interface_table(profile.debug_access))
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_retro_console_identity(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = retro_console_identity_profile()
    issues: list[str] = []

    if profile.story != FPGA_RETRO_CONSOLE_IDENTITY_STORY:
        issues.append(f"Retro Console identity story must be {FPGA_RETRO_CONSOLE_IDENTITY_STORY}")
    if profile.status != RETRO_CONSOLE_SELECTION_STATUS:
        issues.append("Retro Console identity status must remain pending-scan selection")
    if profile.board != FPGA_RETRO_CONSOLE_BOARD:
        issues.append(f"Retro Console board must be {FPGA_RETRO_CONSOLE_BOARD}")
    if profile.previous_first_board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("Retro Console identity must preserve the current Dock board as fallback")
    if not profile.selected_first_target:
        issues.append("Retro Console must be selected as the active first target")
    if "before the Tang Mega 138K Dock" not in profile.selection_reason:
        issues.append("selection reason must record Retro Console before Dock")
    if profile.first_test_profile_gate != FIRST_TEST_PROFILE_GATE:
        issues.append("Retro Console identity must name the first-test profile gate")
    if profile.board_bringup_runbook_gate != BOARD_BRINGUP_RUNBOOK_GATE:
        issues.append("Retro Console identity must name the I23-S06 bring-up gate")

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "board",
        "source",
        "observed_device",
        "observed_package",
        "observed_device_version",
        "gowin_part",
        "programming_path",
        "clock_sources",
        "reset_sources",
        "visible_outputs",
        "uart_debug_access",
        "selected_first_target",
        "supersedes_board",
        "observed_tool",
        "observed_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing Retro Console evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    template = identity_template(profile)
    for token in (
        "story=I34-S01",
        f"board={FPGA_RETRO_CONSOLE_BOARD}",
        "selected_first_target=yes",
        f"supersedes_board={fpga_first_test.TARGET_BOARD_NAME}",
        "gowin_part=",
        "clock_sources=",
        "visible_outputs=",
        "uart_debug_access=",
    ):
        if token not in template:
            issues.append(f"identity template missing {token}")

    selected_record = parse_identity_record(
        "\n".join(
            (
                f"story={FPGA_RETRO_CONSOLE_IDENTITY_STORY}",
                f"board={FPGA_RETRO_CONSOLE_BOARD}",
                "source=board_marking+programmer_jtag_scan",
                "observed_device=scan_recorded_device",
                "observed_package=scan_recorded_package",
                "observed_device_version=B",
                "gowin_part=scan_recorded_gowin_part",
                "programming_path=Gowin Programmer SRAM",
                "clock_sources=verified oscillator from Retro Console evidence",
                "reset_sources=verified reset input from Retro Console evidence",
                "visible_outputs=heartbeat/pass/fail mapped to verified Retro Console outputs",
                "uart_debug_access=verified UART or JTAG status path",
                "selected_first_target=yes",
                f"supersedes_board={fpga_first_test.TARGET_BOARD_NAME}",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-11T00:00:00",
            )
        )
    )
    if not audit_identity_record(selected_record).selected:
        issues.append("complete Retro Console identity record must audit as selected")

    invalid_record = parse_identity_record(
        "\n".join(
            (
                f"story={FPGA_RETRO_CONSOLE_IDENTITY_STORY}",
                f"board={FPGA_RETRO_CONSOLE_BOARD}",
                "source=board_marking",
                "selected_first_target=no",
            )
        )
    )
    if audit_identity_record(invalid_record).status != AUDIT_STATUS_INVALID:
        issues.append("incomplete or unselected Retro Console record must be invalid")

    missing_audit = load_identity_audit(root)
    if missing_audit.status not in (
        AUDIT_STATUS_BLOCKED,
        AUDIT_STATUS_SELECTED,
        AUDIT_STATUS_INVALID,
    ):
        issues.append("Retro Console evidence audit returned an unknown status")

    for collection_name, collection, required in (
        ("programming_paths", profile.programming_paths, ("gowin_programmer_sram",)),
        ("clock_reset_sources", profile.clock_reset_sources, ("clock_sources", "reset_sources")),
        ("visible_outputs", profile.visible_outputs, ("heartbeat_output", "pass_fail_outputs")),
        ("debug_access", profile.debug_access, ("uart_status",)),
    ):
        names = {item.name for item in collection}
        for required_name in required:
            if required_name not in names:
                issues.append(f"{collection_name} missing {required_name}")

    doc = _read_if_exists(root / FPGA_RETRO_CONSOLE_IDENTITY_DOC)
    for token in (
        "Story: I34-S01",
        FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix(),
        FPGA_RETRO_CONSOLE_BOARD,
        fpga_first_test.TARGET_BOARD_NAME,
        FIRST_TEST_PROFILE_GATE,
        BOARD_BRINGUP_RUNBOOK_GATE,
        "selected_first_target=yes",
        "supersedes_board=Sipeed Tang Mega 138K Dock",
        "observed_device",
        "observed_package",
        "gowin_part",
        "programming_path",
        "clock_sources",
        "reset_sources",
        "visible_outputs",
        "uart_debug_access",
        "Gowin Programmer SRAM",
        "do not assume Dock pin names",
        "I34-S02",
        "I34-S06",
        "blocked",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RETRO_CONSOLE_IDENTITY_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _render_interface_table(items: tuple[RetroConsoleInterface, ...]) -> list[str]:
    lines = [
        "| Name | Required | Evidence | Blocker if missing |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| `{item.name}` | {'yes' if item.required else 'no'} | "
            f"{item.evidence} | {item.blocker_if_missing} |"
        )
    return lines


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

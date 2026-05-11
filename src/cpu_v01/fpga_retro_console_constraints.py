"""Tang Retro Console 60K SOM constraint overlay profile.

Owner stories:
- I34-S02: create the Retro Console CST/SDC overlay.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_retro_console_identity


JsonValue = Any

FPGA_RETRO_CONSOLE_CONSTRAINTS_STORY = "I34-S02"
FPGA_RETRO_CONSOLE_CONSTRAINTS_DOC = Path(
    "docs/implementation/fpga-retro-console-constraints.md"
)
FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL = (
    "python tools\\fpga_retro_console_constraints.py --check"
)
RETRO_CONSOLE_CST_PATH = Path("constraints/tang_60k_retro_console_first_test.cst")
RETRO_CONSOLE_CST_TEMPLATE = Path(
    "constraints/tang_60k_retro_console_first_test.cst.template"
)
RETRO_CONSOLE_SDC_PATH = Path("constraints/tang_60k_retro_console_first_test.sdc")
RETRO_CONSOLE_SDC_TEMPLATE = Path(
    "constraints/tang_60k_retro_console_first_test.sdc.template"
)
RETRO_CONSOLE_CONSTRAINT_EVIDENCE = Path(
    "docs/implementation/evidence/i34_s02_retro_console_pins.txt"
)

CONSTRAINT_CONFIRMED_STATUS = "confirmed"
CONSTRAINT_BLOCKED_STATUS = "blocked"
CONSTRAINT_INVALID_STATUS = "invalid"


@dataclass(frozen=True)
class RetroConstraintSignal:
    name: str
    direction: str
    required: bool
    evidence_key: str
    io_standard: str
    polarity: str
    purpose: str

    @property
    def placeholder(self) -> str:
        return f"I34_S02_PIN_{self.name.upper()}"

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "required": self.required,
            "evidence_key": self.evidence_key,
            "io_standard": self.io_standard,
            "polarity": self.polarity,
            "placeholder": self.placeholder,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class RetroConstraintEvidenceField:
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
class RetroConsoleConstraintsOverlay:
    story: str
    board: str
    identity_gate: str
    cst_path: Path
    cst_template_path: Path
    sdc_path: Path
    sdc_template_path: Path
    evidence_path: Path
    clock_period_placeholder: str
    signals: tuple[RetroConstraintSignal, ...]
    evidence_fields: tuple[RetroConstraintEvidenceField, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "identity_gate": self.identity_gate,
            "cst_path": self.cst_path.as_posix(),
            "cst_template_path": self.cst_template_path.as_posix(),
            "sdc_path": self.sdc_path.as_posix(),
            "sdc_template_path": self.sdc_template_path.as_posix(),
            "evidence_path": self.evidence_path.as_posix(),
            "clock_period_placeholder": self.clock_period_placeholder,
            "signals": [signal.as_dict() for signal in self.signals],
            "evidence_fields": [field.as_dict() for field in self.evidence_fields],
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class RetroConstraintEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RetroConstraintAudit:
    status: str
    message: str
    evidence_path: str
    identity_status: str
    missing_fields: tuple[str, ...]
    missing_pins: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def confirmed(self) -> bool:
        return self.status == CONSTRAINT_CONFIRMED_STATUS

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "identity_status": self.identity_status,
            "missing_fields": list(self.missing_fields),
            "missing_pins": list(self.missing_pins),
            "actions": list(self.actions),
        }


def retro_console_constraints_overlay() -> RetroConsoleConstraintsOverlay:
    return RetroConsoleConstraintsOverlay(
        story=FPGA_RETRO_CONSOLE_CONSTRAINTS_STORY,
        board=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD,
        identity_gate=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        cst_path=RETRO_CONSOLE_CST_PATH,
        cst_template_path=RETRO_CONSOLE_CST_TEMPLATE,
        sdc_path=RETRO_CONSOLE_SDC_PATH,
        sdc_template_path=RETRO_CONSOLE_SDC_TEMPLATE,
        evidence_path=RETRO_CONSOLE_CONSTRAINT_EVIDENCE,
        clock_period_placeholder="I34_S02_BOARD_CLK_PERIOD_NS",
        signals=(
            RetroConstraintSignal(
                "board_clk_i",
                "input",
                True,
                "board_clk_i_pin",
                "LVCMOS33_or_recorded",
                "free_running",
                "Verified Retro Console clock input for cpu_v01_fpga_top.",
            ),
            RetroConstraintSignal(
                "board_reset_n_i",
                "input",
                True,
                "board_reset_n_i_pin",
                "LVCMOS33_or_recorded",
                "active_low_or_recorded",
                "Verified reset or user input synchronized by cpu_v01_fpga_top.",
            ),
            RetroConstraintSignal(
                "pass_led_o",
                "output",
                True,
                "pass_led_o_pin",
                "LVCMOS33_or_recorded",
                "recorded_in_evidence",
                "Visible first-test pass output.",
            ),
            RetroConstraintSignal(
                "fail_led_o",
                "output",
                True,
                "fail_led_o_pin",
                "LVCMOS33_or_recorded",
                "recorded_in_evidence",
                "Visible first-test fail output.",
            ),
            RetroConstraintSignal(
                "heartbeat_led_o",
                "output",
                True,
                "heartbeat_led_o_pin",
                "LVCMOS33_or_recorded",
                "recorded_in_evidence",
                "Visible clock/reset/retire heartbeat output.",
            ),
            RetroConstraintSignal(
                "uart_tx_o",
                "output",
                True,
                "uart_tx_o_pin",
                "LVCMOS33_or_recorded",
                "idle_high_8n1_or_recorded",
                "UART status packet stream from the CPU board shell.",
            ),
        ),
        evidence_fields=(
            RetroConstraintEvidenceField("story", True, "Must be I34-S02."),
            RetroConstraintEvidenceField(
                "identity_evidence",
                True,
                "Path to the selected I34-S01 Retro Console identity evidence.",
            ),
            RetroConstraintEvidenceField(
                "source_constraints",
                True,
                "Retro Console schematic, pin spreadsheet, vendor constraints, or scan source.",
            ),
            RetroConstraintEvidenceField(
                "verified_by",
                True,
                "Person or process that checked each signal-to-pin mapping.",
            ),
            RetroConstraintEvidenceField(
                "verified_at",
                True,
                "Local date/time when pins, IO standards, and conflicts were checked.",
            ),
            RetroConstraintEvidenceField(
                "io_voltage",
                True,
                "IO voltage or IO standard for the selected bank and pins.",
            ),
            RetroConstraintEvidenceField(
                "led_polarity",
                True,
                "Observed or documented polarity for pass/fail/heartbeat outputs.",
            ),
            RetroConstraintEvidenceField(
                "uart_debug_mode",
                True,
                "UART/JTAG/debug transport mode used for status output.",
            ),
            RetroConstraintEvidenceField(
                "pin_conflicts",
                True,
                "Known board-function conflicts for every selected pin, or none.",
            ),
            RetroConstraintEvidenceField(
                "board_clk_i_clock_period_ns",
                True,
                "Clock period derived from the verified Retro Console clock source.",
            ),
        ),
        blockers=(
            "I34-S01 60K identity evidence must audit as alternate-target verified before pins can be accepted",
            "final CST and SDC files must not be created while placeholder tokens remain",
            "Retro Console pins must come from board evidence, not Tang Mega Dock with 138K SOM names",
        ),
        handoffs=(
            "I34-S03 consumes the final CST/SDC paths after confirmed evidence",
            "I34-S04 consumes LED, reset, and UART pin choices for board programming",
            "I34-S05 consumes UART/probe pin choices for replayable failure capture",
        ),
    )


def constraint_evidence_template(
    overlay: RetroConsoleConstraintsOverlay | None = None,
) -> str:
    if overlay is None:
        overlay = retro_console_constraints_overlay()
    lines = [
        f"story={overlay.story}",
        f"identity_evidence={fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix()}",
        "source_constraints=",
        "verified_by=",
        "verified_at=",
        "io_voltage=",
        "led_polarity=",
        "uart_debug_mode=",
        "pin_conflicts=",
    ]
    lines.extend(f"{signal.evidence_key}=" for signal in overlay.signals)
    lines.extend(("board_clk_i_clock_period_ns=", ""))
    return "\n".join(lines)


def cst_template(overlay: RetroConsoleConstraintsOverlay | None = None) -> str:
    if overlay is None:
        overlay = retro_console_constraints_overlay()
    lines = [
        "// CPU v0.1 I34-S02 Tang Retro Console 60K SOM first-test CST template.",
        "// Do not use for board programming until:",
        "//   python tools\\fpga_retro_console_constraints.py --audit-evidence",
        "// reports status=confirmed.",
        "// Replace every I34_S02_PIN_* token with verified Retro Console board data.",
        "",
    ]
    for signal in overlay.signals:
        lines.append(f'IO_LOC "{signal.name}" {signal.placeholder};')
        lines.append(f'IO_PORT "{signal.name}" IO_TYPE={signal.io_standard};')
        lines.append("")
    return "\n".join(lines)


def sdc_template(overlay: RetroConsoleConstraintsOverlay | None = None) -> str:
    if overlay is None:
        overlay = retro_console_constraints_overlay()
    return "\n".join(
        (
            "# CPU v0.1 I34-S02 Tang Retro Console 60K SOM timing template.",
            f"create_clock -name board_clk_i -period {overlay.clock_period_placeholder} [get_ports {{board_clk_i}}]",
            "set_false_path -from [get_ports {board_reset_n_i}]",
            "",
        )
    )


def parse_constraint_evidence(text: str) -> RetroConstraintEvidenceRecord:
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
    return RetroConstraintEvidenceRecord(fields)


def audit_constraint_evidence(
    record: RetroConstraintEvidenceRecord,
    *,
    identity_audit: fpga_retro_console_identity.RetroConsoleIdentityAudit,
    evidence_path: str = "<inline>",
    overlay: RetroConsoleConstraintsOverlay | None = None,
) -> RetroConstraintAudit:
    if overlay is None:
        overlay = retro_console_constraints_overlay()
    if not identity_audit.ready_for_constraints:
        return RetroConstraintAudit(
            status=CONSTRAINT_BLOCKED_STATUS,
            message="Retro Console constraints are blocked until I34-S01 60K identity evidence is alternate-target verified.",
            evidence_path=evidence_path,
            identity_status=identity_audit.status,
            missing_fields=(),
            missing_pins=tuple(signal.evidence_key for signal in overlay.signals),
            actions=(
                "capture or fix I34-S01 Retro Console identity evidence",
                "rerun python tools\\fpga_retro_console_identity.py --audit-evidence",
            ),
        )

    missing_fields = [
        field.name
        for field in overlay.evidence_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != overlay.story:
        missing_fields.append("story_must_be_I34-S02")

    missing_pins = [
        signal.evidence_key
        for signal in overlay.signals
        if signal.required and not record.value(signal.evidence_key)
    ]
    if record.value("board_clk_i_clock_period_ns"):
        try:
            period = float(record.value("board_clk_i_clock_period_ns"))
        except ValueError:
            missing_fields.append("board_clk_i_clock_period_ns_must_be_numeric")
        else:
            if period <= 0.0:
                missing_fields.append("board_clk_i_clock_period_ns_must_be_positive")
    else:
        missing_fields.append("board_clk_i_clock_period_ns")

    if missing_fields or missing_pins:
        return RetroConstraintAudit(
            status=CONSTRAINT_INVALID_STATUS,
            message="Retro Console constraint evidence is incomplete or inconsistent.",
            evidence_path=evidence_path,
            identity_status=identity_audit.status,
            missing_fields=tuple(missing_fields),
            missing_pins=tuple(missing_pins),
            actions=(
                "fill every required evidence field",
                "replace every I34_S02_PIN placeholder from verified Retro Console data",
                "rerun the constraint overlay audit",
            ),
        )

    return RetroConstraintAudit(
        status=CONSTRAINT_CONFIRMED_STATUS,
        message="Retro Console constraint evidence is complete enough to create final CST/SDC files.",
        evidence_path=evidence_path,
        identity_status=identity_audit.status,
        missing_fields=(),
        missing_pins=(),
        actions=(
            f"create {overlay.cst_path.as_posix()} from the CST template using verified pins",
            f"create {overlay.sdc_path.as_posix()} from the SDC template using the verified clock period",
            "carry identity and pin evidence into I34-S03 Gowin reports",
        ),
    )


def load_constraint_overlay_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    identity_evidence_path: Path | None = None,
) -> RetroConstraintAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    overlay = retro_console_constraints_overlay()
    relative_path = evidence_path or overlay.evidence_path
    identity_audit = fpga_retro_console_identity.load_identity_audit(
        root,
        identity_evidence_path,
    )
    path = root / relative_path
    if not path.exists():
        return RetroConstraintAudit(
            status=CONSTRAINT_BLOCKED_STATUS,
            message="No verified Retro Console pin evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            identity_status=identity_audit.status,
            missing_fields=tuple(field.name for field in overlay.evidence_fields if field.required),
            missing_pins=tuple(signal.evidence_key for signal in overlay.signals),
            actions=(
                f"create {relative_path.as_posix()} from the evidence template",
                "extract pins from Retro Console board evidence, not Dock constraints",
                "rerun python tools\\fpga_retro_console_constraints.py --audit-evidence",
            ),
        )
    try:
        record = parse_constraint_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return RetroConstraintAudit(
            status=CONSTRAINT_INVALID_STATUS,
            message="Retro Console constraint evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            identity_status=identity_audit.status,
            missing_fields=(str(exc),),
            missing_pins=(),
            actions=("fix the key=value evidence record", "rerun the constraint overlay audit"),
        )
    return audit_constraint_evidence(
        record,
        identity_audit=identity_audit,
        evidence_path=relative_path.as_posix(),
        overlay=overlay,
    )


def fpga_retro_console_constraints_json(*, indent: int = 2) -> str:
    return json.dumps(
        retro_console_constraints_overlay().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_retro_console_constraints(
    overlay: RetroConsoleConstraintsOverlay | None = None,
) -> str:
    if overlay is None:
        overlay = retro_console_constraints_overlay()
    lines = [
        "# FPGA Retro Console Constraints",
        "",
        f"Story: {overlay.story}",
        f"Board: `{overlay.board}`",
        f"Identity gate: `{overlay.identity_gate}`",
        f"CST path: `{overlay.cst_path.as_posix()}`",
        f"CST template: `{overlay.cst_template_path.as_posix()}`",
        f"SDC path: `{overlay.sdc_path.as_posix()}`",
        f"SDC template: `{overlay.sdc_template_path.as_posix()}`",
        f"Evidence path: `{overlay.evidence_path.as_posix()}`",
        "",
        "## Required Signals",
        "",
        "| Signal | Direction | Evidence key | IO standard | Polarity | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for signal in overlay.signals:
        lines.append(
            f"| `{signal.name}` | {signal.direction} | `{signal.evidence_key}` | "
            f"`{signal.io_standard}` | {signal.polarity} | {signal.purpose} |"
        )
    lines.extend(["", "## Evidence Fields", ""])
    lines.extend(
        (
            "| Field | Required | Description |",
            "| --- | --- | --- |",
        )
    )
    for field in overlay.evidence_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in overlay.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_retro_console_constraints(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    overlay = retro_console_constraints_overlay()
    issues: list[str] = []

    if overlay.story != FPGA_RETRO_CONSOLE_CONSTRAINTS_STORY:
        issues.append(f"Retro Console constraints story must be {FPGA_RETRO_CONSOLE_CONSTRAINTS_STORY}")
    if overlay.board != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD:
        issues.append("Retro Console constraints board must match I34-S01")
    if overlay.identity_gate != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL:
        issues.append("Retro Console constraints must depend on I34-S01 identity gate")
    if not overlay.clock_period_placeholder.startswith("I34_S02_"):
        issues.append("Retro Console SDC must keep a story-owned clock placeholder")

    signals = {signal.name: signal for signal in overlay.signals}
    for required in (
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "uart_tx_o",
    ):
        signal = signals.get(required)
        if signal is None:
            issues.append(f"missing Retro Console constraint signal {required}")
        elif not signal.required:
            issues.append(f"{required} must be required")
    for signal in overlay.signals:
        if not signal.io_standard.endswith("_or_recorded"):
            issues.append(f"{signal.name} must require recorded IO standard")

    cst = cst_template(overlay)
    for token in (
        "I34-S02",
        "IO_LOC",
        "IO_PORT",
        "I34_S02_PIN_BOARD_CLK_I",
        "I34_S02_PIN_BOARD_RESET_N_I",
        "I34_S02_PIN_PASS_LED_O",
        "I34_S02_PIN_FAIL_LED_O",
        "I34_S02_PIN_HEARTBEAT_LED_O",
        "I34_S02_PIN_UART_TX_O",
    ):
        if token not in cst:
            issues.append(f"Retro Console CST template missing {token}")

    sdc = sdc_template(overlay)
    for token in (
        "create_clock",
        "board_clk_i",
        overlay.clock_period_placeholder,
        "set_false_path",
        "board_reset_n_i",
    ):
        if token not in sdc:
            issues.append(f"Retro Console SDC template missing {token}")

    for path, tokens in (
        (
            overlay.cst_template_path,
            ("I34_S02_PIN_BOARD_CLK_I", "IO_LOC", "IO_PORT"),
        ),
        (
            overlay.sdc_template_path,
            ("create_clock", overlay.clock_period_placeholder, "board_reset_n_i"),
        ),
    ):
        text = _read_if_exists(root / path)
        for token in tokens:
            if token not in text:
                issues.append(f"{path.as_posix()} missing {token}")

    fields = {field.name: field for field in overlay.evidence_fields}
    for required in (
        "story",
        "identity_evidence",
        "source_constraints",
        "verified_by",
        "verified_at",
        "io_voltage",
        "led_polarity",
        "uart_debug_mode",
        "pin_conflicts",
        "board_clk_i_clock_period_ns",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing Retro Console constraint evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    identity_audit = _fixture_identity_audit()
    pin_record = parse_constraint_evidence(
        "\n".join(
            (
                "story=I34-S02",
                f"identity_evidence={fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix()}",
                "source_constraints=verified Retro Console schematic or pin spreadsheet",
                "verified_by=fixture",
                "verified_at=2026-05-11T00:00:00",
                "io_voltage=LVCMOS33 from verified IO bank",
                "led_polarity=active_high_or_recorded",
                "uart_debug_mode=UART status TX",
                "pin_conflicts=none for selected first-test pins",
                "board_clk_i_pin=P1",
                "board_reset_n_i_pin=P2",
                "pass_led_o_pin=P3",
                "fail_led_o_pin=P4",
                "heartbeat_led_o_pin=P5",
                "uart_tx_o_pin=P6",
                "board_clk_i_clock_period_ns=40.000",
            )
        )
    )
    if not audit_constraint_evidence(pin_record, identity_audit=identity_audit).confirmed:
        issues.append("complete Retro Console constraint evidence must audit as confirmed")

    blocked = load_constraint_overlay_audit(root)
    if blocked.status not in (
        CONSTRAINT_BLOCKED_STATUS,
        CONSTRAINT_CONFIRMED_STATUS,
        CONSTRAINT_INVALID_STATUS,
    ):
        issues.append("Retro Console constraint audit returned an unknown status")

    doc = _read_if_exists(root / FPGA_RETRO_CONSOLE_CONSTRAINTS_DOC)
    for token in (
        "Story: I34-S02",
        FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
        fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        overlay.cst_path.as_posix(),
        overlay.cst_template_path.as_posix(),
        overlay.sdc_path.as_posix(),
        overlay.sdc_template_path.as_posix(),
        overlay.evidence_path.as_posix(),
        "Sipeed Tang Retro Console with 60K SOM",
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "uart_tx_o",
        "I34_S02_PIN_BOARD_CLK_I",
        overlay.clock_period_placeholder,
        "io_voltage",
        "pin_conflicts",
        "not Tang Mega Dock with 138K SOM",
        "I34-S03",
        "blocked",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RETRO_CONSOLE_CONSTRAINTS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _fixture_identity_audit() -> fpga_retro_console_identity.RetroConsoleIdentityAudit:
    record = fpga_retro_console_identity.parse_identity_record(
        "\n".join(
            (
                "story=I34-S01",
                "board=Sipeed Tang Retro Console with 60K SOM",
                "source=programmer_jtag_scan",
                "observed_device=GW5AT-60B",
                "observed_idcode=0x0001481B",
                "observed_package=scan_recorded_package",
                "observed_device_version=B",
                "gowin_part=scan_recorded_gowin_part",
                "programming_path=Gowin Programmer SRAM",
                "clock_sources=verified Retro Console oscillator",
                "reset_sources=verified Retro Console reset input",
                "visible_outputs=heartbeat/pass/fail outputs",
                "uart_debug_access=verified UART status path",
                "selected_first_target=no",
                "primary_138k_target=Sipeed Tang Mega Dock with 138K SOM",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-11T00:00:00",
            )
        )
    )
    return fpga_retro_console_identity.audit_identity_record(record)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

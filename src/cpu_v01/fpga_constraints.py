"""Tang Mega 138K first-test constraint overlay profile for CPU v0.1.

Owner stories:
- I24-S02: verified first-test CST/SDC overlay for the physical board target.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_board_identity, fpga_first_test, fpga_synthesis


JsonValue = Any

FPGA_CONSTRAINTS_STORY = "I24-S02"
FPGA_CONSTRAINTS_DOC = Path("docs/implementation/fpga-constraints-overlay.md")
FPGA_CONSTRAINTS_TOOL = "python tools\\fpga_constraints_overlay.py --check"
FPGA_CONSTRAINTS_CST_TEMPLATE = Path("constraints/tang_mega_138k_first_test.cst.template")
FPGA_CONSTRAINTS_EVIDENCE = Path(
    "docs/implementation/evidence/i24_s02_constraint_pins.txt"
)
CONSTRAINT_CONFIRMED_STATUS = "confirmed"
CONSTRAINT_BLOCKED_STATUS = "blocked"
CONSTRAINT_INVALID_STATUS = "invalid"


@dataclass(frozen=True)
class ConstraintSignal:
    name: str
    direction: str
    required: bool
    evidence_key: str
    io_standard: str
    polarity: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "required": self.required,
            "evidence_key": self.evidence_key,
            "io_standard": self.io_standard,
            "polarity": self.polarity,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class ConstraintEvidenceField:
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
class FpgaConstraintsOverlay:
    story: str
    board: str
    device: str
    package: str
    identity_gate: str
    cst_path: Path
    cst_template_path: Path
    sdc_path: Path
    evidence_path: Path
    clock_period_ns: float
    signals: tuple[ConstraintSignal, ...]
    evidence_fields: tuple[ConstraintEvidenceField, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "device": self.device,
            "package": self.package,
            "identity_gate": self.identity_gate,
            "cst_path": self.cst_path.as_posix(),
            "cst_template_path": self.cst_template_path.as_posix(),
            "sdc_path": self.sdc_path.as_posix(),
            "evidence_path": self.evidence_path.as_posix(),
            "clock_period_ns": self.clock_period_ns,
            "signals": [signal.as_dict() for signal in self.signals],
            "evidence_fields": [field.as_dict() for field in self.evidence_fields],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ConstraintEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class ConstraintOverlayAudit:
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


def fpga_constraints_overlay() -> FpgaConstraintsOverlay:
    return FpgaConstraintsOverlay(
        story=FPGA_CONSTRAINTS_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        package=fpga_first_test.TARGET_IDE_PACKAGE,
        identity_gate=fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        cst_path=fpga_synthesis.FPGA_SYNTHESIS_CONSTRAINT_FILE,
        cst_template_path=FPGA_CONSTRAINTS_CST_TEMPLATE,
        sdc_path=fpga_synthesis.FPGA_SYNTHESIS_TIMING_FILE,
        evidence_path=FPGA_CONSTRAINTS_EVIDENCE,
        clock_period_ns=40.000,
        signals=(
            ConstraintSignal(
                name="board_clk_i",
                direction="input",
                required=True,
                evidence_key="board_clk_i_pin",
                io_standard="LVCMOS33",
                polarity="free_running",
                purpose="25 MHz first-test board clock constrained by a 40 ns SDC period.",
            ),
            ConstraintSignal(
                name="board_reset_n_i",
                direction="input",
                required=True,
                evidence_key="board_reset_n_i_pin",
                io_standard="LVCMOS33",
                polarity="active_low",
                purpose="Asynchronous board reset input, synchronized inside cpu_v01_fpga_top.",
            ),
            ConstraintSignal(
                name="pass_led_o",
                direction="output",
                required=True,
                evidence_key="pass_led_o_pin",
                io_standard="LVCMOS33",
                polarity="active_high_or_recorded_in_evidence",
                purpose="Visible first-test pass output.",
            ),
            ConstraintSignal(
                name="fail_led_o",
                direction="output",
                required=True,
                evidence_key="fail_led_o_pin",
                io_standard="LVCMOS33",
                polarity="active_high_or_recorded_in_evidence",
                purpose="Visible first-test fail output.",
            ),
            ConstraintSignal(
                name="heartbeat_led_o",
                direction="output",
                required=True,
                evidence_key="heartbeat_led_o_pin",
                io_standard="LVCMOS33",
                polarity="active_high_or_recorded_in_evidence",
                purpose="Visible clock/reset/retire heartbeat output.",
            ),
            ConstraintSignal(
                name="uart_tx_o",
                direction="output",
                required=True,
                evidence_key="uart_tx_o_pin",
                io_standard="LVCMOS33",
                polarity="idle_high_8n1",
                purpose="I25-S02 UART debug/status packet stream.",
            ),
        ),
        evidence_fields=(
            ConstraintEvidenceField(
                name="story",
                required=True,
                description="Must be I24-S02.",
            ),
            ConstraintEvidenceField(
                name="identity_evidence",
                required=True,
                description="Path to the confirmed I24-S01 identity evidence record.",
            ),
            ConstraintEvidenceField(
                name="source_constraints",
                required=True,
                description="Sipeed All PIN Constraints file, commit, or release used as the pin source.",
            ),
            ConstraintEvidenceField(
                name="verified_by",
                required=True,
                description="Person or process that checked the signal-to-pin mapping.",
            ),
            ConstraintEvidenceField(
                name="verified_at",
                required=True,
                description="Local date/time when pins and IO standards were checked.",
            ),
            ConstraintEvidenceField(
                name="led_polarity",
                required=True,
                description="Observed or board-documented polarity for pass/fail/heartbeat LEDs.",
            ),
        ),
        blockers=(
            "I24-S01 identity evidence must audit as confirmed before pins can be accepted",
            "Sipeed All PIN Constraints source for the exact SOM/package must be captured",
            "board_clk_i, board_reset_n_i, pass_led_o, fail_led_o, heartbeat_led_o, and uart_tx_o pins must be filled from verified board data",
            "do not create the final CST file until placeholders are replaced with verified pins",
        ),
    )


def constraint_evidence_template(overlay: FpgaConstraintsOverlay | None = None) -> str:
    if overlay is None:
        overlay = fpga_constraints_overlay()
    lines = [
        f"story={overlay.story}",
        f"identity_evidence={fpga_board_identity.FPGA_BOARD_IDENTITY_EVIDENCE.as_posix()}",
        "source_constraints=",
        "verified_by=",
        "verified_at=",
        "led_polarity=",
    ]
    lines.extend(f"{signal.evidence_key}=" for signal in overlay.signals)
    lines.extend(
        (
            f"board_clk_i_clock_period_ns={overlay.clock_period_ns:.3f}",
            "",
        )
    )
    return "\n".join(lines)


def cst_template(overlay: FpgaConstraintsOverlay | None = None) -> str:
    if overlay is None:
        overlay = fpga_constraints_overlay()
    lines = [
        "// CPU v0.1 I24-S02 Tang Mega 138K first-test CST template.",
        "// Do not use for board programming until:",
        "//   python tools\\fpga_constraints_overlay.py --audit-evidence",
        "// reports status=confirmed.",
        "// Replace every I24_S02_PIN_* token with verified Sipeed All PIN Constraints data.",
        "",
    ]
    for signal in overlay.signals:
        placeholder = f"I24_S02_PIN_{signal.name.upper()}"
        lines.append(f'IO_LOC "{signal.name}" {placeholder};')
        lines.append(f'IO_PORT "{signal.name}" IO_TYPE={signal.io_standard};')
        lines.append("")
    return "\n".join(lines)


def sdc_template(overlay: FpgaConstraintsOverlay | None = None) -> str:
    if overlay is None:
        overlay = fpga_constraints_overlay()
    return "\n".join(
        (
            "# CPU v0.1 I24-S02 Tang Mega 138K first-test timing constraints.",
            f"create_clock -name board_clk_i -period {overlay.clock_period_ns:.3f} [get_ports {{board_clk_i}}]",
            "set_false_path -from [get_ports {board_reset_n_i}]",
            "",
        )
    )


def parse_constraint_evidence(text: str) -> ConstraintEvidenceRecord:
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
    return ConstraintEvidenceRecord(fields)


def audit_constraint_evidence(
    record: ConstraintEvidenceRecord,
    *,
    identity_audit: fpga_board_identity.BoardIdentityAudit,
    evidence_path: str = "<inline>",
    overlay: FpgaConstraintsOverlay | None = None,
) -> ConstraintOverlayAudit:
    if overlay is None:
        overlay = fpga_constraints_overlay()
    if not identity_audit.confirmed:
        return ConstraintOverlayAudit(
            status=CONSTRAINT_BLOCKED_STATUS,
            message="Constraint overlay is blocked until I24-S01 identity evidence is confirmed.",
            evidence_path=evidence_path,
            identity_status=identity_audit.status,
            missing_fields=(),
            missing_pins=tuple(signal.evidence_key for signal in overlay.signals),
            actions=(
                "capture or fix I24-S01 board identity evidence",
                "rerun python tools\\fpga_board_identity.py --audit-evidence",
            ),
        )

    missing_fields = [
        field.name
        for field in overlay.evidence_fields
        if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != overlay.story:
        missing_fields.append("story_must_be_I24-S02")
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
            if abs(period - overlay.clock_period_ns) > 0.001:
                missing_fields.append("board_clk_i_clock_period_ns_must_be_40.000")
    else:
        missing_fields.append("board_clk_i_clock_period_ns")

    if missing_fields or missing_pins:
        return ConstraintOverlayAudit(
            status=CONSTRAINT_INVALID_STATUS,
            message="Constraint evidence is incomplete or inconsistent.",
            evidence_path=evidence_path,
            identity_status=identity_audit.status,
            missing_fields=tuple(missing_fields),
            missing_pins=tuple(missing_pins),
            actions=(
                "fill every required evidence field",
                "extract all required pins from the verified Sipeed constraints",
                "rerun the constraint overlay audit",
            ),
        )

    return ConstraintOverlayAudit(
        status=CONSTRAINT_CONFIRMED_STATUS,
        message="Constraint evidence is complete for the assumed Tang Mega 138K first-test target.",
        evidence_path=evidence_path,
        identity_status=identity_audit.status,
        missing_fields=(),
        missing_pins=(),
        actions=(
            f"create {overlay.cst_path.as_posix()} from the CST template using the verified pins",
            f"use {overlay.sdc_path.as_posix()} in the I24-S03 Gowin build",
            "carry identity and pin evidence into the report bundle",
        ),
    )


def load_constraint_overlay_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
    identity_evidence_path: Path | None = None,
) -> ConstraintOverlayAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    overlay = fpga_constraints_overlay()
    relative_path = evidence_path or overlay.evidence_path
    identity_audit = fpga_board_identity.load_identity_audit(root, identity_evidence_path)
    path = root / relative_path
    if not path.exists():
        return ConstraintOverlayAudit(
            status=CONSTRAINT_BLOCKED_STATUS,
            message="No verified first-test pin evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            identity_status=identity_audit.status,
            missing_fields=tuple(field.name for field in overlay.evidence_fields if field.required),
            missing_pins=tuple(signal.evidence_key for signal in overlay.signals),
            actions=(
                f"create {relative_path.as_posix()} from the evidence template",
                "extract pins from the Sipeed All PIN Constraints source for the confirmed board",
                "rerun python tools\\fpga_constraints_overlay.py --audit-evidence",
            ),
        )
    try:
        record = parse_constraint_evidence(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return ConstraintOverlayAudit(
            status=CONSTRAINT_INVALID_STATUS,
            message="Constraint evidence could not be parsed.",
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


def fpga_constraints_overlay_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_constraints_overlay().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_constraints_overlay(
    overlay: FpgaConstraintsOverlay | None = None,
) -> str:
    if overlay is None:
        overlay = fpga_constraints_overlay()
    lines = [
        "# FPGA Constraints Overlay",
        "",
        f"Story: {overlay.story}",
        "",
        f"Board: `{overlay.board}`",
        f"Device: `{overlay.device}`",
        f"Package: `{overlay.package}`",
        f"Identity gate: `{overlay.identity_gate}`",
        f"CST path: `{overlay.cst_path.as_posix()}`",
        f"CST template: `{overlay.cst_template_path.as_posix()}`",
        f"SDC path: `{overlay.sdc_path.as_posix()}`",
        f"Evidence path: `{overlay.evidence_path.as_posix()}`",
        f"Clock period: {overlay.clock_period_ns:.3f} ns",
        "",
        "## Required Signals",
        "",
        "| Signal | Direction | Required | Evidence key | IO standard | Polarity | Purpose |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for signal in overlay.signals:
        lines.append(
            f"| `{signal.name}` | {signal.direction} | "
            f"{'yes' if signal.required else 'no'} | `{signal.evidence_key}` | "
            f"`{signal.io_standard}` | {signal.polarity} | {signal.purpose} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Fields",
            "",
            "| Field | Required | Description |",
            "| --- | --- | --- |",
        ]
    )
    for field in overlay.evidence_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | "
            f"{field.description} |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in overlay.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_constraints_overlay(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    overlay = fpga_constraints_overlay()
    issues: list[str] = []

    if overlay.story != FPGA_CONSTRAINTS_STORY:
        issues.append(f"constraints overlay story must be {FPGA_CONSTRAINTS_STORY}")
    if overlay.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("constraints overlay board must match the first-test profile")
    if overlay.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("constraints overlay device must match the first-test profile")
    if overlay.package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("constraints overlay package must match the first-test profile")
    if overlay.cst_path != fpga_synthesis.FPGA_SYNTHESIS_CONSTRAINT_FILE:
        issues.append("constraints overlay CST path must match I23-S05")
    if overlay.sdc_path != fpga_synthesis.FPGA_SYNTHESIS_TIMING_FILE:
        issues.append("constraints overlay SDC path must match I23-S05")
    if overlay.clock_period_ns != 40.000:
        issues.append("first-test clock period must be 40.000 ns")

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
            issues.append(f"missing required constraint signal {required}")
        elif not signal.required:
            issues.append(f"{required} must be required")

    for signal in overlay.signals:
        if signal.io_standard != "LVCMOS33":
            issues.append(f"{signal.name} must default to LVCMOS33")

    template = cst_template(overlay)
    for token in (
        "IO_LOC",
        "IO_PORT",
        "I24_S02_PIN_BOARD_CLK_I",
        "I24_S02_PIN_BOARD_RESET_N_I",
        "I24_S02_PIN_PASS_LED_O",
        "I24_S02_PIN_FAIL_LED_O",
        "I24_S02_PIN_HEARTBEAT_LED_O",
        "I24_S02_PIN_UART_TX_O",
        "LVCMOS33",
    ):
        if token not in template:
            issues.append(f"CST template missing {token}")

    sdc = sdc_template(overlay)
    for token in (
        "create_clock",
        "board_clk_i",
        "-period 40.000",
        "set_false_path",
        "board_reset_n_i",
    ):
        if token not in sdc:
            issues.append(f"SDC template missing {token}")

    for path, tokens in (
        (
            overlay.cst_template_path,
            ("I24_S02_PIN_BOARD_CLK_I", "IO_LOC", "IO_PORT", "LVCMOS33"),
        ),
        (
            overlay.sdc_path,
            ("create_clock", "board_clk_i", "-period 40.000", "board_reset_n_i"),
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
        "led_polarity",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing constraint evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    identity_record = fpga_board_identity.parse_identity_record(
        "\n".join(
            (
                "story=I24-S01",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "source=programmer_jtag_scan",
                f"observed_device={fpga_first_test.TARGET_FPGA_DEVICE}",
                f"observed_package={fpga_first_test.TARGET_IDE_PACKAGE}",
                "observed_device_version=B",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-08T00:00:00",
            )
        )
    )
    identity_audit = fpga_board_identity.audit_identity_record(identity_record)
    pin_record = parse_constraint_evidence(
        "\n".join(
            (
                "story=I24-S02",
                f"identity_evidence={fpga_board_identity.FPGA_BOARD_IDENTITY_EVIDENCE.as_posix()}",
                "source_constraints=Sipeed All PIN Constraints verified package",
                "verified_by=fixture",
                "verified_at=2026-05-08T00:00:00",
                "led_polarity=active_high",
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
        issues.append("complete constraint evidence must audit as confirmed")

    doc = _read_if_exists(root / FPGA_CONSTRAINTS_DOC)
    for token in (
        "Story: I24-S02",
        FPGA_CONSTRAINTS_TOOL,
        overlay.cst_path.as_posix(),
        overlay.cst_template_path.as_posix(),
        overlay.sdc_path.as_posix(),
        overlay.evidence_path.as_posix(),
        "python tools\\fpga_board_identity.py --check",
        "GW5AST-LV138PG484A",
        "PBG484A",
        "Sipeed All PIN Constraints",
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "uart_tx_o",
        "LVCMOS33",
        "40.000",
        "I24_S02_PIN_BOARD_CLK_I",
        "blocked",
        "I24-S03",
    ):
        if token not in doc:
            issues.append(f"{FPGA_CONSTRAINTS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

"""Tang Mega 138K board identity evidence gate for CPU v0.1.

Owner stories:
- I24-S01: physical board device/package and toolchain target verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test


JsonValue = Any

FPGA_BOARD_IDENTITY_STORY = "I24-S01"
FPGA_BOARD_IDENTITY_DOC = Path("docs/implementation/fpga-board-identity.md")
FPGA_BOARD_IDENTITY_TOOL = "python tools\\fpga_board_identity.py --check"
FPGA_BOARD_IDENTITY_EVIDENCE = Path(
    "docs/implementation/evidence/i24_s01_device_identity.txt"
)
EXPECTED_IDENTITY_STATUS = "confirmed"
BLOCKED_IDENTITY_STATUS = "blocked"
MISMATCH_IDENTITY_STATUS = "target_mismatch"
INVALID_IDENTITY_STATUS = "invalid"


@dataclass(frozen=True)
class BoardIdentityField:
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
class BoardIdentityCommand:
    name: str
    command: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "command": self.command,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class BoardIdentityExpectation:
    story: str
    board: str
    assumed_device: str
    assumed_package: str
    assumed_device_version: str
    evidence_path: Path
    required_fields: tuple[BoardIdentityField, ...]
    scan_commands: tuple[BoardIdentityCommand, ...]
    alternate_targets: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "assumed_device": self.assumed_device,
            "assumed_package": self.assumed_package,
            "assumed_device_version": self.assumed_device_version,
            "evidence_path": self.evidence_path.as_posix(),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "scan_commands": [command.as_dict() for command in self.scan_commands],
            "alternate_targets": list(self.alternate_targets),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class BoardIdentityRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class BoardIdentityAudit:
    status: str
    message: str
    evidence_path: str
    observed_device: str
    observed_package: str
    observed_device_version: str
    issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def confirmed(self) -> bool:
        return self.status == EXPECTED_IDENTITY_STATUS

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "observed_device": self.observed_device,
            "observed_package": self.observed_package,
            "observed_device_version": self.observed_device_version,
            "issues": list(self.issues),
            "actions": list(self.actions),
        }


def board_identity_expectation() -> BoardIdentityExpectation:
    return BoardIdentityExpectation(
        story=FPGA_BOARD_IDENTITY_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        assumed_device=fpga_first_test.TARGET_FPGA_DEVICE,
        assumed_package=fpga_first_test.TARGET_IDE_PACKAGE,
        assumed_device_version=fpga_first_test.TARGET_DEVICE_VERSION,
        evidence_path=FPGA_BOARD_IDENTITY_EVIDENCE,
        required_fields=(
            BoardIdentityField(
                name="story",
                required=True,
                description="Must be I24-S01 so stale I23 blocker evidence is not reused.",
            ),
            BoardIdentityField(
                name="board",
                required=True,
                description="Human-readable board name from the physical board under test.",
            ),
            BoardIdentityField(
                name="source",
                required=True,
                description="board_marking, programmer_jtag_scan, or both.",
            ),
            BoardIdentityField(
                name="observed_device",
                required=True,
                description="Device string reported by marking or scan.",
            ),
            BoardIdentityField(
                name="observed_package",
                required=True,
                description="Package string reported by marking or scan.",
            ),
            BoardIdentityField(
                name="observed_device_version",
                required=True,
                description="Gowin Device Version value selected for the build, normally B or C.",
            ),
            BoardIdentityField(
                name="observed_tool",
                required=True,
                description="Tool or physical method used to capture the evidence.",
            ),
            BoardIdentityField(
                name="observed_at",
                required=True,
                description="Local date/time when the board identity was captured.",
            ),
            BoardIdentityField(
                name="evidence_notes",
                required=False,
                description="Free-form notes, serial number, screenshot path, or command output path.",
            ),
        ),
        scan_commands=(
            BoardIdentityCommand(
                name="gowin_programmer_scan",
                command="Use Gowin Programmer device scan and record the device, package, and Device Version.",
                purpose="Primary vendor-supported identity source for Gowin build settings.",
            ),
            BoardIdentityCommand(
                name="openfpgaloader_detect",
                command="openFPGALoader --detect",
                purpose="Optional independent JTAG visibility check when installed and supported by the cable.",
            ),
            BoardIdentityCommand(
                name="board_marking_photo",
                command="Record the SOM marking and optional photo path in evidence_notes.",
                purpose="Cross-check the public PG484/FPG676 ambiguity before locking constraints.",
            ),
        ),
        alternate_targets=(
            "GW5AST-LV138FPG676A/FPG676A appears in public Tang Mega 138K references",
            "Tang Mega 138K Pro Dock consistently uses the FPG676-style target",
        ),
        blockers=(
            "no physical board marking or programmer/JTAG scan is captured in the repository",
            "do not lock the I24-S02 CST overlay until identity status is confirmed",
            "if FPG676 is observed, update the target profile before running Gowin",
        ),
    )


def identity_template(expectation: BoardIdentityExpectation | None = None) -> str:
    if expectation is None:
        expectation = board_identity_expectation()
    return "\n".join(
        (
            f"story={expectation.story}",
            f"board={expectation.board}",
            "source=",
            "observed_device=",
            "observed_package=",
            "observed_device_version=",
            "observed_tool=",
            "observed_at=",
            "evidence_notes=",
            "",
        )
    )


def parse_identity_record(text: str) -> BoardIdentityRecord:
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
    return BoardIdentityRecord(fields)


def audit_identity_record(
    record: BoardIdentityRecord,
    *,
    evidence_path: str = "<inline>",
    expectation: BoardIdentityExpectation | None = None,
) -> BoardIdentityAudit:
    if expectation is None:
        expectation = board_identity_expectation()
    issues: list[str] = []

    for field in expectation.required_fields:
        if field.required and not record.value(field.name):
            issues.append(f"missing required field {field.name}")

    if record.value("story") and record.value("story") != expectation.story:
        issues.append(f"story must be {expectation.story}")
    if record.value("board") and record.value("board") != expectation.board:
        issues.append(f"board must be {expectation.board}")

    observed_device = record.value("observed_device")
    observed_package = record.value("observed_package")
    observed_device_version = record.value("observed_device_version")
    if issues:
        return BoardIdentityAudit(
            status=INVALID_IDENTITY_STATUS,
            message="Identity record is incomplete or malformed.",
            evidence_path=evidence_path,
            observed_device=observed_device,
            observed_package=observed_package,
            observed_device_version=observed_device_version,
            issues=tuple(issues),
            actions=("capture board marking or JTAG scan again", "rerun the identity audit"),
        )

    device_matches = observed_device == expectation.assumed_device
    package_matches = observed_package == expectation.assumed_package
    if device_matches and package_matches:
        return BoardIdentityAudit(
            status=EXPECTED_IDENTITY_STATUS,
            message="Tang Mega 138K identity matches the assumed first-test target.",
            evidence_path=evidence_path,
            observed_device=observed_device,
            observed_package=observed_package,
            observed_device_version=observed_device_version,
            issues=(),
            actions=(
                "use this device/package in the I24-S02 CST/SDC overlay",
                "carry the evidence path into the Gowin build report bundle",
            ),
        )

    mismatch_reason = (
        "observed FPG676-style target"
        if "FPG676" in observed_device or "FPG676" in observed_package
        else "observed target differs from the assumed first-test target"
    )
    return BoardIdentityAudit(
        status=MISMATCH_IDENTITY_STATUS,
        message=f"{mismatch_reason}; update the target overlay before synthesis.",
        evidence_path=evidence_path,
        observed_device=observed_device,
        observed_package=observed_package,
        observed_device_version=observed_device_version,
        issues=(
            f"expected device {expectation.assumed_device}, observed {observed_device}",
            f"expected package {expectation.assumed_package}, observed {observed_package}",
        ),
        actions=(
            "update src/cpu_v01/fpga_first_test.py target constants",
            "update FPGA first-test, synthesis, and bring-up docs",
            "rerun I23-S05 before creating the I24-S02 CST overlay",
        ),
    )


def load_identity_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> BoardIdentityAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    expectation = board_identity_expectation()
    relative_path = evidence_path or expectation.evidence_path
    path = root / relative_path
    if not path.exists():
        return BoardIdentityAudit(
            status=BLOCKED_IDENTITY_STATUS,
            message="No physical board identity evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            observed_device="",
            observed_package="",
            observed_device_version="",
            issues=("missing board marking or programmer/JTAG scan evidence",),
            actions=(
                f"create {relative_path.as_posix()} from the identity template",
                "record board marking or Gowin Programmer scan output",
                "rerun python tools\\fpga_board_identity.py --audit-evidence",
            ),
        )
    try:
        record = parse_identity_record(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return BoardIdentityAudit(
            status=INVALID_IDENTITY_STATUS,
            message="Identity record could not be parsed.",
            evidence_path=relative_path.as_posix(),
            observed_device="",
            observed_package="",
            observed_device_version="",
            issues=(str(exc),),
            actions=("fix the key=value evidence record", "rerun the identity audit"),
        )
    return audit_identity_record(
        record,
        evidence_path=relative_path.as_posix(),
        expectation=expectation,
    )


def fpga_board_identity_json(*, indent: int = 2) -> str:
    return json.dumps(
        board_identity_expectation().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_board_identity_profile(
    expectation: BoardIdentityExpectation | None = None,
) -> str:
    if expectation is None:
        expectation = board_identity_expectation()
    lines = [
        "# FPGA Board Identity",
        "",
        f"Story: {expectation.story}",
        "",
        f"Board: `{expectation.board}`",
        f"Assumed device: `{expectation.assumed_device}`",
        f"Assumed package: `{expectation.assumed_package}`",
        f"Assumed Device Version: {expectation.assumed_device_version}",
        f"Evidence path: `{expectation.evidence_path.as_posix()}`",
        "",
        "## Required Evidence Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in expectation.required_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | "
            f"{field.description} |"
        )
    lines.extend(
        [
            "",
            "## Scan Commands",
            "",
            "| Name | Command | Purpose |",
            "| --- | --- | --- |",
        ]
    )
    for command in expectation.scan_commands:
        lines.append(f"| `{command.name}` | `{command.command}` | {command.purpose} |")
    lines.extend(["", "## Alternate Targets", ""])
    lines.extend(f"- {target}." for target in expectation.alternate_targets)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in expectation.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_board_identity(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    expectation = board_identity_expectation()
    issues: list[str] = []

    if expectation.story != FPGA_BOARD_IDENTITY_STORY:
        issues.append(f"board identity story must be {FPGA_BOARD_IDENTITY_STORY}")
    if expectation.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("board identity target must match the first-test profile")
    if expectation.assumed_device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("board identity device must match the first-test profile")
    if expectation.assumed_package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("board identity package must match the first-test profile")
    if "JTAG" not in expectation.assumed_device_version:
        issues.append("board identity must preserve the JTAG verification requirement")

    fields = {field.name: field for field in expectation.required_fields}
    for required in (
        "story",
        "board",
        "source",
        "observed_device",
        "observed_package",
        "observed_device_version",
        "observed_tool",
        "observed_at",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing identity evidence field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")

    commands = {command.name for command in expectation.scan_commands}
    for required in ("gowin_programmer_scan", "openfpgaloader_detect", "board_marking_photo"):
        if required not in commands:
            issues.append(f"missing identity scan command {required}")

    good_record = parse_identity_record(
        "\n".join(
            (
                f"story={FPGA_BOARD_IDENTITY_STORY}",
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
    if not audit_identity_record(good_record).confirmed:
        issues.append("expected identity record must audit as confirmed")

    mismatch_record = parse_identity_record(
        "\n".join(
            (
                f"story={FPGA_BOARD_IDENTITY_STORY}",
                f"board={fpga_first_test.TARGET_BOARD_NAME}",
                "source=programmer_jtag_scan",
                "observed_device=GW5AST-LV138FPG676A",
                "observed_package=FPG676A",
                "observed_device_version=B",
                "observed_tool=Gowin Programmer",
                "observed_at=2026-05-08T00:00:00",
            )
        )
    )
    if audit_identity_record(mismatch_record).status != MISMATCH_IDENTITY_STATUS:
        issues.append("FPG676 identity record must audit as a target mismatch")

    missing_audit = load_identity_audit(root)
    if missing_audit.status not in (
        BLOCKED_IDENTITY_STATUS,
        EXPECTED_IDENTITY_STATUS,
        MISMATCH_IDENTITY_STATUS,
        INVALID_IDENTITY_STATUS,
    ):
        issues.append("identity evidence audit returned an unknown status")

    doc = _read_if_exists(root / FPGA_BOARD_IDENTITY_DOC)
    for token in (
        "Story: I24-S01",
        FPGA_BOARD_IDENTITY_TOOL,
        expectation.evidence_path.as_posix(),
        fpga_first_test.TARGET_BOARD_NAME,
        fpga_first_test.TARGET_FPGA_DEVICE,
        fpga_first_test.TARGET_IDE_PACKAGE,
        "Gowin Programmer",
        "openFPGALoader --detect",
        "board_marking",
        "programmer_jtag_scan",
        "observed_device",
        "observed_package",
        "observed_device_version",
        "GW5AST-LV138FPG676A",
        "FPG676A",
        "I24-S02",
        "CST",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_BOARD_IDENTITY_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

"""Gowin build and report-bundle audit for the Tang Mega 138K first test.

Owner stories:
- I24-S03: Gowin synthesis, place-route, bitstream, and report audit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_board_identity, fpga_constraints, fpga_first_test, fpga_synthesis


JsonValue = Any

FPGA_GOWIN_BUILD_STORY = "I24-S03"
FPGA_GOWIN_BUILD_DOC = Path("docs/implementation/fpga-gowin-build.md")
FPGA_GOWIN_BUILD_TOOL = "python tools\\fpga_gowin_build.py --check"
GOWIN_AUDIT_PASSED = "passed"
GOWIN_AUDIT_BLOCKED = "blocked"
GOWIN_AUDIT_FAILED = "failed"


@dataclass(frozen=True)
class GowinBuildStep:
    name: str
    command: str
    prerequisite: str
    output: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "command": self.command,
            "prerequisite": self.prerequisite,
            "output": self.output,
        }


@dataclass(frozen=True)
class GowinReportRequirement:
    name: str
    glob: str
    required_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...]
    failure_condition: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "glob": self.glob,
            "required_tokens": list(self.required_tokens),
            "forbidden_tokens": list(self.forbidden_tokens),
            "failure_condition": self.failure_condition,
        }


@dataclass(frozen=True)
class FpgaGowinBuildProfile:
    story: str
    board: str
    device: str
    package: str
    top_module: str
    build_root: Path
    identity_gate: str
    constraints_gate: str
    synthesis_gate: str
    steps: tuple[GowinBuildStep, ...]
    report_requirements: tuple[GowinReportRequirement, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "device": self.device,
            "package": self.package,
            "top_module": self.top_module,
            "build_root": self.build_root.as_posix(),
            "identity_gate": self.identity_gate,
            "constraints_gate": self.constraints_gate,
            "synthesis_gate": self.synthesis_gate,
            "steps": [step.as_dict() for step in self.steps],
            "report_requirements": [
                requirement.as_dict() for requirement in self.report_requirements
            ],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class GowinReportAudit:
    status: str
    message: str
    build_root: str
    identity_status: str
    constraints_status: str
    missing_reports: tuple[str, ...]
    token_issues: tuple[str, ...]
    failure_markers: tuple[str, ...]
    bitstreams: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == GOWIN_AUDIT_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "build_root": self.build_root,
            "identity_status": self.identity_status,
            "constraints_status": self.constraints_status,
            "missing_reports": list(self.missing_reports),
            "token_issues": list(self.token_issues),
            "failure_markers": list(self.failure_markers),
            "bitstreams": list(self.bitstreams),
            "actions": list(self.actions),
        }


def fpga_gowin_build_profile() -> FpgaGowinBuildProfile:
    return FpgaGowinBuildProfile(
        story=FPGA_GOWIN_BUILD_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        package=fpga_first_test.TARGET_IDE_PACKAGE,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        build_root=fpga_synthesis.FPGA_SYNTHESIS_BUILD_ROOT,
        identity_gate=fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        constraints_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        synthesis_gate=fpga_synthesis.FPGA_SYNTHESIS_TOOL,
        steps=(
            GowinBuildStep(
                name="identity_audit",
                command="python tools\\fpga_board_identity.py --audit-evidence",
                prerequisite="physical board marking or programmer/JTAG scan captured",
                output="confirmed I24-S01 device/package evidence",
            ),
            GowinBuildStep(
                name="constraints_audit",
                command="python tools\\fpga_constraints_overlay.py --audit-evidence",
                prerequisite="confirmed identity plus Sipeed All PIN Constraints pin evidence",
                output="final CST generated from verified pins and the checked SDC",
            ),
            GowinBuildStep(
                name="emit_gowin_tcl",
                command="python tools\\fpga_synthesis_gate.py --gowin-tcl",
                prerequisite="verified target device, CST, and SDC",
                output="build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
            ),
            GowinBuildStep(
                name="gowin_run_all",
                command="gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
                prerequisite="Gowin EDA command shell on PATH",
                output="synthesis, place-route, timing, ports, utilization, and bitstream artifacts",
            ),
            GowinBuildStep(
                name="report_audit",
                command="python tools\\fpga_gowin_build.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
                prerequisite="Gowin reports generated by run all",
                output="passed/failed report-bundle audit for I24-S04 programming handoff",
            ),
        ),
        report_requirements=(
            GowinReportRequirement(
                name="synthesis_report",
                glob="impl/gwsynthesis/*.rpt",
                required_tokens=("cpu_v01_fpga_top", "cpu_v01_core"),
                forbidden_tokens=("black box", "unresolved", "error"),
                failure_condition="memory_or_core_black_box",
            ),
            GowinReportRequirement(
                name="timing_report",
                glob="impl/pnr/*timing*.rpt",
                required_tokens=("Slack", "board_clk_i"),
                forbidden_tokens=("Slack -", "VIOLATED", "negative slack", "unconstrained"),
                failure_condition="negative_timing_slack_at_first_test_clock",
            ),
            GowinReportRequirement(
                name="ports_report",
                glob="impl/pnr/*ports*.rpt",
                required_tokens=(
                    "board_clk_i",
                    "board_reset_n_i",
                    "pass_led_o",
                    "fail_led_o",
                    "heartbeat_led_o",
                ),
                forbidden_tokens=("unassigned", "not constrained", "No LOC"),
                failure_condition="missing_pass_fail_observation_pin",
            ),
            GowinReportRequirement(
                name="utilization_report",
                glob="impl/pnr/*util*.rpt",
                required_tokens=("LUT", "Register"),
                forbidden_tokens=("error", "failed"),
                failure_condition="missing_utilization_report",
            ),
            GowinReportRequirement(
                name="bitstream",
                glob="impl/pnr/*.fs",
                required_tokens=(),
                forbidden_tokens=(),
                failure_condition="missing_bitstream",
            ),
        ),
        blockers=(
            "I24-S01 identity evidence must audit as confirmed",
            "I24-S02 constraint evidence and final CST must audit as confirmed",
            "Gowin EDA must run run all for the checked target",
            "reports must prove no black boxes, no unconstrained paths, nonnegative timing slack, assigned status pins, utilization, and a bitstream",
        ),
    )


def fpga_gowin_build_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_gowin_build_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def fpga_gowin_command_plan(
    profile: FpgaGowinBuildProfile | None = None,
) -> tuple[str, ...]:
    if profile is None:
        profile = fpga_gowin_build_profile()
    return tuple(step.command for step in profile.steps)


def audit_gowin_report_bundle(
    build_root: Path,
    *,
    identity_audit: fpga_board_identity.BoardIdentityAudit | None = None,
    constraints_audit: fpga_constraints.ConstraintOverlayAudit | None = None,
    profile: FpgaGowinBuildProfile | None = None,
) -> GowinReportAudit:
    if profile is None:
        profile = fpga_gowin_build_profile()
    if identity_audit is None:
        identity_audit = fpga_board_identity.load_identity_audit()
    if constraints_audit is None:
        constraints_audit = fpga_constraints.load_constraint_overlay_audit()

    build_root_text = build_root.as_posix()
    if not identity_audit.confirmed or not constraints_audit.confirmed:
        return GowinReportAudit(
            status=GOWIN_AUDIT_BLOCKED,
            message="Gowin build audit is blocked until identity and constraints are confirmed.",
            build_root=build_root_text,
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            missing_reports=tuple(requirement.name for requirement in profile.report_requirements),
            token_issues=(),
            failure_markers=(),
            bitstreams=(),
            actions=(
                "complete I24-S01 identity evidence",
                "complete I24-S02 constraints evidence and final CST",
                "run gw_sh after prerequisites are confirmed",
            ),
        )

    missing_reports: list[str] = []
    token_issues: list[str] = []
    failure_markers: list[str] = []
    bitstreams: list[str] = []

    for requirement in profile.report_requirements:
        matches = sorted(build_root.glob(requirement.glob))
        if not matches:
            missing_reports.append(requirement.name)
            continue
        if requirement.name == "bitstream":
            bitstreams.extend(path.as_posix() for path in matches)
            continue
        text = "\n".join(_read_if_exists(path) for path in matches)
        lower_text = text.lower()
        for token in requirement.required_tokens:
            if token not in text:
                token_issues.append(f"{requirement.name} missing {token}")
        for token in requirement.forbidden_tokens:
            if token.lower() in lower_text:
                failure_markers.append(f"{requirement.name} contains {token}")

    if missing_reports:
        return GowinReportAudit(
            status=GOWIN_AUDIT_BLOCKED,
            message="Gowin report bundle is incomplete.",
            build_root=build_root_text,
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            missing_reports=tuple(missing_reports),
            token_issues=tuple(token_issues),
            failure_markers=tuple(failure_markers),
            bitstreams=tuple(bitstreams),
            actions=("rerun gw_sh run all", "capture the missing Gowin reports"),
        )

    if token_issues or failure_markers:
        return GowinReportAudit(
            status=GOWIN_AUDIT_FAILED,
            message="Gowin reports contain failing or incomplete evidence.",
            build_root=build_root_text,
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            missing_reports=(),
            token_issues=tuple(token_issues),
            failure_markers=tuple(failure_markers),
            bitstreams=tuple(bitstreams),
            actions=(
                "fix black boxes, missing ports, unconstrained paths, or timing failures",
                "rerun Gowin and audit reports before programming",
            ),
        )

    return GowinReportAudit(
        status=GOWIN_AUDIT_PASSED,
        message="Gowin report bundle is complete and passes first-test audit checks.",
        build_root=build_root_text,
        identity_status=identity_audit.status,
        constraints_status=constraints_audit.status,
        missing_reports=(),
        token_issues=(),
        failure_markers=(),
        bitstreams=tuple(bitstreams),
        actions=("hand the audited bitstream to I24-S04 SRAM programming",),
    )


def render_fpga_gowin_build(
    profile: FpgaGowinBuildProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_gowin_build_profile()
    lines = [
        "# FPGA Gowin Build",
        "",
        f"Story: {profile.story}",
        "",
        f"Board: `{profile.board}`",
        f"Device: `{profile.device}`",
        f"Package: `{profile.package}`",
        f"Top module: `{profile.top_module}`",
        f"Build root: `{profile.build_root.as_posix()}`",
        f"Identity gate: `{profile.identity_gate}`",
        f"Constraints gate: `{profile.constraints_gate}`",
        f"Synthesis gate: `{profile.synthesis_gate}`",
        "",
        "## Build Steps",
        "",
        "| Step | Command | Prerequisite | Output |",
        "| --- | --- | --- | --- |",
    ]
    for step in profile.steps:
        lines.append(
            f"| `{step.name}` | `{step.command}` | {step.prerequisite} | {step.output} |"
        )
    lines.extend(
        [
            "",
            "## Report Requirements",
            "",
            "| Requirement | Glob | Required tokens | Forbidden tokens | Failure condition |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for requirement in profile.report_requirements:
        required = ", ".join(f"`{token}`" for token in requirement.required_tokens) or "file exists"
        forbidden = ", ".join(f"`{token}`" for token in requirement.forbidden_tokens) or "-"
        lines.append(
            f"| `{requirement.name}` | `{requirement.glob}` | {required} | "
            f"{forbidden} | `{requirement.failure_condition}` |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_gowin_build(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_gowin_build_profile()
    issues: list[str] = []

    if profile.story != FPGA_GOWIN_BUILD_STORY:
        issues.append(f"Gowin build story must be {FPGA_GOWIN_BUILD_STORY}")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("Gowin build board must match first-test profile")
    if profile.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("Gowin build device must match first-test profile")
    if profile.package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("Gowin build package must match first-test profile")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("Gowin build top module must match first-test profile")
    if profile.build_root != fpga_synthesis.FPGA_SYNTHESIS_BUILD_ROOT:
        issues.append("Gowin build root must match I23-S05")

    for check_issues in (
        fpga_board_identity.validate_fpga_board_identity(root),
        fpga_constraints.validate_fpga_constraints_overlay(root),
        fpga_synthesis.validate_fpga_synthesis_gate(root),
    ):
        issues.extend(check_issues)

    step_names = {step.name for step in profile.steps}
    for required in (
        "identity_audit",
        "constraints_audit",
        "emit_gowin_tcl",
        "gowin_run_all",
        "report_audit",
    ):
        if required not in step_names:
            issues.append(f"missing Gowin build step {required}")

    requirements = {requirement.name: requirement for requirement in profile.report_requirements}
    for required in (
        "synthesis_report",
        "timing_report",
        "ports_report",
        "utilization_report",
        "bitstream",
    ):
        if required not in requirements:
            issues.append(f"missing Gowin report requirement {required}")
    if "negative_timing_slack_at_first_test_clock" not in {
        requirement.failure_condition for requirement in profile.report_requirements
    }:
        issues.append("Gowin build must fail on negative timing slack")
    if not any("black box" in requirement.forbidden_tokens for requirement in profile.report_requirements):
        issues.append("Gowin build must fail on black boxes")

    default_audit = audit_gowin_report_bundle(root / profile.build_root)
    if default_audit.status != GOWIN_AUDIT_BLOCKED:
        issues.append("default Gowin build audit must be blocked without physical evidence")

    doc = _read_if_exists(root / FPGA_GOWIN_BUILD_DOC)
    for token in (
        "Story: I24-S03",
        FPGA_GOWIN_BUILD_TOOL,
        "python tools\\fpga_board_identity.py --audit-evidence",
        "python tools\\fpga_constraints_overlay.py --audit-evidence",
        "python tools\\fpga_synthesis_gate.py --gowin-tcl",
        "gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
        "python tools\\fpga_gowin_build.py --audit-reports",
        "GW5AST-LV138PG484A",
        "PBG484A",
        "cpu_v01_fpga_top",
        "timing",
        "utilization",
        "ports",
        "bitstream",
        "black box",
        "unconstrained",
        "negative_timing_slack_at_first_test_clock",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "I24-S04",
        "blocked",
    ):
        if token not in doc:
            issues.append(f"{FPGA_GOWIN_BUILD_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

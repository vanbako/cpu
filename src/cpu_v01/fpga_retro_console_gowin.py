"""Tang Retro Console 60K SOM Gowin build and timing audit gate.

Owner stories:
- I34-S03: run a Retro Console 60K first-test Gowin build and timing audit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_clock_profiles,
    fpga_first_test,
    fpga_gowin_reports,
    fpga_retro_console_constraints,
    fpga_retro_console_identity,
)


JsonValue = Any

FPGA_RETRO_CONSOLE_GOWIN_STORY = "I34-S03"
FPGA_RETRO_CONSOLE_GOWIN_DOC = Path(
    "docs/implementation/fpga-retro-console-gowin-build.md"
)
FPGA_RETRO_CONSOLE_GOWIN_TOOL = "python tools\\fpga_retro_console_gowin.py --check"
FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE = Path(
    "docs/implementation/evidence/i34_s03_retro_console_gowin_build.txt"
)
RETRO_CONSOLE_GOWIN_BUILD_ROOT = Path(
    "build/fpga/tang_60k_retro_console/first_test"
)
RETRO_CONSOLE_GOWIN_RESULT = "retro_console_gowin_build_pass"
RETRO_CONSOLE_GOWIN_STATUS = "blocked_until_retro_console_gowin_reports"

GOWIN_PASS = "passed"
GOWIN_BLOCKED = "blocked"
GOWIN_FAILED = "failed"
GOWIN_INVALID = "invalid"


@dataclass(frozen=True)
class RetroConsoleGowinRequirement:
    name: str
    field: str
    source: str
    required_policy: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "field": self.field,
            "source": self.source,
            "required_policy": self.required_policy,
        }


@dataclass(frozen=True)
class RetroConsoleGowinProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    identity_gate: str
    constraints_gate: str
    clock_profile_gate: str
    report_parser_gate: str
    build_root: Path
    top_module: str
    clock_profile: str
    cst_path: Path
    sdc_path: Path
    gowin_run_command: str
    required_ports: tuple[str, ...]
    requirements: tuple[RetroConsoleGowinRequirement, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "board": self.board,
            "identity_gate": self.identity_gate,
            "constraints_gate": self.constraints_gate,
            "clock_profile_gate": self.clock_profile_gate,
            "report_parser_gate": self.report_parser_gate,
            "build_root": self.build_root.as_posix(),
            "top_module": self.top_module,
            "clock_profile": self.clock_profile,
            "cst_path": self.cst_path.as_posix(),
            "sdc_path": self.sdc_path.as_posix(),
            "gowin_run_command": self.gowin_run_command,
            "required_ports": list(self.required_ports),
            "requirements": [requirement.as_dict() for requirement in self.requirements],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class RetroConsoleGowinRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class RetroConsoleGowinAudit:
    status: str
    message: str
    evidence_path: str
    identity_status: str
    constraints_status: str
    report_status: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    timing_issues: tuple[str, ...]
    policy_issues: tuple[str, ...]
    bitstreams: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == GOWIN_PASS

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "identity_status": self.identity_status,
            "constraints_status": self.constraints_status,
            "report_status": self.report_status,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "timing_issues": list(self.timing_issues),
            "policy_issues": list(self.policy_issues),
            "bitstreams": list(self.bitstreams),
            "actions": list(self.actions),
        }


def fpga_retro_console_gowin_profile() -> RetroConsoleGowinProfile:
    constraints = fpga_retro_console_constraints.retro_console_constraints_overlay()
    return RetroConsoleGowinProfile(
        story=FPGA_RETRO_CONSOLE_GOWIN_STORY,
        status=RETRO_CONSOLE_GOWIN_STATUS,
        evidence_path=FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE,
        board=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD,
        identity_gate=fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        constraints_gate=fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
        clock_profile_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        report_parser_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        build_root=RETRO_CONSOLE_GOWIN_BUILD_ROOT,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        clock_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        cst_path=constraints.cst_path,
        sdc_path=constraints.sdc_path,
        gowin_run_command="gw_sh build/fpga/tang_60k_retro_console/first_test/run_gowin.tcl",
        required_ports=fpga_gowin_reports.REQUIRED_PORTS,
        requirements=(
            RetroConsoleGowinRequirement(
                "identity",
                "identity_evidence",
                fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix(),
                "must audit as alternate_target_verified for the 60K SOM",
            ),
            RetroConsoleGowinRequirement(
                "constraints",
                "constraints_evidence",
                constraints.evidence_path.as_posix(),
                "must audit as confirmed and use final Retro Console CST/SDC files",
            ),
            RetroConsoleGowinRequirement(
                "synthesis",
                "synthesis_report",
                "impl/gwsynthesis/*.rpt",
                "must name cpu_v01_fpga_top and cpu_v01_core with no black boxes",
            ),
            RetroConsoleGowinRequirement(
                "place_route",
                "place_route_report",
                "impl/pnr/*place*.rpt or impl/pnr/*route*.rpt",
                "must capture place-route completion or equivalent PNR report",
            ),
            RetroConsoleGowinRequirement(
                "timing",
                "timing_report",
                "impl/pnr/*timing*.rpt",
                "worst slack must be nonnegative and unconstrained paths must be zero",
            ),
            RetroConsoleGowinRequirement(
                "utilization",
                "utilization_report",
                "impl/pnr/*util*.rpt",
                "must include at least LUT and Register utilization",
            ),
            RetroConsoleGowinRequirement(
                "ports",
                "ports_report",
                "impl/pnr/*ports*.rpt",
                "must assign clock, reset, LEDs, and UART TX from Retro Console pins",
            ),
            RetroConsoleGowinRequirement(
                "warning_policy",
                "warning_policy",
                "Gowin synthesis and PNR logs",
                "must reject black boxes, errors, failed markers, unconstrained paths, and timing violations",
            ),
            RetroConsoleGowinRequirement(
                "bitstream",
                "bitstream_path",
                "impl/pnr/*.fs",
                "must record bitstream path and 64-character SHA-256",
            ),
        ),
        retest_commands=(
            fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
            fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
            fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            "python tools\\fpga_gowin_reports.py --audit-reports build\\fpga\\tang_60k_retro_console\\first_test",
            FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        ),
        blockers=(
            "I34-S01 identity evidence must audit as alternate-target verified",
            "I34-S02 pin evidence and final Retro Console CST/SDC files must audit as confirmed",
            "Gowin EDA must run for the exact recorded 60K Gowin part",
            "reports must prove no black boxes, no unconstrained paths, nonnegative timing slack, assigned status pins, utilization, and a bitstream",
            "I34-S03 evidence must not claim a Tang Mega Dock with 138K SOM board pass",
        ),
        handoffs=(
            "I34-S04 consumes the audited Retro Console bitstream path and SHA-256 for SRAM programming",
            "I34-S05 consumes timing, port, UART, and bitstream identity if board observations fail",
            "I34-S06 consumes the pass/blocker result while the 138K first CPU path remains active",
        ),
    )


def retro_console_gowin_template(
    profile: RetroConsoleGowinProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_gowin_profile()
    retest_commands = " ; ".join(profile.retest_commands)
    required_ports = ",".join(profile.required_ports)
    return "\n".join(
        (
            f"story={profile.story}",
            "captured_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"identity_evidence={fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix()}",
            f"constraints_evidence={fpga_retro_console_constraints.RETRO_CONSOLE_CONSTRAINT_EVIDENCE.as_posix()}",
            f"cst_path={profile.cst_path.as_posix()}",
            f"sdc_path={profile.sdc_path.as_posix()}",
            "gowin_part=",
            f"top_module={profile.top_module}",
            f"clock_profile={profile.clock_profile}",
            f"build_root={profile.build_root.as_posix()}",
            f"gowin_run_command={profile.gowin_run_command}",
            "synthesis_report=build/fpga/tang_60k_retro_console/first_test/impl/gwsynthesis/synth.rpt",
            "place_route_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/place_route.rpt",
            "timing_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_timing.rpt",
            "utilization_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_util.rpt",
            "ports_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/first_ports.rpt",
            "warnings_report=build/fpga/tang_60k_retro_console/first_test/impl/pnr/warnings.rpt",
            "bitstream_path=build/fpga/tang_60k_retro_console/first_test/impl/pnr/retro_first.fs",
            "bitstream_sha256=",
            "worst_slack_ns=",
            "unconstrained_paths=0",
            f"required_ports={required_ports}",
            "port_mapping_status=captured",
            "warning_policy=no_black_boxes_no_errors_no_failed_markers_no_unconstrained_paths",
            "report_parser_audit=python tools\\fpga_gowin_reports.py --audit-reports build\\fpga\\tang_60k_retro_console\\first_test",
            f"build_result={RETRO_CONSOLE_GOWIN_RESULT}",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_retro_console_gowin(text: str) -> RetroConsoleGowinRecord:
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
    return RetroConsoleGowinRecord(fields)


def audit_retro_console_gowin(
    record: RetroConsoleGowinRecord,
    *,
    evidence_path: str = "<inline>",
    profile: RetroConsoleGowinProfile | None = None,
) -> RetroConsoleGowinAudit:
    if profile is None:
        profile = fpga_retro_console_gowin_profile()

    required_fields = (
        "story",
        "captured_at",
        "repository_commit",
        "board",
        "identity_evidence",
        "constraints_evidence",
        "cst_path",
        "sdc_path",
        "gowin_part",
        "top_module",
        "clock_profile",
        "build_root",
        "gowin_run_command",
        "synthesis_report",
        "place_route_report",
        "timing_report",
        "utilization_report",
        "ports_report",
        "warnings_report",
        "bitstream_path",
        "bitstream_sha256",
        "worst_slack_ns",
        "unconstrained_paths",
        "required_ports",
        "port_mapping_status",
        "warning_policy",
        "report_parser_audit",
        "build_result",
        "retest_commands",
    )
    missing_fields = [field for field in required_fields if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I34-S03")

    link_issues = _link_issues(record, profile)
    timing_issues = _timing_issues(record)
    policy_issues = _policy_issues(record, profile)

    if missing_fields:
        return _audit(
            GOWIN_INVALID,
            "Retro Console Gowin evidence is incomplete or malformed.",
            evidence_path,
            record,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            timing_issues=tuple(timing_issues),
            policy_issues=tuple(policy_issues),
            actions=("complete all required I34-S03 fields", "rerun the Retro Console Gowin audit"),
        )
    if link_issues or policy_issues:
        return _audit(
            GOWIN_INVALID,
            "Retro Console Gowin evidence links or policy fields are invalid.",
            evidence_path,
            record,
            link_issues=tuple(link_issues),
            timing_issues=tuple(timing_issues),
            policy_issues=tuple(policy_issues),
            bitstreams=(record.value("bitstream_path"),),
            actions=("fix report links, target identity, bitstream hash, and policy fields",),
        )
    if timing_issues:
        return _audit(
            GOWIN_FAILED,
            "Retro Console Gowin evidence failed timing policy.",
            evidence_path,
            record,
            report_status=fpga_gowin_reports.GOWIN_REPORTS_FAILED,
            timing_issues=tuple(timing_issues),
            bitstreams=(record.value("bitstream_path"),),
            actions=("fix timing or constraints and rerun Gowin before SRAM programming",),
        )
    return _audit(
        GOWIN_PASS,
        "Retro Console Gowin build and timing evidence passes.",
        evidence_path,
        record,
        constraints_status=fpga_retro_console_constraints.CONSTRAINT_CONFIRMED_STATUS,
        report_status=fpga_gowin_reports.GOWIN_REPORTS_PASSED,
        bitstreams=(record.value("bitstream_path"),),
        actions=("hand Retro Console bitstream path and SHA-256 to I34-S04 SRAM programming evidence",),
    )


def audit_retro_console_gowin_reports(
    build_root: Path,
    *,
    identity_audit: fpga_retro_console_identity.RetroConsoleIdentityAudit | None = None,
    constraints_audit: fpga_retro_console_constraints.RetroConstraintAudit | None = None,
    profile: RetroConsoleGowinProfile | None = None,
) -> RetroConsoleGowinAudit:
    if profile is None:
        profile = fpga_retro_console_gowin_profile()
    if identity_audit is None:
        identity_audit = fpga_retro_console_identity.load_identity_audit()
    if constraints_audit is None:
        constraints_audit = fpga_retro_console_constraints.load_constraint_overlay_audit()
    report_audit = fpga_gowin_reports.audit_gowin_reports(
        build_root,
        profile_id=profile.clock_profile,
    )

    if not identity_audit.ready_for_constraints or not constraints_audit.confirmed:
        return _audit(
            GOWIN_BLOCKED,
            "Retro Console Gowin run is blocked until identity and constraints are confirmed.",
            build_root.as_posix(),
            RetroConsoleGowinRecord({}),
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            report_status=report_audit.status,
            link_issues=tuple(report_audit.missing_reports),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("capture I34-S01 identity and I34-S02 pin evidence before Gowin",),
        )
    if report_audit.status == fpga_gowin_reports.GOWIN_REPORTS_BLOCKED:
        return _audit(
            GOWIN_BLOCKED,
            "Retro Console Gowin run is blocked until all reports and bitstream exist.",
            build_root.as_posix(),
            RetroConsoleGowinRecord({}),
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            report_status=report_audit.status,
            link_issues=tuple(report_audit.missing_reports),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("run gw_sh for the exact Retro Console 60K target and capture reports",),
        )
    if not report_audit.passed:
        return _audit(
            GOWIN_FAILED,
            "Retro Console Gowin report policy failed.",
            build_root.as_posix(),
            RetroConsoleGowinRecord({}),
            identity_status=identity_audit.status,
            constraints_status=constraints_audit.status,
            report_status=report_audit.status,
            timing_issues=tuple(_timing_policy_issues(report_audit)),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("fix timing, constraints, ports, utilization, or synthesis failures and rerun Gowin",),
        )
    return _audit(
        GOWIN_PASS,
        "Retro Console Gowin reports are complete and policy-clean.",
        build_root.as_posix(),
        RetroConsoleGowinRecord({}),
        identity_status=identity_audit.status,
        constraints_status=constraints_audit.status,
        report_status=report_audit.status,
        bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
        actions=("record bitstream SHA-256 and hand off to I34-S04 SRAM programming",),
    )


def load_retro_console_gowin_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> RetroConsoleGowinAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_gowin_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        identity = fpga_retro_console_identity.load_identity_audit(root)
        constraints = fpga_retro_console_constraints.load_constraint_overlay_audit(root)
        return RetroConsoleGowinAudit(
            status=GOWIN_BLOCKED,
            message="No Retro Console Gowin build evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            identity_status=identity.status,
            constraints_status=constraints.status,
            report_status=fpga_gowin_reports.GOWIN_REPORTS_BLOCKED,
            missing_fields=(
                "story",
                "captured_at",
                "repository_commit",
                "identity_evidence",
                "constraints_evidence",
                "gowin_part",
                "synthesis_report",
                "place_route_report",
                "timing_report",
                "utilization_report",
                "ports_report",
                "bitstream_path",
                "bitstream_sha256",
                "worst_slack_ns",
                "unconstrained_paths",
                "build_result",
            ),
            link_issues=(),
            timing_issues=(),
            policy_issues=(),
            bitstreams=(),
            actions=(
                f"create {relative_path.as_posix()} from the Retro Console Gowin evidence template",
                "run I34-S03 only after I34-S01 and I34-S02 are confirmed and Gowin reports exist",
            ),
        )
    try:
        record = parse_retro_console_gowin(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _audit(
            GOWIN_INVALID,
            "Retro Console Gowin evidence could not be parsed.",
            relative_path.as_posix(),
            RetroConsoleGowinRecord({}),
            missing_fields=(str(exc),),
            actions=("fix the key=value evidence record", "rerun the I34-S03 audit"),
        )
    return audit_retro_console_gowin(record, evidence_path=relative_path.as_posix(), profile=profile)


def fpga_retro_console_gowin_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_retro_console_gowin_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_retro_console_gowin(
    profile: RetroConsoleGowinProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_retro_console_gowin_profile()
    lines = [
        "# FPGA Retro Console Gowin Build",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Board: `{profile.board}`",
        f"Top module: `{profile.top_module}`",
        f"Clock profile: `{profile.clock_profile}`",
        f"Build root: `{profile.build_root.as_posix()}`",
        f"Gowin run: `{profile.gowin_run_command}`",
        "",
        "## Requirements",
        "",
        "| Requirement | Field | Source | Policy |",
        "| --- | --- | --- | --- |",
    ]
    for requirement in profile.requirements:
        lines.append(
            f"| `{requirement.name}` | `{requirement.field}` | `{requirement.source}` | "
            f"{requirement.required_policy} |"
        )
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_retro_console_gowin(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_retro_console_gowin_profile()
    issues: list[str] = []

    if profile.story != FPGA_RETRO_CONSOLE_GOWIN_STORY:
        issues.append(f"Retro Console Gowin story must be {FPGA_RETRO_CONSOLE_GOWIN_STORY}")
    if profile.status != RETRO_CONSOLE_GOWIN_STATUS:
        issues.append("Retro Console Gowin profile must remain blocked until reports exist")
    if profile.board != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_BOARD:
        issues.append("Retro Console Gowin board must match I34-S01")
    if profile.identity_gate != fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL:
        issues.append("Retro Console Gowin must depend on I34-S01 identity")
    if profile.constraints_gate != fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL:
        issues.append("Retro Console Gowin must depend on I34-S02 constraints")
    if profile.clock_profile_gate != fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL:
        issues.append("Retro Console Gowin must depend on I28-S01 clock profiles")
    if profile.report_parser_gate != fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL:
        issues.append("Retro Console Gowin must depend on the I28-S03 report parser")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("Retro Console Gowin top must be cpu_v01_fpga_top")
    if profile.clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("Retro Console Gowin must use debug_direct_25mhz until report evidence selects another profile")
    if "138k" in profile.build_root.as_posix().lower():
        issues.append("Retro Console Gowin build root must not use the 138K build directory")

    for check_issues in (
        fpga_retro_console_identity.validate_fpga_retro_console_identity(root),
        fpga_retro_console_constraints.validate_fpga_retro_console_constraints(root),
        fpga_clock_profiles.validate_fpga_clock_profiles(root),
        fpga_gowin_reports.validate_fpga_gowin_reports(root),
    ):
        issues.extend(check_issues)

    requirements = {requirement.name: requirement for requirement in profile.requirements}
    for required in (
        "identity",
        "constraints",
        "synthesis",
        "place_route",
        "timing",
        "utilization",
        "ports",
        "warning_policy",
        "bitstream",
    ):
        if required not in requirements:
            issues.append(f"missing Retro Console Gowin requirement {required}")
    for port in fpga_gowin_reports.REQUIRED_PORTS:
        if port not in profile.required_ports:
            issues.append(f"missing Retro Console Gowin required port {port}")

    complete_record = parse_retro_console_gowin(
        retro_console_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-11T22:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("gowin_part=", "gowin_part=GW5AT-60B-scan-recorded")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("worst_slack_ns=", "worst_slack_ns=1.250")
    )
    if not audit_retro_console_gowin(complete_record).passed:
        issues.append("complete Retro Console Gowin record must audit as passed")

    negative_slack = parse_retro_console_gowin(
        retro_console_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-11T22:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("gowin_part=", "gowin_part=GW5AT-60B-scan-recorded")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("worst_slack_ns=", "worst_slack_ns=-0.100")
    )
    if audit_retro_console_gowin(negative_slack).status != GOWIN_FAILED:
        issues.append("negative Retro Console Gowin slack must fail the audit")

    default_audit = load_retro_console_gowin_audit(root)
    if default_audit.status != GOWIN_BLOCKED:
        issues.append("default Retro Console Gowin audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_RETRO_CONSOLE_GOWIN_DOC)
    for token in (
        "Story: I34-S03",
        FPGA_RETRO_CONSOLE_GOWIN_TOOL,
        FPGA_RETRO_CONSOLE_GOWIN_EVIDENCE.as_posix(),
        fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
        fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        "Sipeed Tang Retro Console with 60K SOM",
        "build/fpga/tang_60k_retro_console/first_test",
        "gowin_part",
        "synthesis_report",
        "place_route_report",
        "timing_report",
        "utilization_report",
        "ports_report",
        "warning_policy",
        "bitstream_path",
        "bitstream_sha256",
        "negative_timing_slack_at_first_test_clock",
        "unconstrained_paths",
        "not claim a Tang Mega Dock with 138K SOM pass",
        "I34-S04",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_RETRO_CONSOLE_GOWIN_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"Retro Console Gowin objects are not JSON serializable: {exc}")

    return tuple(issues)


def _audit(
    status: str,
    message: str,
    evidence_path: str,
    record: RetroConsoleGowinRecord,
    *,
    identity_status: str = "unknown",
    constraints_status: str = "unknown",
    report_status: str = "unknown",
    missing_fields: tuple[str, ...] = (),
    link_issues: tuple[str, ...] = (),
    timing_issues: tuple[str, ...] = (),
    policy_issues: tuple[str, ...] = (),
    bitstreams: tuple[str, ...] = (),
    actions: tuple[str, ...] = (),
) -> RetroConsoleGowinAudit:
    return RetroConsoleGowinAudit(
        status=status,
        message=message,
        evidence_path=evidence_path,
        identity_status=identity_status,
        constraints_status=constraints_status,
        report_status=report_status,
        missing_fields=missing_fields,
        link_issues=link_issues,
        timing_issues=timing_issues,
        policy_issues=policy_issues,
        bitstreams=bitstreams,
        actions=actions,
    )


def _link_issues(
    record: RetroConsoleGowinRecord,
    profile: RetroConsoleGowinProfile,
) -> list[str]:
    issues: list[str] = []
    for field in (
        "identity_evidence",
        "constraints_evidence",
        "cst_path",
        "sdc_path",
        "synthesis_report",
        "place_route_report",
        "timing_report",
        "utilization_report",
        "ports_report",
        "warnings_report",
        "bitstream_path",
    ):
        value = record.value(field)
        if value and _is_empty_disposition(value):
            issues.append(f"{field} must link a concrete artifact path")

    expected_values = {
        "board": profile.board,
        "top_module": profile.top_module,
        "clock_profile": profile.clock_profile,
        "build_root": profile.build_root.as_posix(),
        "gowin_run_command": profile.gowin_run_command,
        "identity_evidence": fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE.as_posix(),
        "constraints_evidence": fpga_retro_console_constraints.RETRO_CONSOLE_CONSTRAINT_EVIDENCE.as_posix(),
        "cst_path": profile.cst_path.as_posix(),
        "sdc_path": profile.sdc_path.as_posix(),
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            issues.append(f"{field} must be {expected}")

    for field in (
        "synthesis_report",
        "place_route_report",
        "timing_report",
        "utilization_report",
        "ports_report",
        "warnings_report",
        "bitstream_path",
    ):
        value = record.value(field)
        if value and "tang_60k_retro_console" not in value:
            issues.append(f"{field} must reference the Retro Console 60K build root")
        if value and "tang_mega_138k" in value:
            issues.append(f"{field} must not reference the Tang Mega 138K build root")
    return issues


def _timing_issues(record: RetroConsoleGowinRecord) -> list[str]:
    issues: list[str] = []
    slack = _parse_float(record.value("worst_slack_ns"))
    if record.value("worst_slack_ns") and slack is None:
        issues.append("worst_slack_ns must be numeric")
    elif slack is not None and slack < 0.0:
        issues.append("negative_timing_slack_at_first_test_clock")

    unconstrained = _parse_int(record.value("unconstrained_paths"))
    if record.value("unconstrained_paths") and unconstrained is None:
        issues.append("unconstrained_paths must be an integer")
    elif unconstrained not in (None, 0):
        issues.append("unconstrained_paths_present")
    return issues


def _policy_issues(
    record: RetroConsoleGowinRecord,
    profile: RetroConsoleGowinProfile,
) -> list[str]:
    issues: list[str] = []
    sha = record.value("bitstream_sha256")
    if sha and (len(sha) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha)):
        issues.append("bitstream_sha256 must be a 64-character hex digest")
    if record.value("gowin_part") and "60" not in record.value("gowin_part"):
        issues.append("gowin_part must name the recorded 60K target")
    required_ports = _split_csv(record.value("required_ports"))
    for port in profile.required_ports:
        if required_ports and port not in required_ports:
            issues.append(f"required_ports must include {port}")
    if record.value("port_mapping_status") and record.value("port_mapping_status") != "captured":
        issues.append("port_mapping_status must be captured")
    if record.value("warning_policy") and not _mentions_all(
        record.value("warning_policy").lower(),
        "black",
        "error",
        "failed",
        "unconstrained",
    ):
        issues.append("warning_policy must reject black boxes, errors, failed markers, and unconstrained paths")
    if record.value("build_result") != RETRO_CONSOLE_GOWIN_RESULT:
        issues.append("build_result must be retro_console_gowin_build_pass")
    retest = record.value("retest_commands")
    for command in (
        fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_TOOL,
        fpga_retro_console_constraints.FPGA_RETRO_CONSOLE_CONSTRAINTS_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
    ):
        if retest and command not in retest:
            issues.append(f"retest_commands must include {command}")
    return issues


def _timing_policy_issues(
    report_audit: fpga_gowin_reports.GowinReportPolicyAudit,
) -> tuple[str, ...]:
    return tuple(
        issue
        for issue in report_audit.policy_violations
        if issue
        in {
            "negative_timing_slack_at_first_test_clock",
            "unconstrained_paths_present",
            "missing_timing_slack",
        }
    )


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _mentions_all(value: str, *tokens: str) -> bool:
    return all(token in value for token in tokens)


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

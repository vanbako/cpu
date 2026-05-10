"""First-pass integrated SoC Gowin build and timing audit gate.

Owner stories:
- I31-S02: run Gowin build and timing audit for the integrated SoC top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_clock_profiles,
    fpga_first_pass_bundle,
    fpga_first_test,
    fpga_gowin_build,
    fpga_gowin_reports,
    fpga_reproducible_build,
)


JsonValue = Any

FPGA_FIRST_PASS_GOWIN_STORY = "I31-S02"
FPGA_FIRST_PASS_GOWIN_DOC = Path("docs/implementation/fpga-first-pass-gowin-build.md")
FPGA_FIRST_PASS_GOWIN_TOOL = "python tools\\fpga_first_pass_gowin.py --check"
FPGA_FIRST_PASS_GOWIN_EVIDENCE = Path(
    "docs/implementation/evidence/i31_s02_gowin_build_timing.txt"
)
FPGA_FIRST_PASS_GOWIN_RESULT = "gowin_build_pass"
FIRST_PASS_GOWIN_PROFILE_STATUS = "blocked_until_gowin_reports"

GOWIN_PASS = "passed"
GOWIN_BLOCKED = "blocked"
GOWIN_FAILED = "failed"
GOWIN_INVALID = "invalid"


@dataclass(frozen=True)
class FirstPassGowinRequirement:
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
class FirstPassGowinProfile:
    story: str
    status: str
    evidence_path: Path
    bundle_gate: str
    gowin_build_gate: str
    gowin_reports_gate: str
    reproducible_build_gate: str
    board: str
    top_module: str
    selected_image: str
    build_root: Path
    clock_profile: str
    gowin_run_command: str
    required_ports: tuple[str, ...]
    requirements: tuple[FirstPassGowinRequirement, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def requirement_by_name(self, name: str) -> FirstPassGowinRequirement:
        for requirement in self.requirements:
            if requirement.name == name:
                return requirement
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "bundle_gate": self.bundle_gate,
            "gowin_build_gate": self.gowin_build_gate,
            "gowin_reports_gate": self.gowin_reports_gate,
            "reproducible_build_gate": self.reproducible_build_gate,
            "board": self.board,
            "top_module": self.top_module,
            "selected_image": self.selected_image,
            "build_root": self.build_root.as_posix(),
            "clock_profile": self.clock_profile,
            "gowin_run_command": self.gowin_run_command,
            "required_ports": list(self.required_ports),
            "requirements": [requirement.as_dict() for requirement in self.requirements],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstPassGowinRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstPassGowinAudit:
    status: str
    message: str
    evidence_path: str
    bundle_status: str
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
            "bundle_status": self.bundle_status,
            "report_status": self.report_status,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "timing_issues": list(self.timing_issues),
            "policy_issues": list(self.policy_issues),
            "bitstreams": list(self.bitstreams),
            "actions": list(self.actions),
        }


def fpga_first_pass_gowin_profile() -> FirstPassGowinProfile:
    bundle = fpga_first_pass_bundle.fpga_first_pass_bundle_profile()
    build = fpga_gowin_build.fpga_gowin_build_profile()
    parser = fpga_gowin_reports.fpga_gowin_report_parser_profile()
    return FirstPassGowinProfile(
        story=FPGA_FIRST_PASS_GOWIN_STORY,
        status=FIRST_PASS_GOWIN_PROFILE_STATUS,
        evidence_path=FPGA_FIRST_PASS_GOWIN_EVIDENCE,
        bundle_gate=fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_TOOL,
        gowin_build_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        gowin_reports_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        reproducible_build_gate=fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        board=fpga_first_test.TARGET_BOARD_NAME,
        top_module=bundle.top_module,
        selected_image=bundle.selected_image,
        build_root=build.build_root,
        clock_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        gowin_run_command="gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
        required_ports=parser.required_ports,
        requirements=(
            FirstPassGowinRequirement(
                "synthesis",
                "synthesis_report",
                "impl/gwsynthesis/*.rpt",
                "must name cpu_v01_fpga_top and cpu_v01_core with no black boxes",
            ),
            FirstPassGowinRequirement(
                "place_route",
                "place_route_report",
                "impl/pnr/*place*.rpt or impl/pnr/*route*.rpt",
                "must capture place-route completion or equivalent PNR report",
            ),
            FirstPassGowinRequirement(
                "timing",
                "timing_report",
                "impl/pnr/*timing*.rpt",
                "worst slack must be nonnegative and unconstrained paths must be zero",
            ),
            FirstPassGowinRequirement(
                "utilization",
                "utilization_report",
                "impl/pnr/*util*.rpt",
                "must include at least LUT and Register utilization",
            ),
            FirstPassGowinRequirement(
                "ports",
                "ports_report",
                "impl/pnr/*ports*.rpt",
                "must assign clock, reset, LEDs, and UART TX",
            ),
            FirstPassGowinRequirement(
                "warning_policy",
                "warning_policy",
                "Gowin synthesis and PNR logs",
                "must reject black boxes, errors, failed markers, unconstrained paths, and timing violations",
            ),
            FirstPassGowinRequirement(
                "bitstream",
                "bitstream_path",
                "impl/pnr/*.fs",
                "must record bitstream path and 64-character SHA-256",
            ),
        ),
        retest_commands=(
            fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_TOOL,
            fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            "python tools\\fpga_gowin_reports.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        ),
        blockers=(
            "I31-S01 first-pass bundle must be frozen before Gowin is run",
            "Gowin reports and bitstream are missing until gw_sh run all completes",
            "negative slack, unconstrained paths, black boxes, missing ports, or failed markers reject the build",
            "bitstream path and bitstream_sha256 must be carried into I31-S03 programming evidence",
        ),
    )


def first_pass_gowin_template(profile: FirstPassGowinProfile | None = None) -> str:
    if profile is None:
        profile = fpga_first_pass_gowin_profile()
    retest_commands = " ; ".join(profile.retest_commands)
    required_ports = ",".join(profile.required_ports)
    return "\n".join(
        (
            f"story={profile.story}",
            "captured_at=",
            "repository_commit=",
            f"first_pass_bundle={fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_EVIDENCE.as_posix()}",
            f"top_module={profile.top_module}",
            f"selected_image={profile.selected_image}",
            f"clock_profile={profile.clock_profile}",
            f"build_root={profile.build_root.as_posix()}",
            f"gowin_run_command={profile.gowin_run_command}",
            "synthesis_report=build/fpga/tang_mega_138k/first_test/impl/gwsynthesis/synth.rpt",
            "place_route_report=build/fpga/tang_mega_138k/first_test/impl/pnr/place_route.rpt",
            "timing_report=build/fpga/tang_mega_138k/first_test/impl/pnr/first_timing.rpt",
            "utilization_report=build/fpga/tang_mega_138k/first_test/impl/pnr/first_util.rpt",
            "ports_report=build/fpga/tang_mega_138k/first_test/impl/pnr/first_ports.rpt",
            "warnings_report=build/fpga/tang_mega_138k/first_test/impl/pnr/warnings.rpt",
            "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
            "bitstream_sha256=",
            "worst_slack_ns=",
            "unconstrained_paths=0",
            f"required_ports={required_ports}",
            "warning_policy=no_black_boxes_no_errors_no_failed_markers_no_unconstrained_paths",
            "gowin_reports_audit=python tools\\fpga_gowin_reports.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
            "gowin_build_audit=python tools\\fpga_gowin_build.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
            f"build_result={FPGA_FIRST_PASS_GOWIN_RESULT}",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_first_pass_gowin(text: str) -> FirstPassGowinRecord:
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
    return FirstPassGowinRecord(fields)


def audit_first_pass_gowin(
    record: FirstPassGowinRecord,
    *,
    evidence_path: str = "<inline>",
    profile: FirstPassGowinProfile | None = None,
) -> FirstPassGowinAudit:
    if profile is None:
        profile = fpga_first_pass_gowin_profile()

    required_fields = (
        "story",
        "captured_at",
        "repository_commit",
        "first_pass_bundle",
        "top_module",
        "selected_image",
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
        "warning_policy",
        "gowin_reports_audit",
        "gowin_build_audit",
        "build_result",
        "retest_commands",
    )
    missing_fields = [field for field in required_fields if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I31-S02")

    link_issues: list[str] = []
    for field in (
        "first_pass_bundle",
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
            link_issues.append(f"{field} must link a concrete artifact path")

    expected_values = {
        "top_module": profile.top_module,
        "selected_image": profile.selected_image,
        "clock_profile": profile.clock_profile,
        "build_root": profile.build_root.as_posix(),
        "gowin_run_command": profile.gowin_run_command,
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            link_issues.append(f"{field} must be {expected}")

    if record.value("first_pass_bundle") and "i31_s01" not in record.value("first_pass_bundle").lower():
        link_issues.append("first_pass_bundle must reference the I31-S01 bundle")

    timing_issues: list[str] = []
    slack = _parse_float(record.value("worst_slack_ns"))
    if record.value("worst_slack_ns") and slack is None:
        timing_issues.append("worst_slack_ns must be numeric")
    elif slack is not None and slack < 0.0:
        timing_issues.append("negative_timing_slack_at_first_test_clock")

    unconstrained = _parse_int(record.value("unconstrained_paths"))
    if record.value("unconstrained_paths") and unconstrained is None:
        timing_issues.append("unconstrained_paths must be an integer")
    elif unconstrained not in (None, 0):
        timing_issues.append("unconstrained_paths_present")

    policy_issues: list[str] = []
    sha = record.value("bitstream_sha256")
    if sha and (len(sha) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha)):
        policy_issues.append("bitstream_sha256 must be a 64-character hex digest")
    required_ports = _split_csv(record.value("required_ports"))
    for port in profile.required_ports:
        if required_ports and port not in required_ports:
            policy_issues.append(f"required_ports must include {port}")
    if record.value("warning_policy") and not _mentions_all(
        record.value("warning_policy").lower(),
        "black",
        "error",
        "failed",
        "unconstrained",
    ):
        policy_issues.append("warning_policy must reject black boxes, errors, failed markers, and unconstrained paths")
    if record.value("build_result") != FPGA_FIRST_PASS_GOWIN_RESULT:
        policy_issues.append("build_result must be gowin_build_pass")
    retest = record.value("retest_commands")
    for command in (
        fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
    ):
        if retest and command not in retest:
            policy_issues.append(f"retest_commands must include {command}")

    if missing_fields:
        return FirstPassGowinAudit(
            status=GOWIN_INVALID,
            message="First-pass Gowin evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            bundle_status="unknown",
            report_status="unknown",
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            timing_issues=tuple(timing_issues),
            policy_issues=tuple(policy_issues),
            bitstreams=(),
            actions=("complete all required Gowin evidence fields", "rerun the I31-S02 audit"),
        )
    if link_issues or policy_issues:
        return FirstPassGowinAudit(
            status=GOWIN_INVALID,
            message="First-pass Gowin evidence links or policy fields are invalid.",
            evidence_path=evidence_path,
            bundle_status="unknown",
            report_status="unknown",
            missing_fields=(),
            link_issues=tuple(link_issues),
            timing_issues=tuple(timing_issues),
            policy_issues=tuple(policy_issues),
            bitstreams=(record.value("bitstream_path"),),
            actions=("fix report links, bitstream identity, and policy fields",),
        )
    if timing_issues:
        return FirstPassGowinAudit(
            status=GOWIN_FAILED,
            message="First-pass Gowin evidence failed timing policy.",
            evidence_path=evidence_path,
            bundle_status="unknown",
            report_status="failed",
            missing_fields=(),
            link_issues=(),
            timing_issues=tuple(timing_issues),
            policy_issues=(),
            bitstreams=(record.value("bitstream_path"),),
            actions=("fix timing or constraints and rerun Gowin before programming",),
        )
    return FirstPassGowinAudit(
        status=GOWIN_PASS,
        message="First-pass Gowin build and timing evidence passes.",
        evidence_path=evidence_path,
        bundle_status=fpga_first_pass_bundle.BUNDLE_FROZEN,
        report_status=fpga_gowin_reports.GOWIN_REPORTS_PASSED,
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=(record.value("bitstream_path"),),
        actions=("hand bitstream path and SHA-256 to I31-S03 SRAM programming evidence",),
    )


def audit_first_pass_gowin_reports(
    build_root: Path,
    *,
    bundle_audit: fpga_first_pass_bundle.FirstPassBundleAudit | None = None,
    profile: FirstPassGowinProfile | None = None,
) -> FirstPassGowinAudit:
    if profile is None:
        profile = fpga_first_pass_gowin_profile()
    if bundle_audit is None:
        bundle_audit = fpga_first_pass_bundle.load_first_pass_bundle_audit()
    report_audit = fpga_gowin_reports.audit_gowin_reports(
        build_root,
        profile_id=profile.clock_profile,
    )

    if not bundle_audit.passed:
        return FirstPassGowinAudit(
            status=GOWIN_BLOCKED,
            message="First-pass Gowin run is blocked until the I31-S01 bundle is frozen.",
            evidence_path=build_root.as_posix(),
            bundle_status=bundle_audit.status,
            report_status=report_audit.status,
            missing_fields=(),
            link_issues=tuple(report_audit.missing_reports),
            timing_issues=(),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("freeze the I31-S01 bundle before consuming Gowin reports",),
        )
    if report_audit.status == fpga_gowin_reports.GOWIN_REPORTS_BLOCKED:
        return FirstPassGowinAudit(
            status=GOWIN_BLOCKED,
            message="First-pass Gowin run is blocked until all reports and bitstream exist.",
            evidence_path=build_root.as_posix(),
            bundle_status=bundle_audit.status,
            report_status=report_audit.status,
            missing_fields=(),
            link_issues=tuple(report_audit.missing_reports),
            timing_issues=(),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("run gw_sh and capture the complete report bundle",),
        )
    if not report_audit.passed:
        return FirstPassGowinAudit(
            status=GOWIN_FAILED,
            message="First-pass Gowin report policy failed.",
            evidence_path=build_root.as_posix(),
            bundle_status=bundle_audit.status,
            report_status=report_audit.status,
            missing_fields=(),
            link_issues=(),
            timing_issues=tuple(_timing_policy_issues(report_audit)),
            policy_issues=tuple(report_audit.policy_violations),
            bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
            actions=("fix report policy violations and rerun Gowin",),
        )
    return FirstPassGowinAudit(
        status=GOWIN_PASS,
        message="First-pass Gowin reports are complete and policy-clean.",
        evidence_path=build_root.as_posix(),
        bundle_status=bundle_audit.status,
        report_status=report_audit.status,
        missing_fields=(),
        link_issues=(),
        timing_issues=(),
        policy_issues=(),
        bitstreams=tuple(bitstream.path for bitstream in report_audit.parse.bitstreams),
        actions=("record bitstream SHA-256 and hand off to I31-S03 programming",),
    )


def load_first_pass_gowin_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> FirstPassGowinAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_gowin_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return FirstPassGowinAudit(
            status=GOWIN_BLOCKED,
            message="No first-pass Gowin build evidence has been captured yet.",
            evidence_path=relative_path.as_posix(),
            bundle_status=fpga_first_pass_bundle.load_first_pass_bundle_audit(root).status,
            report_status=fpga_gowin_reports.GOWIN_REPORTS_BLOCKED,
            missing_fields=(
                "story",
                "captured_at",
                "repository_commit",
                "first_pass_bundle",
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
                f"create {relative_path.as_posix()} from the Gowin evidence template",
                "run I31-S02 only after I31-S01 is frozen and Gowin reports exist",
            ),
        )
    try:
        record = parse_first_pass_gowin(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return FirstPassGowinAudit(
            status=GOWIN_INVALID,
            message="First-pass Gowin evidence could not be parsed.",
            evidence_path=relative_path.as_posix(),
            bundle_status="unknown",
            report_status="unknown",
            missing_fields=(str(exc),),
            link_issues=(),
            timing_issues=(),
            policy_issues=(),
            bitstreams=(),
            actions=("fix the key=value evidence record", "rerun the I31-S02 audit"),
        )
    return audit_first_pass_gowin(record, evidence_path=relative_path.as_posix(), profile=profile)


def fpga_first_pass_gowin_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_gowin_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_gowin(
    profile: FirstPassGowinProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_gowin_profile()
    lines = [
        "# FPGA First-Pass Gowin Build",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Top module: `{profile.top_module}`",
        f"Selected image: `{profile.selected_image}`",
        f"Clock profile: `{profile.clock_profile}`",
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


def validate_fpga_first_pass_gowin(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_gowin_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_GOWIN_STORY:
        issues.append(f"first-pass Gowin story must be {FPGA_FIRST_PASS_GOWIN_STORY}")
    if profile.status != FIRST_PASS_GOWIN_PROFILE_STATUS:
        issues.append("first-pass Gowin profile must remain blocked until reports exist")
    if profile.bundle_gate != fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_TOOL:
        issues.append("first-pass Gowin must depend on I31-S01")
    if profile.gowin_reports_gate != fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL:
        issues.append("first-pass Gowin must depend on the I28-S03 report parser")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("first-pass Gowin top must be cpu_v01_fpga_top")
    if profile.selected_image != fpga_first_pass_bundle.FPGA_FIRST_PASS_SELECTED_IMAGE:
        issues.append("first-pass Gowin selected image must match I31-S01")
    if profile.clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("first-pass Gowin must use debug_direct_25mhz")

    for check_issues in (
        fpga_first_pass_bundle.validate_fpga_first_pass_bundle(root),
        fpga_gowin_build.validate_fpga_gowin_build(root),
        fpga_gowin_reports.validate_fpga_gowin_reports(root),
        fpga_reproducible_build.validate_fpga_reproducible_build(root),
    ):
        issues.extend(check_issues)

    requirements = {requirement.name: requirement for requirement in profile.requirements}
    for required in (
        "synthesis",
        "place_route",
        "timing",
        "utilization",
        "ports",
        "warning_policy",
        "bitstream",
    ):
        if required not in requirements:
            issues.append(f"missing first-pass Gowin requirement {required}")
    for port in fpga_gowin_reports.REQUIRED_PORTS:
        if port not in profile.required_ports:
            issues.append(f"missing first-pass Gowin required port {port}")

    complete_record = parse_first_pass_gowin(
        first_pass_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("worst_slack_ns=", "worst_slack_ns=1.250")
    )
    if not audit_first_pass_gowin(complete_record).passed:
        issues.append("complete first-pass Gowin record must audit as passed")

    negative_slack = parse_first_pass_gowin(
        first_pass_gowin_template()
        .replace("captured_at=", "captured_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace(
            "bitstream_sha256=",
            "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        )
        .replace("worst_slack_ns=", "worst_slack_ns=-0.100")
    )
    if audit_first_pass_gowin(negative_slack).status != GOWIN_FAILED:
        issues.append("negative first-pass Gowin slack must fail the audit")

    default_audit = load_first_pass_gowin_audit(root)
    if default_audit.status != GOWIN_BLOCKED:
        issues.append("default first-pass Gowin audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_GOWIN_DOC)
    for token in (
        "Story: I31-S02",
        FPGA_FIRST_PASS_GOWIN_TOOL,
        FPGA_FIRST_PASS_GOWIN_EVIDENCE.as_posix(),
        fpga_first_pass_bundle.FPGA_FIRST_PASS_BUNDLE_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
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
        "I31-S03",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_GOWIN_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass Gowin objects are not JSON serializable: {exc}")

    return tuple(issues)


def _timing_policy_issues(report_audit: fpga_gowin_reports.GowinReportPolicyAudit) -> tuple[str, ...]:
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

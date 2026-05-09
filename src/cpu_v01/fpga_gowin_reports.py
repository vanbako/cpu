"""Automated Gowin report parser and CI-style policy audit.

Owner stories:
- I28-S03: parse Gowin timing, utilization, ports, warnings, and bitstream reports.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_clock_profiles, fpga_gowin_build


JsonValue = Any

FPGA_GOWIN_REPORTS_STORY = "I28-S03"
FPGA_GOWIN_REPORTS_DOC = Path("docs/implementation/fpga-gowin-report-parser.md")
FPGA_GOWIN_REPORTS_TOOL = "python tools\\fpga_gowin_reports.py --check"
FPGA_GOWIN_REPORTS_DEFAULT_PROFILE = fpga_clock_profiles.DEBUG_PROFILE_ID
GOWIN_REPORTS_PASSED = "passed"
GOWIN_REPORTS_BLOCKED = "blocked"
GOWIN_REPORTS_FAILED = "failed"

REQUIRED_PORTS = (
    "board_clk_i",
    "board_reset_n_i",
    "pass_led_o",
    "fail_led_o",
    "heartbeat_led_o",
    "uart_tx_o",
)
REQUIRED_UTILIZATION_METRICS = ("LUT", "Register")
POLICY_FORBIDDEN_TOKENS = (
    "black box",
    "unresolved",
    "negative slack",
    "violated",
)


@dataclass(frozen=True)
class GowinReportParserProfile:
    story: str
    build_root: Path
    clock_profile_gate: str
    gowin_build_gate: str
    default_clock_profile: str
    report_globs: dict[str, str]
    required_ports: tuple[str, ...]
    required_utilization_metrics: tuple[str, ...]
    policy_checks: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "build_root": self.build_root.as_posix(),
            "clock_profile_gate": self.clock_profile_gate,
            "gowin_build_gate": self.gowin_build_gate,
            "default_clock_profile": self.default_clock_profile,
            "report_globs": dict(self.report_globs),
            "required_ports": list(self.required_ports),
            "required_utilization_metrics": list(self.required_utilization_metrics),
            "policy_checks": list(self.policy_checks),
        }


@dataclass(frozen=True)
class ClockSummary:
    name: str
    frequency_mhz: float | None
    period_ns: float | None
    source: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "frequency_mhz": self.frequency_mhz,
            "period_ns": self.period_ns,
            "source": self.source,
        }


@dataclass(frozen=True)
class PortAssignment:
    signal: str
    assigned: bool
    location: str
    io_standard: str
    source: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "signal": self.signal,
            "assigned": self.assigned,
            "location": self.location,
            "io_standard": self.io_standard,
            "source": self.source,
        }


@dataclass(frozen=True)
class UtilizationMetric:
    name: str
    value: int
    source: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
        }


@dataclass(frozen=True)
class BitstreamIdentity:
    path: str
    size_bytes: int
    sha256: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class GowinReportParse:
    build_root: str
    profile_id: str
    report_paths: dict[str, tuple[str, ...]]
    worst_slack_ns: float | None
    clock_summary: tuple[ClockSummary, ...]
    unconstrained_paths: int
    port_assignments: tuple[PortAssignment, ...]
    utilization: tuple[UtilizationMetric, ...]
    warning_lines: tuple[str, ...]
    error_lines: tuple[str, ...]
    bitstreams: tuple[BitstreamIdentity, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "build_root": self.build_root,
            "profile_id": self.profile_id,
            "report_paths": {kind: list(paths) for kind, paths in self.report_paths.items()},
            "worst_slack_ns": self.worst_slack_ns,
            "clock_summary": [clock.as_dict() for clock in self.clock_summary],
            "unconstrained_paths": self.unconstrained_paths,
            "port_assignments": [port.as_dict() for port in self.port_assignments],
            "utilization": [metric.as_dict() for metric in self.utilization],
            "warning_lines": list(self.warning_lines),
            "error_lines": list(self.error_lines),
            "bitstreams": [bitstream.as_dict() for bitstream in self.bitstreams],
        }


@dataclass(frozen=True)
class GowinReportPolicyAudit:
    status: str
    message: str
    parse: GowinReportParse
    missing_reports: tuple[str, ...]
    missing_ports: tuple[str, ...]
    missing_utilization_metrics: tuple[str, ...]
    policy_violations: tuple[str, ...]
    margin_warnings: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == GOWIN_REPORTS_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "parse": self.parse.as_dict(),
            "missing_reports": list(self.missing_reports),
            "missing_ports": list(self.missing_ports),
            "missing_utilization_metrics": list(self.missing_utilization_metrics),
            "policy_violations": list(self.policy_violations),
            "margin_warnings": list(self.margin_warnings),
            "actions": list(self.actions),
        }


def fpga_gowin_report_parser_profile() -> GowinReportParserProfile:
    return GowinReportParserProfile(
        story=FPGA_GOWIN_REPORTS_STORY,
        build_root=fpga_gowin_build.fpga_gowin_build_profile().build_root,
        clock_profile_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        gowin_build_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        default_clock_profile=FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
        report_globs={
            "synthesis": "impl/gwsynthesis/*.rpt",
            "timing": "impl/pnr/*timing*.rpt",
            "ports": "impl/pnr/*ports*.rpt",
            "utilization": "impl/pnr/*util*.rpt",
            "bitstream": "impl/pnr/*.fs",
        },
        required_ports=REQUIRED_PORTS,
        required_utilization_metrics=REQUIRED_UTILIZATION_METRICS,
        policy_checks=(
            "all required reports and bitstreams exist",
            "worst slack is parsed and nonnegative",
            "unconstrained paths are zero",
            "required status and UART ports have LOC assignments",
            "required utilization metrics are present",
            "black boxes, unresolved modules, errors, and violated timing are rejected",
            "bitstream identity records path, size, and SHA-256",
        ),
    )


def fpga_gowin_report_parser_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_gowin_report_parser_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def parse_gowin_report_bundle(
    build_root: Path,
    *,
    profile_id: str = FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
    parser_profile: GowinReportParserProfile | None = None,
) -> GowinReportParse:
    if parser_profile is None:
        parser_profile = fpga_gowin_report_parser_profile()

    report_paths: dict[str, tuple[str, ...]] = {}
    report_text: dict[str, str] = {}
    for kind, glob in parser_profile.report_globs.items():
        matches = tuple(sorted(build_root.glob(glob)))
        report_paths[kind] = tuple(path.as_posix() for path in matches)
        if kind != "bitstream":
            report_text[kind] = "\n".join(_read_if_exists(path) for path in matches)

    timing_text = report_text.get("timing", "")
    ports_text = report_text.get("ports", "")
    utilization_text = report_text.get("utilization", "")
    all_report_text = "\n".join(report_text.values())

    return GowinReportParse(
        build_root=build_root.as_posix(),
        profile_id=profile_id,
        report_paths=report_paths,
        worst_slack_ns=_parse_worst_slack(timing_text),
        clock_summary=_parse_clock_summary(timing_text),
        unconstrained_paths=_parse_unconstrained_paths(timing_text),
        port_assignments=_parse_ports(ports_text, parser_profile.required_ports),
        utilization=_parse_utilization(utilization_text),
        warning_lines=_matching_lines(all_report_text, ("warning",)),
        error_lines=_matching_lines(all_report_text, ("error", "failed")),
        bitstreams=_bitstream_identities(build_root, parser_profile.report_globs["bitstream"]),
    )


def audit_gowin_reports(
    build_root: Path,
    *,
    profile_id: str = FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
    parser_profile: GowinReportParserProfile | None = None,
) -> GowinReportPolicyAudit:
    if parser_profile is None:
        parser_profile = fpga_gowin_report_parser_profile()
    parsed = parse_gowin_report_bundle(
        build_root,
        profile_id=profile_id,
        parser_profile=parser_profile,
    )
    clock_profile = fpga_clock_profiles.fpga_clock_profile_set().profile_by_id(profile_id)

    missing_reports = tuple(
        kind
        for kind in parser_profile.report_globs
        if not parsed.report_paths.get(kind)
        and kind != "bitstream"
    )
    if not parsed.bitstreams:
        missing_reports = (*missing_reports, "bitstream")

    ports = {port.signal: port for port in parsed.port_assignments}
    missing_ports = tuple(
        signal
        for signal in parser_profile.required_ports
        if signal not in ports or not ports[signal].assigned
    )
    metric_names = {metric.name.lower() for metric in parsed.utilization}
    missing_metrics = tuple(
        metric
        for metric in parser_profile.required_utilization_metrics
        if metric.lower() not in metric_names
    )

    policy_violations: list[str] = []
    margin_warnings: list[str] = []
    all_text = _all_report_text(parsed, build_root)
    lower_text = all_text.lower()

    if parsed.worst_slack_ns is None:
        policy_violations.append("missing_timing_slack")
    elif parsed.worst_slack_ns < clock_profile.minimum_slack_ns:
        policy_violations.append("negative_timing_slack_at_first_test_clock")
    elif parsed.worst_slack_ns < clock_profile.target_slack_ns:
        margin_warnings.append("timing_slack_below_target_margin")

    if parsed.unconstrained_paths > 0 or _has_unconstrained_failure_lines(all_text):
        policy_violations.append("unconstrained_paths_present")
    for token in POLICY_FORBIDDEN_TOKENS:
        if token in lower_text:
            policy_violations.append(f"forbidden_report_token:{token}")
    if any("negative slack" in line.lower() for line in parsed.error_lines):
        policy_violations.append("negative_timing_slack_at_first_test_clock")
    if parsed.error_lines:
        policy_violations.append("gowin_error_or_failed_marker_present")
    if missing_ports:
        policy_violations.append("missing_status_or_uart_observation_pin")
    if missing_metrics:
        policy_violations.append("missing_utilization_metric")

    policy_violations = sorted(set(policy_violations))

    if missing_reports:
        return GowinReportPolicyAudit(
            status=GOWIN_REPORTS_BLOCKED,
            message="Gowin report parser is blocked until the full report bundle exists.",
            parse=parsed,
            missing_reports=missing_reports,
            missing_ports=missing_ports,
            missing_utilization_metrics=missing_metrics,
            policy_violations=tuple(policy_violations),
            margin_warnings=tuple(margin_warnings),
            actions=("run gw_sh run all", "capture timing, utilization, ports, and bitstream outputs"),
        )
    if policy_violations:
        return GowinReportPolicyAudit(
            status=GOWIN_REPORTS_FAILED,
            message="Gowin report parser found CI policy violations.",
            parse=parsed,
            missing_reports=(),
            missing_ports=missing_ports,
            missing_utilization_metrics=missing_metrics,
            policy_violations=tuple(policy_violations),
            margin_warnings=tuple(margin_warnings),
            actions=("fix timing, constraints, ports, utilization, or synthesis failures", "rerun Gowin reports"),
        )
    return GowinReportPolicyAudit(
        status=GOWIN_REPORTS_PASSED,
        message="Gowin report parser found a complete policy-clean report bundle.",
        parse=parsed,
        missing_reports=(),
        missing_ports=(),
        missing_utilization_metrics=(),
        policy_violations=(),
        margin_warnings=tuple(margin_warnings),
        actions=("feed parsed timing and bitstream identity to I28-S04 and I28-S05",),
    )


def render_gowin_report_parser(profile: GowinReportParserProfile | None = None) -> str:
    if profile is None:
        profile = fpga_gowin_report_parser_profile()
    lines = [
        "# FPGA Gowin Report Parser",
        "",
        f"Story: {profile.story}",
        f"Build root: `{profile.build_root.as_posix()}`",
        f"Clock profile gate: `{profile.clock_profile_gate}`",
        f"Gowin build gate: `{profile.gowin_build_gate}`",
        f"Default clock profile: `{profile.default_clock_profile}`",
        "",
        "## Report Globs",
        "",
        "| Kind | Glob |",
        "| --- | --- |",
    ]
    for kind, glob in profile.report_globs.items():
        lines.append(f"| `{kind}` | `{glob}` |")
    lines.extend(["", "## Policy Checks", ""])
    lines.extend(f"- {check}." for check in profile.policy_checks)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_gowin_reports(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_gowin_report_parser_profile()
    issues: list[str] = []

    if profile.story != FPGA_GOWIN_REPORTS_STORY:
        issues.append(f"Gowin report parser story must be {FPGA_GOWIN_REPORTS_STORY}")
    if profile.clock_profile_gate != fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL:
        issues.append("Gowin report parser must depend on I28-S01 clock profiles")
    if profile.gowin_build_gate != fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL:
        issues.append("Gowin report parser must depend on the I24-S03 Gowin build gate")
    if profile.default_clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("Gowin report parser default profile must be debug_direct_25mhz")
    for required in ("synthesis", "timing", "ports", "utilization", "bitstream"):
        if required not in profile.report_globs:
            issues.append(f"missing Gowin parser report glob {required}")
    for required in REQUIRED_PORTS:
        if required not in profile.required_ports:
            issues.append(f"missing required parsed port {required}")
    for required in REQUIRED_UTILIZATION_METRICS:
        if required not in profile.required_utilization_metrics:
            issues.append(f"missing required utilization metric {required}")

    issues.extend(fpga_clock_profiles.validate_fpga_clock_profiles(root))
    issues.extend(fpga_gowin_build.validate_fpga_gowin_build(root))

    default_audit = audit_gowin_reports(root / profile.build_root)
    if default_audit.status != GOWIN_REPORTS_BLOCKED:
        issues.append("default Gowin parser audit must be blocked without reports")
    if "bitstream" not in default_audit.missing_reports:
        issues.append("default Gowin parser audit must report missing bitstream identity")

    doc = _read_if_exists(root / FPGA_GOWIN_REPORTS_DOC)
    for token in (
        "Story: I28-S03",
        FPGA_GOWIN_REPORTS_TOOL,
        "python tools\\fpga_clock_profiles.py --check",
        "python tools\\fpga_gowin_build.py --check",
        "python tools\\fpga_gowin_reports.py --audit-reports",
        "worst slack",
        "utilization",
        "unconstrained paths",
        "port assignments",
        "warnings",
        "bitstream identity",
        "clock summary",
        "negative_timing_slack_at_first_test_clock",
        "missing_status_or_uart_observation_pin",
        "I28-S04",
        "I28-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_GOWIN_REPORTS_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(default_audit.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"Gowin report parser objects are not JSON serializable: {exc}")

    return tuple(issues)


def _parse_worst_slack(text: str) -> float | None:
    values: list[float] = []
    patterns = (
        r"\bWorst\s+Slack\b\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)",
        r"\bSlack\b\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            values.append(float(match.group(1)))
    if not values:
        return None
    return min(values)


def _parse_clock_summary(text: str) -> tuple[ClockSummary, ...]:
    clocks: dict[str, ClockSummary] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.search(r"\bClock\b\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        if match is None:
            continue
        name = match.group(1)
        frequency = _first_float_before_unit(line, "MHz")
        period = _first_float_before_unit(line, "ns")
        clocks[name] = ClockSummary(
            name=name,
            frequency_mhz=frequency,
            period_ns=period,
            source=line,
        )
    return tuple(clocks[name] for name in sorted(clocks))


def _parse_unconstrained_paths(text: str) -> int:
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if "unconstrained" not in lower:
            continue
        match = re.search(r"unconstrained\s+paths?\s*[:=]?\s*(\d+)", lower)
        if match is not None:
            count += int(match.group(1))
        elif "0" not in lower:
            count += 1
    return count


def _parse_ports(text: str, required_ports: tuple[str, ...]) -> tuple[PortAssignment, ...]:
    assignments: list[PortAssignment] = []
    for signal in required_ports:
        matching = [line.strip() for line in text.splitlines() if signal in line]
        if not matching:
            continue
        source = matching[-1]
        lower = source.lower()
        assigned = not any(token in lower for token in ("unassigned", "not constrained", "no loc"))
        location_match = re.search(r"\bLOC(?:ATION)?\b\s*[=:]?\s*([A-Za-z0-9_]+)", source)
        io_match = re.search(r"\b(?:IO_TYPE|IOSTANDARD|IO_STANDARD)\b\s*[=:]?\s*([A-Za-z0-9_]+)", source)
        assignments.append(
            PortAssignment(
                signal=signal,
                assigned=assigned,
                location=location_match.group(1) if location_match else "",
                io_standard=io_match.group(1) if io_match else "",
                source=source,
            )
        )
    return tuple(assignments)


def _parse_utilization(text: str) -> tuple[UtilizationMetric, ...]:
    aliases = {
        "LUT": ("LUT", "LUTs"),
        "Register": ("Register", "Registers", "REG"),
        "B-SRAM": ("B-SRAM", "BSRAM", "BRAM"),
    }
    metrics: list[UtilizationMetric] = []
    for canonical, names in aliases.items():
        for raw_line in text.splitlines():
            line = raw_line.strip()
            for name in names:
                match = re.search(
                    rf"\b{re.escape(name)}\b\s*[:=]?\s*(\d+)",
                    line,
                    flags=re.IGNORECASE,
                )
                if match is not None:
                    metrics.append(
                        UtilizationMetric(
                            name=canonical,
                            value=int(match.group(1)),
                            source=line,
                        )
                    )
                    break
            if metrics and metrics[-1].name == canonical:
                break
    return tuple(metrics)


def _bitstream_identities(build_root: Path, glob: str) -> tuple[BitstreamIdentity, ...]:
    identities: list[BitstreamIdentity] = []
    for path in sorted(build_root.glob(glob)):
        if not path.is_file():
            continue
        data = path.read_bytes()
        identities.append(
            BitstreamIdentity(
                path=path.as_posix(),
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
    return tuple(identities)


def _matching_lines(text: str, tokens: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if any(token in lower for token in tokens) and not _is_zero_summary_line(lower):
            lines.append(line)
    return tuple(lines)


def _has_unconstrained_failure_lines(text: str) -> bool:
    for raw_line in text.splitlines():
        lower = raw_line.strip().lower()
        if "unconstrained" in lower and not re.search(r"unconstrained\s+paths?\s*[:=]?\s*0\b", lower):
            return True
    return False


def _is_zero_summary_line(lower_line: str) -> bool:
    return bool(re.search(r"\b(warnings?|errors?|failed)\b\s*[:=]?\s*0\b", lower_line))


def _first_float_before_unit(line: str, unit: str) -> float | None:
    pattern = rf"([-+]?\d+(?:\.\d+)?)\s*{re.escape(unit)}\b"
    match = re.search(pattern, line, flags=re.IGNORECASE)
    if match is None:
        return None
    return float(match.group(1))


def _all_report_text(parsed: GowinReportParse, build_root: Path) -> str:
    chunks: list[str] = []
    for kind, paths in parsed.report_paths.items():
        if kind == "bitstream":
            continue
        for raw_path in paths:
            path = Path(raw_path)
            if not path.is_absolute() and not path.exists():
                path = build_root / path.relative_to(build_root) if raw_path.startswith(build_root.as_posix()) else path
            chunks.append(_read_if_exists(path))
    return "\n".join(chunks)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

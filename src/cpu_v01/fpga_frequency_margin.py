"""FPGA frequency sweep and conservative default selection profile.

Owner stories:
- I28-S04: track maximum passing first-test clock and select conservative defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_clock_profiles, fpga_gowin_reports


JsonValue = Any

FPGA_FREQUENCY_MARGIN_STORY = "I28-S04"
FPGA_FREQUENCY_MARGIN_DOC = Path("docs/implementation/fpga-frequency-margin.md")
FPGA_FREQUENCY_MARGIN_TOOL = "python tools\\fpga_frequency_margin.py --check"
FPGA_FREQUENCY_EVIDENCE = Path("docs/implementation/evidence/i28_s04_frequency_sweep.json")
CONSERVATIVE_DEFAULT_HZ = fpga_clock_profiles.BOARD_CLOCK_HZ
DEFAULT_MARGIN_STATUS = "documented_blocker"


@dataclass(frozen=True)
class FrequencySweepPoint:
    profile_id: str
    requested_hz: int
    build_root: str
    report_status: str
    worst_slack_ns: float | None
    target_margin_met: bool
    bitstream_sha256: str
    policy_violations: tuple[str, ...]
    margin_warnings: tuple[str, ...]
    notes: str

    @property
    def passed(self) -> bool:
        return self.report_status == fpga_gowin_reports.GOWIN_REPORTS_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "profile_id": self.profile_id,
            "requested_hz": self.requested_hz,
            "build_root": self.build_root,
            "report_status": self.report_status,
            "worst_slack_ns": self.worst_slack_ns,
            "target_margin_met": self.target_margin_met,
            "bitstream_sha256": self.bitstream_sha256,
            "policy_violations": list(self.policy_violations),
            "margin_warnings": list(self.margin_warnings),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FrequencySweepSummary:
    story: str
    status: str
    evidence_path: Path
    parser_gate: str
    clock_profile_gate: str
    current_default_profile: str
    selected_debug_default_hz: int
    selected_release_default_hz: int
    maximum_passing_hz: int | None
    maximum_passing_profile: str
    points: tuple[FrequencySweepPoint, ...]
    blockers: tuple[str, ...]
    handoffs: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "parser_gate": self.parser_gate,
            "clock_profile_gate": self.clock_profile_gate,
            "current_default_profile": self.current_default_profile,
            "selected_debug_default_hz": self.selected_debug_default_hz,
            "selected_release_default_hz": self.selected_release_default_hz,
            "maximum_passing_hz": self.maximum_passing_hz,
            "maximum_passing_profile": self.maximum_passing_profile,
            "points": [point.as_dict() for point in self.points],
            "blockers": list(self.blockers),
            "handoffs": list(self.handoffs),
        }


def fpga_frequency_margin_summary(
    points: tuple[FrequencySweepPoint, ...] = (),
) -> FrequencySweepSummary:
    passing = tuple(point for point in points if point.passed)
    maximum = max((point.requested_hz for point in passing), default=None)
    maximum_profile = ""
    if maximum is not None:
        for point in passing:
            if point.requested_hz == maximum:
                maximum_profile = point.profile_id
                break
    status = "evidence_recorded" if passing else DEFAULT_MARGIN_STATUS

    return FrequencySweepSummary(
        story=FPGA_FREQUENCY_MARGIN_STORY,
        status=status,
        evidence_path=FPGA_FREQUENCY_EVIDENCE,
        parser_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        clock_profile_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        current_default_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        selected_debug_default_hz=CONSERVATIVE_DEFAULT_HZ,
        selected_release_default_hz=CONSERVATIVE_DEFAULT_HZ,
        maximum_passing_hz=maximum,
        maximum_passing_profile=maximum_profile,
        points=tuple(sorted(points, key=lambda point: point.requested_hz)),
        blockers=_frequency_blockers(passing),
        handoffs=(
            "I28-S05 must archive the selected clock profile, parsed report bundle, bitstream hash, and sweep summary",
            "I29 external-memory work must not raise the board default before I28 timing margin is recorded",
            "release_pll_25mhz remains conservative until PLL/reset evidence and passing reports exist",
        ),
    )


def sweep_point_from_report_audit(
    audit: fpga_gowin_reports.GowinReportPolicyAudit,
    *,
    requested_hz: int | None = None,
    notes: str = "",
) -> FrequencySweepPoint:
    if requested_hz is None:
        clock_profile = fpga_clock_profiles.fpga_clock_profile_set().profile_by_id(
            audit.parse.profile_id
        )
        requested_hz = clock_profile.source_hz
    bitstream_sha256 = audit.parse.bitstreams[0].sha256 if audit.parse.bitstreams else ""
    return FrequencySweepPoint(
        profile_id=audit.parse.profile_id,
        requested_hz=requested_hz,
        build_root=audit.parse.build_root,
        report_status=audit.status,
        worst_slack_ns=audit.parse.worst_slack_ns,
        target_margin_met="timing_slack_below_target_margin" not in audit.margin_warnings,
        bitstream_sha256=bitstream_sha256,
        policy_violations=audit.policy_violations,
        margin_warnings=audit.margin_warnings,
        notes=notes,
    )


def frequency_evidence_template() -> str:
    template = fpga_frequency_margin_summary().as_dict()
    template["points"] = [
        {
            "profile_id": fpga_clock_profiles.DEBUG_PROFILE_ID,
            "requested_hz": CONSERVATIVE_DEFAULT_HZ,
            "build_root": "build/fpga/tang_mega_138k/first_test",
            "report_status": "passed|failed|blocked",
            "worst_slack_ns": None,
            "target_margin_met": False,
            "bitstream_sha256": "",
            "policy_violations": [],
            "margin_warnings": [],
            "notes": "replace with parsed I28-S03 report evidence",
        }
    ]
    return json.dumps(template, indent=2, sort_keys=True) + "\n"


def fpga_frequency_margin_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_frequency_margin_summary().as_dict(), indent=indent, sort_keys=True)


def render_fpga_frequency_margin(summary: FrequencySweepSummary | None = None) -> str:
    if summary is None:
        summary = fpga_frequency_margin_summary()
    lines = [
        "# FPGA Frequency Margin",
        "",
        f"Story: {summary.story}",
        f"Status: `{summary.status}`",
        f"Evidence path: `{summary.evidence_path.as_posix()}`",
        f"Parser gate: `{summary.parser_gate}`",
        f"Clock profile gate: `{summary.clock_profile_gate}`",
        f"Current default profile: `{summary.current_default_profile}`",
        f"Debug default: {summary.selected_debug_default_hz} Hz",
        f"Release default: {summary.selected_release_default_hz} Hz",
        f"Maximum passing: {summary.maximum_passing_hz if summary.maximum_passing_hz is not None else 'none'}",
        "",
        "## Sweep Points",
        "",
        "| Profile | Requested Hz | Status | Worst slack | Target margin | Bitstream |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for point in summary.points:
        lines.append(
            f"| `{point.profile_id}` | {point.requested_hz} | {point.report_status} | "
            f"{point.worst_slack_ns if point.worst_slack_ns is not None else '-'} | "
            f"{'met' if point.target_margin_met else 'not met'} | "
            f"`{point.bitstream_sha256[:12]}` |"
        )
    if not summary.points:
        lines.append("| - | - | documented_blocker | - | - | - |")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in summary.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_frequency_margin(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    summary = fpga_frequency_margin_summary()
    issues: list[str] = []

    if summary.story != FPGA_FREQUENCY_MARGIN_STORY:
        issues.append(f"frequency margin story must be {FPGA_FREQUENCY_MARGIN_STORY}")
    if summary.parser_gate != fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL:
        issues.append("frequency margin must depend on the I28-S03 report parser")
    if summary.clock_profile_gate != fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL:
        issues.append("frequency margin must depend on I28-S01 clock profiles")
    if summary.current_default_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("frequency margin default profile must be debug_direct_25mhz")
    if summary.selected_debug_default_hz != CONSERVATIVE_DEFAULT_HZ:
        issues.append("debug default frequency must stay at the conservative 25 MHz")
    if summary.selected_release_default_hz != CONSERVATIVE_DEFAULT_HZ:
        issues.append("release default frequency must stay at the conservative 25 MHz")
    if summary.maximum_passing_hz is not None:
        issues.append("default summary must not invent a maximum passing frequency")
    if summary.status != DEFAULT_MARGIN_STATUS:
        issues.append("default summary must be documented_blocker until sweep evidence exists")

    issues.extend(fpga_clock_profiles.validate_fpga_clock_profiles(root))
    issues.extend(fpga_gowin_reports.validate_fpga_gowin_reports(root))

    template = frequency_evidence_template()
    for token in (
        "debug_direct_25mhz",
        "requested_hz",
        "worst_slack_ns",
        "bitstream_sha256",
        "policy_violations",
    ):
        if token not in template:
            issues.append(f"frequency evidence template missing {token}")

    doc = _read_if_exists(root / FPGA_FREQUENCY_MARGIN_DOC)
    for token in (
        "Story: I28-S04",
        FPGA_FREQUENCY_MARGIN_TOOL,
        "python tools\\fpga_gowin_reports.py --check",
        "debug_direct_25mhz",
        "25 MHz",
        "maximum passing",
        "selected_debug_default_hz",
        "selected_release_default_hz",
        "documented_blocker",
        "frequency sweep",
        "worst slack",
        "bitstream_sha256",
        "I28-S05",
        "I29",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FREQUENCY_MARGIN_DOC.as_posix()} missing {token}")

    try:
        json.dumps(summary.as_dict(), sort_keys=True)
        frequency_evidence_template()
    except TypeError as exc:
        issues.append(f"frequency margin objects are not JSON serializable: {exc}")

    return tuple(issues)


def _frequency_blockers(passing: tuple[FrequencySweepPoint, ...]) -> tuple[str, ...]:
    blockers = [
        "no physical Gowin frequency sweep evidence has been captured in docs/implementation/evidence",
        "I24-S01 identity and I24-S02 pin evidence are still blocked",
        "keep debug and release defaults at 25 MHz until parsed report evidence exists",
    ]
    if passing:
        blockers[0] = "frequency evidence exists, but conservative 25 MHz defaults remain selected until release policy changes"
    return tuple(blockers)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

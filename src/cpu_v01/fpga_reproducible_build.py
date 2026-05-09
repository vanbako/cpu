"""Reproducible FPGA build profile and evidence manifest contract.

Owner stories:
- I28-S05: publish a reproducible FPGA build profile.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_board_identity,
    fpga_clock_profiles,
    fpga_constraints,
    fpga_first_test,
    fpga_frequency_margin,
    fpga_gowin_build,
    fpga_gowin_reports,
    fpga_reset_cdc,
    fpga_synthesis,
)


JsonValue = Any

FPGA_REPRO_BUILD_STORY = "I28-S05"
FPGA_REPRO_BUILD_DOC = Path("docs/implementation/fpga-reproducible-build.md")
FPGA_REPRO_BUILD_TOOL = "python tools\\fpga_reproducible_build.py --check"
FPGA_REPRO_BUILD_MANIFEST = Path(
    "docs/implementation/evidence/i28_s05_reproducible_build_manifest.json"
)
FPGA_REPRO_BUILD_STATUS = "documented_blocker"


@dataclass(frozen=True)
class ReproBuildArtifact:
    name: str
    path: str
    required: bool
    producer_gate: str
    captured_status: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "path": self.path,
            "required": self.required,
            "producer_gate": self.producer_gate,
            "captured_status": self.captured_status,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class ReproBuildTool:
    name: str
    executable: str
    version_evidence: str
    required: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "executable": self.executable,
            "version_evidence": self.version_evidence,
            "required": self.required,
        }


@dataclass(frozen=True)
class ReproducibleBuildProfile:
    story: str
    status: str
    manifest_path: Path
    board: str
    device: str
    package: str
    top_module: str
    build_root: Path
    selected_clock_profile: str
    selected_debug_default_hz: int
    selected_release_default_hz: int
    gates: tuple[str, ...]
    tools: tuple[ReproBuildTool, ...]
    artifacts: tuple[ReproBuildArtifact, ...]
    reproduction_steps: tuple[str, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "manifest_path": self.manifest_path.as_posix(),
            "board": self.board,
            "device": self.device,
            "package": self.package,
            "top_module": self.top_module,
            "build_root": self.build_root.as_posix(),
            "selected_clock_profile": self.selected_clock_profile,
            "selected_debug_default_hz": self.selected_debug_default_hz,
            "selected_release_default_hz": self.selected_release_default_hz,
            "gates": list(self.gates),
            "tools": [tool.as_dict() for tool in self.tools],
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "reproduction_steps": list(self.reproduction_steps),
            "blockers": list(self.blockers),
        }


def fpga_reproducible_build_profile() -> ReproducibleBuildProfile:
    frequency = fpga_frequency_margin.fpga_frequency_margin_summary()
    return ReproducibleBuildProfile(
        story=FPGA_REPRO_BUILD_STORY,
        status=FPGA_REPRO_BUILD_STATUS,
        manifest_path=FPGA_REPRO_BUILD_MANIFEST,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        package=fpga_first_test.TARGET_IDE_PACKAGE,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        build_root=fpga_gowin_build.fpga_gowin_build_profile().build_root,
        selected_clock_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        selected_debug_default_hz=frequency.selected_debug_default_hz,
        selected_release_default_hz=frequency.selected_release_default_hz,
        gates=(
            fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
            fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            fpga_synthesis.FPGA_SYNTHESIS_TOOL,
            fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
            fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
            fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            fpga_frequency_margin.FPGA_FREQUENCY_MARGIN_TOOL,
        ),
        tools=(
            ReproBuildTool(
                name="Gowin EDA",
                executable="gw_sh",
                version_evidence="Gowin command-shell version and install path captured in manifest",
                required=True,
            ),
            ReproBuildTool(
                name="Gowin Programmer",
                executable="programmer_cli_or_gui",
                version_evidence="programmer version, cable mode, and SRAM/flash mode captured in board evidence",
                required=True,
            ),
            ReproBuildTool(
                name="Verilator",
                executable="verilator",
                version_evidence="Verilator version captured with pre-Gowin lint/elaboration logs",
                required=True,
            ),
            ReproBuildTool(
                name="Python",
                executable="python",
                version_evidence="Python version and repository commit captured in manifest",
                required=True,
            ),
        ),
        artifacts=_repro_artifacts(),
        reproduction_steps=(
            "confirm I24-S01 device/package evidence",
            "confirm I24-S02 constraints evidence and generate the final CST from verified pins",
            "run python tools\\fpga_synthesis_gate.py --gowin-tcl and archive the generated Tcl",
            "run gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
            "run python tools\\fpga_gowin_reports.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
            "record bitstream SHA-256, selected clock profile, reset/CDC audit, and frequency margin summary",
            "link board programming and first-board evidence before claiming reproducibility",
        ),
        blockers=(
            "I24-S01 identity evidence is not captured",
            "I24-S02 final CST from verified pins is not captured",
            "Gowin reports and bitstream are not present under the build root",
            "I24-S04/I24-S05 board programming and evidence archive are not complete",
        ),
    )


def fpga_reproducible_build_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_reproducible_build_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def reproducible_build_manifest_template() -> str:
    profile = fpga_reproducible_build_profile()
    template = profile.as_dict()
    template["repository_commit"] = ""
    template["gowin_eda_version"] = ""
    template["gowin_programmer_version"] = ""
    template["verilator_version"] = ""
    template["python_version"] = ""
    template["bitstream_sha256"] = ""
    template["board_evidence_path"] = "docs/implementation/evidence/i24_s05_first_board_archive.txt"
    return json.dumps(template, indent=2, sort_keys=True) + "\n"


def render_fpga_reproducible_build(
    profile: ReproducibleBuildProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_reproducible_build_profile()
    lines = [
        "# FPGA Reproducible Build",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Manifest: `{profile.manifest_path.as_posix()}`",
        f"Board: `{profile.board}`",
        f"Device: `{profile.device}`",
        f"Package: `{profile.package}`",
        f"Top module: `{profile.top_module}`",
        f"Build root: `{profile.build_root.as_posix()}`",
        f"Selected clock profile: `{profile.selected_clock_profile}`",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path | Gate | Status |",
        "| --- | --- | --- | --- |",
    ]
    for artifact in profile.artifacts:
        lines.append(
            f"| `{artifact.name}` | `{artifact.path}` | `{artifact.producer_gate}` | "
            f"{artifact.captured_status} |"
        )
    lines.extend(["", "## Reproduction Steps", ""])
    lines.extend(f"{index}. {step}." for index, step in enumerate(profile.reproduction_steps, start=1))
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_reproducible_build(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_reproducible_build_profile()
    issues: list[str] = []

    if profile.story != FPGA_REPRO_BUILD_STORY:
        issues.append(f"reproducible build story must be {FPGA_REPRO_BUILD_STORY}")
    if profile.status != FPGA_REPRO_BUILD_STATUS:
        issues.append("reproducible build must remain documented_blocker until evidence exists")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("reproducible build board must match first-test target")
    if profile.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("reproducible build device must match first-test target")
    if profile.package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("reproducible build package must match first-test target")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("reproducible build top must match first-test target")
    if profile.selected_clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("reproducible build must select the conservative debug clock profile")
    if profile.selected_debug_default_hz != fpga_frequency_margin.CONSERVATIVE_DEFAULT_HZ:
        issues.append("reproducible build debug default must stay at 25 MHz")
    if profile.selected_release_default_hz != fpga_frequency_margin.CONSERVATIVE_DEFAULT_HZ:
        issues.append("reproducible build release default must stay at 25 MHz")

    for check_issues in (
        fpga_reset_cdc.validate_fpga_reset_cdc(root),
        fpga_gowin_reports.validate_fpga_gowin_reports(root),
        fpga_frequency_margin.validate_fpga_frequency_margin(root),
    ):
        issues.extend(check_issues)

    for required_gate in (
        fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
        fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
        fpga_frequency_margin.FPGA_FREQUENCY_MARGIN_TOOL,
    ):
        if required_gate not in profile.gates:
            issues.append(f"missing reproducible build gate {required_gate}")

    artifacts = {artifact.name: artifact for artifact in profile.artifacts}
    for required in (
        "device_package_evidence",
        "constraints_cst_sdc",
        "gowin_tcl",
        "gowin_reports",
        "bitstream_identity",
        "clock_profile",
        "reset_cdc_audit",
        "frequency_margin",
        "board_evidence",
    ):
        if required not in artifacts:
            issues.append(f"missing reproducible build artifact {required}")

    tools = {tool.name for tool in profile.tools}
    for required in ("Gowin EDA", "Gowin Programmer", "Verilator", "Python"):
        if required not in tools:
            issues.append(f"missing reproducible build tool {required}")

    template = reproducible_build_manifest_template()
    for token in (
        "repository_commit",
        "gowin_eda_version",
        "bitstream_sha256",
        "selected_clock_profile",
        "board_evidence_path",
    ):
        if token not in template:
            issues.append(f"reproducible build manifest template missing {token}")

    doc = _read_if_exists(root / FPGA_REPRO_BUILD_DOC)
    for token in (
        "Story: I28-S05",
        FPGA_REPRO_BUILD_TOOL,
        "python tools\\fpga_reset_cdc.py --check",
        "python tools\\fpga_gowin_reports.py --check",
        "python tools\\fpga_frequency_margin.py --check",
        "tool version",
        "device/package",
        "constraints",
        "Tcl",
        "reports",
        "bitstream_sha256",
        "board evidence",
        "debug_direct_25mhz",
        "documented_blocker",
        "I24-S05",
        "I29",
    ):
        if token not in doc:
            issues.append(f"{FPGA_REPRO_BUILD_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        reproducible_build_manifest_template()
    except TypeError as exc:
        issues.append(f"reproducible build objects are not JSON serializable: {exc}")

    return tuple(issues)


def _repro_artifacts() -> tuple[ReproBuildArtifact, ...]:
    return (
        ReproBuildArtifact(
            name="device_package_evidence",
            path="docs/implementation/evidence/i24_s01_device_identity.txt",
            required=True,
            producer_gate=fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
            captured_status="blocked",
            purpose="confirm the exact Tang Mega 138K device, package, and device version",
        ),
        ReproBuildArtifact(
            name="constraints_cst_sdc",
            path="constraints/tang_mega_138k_first_test.cst and constraints/tang_mega_138k_first_test.sdc",
            required=True,
            producer_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            captured_status="blocked",
            purpose="bind verified pins, IO standards, reset false path, and board clock period",
        ),
        ReproBuildArtifact(
            name="gowin_tcl",
            path="build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
            required=True,
            producer_gate=fpga_synthesis.FPGA_SYNTHESIS_TOOL,
            captured_status="template_only",
            purpose="replay the same Gowin source, top, device, CST, and SDC inputs",
        ),
        ReproBuildArtifact(
            name="gowin_reports",
            path="build/fpga/tang_mega_138k/first_test/impl",
            required=True,
            producer_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            captured_status="missing",
            purpose="capture synthesis, timing, ports, utilization, warnings, and clock summary",
        ),
        ReproBuildArtifact(
            name="bitstream_identity",
            path="build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs",
            required=True,
            producer_gate=fpga_gowin_reports.FPGA_GOWIN_REPORTS_TOOL,
            captured_status="missing",
            purpose="record exact bitstream path, size, and bitstream_sha256",
        ),
        ReproBuildArtifact(
            name="clock_profile",
            path="docs/implementation/fpga-clock-profiles.md",
            required=True,
            producer_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            captured_status="documented",
            purpose="record selected debug_direct_25mhz profile and conservative defaults",
        ),
        ReproBuildArtifact(
            name="reset_cdc_audit",
            path="docs/implementation/fpga-reset-cdc-audit.md",
            required=True,
            producer_gate=fpga_reset_cdc.FPGA_RESET_CDC_TOOL,
            captured_status="documented",
            purpose="record reset synchronizers, async-input blockers, and generated-clock status",
        ),
        ReproBuildArtifact(
            name="frequency_margin",
            path=fpga_frequency_margin.FPGA_FREQUENCY_EVIDENCE.as_posix(),
            required=True,
            producer_gate=fpga_frequency_margin.FPGA_FREQUENCY_MARGIN_TOOL,
            captured_status="documented_blocker",
            purpose="record maximum passing clock or explain missing sweep evidence",
        ),
        ReproBuildArtifact(
            name="board_evidence",
            path="docs/implementation/evidence/i24_s05_first_board_archive.txt",
            required=True,
            producer_gate="python tools\\fpga_first_board_archive.py --check",
            captured_status="blocked",
            purpose="link programming log, reset observation, LEDs/probes, and residual blockers",
        ),
    )


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

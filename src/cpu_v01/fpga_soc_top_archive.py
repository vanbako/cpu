"""FPGA SoC top integration closure archive gate.

Owner stories:
- I30-S06: archive SoC top integration closure evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_debug_evidence,
    fpga_replay_mapper,
    fpga_soc_top_smoke,
)


JsonValue = Any

FPGA_SOC_TOP_ARCHIVE_STORY = "I30-S06"
FPGA_SOC_TOP_ARCHIVE_DOC = Path("docs/implementation/fpga-soc-top-archive.md")
FPGA_SOC_TOP_ARCHIVE_TOOL = "python tools\\fpga_soc_top_archive.py --check"
FPGA_SOC_TOP_ARCHIVE_EVIDENCE = Path(
    "docs/implementation/evidence/i30_s06_soc_top_closure_archive.txt"
)
FPGA_SOC_TOP_ARCHIVE_RESULT = "soc_top_closure_pass"
ARCHIVE_ARCHIVED = "archived"
ARCHIVE_BLOCKED = "blocked"
ARCHIVE_INVALID = "invalid"
ARCHIVE_NEEDS_FOLLOWUP = "needs_followup"


@dataclass(frozen=True)
class SocTopArchiveField:
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
class SocTopArchiveProfile:
    story: str
    evidence_path: Path
    required_result: str
    top_module: str
    top_smoke_gate: str
    replay_mapper_gate: str
    debug_evidence_gate: str
    verilator_command: str
    run_command: str
    rtl_sources: tuple[str, ...]
    required_fields: tuple[SocTopArchiveField, ...]
    link_fields: tuple[str, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def field_by_name(self, name: str) -> SocTopArchiveField:
        for field in self.required_fields:
            if field.name == name:
                return field
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "evidence_path": self.evidence_path.as_posix(),
            "required_result": self.required_result,
            "top_module": self.top_module,
            "top_smoke_gate": self.top_smoke_gate,
            "replay_mapper_gate": self.replay_mapper_gate,
            "debug_evidence_gate": self.debug_evidence_gate,
            "verilator_command": self.verilator_command,
            "run_command": self.run_command,
            "rtl_sources": list(self.rtl_sources),
            "required_fields": [field.as_dict() for field in self.required_fields],
            "link_fields": list(self.link_fields),
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class SocTopArchiveRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class SocTopArchiveAudit:
    status: str
    message: str
    evidence_path: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == ARCHIVE_ARCHIVED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_soc_top_archive_profile() -> SocTopArchiveProfile:
    smoke_profile = fpga_soc_top_smoke.fpga_soc_top_smoke_profile()
    rtl_sources = tuple(path.as_posix() for path in fpga_soc_top_smoke.FPGA_SOC_TOP_SMOKE_SOURCES)
    return SocTopArchiveProfile(
        story=FPGA_SOC_TOP_ARCHIVE_STORY,
        evidence_path=FPGA_SOC_TOP_ARCHIVE_EVIDENCE,
        required_result=FPGA_SOC_TOP_ARCHIVE_RESULT,
        top_module=smoke_profile.top_module,
        top_smoke_gate=fpga_soc_top_smoke.FPGA_SOC_TOP_SMOKE_TOOL,
        replay_mapper_gate=fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        debug_evidence_gate=fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        verilator_command=smoke_profile.verilator_command,
        run_command=smoke_profile.run_command,
        rtl_sources=rtl_sources,
        required_fields=(
            SocTopArchiveField("story", True, "Must be I30-S06."),
            SocTopArchiveField("archived_at", True, "Local archive date/time."),
            SocTopArchiveField("repository_commit", True, "Repository commit used for the RTL smoke."),
            SocTopArchiveField("top_module", True, "Must be cpu_v01_fpga_top."),
            SocTopArchiveField("rtl_sources", True, "Comma-separated RTL source paths from the I30-S05 smoke."),
            SocTopArchiveField("verilator_command", True, "Exact I30-S05 Verilator build command."),
            SocTopArchiveField("verilator_build_log", True, "Captured Verilator build log path."),
            SocTopArchiveField("smoke_run_command", True, "Exact I30-S05 smoke executable command."),
            SocTopArchiveField("smoke_run_log", True, "Captured smoke executable log path."),
            SocTopArchiveField("decoded_uart_trace", True, "Decoded UART firmware output or transcript."),
            SocTopArchiveField("decoded_status_trace", True, "Decoded status/fault trace or packet capture."),
            SocTopArchiveField("probe_trace", False, "Optional GAO/ILA/LED probe capture path."),
            SocTopArchiveField("replay_mapping", True, "I25-S04 replay mapping record or command output."),
            SocTopArchiveField("debug_evidence", True, "I25-S05 debug-evidence triage record."),
            SocTopArchiveField("closure_result", True, "Must be soc_top_closure_pass for archive pass."),
            SocTopArchiveField("remaining_blockers", True, "none, or named blockers."),
            SocTopArchiveField("filed_issues", True, "none, or issue IDs for residual blockers."),
            SocTopArchiveField("retest_commands", True, "Commands to rerun validators, Verilator build, and smoke executable."),
        ),
        link_fields=(
            "verilator_build_log",
            "smoke_run_log",
            "decoded_uart_trace",
            "decoded_status_trace",
            "replay_mapping",
            "debug_evidence",
        ),
        retest_commands=(
            fpga_soc_top_smoke.FPGA_SOC_TOP_SMOKE_TOOL,
            smoke_profile.verilator_command,
            smoke_profile.run_command,
            fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
            fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        ),
        blockers=(
            "I30-S05 top-level smoke must have captured build and run logs",
            "decoded UART/status or probe traces must be linked before I31-S01 can consume the archive",
            "I25-S04 replay mapping must name the nearest replay command or pass/no-mismatch disposition",
            "I25-S05 debug evidence must classify any non-pass result and preserve first-failure diagnostics",
            "remaining blockers must be none, or filed with issue IDs and retest commands",
        ),
    )


def soc_top_archive_template(profile: SocTopArchiveProfile | None = None) -> str:
    if profile is None:
        profile = fpga_soc_top_archive_profile()
    rtl_sources = ",".join(profile.rtl_sources)
    retest_commands = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "archived_at=",
            "repository_commit=",
            f"top_module={profile.top_module}",
            f"rtl_sources={rtl_sources}",
            f"verilator_command={profile.verilator_command}",
            "verilator_build_log=docs/implementation/evidence/i30_s06_verilator_build.log",
            f"smoke_run_command={profile.run_command}",
            "smoke_run_log=docs/implementation/evidence/i30_s06_soc_top_smoke.log",
            "decoded_uart_trace=docs/implementation/evidence/i30_s06_uart_trace.txt",
            "decoded_status_trace=docs/implementation/evidence/i30_s06_status_trace.json",
            "probe_trace=none",
            "replay_mapping=docs/implementation/evidence/i30_s06_replay_mapping.txt",
            "debug_evidence=docs/implementation/evidence/i30_s06_debug_evidence.txt",
            f"closure_result={profile.required_result}",
            "remaining_blockers=none",
            "filed_issues=none",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_soc_top_archive(text: str) -> SocTopArchiveRecord:
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
    return SocTopArchiveRecord(fields)


def audit_soc_top_archive(
    record: SocTopArchiveRecord,
    *,
    evidence_path: str = "<inline>",
    profile: SocTopArchiveProfile | None = None,
) -> SocTopArchiveAudit:
    if profile is None:
        profile = fpga_soc_top_archive_profile()

    missing_fields = [
        field.name for field in profile.required_fields if field.required and not record.value(field.name)
    ]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I30-S06")
    if record.value("top_module") and record.value("top_module") != profile.top_module:
        missing_fields.append("top_module_must_be_cpu_v01_fpga_top")

    link_issues: list[str] = []
    for field in profile.link_fields:
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence")

    rtl_sources = record.value("rtl_sources")
    for source in ("rtl/cpu_v01_core.sv", "rtl/cpu_v01_fpga_top.sv", "rtl/cpu_v01_fpga_top_soc_smoke_tb.sv"):
        if rtl_sources and source not in rtl_sources:
            link_issues.append(f"rtl_sources must include {source}")

    if record.value("verilator_command") and record.value("verilator_command") != profile.verilator_command:
        link_issues.append("verilator_command must match the I30-S05 smoke build command")
    if record.value("smoke_run_command") and record.value("smoke_run_command") != profile.run_command:
        link_issues.append("smoke_run_command must match the I30-S05 smoke executable")
    if record.value("replay_mapping") and not _mentions_story_or_tool(
        record.value("replay_mapping"),
        "i25_s04",
        "fpga_replay_mapper",
        "replay",
    ):
        link_issues.append("replay_mapping must reference I25-S04 replay mapping evidence")
    if record.value("debug_evidence") and not _mentions_story_or_tool(
        record.value("debug_evidence"),
        "i25_s05",
        "fpga_debug_evidence",
        "debug_evidence",
    ):
        link_issues.append("debug_evidence must reference I25-S05 debug evidence")

    blocker_issues: list[str] = []
    if record.value("closure_result") != profile.required_result:
        blocker_issues.append("closure_result must be soc_top_closure_pass")

    retest_commands = record.value("retest_commands")
    for command in (profile.top_smoke_gate, profile.replay_mapper_gate, profile.debug_evidence_gate):
        if retest_commands and command not in retest_commands:
            blocker_issues.append(f"retest_commands must include {command}")
    if retest_commands and profile.run_command not in retest_commands:
        blocker_issues.append("retest_commands must include the smoke executable run command")

    remaining_blockers = record.value("remaining_blockers")
    filed_issues = record.value("filed_issues")
    if remaining_blockers and not _is_empty_disposition(remaining_blockers):
        if _is_empty_disposition(filed_issues):
            blocker_issues.append("remaining blockers must have filed_issues")
        if _is_empty_disposition(retest_commands):
            blocker_issues.append("remaining blockers must have retest_commands")

    if missing_fields:
        return SocTopArchiveAudit(
            status=ARCHIVE_INVALID,
            message="SoC top closure archive evidence is incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required archive fields", "rerun the I30-S06 audit"),
        )
    if link_issues:
        return SocTopArchiveAudit(
            status=ARCHIVE_INVALID,
            message="SoC top closure archive links are incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=tuple(link_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("replace placeholders with concrete evidence links", "rerun the I30-S06 audit"),
        )
    if blocker_issues:
        return SocTopArchiveAudit(
            status=ARCHIVE_NEEDS_FOLLOWUP,
            message="SoC top closure archive exists but blocker disposition is not complete.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=(),
            blocker_issues=tuple(blocker_issues),
            actions=("file or close remaining blockers", "record exact retest commands before handoff"),
        )
    return SocTopArchiveAudit(
        status=ARCHIVE_ARCHIVED,
        message="SoC top integration closure archive is complete.",
        evidence_path=evidence_path,
        missing_fields=(),
        link_issues=(),
        blocker_issues=(),
        actions=("archive can be handed to I31-S01 first-pass board build preparation",),
    )


def load_soc_top_archive_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> SocTopArchiveAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_archive_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return SocTopArchiveAudit(
            status=ARCHIVE_BLOCKED,
            message="No SoC top integration closure archive has been captured yet.",
            evidence_path=relative_path.as_posix(),
            missing_fields=tuple(field.name for field in profile.required_fields if field.required),
            link_issues=(),
            blocker_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the archive template",
                "link RTL sources, Verilator logs, decoded traces, replay mapping, and debug evidence",
                "close or file remaining blockers with retest commands",
            ),
        )
    try:
        record = parse_soc_top_archive(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return SocTopArchiveAudit(
            status=ARCHIVE_INVALID,
            message="SoC top closure archive could not be parsed.",
            evidence_path=relative_path.as_posix(),
            missing_fields=(str(exc),),
            link_issues=(),
            blocker_issues=(),
            actions=("fix the key=value archive record", "rerun the I30-S06 audit"),
        )
    return audit_soc_top_archive(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_soc_top_archive_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_soc_top_archive_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_soc_top_archive(
    profile: SocTopArchiveProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_soc_top_archive_profile()
    lines = [
        "# FPGA SoC Top Archive",
        "",
        f"Story: {profile.story}",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Required result: `{profile.required_result}`",
        f"Top module: `{profile.top_module}`",
        "",
        "## Gates",
        "",
        f"- `{profile.top_smoke_gate}`",
        f"- `{profile.replay_mapper_gate}`",
        f"- `{profile.debug_evidence_gate}`",
        "",
        "## Required Fields",
        "",
        "| Field | Required | Description |",
        "| --- | --- | --- |",
    ]
    for field in profile.required_fields:
        lines.append(
            f"| `{field.name}` | {'yes' if field.required else 'no'} | {field.description} |"
        )
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_soc_top_archive(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_soc_top_archive_profile()
    issues: list[str] = []

    if profile.story != FPGA_SOC_TOP_ARCHIVE_STORY:
        issues.append(f"SoC top archive story must be {FPGA_SOC_TOP_ARCHIVE_STORY}")
    if profile.required_result != FPGA_SOC_TOP_ARCHIVE_RESULT:
        issues.append("SoC top archive result must be soc_top_closure_pass")
    if profile.top_module != "cpu_v01_fpga_top":
        issues.append("SoC top archive must target cpu_v01_fpga_top")
    if profile.top_smoke_gate != fpga_soc_top_smoke.FPGA_SOC_TOP_SMOKE_TOOL:
        issues.append("SoC top archive must depend on the I30-S05 smoke gate")
    if profile.replay_mapper_gate != fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL:
        issues.append("SoC top archive must depend on the I25-S04 replay mapper")
    if profile.debug_evidence_gate != fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL:
        issues.append("SoC top archive must depend on the I25-S05 debug evidence gate")

    issues.extend(fpga_soc_top_smoke.validate_fpga_soc_top_smoke(root))
    issues.extend(fpga_replay_mapper.validate_fpga_replay_mapper(root))
    issues.extend(fpga_debug_evidence.validate_fpga_debug_evidence(root))

    fields = {field.name: field for field in profile.required_fields}
    for required in (
        "story",
        "archived_at",
        "repository_commit",
        "top_module",
        "rtl_sources",
        "verilator_command",
        "verilator_build_log",
        "smoke_run_command",
        "smoke_run_log",
        "decoded_uart_trace",
        "decoded_status_trace",
        "replay_mapping",
        "debug_evidence",
        "closure_result",
        "remaining_blockers",
        "filed_issues",
        "retest_commands",
    ):
        field = fields.get(required)
        if field is None:
            issues.append(f"missing SoC top archive field {required}")
        elif not field.required:
            issues.append(f"{required} must be required")
    for link in profile.link_fields:
        if link not in fields:
            issues.append(f"SoC top archive link field {link} must also be required")

    for source in (
        "rtl/cpu_v01_core.sv",
        "rtl/cpu_v01_fpga_top.sv",
        "rtl/cpu_v01_fpga_top_soc_smoke_tb.sv",
    ):
        if source not in profile.rtl_sources:
            issues.append(f"SoC top archive RTL sources missing {source}")
        if not (root / source).exists():
            issues.append(f"missing SoC top archive RTL source {source}")

    good_record = parse_soc_top_archive(
        soc_top_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_soc_top_archive(good_record).passed:
        issues.append("complete SoC top closure archive must audit as archived")

    followup_record = parse_soc_top_archive(
        soc_top_archive_template()
        .replace("archived_at=", "archived_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("remaining_blockers=none", "remaining_blockers=timer_irq_core_delivery")
    )
    followup_audit = audit_soc_top_archive(followup_record)
    if followup_audit.status != ARCHIVE_NEEDS_FOLLOWUP:
        issues.append("remaining SoC top blockers without filed issues must require follow-up")

    default_audit = load_soc_top_archive_audit(root)
    if default_audit.status != ARCHIVE_BLOCKED:
        issues.append("default SoC top closure archive audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_SOC_TOP_ARCHIVE_DOC)
    for token in (
        "Story: I30-S06",
        FPGA_SOC_TOP_ARCHIVE_TOOL,
        FPGA_SOC_TOP_ARCHIVE_EVIDENCE.as_posix(),
        fpga_soc_top_smoke.FPGA_SOC_TOP_SMOKE_TOOL,
        fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_TOOL,
        "rtl/cpu_v01_fpga_top.sv",
        "rtl/cpu_v01_fpga_top_soc_smoke_tb.sv",
        "Verilator logs",
        "decoded UART/status",
        "probe_trace",
        "replay_mapping",
        "debug_evidence",
        "soc_top_closure_pass",
        "remaining_blockers",
        "filed_issues",
        "retest_commands",
        "blocked",
        "I31-S01",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SOC_TOP_ARCHIVE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(load_soc_top_archive_audit(root).as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"SoC top archive objects are not JSON serializable: {exc}")

    return tuple(issues)


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _mentions_story_or_tool(value: str, *tokens: str) -> bool:
    lowered = value.lower()
    return any(token.lower() in lowered for token in tokens)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

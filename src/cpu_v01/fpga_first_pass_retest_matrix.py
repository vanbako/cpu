"""Board retest matrix for the first physical integrated CPU pass.

Owner stories:
- I31-S06: publish a board retest matrix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_pass_archive, fpga_first_test


JsonValue = Any

FPGA_FIRST_PASS_RETEST_STORY = "I31-S06"
FPGA_FIRST_PASS_RETEST_DOC = Path("docs/implementation/fpga-first-pass-retest-matrix.md")
FPGA_FIRST_PASS_RETEST_TOOL = "python tools\\fpga_first_pass_retest_matrix.py --check"
FIRST_PASS_RETEST_STATUS = "published_first_cpu_retest_matrix"


@dataclass(frozen=True)
class RetestMatrixRow:
    phase: str
    command: str
    required_captures: tuple[str, ...]
    board_assumptions: tuple[str, ...]
    rerun_when: tuple[str, ...]
    accept_when: tuple[str, ...]
    evidence_handoff: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "phase": self.phase,
            "command": self.command,
            "required_captures": list(self.required_captures),
            "board_assumptions": list(self.board_assumptions),
            "rerun_when": list(self.rerun_when),
            "accept_when": list(self.accept_when),
            "evidence_handoff": self.evidence_handoff,
        }


@dataclass(frozen=True)
class FirstPassRetestMatrixProfile:
    story: str
    status: str
    board: str
    archive_gate: str
    matrix_rows: tuple[RetestMatrixRow, ...]
    known_board_assumptions: tuple[str, ...]
    first_pass_acceptance: tuple[str, ...]
    blocker_acceptance: tuple[str, ...]

    def row_by_phase(self, phase: str) -> RetestMatrixRow:
        for row in self.matrix_rows:
            if row.phase == phase:
                return row
        raise KeyError(phase)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "board": self.board,
            "archive_gate": self.archive_gate,
            "matrix_rows": [row.as_dict() for row in self.matrix_rows],
            "known_board_assumptions": list(self.known_board_assumptions),
            "first_pass_acceptance": list(self.first_pass_acceptance),
            "blocker_acceptance": list(self.blocker_acceptance),
        }


def fpga_first_pass_retest_matrix_profile() -> FirstPassRetestMatrixProfile:
    archive = fpga_first_pass_archive.fpga_first_pass_archive_profile()
    return FirstPassRetestMatrixProfile(
        story=FPGA_FIRST_PASS_RETEST_STORY,
        status=FIRST_PASS_RETEST_STATUS,
        board=fpga_first_test.TARGET_BOARD_NAME,
        archive_gate=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        matrix_rows=(
            RetestMatrixRow(
                phase="identity_constraints",
                command="python tools\\fpga_first_board_archive.py --check",
                required_captures=(
                    "I24-S01 device/package scan or marking evidence",
                    "I24-S02 CST pin overlay evidence",
                    "I24-S03 Gowin report bundle and bitstream path",
                ),
                board_assumptions=(
                    "target board is Sipeed Tang Mega 138K Dock",
                    "device/package and overlay still match the physical board",
                ),
                rerun_when=(
                    "the physical board, package, constraints, PLL profile, or Gowin report bundle changes",
                    "any pin, clock, reset, LED, UART, or probe overlay is edited",
                ),
                accept_when=(
                    "I24-S05 archive links scan, constraints, reports, bitstream, programming, reset, and LED evidence",
                    "linked evidence is concrete and not a placeholder",
                ),
                evidence_handoff=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_EVIDENCE.as_posix(),
            ),
            RetestMatrixRow(
                phase="sram_programming_observation",
                command="python tools\\fpga_first_pass_programming.py --check",
                required_captures=(
                    "bitstream_sha256 and exact .fs path",
                    "programming_log in SRAM mode",
                    "reset_observation after reset release",
                    "heartbeat, pass LED, fail LED, UART log, decoded status packet, and optional probe capture",
                ),
                board_assumptions=(
                    "SRAM programming is used; flash programming does not satisfy first-pass evidence",
                    "selected image and bitstream match the I31-S02 Gowin build",
                ),
                rerun_when=(
                    "bitstream, image, constraints, reset sequencing, UART status transport, or probe capture changes",
                    "programming log, reset release, heartbeat, LED, or UART packet evidence is missing",
                ),
                accept_when=(
                    "I31-S03 audit status is observed",
                    "first_pass requires pass LED yes, fail LED no, pass_fail_state first_pass, retire_count at least 8, and fault_code 0",
                    "failure_observed is accepted only as a handoff to I31-S04 replay classification",
                ),
                evidence_handoff=archive.evidence_path.as_posix(),
            ),
            RetestMatrixRow(
                phase="failure_replay_classification",
                command="python tools\\fpga_first_pass_replay.py --check",
                required_captures=(
                    "captured 32-byte status packet",
                    "I25-S04 replay mapping and selected replay command",
                    "observed_trace path or explicit none",
                    "first_mismatch or assertion diagnostic",
                    "I25-S05 debug evidence status and filed follow-up issue",
                ),
                board_assumptions=(
                    "I31-S03 reported failure_observed",
                    "UART or GAO/ILA capture is available for nontrivial failures",
                ),
                rerun_when=(
                    "pass/fail state is failed, fault code is nonzero, fail LED is observed, or heartbeat/reset behavior is suspect",
                    "first_mismatch, replay command, failure class, or filed issue is absent",
                ),
                accept_when=(
                    "I31-S04 audit status is classified",
                    "failure class is clock_reset, memory, firmware, trap, translation, loader, or board_integration",
                    "replay_case_id and first_mismatch are preserved for blocker disposition",
                ),
                evidence_handoff=archive.evidence_path.as_posix(),
            ),
            RetestMatrixRow(
                phase="final_archive",
                command=fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
                required_captures=(
                    "I31-S05 archive record",
                    "pass_fail_result and archive_result",
                    "residual_blockers, filed_issues, and retest_steps",
                ),
                board_assumptions=(
                    "I24-S05 and I31-S03 evidence are available",
                    "I31-S04 evidence is available for blocker_disposition_archived",
                ),
                rerun_when=(
                    "any upstream evidence link changes",
                    "archive_result changes between first_pass_archived and blocker_disposition_archived",
                    "residual blockers or filed issues change",
                ),
                accept_when=(
                    "I31-S05 audit status is archived",
                    "first_pass_archived has no residual blockers",
                    "blocker_disposition_archived has concrete residual_blockers, filed_issues, first_mismatch, and retest_steps",
                ),
                evidence_handoff=archive.evidence_path.as_posix(),
            ),
            RetestMatrixRow(
                phase="local_regression_gate",
                command="python tools\\local_checks.py",
                required_captures=(
                    "local_checks output or transcript",
                    "conformance and litmus pass counts",
                    "any non-fatal CRLF warnings recorded with the archive",
                ),
                board_assumptions=(
                    "the local repository commit matches repository_commit in the archive",
                    "Verilator and Python tools are available on the same PATH profile used for prior gates",
                ),
                rerun_when=(
                    "before handing I31-S05 to release-candidate evidence",
                    "after any source, tool, RTL, test, or documentation change",
                ),
                accept_when=(
                    "local_checks exits 0",
                    "spec reference, story coverage, conformance, litmus, and whitespace gates pass",
                ),
                evidence_handoff=archive.evidence_path.as_posix(),
            ),
        ),
        known_board_assumptions=(
            "target board is Sipeed Tang Mega 138K Dock",
            "SRAM mode is the required programming mode for first-pass evidence",
            "bitstream identity comes from I31-S02 and is repeated in I31-S03/I31-S05",
            "UART status packets use the I25-S01 32-byte packet layout",
            "a first CPU pass is not accepted without I31-S05 archive_result=first_pass_archived",
            "a board failure is not accepted as triaged without I31-S04 replay_status=classified",
        ),
        first_pass_acceptance=(
            "I31-S03 observed with board_result=first_pass",
            "pass LED yes, fail LED no, first_pass status packet, retire_count at least 8, fault_code 0",
            "I31-S05 archived with archive_result=first_pass_archived and residual_blockers=none",
            "local_checks exits 0 for the same repository commit",
        ),
        blocker_acceptance=(
            "I31-S03 observed with board_result=failure_observed",
            "I31-S04 classified the failure and preserved replay_case_id plus first_mismatch",
            "I31-S05 archived with archive_result=blocker_disposition_archived",
            "residual_blockers, filed_issues, and retest_steps are concrete",
        ),
    )


def fpga_first_pass_retest_matrix_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_retest_matrix_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_retest_matrix(
    profile: FirstPassRetestMatrixProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_retest_matrix_profile()
    lines = [
        "# FPGA First-Pass Retest Matrix",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Board: `{profile.board}`",
        f"Archive gate: `{profile.archive_gate}`",
        "",
        "| Phase | Command | Required captures | Rerun when | Accept when |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in profile.matrix_rows:
        lines.append(
            f"| `{row.phase}` | `{row.command}` | "
            f"{'; '.join(row.required_captures)} | "
            f"{'; '.join(row.rerun_when)} | "
            f"{'; '.join(row.accept_when)} |"
        )
    lines.extend(["", "## Known Board Assumptions", ""])
    lines.extend(f"- {assumption}." for assumption in profile.known_board_assumptions)
    lines.extend(["", "## First-Pass Acceptance", ""])
    lines.extend(f"- {criterion}." for criterion in profile.first_pass_acceptance)
    lines.extend(["", "## Blocker Acceptance", ""])
    lines.extend(f"- {criterion}." for criterion in profile.blocker_acceptance)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_pass_retest_matrix(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_retest_matrix_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_RETEST_STORY:
        issues.append(f"first-pass retest matrix story must be {FPGA_FIRST_PASS_RETEST_STORY}")
    if profile.status != FIRST_PASS_RETEST_STATUS:
        issues.append("first-pass retest matrix status must be published")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("first-pass retest matrix board must match first-test target")
    if profile.archive_gate != fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL:
        issues.append("first-pass retest matrix must depend on I31-S05 archive")

    issues.extend(fpga_first_pass_archive.validate_fpga_first_pass_archive(root))

    required_phases = (
        "identity_constraints",
        "sram_programming_observation",
        "failure_replay_classification",
        "final_archive",
        "local_regression_gate",
    )
    rows = {row.phase: row for row in profile.matrix_rows}
    for phase in required_phases:
        if phase not in rows:
            issues.append(f"missing retest matrix phase {phase}")

    required_commands = (
        "python tools\\fpga_first_board_archive.py --check",
        "python tools\\fpga_first_pass_programming.py --check",
        "python tools\\fpga_first_pass_replay.py --check",
        "python tools\\fpga_first_pass_archive.py --check",
        "python tools\\local_checks.py",
    )
    commands = tuple(row.command for row in profile.matrix_rows)
    for command in required_commands:
        if command not in commands:
            issues.append(f"missing retest matrix command {command}")

    for row in profile.matrix_rows:
        if not row.required_captures:
            issues.append(f"{row.phase} must name required captures")
        if not row.board_assumptions:
            issues.append(f"{row.phase} must name known board assumptions")
        if not row.rerun_when:
            issues.append(f"{row.phase} must name rerun criteria")
        if not row.accept_when:
            issues.append(f"{row.phase} must name acceptance criteria")
        if not row.evidence_handoff:
            issues.append(f"{row.phase} must name evidence handoff")

    for token in (
        "Sipeed Tang Mega 138K Dock",
        "SRAM mode",
        "I25-S01 32-byte packet",
        "first_pass_archived",
        "blocker_disposition_archived",
        "residual_blockers",
        "filed_issues",
        "retest_steps",
    ):
        if token not in " ".join(profile.known_board_assumptions + profile.first_pass_acceptance + profile.blocker_acceptance):
            issues.append(f"first-pass retest matrix assumptions or criteria missing {token}")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_RETEST_DOC)
    for token in (
        "Story: I31-S06",
        FPGA_FIRST_PASS_RETEST_TOOL,
        fpga_first_pass_archive.FPGA_FIRST_PASS_ARCHIVE_TOOL,
        "python tools\\fpga_first_board_archive.py --check",
        "python tools\\fpga_first_pass_programming.py --check",
        "python tools\\fpga_first_pass_replay.py --check",
        "python tools\\local_checks.py",
        "identity_constraints",
        "sram_programming_observation",
        "failure_replay_classification",
        "final_archive",
        "local_regression_gate",
        "required captures",
        "known board assumptions",
        "rerun criteria",
        "acceptance criteria",
        "first_pass_archived",
        "blocker_disposition_archived",
        "I31-S05",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_RETEST_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass retest matrix objects are not JSON serializable: {exc}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

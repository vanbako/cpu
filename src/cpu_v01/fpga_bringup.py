"""FPGA board bring-up runbook for CPU v0.1.

Owner stories:
- I23-S06: first board programming, reset, observation, triage, and evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_synthesis


JsonValue = Any

FPGA_BRINGUP_STORY = "I23-S06"
FPGA_BRINGUP_DOC = Path("docs/implementation/fpga-board-bringup.md")
FPGA_BRINGUP_TOOL = "python tools\\fpga_bringup_runbook.py --check"
FPGA_BRINGUP_PROGRAMMING_MODE = "Gowin Programmer SRAM first, flash only after repeatable SRAM pass"


@dataclass(frozen=True)
class BringupPrerequisite:
    name: str
    required: bool
    evidence: str
    blocker_if_missing: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "evidence": self.evidence,
            "blocker_if_missing": self.blocker_if_missing,
        }


@dataclass(frozen=True)
class BringupProcedureStep:
    order: int
    name: str
    action: str
    expected_observation: str
    failure_triage: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "order": self.order,
            "name": self.name,
            "action": self.action,
            "expected_observation": self.expected_observation,
            "failure_triage": self.failure_triage,
        }


@dataclass(frozen=True)
class BringupObservation:
    name: str
    required: bool
    source_signal: str
    expected_result: str
    evidence_capture: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "source_signal": self.source_signal,
            "expected_result": self.expected_result,
            "evidence_capture": self.evidence_capture,
        }


@dataclass(frozen=True)
class BringupEvidence:
    name: str
    required: bool
    path_or_record: str
    acceptance_rule: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "required": self.required,
            "path_or_record": self.path_or_record,
            "acceptance_rule": self.acceptance_rule,
        }


@dataclass(frozen=True)
class BringupTriageCase:
    symptom: str
    likely_causes: tuple[str, ...]
    actions: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "symptom": self.symptom,
            "likely_causes": list(self.likely_causes),
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class FpgaBoardBringupRunbook:
    story: str
    board: str
    device: str
    ide_package: str
    top_module: str
    synthesis_gate: str
    programming_mode: str
    prerequisites: tuple[BringupPrerequisite, ...]
    procedure: tuple[BringupProcedureStep, ...]
    observations: tuple[BringupObservation, ...]
    evidence: tuple[BringupEvidence, ...]
    triage: tuple[BringupTriageCase, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "device": self.device,
            "ide_package": self.ide_package,
            "top_module": self.top_module,
            "synthesis_gate": self.synthesis_gate,
            "programming_mode": self.programming_mode,
            "prerequisites": [
                prerequisite.as_dict() for prerequisite in self.prerequisites
            ],
            "procedure": [step.as_dict() for step in self.procedure],
            "observations": [
                observation.as_dict() for observation in self.observations
            ],
            "evidence": [item.as_dict() for item in self.evidence],
            "triage": [case.as_dict() for case in self.triage],
            "blockers": list(self.blockers),
        }


def fpga_board_bringup_runbook() -> FpgaBoardBringupRunbook:
    return FpgaBoardBringupRunbook(
        story=FPGA_BRINGUP_STORY,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        ide_package=fpga_first_test.TARGET_IDE_PACKAGE,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        synthesis_gate=fpga_synthesis.FPGA_SYNTHESIS_TOOL,
        programming_mode=FPGA_BRINGUP_PROGRAMMING_MODE,
        prerequisites=(
            BringupPrerequisite(
                name="device_package_confirmed",
                required=True,
                evidence="Board marking or programmer/JTAG scan confirms GW5AST-LV138PG484A/PBG484A or updates the target overlay.",
                blocker_if_missing="Do not lock the CST or program the board until the PG484 versus FPG676 ambiguity is resolved.",
            ),
            BringupPrerequisite(
                name="i23_s05_gate_passed",
                required=True,
                evidence="python tools\\fpga_synthesis_gate.py --check and the Gowin timing, utilization, ports, and bitstream reports pass.",
                blocker_if_missing="Record a documented blocker instead of claiming first-board execution.",
            ),
            BringupPrerequisite(
                name="constraints_verified",
                required=True,
                evidence="constraints/tang_mega_138k_first_test.cst maps board_clk_i, board_reset_n_i, pass_led_o, fail_led_o, and heartbeat_led_o with correct IO standard and polarity.",
                blocker_if_missing="Return to I23-S05 and extract the verified Sipeed pin overlay.",
            ),
            BringupPrerequisite(
                name="board_power_and_usb_ready",
                required=True,
                evidence="Sipeed Tang Mega 138K Dock is powered and the onboard USB JTAG/UART enumerates.",
                blocker_if_missing="Triage cable, driver, boot mode, and board power before programming.",
            ),
            BringupPrerequisite(
                name="programmer_selected",
                required=True,
                evidence="Gowin Programmer or openFPGALoader command is selected for the verified device; SRAM programming is selected first.",
                blocker_if_missing="Do not use flash programming until volatile programming has a repeatable pass.",
            ),
        ),
        procedure=(
            BringupProcedureStep(
                order=1,
                name="record_board_identity",
                action="Inspect the Tang Mega 138K SOM marking and/or run a programmer/JTAG scan; record the observed device, package, and device version.",
                expected_observation="The record matches GW5AST-LV138PG484A, PBG484A, and the selected B/C device version, or explicitly updates the target profile.",
                failure_triage="If the board reports FPG676 or a different package, stop and update the synthesis overlay before building.",
            ),
            BringupProcedureStep(
                order=2,
                name="verify_synthesis_gate",
                action="Run python tools\\fpga_synthesis_gate.py --check, generate the Gowin Tcl, run gw_sh, and audit reports with --check-reports.",
                expected_observation="Timing slack, utilization, port assignment, and .fs bitstream evidence exist under build/fpga/tang_mega_138k/first_test.",
                failure_triage="Fix missing constraints, black boxes, negative slack, or missing pass/fail/heartbeat pins before touching the board.",
            ),
            BringupProcedureStep(
                order=3,
                name="prepare_board",
                action="Connect board power and onboard USB JTAG/UART, confirm 3.3 V IO safety for the selected LED pins, and keep reset asserted.",
                expected_observation="The programmer sees the board and no unsupported IO voltage or cabling issue is present.",
                failure_triage="Recheck cable, driver, jumper/boot mode, and board power before continuing.",
            ),
            BringupProcedureStep(
                order=4,
                name="program_sram",
                action="Program the first-test .fs bitstream through Gowin Programmer SRAM mode, or openFPGALoader only after device/package confirmation.",
                expected_observation="Programming exits successfully and the board remains responsive.",
                failure_triage="If programming fails, compare the selected device/package and cable scan against the synthesis report.",
            ),
            BringupProcedureStep(
                order=5,
                name="release_reset",
                action="Release board_reset_n_i and observe the pass, fail, heartbeat, retire-count, and fault-code surfaces for at least 10 seconds.",
                expected_observation="heartbeat_led_o toggles, pass_led_o asserts after the deterministic retire sequence, fail_led_o remains deasserted, status_retire_count_o advances, and status_fault_code_o is zero.",
                failure_triage="If heartbeat is dead, debug clock/reset; if fail asserts or pass never asserts, capture fault and retire probes.",
            ),
            BringupProcedureStep(
                order=6,
                name="capture_evidence",
                action="Save the programming log, report bundle, device scan, reset observation, and LED photo or video; otherwise record the exact documented blocker.",
                expected_observation="The first-pass evidence is enough for another engineer to replay the build and board observation.",
                failure_triage="If evidence is incomplete, mark the run inconclusive rather than passing the story.",
            ),
        ),
        observations=(
            BringupObservation(
                name="heartbeat_led_o",
                required=True,
                source_signal="debug_retire_sequence",
                expected_result="Toggles after reset release to prove board_clk_i and synchronized reset are alive.",
                evidence_capture="Short video or logic capture showing heartbeat activity.",
            ),
            BringupObservation(
                name="pass_led_o",
                required=True,
                source_signal="first_test_status.pass",
                expected_result="Asserts after the smoke firmware reaches its deterministic pass condition.",
                evidence_capture="Photo or video that also identifies the programmed board.",
            ),
            BringupObservation(
                name="fail_led_o",
                required=True,
                source_signal="first_test_status.fail",
                expected_result="Remains deasserted during and after the pass observation.",
                evidence_capture="Photo, video, or probe capture showing fail low when pass is high.",
            ),
            BringupObservation(
                name="status_retire_count_o",
                required=False,
                source_signal="debug_retire_sequence",
                expected_result="Advances to at least 8 retired instructions during the smoke run.",
                evidence_capture="GAO, UART, or logic-analyzer capture when available.",
            ),
            BringupObservation(
                name="status_fault_code_o",
                required=False,
                source_signal="retire_packet.fault.cause",
                expected_result="Stays zero for the passing first-test program.",
                evidence_capture="GAO, UART, or logic-analyzer capture when available.",
            ),
        ),
        evidence=(
            BringupEvidence(
                name="device_scan_record",
                required=True,
                path_or_record="docs/implementation/evidence/i23_s06_device_scan.txt",
                acceptance_rule="Names the observed FPGA device, package, and device version used by the build.",
            ),
            BringupEvidence(
                name="i23_s05_report_bundle",
                required=True,
                path_or_record="build/fpga/tang_mega_138k/first_test/impl",
                acceptance_rule="Includes synthesis, timing, port, utilization, and bitstream artifacts accepted by --check-reports.",
            ),
            BringupEvidence(
                name="bitstream_path",
                required=True,
                path_or_record="build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs",
                acceptance_rule="Matches the build audited immediately before programming.",
            ),
            BringupEvidence(
                name="programming_log",
                required=True,
                path_or_record="docs/implementation/evidence/i23_s06_programming_log.txt",
                acceptance_rule="Shows the programmer command/tool, selected SRAM mode, target device, and successful exit.",
            ),
            BringupEvidence(
                name="reset_observation",
                required=True,
                path_or_record="docs/implementation/evidence/i23_s06_reset_observation.txt",
                acceptance_rule="Records reset assertion/release timing and the first 10 seconds of observation.",
            ),
            BringupEvidence(
                name="led_photo_or_video",
                required=True,
                path_or_record="docs/implementation/evidence/i23_s06_led_evidence.*",
                acceptance_rule="Shows heartbeat_led_o activity, pass_led_o asserted, and fail_led_o deasserted on the programmed board.",
            ),
            BringupEvidence(
                name="documented_blocker",
                required=True,
                path_or_record="docs/implementation/fpga-board-bringup.md#current-blocker",
                acceptance_rule="Acceptable instead of physical pass evidence only when board execution cannot yet be performed.",
            ),
        ),
        triage=(
            BringupTriageCase(
                symptom="no_jtag_device",
                likely_causes=("USB cable/driver issue", "board power missing", "wrong programmer mode"),
                actions=("verify board power", "try Gowin Programmer scan", "record scan failure as blocker"),
            ),
            BringupTriageCase(
                symptom="programmer_rejects_device_or_package",
                likely_causes=("PG484/FPG676 target mismatch", "wrong Device Version B/C", "stale CST/project"),
                actions=("record actual scan", "update target profile", "rerun I23-S05 before programming"),
            ),
            BringupTriageCase(
                symptom="no_heartbeat",
                likely_causes=("board_clk_i not pinned", "board_reset_n_i held active", "PLL or clock constraint issue"),
                actions=("probe clock/reset", "check port report", "rerun with reset held/released observations"),
            ),
            BringupTriageCase(
                symptom="fail_led_asserted",
                likely_causes=("firmware trapped", "memory image mismatch", "tag RAM initialization mismatch"),
                actions=("capture status_fault_code_o", "capture status_retire_count_o", "replay Verilator smoke"),
            ),
            BringupTriageCase(
                symptom="pass_never_asserts",
                likely_causes=("ROM did not execute", "retire path stalled", "LED polarity inverted"),
                actions=("check heartbeat", "capture retire count", "verify LED polarity and ROM image"),
            ),
            BringupTriageCase(
                symptom="timing_or_report_missing",
                likely_causes=("Gowin flow incomplete", "report paths changed", "negative timing slack"),
                actions=("rerun report audit", "fix I23-S05 gate", "do not count board evidence"),
            ),
        ),
        blockers=(
            "physical Tang Mega 138K device/package scan has not been captured in this repository",
            "verified Tang Mega 138K CST pin overlay for board_clk_i, board_reset_n_i, pass_led_o, fail_led_o, and heartbeat_led_o is still pending",
            "Gowin timing, utilization, ports, and bitstream reports are not yet present under build/fpga/tang_mega_138k/first_test",
            "no programming log, reset observation, or LED photo/video evidence has been captured yet",
        ),
    )


def fpga_board_bringup_runbook_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_board_bringup_runbook().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def fpga_bringup_command_plan(
    runbook: FpgaBoardBringupRunbook | None = None,
) -> tuple[str, ...]:
    if runbook is None:
        runbook = fpga_board_bringup_runbook()
    return (
        runbook.synthesis_gate,
        "python tools\\fpga_synthesis_gate.py --plan",
        "python tools\\fpga_synthesis_gate.py --gowin-tcl",
        "gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
        "python tools\\fpga_synthesis_gate.py --check-reports build\\fpga\\tang_mega_138k\\first_test",
        "program build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs with Gowin Programmer SRAM mode",
        "release board_reset_n_i and observe pass_led_o, fail_led_o, heartbeat_led_o, status_retire_count_o, and status_fault_code_o",
    )


def render_fpga_bringup_runbook(
    runbook: FpgaBoardBringupRunbook | None = None,
) -> str:
    if runbook is None:
        runbook = fpga_board_bringup_runbook()
    lines = [
        "# FPGA Board Bring-Up Runbook",
        "",
        f"Story: {runbook.story}",
        "",
        f"Board: `{runbook.board}`",
        f"Device: `{runbook.device}`",
        f"IDE package: `{runbook.ide_package}`",
        f"Top module: `{runbook.top_module}`",
        f"Synthesis gate: `{runbook.synthesis_gate}`",
        f"Programming mode: {runbook.programming_mode}.",
        "",
        "## Prerequisites",
        "",
        "| Name | Required | Evidence | Blocker if missing |",
        "| --- | --- | --- | --- |",
    ]
    for prerequisite in runbook.prerequisites:
        lines.append(
            f"| `{prerequisite.name}` | "
            f"{'yes' if prerequisite.required else 'no'} | "
            f"{prerequisite.evidence} | {prerequisite.blocker_if_missing} |"
        )
    lines.extend(
        [
            "",
            "## Procedure",
            "",
            "| Order | Step | Action | Expected observation | Failure triage |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for step in runbook.procedure:
        lines.append(
            f"| {step.order} | `{step.name}` | {step.action} | "
            f"{step.expected_observation} | {step.failure_triage} |"
        )
    lines.extend(
        [
            "",
            "## Expected Observations",
            "",
            "| Observation | Required | Source | Expected result | Evidence capture |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for observation in runbook.observations:
        lines.append(
            f"| `{observation.name}` | "
            f"{'yes' if observation.required else 'no'} | "
            f"`{observation.source_signal}` | {observation.expected_result} | "
            f"{observation.evidence_capture} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Evidence | Required | Path or record | Acceptance rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in runbook.evidence:
        lines.append(
            f"| `{item.name}` | {'yes' if item.required else 'no'} | "
            f"`{item.path_or_record}` | {item.acceptance_rule} |"
        )
    lines.extend(
        [
            "",
            "## Triage",
            "",
            "| Symptom | Likely causes | Actions |",
            "| --- | --- | --- |",
        ]
    )
    for case in runbook.triage:
        causes = ", ".join(case.likely_causes)
        actions = ", ".join(case.actions)
        lines.append(f"| `{case.symptom}` | {causes} | {actions} |")
    lines.extend(["", "## Current Blocker", ""])
    lines.extend(f"- {blocker}." for blocker in runbook.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_board_bringup(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    runbook = fpga_board_bringup_runbook()
    issues: list[str] = []

    if runbook.story != FPGA_BRINGUP_STORY:
        issues.append(f"bring-up runbook story must be {FPGA_BRINGUP_STORY}")
    if runbook.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("bring-up board must match the first-test profile")
    if runbook.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("bring-up device must match the first-test profile")
    if runbook.ide_package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("bring-up package must match the first-test profile")
    if runbook.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("bring-up top module must match the first-test profile")
    if runbook.synthesis_gate != fpga_synthesis.FPGA_SYNTHESIS_TOOL:
        issues.append("bring-up runbook must depend on the I23-S05 synthesis gate")

    synthesis_issues = fpga_synthesis.validate_fpga_synthesis_gate(root)
    issues.extend(f"I23-S05 prerequisite: {issue}" for issue in synthesis_issues)

    prerequisites = {item.name: item for item in runbook.prerequisites}
    for required in (
        "device_package_confirmed",
        "i23_s05_gate_passed",
        "constraints_verified",
        "board_power_and_usb_ready",
        "programmer_selected",
    ):
        prerequisite = prerequisites.get(required)
        if prerequisite is None:
            issues.append(f"missing bring-up prerequisite {required}")
        elif not prerequisite.required:
            issues.append(f"{required} must be required")

    step_names = {step.name for step in runbook.procedure}
    for required in (
        "record_board_identity",
        "verify_synthesis_gate",
        "prepare_board",
        "program_sram",
        "release_reset",
        "capture_evidence",
    ):
        if required not in step_names:
            issues.append(f"missing bring-up procedure step {required}")

    observations = {observation.name: observation for observation in runbook.observations}
    for required in ("heartbeat_led_o", "pass_led_o", "fail_led_o"):
        observation = observations.get(required)
        if observation is None:
            issues.append(f"missing required board observation {required}")
        elif not observation.required:
            issues.append(f"{required} must be a required board observation")
    for optional in ("status_retire_count_o", "status_fault_code_o"):
        if optional not in observations:
            issues.append(f"missing optional triage observation {optional}")

    evidence = {item.name: item for item in runbook.evidence}
    for required in (
        "device_scan_record",
        "i23_s05_report_bundle",
        "bitstream_path",
        "programming_log",
        "reset_observation",
        "led_photo_or_video",
        "documented_blocker",
    ):
        if required not in evidence:
            issues.append(f"missing bring-up evidence item {required}")

    triage = {case.symptom for case in runbook.triage}
    for required in (
        "no_jtag_device",
        "programmer_rejects_device_or_package",
        "no_heartbeat",
        "fail_led_asserted",
        "pass_never_asserts",
        "timing_or_report_missing",
    ):
        if required not in triage:
            issues.append(f"missing bring-up triage case {required}")

    if len(fpga_bringup_command_plan(runbook)) < 6:
        issues.append("bring-up command plan must include synthesis, programming, and observation")
    if not runbook.blockers:
        issues.append("bring-up runbook must record current blockers")

    doc = _read_if_exists(root / FPGA_BRINGUP_DOC)
    for token in (
        "Story: I23-S06",
        FPGA_BRINGUP_TOOL,
        fpga_first_test.TARGET_BOARD_NAME,
        fpga_first_test.TARGET_FPGA_DEVICE,
        fpga_first_test.TARGET_IDE_PACKAGE,
        "python tools\\fpga_synthesis_gate.py --check",
        "Gowin Programmer SRAM",
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "status_retire_count_o",
        "status_fault_code_o",
        "programming_log",
        "led_photo_or_video",
        "documented blocker",
        "PG484",
        "FPG676",
    ):
        if token not in doc:
            issues.append(f"{FPGA_BRINGUP_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

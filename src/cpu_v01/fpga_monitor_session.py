"""Interactive FPGA monitor multi-program session fixtures.

Owner stories:
- I32-S03: load and execute multiple board-safe programs in one session.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_bram_images,
    fpga_debug_status,
    fpga_monitor_firmware,
    fpga_monitor_profile,
    fpga_program_loader,
    fpga_smoke_corpus,
    platform,
)


JsonValue = Any

FPGA_MONITOR_SESSION_STORY = "I32-S03"
FPGA_MONITOR_SESSION_DOC = Path("docs/implementation/fpga-monitor-multi-program-session.md")
FPGA_MONITOR_SESSION_TOOL = "python tools\\fpga_monitor_session.py --check"
FPGA_MONITOR_SESSION_STATUS = "multi_program_session_fixture"

DEFAULT_SESSION_CASE_IDS = (
    "scalar_control.call_return",
    "trap_syscall.sys_pause_iret",
)


@dataclass(frozen=True)
class MonitorSessionCaseSelection:
    case_id: str
    category: str
    program_id: str
    source_case_id: str
    expected_result: str
    manifest_image_sha256: str
    ram_image_sha256: str
    replay_case_id: str
    expected_led_signature: str
    expected_uart_signature: str
    expected_probe_signature: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "expected_result": self.expected_result,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "replay_case_id": self.replay_case_id,
            "expected_led_signature": self.expected_led_signature,
            "expected_uart_signature": self.expected_uart_signature,
            "expected_probe_signature": self.expected_probe_signature,
        }


@dataclass(frozen=True)
class MonitorSessionProfile:
    story: str
    status: str
    monitor_firmware_gate: str
    bram_image_gate: str
    smoke_corpus_gate: str
    selected_cases: tuple[MonitorSessionCaseSelection, ...]
    session_rules: tuple[str, ...]
    handoffs: tuple[str, ...]

    def selection_by_case_id(self, case_id: str) -> MonitorSessionCaseSelection:
        for selection in self.selected_cases:
            if selection.case_id == case_id:
                return selection
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "monitor_firmware_gate": self.monitor_firmware_gate,
            "bram_image_gate": self.bram_image_gate,
            "smoke_corpus_gate": self.smoke_corpus_gate,
            "selected_cases": [case.as_dict() for case in self.selected_cases],
            "session_rules": list(self.session_rules),
            "handoffs": list(self.handoffs),
        }


@dataclass(frozen=True)
class MonitorProgramObservation:
    run_index: int
    case_id: str
    category: str
    program_id: str
    manifest_image_sha256: str
    ram_image_sha256: str
    loaded_cells: int
    loader_status_name: str
    monitor_status_sequence: tuple[str, ...]
    started: bool
    start_pc_cell: int
    status_packet_sequence: int
    status_packet_state: str
    status_packet_fault_code: int
    expected_result: str
    expected_led_signature: str
    expected_uart_signature: str
    expected_probe_signature: str
    debug_signature_kind: str
    signature_digest: str
    replay_case_id: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "run_index": self.run_index,
            "case_id": self.case_id,
            "category": self.category,
            "program_id": self.program_id,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "loaded_cells": self.loaded_cells,
            "loader_status_name": self.loader_status_name,
            "monitor_status_sequence": list(self.monitor_status_sequence),
            "started": self.started,
            "start_pc_cell": self.start_pc_cell,
            "status_packet_sequence": self.status_packet_sequence,
            "status_packet_state": self.status_packet_state,
            "status_packet_fault_code": self.status_packet_fault_code,
            "expected_result": self.expected_result,
            "expected_led_signature": self.expected_led_signature,
            "expected_uart_signature": self.expected_uart_signature,
            "expected_probe_signature": self.expected_probe_signature,
            "debug_signature_kind": self.debug_signature_kind,
            "signature_digest": self.signature_digest,
            "replay_case_id": self.replay_case_id,
        }


@dataclass(frozen=True)
class MonitorProgramRun:
    run_index: int
    case_id: str
    command_results: tuple[fpga_monitor_firmware.MonitorFirmwareCommandResult, ...]
    observation: MonitorProgramObservation
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "run_index": self.run_index,
            "case_id": self.case_id,
            "passed": self.passed,
            "command_results": [result.as_dict() for result in self.command_results],
            "observation": self.observation.as_dict(),
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class MonitorSessionRun:
    story: str
    status: str
    initial_hello: fpga_monitor_firmware.MonitorFirmwareCommandResult
    program_runs: tuple[MonitorProgramRun, ...]
    final_snapshot: fpga_monitor_firmware.MonitorFirmwareSnapshot
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    @property
    def loaded_program_ids(self) -> tuple[str, ...]:
        return tuple(run.observation.program_id for run in self.program_runs)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "passed": self.passed,
            "initial_hello": self.initial_hello.as_dict(),
            "program_runs": [run.as_dict() for run in self.program_runs],
            "final_snapshot": self.final_snapshot.as_dict(),
            "issues": list(self.issues),
        }


def fpga_monitor_session_profile(
    case_ids: tuple[str, ...] = DEFAULT_SESSION_CASE_IDS,
) -> MonitorSessionProfile:
    return MonitorSessionProfile(
        story=FPGA_MONITOR_SESSION_STORY,
        status=FPGA_MONITOR_SESSION_STATUS,
        monitor_firmware_gate=fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL,
        bram_image_gate=fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        smoke_corpus_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        selected_cases=tuple(_selection_for_case(case_id) for case_id in case_ids),
        session_rules=(
            "each program run is a bounded monitor transaction with HALT, LOAD_IMAGE, READ_STATUS, and RESUME",
            "LOAD_IMAGE supplies manifest and data-RAM hashes from the I26-S02 generated image bundle",
            "each selected case must be image_ready in the I26-S05 smoke corpus",
            "distinct expected LED, UART, and probe signatures are preserved with the run observation",
        ),
        handoffs=(
            "I32-S04 adds register, CSR/CCSR, memory-window, and replay snapshot capture for failed sessions",
            "I32-S05 expands the interactive board corpus beyond this two-program executable fixture",
            "I32-S06 captures a physical board session or blocker using the same command and signature fields",
        ),
    )


def run_monitor_session(
    case_ids: tuple[str, ...] = DEFAULT_SESSION_CASE_IDS,
) -> MonitorSessionRun:
    state = fpga_monitor_firmware.fpga_monitor_firmware_state()
    initial_hello = fpga_monitor_firmware.execute_monitor_command(
        state,
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_HELLO
        ),
    )
    program_runs: list[MonitorProgramRun] = []
    for index, case_id in enumerate(case_ids, start=1):
        program_runs.append(_run_one_program(state, case_id, index))
    final_snapshot = state.snapshot()
    issues = _session_issues(initial_hello, tuple(program_runs), final_snapshot)
    return MonitorSessionRun(
        story=FPGA_MONITOR_SESSION_STORY,
        status=FPGA_MONITOR_SESSION_STATUS,
        initial_hello=initial_hello,
        program_runs=tuple(program_runs),
        final_snapshot=final_snapshot,
        issues=tuple(issues),
    )


def fpga_monitor_session_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_monitor_session_profile().as_dict(), indent=indent, sort_keys=True)


def fpga_monitor_session_run_json(*, indent: int = 2) -> str:
    return json.dumps(run_monitor_session().as_dict(), indent=indent, sort_keys=True)


def render_fpga_monitor_session(profile: MonitorSessionProfile | None = None) -> str:
    if profile is None:
        profile = fpga_monitor_session_profile()
    lines = [
        "# FPGA Monitor Multi-Program Session",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Monitor firmware gate: `{profile.monitor_firmware_gate}`",
        f"BRAM image gate: `{profile.bram_image_gate}`",
        f"Smoke corpus gate: `{profile.smoke_corpus_gate}`",
        "",
        "## Selected Cases",
        "",
        "| Case | Program | Expected result | Replay |",
        "| --- | --- | --- | --- |",
    ]
    for selection in profile.selected_cases:
        lines.append(
            f"| `{selection.case_id}` | `{selection.program_id}` | "
            f"`{selection.expected_result}` | `{selection.replay_case_id}` |"
        )
    lines.extend(["", "## Session Rules", ""])
    lines.extend(f"- {rule}." for rule in profile.session_rules)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_monitor_session(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_monitor_session_profile()
    issues: list[str] = []

    if profile.story != FPGA_MONITOR_SESSION_STORY:
        issues.append(f"monitor session story must be {FPGA_MONITOR_SESSION_STORY}")
    if profile.status != FPGA_MONITOR_SESSION_STATUS:
        issues.append("monitor session status must remain fixture-defined")
    if profile.monitor_firmware_gate != fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL:
        issues.append("monitor session must depend on I32-S02 monitor firmware")
    if profile.bram_image_gate != fpga_bram_images.FPGA_BRAM_IMAGES_TOOL:
        issues.append("monitor session must depend on I26-S02 BRAM image generation")
    if profile.smoke_corpus_gate != fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL:
        issues.append("monitor session must depend on I26-S05 smoke corpus")

    issues.extend(fpga_monitor_firmware.validate_fpga_monitor_firmware(root))
    issues.extend(fpga_bram_images.validate_fpga_bram_images(root))
    issues.extend(fpga_smoke_corpus.validate_fpga_smoke_corpus(root))

    if len(profile.selected_cases) < 2:
        issues.append("monitor session must select at least two programs")
    if len({case.case_id for case in profile.selected_cases}) != len(profile.selected_cases):
        issues.append("monitor session selected cases must be unique")
    if len({case.category for case in profile.selected_cases}) < 2:
        issues.append("monitor session selected cases must cover distinct categories")
    for selection in profile.selected_cases:
        if len(selection.manifest_image_sha256) != 64:
            issues.append(f"{selection.case_id}: manifest hash must be SHA-256")
        if len(selection.ram_image_sha256) != 64:
            issues.append(f"{selection.case_id}: RAM hash must be SHA-256")

    run = run_monitor_session()
    if not run.passed:
        issues.extend(run.issues)
    if len(run.program_runs) < 2:
        issues.append("monitor session run must execute at least two programs")
    signatures = {program.observation.signature_digest for program in run.program_runs}
    if len(signatures) != len(run.program_runs):
        issues.append("monitor session observations must have distinct signatures")
    for program in run.program_runs:
        if not program.passed:
            issues.append(f"{program.case_id}: {'; '.join(program.issues)}")
        if len(program.command_results) > fpga_monitor_firmware.MAX_MONITOR_COMMANDS:
            issues.append(f"{program.case_id}: transaction exceeded monitor command bound")
        for result in program.command_results:
            packet_issues = fpga_debug_status.validate_debug_status_packet(
                result.report.debug_packet
            )
            if packet_issues:
                issues.append(
                    f"{program.case_id}:{result.request.command_name}: invalid debug packet "
                    + "; ".join(packet_issues)
                )

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"monitor session objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_MONITOR_SESSION_DOC)
    for token in (
        "Story: I32-S03",
        FPGA_MONITOR_SESSION_TOOL,
        fpga_monitor_firmware.FPGA_MONITOR_FIRMWARE_TOOL,
        fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        "scalar_control.call_return",
        "trap_syscall.sys_pause_iret",
        "LOAD_IMAGE",
        "RESUME",
        "manifest_image_sha256",
        "ram_image_sha256",
        "expected LED",
        "expected UART",
        "expected probe",
        "signature_digest",
        "I32-S04",
        "I32-S05",
        "I32-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MONITOR_SESSION_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _run_one_program(
    state: fpga_monitor_firmware.MonitorFirmwareState,
    case_id: str,
    run_index: int,
) -> MonitorProgramRun:
    case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(case_id)
    request = fpga_program_loader.program_load_request_for_program(case.program_id)
    commands = (
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_HALT,
            reason=f"prepare_{case.category}",
        ),
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_LOAD_IMAGE,
            program_id=case.program_id,
            cell_count=fpga_program_loader.MAX_CHUNK_CELLS,
            manifest_image_sha256=request.manifest_image_sha256,
            ram_image_sha256=request.ram_image_sha256,
        ),
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_READ_STATUS,
        ),
        fpga_monitor_firmware.MonitorFirmwareCommandRequest(
            fpga_monitor_profile.COMMAND_RESUME,
            entry_cell=platform.RESET_VECTOR,
        ),
    )
    results = tuple(
        fpga_monitor_firmware.execute_monitor_command(state, command)
        for command in commands
    )
    observation = _program_observation(case, request, run_index, results)
    return MonitorProgramRun(
        run_index=run_index,
        case_id=case.case_id,
        command_results=results,
        observation=observation,
        issues=tuple(_program_issues(case, request, results, observation)),
    )


def _program_observation(
    case: fpga_smoke_corpus.FpgaSmokeCorpusCase,
    request: fpga_program_loader.ProgramLoadRequest,
    run_index: int,
    results: tuple[fpga_monitor_firmware.MonitorFirmwareCommandResult, ...],
) -> MonitorProgramObservation:
    load_result = _result_for_command(results, fpga_monitor_profile.COMMAND_LOAD_IMAGE)
    resume_result = _result_for_command(results, fpga_monitor_profile.COMMAND_RESUME)
    resume_packet = resume_result.report.debug_packet
    return MonitorProgramObservation(
        run_index=run_index,
        case_id=case.case_id,
        category=case.category,
        program_id=case.program_id,
        manifest_image_sha256=request.manifest_image_sha256,
        ram_image_sha256=request.ram_image_sha256,
        loaded_cells=load_result.installed_cells,
        loader_status_name=load_result.loader_status_name,
        monitor_status_sequence=tuple(result.status_name for result in results),
        started=resume_result.passed,
        start_pc_cell=resume_result.state_after.pc_cell,
        status_packet_sequence=resume_packet.sequence,
        status_packet_state=fpga_debug_status.fpga_debug_status_profile().pass_fail_states[
            resume_packet.pass_fail_state
        ],
        status_packet_fault_code=resume_packet.fault_code,
        expected_result=case.expected_result,
        expected_led_signature=case.expected_led_signature,
        expected_uart_signature=case.expected_uart_signature,
        expected_probe_signature=case.expected_probe_signature,
        debug_signature_kind=_debug_signature_kind(case),
        signature_digest=_signature_digest(case),
        replay_case_id=case.replay_case_id,
    )


def _program_issues(
    case: fpga_smoke_corpus.FpgaSmokeCorpusCase,
    request: fpga_program_loader.ProgramLoadRequest,
    results: tuple[fpga_monitor_firmware.MonitorFirmwareCommandResult, ...],
    observation: MonitorProgramObservation,
) -> list[str]:
    issues: list[str] = []
    if len(results) > fpga_monitor_firmware.MAX_MONITOR_COMMANDS:
        issues.append("program transaction exceeds monitor command bound")
    expected_sequence = ("OK", "OK", "OK", "OK")
    if observation.monitor_status_sequence != expected_sequence:
        issues.append(
            f"monitor status sequence {observation.monitor_status_sequence!r} "
            f"did not match {expected_sequence!r}"
        )
    if observation.loader_status_name != "OK":
        issues.append("program LOAD_IMAGE did not return loader OK")
    if observation.loaded_cells != len(request.payload_cells):
        issues.append("loaded cell count does not match the generated RAM image")
    if not observation.started:
        issues.append("program did not start through RESUME")
    if observation.start_pc_cell != platform.RESET_VECTOR:
        issues.append("program did not start at the reset vector")
    if observation.status_packet_fault_code != 0:
        issues.append("monitor resume status packet carried a fault")
    if not observation.signature_digest:
        issues.append("program observation did not preserve a signature digest")
    if case.bram_image_status != "image_ready":
        issues.append("selected session case is not image_ready")
    return issues


def _session_issues(
    initial_hello: fpga_monitor_firmware.MonitorFirmwareCommandResult,
    program_runs: tuple[MonitorProgramRun, ...],
    final_snapshot: fpga_monitor_firmware.MonitorFirmwareSnapshot,
) -> list[str]:
    issues: list[str] = []
    if not initial_hello.passed:
        issues.append("initial HELLO did not pass")
    if len(program_runs) < 2:
        issues.append("session must include at least two program runs")
    loaded_programs = [run.observation.program_id for run in program_runs]
    if len(loaded_programs) != len(set(loaded_programs)):
        issues.append("session loaded duplicate programs")
    signature_digests = [run.observation.signature_digest for run in program_runs]
    if len(signature_digests) != len(set(signature_digests)):
        issues.append("session observations are not distinct")
    for run in program_runs:
        if not run.passed:
            issues.append(f"{run.case_id}: {'; '.join(run.issues)}")
    if program_runs and final_snapshot.loaded_program_id != program_runs[-1].observation.program_id:
        issues.append("final monitor state does not preserve the last loaded program ID")
    if final_snapshot.monitor_state != fpga_monitor_firmware.STATE_PROGRAM_RUNNING:
        issues.append("session did not leave the final program running")
    if final_snapshot.tag_bits_set != 0:
        issues.append("session left tag RAM bits set")
    return issues


def _selection_for_case(case_id: str) -> MonitorSessionCaseSelection:
    case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(case_id)
    request = fpga_program_loader.program_load_request_for_program(case.program_id)
    return MonitorSessionCaseSelection(
        case_id=case.case_id,
        category=case.category,
        program_id=case.program_id,
        source_case_id=case.source_case_id,
        expected_result=case.expected_result,
        manifest_image_sha256=request.manifest_image_sha256,
        ram_image_sha256=request.ram_image_sha256,
        replay_case_id=case.replay_case_id,
        expected_led_signature=case.expected_led_signature,
        expected_uart_signature=case.expected_uart_signature,
        expected_probe_signature=case.expected_probe_signature,
    )


def _result_for_command(
    results: tuple[fpga_monitor_firmware.MonitorFirmwareCommandResult, ...],
    command_name: str,
) -> fpga_monitor_firmware.MonitorFirmwareCommandResult:
    for result in results:
        if result.request.command_name == command_name:
            return result
    raise KeyError(command_name)


def _signature_digest(case: fpga_smoke_corpus.FpgaSmokeCorpusCase) -> str:
    payload = "|".join(
        (
            case.case_id,
            case.expected_result,
            case.expected_led_signature,
            case.expected_uart_signature,
            case.expected_probe_signature,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _debug_signature_kind(case: fpga_smoke_corpus.FpgaSmokeCorpusCase) -> str:
    expected = case.expected_result.lower()
    if expected.startswith("pass"):
        return "pass_progress"
    if expected.startswith("trap"):
        return "trap_debug"
    if expected.startswith("fault"):
        return "fault_debug"
    text = " ".join(
        (
            case.expected_result,
            case.expected_led_signature,
            case.expected_uart_signature,
            case.expected_probe_signature,
        )
    ).lower()
    if "trap" in text:
        return "trap_debug"
    if "fault" in text:
        return "fault_debug"
    if "pass" in text:
        return "pass_progress"
    if "retire" in text:
        return "retire_progress"
    return "debug_status"


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

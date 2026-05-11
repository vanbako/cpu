"""Interactive FPGA board program corpus.

Owner stories:
- I32-S05: publish the interactive board program corpus.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_monitor_firmware,
    fpga_monitor_profile,
    fpga_monitor_session,
    fpga_program_loader,
    fpga_smoke_corpus,
    toolchain_corpus,
    verilator_harness,
)


JsonValue = Any

FPGA_INTERACTIVE_CORPUS_STORY = "I32-S05"
FPGA_INTERACTIVE_CORPUS_DOC = Path("docs/implementation/fpga-interactive-program-corpus.md")
FPGA_INTERACTIVE_CORPUS_TOOL = "python tools\\fpga_interactive_corpus.py --check"
FPGA_INTERACTIVE_CORPUS_STATUS = "published_interactive_board_program_corpus"
TOOLCHAIN_CORPUS_TOOL = "python tools\\toolchain_corpus.py --check"

LOAD_MODE_MONITOR_IMAGE = "monitor_load_image"
LOAD_MODE_LOADER_REJECTION = "monitor_loader_rejection"
LOAD_MODE_REPLAY_ONLY = "replay_only_until_fault_harness"

REQUIRED_INTERACTIVE_CATEGORIES = frozenset(
    {
        "scalar_control",
        "capability_memory",
        "trap_syscall",
        "loader_rejection",
        "failure_path",
    }
)

IMAGE_READY_CASE_IDS = (
    "scalar_control.call_return",
    "capability_memory.csc_clc_st48_ld48",
    "trap_syscall.sys_pause_iret",
)
FAILURE_PATH_CASE_ID = "failure_path.divide_by_zero"
LOADER_REJECTION_CASE_ID = "loader_rejection.bad_hash"


@dataclass(frozen=True)
class InteractiveCorpusCase:
    case_id: str
    category: str
    source: str
    source_case_id: str
    source_toolchain_case_id: str
    program_id: str
    load_mode: str
    board_readiness: str
    manifest_hash_kind: str
    manifest_image_sha256: str
    ram_image_sha256: str
    rejected_manifest_image_sha256: str
    expected_result: str
    expected_monitor_status: str
    expected_loader_status: str
    monitor_commands: tuple[str, ...]
    replay_case_id: str
    replay_command: str
    expected_led_signature: str
    expected_uart_signature: str
    expected_probe_signature: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "source": self.source,
            "source_case_id": self.source_case_id,
            "source_toolchain_case_id": self.source_toolchain_case_id,
            "program_id": self.program_id,
            "load_mode": self.load_mode,
            "board_readiness": self.board_readiness,
            "manifest_hash_kind": self.manifest_hash_kind,
            "manifest_image_sha256": self.manifest_image_sha256,
            "ram_image_sha256": self.ram_image_sha256,
            "rejected_manifest_image_sha256": self.rejected_manifest_image_sha256,
            "expected_result": self.expected_result,
            "expected_monitor_status": self.expected_monitor_status,
            "expected_loader_status": self.expected_loader_status,
            "monitor_commands": list(self.monitor_commands),
            "replay_case_id": self.replay_case_id,
            "replay_command": self.replay_command,
            "expected_led_signature": self.expected_led_signature,
            "expected_uart_signature": self.expected_uart_signature,
            "expected_probe_signature": self.expected_probe_signature,
        }


@dataclass(frozen=True)
class InteractiveCorpusProfile:
    story: str
    status: str
    monitor_session_gate: str
    toolchain_corpus_gate: str
    smoke_corpus_gate: str
    loader_gate: str
    required_categories: tuple[str, ...]
    cases: tuple[InteractiveCorpusCase, ...]
    publication_rules: tuple[str, ...]
    handoffs: tuple[str, ...]

    def case_by_id(self, case_id: str) -> InteractiveCorpusCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "monitor_session_gate": self.monitor_session_gate,
            "toolchain_corpus_gate": self.toolchain_corpus_gate,
            "smoke_corpus_gate": self.smoke_corpus_gate,
            "loader_gate": self.loader_gate,
            "required_categories": list(self.required_categories),
            "cases": [case.as_dict() for case in self.cases],
            "publication_rules": list(self.publication_rules),
            "handoffs": list(self.handoffs),
        }


def fpga_interactive_corpus_profile() -> InteractiveCorpusProfile:
    cases = (
        *(_image_ready_entry(case_id) for case_id in IMAGE_READY_CASE_IDS),
        _loader_rejection_entry(),
        _failure_path_entry(),
    )
    return InteractiveCorpusProfile(
        story=FPGA_INTERACTIVE_CORPUS_STORY,
        status=FPGA_INTERACTIVE_CORPUS_STATUS,
        monitor_session_gate=fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        toolchain_corpus_gate=TOOLCHAIN_CORPUS_TOOL,
        smoke_corpus_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        loader_gate=fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        required_categories=tuple(sorted(REQUIRED_INTERACTIVE_CATEGORIES)),
        cases=cases,
        publication_rules=(
            "image_ready cases use generated manifest_image_sha256 and ram_image_sha256 values",
            "loader rejection cases publish both the selected manifest hash and rejected stale hash",
            "failure-path cases retain replay-only planned identity hashes until the harness emits a board image",
            "every case carries expected LED, UART, probe, and replay or fixture reproduction fields",
        ),
        handoffs=(
            "I32-S06 consumes this corpus to capture an interactive multi-program board session",
            "loader rejection remains a ROM monitor fixture until physical UART evidence is archived",
            "failure-path replay-only entries must be replaced with image_ready manifests when the fault harness exists",
        ),
    )


def fpga_interactive_corpus_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_interactive_corpus_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_interactive_corpus(
    profile: InteractiveCorpusProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_interactive_corpus_profile()
    lines = [
        "# FPGA Interactive Program Corpus",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Monitor session gate: `{profile.monitor_session_gate}`",
        f"Toolchain corpus gate: `{profile.toolchain_corpus_gate}`",
        f"Smoke corpus gate: `{profile.smoke_corpus_gate}`",
        f"Loader gate: `{profile.loader_gate}`",
        "",
        "## Cases",
        "",
        "| Case | Category | Program | Load mode | Expected result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in profile.cases:
        lines.append(
            f"| `{case.case_id}` | `{case.category}` | `{case.program_id}` | "
            f"`{case.load_mode}` | `{case.expected_result}` |"
        )
    lines.extend(["", "## Publication Rules", ""])
    lines.extend(f"- {rule}." for rule in profile.publication_rules)
    lines.append("")
    return "\n".join(lines)


def run_loader_rejection_case() -> fpga_monitor_firmware.MonitorFirmwareFixtureRun:
    return fpga_monitor_firmware.run_monitor_firmware_fixture(
        fpga_monitor_firmware.FIXTURE_REJECT_BAD_HASH
    )


def validate_fpga_interactive_corpus(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_interactive_corpus_profile()
    issues: list[str] = []

    if profile.story != FPGA_INTERACTIVE_CORPUS_STORY:
        issues.append(f"interactive corpus story must be {FPGA_INTERACTIVE_CORPUS_STORY}")
    if profile.status != FPGA_INTERACTIVE_CORPUS_STATUS:
        issues.append("interactive corpus status must remain publication-defined")
    if profile.monitor_session_gate != fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL:
        issues.append("interactive corpus must depend on I32-S03 monitor sessions")
    if profile.toolchain_corpus_gate != TOOLCHAIN_CORPUS_TOOL:
        issues.append("interactive corpus must depend on the I17-S04 toolchain corpus")
    if profile.smoke_corpus_gate != fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL:
        issues.append("interactive corpus must depend on the I26-S05 smoke corpus")
    if profile.loader_gate != fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL:
        issues.append("interactive corpus must name the I26-S04 loader gate")

    issues.extend(fpga_monitor_session.validate_fpga_monitor_session(root))
    issues.extend(fpga_smoke_corpus.validate_fpga_smoke_corpus(root))
    issues.extend(toolchain_corpus.validate_toolchain_corpus())

    case_ids = [case.case_id for case in profile.cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("interactive corpus case IDs must be unique")
    categories = {case.category for case in profile.cases}
    for category in sorted(REQUIRED_INTERACTIVE_CATEGORIES - categories):
        issues.append(f"missing interactive corpus category {category}")
    for category in sorted(categories - REQUIRED_INTERACTIVE_CATEGORIES):
        issues.append(f"unknown interactive corpus category {category}")

    replay_case_ids = set(verilator_harness.regression_case_ids(verilator_harness.HarnessSuite.ALL))
    for case in profile.cases:
        _validate_case_common(case, issues)
        if case.load_mode == LOAD_MODE_MONITOR_IMAGE:
            _validate_image_ready_case(case, issues, replay_case_ids)
        elif case.load_mode == LOAD_MODE_LOADER_REJECTION:
            _validate_loader_rejection_case(case, issues)
        elif case.load_mode == LOAD_MODE_REPLAY_ONLY:
            _validate_replay_only_case(case, issues, replay_case_ids)
        else:
            issues.append(f"{case.case_id}: unknown load mode {case.load_mode!r}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run_loader_rejection_case().as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"interactive corpus objects are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_INTERACTIVE_CORPUS_DOC)
    for token in (
        "Story: I32-S05",
        FPGA_INTERACTIVE_CORPUS_TOOL,
        fpga_monitor_session.FPGA_MONITOR_SESSION_TOOL,
        TOOLCHAIN_CORPUS_TOOL,
        fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        fpga_program_loader.FPGA_PROGRAM_LOADER_TOOL,
        "scalar/control",
        "capability memory",
        "trap/syscall",
        "loader rejection",
        "failure-path",
        "scalar_control.call_return",
        "capability_memory.csc_clc_st48_ld48",
        "trap_syscall.sys_pause_iret",
        LOADER_REJECTION_CASE_ID,
        FAILURE_PATH_CASE_ID,
        "manifest_image_sha256",
        "ram_image_sha256",
        "rejected_manifest_image_sha256",
        "expected UART",
        "expected probe",
        "BAD_HASH",
        "LOADER_ERROR",
        "python tools\\verilator_diff_harness.py --case-id fault_cases.divide_by_zero",
        "I32-S06",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_INTERACTIVE_CORPUS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _image_ready_entry(case_id: str) -> InteractiveCorpusCase:
    case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(case_id)
    request = fpga_program_loader.program_load_request_for_program(case.program_id)
    return InteractiveCorpusCase(
        case_id=case.case_id,
        category=case.category,
        source=case.source,
        source_case_id=case.source_case_id,
        source_toolchain_case_id=case.source_case_id,
        program_id=case.program_id,
        load_mode=LOAD_MODE_MONITOR_IMAGE,
        board_readiness=case.board_readiness,
        manifest_hash_kind="generated_bram_manifest",
        manifest_image_sha256=request.manifest_image_sha256,
        ram_image_sha256=request.ram_image_sha256,
        rejected_manifest_image_sha256="",
        expected_result=case.expected_result,
        expected_monitor_status="OK",
        expected_loader_status="OK",
        monitor_commands=(
            fpga_monitor_profile.COMMAND_HALT,
            fpga_monitor_profile.COMMAND_LOAD_IMAGE,
            fpga_monitor_profile.COMMAND_READ_STATUS,
            fpga_monitor_profile.COMMAND_RESUME,
        ),
        replay_case_id=case.replay_case_id,
        replay_command=_verilator_replay_command(case.replay_case_id),
        expected_led_signature=case.expected_led_signature,
        expected_uart_signature=case.expected_uart_signature,
        expected_probe_signature=case.expected_probe_signature,
    )


def _loader_rejection_entry() -> InteractiveCorpusCase:
    program_id = "relocation.branch_call_data_fpga"
    request = fpga_program_loader.program_load_request_for_program(program_id)
    plan = fpga_program_loader.fpga_program_loader_profile().plan_by_program_id(program_id)
    run = run_loader_rejection_case()
    failed = run.command_results[-1]
    return InteractiveCorpusCase(
        case_id=LOADER_REJECTION_CASE_ID,
        category="loader_rejection",
        source="I32-S02 ROM monitor bad-hash fixture over I26-S04 loader metadata",
        source_case_id=fpga_monitor_firmware.FIXTURE_REJECT_BAD_HASH,
        source_toolchain_case_id=plan.source_case_id,
        program_id=program_id,
        load_mode=LOAD_MODE_LOADER_REJECTION,
        board_readiness="ready_as_monitor_rejection_fixture",
        manifest_hash_kind="generated_bram_manifest_with_rejected_hash_fixture",
        manifest_image_sha256=request.manifest_image_sha256,
        ram_image_sha256=request.ram_image_sha256,
        rejected_manifest_image_sha256="0" * 64,
        expected_result="loader_rejected_before_memory_mutation",
        expected_monitor_status="LOADER_ERROR",
        expected_loader_status="BAD_HASH",
        monitor_commands=(
            fpga_monitor_profile.COMMAND_HELLO,
            fpga_monitor_profile.COMMAND_HALT,
            fpga_monitor_profile.COMMAND_LOAD_IMAGE,
        ),
        replay_case_id=fpga_monitor_firmware.FIXTURE_REJECT_BAD_HASH,
        replay_command=(
            "python tools\\fpga_monitor_firmware.py --run-fixture "
            f"{fpga_monitor_firmware.FIXTURE_REJECT_BAD_HASH}"
        ),
        expected_led_signature="pass_led_o stays deasserted; fail/status observation reports loader rejection",
        expected_uart_signature=failed.report.uart_message.strip(),
        expected_probe_signature=(
            "data_ram checksum and tag_ram bits remain unchanged; loaded_program_id remains empty"
        ),
    )


def _failure_path_entry() -> InteractiveCorpusCase:
    case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(FAILURE_PATH_CASE_ID)
    return InteractiveCorpusCase(
        case_id=case.case_id,
        category=case.category,
        source=case.source,
        source_case_id=case.source_case_id,
        source_toolchain_case_id="",
        program_id=case.program_id,
        load_mode=LOAD_MODE_REPLAY_ONLY,
        board_readiness=case.board_readiness,
        manifest_hash_kind="planned_replay_identity_until_fault_harness",
        manifest_image_sha256=_planned_hash("manifest", case),
        ram_image_sha256=_planned_hash("ram", case),
        rejected_manifest_image_sha256="",
        expected_result=case.expected_result,
        expected_monitor_status="REPLAY_ONLY",
        expected_loader_status="REPLAY_ONLY",
        monitor_commands=("CAPTURE_STATUS", "MAP_REPLAY", "RUN_REPLAY"),
        replay_case_id=case.replay_case_id,
        replay_command=_verilator_replay_command(case.replay_case_id),
        expected_led_signature=case.expected_led_signature,
        expected_uart_signature=case.expected_uart_signature,
        expected_probe_signature=case.expected_probe_signature,
    )


def _validate_case_common(case: InteractiveCorpusCase, issues: list[str]) -> None:
    if not case.case_id:
        issues.append("interactive corpus case ID must not be empty")
    if not case.program_id:
        issues.append(f"{case.case_id}: program_id must not be empty")
    if not _is_sha256(case.manifest_image_sha256):
        issues.append(f"{case.case_id}: manifest_image_sha256 must be SHA-256")
    if not _is_sha256(case.ram_image_sha256):
        issues.append(f"{case.case_id}: ram_image_sha256 must be SHA-256")
    if case.rejected_manifest_image_sha256 and not _is_sha256(case.rejected_manifest_image_sha256):
        issues.append(f"{case.case_id}: rejected_manifest_image_sha256 must be SHA-256")
    if not case.monitor_commands:
        issues.append(f"{case.case_id}: monitor command sequence must not be empty")
    if not case.replay_command:
        issues.append(f"{case.case_id}: replay or fixture command must not be empty")
    for field_name, value in (
        ("expected_led_signature", case.expected_led_signature),
        ("expected_uart_signature", case.expected_uart_signature),
        ("expected_probe_signature", case.expected_probe_signature),
    ):
        if not value:
            issues.append(f"{case.case_id}: missing {field_name}")
    if "led" not in case.expected_led_signature.lower():
        issues.append(f"{case.case_id}: expected LED signature must name LED observation")
    if not any(
        token in case.expected_uart_signature.lower()
        for token in ("fault", "pass", "retire", "trap", "bad_hash", "loader")
    ):
        issues.append(f"{case.case_id}: expected UART signature must name observable status")


def _validate_image_ready_case(
    case: InteractiveCorpusCase,
    issues: list[str],
    replay_case_ids: set[str],
) -> None:
    smoke = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(case.case_id)
    if smoke.bram_image_status != "image_ready":
        issues.append(f"{case.case_id}: interactive monitor image case must be image_ready")
    request = fpga_program_loader.program_load_request_for_program(smoke.program_id)
    if case.manifest_image_sha256 != request.manifest_image_sha256:
        issues.append(f"{case.case_id}: manifest hash does not match loader request")
    if case.ram_image_sha256 != request.ram_image_sha256:
        issues.append(f"{case.case_id}: RAM hash does not match loader request")
    try:
        toolchain_corpus.toolchain_case_by_id(case.source_toolchain_case_id)
    except KeyError:
        issues.append(f"{case.case_id}: source toolchain case is not in I17-S04")
    if case.expected_monitor_status != "OK" or case.expected_loader_status != "OK":
        issues.append(f"{case.case_id}: image-ready case must expect monitor and loader OK")
    if case.replay_case_id not in replay_case_ids:
        issues.append(f"{case.case_id}: replay case is not in the Verilator corpus")
    if "verilator_diff_harness.py --case-id" not in case.replay_command:
        issues.append(f"{case.case_id}: replay command must name the Verilator diff harness")


def _validate_loader_rejection_case(case: InteractiveCorpusCase, issues: list[str]) -> None:
    run = run_loader_rejection_case()
    if not run.passed:
        issues.append(f"{case.case_id}: loader rejection fixture did not pass")
    if case.expected_monitor_status != "LOADER_ERROR":
        issues.append(f"{case.case_id}: loader rejection must expect LOADER_ERROR")
    if case.expected_loader_status != "BAD_HASH":
        issues.append(f"{case.case_id}: loader rejection must expect BAD_HASH")
    if case.rejected_manifest_image_sha256 == case.manifest_image_sha256:
        issues.append(f"{case.case_id}: rejected hash must differ from selected manifest hash")
    if "BAD_HASH" not in case.expected_uart_signature:
        issues.append(f"{case.case_id}: UART signature must expose BAD_HASH")
    if "fpga_monitor_firmware.py --run-fixture" not in case.replay_command:
        issues.append(f"{case.case_id}: rejection case must reproduce through the monitor fixture")
    try:
        toolchain_corpus.toolchain_case_by_id(case.source_toolchain_case_id)
    except KeyError:
        issues.append(f"{case.case_id}: source toolchain case is not in I17-S04")
    final = run.final_snapshot
    initial = run.initial_snapshot
    if final.loaded_program_id != initial.loaded_program_id:
        issues.append(f"{case.case_id}: bad-hash fixture changed loaded_program_id")
    if final.data_ram_checksum != initial.data_ram_checksum:
        issues.append(f"{case.case_id}: bad-hash fixture mutated data_ram")
    if final.tag_bits_set != initial.tag_bits_set:
        issues.append(f"{case.case_id}: bad-hash fixture mutated tag_ram")


def _validate_replay_only_case(
    case: InteractiveCorpusCase,
    issues: list[str],
    replay_case_ids: set[str],
) -> None:
    smoke = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(case.case_id)
    if smoke.bram_image_status == "image_ready":
        issues.append(f"{case.case_id}: replay-only case unexpectedly became image_ready")
    if case.replay_case_id not in replay_case_ids:
        issues.append(f"{case.case_id}: replay case is not in the Verilator corpus")
    if "verilator_diff_harness.py --case-id" not in case.replay_command:
        issues.append(f"{case.case_id}: replay-only case must name the Verilator diff harness")
    if case.expected_monitor_status != "REPLAY_ONLY" or case.expected_loader_status != "REPLAY_ONLY":
        issues.append(f"{case.case_id}: replay-only case must be explicitly marked")
    if "planned" not in case.manifest_hash_kind:
        issues.append(f"{case.case_id}: replay-only manifest hash kind must be planned")


def _verilator_replay_command(case_id: str) -> str:
    return f"python tools\\verilator_diff_harness.py --case-id {case_id}"


def _planned_hash(kind: str, case: fpga_smoke_corpus.FpgaSmokeCorpusCase) -> str:
    payload = "|".join(
        (
            "I32-S05",
            kind,
            case.case_id,
            case.program_id,
            case.bram_image_status,
            case.replay_case_id,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

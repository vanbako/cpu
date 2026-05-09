"""Map FPGA debug/status captures to Verilator replay cases.

Owner stories:
- I25-S04: map board failure captures back to Verilator replay cases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_bringup, fpga_debug_status, fpga_uart_status, instructions, verilator_harness


JsonValue = Any

FPGA_REPLAY_MAPPER_STORY = "I25-S04"
FPGA_REPLAY_MAPPER_DOC = Path("docs/implementation/fpga-replay-mapper.md")
FPGA_REPLAY_MAPPER_TOOL = "python tools\\fpga_replay_mapper.py --check"
OBSERVED_TRACE_TEMPLATE = "build\\fpga\\captures\\status_sequence_{sequence}_retire_trace.json"


@dataclass(frozen=True)
class ReplayHeuristic:
    name: str
    condition: str
    primary_case_id: str
    secondary_case_ids: tuple[str, ...]
    rationale: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "condition": self.condition,
            "primary_case_id": self.primary_case_id,
            "secondary_case_ids": list(self.secondary_case_ids),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ReplayCandidate:
    case_id: str
    score: int
    source: str
    suite: str
    golden_trace_case_id: str
    replay_command: str
    compare_command: str
    rationale: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "score": self.score,
            "source": self.source,
            "suite": self.suite,
            "golden_trace_case_id": self.golden_trace_case_id,
            "replay_command": self.replay_command,
            "compare_command": self.compare_command,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ReplayMapping:
    story: str
    packet: dict[str, JsonValue]
    packet_hex: str
    pass_fail_state: str
    flag_names: tuple[str, ...]
    candidates: tuple[ReplayCandidate, ...]
    diagnostics: tuple[str, ...]
    preservation_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "packet": self.packet,
            "packet_hex": self.packet_hex,
            "pass_fail_state": self.pass_fail_state,
            "flag_names": list(self.flag_names),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "diagnostics": list(self.diagnostics),
            "preservation_rules": list(self.preservation_rules),
        }


@dataclass(frozen=True)
class FpgaReplayMapperProfile:
    story: str
    packet_gate: str
    uart_gate: str
    regression_gate: str
    bringup_gate: str
    heuristics: tuple[ReplayHeuristic, ...]
    required_capture_fields: tuple[str, ...]
    output_commands: tuple[str, ...]
    preservation_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "packet_gate": self.packet_gate,
            "uart_gate": self.uart_gate,
            "regression_gate": self.regression_gate,
            "bringup_gate": self.bringup_gate,
            "heuristics": [heuristic.as_dict() for heuristic in self.heuristics],
            "required_capture_fields": list(self.required_capture_fields),
            "output_commands": list(self.output_commands),
            "preservation_rules": list(self.preservation_rules),
        }


def fpga_replay_mapper_profile() -> FpgaReplayMapperProfile:
    return FpgaReplayMapperProfile(
        story=FPGA_REPLAY_MAPPER_STORY,
        packet_gate=fpga_debug_status.FPGA_DEBUG_STATUS_TOOL,
        uart_gate=fpga_uart_status.FPGA_UART_STATUS_TOOL,
        regression_gate="python tools\\verilator_diff_harness.py --case-id <case_id>",
        bringup_gate=fpga_bringup.FPGA_BRINGUP_TOOL,
        heuristics=(
            ReplayHeuristic(
                "reset_or_idle",
                "reset_asserted or core_idle with retire_count == 0",
                "core.shell.reset_idle",
                (),
                "start with the integrated reset shell when the board never reaches retire",
            ),
            ReplayHeuristic(
                "first_pass_or_running",
                "first_pass/pass_led or retire_count >= 8 without a fault",
                "core.scalar.integer_ops_add_mul",
                ("integer_ops.add_mul", "reset_smoke.add_slot0"),
                "use the fast integrated retire path as the nearest passing core replay",
            ),
            ReplayHeuristic(
                "fetch_decode_fault",
                "illegal, breakpoint, align, or low-PC access fault",
                "core.fetch_decode.slot1_48bit_placement",
                ("fault_cases.slot1_48bit_placement",),
                "fetch/decode cases preserve PC, slot, and first fault diagnostics",
            ),
            ReplayHeuristic(
                "capability_or_memory_fault",
                "capability tag/bounds/permission/local-store fault",
                "core.cap_mem.memory_tag_ops",
                ("fault_cases.invalid_tag_csetaddr", "memory_tag_ops.csc_clc_st48_ld48"),
                "capability and tag-memory failures should replay against the integrated cap/mem fixture",
            ),
            ReplayHeuristic(
                "trap_or_return_fault",
                "syscall or return-stack fault",
                "core.control_trap.sys_iret",
                ("traps.sys_to_tvc", "traps.sys_iret_return"),
                "trap-frame and return-stack symptoms map to the integrated control/trap fixture",
            ),
            ReplayHeuristic(
                "translation_fault",
                "page fault",
                "core.mmu_tlb.translation_sfence",
                (),
                "translation symptoms map to the integrated MMU/TLB assertion fixture",
            ),
            ReplayHeuristic(
                "scalar_fault",
                "divide-by-zero or scalar arithmetic trap",
                "fault_cases.divide_by_zero",
                ("core.scalar.integer_ops_add_mul",),
                "scalar arithmetic faults are nearest to the golden scalar fault corpus",
            ),
        ),
        required_capture_fields=(
            "flags",
            "slot",
            "pass_fail_state",
            "pc_cell",
            "retire_count",
            "fault_code",
            "trap_cause",
            "build_id",
            "sequence",
        ),
        output_commands=(
            "python tools\\fpga_debug_status_packet.py --decode-hex <packet_hex>",
            "python tools\\fpga_replay_mapper.py --map-hex <packet_hex>",
            "python tools\\verilator_diff_harness.py --case-id <case_id>",
            "python tools\\verilator_diff_harness.py --case-id <case_id> --observed-trace build\\fpga\\captures\\status_sequence_<sequence>_retire_trace.json",
        ),
        preservation_rules=(
            "preserve the original packet hex and decoded JSON",
            "preserve the selected case ID and all ranked alternatives",
            "preserve the Verilator harness first-mismatch line when an observed retire trace is available",
            "preserve the UART or GAO/ILA capture path with the board evidence",
        ),
    )


def fpga_replay_mapper_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_replay_mapper_profile().as_dict(), indent=indent, sort_keys=True)


def example_replay_mapping() -> ReplayMapping:
    return map_debug_status_packet(fpga_debug_status.example_debug_status_packet())


def map_debug_status_hex(packet_hex: str) -> ReplayMapping:
    packet = fpga_debug_status.decode_debug_status_packet(bytes.fromhex(packet_hex))
    return map_debug_status_packet(packet, packet_hex=packet_hex)


def map_debug_status_packet(
    packet: fpga_debug_status.DebugStatusPacket,
    *,
    packet_hex: str | None = None,
) -> ReplayMapping:
    if packet_hex is None:
        packet_hex = fpga_debug_status.encode_debug_status_packet(packet).hex()
    flag_names = _flag_names(packet)
    pass_fail_state = _pass_fail_state_name(packet)
    candidates = _ranked_candidates(packet, flag_names, pass_fail_state)
    diagnostics = _diagnostics_for(packet, flag_names, pass_fail_state, candidates)
    return ReplayMapping(
        story=FPGA_REPLAY_MAPPER_STORY,
        packet=packet.as_dict(),
        packet_hex=packet_hex,
        pass_fail_state=pass_fail_state,
        flag_names=flag_names,
        candidates=candidates,
        diagnostics=diagnostics,
        preservation_rules=fpga_replay_mapper_profile().preservation_rules,
    )


def render_replay_mapping(mapping: ReplayMapping | None = None) -> str:
    if mapping is None:
        mapping = example_replay_mapping()
    lines = [
        "# FPGA Replay Mapping",
        "",
        f"Story: {mapping.story}",
        f"Pass/fail state: `{mapping.pass_fail_state}`",
        f"Flags: {', '.join(f'`{flag}`' for flag in mapping.flag_names) or 'none'}",
        f"Packet sequence: {mapping.packet['sequence']}",
        "",
        "## Candidates",
        "",
        "| Score | Case ID | Suite | Source | Replay command |",
        "| --- | --- | --- | --- | --- |",
    ]
    for candidate in mapping.candidates:
        lines.append(
            f"| {candidate.score} | `{candidate.case_id}` | `{candidate.suite}` | "
            f"`{candidate.source}` | `{candidate.replay_command}` |"
        )
    lines.extend(["", "## Diagnostics", ""])
    lines.extend(f"- {line}." for line in mapping.diagnostics)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_replay_mapper(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_replay_mapper_profile()
    issues: list[str] = []

    if profile.story != FPGA_REPLAY_MAPPER_STORY:
        issues.append(f"replay mapper story must be {FPGA_REPLAY_MAPPER_STORY}")
    if profile.packet_gate != fpga_debug_status.FPGA_DEBUG_STATUS_TOOL:
        issues.append("replay mapper packet gate must be I25-S01")
    if profile.uart_gate != fpga_uart_status.FPGA_UART_STATUS_TOOL:
        issues.append("replay mapper UART gate must be I25-S02")
    if "verilator_diff_harness.py" not in profile.regression_gate:
        issues.append("replay mapper must use the Verilator differential harness")
    if profile.bringup_gate != fpga_bringup.FPGA_BRINGUP_TOOL:
        issues.append("replay mapper bring-up gate must be I23-S06")

    issues.extend(fpga_debug_status.validate_fpga_debug_status(root))
    issues.extend(fpga_uart_status.validate_fpga_uart_status(root))
    issues.extend(fpga_bringup.validate_fpga_board_bringup(root))

    all_cases = {case.case_id: case for case in verilator_harness.regression_cases(verilator_harness.HarnessSuite.ALL)}
    for heuristic in profile.heuristics:
        if heuristic.primary_case_id not in all_cases:
            issues.append(f"missing primary replay case {heuristic.primary_case_id}")
        for case_id in heuristic.secondary_case_ids:
            if case_id not in all_cases:
                issues.append(f"missing secondary replay case {case_id}")

    integrated_ids = {case.case_id for case in all_cases.values() if case.source == "integrated"}
    for required in (
        "core.shell.reset_idle",
        "core.fetch_decode.slot1_48bit_placement",
        "core.scalar.integer_ops_add_mul",
        "core.cap_mem.memory_tag_ops",
        "core.control_trap.sys_iret",
        "core.mmu_tlb.translation_sfence",
    ):
        if required not in integrated_ids:
            issues.append(f"integrated replay case missing {required}")

    example = example_replay_mapping()
    if not example.candidates:
        issues.append("example replay mapping must produce candidates")
    elif example.candidates[0].case_id != "core.scalar.integer_ops_add_mul":
        issues.append("first-pass example must map to core.scalar.integer_ops_add_mul")

    fault_packet = fpga_debug_status.DebugStatusPacket(
        flags=fpga_debug_status.debug_status_flag_mask("reset_observed", "fault_valid", "fail_led"),
        slot=1,
        pass_fail_state=3,
        pc_cell=0x1001,
        retire_count=1,
        fault_code=int(instructions.ExceptionCause.ALIGN_FAULT),
        trap_cause=int(instructions.ExceptionCause.ALIGN_FAULT),
        build_id=0x2501C0DE,
        sequence=7,
    )
    fault_mapping = map_debug_status_packet(fault_packet)
    if not fault_mapping.candidates or fault_mapping.candidates[0].case_id != "core.fetch_decode.slot1_48bit_placement":
        issues.append("align fault mapping must prefer core.fetch_decode.slot1_48bit_placement")
    if not any("first-mismatch" in line for line in fault_mapping.diagnostics):
        issues.append("fault mapping diagnostics must preserve first-mismatch output")

    doc = _read_if_exists(root / FPGA_REPLAY_MAPPER_DOC)
    for token in (
        "Story: I25-S04",
        FPGA_REPLAY_MAPPER_TOOL,
        "python tools\\fpga_debug_status_packet.py --decode-hex",
        "python tools\\fpga_replay_mapper.py --map-hex",
        "python tools\\verilator_diff_harness.py --case-id",
        "core.fetch_decode.slot1_48bit_placement",
        "core.scalar.integer_ops_add_mul",
        "core.cap_mem.memory_tag_ops",
        "core.control_trap.sys_iret",
        "core.mmu_tlb.translation_sfence",
        "fault_cases.divide_by_zero",
        "first-mismatch",
        "observed-trace",
        "UART",
        "GAO/ILA",
    ):
        if token not in doc:
            issues.append(f"{FPGA_REPLAY_MAPPER_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _ranked_candidates(
    packet: fpga_debug_status.DebugStatusPacket,
    flag_names: tuple[str, ...],
    pass_fail_state: str,
) -> tuple[ReplayCandidate, ...]:
    candidates: dict[str, ReplayCandidate] = {}

    def add(case_id: str, score: int, rationale: str) -> None:
        candidate = _candidate_for(case_id, score, packet.sequence, rationale)
        previous = candidates.get(case_id)
        if previous is None or candidate.score > previous.score:
            candidates[case_id] = candidate

    cause = _dominant_cause(packet)
    fault_like = bool(cause) or "fault_valid" in flag_names or "fail_led" in flag_names or pass_fail_state == "failed"
    pass_like = pass_fail_state == "first_pass" or "pass_led" in flag_names
    idle_like = (
        "reset_asserted" in flag_names
        or ("core_idle" in flag_names and packet.retire_count == 0)
        or pass_fail_state == "idle_or_reset"
    )

    if idle_like and packet.retire_count == 0:
        add("core.shell.reset_idle", 100, "capture is reset/idle with no retire progress")

    if pass_like and not fault_like:
        add("core.scalar.integer_ops_add_mul", 95, "capture reached first_pass without a sticky fault")
        add("integer_ops.add_mul", 82, "golden scalar retire trace is the nearest fast pass comparison")
        add("reset_smoke.add_slot0", 68, "reset smoke is useful when only early reset-to-retire behavior is suspect")

    if packet.retire_count >= 8 and not fault_like:
        add("core.scalar.integer_ops_add_mul", 88, "retire_count reached the first-test pass threshold")

    if cause in {
        instructions.ExceptionCause.ILLEGAL_INSTRUCTION,
        instructions.ExceptionCause.BREAKPOINT,
        instructions.ExceptionCause.ALIGN_FAULT,
    } or (cause == instructions.ExceptionCause.ACCESS_FAULT and packet.pc_cell < 0x2000):
        add("core.fetch_decode.slot1_48bit_placement", 98, "fault is a fetch/decode or low-PC placement symptom")
        add("fault_cases.slot1_48bit_placement", 86, "golden placement fault preserves PC/slot diagnostics")

    if cause in {
        instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
        instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT,
        instructions.ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
        instructions.ExceptionCause.CAPABILITY_LOCAL_STORE_FAULT,
    }:
        add("core.cap_mem.memory_tag_ops", 97, "capability or tag-memory fault maps to the integrated cap/mem fixture")
        add("fault_cases.invalid_tag_csetaddr", 88, "golden invalid-tag case is the closest fault comparison")
        add("memory_tag_ops.csc_clc_st48_ld48", 76, "golden memory/tag case checks normal capability-memory flow")

    if cause in {
        instructions.ExceptionCause.SYSCALL_TRAP,
        instructions.ExceptionCause.RETURN_STACK_UNDERFLOW,
        instructions.ExceptionCause.RETURN_STACK_OVERFLOW,
        instructions.ExceptionCause.RETURN_STACK_PERMISSION_FAULT,
    }:
        add("core.control_trap.sys_iret", 97, "trap or return-stack fault maps to the integrated control/trap fixture")
        add("traps.sys_to_tvc", 86, "golden trap-entry case isolates TVC entry")
        add("traps.sys_iret_return", 82, "golden IRET case checks trap-frame restoration")

    if cause == instructions.ExceptionCause.PAGE_FAULT:
        add("core.mmu_tlb.translation_sfence", 97, "page fault maps to the integrated MMU/TLB fixture")

    if cause == instructions.ExceptionCause.DIVIDE_BY_ZERO:
        add("fault_cases.divide_by_zero", 96, "divide-by-zero has a direct golden fault case")
        add("core.scalar.integer_ops_add_mul", 72, "scalar integrated fixture checks the same arithmetic/retire path")

    if fault_like and not candidates:
        add("core.fetch_decode.slot1_48bit_placement", 70, "unknown fault starts with the fast integrated fetch/decode case")
        add("core.scalar.integer_ops_add_mul", 60, "fallback fast integrated retire path")

    if not candidates:
        add("core.shell.reset_idle", 55, "fallback when capture has no fault or retire signature")
        add("core.scalar.integer_ops_add_mul", 50, "fallback fast integrated core replay")

    return tuple(sorted(candidates.values(), key=lambda candidate: (-candidate.score, candidate.case_id)))


def _candidate_for(case_id: str, score: int, sequence: int, rationale: str) -> ReplayCandidate:
    cases = {case.case_id: case for case in verilator_harness.regression_cases(verilator_harness.HarnessSuite.ALL)}
    case = cases[case_id]
    observed_trace = OBSERVED_TRACE_TEMPLATE.format(sequence=sequence)
    return ReplayCandidate(
        case_id=case.case_id,
        score=score,
        source=case.source,
        suite=case.suite.value,
        golden_trace_case_id=case.golden_trace_case_id,
        replay_command=f"python tools\\verilator_diff_harness.py --case-id {case.case_id}",
        compare_command=(
            f"python tools\\verilator_diff_harness.py --case-id {case.case_id} "
            f"--observed-trace {observed_trace}"
        ),
        rationale=rationale,
    )


def _dominant_cause(
    packet: fpga_debug_status.DebugStatusPacket,
) -> instructions.ExceptionCause | None:
    raw = packet.trap_cause or packet.fault_code
    if raw == 0:
        return None
    try:
        return instructions.ExceptionCause(raw)
    except ValueError:
        return None


def _flag_names(packet: fpga_debug_status.DebugStatusPacket) -> tuple[str, ...]:
    return tuple(
        flag.name
        for flag in fpga_debug_status.fpga_debug_status_profile().flags
        if packet.flags & (1 << flag.bit)
    )


def _pass_fail_state_name(packet: fpga_debug_status.DebugStatusPacket) -> str:
    states = fpga_debug_status.fpga_debug_status_profile().pass_fail_states
    return states.get(packet.pass_fail_state, f"unknown_{packet.pass_fail_state}")


def _diagnostics_for(
    packet: fpga_debug_status.DebugStatusPacket,
    flag_names: tuple[str, ...],
    pass_fail_state: str,
    candidates: tuple[ReplayCandidate, ...],
) -> tuple[str, ...]:
    lines = [
        f"decoded status packet sequence {packet.sequence} with state {pass_fail_state}",
        f"captured flags: {', '.join(flag_names) if flag_names else 'none'}",
    ]
    cause = _dominant_cause(packet)
    if cause is None:
        lines.append("no decoded fault cause; use candidates to reproduce pass, idle, or stalled behavior")
    else:
        lines.append(f"decoded fault cause {cause.name} (0x{int(cause):04X}) at pc_cell 0x{packet.pc_cell:X} slot {packet.slot}")
    if candidates:
        lines.append(f"start replay with {candidates[0].case_id}")
        if candidates[0].golden_trace_case_id:
            lines.append(
                "run the observed-trace command when a converted retire trace is available to preserve first-mismatch diagnostics"
            )
        else:
            lines.append("candidate has no golden trace; preserve assertion output and probe capture around the trigger")
    return tuple(lines)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

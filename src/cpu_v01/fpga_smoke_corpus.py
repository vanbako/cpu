"""FPGA smoke-program corpus and expected board signatures.

Owner stories:
- I26-S05: publish an FPGA smoke-program corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_bram_images, fpga_replay_mapper, verilator_harness


JsonValue = Any

FPGA_SMOKE_CORPUS_STORY = "I26-S05"
FPGA_SMOKE_CORPUS_DOC = Path("docs/implementation/fpga-smoke-program-corpus.md")
FPGA_SMOKE_CORPUS_TOOL = "python tools\\fpga_smoke_corpus.py --check"
REQUIRED_SMOKE_CATEGORIES = frozenset(
    {
        "reset_pass",
        "scalar_control",
        "capability_memory",
        "trap_syscall",
        "translation_fault",
        "failure_path",
    }
)


@dataclass(frozen=True)
class FpgaSmokeCorpusCase:
    case_id: str
    category: str
    source: str
    program_id: str
    source_case_id: str
    bram_image_status: str
    board_readiness: str
    replay_case_id: str
    expected_result: str
    expected_led_signature: str
    expected_uart_signature: str
    expected_probe_signature: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "source": self.source,
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "bram_image_status": self.bram_image_status,
            "board_readiness": self.board_readiness,
            "replay_case_id": self.replay_case_id,
            "expected_result": self.expected_result,
            "expected_led_signature": self.expected_led_signature,
            "expected_uart_signature": self.expected_uart_signature,
            "expected_probe_signature": self.expected_probe_signature,
        }


@dataclass(frozen=True)
class FpgaSmokeCorpusProfile:
    story: str
    bram_image_gate: str
    replay_gate: str
    required_categories: tuple[str, ...]
    cases: tuple[FpgaSmokeCorpusCase, ...]
    blockers: tuple[str, ...]

    def case_by_id(self, case_id: str) -> FpgaSmokeCorpusCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "bram_image_gate": self.bram_image_gate,
            "replay_gate": self.replay_gate,
            "required_categories": list(self.required_categories),
            "cases": [case.as_dict() for case in self.cases],
            "blockers": list(self.blockers),
        }


def fpga_smoke_corpus_profile() -> FpgaSmokeCorpusProfile:
    return FpgaSmokeCorpusProfile(
        story=FPGA_SMOKE_CORPUS_STORY,
        bram_image_gate=fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        replay_gate=fpga_replay_mapper.FPGA_REPLAY_MAPPER_TOOL,
        required_categories=tuple(sorted(REQUIRED_SMOKE_CATEGORIES)),
        cases=(
            FpgaSmokeCorpusCase(
                case_id="reset_pass.first_test_pause_stream",
                category="reset_pass",
                source="I23-S04 built-in PAUSE stream",
                program_id="builtin.first_test_pause_stream",
                source_case_id="reset_smoke.add_slot0",
                bram_image_status="built_in_first_test",
                board_readiness="ready_for_first_test",
                replay_case_id="core.scalar.integer_ops_add_mul",
                expected_result="pass",
                expected_led_signature="heartbeat_led_o toggles; pass_led_o asserts; fail_led_o stays deasserted",
                expected_uart_signature="pass flag set, retire_count >= 8, fault_code == 0",
                expected_probe_signature="debug_retire_sequence reaches the pass threshold with no sticky fault",
            ),
            FpgaSmokeCorpusCase(
                case_id="scalar_control.call_return",
                category="scalar_control",
                source="I17-S04 call/return binary fixture",
                program_id="call_return.direct_call_ret_fpga",
                source_case_id="call_return.direct_call_ret_binary",
                bram_image_status="image_ready",
                board_readiness="harness_required_for_pass",
                replay_case_id="core.scalar.integer_ops_add_mul",
                expected_result="pass_after_harness",
                expected_led_signature="heartbeat_led_o toggles; pass_led_o asserts only after bounded control-flow completion",
                expected_uart_signature="retire_count advances, pass/fail state remains running until harness completion",
                expected_probe_signature="PC leaves reset vector through CALL/RET fixture and no fault_code is sampled",
            ),
            FpgaSmokeCorpusCase(
                case_id="capability_memory.csc_clc_st48_ld48",
                category="capability_memory",
                source="I17-S04 capability memory binary fixture",
                program_id="capability_memory.csc_clc_st48_ld48_fpga",
                source_case_id="capability_memory.csc_clc_st48_ld48_binary",
                bram_image_status="image_ready",
                board_readiness="capability_register_harness_required",
                replay_case_id="core.cap_mem.memory_tag_ops",
                expected_result="pass_after_harness_or_capability_fault",
                expected_led_signature="pass_led_o asserts with register setup; fail_led_o asserts on tag, bounds, or permission fault",
                expected_uart_signature="fault_code distinguishes capability/tag-memory failure from scalar failure",
                expected_probe_signature="tag_ram starts clear, CSC writes a tag, ST48 clears the same slot tag",
            ),
            FpgaSmokeCorpusCase(
                case_id="trap_syscall.sys_pause_iret",
                category="trap_syscall",
                source="I17-S04 syscall/trap binary fixture",
                program_id="syscall_trap.sys_pause_iret_fpga",
                source_case_id="syscall_trap.sys_pause_iret_binary",
                bram_image_status="image_ready",
                board_readiness="trap_harness_required_for_pass",
                replay_case_id="core.control_trap.sys_iret",
                expected_result="trap_or_pass_after_harness",
                expected_led_signature="fail_led_o may assert before trap-aware harness completion",
                expected_uart_signature="trap_cause or fault_code reports syscall trap; PC/slot identify the trap site",
                expected_probe_signature="EPCC/TVC path is visible through replay and status packet progression",
            ),
            FpgaSmokeCorpusCase(
                case_id="translation_fault.mmu_tlb_page_fault",
                category="translation_fault",
                source="I22-S06 integrated MMU/TLB replay fixture",
                program_id="planned.translation_fault_mmu_tlb",
                source_case_id="core.mmu_tlb.translation_sfence",
                bram_image_status="replay_only_until_mmu_harness",
                board_readiness="requires_mmu_page_table_harness",
                replay_case_id="core.mmu_tlb.translation_sfence",
                expected_result="fault",
                expected_led_signature="fail_led_o asserts; pass_led_o stays deasserted",
                expected_uart_signature="fault_code reports page fault and pass/fail state is failed",
                expected_probe_signature="translation state, SATP/ASID, and SFENCE progress match replay case",
            ),
            FpgaSmokeCorpusCase(
                case_id="failure_path.divide_by_zero",
                category="failure_path",
                source="I20-S02 golden scalar fault fixture",
                program_id="planned.divide_by_zero_fault",
                source_case_id="fault_cases.divide_by_zero",
                bram_image_status="replay_only_until_fault_harness",
                board_readiness="requires_fault_injection_harness",
                replay_case_id="fault_cases.divide_by_zero",
                expected_result="fault",
                expected_led_signature="fail_led_o asserts; heartbeat_led_o proves clock/reset stayed alive",
                expected_uart_signature="fault_code reports divide-by-zero and first_mismatch is preserved by I25-S04",
                expected_probe_signature="no destination register write occurs after the precise scalar fault",
            ),
        ),
        blockers=(
            "I26-S04 loader remains blocked until I27-S02 exists",
            "translation and divide-by-zero board images need harness work before they are image_ready",
            "physical LED/UART/probe signatures remain evidence, not pass claims, until I24-S04/I24-S05 board runs exist",
        ),
    )


def fpga_smoke_corpus_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_smoke_corpus_profile().as_dict(), indent=indent, sort_keys=True)


def render_fpga_smoke_corpus() -> str:
    profile = fpga_smoke_corpus_profile()
    lines = [
        "# FPGA Smoke Program Corpus",
        "",
        f"Story: `{profile.story}`",
        f"BRAM image gate: `{profile.bram_image_gate}`",
        f"Replay gate: `{profile.replay_gate}`",
        "",
        "## Cases",
        "",
    ]
    for case in profile.cases:
        lines.extend(
            (
                f"### `{case.case_id}`",
                "",
                f"- Category: `{case.category}`.",
                f"- Program ID: `{case.program_id}`.",
                f"- BRAM status: `{case.bram_image_status}`.",
                f"- Replay: `{case.replay_case_id}`.",
                f"- LED: {case.expected_led_signature}.",
                f"- UART: {case.expected_uart_signature}.",
                f"- Probe: {case.expected_probe_signature}.",
                "",
            )
        )
    return "\n".join(lines)


def validate_fpga_smoke_corpus(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_smoke_corpus_profile()
    issues: list[str] = []

    if profile.story != FPGA_SMOKE_CORPUS_STORY:
        issues.append("FPGA smoke corpus story mismatch")
    issues.extend(fpga_bram_images.validate_fpga_bram_images(root))
    issues.extend(fpga_replay_mapper.validate_fpga_replay_mapper(root))

    case_ids = [case.case_id for case in profile.cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("FPGA smoke corpus case IDs are not unique")
    categories = {case.category for case in profile.cases}
    for category in sorted(REQUIRED_SMOKE_CATEGORIES - categories):
        issues.append(f"missing FPGA smoke category {category}")
    for category in sorted(categories - REQUIRED_SMOKE_CATEGORIES):
        issues.append(f"unknown FPGA smoke category {category}")

    image_ready_programs = {
        bundle.program_id for bundle in fpga_bram_images.fpga_bram_image_bundles()
    }
    replay_cases = {
        case.case_id
        for case in verilator_harness.regression_cases(verilator_harness.HarnessSuite.ALL)
    }
    for case in profile.cases:
        if case.bram_image_status == "image_ready" and case.program_id not in image_ready_programs:
            issues.append(f"{case.case_id}: image_ready program is not generated by I26-S02")
        if case.replay_case_id not in replay_cases:
            issues.append(f"{case.case_id}: replay case {case.replay_case_id!r} is not in the Verilator corpus")
        for field_name, value in (
            ("expected_led_signature", case.expected_led_signature),
            ("expected_uart_signature", case.expected_uart_signature),
            ("expected_probe_signature", case.expected_probe_signature),
        ):
            if not value:
                issues.append(f"{case.case_id}: missing {field_name}")
        if "led" not in case.expected_led_signature.lower():
            issues.append(f"{case.case_id}: LED signature must name LED observation")
        if not any(token in case.expected_uart_signature.lower() for token in ("fault", "pass", "retire", "trap")):
            issues.append(f"{case.case_id}: UART signature must name status packet content")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA smoke corpus is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_SMOKE_CORPUS_DOC)
    for token in (
        "Story: I26-S05",
        FPGA_SMOKE_CORPUS_TOOL,
        "python tools\\fpga_bram_images.py --check",
        "python tools\\fpga_replay_mapper.py --check",
        "reset_pass",
        "scalar_control",
        "capability_memory",
        "trap_syscall",
        "translation_fault",
        "failure_path",
        "expected LED",
        "expected UART",
        "expected probe",
        "call_return.direct_call_ret_fpga",
        "capability_memory.csc_clc_st48_ld48_fpga",
        "I26-S04",
        "I24-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SMOKE_CORPUS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

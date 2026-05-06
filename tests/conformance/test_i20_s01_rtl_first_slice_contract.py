"""I20-S01 conformance tests for the first RTL slice contract."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs" / "implementation" / "rtl-first-slice-contract.md"


def contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


class RtlFirstSliceContractTests(unittest.TestCase):
    def test_contract_artifact_identifies_story_and_required_sections(self) -> None:
        text = contract_text()

        self.assertIn("Story: I20-S01", text)
        for heading in (
            "## Slice Boundary",
            "## Pipeline Boundaries",
            "## Stall And Flush Rules",
            "## Commit Packet Timing",
            "## Memory And Tag Assumptions",
            "## Unsupported Feature Behavior",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

    def test_first_slice_inclusions_and_exclusions_are_named(self) -> None:
        text = contract_text()

        for included in (
            "`reset_smoke`",
            "`instruction_fetch`",
            "`slot_0_fetch`",
            "`legal_placement_fault`",
            "`integer_register_writes`",
            "`retire_trace`",
        ):
            with self.subTest(included=included):
                self.assertIn(included, text)

        for excluded in (
            "capability register behavior",
            "data-memory payload and tag writes",
            "traps, `IRET`, direct `CALL`, and protected return-stack transactions",
            "TLB, page-table, cache, and coherence behavior",
            "debug halt, interrupts, MMIO devices, DMA, and secondary cores",
        ):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, text)

    def test_pipeline_stage_boundaries_are_ordered_and_trace_visible(self) -> None:
        text = contract_text()
        ordered = ("FE0", "FE1", "PD", "XLT", "ISS", "EX", "MEM", "WB", "RT")

        self.assertIn("FE0 -> FE1 -> PD -> XLT -> ISS -> EX -> MEM -> WB -> RT", text)
        for stage in ordered:
            with self.subTest(stage=stage):
                self.assertIn(f"| `{stage}` |", text)

        self.assertIn("stage with `valid` asserted keeps its payload stable", text)
        self.assertIn("RT` retires in sequence order", text)
        self.assertIn("kills all younger", text)

    def test_retire_packet_timing_and_fields_are_fixed(self) -> None:
        text = contract_text()

        self.assertIn("same cycle that `RT` decides the outcome", text)
        self.assertIn("architectural state update occurs on that retire edge", text)
        for field in (
            "`valid`",
            "`sequence`",
            "`pc_cell`",
            "`slot`",
            "`instruction_length`",
            "`opcode_id`",
            "`normal_effects`",
            "`fault_packet`",
            "`redirect_packet`",
        ):
            with self.subTest(field=field):
                self.assertIn(field, text)
        self.assertIn("Exactly one of `normal_effects`, `fault_packet`, or `redirect_packet`", text)
        self.assertIn("Fault packets suppress all normal effects", text)

    def test_memory_tag_assumptions_and_unsupported_behavior_are_deterministic(self) -> None:
        text = contract_text()

        for phrase in (
            "A cell is 24 bits",
            "capability slot is four naturally aligned cells",
            "`CLC` and `CSC` transfer capability payload and tag together",
            "Integer stores that overlap a capability slot clear that slot's tag",
            "Unsupported opcode or instruction class",
            "precise illegal-instruction fault packet",
            "No fixture may depend on an indefinite stall",
            "bounded precise fault",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()

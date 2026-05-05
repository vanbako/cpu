"""I13-S02 conformance tests for pipeline/semantic result comparison."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, instructions, integer, memory_ops, pipeline, program, reset, state
from cpu_v01.memory import TaggedMemory


def executable_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0, 1 << 48),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def data_capability(cursor: int = 0x2000) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(0x2000, 0x3000),
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def integer_factory(memory: TaggedMemory | None):
    del memory
    return lambda core, instruction: integer.execute_integer(core, instruction)


class PipelineSemanticComparisonTests(unittest.TestCase):
    def test_straight_line_integer_pipeline_matches_semantic_execution(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(0, 2)
        core.write_d(1, 3)
        core.write_d(3, 4)
        decoded = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),
                (0x1001, state.SLOT_0, integer.integer_instruction("MUL", (4, 2, 3))),
            )
        )

        comparison = pipeline.compare_pipeline_to_semantic(
            core,
            decoded,
            integer_factory,
            steps=2,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[4], 20)
        self.assertEqual(comparison.pipeline_snapshot.csr_values, comparison.semantic_snapshot.csr_values)
        self.assertEqual(tuple(trace.sequence for trace in comparison.pipeline_traces), (0, 1))

    def test_load_store_pipeline_matches_semantic_memory_observations(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_c(0, data_capability())
        core.write_d(1, 0)
        core.write_d(2, 0x123456789ABC)
        memory = TaggedMemory()
        decoded = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, memory_ops.memory_instruction("ST48", (0, 1, 2))),
                (0x1001, state.SLOT_0, memory_ops.memory_instruction("LD48", (3, 0, 1))),
            )
        )

        def memory_factory(memory: TaggedMemory | None):
            assert memory is not None
            return lambda core, instruction: memory_ops.execute_memory(core, memory, instruction)

        comparison = pipeline.compare_pipeline_to_semantic(
            core,
            decoded,
            memory_factory,
            memory=memory,
            steps=2,
            observed_cells=(0x2000, 0x2001),
            observed_tag_slots=(0x2000,),
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[3], 0x123456789ABC)
        self.assertEqual(comparison.pipeline_snapshot.memory_cells, ((0x2000, 0x789ABC), (0x2001, 0x123456)))
        self.assertEqual(comparison.pipeline_snapshot.memory_tags, ((0x2000, False),))

    def test_branch_redirect_pipeline_matches_semantic_target_state(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        target = executable_capability(0x1800)
        decoded = program.DecodedProgram.from_layout(
            (
                (
                    0x1000,
                    state.SLOT_0,
                    instructions.DecodedInstruction("BRA", instructions.InstructionSize.BITS_24),
                ),
            )
        )

        def branch_factory(memory: TaggedMemory | None):
            del memory

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                del core
                return program.redirect_to_explicit_target(
                    instruction,
                    instructions.RedirectKind.BRANCH,
                    target,
                )

            return execute

        comparison = pipeline.compare_pipeline_to_semantic(
            core,
            decoded,
            branch_factory,
            steps=1,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.pcc.payload.cursor, 0x1800)
        self.assertEqual(comparison.semantic_snapshot.pcc.payload.cursor, 0x1800)
        self.assertTrue(comparison.pipeline_traces[0].result.is_redirect)

    def test_fault_and_trap_entry_pipeline_matches_semantic_execution(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], executable_capability(0x9000))
        decoded = program.DecodedProgram.from_layout(
            ((0x1000, state.SLOT_0, instructions.DecodedInstruction("SYS", instructions.InstructionSize.BITS_12)),)
        )

        def syscall_factory(memory: TaggedMemory | None):
            del memory

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                del core
                return instruction.fault(
                    instructions.FaultPacket(
                        instructions.ExceptionCause.SYSCALL_TRAP,
                        instruction.location,
                    )
                )

            return execute

        comparison = pipeline.compare_pipeline_to_semantic(
            core,
            decoded,
            syscall_factory,
            steps=1,
            enter_traps=True,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        cause_number = csrs.CSR_CAUSE
        self.assertIn((cause_number, int(instructions.ExceptionCause.SYSCALL_TRAP)), comparison.pipeline_snapshot.csr_values)
        self.assertEqual(comparison.pipeline_snapshot.pcc.payload.cursor, 0x9000)
        self.assertEqual(comparison.pipeline_snapshot.epcc.payload.cursor, 0x1000)
        self.assertTrue(comparison.pipeline_traces[0].trap_entry.entered)

    def test_comparison_reports_result_or_state_mismatch(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        decoded = program.DecodedProgram.from_layout(
            ((0x1000, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),)
        )

        calls = {"count": 0}

        def divergent_factory(memory: TaggedMemory | None):
            del memory

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                calls["count"] += 1
                if calls["count"] == 1:
                    core.write_d(0, 99)
                return integer.execute_integer(core, instruction)

            return execute

        comparison = pipeline.compare_pipeline_to_semantic(
            core,
            decoded,
            divergent_factory,
            steps=1,
        )

        self.assertFalse(comparison.matches)
        self.assertIn("mismatch", "; ".join(comparison.issues))

    def test_documentation_artifact_names_snapshot_comparison_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "pipeline-semantic-comparison.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I13-S02", text)
        self.assertIn("compares each step's result packet", text)
        self.assertIn("Snapshots include integer registers", text)


if __name__ == "__main__":
    unittest.main()

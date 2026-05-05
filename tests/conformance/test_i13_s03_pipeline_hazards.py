"""I13-S03 conformance tests for first hazard, MDU, and predictor cases."""

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


def slotted_target(cursor: int) -> state.SlottedCapability:
    return state.SlottedCapability.from_capability(executable_capability(cursor), state.SLOT_0)


def event_kinds(
    comparison: pipeline.HazardPipelineComparison,
) -> tuple[pipeline.PipelineHazardKind, ...]:
    return tuple(event.kind for event in comparison.hazard_events)


class PipelineHazardModelTests(unittest.TestCase):
    def test_load_use_interlock_stalls_dependent_integer_consumer(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_c(0, data_capability())
        core.write_d(1, 0)
        core.write_d(4, 1)
        memory = TaggedMemory()
        memory.st48(0x2000, 41)
        decoded = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, memory_ops.memory_instruction("LD48", (2, 0, 1))),
                (0x1001, state.SLOT_0, integer.integer_instruction("ADD", (3, 2, 4))),
            )
        )

        def executor_factory(memory: TaggedMemory | None):
            assert memory is not None

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                if instruction.mnemonic in memory_ops.MEMORY_MNEMONICS:
                    return memory_ops.execute_memory(core, memory, instruction)
                return integer.execute_integer(core, instruction)

            return execute

        comparison = pipeline.compare_hazard_pipeline_to_semantic(
            core,
            decoded,
            executor_factory,
            memory=memory,
            steps=2,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[3], 42)
        self.assertIn(pipeline.PipelineHazardKind.LOAD_USE_INTERLOCK, event_kinds(comparison))
        interlock = next(
            event
            for event in comparison.hazard_events
            if event.kind is pipeline.PipelineHazardKind.LOAD_USE_INTERLOCK
        )
        self.assertEqual(tuple(register.label for register in interlock.registers), ("D2",))

    def test_mdu_destination_busy_blocks_dependent_consumer_without_csr_path(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(0, 6)
        core.write_d(1, 7)
        core.write_d(4, 1)
        decoded = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, integer.integer_instruction("MUL", (2, 0, 1))),
                (0x1001, state.SLOT_0, integer.integer_instruction("ADD", (3, 2, 4))),
            )
        )

        def integer_factory(memory: TaggedMemory | None):
            del memory
            return lambda core, instruction: integer.execute_integer(core, instruction)

        comparison = pipeline.compare_hazard_pipeline_to_semantic(
            core,
            decoded,
            integer_factory,
            steps=2,
            timing=pipeline.PipelineTimingProfile(multiply_latency=3),
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[3], 43)
        self.assertIn(pipeline.PipelineHazardKind.MDU_ISSUE, event_kinds(comparison))
        self.assertIn(pipeline.PipelineHazardKind.SCOREBOARD_BUSY, event_kinds(comparison))
        self.assertFalse(
            any("MDU" in name for name in csrs.ASSIGNED_CSR_NUMBER_TO_NAME.values())
        )

    def test_taken_branch_predicted_not_taken_flushes_wrong_path(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(5, 10)
        core.write_d(6, 1)
        core.write_d(7, 30)
        core.write_d(8, 2)
        target = slotted_target(0x1010)
        decoded = program.DecodedProgram.from_layout(
            (
                (
                    0x1000,
                    state.SLOT_0,
                    instructions.DecodedInstruction(
                        "BCC",
                        instructions.InstructionSize.BITS_24,
                        operands=(0x1010,),
                    ),
                ),
                (0x1001, state.SLOT_0, integer.integer_instruction("ADD", (5, 5, 6))),
                (0x1010, state.SLOT_0, integer.integer_instruction("ADD", (7, 7, 8))),
            )
        )

        def executor_factory(memory: TaggedMemory | None):
            del memory

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                if instruction.mnemonic == "BCC":
                    return program.redirect_to_explicit_target(
                        instruction,
                        instructions.RedirectKind.BRANCH,
                        target,
                    )
                return integer.execute_integer(core, instruction)

            return execute

        comparison = pipeline.compare_hazard_pipeline_to_semantic(
            core,
            decoded,
            executor_factory,
            steps=2,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[5], 10)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[7], 32)
        self.assertIn(pipeline.PipelineHazardKind.BHT_PREDICT, event_kinds(comparison))
        self.assertIn(pipeline.PipelineHazardKind.BRANCH_FLUSH, event_kinds(comparison))
        self.assertIn(pipeline.PipelineHazardKind.WRONG_PATH_KILL, event_kinds(comparison))
        self.assertTrue(comparison.predictions[0].mispredicted)

    def test_return_stack_prediction_matches_call_ret_semantic_flow(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(3, 4)
        core.write_d(4, 5)
        target = slotted_target(0x1100)
        continuation = slotted_target(0x1001)
        decoded = program.DecodedProgram.from_layout(
            (
                (
                    0x1000,
                    state.SLOT_0,
                    instructions.DecodedInstruction(
                        "CALL",
                        instructions.InstructionSize.BITS_24,
                        operands=(0x1100,),
                    ),
                ),
                (0x1001, state.SLOT_0, integer.integer_instruction("ADD", (3, 3, 4))),
                (0x1100, state.SLOT_0, instructions.DecodedInstruction("RET", instructions.InstructionSize.BITS_12)),
            )
        )

        def executor_factory(memory: TaggedMemory | None):
            del memory

            def execute(core: state.CoreState, instruction: instructions.DecodedInstruction):
                if instruction.mnemonic == "CALL":
                    return instruction.normal_retire(
                        instructions.ArchitecturalEffects(pcc_update=target)
                    )
                if instruction.mnemonic == "RET":
                    return instruction.normal_retire(
                        instructions.ArchitecturalEffects(pcc_update=continuation)
                    )
                return integer.execute_integer(core, instruction)

            return execute

        comparison = pipeline.compare_hazard_pipeline_to_semantic(
            core,
            decoded,
            executor_factory,
            steps=3,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.integer_registers[3], 9)
        self.assertIn(pipeline.PipelineHazardKind.RAS_PUSH, event_kinds(comparison))
        self.assertIn(pipeline.PipelineHazardKind.RAS_PREDICT, event_kinds(comparison))
        self.assertIn(pipeline.PipelineHazardKind.RAS_CONSUME, event_kinds(comparison))
        ras_predictions = [
            prediction for prediction in comparison.predictions if prediction.source == "RAS"
        ]
        self.assertEqual(len(ras_predictions), 1)
        self.assertTrue(ras_predictions[0].used)
        self.assertFalse(ras_predictions[0].mispredicted)

    def test_privilege_context_change_flushes_predictor_state(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        user_sr = core.read_csr(csrs.CSR_SR) & ~(1 << csrs.SR_PRIV_BIT)
        core.write_csr_raw(csrs.CSR_SR, user_sr)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], executable_capability(0x9000))
        decoded = program.DecodedProgram.from_layout(
            ((0x1000, state.SLOT_0, instructions.DecodedInstruction("SYS", instructions.InstructionSize.BITS_12)),)
        )

        def executor_factory(memory: TaggedMemory | None):
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

        comparison = pipeline.compare_hazard_pipeline_to_semantic(
            core,
            decoded,
            executor_factory,
            steps=1,
            enter_traps=True,
        )

        self.assertTrue(comparison.matches, comparison.issues)
        self.assertEqual(comparison.pipeline_snapshot.pcc.payload.cursor, 0x9000)
        self.assertIn(
            pipeline.PipelineHazardKind.PREDICTOR_CONTEXT_FLUSH,
            event_kinds(comparison),
        )

    def test_documentation_artifact_names_hazard_and_predictor_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "pipeline-hazards-predictor.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I13-S03", text)
        self.assertIn("load-use interlocks", text)
        self.assertIn("return-address stack", text)


if __name__ == "__main__":
    unittest.main()

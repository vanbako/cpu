"""I13-S01 conformance tests for the single-issue pipeline trace model."""

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


def executable_capability(cursor: int, *, base: int = 0, top: int = 1 << 48) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def data_capability(cursor: int, *, base: int = 0x2000, top: int = 0x3000) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    )
    return caps.Capability.valid(payload)


def tvc_capability(cursor: int) -> caps.Capability:
    return executable_capability(cursor)


def integer_executor(core: state.CoreState, decoded: instructions.DecodedInstruction) -> instructions.ExecutionResult:
    return integer.execute_integer(core, decoded)


class PipelineTraceModelTests(unittest.TestCase):
    def test_pipeline_model_self_validation_passes(self) -> None:
        self.assertEqual(pipeline.validate_pipeline_trace_model(), ())
        self.assertEqual(
            tuple(stage.value for stage in pipeline.PIPELINE_STAGE_ORDER),
            ("FE0", "FE1", "PD", "XLT", "ISS", "EX", "MEM", "WB", "RT"),
        )

    def test_straight_line_integer_trace_commits_only_at_rt_in_order(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_d(0, 1)
        core.write_d(1, 2)
        core.write_d(3, 4)
        decoded = program.DecodedProgram.from_layout(
            (
                (0x1000, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),
                (0x1001, state.SLOT_0, integer.integer_instruction("ADD", (4, 2, 3))),
            )
        )
        model = pipeline.SingleIssuePipeline(decoded, integer_executor)

        first = model.step(core)
        second = model.step(core)

        self.assertEqual(first.sequence, 0)
        self.assertEqual(second.sequence, 1)
        self.assertEqual(first.stages, pipeline.PIPELINE_STAGE_ORDER)
        self.assertTrue(first.retired)
        self.assertEqual(core.read_d(2), 3)
        self.assertEqual(core.read_d(4), 7)
        self.assertEqual(core.pcc.payload.cursor, 0x1002)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 2)
        self.assertTrue(
            all(event.pending_result_kind is None for event in first.events[:5])
        )
        self.assertEqual(
            tuple(event.pending_result_kind for event in first.events[5:]),
            (instructions.ExecutionResultKind.NORMAL_RETIRE,) * 4,
        )

    def test_memory_instruction_result_is_detected_at_mem_and_committed_at_rt(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        memory = TaggedMemory()
        memory.st48(0x2000, 0x123456789ABC)
        core.write_c(0, data_capability(0x2000))
        core.write_d(1, 0)
        decoded = program.DecodedProgram.from_layout(
            ((0x1000, state.SLOT_0, memory_ops.memory_instruction("LD48", (2, 0, 1))),)
        )
        model = pipeline.SingleIssuePipeline(
            decoded,
            lambda core, instruction: memory_ops.execute_memory(core, memory, instruction),
            memory=memory,
        )

        trace = model.step(core)

        mem_index = pipeline.PIPELINE_STAGE_ORDER.index(instructions.PipelineStage.MEM)
        self.assertTrue(all(event.pending_result_kind is None for event in trace.events[:mem_index]))
        self.assertEqual(
            tuple(event.pending_result_kind for event in trace.events[mem_index:]),
            (instructions.ExecutionResultKind.NORMAL_RETIRE,) * 3,
        )
        self.assertEqual(core.read_d(2), 0x123456789ABC)
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 1)

    def test_branch_redirect_trace_installs_target_at_rt(self) -> None:
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

        def branch_executor(
            core: state.CoreState,
            decoded: instructions.DecodedInstruction,
        ) -> instructions.ExecutionResult:
            del core
            return program.redirect_to_explicit_target(
                decoded,
                instructions.RedirectKind.BRANCH,
                target,
            )

        trace = pipeline.SingleIssuePipeline(decoded, branch_executor).step(core)

        self.assertTrue(trace.result.is_redirect)
        self.assertEqual(core.pcc.payload.cursor, 0x1800)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(trace.events[-1].pending_result_kind, instructions.ExecutionResultKind.REDIRECT)

    def test_fault_trace_carries_syscall_to_rt_and_enters_trap_precisely(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], tvc_capability(0x9000))
        decoded = program.DecodedProgram.from_layout(
            ((0x1000, state.SLOT_0, instructions.DecodedInstruction("SYS", instructions.InstructionSize.BITS_12)),)
        )

        def syscall_executor(
            core: state.CoreState,
            decoded: instructions.DecodedInstruction,
        ) -> instructions.ExecutionResult:
            del core
            return decoded.fault(
                instructions.FaultPacket(
                    instructions.ExceptionCause.SYSCALL_TRAP,
                    decoded.location,
                )
            )

        trace = pipeline.SingleIssuePipeline(
            decoded,
            syscall_executor,
            enter_traps=True,
        ).step(core)

        self.assertTrue(trace.result.is_fault)
        self.assertTrue(trace.trap_entry.entered)
        self.assertEqual(core.epcc.payload.cursor, 0x1000)
        self.assertEqual(core.epcc.slot, state.SLOT_0)
        self.assertEqual(core.pcc.payload.cursor, 0x9000)
        self.assertEqual(core.read_csr(csrs.CSR_CAUSE), int(instructions.ExceptionCause.SYSCALL_TRAP))
        self.assertEqual(core.read_csr(csrs.CSR_INSTRET), 0)
        self.assertEqual(trace.events[-1].pending_result_kind, instructions.ExecutionResultKind.FAULT)

    def test_placement_fault_is_detected_at_pd_but_not_committed_before_rt(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.install_pcc(core.pcc.with_slot(state.SLOT_1))
        decoded = program.DecodedProgram.from_layout(
            (
                (
                    0x1000,
                    state.SLOT_1,
                    instructions.DecodedInstruction("BAD24", instructions.InstructionSize.BITS_24),
                ),
            )
        )
        model = pipeline.SingleIssuePipeline(decoded, integer_executor)

        trace = model.step(core)

        pd_index = pipeline.PIPELINE_STAGE_ORDER.index(instructions.PipelineStage.PD)
        self.assertTrue(trace.result.is_fault)
        self.assertEqual(trace.result.fault_packet.cause, instructions.ExceptionCause.ALIGN_FAULT)
        self.assertTrue(all(event.pending_result_kind is None for event in trace.events[:pd_index]))
        self.assertEqual(
            tuple(event.pending_result_kind for event in trace.events[pd_index:]),
            (instructions.ExecutionResultKind.FAULT,) * 7,
        )
        self.assertEqual(core.pcc.payload.cursor, 0x1000)
        self.assertEqual(core.pcc.slot, state.SLOT_1)

    def test_documentation_artifact_names_stage_order_and_retire_boundary(self) -> None:
        text = (ROOT / "docs" / "implementation" / "pipeline-trace.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I13-S01", text)
        self.assertIn("FE0 -> FE1 -> PD -> XLT -> ISS -> EX -> MEM -> WB -> RT", text)
        self.assertIn("Architectural state changes happen only", text)


if __name__ == "__main__":
    unittest.main()

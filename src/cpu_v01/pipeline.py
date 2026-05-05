"""Single-issue pipeline trace model for CPU v0.1.

Owner stories:
- E13-S01: pipeline stages and retire trace vocabulary.
- I13-S01: executable single-issue trace model.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass

from . import atomic_ops, cache_ops, call_ops, control_ops, csrs, memory_ops, program, return_ops, traps
from .execution import commit_normal_result
from .instructions import (
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    ExecutionResultKind,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
    PipelineStage,
)
from .memory import TaggedMemory
from .state import CoreState, SlottedCapability


PIPELINE_STAGE_ORDER = (
    PipelineStage.FE0,
    PipelineStage.FE1,
    PipelineStage.PD,
    PipelineStage.XLT,
    PipelineStage.ISS,
    PipelineStage.EX,
    PipelineStage.MEM,
    PipelineStage.WB,
    PipelineStage.RT,
)

MEMORY_RESULT_MNEMONICS = frozenset(
    memory_ops.MEMORY_MNEMONICS
    | atomic_ops.ATOMIC_MNEMONICS
    | cache_ops.CACHE_MNEMONICS
    | call_ops.CALL_MNEMONICS
    | return_ops.RET_MNEMONICS
)

InstructionExecutor = Callable[[CoreState, DecodedInstruction], ExecutionResult]
ExecutorFactory = Callable[[TaggedMemory | None], InstructionExecutor]


@dataclass(frozen=True)
class PipelineTraceEvent:
    sequence: int
    stage: PipelineStage
    address: int
    slot: int
    mnemonic: str
    pending_result_kind: ExecutionResultKind | None = None
    retired: bool = False

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a nonnegative int")
        object.__setattr__(self, "stage", PipelineStage(self.stage))
        object.__setattr__(self, "pending_result_kind", _result_kind_or_none(self.pending_result_kind))
        if type(self.retired) is not bool:
            raise TypeError("retired must be a bool")


@dataclass(frozen=True)
class PipelineStepTrace:
    sequence: int
    instruction: DecodedInstruction
    result: ExecutionResult
    events: tuple[PipelineTraceEvent, ...]
    trap_entry: traps.TrapEntryResult | None = None

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        return tuple(event.stage for event in self.events)

    @property
    def retired(self) -> bool:
        return self.events[-1].retired


@dataclass(frozen=True)
class ArchitecturalSnapshot:
    integer_registers: tuple[int, ...]
    general_capabilities: tuple[object, ...]
    pcc: SlottedCapability
    epcc: SlottedCapability
    csr_values: tuple[tuple[int, int], ...]
    memory_cells: tuple[tuple[int, int], ...] = ()
    memory_tags: tuple[tuple[int, bool], ...] = ()


@dataclass(frozen=True)
class PipelineSemanticComparison:
    pipeline_traces: tuple[PipelineStepTrace, ...]
    semantic_results: tuple[ExecutionResult, ...]
    pipeline_snapshot: ArchitecturalSnapshot
    semantic_snapshot: ArchitecturalSnapshot
    issues: tuple[str, ...]

    @property
    def matches(self) -> bool:
        return not self.issues


class SingleIssuePipeline:
    """Deterministic single-issue, in-order trace wrapper around decoded execution."""

    def __init__(
        self,
        decoded_program: program.DecodedProgram,
        executor: InstructionExecutor,
        *,
        memory: TaggedMemory | None = None,
        enter_traps: bool = False,
    ) -> None:
        if not isinstance(decoded_program, program.DecodedProgram):
            raise TypeError("decoded_program must be a DecodedProgram")
        if not callable(executor):
            raise TypeError("executor must be callable")
        if memory is not None and not isinstance(memory, TaggedMemory):
            raise TypeError("memory must be TaggedMemory or None")
        if type(enter_traps) is not bool:
            raise TypeError("enter_traps must be a bool")
        self.decoded_program = decoded_program
        self.executor = executor
        self.memory = memory
        self.enter_traps = enter_traps
        self._next_sequence = 0
        self._events: list[PipelineTraceEvent] = []

    @property
    def events(self) -> tuple[PipelineTraceEvent, ...]:
        return tuple(self._events)

    def step(self, core: CoreState, *, commit: bool = True) -> PipelineStepTrace:
        if not isinstance(core, CoreState):
            raise TypeError("core must be a CoreState")
        if type(commit) is not bool:
            raise TypeError("commit must be a bool")

        sequence = self._next_sequence
        self._next_sequence += 1

        instruction, result, result_stage = _prepare_result(
            core,
            self.decoded_program,
            self.executor,
        )
        trap_entry = _commit_at_retire(
            core,
            result,
            self.memory,
            commit=commit,
            enter_traps=self.enter_traps,
        )
        events = _trace_events(
            sequence,
            instruction,
            result,
            result_stage,
            retired=commit,
        )
        self._events.extend(events)
        return PipelineStepTrace(sequence, instruction, result, events, trap_entry)


def trace_single_step(
    core: CoreState,
    decoded_program: program.DecodedProgram,
    executor: InstructionExecutor,
    *,
    memory: TaggedMemory | None = None,
    commit: bool = True,
    enter_traps: bool = False,
) -> PipelineStepTrace:
    pipeline = SingleIssuePipeline(
        decoded_program,
        executor,
        memory=memory,
        enter_traps=enter_traps,
    )
    return pipeline.step(core, commit=commit)


def validate_pipeline_trace_model() -> tuple[str, ...]:
    issues: list[str] = []
    expected = ("FE0", "FE1", "PD", "XLT", "ISS", "EX", "MEM", "WB", "RT")
    if tuple(stage.value for stage in PIPELINE_STAGE_ORDER) != expected:
        issues.append("pipeline stage order does not match E13-S01")
    if PipelineStage.RT is not PIPELINE_STAGE_ORDER[-1]:
        issues.append("RT must be the final pipeline stage")
    if not MEMORY_RESULT_MNEMONICS >= memory_ops.MEMORY_MNEMONICS:
        issues.append("memory instructions must resolve in MEM")
    return tuple(issues)


def compare_pipeline_to_semantic(
    core: CoreState,
    decoded_program: program.DecodedProgram,
    executor_factory: ExecutorFactory,
    *,
    memory: TaggedMemory | None = None,
    steps: int,
    enter_traps: bool = False,
    observed_cells: tuple[int, ...] = (),
    observed_tag_slots: tuple[int, ...] = (),
) -> PipelineSemanticComparison:
    """Run pipeline and semantic execution on copied state and compare outcomes."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(decoded_program, program.DecodedProgram):
        raise TypeError("decoded_program must be a DecodedProgram")
    if not callable(executor_factory):
        raise TypeError("executor_factory must be callable")
    if memory is not None and not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be TaggedMemory or None")
    if type(steps) is not int or steps < 0:
        raise ValueError("steps must be a nonnegative int")

    pipeline_core = copy.deepcopy(core)
    semantic_core = copy.deepcopy(core)
    pipeline_memory = copy.deepcopy(memory) if memory is not None else None
    semantic_memory = copy.deepcopy(memory) if memory is not None else None

    pipeline_executor = executor_factory(pipeline_memory)
    semantic_executor = executor_factory(semantic_memory)
    trace_model = SingleIssuePipeline(
        decoded_program,
        pipeline_executor,
        memory=pipeline_memory,
        enter_traps=enter_traps,
    )

    pipeline_traces: list[PipelineStepTrace] = []
    semantic_results: list[ExecutionResult] = []
    issues: list[str] = []
    for step_index in range(steps):
        pipeline_trace = trace_model.step(pipeline_core)
        semantic_result = _semantic_step(
            semantic_core,
            decoded_program,
            semantic_executor,
            semantic_memory,
            enter_traps=enter_traps,
        )
        pipeline_traces.append(pipeline_trace)
        semantic_results.append(semantic_result)
        if pipeline_trace.result != semantic_result:
            issues.append(f"step {step_index} result packet mismatch")

    pipeline_snapshot = _snapshot(
        pipeline_core,
        pipeline_memory,
        observed_cells=observed_cells,
        observed_tag_slots=observed_tag_slots,
    )
    semantic_snapshot = _snapshot(
        semantic_core,
        semantic_memory,
        observed_cells=observed_cells,
        observed_tag_slots=observed_tag_slots,
    )
    if pipeline_snapshot != semantic_snapshot:
        issues.append("final architectural snapshot mismatch")

    return PipelineSemanticComparison(
        tuple(pipeline_traces),
        tuple(semantic_results),
        pipeline_snapshot,
        semantic_snapshot,
        tuple(issues),
    )


def _prepare_result(
    core: CoreState,
    decoded_program: program.DecodedProgram,
    executor: InstructionExecutor,
) -> tuple[DecodedInstruction, ExecutionResult, PipelineStage]:
    try:
        instruction = decoded_program.fetch(core)
    except KeyError:
        instruction = _missing_instruction(core)
        return (
            instruction,
            instruction.fault(
                FaultPacket(
                    ExceptionCause.ILLEGAL_INSTRUCTION,
                    InstructionLocation(core.pcc),
                    tval=core.pcc.payload.cursor,
                )
            ),
            PipelineStage.XLT,
        )

    placement_fault = instruction.placement_fault()
    if placement_fault is not None:
        return instruction, instruction.fault(placement_fault), PipelineStage.PD

    result = executor(core, instruction)
    if not isinstance(result, ExecutionResult):
        raise TypeError("executor must return an ExecutionResult")
    if result.is_normal_retire:
        result = program.with_sequential_fallthrough(result)
    return instruction, result, _result_detection_stage(instruction)


def _semantic_step(
    core: CoreState,
    decoded_program: program.DecodedProgram,
    executor: InstructionExecutor,
    memory: TaggedMemory | None,
    *,
    enter_traps: bool,
) -> ExecutionResult:
    result = program.step_decoded_program(
        core,
        decoded_program,
        executor,
        memory=memory,
        commit=False,
    )
    _commit_at_retire(core, result, memory, commit=True, enter_traps=enter_traps)
    return result


def _commit_at_retire(
    core: CoreState,
    result: ExecutionResult,
    memory: TaggedMemory | None,
    *,
    commit: bool,
    enter_traps: bool,
) -> traps.TrapEntryResult | None:
    if not commit:
        return None
    if result.is_normal_retire:
        commit_normal_result(core, result, memory)
        return None
    if result.is_redirect:
        assert result.redirect_packet is not None
        core.install_pcc(result.redirect_packet.target)
        return None
    if result.is_fault and enter_traps:
        return traps.enter_trap_from_result(core, result)
    return None


def _trace_events(
    sequence: int,
    instruction: DecodedInstruction,
    result: ExecutionResult,
    result_stage: PipelineStage,
    *,
    retired: bool,
) -> tuple[PipelineTraceEvent, ...]:
    location = instruction.location
    if location is None:
        raise ValueError("pipeline trace requires located instructions")
    result_index = PIPELINE_STAGE_ORDER.index(result_stage)
    events: list[PipelineTraceEvent] = []
    for index, stage in enumerate(PIPELINE_STAGE_ORDER):
        pending_kind = result.kind if index >= result_index else None
        events.append(
            PipelineTraceEvent(
                sequence,
                stage,
                location.address,
                location.slot,
                instruction.mnemonic,
                pending_kind,
                retired=retired and stage is PipelineStage.RT,
            )
        )
    return tuple(events)


def _result_detection_stage(instruction: DecodedInstruction) -> PipelineStage:
    if instruction.mnemonic in MEMORY_RESULT_MNEMONICS:
        return PipelineStage.MEM
    return PipelineStage.EX


def _missing_instruction(core: CoreState) -> DecodedInstruction:
    return DecodedInstruction(
        "ILLEGAL",
        InstructionSize.BITS_12,
        location=InstructionLocation(core.pcc),
    )


def _result_kind_or_none(value: ExecutionResultKind | None) -> ExecutionResultKind | None:
    if value is None:
        return None
    return ExecutionResultKind(value)


def _snapshot(
    core: CoreState,
    memory: TaggedMemory | None,
    *,
    observed_cells: tuple[int, ...],
    observed_tag_slots: tuple[int, ...],
) -> ArchitecturalSnapshot:
    memory_cells: tuple[tuple[int, int], ...] = ()
    memory_tags: tuple[tuple[int, bool], ...] = ()
    if memory is not None:
        memory_cells = tuple((address, memory.read_cell(address)) for address in observed_cells)
        memory_tags = tuple((slot, memory.capability_tag(slot)) for slot in observed_tag_slots)
    return ArchitecturalSnapshot(
        integer_registers=core.integer_registers.as_tuple(),
        general_capabilities=core.general_capabilities.as_tuple(),
        pcc=core.pcc,
        epcc=core.epcc,
        csr_values=tuple(
            (number, core.read_csr(number))
            for number in sorted(csrs.ASSIGNED_CSR_NUMBER_TO_NAME)
        ),
        memory_cells=memory_cells,
        memory_tags=memory_tags,
    )

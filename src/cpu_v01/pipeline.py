"""Single-issue pipeline trace model for CPU v0.1.

Owner stories:
- E13-S01: pipeline stages and retire trace vocabulary.
- I13-S01: executable single-issue trace model.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum

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
from .state import CoreState, SLOT_0, SlottedCapability


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

MDU_MNEMONICS = frozenset({"MUL", "MULU", "DIV", "DIVU", "MOD", "MODU"})
LOAD_RESULT_MNEMONICS = frozenset({"LD48", "LL48", "CLC"})
CONDITIONAL_BRANCH_MNEMONICS = frozenset({"BCC"})

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


@dataclass(frozen=True)
class RegisterRef:
    bank: str
    index: int

    def __post_init__(self) -> None:
        if self.bank not in {"D", "C"}:
            raise ValueError("bank must be 'D' or 'C'")
        if type(self.index) is not int or self.index < 0:
            raise ValueError("index must be a nonnegative int")

    @property
    def label(self) -> str:
        return f"{self.bank}{self.index}"


class PipelineHazardKind(Enum):
    LOAD_USE_INTERLOCK = "LOAD_USE_INTERLOCK"
    SCOREBOARD_BUSY = "SCOREBOARD_BUSY"
    MDU_ISSUE = "MDU_ISSUE"
    BHT_PREDICT = "BHT_PREDICT"
    RAS_PUSH = "RAS_PUSH"
    RAS_PREDICT = "RAS_PREDICT"
    RAS_CONSUME = "RAS_CONSUME"
    BRANCH_FLUSH = "BRANCH_FLUSH"
    RAS_MISPREDICT = "RAS_MISPREDICT"
    WRONG_PATH_KILL = "WRONG_PATH_KILL"
    PREDICTOR_CONTEXT_FLUSH = "PREDICTOR_CONTEXT_FLUSH"


@dataclass(frozen=True)
class PipelineHazardEvent:
    sequence: int
    cycle: int
    stage: PipelineStage
    kind: PipelineHazardKind
    instruction: str
    detail: str = ""
    registers: tuple[RegisterRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a nonnegative int")
        if type(self.cycle) is not int or self.cycle < 0:
            raise ValueError("cycle must be a nonnegative int")
        object.__setattr__(self, "stage", PipelineStage(self.stage))
        object.__setattr__(self, "kind", PipelineHazardKind(self.kind))
        if not isinstance(self.instruction, str) or not self.instruction:
            raise ValueError("instruction must be a nonempty str")
        if not isinstance(self.detail, str):
            raise TypeError("detail must be a str")
        object.__setattr__(self, "registers", tuple(self.registers))


@dataclass(frozen=True)
class PipelineTimingProfile:
    load_use_interlock_cycles: int = 1
    multiply_latency: int = 3
    divide_latency: int = 8
    bht_entries: int = 16
    ras_entries: int = 4

    def __post_init__(self) -> None:
        for name in (
            "load_use_interlock_cycles",
            "multiply_latency",
            "divide_latency",
            "bht_entries",
            "ras_entries",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive int")
        if self.bht_entries & (self.bht_entries - 1):
            raise ValueError("bht_entries must be a power of two")
        if self.bht_entries < 16:
            raise ValueError("bht_entries must be at least 16")
        if self.ras_entries < 4:
            raise ValueError("ras_entries must be at least 4")

    def mdu_latency(self, mnemonic: str) -> int:
        mnemonic = mnemonic.upper()
        if mnemonic in {"MUL", "MULU"}:
            return self.multiply_latency
        if mnemonic in {"DIV", "DIVU", "MOD", "MODU"}:
            return self.divide_latency
        raise ValueError(f"{mnemonic} is not an MDU instruction")


@dataclass(frozen=True)
class PredictorContext:
    privilege: int
    satp_mode: int
    asid: int

    @classmethod
    def from_core(cls, core: CoreState) -> "PredictorContext":
        sr = core.read_csr(csrs.CSR_SR)
        satp = core.read_csr(csrs.CSR_SATP)
        return cls(
            privilege=1 if sr & (1 << csrs.SR_PRIV_BIT) else 0,
            satp_mode=csrs.satp_mode(satp),
            asid=csrs.satp_asid(satp),
        )


@dataclass(frozen=True)
class PipelinePrediction:
    sequence: int
    source: str
    used: bool
    predicted: SlottedCapability | None
    resolved: SlottedCapability | None
    mispredicted: bool

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a nonnegative int")
        if self.source not in {"BHT", "RAS"}:
            raise ValueError("source must be BHT or RAS")
        if type(self.used) is not bool:
            raise TypeError("used must be a bool")
        if self.predicted is not None and not isinstance(self.predicted, SlottedCapability):
            raise TypeError("predicted must be SlottedCapability or None")
        if self.resolved is not None and not isinstance(self.resolved, SlottedCapability):
            raise TypeError("resolved must be SlottedCapability or None")
        if type(self.mispredicted) is not bool:
            raise TypeError("mispredicted must be a bool")


@dataclass(frozen=True)
class HazardPipelineComparison:
    pipeline_traces: tuple[PipelineStepTrace, ...]
    semantic_results: tuple[ExecutionResult, ...]
    pipeline_snapshot: ArchitecturalSnapshot
    semantic_snapshot: ArchitecturalSnapshot
    hazard_events: tuple[PipelineHazardEvent, ...]
    predictions: tuple[PipelinePrediction, ...]
    issues: tuple[str, ...]

    @property
    def matches(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class _BusyDestination:
    destination: RegisterRef
    sequence: int
    mnemonic: str
    remaining_interlocks: int
    kind: PipelineHazardKind


@dataclass(frozen=True)
class _PredictionChoice:
    source: str
    target: SlottedCapability | None
    used: bool


@dataclass(frozen=True)
class _RasEntry:
    target: SlottedCapability
    context: PredictorContext


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


class ConservativeBranchPredictor:
    """E13-S04 MVP predictor model: BHT for `BCC`, RAS for `CALL`/`RET`."""

    def __init__(
        self,
        *,
        bht_entries: int = 16,
        ras_entries: int = 4,
    ) -> None:
        profile = PipelineTimingProfile(bht_entries=bht_entries, ras_entries=ras_entries)
        self._bht = [1] * profile.bht_entries
        self._ras_entries = profile.ras_entries
        self._ras: list[_RasEntry] = []
        self._context: PredictorContext | None = None

    @property
    def bht_counters(self) -> tuple[int, ...]:
        return tuple(self._bht)

    @property
    def ras_depth(self) -> int:
        return len(self._ras)

    def predict(self, instruction: DecodedInstruction, core: CoreState) -> _PredictionChoice | None:
        if not isinstance(instruction, DecodedInstruction):
            raise TypeError("instruction must be a DecodedInstruction")
        if not isinstance(core, CoreState):
            raise TypeError("core must be a CoreState")
        context = PredictorContext.from_core(core)
        if self._context is None:
            self._context = context

        if instruction.mnemonic in CONDITIONAL_BRANCH_MNEMONICS:
            if instruction.location is None:
                return None
            index = self._bht_index(instruction)
            target = _direct_branch_target(instruction, core)
            if target is None:
                return None
            if self._bht[index] >= 2:
                return _PredictionChoice("BHT", target, True)
            return _PredictionChoice("BHT", _sequential_location(instruction), True)

        if instruction.mnemonic in return_ops.RET_MNEMONICS:
            for entry in reversed(self._ras):
                if entry.context == context:
                    return _PredictionChoice("RAS", entry.target, True)
            return _PredictionChoice("RAS", None, False)

        return None

    def record_retire(
        self,
        result: ExecutionResult,
        context: PredictorContext,
    ) -> None:
        if not isinstance(result, ExecutionResult):
            raise TypeError("result must be an ExecutionResult")
        if not isinstance(context, PredictorContext):
            raise TypeError("context must be a PredictorContext")
        instruction = result.instruction

        if instruction.mnemonic in CONDITIONAL_BRANCH_MNEMONICS:
            self._record_bht_retire(result)
        if instruction.mnemonic in call_ops.CALL_MNEMONICS and result.is_normal_retire:
            target = _call_continuation_location(instruction)
            self._ras.append(_RasEntry(target, context))
            if len(self._ras) > self._ras_entries:
                self._ras.pop(0)
        if instruction.mnemonic in return_ops.RET_MNEMONICS and result.is_normal_retire:
            for index in range(len(self._ras) - 1, -1, -1):
                if self._ras[index].context == context:
                    del self._ras[index]
                    break

    def flush(self, context: PredictorContext) -> None:
        if not isinstance(context, PredictorContext):
            raise TypeError("context must be a PredictorContext")
        self._bht = [1] * len(self._bht)
        self._ras.clear()
        self._context = context

    def _record_bht_retire(self, result: ExecutionResult) -> None:
        instruction = result.instruction
        if instruction.location is None or result.is_fault or result.is_debug_event:
            return
        index = self._bht_index(instruction)
        taken = result.is_redirect
        if taken:
            self._bht[index] = min(3, self._bht[index] + 1)
        else:
            self._bht[index] = max(0, self._bht[index] - 1)

    def _bht_index(self, instruction: DecodedInstruction) -> int:
        assert instruction.location is not None
        address = instruction.location.address
        slot = instruction.location.slot
        return ((address << 1) ^ slot) & (len(self._bht) - 1)


class HazardAwarePipeline(SingleIssuePipeline):
    """Single-issue trace model with first hazard, MDU, and predictor annotations."""

    def __init__(
        self,
        decoded_program: program.DecodedProgram,
        executor: InstructionExecutor,
        *,
        memory: TaggedMemory | None = None,
        enter_traps: bool = False,
        timing: PipelineTimingProfile | None = None,
        predictor: ConservativeBranchPredictor | None = None,
    ) -> None:
        super().__init__(
            decoded_program,
            executor,
            memory=memory,
            enter_traps=enter_traps,
        )
        self.timing = timing if timing is not None else PipelineTimingProfile()
        if not isinstance(self.timing, PipelineTimingProfile):
            raise TypeError("timing must be a PipelineTimingProfile")
        self.predictor = (
            predictor
            if predictor is not None
            else ConservativeBranchPredictor(
                bht_entries=self.timing.bht_entries,
                ras_entries=self.timing.ras_entries,
            )
        )
        if not isinstance(self.predictor, ConservativeBranchPredictor):
            raise TypeError("predictor must be a ConservativeBranchPredictor")
        self._cycle = 0
        self._hazard_events: list[PipelineHazardEvent] = []
        self._predictions: list[PipelinePrediction] = []
        self._busy_destinations: list[_BusyDestination] = []

    @property
    def hazard_events(self) -> tuple[PipelineHazardEvent, ...]:
        return tuple(self._hazard_events)

    @property
    def predictions(self) -> tuple[PipelinePrediction, ...]:
        return tuple(self._predictions)

    def step(self, core: CoreState, *, commit: bool = True) -> PipelineStepTrace:
        if not isinstance(core, CoreState):
            raise TypeError("core must be a CoreState")
        sequence = self._next_sequence
        context_before = PredictorContext.from_core(core)
        instruction = _peek_instruction(self.decoded_program, core)

        consumed, stall_cycles = self._record_source_interlocks(sequence, instruction)
        choice = self.predictor.predict(instruction, core)
        self._record_prediction_event(sequence, instruction, choice)

        trace = super().step(core, commit=commit)
        resolved = _resolved_location(trace.result)
        self._record_prediction_resolution(sequence, trace, choice, resolved)
        self._record_predictor_retire_events(sequence, trace)
        self.predictor.record_retire(trace.result, context_before)

        context_after = PredictorContext.from_core(core)
        if commit and context_after != context_before:
            self.predictor.flush(context_after)
            self._append_event(
                sequence,
                PipelineStage.RT,
                PipelineHazardKind.PREDICTOR_CONTEXT_FLUSH,
                trace.instruction,
                "predictor state flushed after privilege, SATP, or ASID context change",
            )

        self._age_busy_destinations(consumed)
        self._record_result_busy_destination(trace)
        self._cycle += len(PIPELINE_STAGE_ORDER) + stall_cycles
        return trace

    def _record_source_interlocks(
        self,
        sequence: int,
        instruction: DecodedInstruction,
    ) -> tuple[tuple[_BusyDestination, ...], int]:
        sources = set(_source_registers(instruction))
        consumed: list[_BusyDestination] = []
        stall_cycles = 0
        for busy in self._busy_destinations:
            if busy.destination not in sources or busy.remaining_interlocks <= 0:
                continue
            consumed.append(busy)
            stall_cycles = max(stall_cycles, busy.remaining_interlocks)
            detail = f"{busy.destination.label} waits for sequence {busy.sequence} {busy.mnemonic}"
            self._append_event(
                sequence,
                PipelineStage.ISS,
                busy.kind,
                instruction,
                detail,
                registers=(busy.destination,),
            )
        return tuple(consumed), stall_cycles

    def _record_prediction_event(
        self,
        sequence: int,
        instruction: DecodedInstruction,
        choice: _PredictionChoice | None,
    ) -> None:
        if choice is None or not choice.used:
            return
        if choice.source == "BHT":
            kind = PipelineHazardKind.BHT_PREDICT
        elif choice.source == "RAS":
            kind = PipelineHazardKind.RAS_PREDICT
        else:
            raise AssertionError(f"unknown prediction source {choice.source}")
        self._append_event(
            sequence,
            PipelineStage.FE0,
            kind,
            instruction,
            _location_detail("predicted", choice.target),
        )

    def _record_prediction_resolution(
        self,
        sequence: int,
        trace: PipelineStepTrace,
        choice: _PredictionChoice | None,
        resolved: SlottedCapability | None,
    ) -> None:
        if choice is None:
            return
        mispredicted = _prediction_missed(choice, trace.result, resolved)
        self._predictions.append(
            PipelinePrediction(
                sequence,
                choice.source,
                choice.used,
                choice.target,
                resolved,
                mispredicted,
            )
        )
        if not mispredicted:
            return
        kind = (
            PipelineHazardKind.RAS_MISPREDICT
            if choice.source == "RAS"
            else PipelineHazardKind.BRANCH_FLUSH
        )
        self._append_event(
            sequence,
            PipelineStage.RT,
            kind,
            trace.instruction,
            _location_detail("resolved", resolved),
        )
        self._append_event(
            sequence,
            PipelineStage.RT,
            PipelineHazardKind.WRONG_PATH_KILL,
            trace.instruction,
            "younger wrong-path work killed before architectural update",
        )

    def _record_predictor_retire_events(
        self,
        sequence: int,
        trace: PipelineStepTrace,
    ) -> None:
        instruction = trace.instruction
        if instruction.mnemonic in call_ops.CALL_MNEMONICS and trace.result.is_normal_retire:
            self._append_event(
                sequence,
                PipelineStage.RT,
                PipelineHazardKind.RAS_PUSH,
                instruction,
                _location_detail("push", _call_continuation_location(instruction)),
            )
        if instruction.mnemonic in return_ops.RET_MNEMONICS and trace.result.is_normal_retire:
            self._append_event(
                sequence,
                PipelineStage.RT,
                PipelineHazardKind.RAS_CONSUME,
                instruction,
                "consume the top same-context return prediction entry",
            )

    def _age_busy_destinations(
        self,
        consumed: tuple[_BusyDestination, ...],
    ) -> None:
        consumed_set = set(consumed)
        aged: list[_BusyDestination] = []
        for busy in self._busy_destinations:
            if busy in consumed_set:
                continue
            remaining = busy.remaining_interlocks - 1
            if remaining > 0:
                aged.append(replace(busy, remaining_interlocks=remaining))
        self._busy_destinations = aged

    def _record_result_busy_destination(self, trace: PipelineStepTrace) -> None:
        result = trace.result
        if not result.is_normal_retire:
            return
        destinations = _destination_registers(result)
        if not destinations:
            return
        mnemonic = result.instruction.mnemonic
        if mnemonic in LOAD_RESULT_MNEMONICS:
            for destination in destinations:
                self._busy_destinations.append(
                    _BusyDestination(
                        destination,
                        trace.sequence,
                        mnemonic,
                        self.timing.load_use_interlock_cycles,
                        PipelineHazardKind.LOAD_USE_INTERLOCK,
                    )
                )
        elif mnemonic in MDU_MNEMONICS:
            interlocks = max(1, self.timing.mdu_latency(mnemonic) - 1)
            for destination in destinations:
                self._busy_destinations.append(
                    _BusyDestination(
                        destination,
                        trace.sequence,
                        mnemonic,
                        interlocks,
                        PipelineHazardKind.SCOREBOARD_BUSY,
                    )
                )
            self._append_event(
                trace.sequence,
                PipelineStage.ISS,
                PipelineHazardKind.MDU_ISSUE,
                result.instruction,
                "MDU destination marked busy until normal writeback/retire",
                registers=destinations,
            )

    def _append_event(
        self,
        sequence: int,
        stage: PipelineStage,
        kind: PipelineHazardKind,
        instruction: DecodedInstruction,
        detail: str = "",
        *,
        registers: tuple[RegisterRef, ...] = (),
    ) -> None:
        self._hazard_events.append(
            PipelineHazardEvent(
                sequence,
                self._cycle + PIPELINE_STAGE_ORDER.index(stage),
                stage,
                kind,
                instruction.mnemonic,
                detail,
                registers,
            )
        )


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


def compare_hazard_pipeline_to_semantic(
    core: CoreState,
    decoded_program: program.DecodedProgram,
    executor_factory: ExecutorFactory,
    *,
    memory: TaggedMemory | None = None,
    steps: int,
    enter_traps: bool = False,
    observed_cells: tuple[int, ...] = (),
    observed_tag_slots: tuple[int, ...] = (),
    timing: PipelineTimingProfile | None = None,
    predictor: ConservativeBranchPredictor | None = None,
) -> HazardPipelineComparison:
    """Compare hazard-annotated pipeline execution with semantic execution."""
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
    trace_model = HazardAwarePipeline(
        decoded_program,
        pipeline_executor,
        memory=pipeline_memory,
        enter_traps=enter_traps,
        timing=timing,
        predictor=predictor,
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

    return HazardPipelineComparison(
        tuple(pipeline_traces),
        tuple(semantic_results),
        pipeline_snapshot,
        semantic_snapshot,
        trace_model.hazard_events,
        trace_model.predictions,
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


def _peek_instruction(
    decoded_program: program.DecodedProgram,
    core: CoreState,
) -> DecodedInstruction:
    try:
        return decoded_program.fetch(core)
    except KeyError:
        return _missing_instruction(core)


def _source_registers(instruction: DecodedInstruction) -> tuple[RegisterRef, ...]:
    operands = instruction.operands
    mnemonic = instruction.mnemonic
    sources: list[RegisterRef] = []

    def add_d(index: object) -> None:
        if type(index) is int:
            sources.append(RegisterRef("D", index))

    def add_c(index: object) -> None:
        if type(index) is int:
            sources.append(RegisterRef("C", index))

    if mnemonic in {"CPY", "NEG", "NOT"} and len(operands) >= 2:
        add_d(operands[1])
    elif mnemonic in {
        "ADD",
        "ADDU",
        "SUB",
        "SUBU",
        "MUL",
        "MULU",
        "DIV",
        "DIVU",
        "MOD",
        "MODU",
        "AND",
        "OR",
        "XOR",
        "SHL",
        "SHRS",
        "SHRU",
        "ROL",
        "ROR",
        "BSET",
        "BCLR",
    } and len(operands) >= 3:
        add_d(operands[1])
        add_d(operands[2])
    elif mnemonic in {"CMP", "CMPU", "TST"} and len(operands) >= 2:
        add_d(operands[0])
        add_d(operands[1])
    elif mnemonic == "CMOVCC" and len(operands) >= 2:
        add_d(operands[1])
    elif mnemonic in {"LD48", "CLC"} and len(operands) >= 3:
        add_c(operands[1])
        add_d(operands[2])
    elif mnemonic == "ST48" and len(operands) >= 3:
        add_c(operands[0])
        add_d(operands[1])
        add_d(operands[2])
    elif mnemonic == "CSC" and len(operands) >= 3:
        add_c(operands[0])
        add_d(operands[1])
        add_c(operands[2])
    elif mnemonic == "CALLC" and operands:
        add_c(operands[0])

    return tuple(dict.fromkeys(sources))


def _destination_registers(result: ExecutionResult) -> tuple[RegisterRef, ...]:
    if not result.is_normal_retire:
        return ()
    assert result.normal is not None
    effects = result.normal.effects
    destinations = [
        *(RegisterRef("D", index) for index, _ in effects.integer_writes),
        *(RegisterRef("C", index) for index, _ in effects.capability_writes),
    ]
    return tuple(dict.fromkeys(destinations))


def _direct_branch_target(
    instruction: DecodedInstruction,
    core: CoreState,
) -> SlottedCapability | None:
    raw_target = instruction.attributes.get("target")
    if raw_target is None and instruction.operands:
        raw_target = instruction.operands[0]
    if raw_target is None:
        return None
    if isinstance(raw_target, SlottedCapability):
        if raw_target.slot != SLOT_0:
            return None
        return SlottedCapability.from_capability(raw_target.capability, SLOT_0)
    if type(raw_target) is int:
        return SlottedCapability.from_capability(
            core.pcc.without_slot().with_cursor(raw_target),
            SLOT_0,
        )
    return None


def _sequential_location(instruction: DecodedInstruction) -> SlottedCapability:
    if instruction.location is None:
        raise ValueError("prediction requires a located instruction")
    return program.sequential_pcc(instruction.location.pcc, instruction.size)


def _call_continuation_location(instruction: DecodedInstruction) -> SlottedCapability:
    if instruction.location is None:
        raise ValueError("CALL prediction requires a located instruction")
    increment = 2 if instruction.size is InstructionSize.BITS_48 else 1
    return SlottedCapability.from_capability(
        instruction.location.pcc.without_slot().with_cursor(
            instruction.location.address + increment
        ),
        SLOT_0,
    )


def _resolved_location(result: ExecutionResult) -> SlottedCapability | None:
    if result.is_redirect:
        assert result.redirect_packet is not None
        return result.redirect_packet.target
    if result.is_normal_retire:
        assert result.normal is not None
        return result.normal.effects.pcc_update
    return None


def _prediction_missed(
    choice: _PredictionChoice,
    result: ExecutionResult,
    resolved: SlottedCapability | None,
) -> bool:
    if not choice.used:
        return False
    if result.is_fault or result.is_debug_event:
        return True
    if choice.target is None or resolved is None:
        return choice.target is not resolved
    return not _same_location(choice.target, resolved)


def _same_location(left: SlottedCapability, right: SlottedCapability) -> bool:
    return left.payload.cursor == right.payload.cursor and left.slot == right.slot


def _location_detail(prefix: str, target: SlottedCapability | None) -> str:
    if target is None:
        return f"{prefix}: none"
    return f"{prefix}: {target.payload.cursor:#x}, slot {target.slot}"


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

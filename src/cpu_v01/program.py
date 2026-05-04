"""Decoded-program fetch and hidden-slot sequencing helpers for CPU v0.1.

Owner stories:
- E01-S05: hidden slot behavior for PCC and EPCC.
- E04-S01: instruction-size and fetch-group placement rules.
- I04-S01: decoded-program fetch placement and sequential PCC updates.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from types import MappingProxyType

from .capabilities import Capability
from .cells import require_cell_address
from .execution import commit_normal_result
from .instructions import (
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
    RedirectKind,
    RedirectPacket,
)
from .memory import TaggedMemory
from .state import CoreState, SLOT_0, SLOT_1, SlottedCapability, require_slot


ProgramKey = tuple[int, int]
InstructionExecutor = Callable[[CoreState, DecodedInstruction], ExecutionResult]


class DecodedProgram:
    """A hand-authored decoded program indexed by architectural cell and slot."""

    def __init__(self, entries: Mapping[ProgramKey, DecodedInstruction]) -> None:
        checked: dict[ProgramKey, DecodedInstruction] = {}
        for key, instruction in entries.items():
            address, slot = _program_key(key)
            if not isinstance(instruction, DecodedInstruction):
                raise TypeError("program entries must be DecodedInstruction values")
            if (address, slot) in checked:
                raise ValueError(f"duplicate decoded instruction at {(address, slot)!r}")
            checked[(address, slot)] = instruction
        self._entries = MappingProxyType(checked)

    @classmethod
    def from_layout(
        cls,
        entries: Iterable[tuple[int, int, DecodedInstruction]],
    ) -> "DecodedProgram":
        """Build a program from `(cell_address, slot, instruction_template)` rows."""
        layout: dict[ProgramKey, DecodedInstruction] = {}
        for address, slot, instruction in entries:
            key = _program_key((address, slot))
            if key in layout:
                raise ValueError(f"duplicate decoded instruction at {key!r}")
            if not isinstance(instruction, DecodedInstruction):
                raise TypeError("instruction template must be a DecodedInstruction")
            layout[key] = instruction
        return cls(layout)

    @classmethod
    def from_located(
        cls,
        instructions: Iterable[DecodedInstruction],
    ) -> "DecodedProgram":
        """Build a program from instructions that already carry locations."""
        layout: dict[ProgramKey, DecodedInstruction] = {}
        for instruction in instructions:
            if not isinstance(instruction, DecodedInstruction):
                raise TypeError("program entries must be DecodedInstruction values")
            if instruction.location is None:
                raise ValueError("located program entries require instruction.location")
            key = (instruction.location.address, instruction.location.slot)
            if key in layout:
                raise ValueError(f"duplicate decoded instruction at {key!r}")
            layout[key] = instruction
        return cls(layout)

    def __len__(self) -> int:
        return len(self._entries)

    def contains_location(self, address: int, slot: int) -> bool:
        return _program_key((address, slot)) in self._entries

    def fetch(self, core: CoreState) -> DecodedInstruction:
        """Fetch the decoded instruction at the current `PCC` cell and slot."""
        if not isinstance(core, CoreState):
            raise TypeError("core must be a CoreState")
        location = InstructionLocation(core.pcc)
        try:
            template = self._entries[(location.address, location.slot)]
        except KeyError as exc:
            raise KeyError(
                f"no decoded instruction at cell {location.address:#x}, "
                f"slot {location.slot}"
            ) from exc
        return _with_location(template, location)

    def step(
        self,
        core: CoreState,
        executor: InstructionExecutor,
        *,
        memory: TaggedMemory | None = None,
        commit: bool = True,
    ) -> ExecutionResult:
        """Fetch, execute, add fall-through for normal retire, and optionally commit."""
        result = step_decoded_program(
            core,
            self,
            executor,
            memory=memory,
            commit=commit,
        )
        return result


def step_decoded_program(
    core: CoreState,
    program: DecodedProgram,
    executor: InstructionExecutor,
    *,
    memory: TaggedMemory | None = None,
    commit: bool = True,
) -> ExecutionResult:
    """Run one decoded-program instruction from the current `PCC`."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(program, DecodedProgram):
        raise TypeError("program must be a DecodedProgram")
    if not callable(executor):
        raise TypeError("executor must be callable")

    try:
        instruction = program.fetch(core)
    except KeyError:
        result = _missing_instruction_fault(core)
    else:
        placement_fault = instruction.placement_fault()
        if placement_fault is not None:
            result = instruction.fault(placement_fault)
        else:
            result = executor(core, instruction)
            if not isinstance(result, ExecutionResult):
                raise TypeError("executor must return an ExecutionResult")
            result = with_sequential_fallthrough(result)

    if commit and result.is_normal_retire:
        commit_normal_result(core, result, memory)
    return result


def with_sequential_fallthrough(result: ExecutionResult) -> ExecutionResult:
    """Attach the architectural fall-through `PCC` update to normal retire."""
    if not isinstance(result, ExecutionResult):
        raise TypeError("result must be an ExecutionResult")
    if not result.is_normal_retire:
        return result
    assert result.normal is not None
    effects = result.normal.effects
    if effects.pcc_update is not None:
        return result

    instruction = result.instruction
    if instruction.location is None:
        raise ValueError("normal fall-through requires an instruction location")
    placement_fault = instruction.placement_fault()
    if placement_fault is not None:
        return instruction.fault(placement_fault)

    effects_with_pcc = replace(
        effects,
        pcc_update=sequential_pcc(instruction.location.pcc, instruction.size),
    )
    return ExecutionResult.normal_retire(instruction, effects_with_pcc)


def sequential_pcc(
    current: SlottedCapability,
    size: InstructionSize,
) -> SlottedCapability:
    """Return the fall-through `PCC` for a legally placed instruction."""
    if not isinstance(current, SlottedCapability):
        raise TypeError("current must be a SlottedCapability")
    size = InstructionSize(size)
    if not size.is_legal_start(current.payload.cursor, current.slot):
        raise ValueError("instruction size is not legal at the current PCC slot")

    if size is InstructionSize.BITS_12 and current.slot == SLOT_0:
        next_cursor = current.payload.cursor
        next_slot = SLOT_1
    elif size is InstructionSize.BITS_12:
        next_cursor = current.payload.cursor + 1
        next_slot = SLOT_0
    else:
        next_cursor = current.payload.cursor + size.cells
        next_slot = SLOT_0

    next_capability = current.capability.with_cursor(next_cursor)
    return SlottedCapability.from_capability(next_capability, next_slot)


def explicit_slot0_target(
    target: Capability | SlottedCapability,
) -> SlottedCapability:
    """Normalize an explicit control-transfer target and reject slot 1."""
    if isinstance(target, SlottedCapability):
        if target.slot != SLOT_0:
            raise ValueError("explicit control-transfer targets must enter slot 0")
        return SlottedCapability.from_capability(target.capability, SLOT_0)
    if isinstance(target, Capability):
        return SlottedCapability.from_capability(target, SLOT_0)
    raise TypeError("target must be a Capability or SlottedCapability")


def redirect_to_explicit_target(
    instruction: DecodedInstruction,
    kind: RedirectKind,
    target: Capability | SlottedCapability,
) -> ExecutionResult:
    """Create a redirect result, or an `ALIGN_FAULT` for an explicit slot-1 target."""
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")
    kind = RedirectKind(kind)
    if instruction.location is None:
        raise ValueError("explicit redirect faults require an instruction location")

    if isinstance(target, SlottedCapability) and target.slot != SLOT_0:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ALIGN_FAULT,
                instruction.location,
                tval=target.payload.cursor,
            )
        )

    normalized = explicit_slot0_target(target)
    return instruction.redirect(RedirectPacket(kind, normalized))


def _program_key(key: ProgramKey) -> ProgramKey:
    if not isinstance(key, tuple) or len(key) != 2:
        raise TypeError("program key must be a (cell_address, slot) tuple")
    address, slot = key
    return (require_cell_address(address), require_slot(slot))


def _with_location(
    instruction: DecodedInstruction,
    location: InstructionLocation,
) -> DecodedInstruction:
    return DecodedInstruction(
        instruction.mnemonic,
        instruction.size,
        operands=instruction.operands,
        location=location,
        attributes=instruction.attributes,
    )


def _missing_instruction_fault(core: CoreState) -> ExecutionResult:
    location = InstructionLocation(core.pcc)
    instruction = DecodedInstruction(
        "ILLEGAL",
        InstructionSize.BITS_12,
        location=location,
    )
    return instruction.fault(
        FaultPacket(
            ExceptionCause.ILLEGAL_INSTRUCTION,
            location,
            tval=location.address,
        )
    )

"""Execution-result commit helpers for CPU v0.1."""

from __future__ import annotations

from .capabilities import Capability
from .cells import CAPABILITY_OBJECT_CELLS, INTEGER_OBJECT_CELLS
from .csrs import CSR_INSTRET, CSR_MASK
from .instructions import ExecutionResult, ExecutionResultKind
from .memory import TaggedMemory
from .state import CoreState, SlottedCapability


def commit_normal_result(
    core: CoreState,
    result: ExecutionResult,
    memory: TaggedMemory | None = None,
) -> None:
    """Commit a normal-retire result packet to architectural state."""
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(result, ExecutionResult):
        raise TypeError("result must be an ExecutionResult")
    if result.kind is not ExecutionResultKind.NORMAL_RETIRE:
        raise ValueError("only normal-retire results can be committed here")
    assert result.normal is not None

    effects = result.normal.effects

    for index, value in effects.integer_writes:
        core.write_d(index, value)

    for index, capability in effects.capability_writes:
        if not isinstance(capability, Capability):
            raise TypeError("capability write value must be a Capability")
        core.write_c(index, capability)

    explicit_instret_write = False
    for number, value in effects.csr_writes:
        explicit_instret_write = explicit_instret_write or number == CSR_INSTRET
        core.write_csr_raw(number, value)

    for index, capability in effects.ccsr_writes:
        if not isinstance(capability, Capability):
            raise TypeError("CCSR write value must be a Capability")
        core.write_ccsr(index, capability)

    if effects.memory_effects:
        if not isinstance(memory, TaggedMemory):
            raise ValueError("memory effects require a TaggedMemory commit target")
        for memory_effect in effects.memory_effects:
            apply_effect = getattr(memory_effect, "apply", None)
            if apply_effect is None:
                raise TypeError("memory effect must provide apply(memory)")
            apply_effect(memory)
            _clear_reservation_for_memory_effect(core, memory_effect)

    for tlb_effect in effects.tlb_effects:
        apply_effect = getattr(tlb_effect, "apply", None)
        if apply_effect is None:
            raise TypeError("TLB effect must provide apply(core)")
        apply_effect(core)

    for reservation_effect in effects.reservation_effects:
        apply_effect = getattr(reservation_effect, "apply", None)
        if apply_effect is None:
            raise TypeError("reservation effect must provide apply(core)")
        apply_effect(core)

    if effects.pcc_update is not None:
        if not isinstance(effects.pcc_update, SlottedCapability):
            raise TypeError("pcc_update must be a SlottedCapability")
        core.install_pcc(effects.pcc_update)

    if effects.epcc_update is not None:
        if not isinstance(effects.epcc_update, SlottedCapability):
            raise TypeError("epcc_update must be a SlottedCapability")
        core.install_epcc(effects.epcc_update)

    if not explicit_instret_write:
        core.write_csr_raw(CSR_INSTRET, (core.read_csr(CSR_INSTRET) + 1) & CSR_MASK)


def _clear_reservation_for_memory_effect(core: CoreState, memory_effect: object) -> None:
    address = getattr(memory_effect, "address", None)
    if type(address) is not int:
        return
    length_cells = getattr(memory_effect, "length_cells", None)
    if type(length_cells) is not int:
        if hasattr(memory_effect, "capability"):
            length_cells = CAPABILITY_OBJECT_CELLS
        else:
            length_cells = INTEGER_OBJECT_CELLS
    core.reservation.clear_if_overlaps(address, length_cells)

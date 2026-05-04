"""Cache maintenance instruction semantics for CPU v0.1.

Owner stories:
- E08-S04: fence and cache-maintenance ordering context.
- E09-S06: page memory-type legality for cache maintenance.
- E10-S05: `CACHE.CLEAN`, `CACHE.INVAL`, and `CACHE.CLEANINVAL`.
- I06-S04: cache/DMA litmus model support.
"""

from __future__ import annotations

from . import csrs
from .capabilities import decode_bounds_metadata
from .cells import ADDRESS_SPACE_CELLS, CACHE_LINE_CELLS
from .instructions import (
    ArchitecturalEffects,
    CapCause,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultCapIndex,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .memory import TaggedMemory
from .mmu import AccessType, MEMORY_TYPE_DEVICE_ORDERED, Translation, translate
from .reservations import ReservationClearEffect
from .state import CoreState, require_general_capability_register_index, require_integer_register_index


CACHE_MNEMONICS = frozenset({"CACHE.CLEAN", "CACHE.INVAL", "CACHE.CLEANINVAL"})


def cache_instruction(
    mnemonic: str,
    operands: tuple[object, ...],
    *,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(
        mnemonic,
        InstructionSize.BITS_24,
        operands=operands,
        location=location,
    )


def execute_cache(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_cache_checked(core, memory, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_cache_checked(
    core: CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic not in CACHE_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    location = _instruction_location(core, instruction)
    if not instruction.size.is_legal_start(location.address, location.slot):
        return instruction.fault(
            FaultPacket(ExceptionCause.ALIGN_FAULT, location, tval=location.address)
        )

    ca, di, dn = _operands(instruction, 3)
    ca = require_general_capability_register_index(ca)
    di = require_integer_register_index(di)
    dn = require_integer_register_index(dn)
    if not _is_kernel_mode(core):
        return instruction.fault(FaultPacket(ExceptionCause.PRIVILEGE_FAULT, location))

    length = core.read_d(dn)
    if length == 0:
        return instruction.normal_retire()

    start = _effective_address(core, ca, di)
    fault = _check_range_authority(core, instruction, ca, start, length)
    if fault is not None:
        return fault

    reservation_clear = False
    for virtual_line in range(_line_base(start), _line_top(start + length), CACHE_LINE_CELLS):
        translated = translate(
            core,
            memory,
            virtual_line,
            AccessType.MAINTENANCE,
            location,
        )
        if not isinstance(translated, Translation):
            return instruction.fault(translated)
        if translated.memory_type == MEMORY_TYPE_DEVICE_ORDERED:
            return instruction.fault(
                FaultPacket(
                    ExceptionCause.ACCESS_FAULT,
                    location,
                    tval=translated.physical_address,
                )
            )
        if instruction.mnemonic in ("CACHE.INVAL", "CACHE.CLEANINVAL"):
            reservation_clear = reservation_clear or core.reservation.overlaps(
                translated.physical_address,
                CACHE_LINE_CELLS,
            )

    if reservation_clear:
        return instruction.normal_retire(
            ArchitecturalEffects(reservation_effects=(ReservationClearEffect(),))
        )
    return instruction.normal_retire()


def _check_range_authority(
    core: CoreState,
    instruction: DecodedInstruction,
    authorizer_index: int,
    start: int,
    length: int,
) -> ExecutionResult | None:
    authorizer = core.read_c(authorizer_index)
    fault_cap_idx = _c_index(authorizer_index)
    if authorizer.is_invalid:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_TAG_FAULT,
            CapCause.TAG,
            fault_cap_idx,
            0,
        )
    if authorizer.is_sealed:
        return _capability_fault(
            core,
            instruction,
            ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
            CapCause.SEAL_TYPE,
            fault_cap_idx,
            0,
        )
    end = start + length
    if start < 0 or end <= start or end > ADDRESS_SPACE_CELLS:
        return _bounds_fault(core, instruction, fault_cap_idx, 0)
    line_start = _line_base(start)
    line_end = _line_top(end)
    bounds = decode_bounds_metadata(authorizer.payload.bounds_metadata)
    if not bounds.contains_range(start, end):
        return _bounds_fault(core, instruction, fault_cap_idx, start)
    if not bounds.contains_range(line_start, line_end):
        return _bounds_fault(core, instruction, fault_cap_idx, line_start)
    return None


def _instruction_location(
    core: CoreState,
    instruction: DecodedInstruction,
) -> InstructionLocation:
    if instruction.location is not None:
        return instruction.location
    return InstructionLocation(core.pcc)


def _operands(instruction: DecodedInstruction, count: int) -> tuple[int, ...]:
    if len(instruction.operands) != count:
        raise ValueError("wrong operand count")
    result = []
    for operand in instruction.operands:
        if type(operand) is not int:
            raise TypeError("cache operands must be register indices")
        result.append(operand)
    return tuple(result)


def _effective_address(core: CoreState, capability_index: int, offset_index: int) -> int:
    return core.read_c(capability_index).payload.cursor + _signed_48(core.read_d(offset_index))


def _signed_48(value: int) -> int:
    value &= (1 << 48) - 1
    sign_bit = 1 << 47
    if value & sign_bit:
        return value - (1 << 48)
    return value


def _line_base(address: int) -> int:
    return address - (address % CACHE_LINE_CELLS)


def _line_top(end: int) -> int:
    if end % CACHE_LINE_CELLS == 0:
        return end
    return end + (CACHE_LINE_CELLS - (end % CACHE_LINE_CELLS))


def _is_kernel_mode(core: CoreState) -> bool:
    return bool(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_PRIV_BIT))


def _c_index(index: int) -> FaultCapIndex:
    return FaultCapIndex(0x10 + index)


def _bounds_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        CapCause.BOUNDS,
        fault_cap_idx,
        tval,
    )


def _capability_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    cause: ExceptionCause,
    capcause: CapCause,
    fault_cap_idx: FaultCapIndex,
    tval: int,
) -> ExecutionResult:
    return instruction.fault(
        FaultPacket(
            cause,
            _instruction_location(core, instruction),
            tval=tval,
            capcause=capcause,
            fault_cap_idx=fault_cap_idx,
        )
    )

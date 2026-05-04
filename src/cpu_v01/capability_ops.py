"""Register-only capability instruction semantics for CPU v0.1.

Owner stories:
- E03-S03: monotonic capability derivation.
- E04-S05: capability instruction semantics.
- I03-S03: first capability derivation operations.
"""

from __future__ import annotations

from . import csrs
from .capabilities import (
    Capability,
    CapabilityPermission,
    OTYPE_UNSEALED,
    decode_bounds_metadata,
    encode_bounds_metadata,
    is_cseal_available_otype,
    is_cunseal_available_otype,
)
from .cells import ADDRESS_SPACE_CELLS
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
from .state import (
    CoreState,
    require_general_capability_register_index,
    require_integer_register_index,
)


REGISTER_DERIVATION_MNEMONICS = frozenset(
    {
        "CMOVE",
        "CGETADDR",
        "CSETADDR",
        "CINCADDR",
        "CSETBOUNDS",
        "CANDPERM",
        "CSEAL",
        "CUNSEAL",
    }
)


def capability_instruction(
    mnemonic: str,
    operands: tuple[object, ...],
    *,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    return DecodedInstruction(
        mnemonic,
        InstructionSize.BITS_48,
        operands=operands,
        location=location,
    )


def execute_capability(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_capability_checked(core, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_capability_checked(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    mnemonic = instruction.mnemonic
    if mnemonic not in REGISTER_DERIVATION_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    if mnemonic == "CMOVE":
        cd, cs = _operands(instruction, 2)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, core.read_c(cs)),))
        )

    if mnemonic == "CGETADDR":
        dd, cs = _operands(instruction, 2)
        dd = require_integer_register_index(dd)
        cs = require_general_capability_register_index(cs)
        return instruction.normal_retire(
            ArchitecturalEffects(integer_writes=((dd, core.read_c(cs).payload.cursor),))
        )

    if mnemonic == "CSETADDR":
        cd, cs, da = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        da = require_integer_register_index(da)
        source = core.read_c(cs)
        fault = _require_valid_unsealed(core, instruction, source, cs)
        if fault is not None:
            return fault
        candidate = core.read_d(da)
        if not _contains_cursor(source, candidate):
            return _capability_fault(
                core,
                instruction,
                ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                CapCause.BOUNDS,
                _c_index(cs),
                candidate,
            )
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, source.with_cursor(candidate)),))
        )

    if mnemonic == "CINCADDR":
        cd, cs, di = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        di = require_integer_register_index(di)
        source = core.read_c(cs)
        fault = _require_valid_unsealed(core, instruction, source, cs)
        if fault is not None:
            return fault
        candidate = source.payload.cursor + _signed_48(core.read_d(di))
        if not 0 <= candidate < ADDRESS_SPACE_CELLS:
            return _capability_fault(
                core,
                instruction,
                ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                CapCause.BOUNDS,
                _c_index(cs),
                0,
            )
        if not _contains_cursor(source, candidate):
            return _capability_fault(
                core,
                instruction,
                ExceptionCause.CAPABILITY_BOUNDS_FAULT,
                CapCause.BOUNDS,
                _c_index(cs),
                candidate,
            )
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, source.with_cursor(candidate)),))
        )

    if mnemonic == "CSETBOUNDS":
        cd, cs, dlen = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        dlen = require_integer_register_index(dlen)
        source = core.read_c(cs)
        fault = _require_valid_unsealed(core, instruction, source, cs)
        if fault is not None:
            return fault
        requested_base = source.payload.cursor
        requested_len = core.read_d(dlen)
        if requested_len == 0:
            return _bounds_fault(core, instruction, cs, requested_base)
        requested_top = requested_base + requested_len
        if requested_top > ADDRESS_SPACE_CELLS:
            return _bounds_fault(core, instruction, cs, 0)
        parent_bounds = decode_bounds_metadata(source.payload.bounds_metadata)
        if not parent_bounds.contains_range(requested_base, requested_top):
            tval = requested_base
            if parent_bounds.contains_cursor(requested_base):
                tval = requested_top
            return _bounds_fault(core, instruction, cs, tval)
        try:
            bounds_metadata = encode_bounds_metadata(requested_base, requested_top)
        except ValueError:
            return _bounds_fault(core, instruction, cs, requested_top)
        payload = source.payload.with_bounds_metadata(bounds_metadata)
        return instruction.normal_retire(
            ArchitecturalEffects(
                capability_writes=((cd, source.with_payload(payload)),)
            )
        )

    if mnemonic == "CANDPERM":
        cd, cs, dmask = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        dmask = require_integer_register_index(dmask)
        source = core.read_c(cs)
        fault = _require_valid_unsealed(core, instruction, source, cs)
        if fault is not None:
            return fault
        result = source.clear_permissions_by_mask(core.read_d(dmask) & 0xFF)
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, result),))
        )

    if mnemonic == "CSEAL":
        cd, cs, cauth = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        cauth = require_general_capability_register_index(cauth)
        source = core.read_c(cs)
        authority = core.read_c(cauth)
        fault = _require_valid_unsealed(core, instruction, source, cs)
        if fault is not None:
            return fault
        fault = _require_valid_unsealed(core, instruction, authority, cauth)
        if fault is not None:
            return fault
        if not authority.payload.has_permissions(CapabilityPermission.SEAL):
            return _permission_fault(core, instruction, cauth)
        otype = authority.payload.cursor & 0xFF
        if not is_cseal_available_otype(otype):
            return _seal_type_fault(core, instruction, cauth)
        return instruction.normal_retire(
            ArchitecturalEffects(capability_writes=((cd, source.with_otype(otype)),))
        )

    if mnemonic == "CUNSEAL":
        cd, cs, cauth = _operands(instruction, 3)
        cd = require_general_capability_register_index(cd)
        cs = require_general_capability_register_index(cs)
        cauth = require_general_capability_register_index(cauth)
        source = core.read_c(cs)
        authority = core.read_c(cauth)
        if source.is_invalid:
            return _tag_fault(core, instruction, cs)
        if source.is_unsealed:
            return _seal_type_fault(core, instruction, cs)
        fault = _require_valid_unsealed(core, instruction, authority, cauth)
        if fault is not None:
            return fault
        if not authority.payload.has_permissions(CapabilityPermission.UNSEAL):
            return _permission_fault(core, instruction, cauth)
        otype = authority.payload.cursor & 0xFF
        if otype != source.payload.otype or not is_cunseal_available_otype(otype):
            return _seal_type_fault(core, instruction, cauth)
        return instruction.normal_retire(
            ArchitecturalEffects(
                capability_writes=((cd, source.with_otype(OTYPE_UNSEALED)),)
            )
        )

    raise AssertionError(f"unhandled capability mnemonic {mnemonic}")


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
            raise TypeError("capability instruction operands must be register indices")
        result.append(operand)
    return tuple(result)


def _c_index(index: int) -> FaultCapIndex:
    return FaultCapIndex(0x10 + index)


def _signed_48(value: int) -> int:
    value &= csrs.CSR_MASK
    sign_bit = 1 << 47
    if value & sign_bit:
        return value - (1 << 48)
    return value


def _contains_cursor(capability: Capability, cursor: int) -> bool:
    bounds = decode_bounds_metadata(capability.payload.bounds_metadata)
    return bounds.contains_cursor(cursor)


def _require_valid_unsealed(
    core: CoreState,
    instruction: DecodedInstruction,
    capability: Capability,
    register_index: int,
) -> ExecutionResult | None:
    if capability.is_invalid:
        return _tag_fault(core, instruction, register_index)
    if capability.is_sealed:
        return _seal_type_fault(core, instruction, register_index)
    return None


def _tag_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    register_index: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_TAG_FAULT,
        CapCause.TAG,
        _c_index(register_index),
        0,
    )


def _bounds_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    register_index: int,
    tval: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_BOUNDS_FAULT,
        CapCause.BOUNDS,
        _c_index(register_index),
        tval,
    )


def _permission_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    register_index: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_PERMISSION_FAULT,
        CapCause.PERMISSION,
        _c_index(register_index),
        0,
    )


def _seal_type_fault(
    core: CoreState,
    instruction: DecodedInstruction,
    register_index: int,
) -> ExecutionResult:
    return _capability_fault(
        core,
        instruction,
        ExceptionCause.CAPABILITY_SEAL_TYPE_FAULT,
        CapCause.SEAL_TYPE,
        _c_index(register_index),
        0,
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

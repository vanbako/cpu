"""Integer instruction semantics for CPU v0.1.

Owner stories:
- E01-S02: integer widths and write forms.
- E01-S06: condition flag behavior.
- E04-S02: mandatory integer operation set.
- I03-S02: baseline integer operation execution.
"""

from __future__ import annotations

from enum import Enum, IntEnum

from . import csrs
from .instructions import (
    ArchitecturalEffects,
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .state import CoreState


class IntegerWidth(IntEnum):
    W8 = 8
    W12 = 12
    W16 = 16
    W24 = 24
    W32 = 32
    W48 = 48

    @property
    def mask(self) -> int:
        return (1 << int(self)) - 1

    @property
    def sign_bit(self) -> int:
        return 1 << (int(self) - 1)


class WriteForm(Enum):
    ZERO_EXTEND = "ZERO_EXTEND"
    SIGN_EXTEND = "SIGN_EXTEND"
    FULL_WIDTH = "FULL_WIDTH"


class ConditionCode(Enum):
    AL = "AL"
    EQ = "EQ"
    NE = "NE"
    CS = "CS"
    HS = "CS"
    CC = "CC"
    LO = "CC"
    MI = "MI"
    PL = "PL"
    VS = "VS"
    VC = "VC"
    HI = "HI"
    LS = "LS"
    GE = "GE"
    LT = "LT"
    GT = "GT"
    LE = "LE"


MANDATORY_INTEGER_MNEMONICS = frozenset(
    {
        "CPY",
        "NEG",
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
        "NOT",
        "AND",
        "OR",
        "XOR",
        "SHL",
        "SHRS",
        "SHRU",
        "ROL",
        "ROR",
        "CMP",
        "CMPU",
        "TST",
        "SETCC",
        "CMOVCC",
        "BSET",
        "BCLR",
    }
)

UNARY_MNEMONICS = frozenset({"CPY", "NEG", "NOT"})
BINARY_MNEMONICS = frozenset(
    {
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
    }
)
FLAG_MNEMONICS = frozenset({"CMP", "CMPU", "TST"})


def integer_instruction(
    mnemonic: str,
    operands: tuple[object, ...],
    *,
    width: IntegerWidth = IntegerWidth.W48,
    write_form: WriteForm = WriteForm.ZERO_EXTEND,
    condition: ConditionCode | str | None = None,
    location: InstructionLocation | None = None,
) -> DecodedInstruction:
    attributes: dict[str, object] = {
        "width": IntegerWidth(width),
        "write_form": WriteForm(write_form),
    }
    if condition is not None:
        attributes["condition"] = normalize_condition(condition)
    return DecodedInstruction(
        mnemonic,
        InstructionSize.BITS_24,
        operands=operands,
        location=location,
        attributes=attributes,
    )


def execute_integer(core: CoreState, instruction: DecodedInstruction) -> ExecutionResult:
    if not isinstance(core, CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(instruction, DecodedInstruction):
        raise TypeError("instruction must be a DecodedInstruction")

    try:
        return _execute_integer_checked(core, instruction)
    except (IndexError, KeyError, TypeError, ValueError):
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )


def _execute_integer_checked(
    core: CoreState,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    mnemonic = instruction.mnemonic
    if mnemonic not in MANDATORY_INTEGER_MNEMONICS:
        return instruction.fault(
            FaultPacket(
                ExceptionCause.ILLEGAL_INSTRUCTION,
                _instruction_location(core, instruction),
            )
        )

    if mnemonic in UNARY_MNEMONICS:
        rd, rs = _operands(instruction, 2)
        width = _width(instruction)
        write_form = _write_form(instruction)
        source = _u(core.read_d(rs), width)
        result = _unary_result(mnemonic, source, width)
        return _integer_write_result(instruction, rd, result, width, write_form)

    if mnemonic in BINARY_MNEMONICS:
        rd, ra, rb = _operands(instruction, 3)
        width = _width(instruction)
        write_form = _write_form(instruction)
        lhs = core.read_d(ra)
        rhs = core.read_d(rb)
        if mnemonic in {"DIV", "DIVU", "MOD", "MODU"} and _u(rhs, width) == 0:
            return instruction.fault(
                FaultPacket(
                    ExceptionCause.DIVIDE_BY_ZERO,
                    _instruction_location(core, instruction),
                )
            )
        result = _binary_result(mnemonic, lhs, rhs, width)
        return _integer_write_result(instruction, rd, result, width, write_form)

    if mnemonic in FLAG_MNEMONICS:
        ra, rb = _operands(instruction, 2)
        width = _width(instruction)
        new_sr = _flag_result(
            mnemonic,
            core.read_d(ra),
            core.read_d(rb),
            width,
            core.read_csr(csrs.CSR_SR),
        )
        return instruction.normal_retire(
            ArchitecturalEffects(csr_writes=((csrs.CSR_SR, new_sr),))
        )

    if mnemonic == "SETCC":
        rd = _operands(instruction, 1)[0]
        condition = _condition(instruction)
        value = 1 if condition_true(condition, core.read_csr(csrs.CSR_SR)) else 0
        return instruction.normal_retire(
            ArchitecturalEffects(integer_writes=((rd, value),))
        )

    if mnemonic == "CMOVCC":
        rd, rs = _operands(instruction, 2)
        condition = _condition(instruction)
        if not condition_true(condition, core.read_csr(csrs.CSR_SR)):
            return instruction.normal_retire()
        width = _width(instruction)
        write_form = _write_form(instruction)
        value = _apply_write_form(_u(core.read_d(rs), width), width, write_form)
        return instruction.normal_retire(
            ArchitecturalEffects(integer_writes=((rd, value),))
        )

    raise AssertionError(f"unhandled integer mnemonic {mnemonic}")


def condition_true(condition: ConditionCode | str, sr_value: int) -> bool:
    condition = normalize_condition(condition)
    z = _bit(sr_value, csrs.SR_Z_BIT)
    n = _bit(sr_value, csrs.SR_N_BIT)
    c = _bit(sr_value, csrs.SR_C_BIT)
    v = _bit(sr_value, csrs.SR_V_BIT)

    if condition is ConditionCode.AL:
        return True
    if condition is ConditionCode.EQ:
        return z
    if condition is ConditionCode.NE:
        return not z
    if condition is ConditionCode.CS:
        return c
    if condition is ConditionCode.CC:
        return not c
    if condition is ConditionCode.MI:
        return n
    if condition is ConditionCode.PL:
        return not n
    if condition is ConditionCode.VS:
        return v
    if condition is ConditionCode.VC:
        return not v
    if condition is ConditionCode.HI:
        return c and not z
    if condition is ConditionCode.LS:
        return (not c) or z
    if condition is ConditionCode.GE:
        return n == v
    if condition is ConditionCode.LT:
        return n != v
    if condition is ConditionCode.GT:
        return (not z) and n == v
    if condition is ConditionCode.LE:
        return z or n != v
    raise AssertionError(f"unhandled condition {condition}")


def normalize_condition(condition: ConditionCode | str) -> ConditionCode:
    if isinstance(condition, ConditionCode):
        return condition
    if not isinstance(condition, str):
        raise TypeError("condition must be a ConditionCode or str")
    normalized = condition.upper()
    if normalized == "HS":
        normalized = "CS"
    elif normalized == "LO":
        normalized = "CC"
    return ConditionCode[normalized]


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
            raise TypeError("integer operands must be register indices")
        result.append(operand)
    return tuple(result)


def _width(instruction: DecodedInstruction) -> IntegerWidth:
    return IntegerWidth(instruction.attributes.get("width", IntegerWidth.W48))


def _write_form(instruction: DecodedInstruction) -> WriteForm:
    return WriteForm(instruction.attributes.get("write_form", WriteForm.ZERO_EXTEND))


def _condition(instruction: DecodedInstruction) -> ConditionCode:
    return normalize_condition(instruction.attributes["condition"])


def _integer_write_result(
    instruction: DecodedInstruction,
    rd: int,
    result_w: int,
    width: IntegerWidth,
    write_form: WriteForm,
) -> ExecutionResult:
    value = _apply_write_form(result_w, width, write_form)
    return instruction.normal_retire(
        ArchitecturalEffects(integer_writes=((rd, value),))
    )


def _apply_write_form(result_w: int, width: IntegerWidth, write_form: WriteForm) -> int:
    result_w &= width.mask
    if width is IntegerWidth.W48:
        return result_w
    if write_form is WriteForm.ZERO_EXTEND:
        return result_w
    if write_form is WriteForm.SIGN_EXTEND:
        if result_w & width.sign_bit:
            return result_w | (csrs.CSR_MASK ^ width.mask)
        return result_w
    if write_form is WriteForm.FULL_WIDTH:
        raise ValueError("full-width write form is valid only for W48")
    raise AssertionError(f"unhandled write form {write_form}")


def _unary_result(mnemonic: str, source: int, width: IntegerWidth) -> int:
    if mnemonic == "CPY":
        return source
    if mnemonic == "NEG":
        return (-source) & width.mask
    if mnemonic == "NOT":
        return (~source) & width.mask
    raise AssertionError(f"unhandled unary mnemonic {mnemonic}")


def _binary_result(mnemonic: str, lhs: int, rhs: int, width: IntegerWidth) -> int:
    lhs_u = _u(lhs, width)
    rhs_u = _u(rhs, width)
    count = rhs & 0x3F

    if mnemonic in {"ADD", "ADDU"}:
        return (lhs_u + rhs_u) & width.mask
    if mnemonic in {"SUB", "SUBU"}:
        return (lhs_u - rhs_u) & width.mask
    if mnemonic == "MUL":
        return (_s(lhs, width) * _s(rhs, width)) & width.mask
    if mnemonic == "MULU":
        return (lhs_u * rhs_u) & width.mask
    if mnemonic == "DIV":
        return _signed_div(_s(lhs, width), _s(rhs, width)) & width.mask
    if mnemonic == "DIVU":
        return lhs_u // rhs_u
    if mnemonic == "MOD":
        return _signed_mod(_s(lhs, width), _s(rhs, width)) & width.mask
    if mnemonic == "MODU":
        return lhs_u % rhs_u
    if mnemonic == "AND":
        return lhs_u & rhs_u
    if mnemonic == "OR":
        return lhs_u | rhs_u
    if mnemonic == "XOR":
        return lhs_u ^ rhs_u
    if mnemonic == "SHL":
        return 0 if count >= int(width) else (lhs_u << count) & width.mask
    if mnemonic == "SHRU":
        return 0 if count >= int(width) else lhs_u >> count
    if mnemonic == "SHRS":
        if count >= int(width):
            return width.mask if _s(lhs, width) < 0 else 0
        return (_s(lhs, width) >> count) & width.mask
    if mnemonic == "ROL":
        rot = count % int(width)
        if rot == 0:
            return lhs_u
        return ((lhs_u << rot) | (lhs_u >> (int(width) - rot))) & width.mask
    if mnemonic == "ROR":
        rot = count % int(width)
        if rot == 0:
            return lhs_u
        return ((lhs_u >> rot) | (lhs_u << (int(width) - rot))) & width.mask
    if mnemonic == "BSET":
        return lhs_u | (1 << (count % int(width)))
    if mnemonic == "BCLR":
        return lhs_u & ~(1 << (count % int(width)))
    raise AssertionError(f"unhandled binary mnemonic {mnemonic}")


def _flag_result(
    mnemonic: str,
    lhs: int,
    rhs: int,
    width: IntegerWidth,
    old_sr: int,
) -> int:
    lhs_u = _u(lhs, width)
    rhs_u = _u(rhs, width)
    if mnemonic in {"CMP", "CMPU"}:
        diff = (lhs_u - rhs_u) & width.mask
        lhs_sign = bool(lhs_u & width.sign_bit)
        rhs_sign = bool(rhs_u & width.sign_bit)
        diff_sign = bool(diff & width.sign_bit)
        return _set_flags(
            old_sr,
            z=diff == 0,
            n=diff_sign,
            c=lhs_u >= rhs_u,
            v=(lhs_sign != rhs_sign) and (diff_sign != lhs_sign),
        )
    if mnemonic == "TST":
        value = lhs_u & rhs_u
        return _set_flags(
            old_sr,
            z=value == 0,
            n=bool(value & width.sign_bit),
            c=False,
            v=False,
        )
    raise AssertionError(f"unhandled flag mnemonic {mnemonic}")


def _u(value: int, width: IntegerWidth) -> int:
    return value & width.mask


def _s(value: int, width: IntegerWidth) -> int:
    value = _u(value, width)
    if value & width.sign_bit:
        return value - (1 << int(width))
    return value


def _signed_div(lhs: int, rhs: int) -> int:
    quotient = abs(lhs) // abs(rhs)
    return -quotient if (lhs < 0) != (rhs < 0) else quotient


def _signed_mod(lhs: int, rhs: int) -> int:
    quotient = _signed_div(lhs, rhs)
    return lhs - quotient * rhs


def _bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))


def _set_flags(old_sr: int, *, z: bool, n: bool, c: bool, v: bool) -> int:
    flags_mask = (
        (1 << csrs.SR_Z_BIT)
        | (1 << csrs.SR_N_BIT)
        | (1 << csrs.SR_C_BIT)
        | (1 << csrs.SR_V_BIT)
    )
    value = old_sr & ~flags_mask
    if z:
        value |= 1 << csrs.SR_Z_BIT
    if n:
        value |= 1 << csrs.SR_N_BIT
    if c:
        value |= 1 << csrs.SR_C_BIT
    if v:
        value |= 1 << csrs.SR_V_BIT
    return value

"""Assembler/disassembler helpers for CPU v0.1 binary fixtures.

Owner stories:
- E04-S01: instruction packing and placement rules.
- E04-S06: mandatory source mnemonics and `SCALL` synonym.
- I07-S02: assembler/disassembler binary fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Sequence

from . import cells as cell_model
from . import csrs, opcodes, state
from .instructions import InstructionSize


class AssemblyError(ValueError):
    """Raised when source text cannot be encoded as a v0.1 fixture."""


class DecodeError(ValueError):
    """Raised when fixture bits do not name a legal v0.1 instruction encoding."""


class IntegerWidthCode(IntEnum):
    W8 = 0
    W12 = 1
    W16 = 2
    W24 = 3
    W32 = 4
    W48 = 5


WIDTH_SUFFIX_TO_CODE = {
    "W8": IntegerWidthCode.W8,
    "W12": IntegerWidthCode.W12,
    "W16": IntegerWidthCode.W16,
    "W24": IntegerWidthCode.W24,
    "W32": IntegerWidthCode.W32,
    "W48": IntegerWidthCode.W48,
}

WIDTH_CODE_TO_SUFFIX = {code: suffix for suffix, code in WIDTH_SUFFIX_TO_CODE.items()}
WRITE_SUFFIX_TO_CODE = {"Z": 0, "S": 1}
WRITE_CODE_TO_SUFFIX = {code: suffix for suffix, code in WRITE_SUFFIX_TO_CODE.items()}
DEFAULT_WIDTH_CODE = IntegerWidthCode.W48
DEFAULT_WRITE_CODE = WRITE_SUFFIX_TO_CODE["Z"]

CANONICAL_CONDITION_CODES = (
    "AL",
    "EQ",
    "NE",
    "CS",
    "CC",
    "MI",
    "PL",
    "VS",
    "VC",
    "HI",
    "LS",
    "GE",
    "LT",
    "GT",
    "LE",
)
CONDITION_TO_CODE = {name: index for index, name in enumerate(CANONICAL_CONDITION_CODES)}
CODE_TO_CONDITION = {index: name for name, index in CONDITION_TO_CODE.items()}


@dataclass(frozen=True)
class EncodedInstruction:
    """A single assembled instruction before or after program packing."""

    form: opcodes.OpcodeForm
    value: int
    operands: tuple[object, ...] = ()
    width: IntegerWidthCode = DEFAULT_WIDTH_CODE
    write_code: int = DEFAULT_WRITE_CODE

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _require_uint(self.value, self.form.size.bits, "value"))
        object.__setattr__(self, "operands", tuple(self.operands))
        object.__setattr__(self, "width", IntegerWidthCode(self.width))
        if self.write_code not in WRITE_CODE_TO_SUFFIX:
            raise ValueError("write_code must be a defined fixture write-form code")

    @property
    def size(self) -> InstructionSize:
        return self.form.size

    @property
    def cells(self) -> tuple[int, ...]:
        if self.size is InstructionSize.BITS_12:
            return (self.value,)
        if self.size is InstructionSize.BITS_24:
            return (self.value & cell_model.CELL_MASK,)
        return (
            self.value & cell_model.CELL_MASK,
            (self.value >> cell_model.CELL_BITS) & cell_model.CELL_MASK,
        )

    @property
    def source(self) -> str:
        return format_instruction(self)


_FORM_BY_SIZE_OPCODE = {
    (form.size, form.opcode_id): form for form in opcodes.all_opcode_forms()
}


def assemble_line(source: str) -> EncodedInstruction:
    """Assemble one source instruction into its unpacked binary value."""

    mnemonic_text, operand_tokens, suffixes = _split_source(source)
    canonical, implied_condition = _canonicalize_source_mnemonic(mnemonic_text)
    forced_long = False
    width = DEFAULT_WIDTH_CODE
    write_code = DEFAULT_WRITE_CODE
    seen_width = False
    seen_write = False
    for suffix in suffixes:
        if suffix == "L":
            if forced_long:
                raise AssemblyError("duplicate .L suffix")
            forced_long = True
        elif suffix in WIDTH_SUFFIX_TO_CODE:
            if seen_width:
                raise AssemblyError("duplicate width suffix")
            width = WIDTH_SUFFIX_TO_CODE[suffix]
            seen_width = True
        elif suffix in WRITE_SUFFIX_TO_CODE:
            if seen_write:
                raise AssemblyError("duplicate write-form suffix")
            write_code = WRITE_SUFFIX_TO_CODE[suffix]
            seen_write = True
        else:
            raise AssemblyError(f"unsupported mnemonic suffix .{suffix}")

    if implied_condition is not None:
        if canonical == "BCC":
            operand_tokens = (implied_condition, *operand_tokens)
        else:
            operand_tokens = (*operand_tokens, implied_condition)

    try:
        forms = opcodes.opcode_forms_for(canonical)
    except KeyError as exc:
        raise AssemblyError(str(exc)) from exc

    form = _select_form(forms, operand_tokens, forced_long)
    operand_bits, operands = _encode_operands(form, operand_tokens, width, write_code)
    value = _compose_value(form, operand_bits)
    return EncodedInstruction(form, value, operands, width, write_code)


def decode_value(size: InstructionSize, value: int) -> EncodedInstruction:
    """Decode one unpacked instruction value."""

    size = InstructionSize(size)
    value = _require_uint(value, size.bits, "value")
    opcode_id = _opcode_id_from_value(size, value)
    form = _FORM_BY_SIZE_OPCODE.get((size, opcode_id))
    if form is None or (value & form.fixed_mask) != form.fixed_value:
        raise DecodeError(f"reserved {size.bits}-bit opcode selector 0x{opcode_id:02X}")
    operand_bits = _extract_operand_bits(form, value)
    operands, width, write_code = _decode_operands(form, operand_bits)
    return EncodedInstruction(form, value, operands, width, write_code)


def assemble_program(lines: Iterable[str]) -> tuple[int, ...]:
    """Assemble source lines into packed 24-bit instruction cells."""

    cells: list[int] = []
    half_full = False
    for line in lines:
        if not _strip_comment(line):
            continue
        encoded = assemble_line(line)
        if encoded.size is InstructionSize.BITS_12:
            if half_full:
                cells[-1] |= encoded.value << 12
                half_full = False
            else:
                cells.append(encoded.value)
                half_full = True
            continue

        if half_full:
            raise AssemblyError("24-bit and 48-bit instructions cannot start in slot 1")
        if encoded.size is InstructionSize.BITS_24:
            cells.append(encoded.cells[0])
            continue

        if len(cells) % cell_model.FETCH_GROUP_CELLS != 0:
            raise AssemblyError("48-bit instructions must start at a fetch-group boundary")
        cells.extend(encoded.cells)

    return tuple(cells)


def disassemble_program(cells: Iterable[int]) -> tuple[str, ...]:
    """Disassemble packed 24-bit instruction cells to canonical source lines."""

    cell_values = tuple(cell_model.require_cell_value(cell) for cell in cells)
    lines: list[str] = []
    index = 0
    while index < len(cell_values):
        cell = cell_values[index]
        major = (cell >> 16) & 0xFF
        if (InstructionSize.BITS_48, major) in _FORM_BY_SIZE_OPCODE:
            if index % cell_model.FETCH_GROUP_CELLS != 0:
                raise DecodeError("48-bit instruction starts outside fetch-group slot 0")
            if index + 1 >= len(cell_values):
                raise DecodeError("truncated 48-bit instruction")
            value = cell | (cell_values[index + 1] << cell_model.CELL_BITS)
            lines.append(format_instruction(decode_value(InstructionSize.BITS_48, value)))
            index += 2
            continue

        if (InstructionSize.BITS_24, major) in _FORM_BY_SIZE_OPCODE:
            lines.append(format_instruction(decode_value(InstructionSize.BITS_24, cell)))
            index += 1
            continue

        low = cell & 0xFFF
        high = (cell >> 12) & 0xFFF
        lines.append(format_instruction(decode_value(InstructionSize.BITS_12, low)))
        if high:
            lines.append(format_instruction(decode_value(InstructionSize.BITS_12, high)))
        index += 1
    return tuple(lines)


def format_instruction(encoded: EncodedInstruction) -> str:
    mnemonic = _format_mnemonic(encoded)
    operands = tuple(_format_operand(operand) for operand in encoded.operands)
    if not operands:
        return mnemonic
    return f"{mnemonic} {', '.join(operands)}"


def _format_mnemonic(encoded: EncodedInstruction) -> str:
    mnemonic = encoded.form.source_mnemonic
    if mnemonic == "SCALL":
        mnemonic = "SYS"
    if (
        encoded.form.mnemonic in {"CSRRD", "CSRWR", "CSRSET", "CSRCLR"}
        and encoded.form.size is InstructionSize.BITS_48
        and _encoded_csr_number(encoded) < csrs.FAST_CSR_COUNT
    ):
        mnemonic = f"{mnemonic}.L"
    if "WIDTH" not in encoded.form.binary_format:
        return mnemonic
    suffixes: list[str] = []
    if encoded.width != DEFAULT_WIDTH_CODE:
        suffixes.append(WIDTH_CODE_TO_SUFFIX[encoded.width])
    if encoded.write_code != DEFAULT_WRITE_CODE:
        suffixes.append(WRITE_CODE_TO_SUFFIX[encoded.write_code])
    if suffixes:
        return mnemonic.upper() + "." + ".".join(suffixes)
    return mnemonic


def _encoded_csr_number(encoded: EncodedInstruction) -> int:
    for operand in encoded.operands:
        kind, value = operand
        if kind == "CSR":
            return int(value)
    raise AssertionError("CSR form has no CSR operand")


def _format_operand(operand: object) -> str:
    kind, value = operand
    if kind == "D":
        return f"D{value}"
    if kind == "C":
        return f"C{value}"
    if kind == "COND":
        return str(value)
    if kind == "TARGET":
        return _format_int(value)
    if kind == "CSR":
        return _format_csr(value)
    if kind == "CCSR":
        return _format_ccsr(value)
    raise AssertionError(f"unknown operand kind {kind!r}")


def _split_source(source: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    text = _strip_comment(source)
    if not text:
        raise AssemblyError("source line is empty")
    parts = text.split(None, 1)
    mnemonic = parts[0].strip()
    operands = ()
    if len(parts) == 2:
        operands = tuple(part.strip() for part in parts[1].split(","))
        if any(not operand for operand in operands):
            raise AssemblyError(f"malformed operand list in {source!r}")

    exact = _try_opcode_mnemonic(mnemonic)
    if exact is not None:
        return exact, operands, ()

    pieces = mnemonic.upper().split(".")
    for end in range(len(pieces) - 1, 0, -1):
        candidate = ".".join(pieces[:end])
        exact = _try_opcode_mnemonic(candidate)
        if exact is not None:
            return exact, operands, tuple(pieces[end:])
    return mnemonic, operands, ()


def _strip_comment(source: str) -> str:
    return source.split("#", 1)[0].split(";", 1)[0].strip()


def _try_opcode_mnemonic(mnemonic: str) -> str | None:
    try:
        opcodes.opcode_forms_for(mnemonic)
    except KeyError:
        return None
    return mnemonic


def _canonicalize_source_mnemonic(mnemonic: str) -> tuple[str, str | None]:
    normalized = opcodes.normalize_mnemonic(mnemonic)
    if _try_opcode_mnemonic(normalized) is not None:
        return opcodes.canonical_mnemonic(normalized), None

    for prefix, family in (("CMOV", "CMOVCC"), ("SET", "SETCC"), ("B", "BCC")):
        if normalized.startswith(prefix) and len(normalized) > len(prefix):
            suffix = normalized[len(prefix) :]
            try:
                condition = opcodes.canonical_condition(suffix)
            except KeyError:
                continue
            return family, condition
    return normalized, None


def _select_form(
    forms: Sequence[opcodes.OpcodeForm],
    operands: Sequence[str],
    forced_long: bool,
) -> opcodes.OpcodeForm:
    if len(forms) == 1:
        if forced_long:
            raise AssemblyError(f"{forms[0].mnemonic} has no long form")
        return forms[0]

    mnemonic = forms[0].mnemonic
    if mnemonic not in {"CSRRD", "CSRWR", "CSRSET", "CSRCLR"}:
        raise AssemblyError(f"{mnemonic} requires an explicit fixture form")

    csr_token = _csr_operand_token(mnemonic, operands)
    csr_number = _parse_csr(csr_token)
    target_size = InstructionSize.BITS_48 if forced_long or csr_number >= csrs.FAST_CSR_COUNT else InstructionSize.BITS_24
    for form in forms:
        if form.size is target_size:
            return form
    raise AssemblyError(f"{mnemonic} has no {target_size.bits}-bit form")


def _csr_operand_token(mnemonic: str, operands: Sequence[str]) -> str:
    expected = {
        "CSRRD": 2,
        "CSRWR": 2,
        "CSRSET": 3,
        "CSRCLR": 3,
    }[mnemonic]
    if len(operands) != expected:
        raise AssemblyError(f"{mnemonic} expects {expected} operands")
    return operands[1] if mnemonic in {"CSRRD", "CSRSET", "CSRCLR"} else operands[0]


def _compose_value(form: opcodes.OpcodeForm, operand_bits: int) -> int:
    if form.size is InstructionSize.BITS_12:
        if operand_bits:
            raise AssemblyError(f"{form.mnemonic} has no operand bits")
        return form.fixed_value
    if form.size is InstructionSize.BITS_24:
        operand_bits = _require_uint(operand_bits, 16, "operand_bits")
        return form.fixed_value | operand_bits
    operand_bits = _require_uint(operand_bits, 40, "operand_bits")
    high_operands = operand_bits >> 16
    low_operands = operand_bits & 0xFFFF
    return (high_operands << 24) | form.fixed_value | low_operands


def _extract_operand_bits(form: opcodes.OpcodeForm, value: int) -> int:
    if form.size is InstructionSize.BITS_12:
        return 0
    if form.size is InstructionSize.BITS_24:
        return value & 0xFFFF
    return ((value >> 24) << 16) | (value & 0xFFFF)


def _opcode_id_from_value(size: InstructionSize, value: int) -> int:
    if size is InstructionSize.BITS_12:
        return value
    return (value >> 16) & 0xFF


def _encode_operands(
    form: opcodes.OpcodeForm,
    tokens: Sequence[str],
    width: IntegerWidthCode,
    write_code: int,
) -> tuple[int, tuple[object, ...]]:
    values, operands, field_widths = _operand_values(form.binary_format, form.mnemonic, tokens, width, write_code)
    total_bits = 16 if form.size is InstructionSize.BITS_24 else 40
    if form.size is InstructionSize.BITS_12:
        total_bits = 0
    return _pack_fields(values, field_widths, total_bits), operands


def _decode_operands(
    form: opcodes.OpcodeForm,
    operand_bits: int,
) -> tuple[tuple[object, ...], IntegerWidthCode, int]:
    values, reserved = _unpack_fields(operand_bits, _field_widths(form.binary_format), _operand_total_bits(form))
    if reserved:
        raise DecodeError(f"{form.mnemonic} has nonzero reserved operand bits")
    return _operands_from_values(form.binary_format, form.mnemonic, values)


def _operand_total_bits(form: opcodes.OpcodeForm) -> int:
    if form.size is InstructionSize.BITS_12:
        return 0
    if form.size is InstructionSize.BITS_24:
        return 16
    return 40


def _operand_values(
    binary_format: str,
    mnemonic: str,
    tokens: Sequence[str],
    width: IntegerWidthCode,
    write_code: int,
) -> tuple[tuple[int, ...], tuple[object, ...], tuple[int, ...]]:
    if binary_format in {"OP12", "OP24"}:
        _require_operand_count(mnemonic, tokens, 0)
        return (), (), ()
    if binary_format == "D":
        _require_operand_count(mnemonic, tokens, 1)
        d0 = _parse_d(tokens[0])
        return (d0,), (("D", d0),), (4,)
    if binary_format == "C":
        _require_operand_count(mnemonic, tokens, 1)
        c0 = _parse_c(tokens[0])
        return (c0,), (("C", c0),), (4,)
    if binary_format == "D_D":
        _require_operand_count(mnemonic, tokens, 2)
        d0, d1 = (_parse_d(token) for token in tokens)
        return (d0, d1), (("D", d0), ("D", d1)), (4, 4)
    if binary_format == "D_D_WIDTH_WF":
        _require_operand_count(mnemonic, tokens, 2)
        d0, d1 = (_parse_d(token) for token in tokens)
        return (d0, d1, int(width), write_code), (("D", d0), ("D", d1)), (4, 4, 3, 1)
    if binary_format == "D_D_D_WIDTH_WF":
        _require_operand_count(mnemonic, tokens, 3)
        d0, d1, d2 = (_parse_d(token) for token in tokens)
        return (
            (d0, d1, d2, int(width), write_code),
            (("D", d0), ("D", d1), ("D", d2)),
            (4, 4, 4, 3, 1),
        )
    if binary_format == "D_D_WIDTH":
        _require_operand_count(mnemonic, tokens, 2)
        d0, d1 = (_parse_d(token) for token in tokens)
        return (d0, d1, int(width)), (("D", d0), ("D", d1)), (4, 4, 3)
    if binary_format == "D_CC":
        _require_operand_count(mnemonic, tokens, 2)
        d0 = _parse_d(tokens[0])
        condition = _parse_condition(tokens[1])
        return (d0, condition), (("D", d0), ("COND", CODE_TO_CONDITION[condition])), (4, 4)
    if binary_format == "D_D_CC":
        _require_operand_count(mnemonic, tokens, 3)
        d0 = _parse_d(tokens[0])
        d1 = _parse_d(tokens[1])
        condition = _parse_condition(tokens[2])
        return (d0, d1, condition), (("D", d0), ("D", d1), ("COND", CODE_TO_CONDITION[condition])), (4, 4, 4)
    if binary_format == "D_C_D":
        _require_operand_count(mnemonic, tokens, 3)
        d0 = _parse_d(tokens[0])
        c0 = _parse_c(tokens[1])
        d1 = _parse_d(tokens[2])
        return (d0, c0, d1), (("D", d0), ("C", c0), ("D", d1)), (4, 4, 4)
    if binary_format == "C_D_D":
        _require_operand_count(mnemonic, tokens, 3)
        c0 = _parse_c(tokens[0])
        d0 = _parse_d(tokens[1])
        d1 = _parse_d(tokens[2])
        return (c0, d0, d1), (("C", c0), ("D", d0), ("D", d1)), (4, 4, 4)
    if binary_format == "C_C_D":
        _require_operand_count(mnemonic, tokens, 3)
        c0 = _parse_c(tokens[0])
        c1 = _parse_c(tokens[1])
        d0 = _parse_d(tokens[2])
        return (c0, c1, d0), (("C", c0), ("C", c1), ("D", d0)), (4, 4, 4)
    if binary_format == "C_D_C":
        _require_operand_count(mnemonic, tokens, 3)
        c0 = _parse_c(tokens[0])
        d0 = _parse_d(tokens[1])
        c1 = _parse_c(tokens[2])
        return (c0, d0, c1), (("C", c0), ("D", d0), ("C", c1)), (4, 4, 4)
    if binary_format == "D_C_D_D":
        _require_operand_count(mnemonic, tokens, 4)
        d0 = _parse_d(tokens[0])
        c0 = _parse_c(tokens[1])
        d1 = _parse_d(tokens[2])
        d2 = _parse_d(tokens[3])
        return (d0, c0, d1, d2), (("D", d0), ("C", c0), ("D", d1), ("D", d2)), (4, 4, 4, 4)
    if binary_format == "C_C":
        _require_operand_count(mnemonic, tokens, 2)
        c0, c1 = (_parse_c(token) for token in tokens)
        return (c0, c1), (("C", c0), ("C", c1)), (4, 4)
    if binary_format == "D_C":
        _require_operand_count(mnemonic, tokens, 2)
        d0 = _parse_d(tokens[0])
        c0 = _parse_c(tokens[1])
        return (d0, c0), (("D", d0), ("C", c0)), (4, 4)
    if binary_format == "C_C_C":
        _require_operand_count(mnemonic, tokens, 3)
        c0, c1, c2 = (_parse_c(token) for token in tokens)
        return (c0, c1, c2), (("C", c0), ("C", c1), ("C", c2)), (4, 4, 4)
    if binary_format == "TARGET24":
        _require_operand_count(mnemonic, tokens, 1)
        target = _parse_uint(tokens[0], 16, "target")
        return (target,), (("TARGET", target),), (16,)
    if binary_format == "CC_TARGET":
        _require_operand_count(mnemonic, tokens, 2)
        condition = _parse_condition(tokens[0])
        target = _parse_uint(tokens[1], 12, "target")
        return (condition, target), (("COND", CODE_TO_CONDITION[condition]), ("TARGET", target)), (4, 12)
    if binary_format == "C_D":
        _require_operand_count(mnemonic, tokens, 2)
        c0 = _parse_c(tokens[0])
        d0 = _parse_d(tokens[1])
        return (c0, d0), (("C", c0), ("D", d0)), (4, 4)
    if binary_format == "D_CSR4":
        _require_operand_count(mnemonic, tokens, 2)
        d0 = _parse_d(tokens[0])
        csr = _parse_csr(tokens[1])
        if csr >= csrs.FAST_CSR_COUNT:
            raise AssemblyError("fast CSR form can only encode CSR numbers 0x00-0x0F")
        return (d0, csr), (("D", d0), ("CSR", csr)), (4, 4)
    if binary_format == "CSR4_D":
        _require_operand_count(mnemonic, tokens, 2)
        csr = _parse_csr(tokens[0])
        d0 = _parse_d(tokens[1])
        if csr >= csrs.FAST_CSR_COUNT:
            raise AssemblyError("fast CSR form can only encode CSR numbers 0x00-0x0F")
        return (csr, d0), (("CSR", csr), ("D", d0)), (4, 4)
    if binary_format == "D_CSR4_D":
        _require_operand_count(mnemonic, tokens, 3)
        d0 = _parse_d(tokens[0])
        csr = _parse_csr(tokens[1])
        d1 = _parse_d(tokens[2])
        if csr >= csrs.FAST_CSR_COUNT:
            raise AssemblyError("fast CSR form can only encode CSR numbers 0x00-0x0F")
        return (d0, csr, d1), (("D", d0), ("CSR", csr), ("D", d1)), (4, 4, 4)
    if binary_format == "D_CSR8":
        _require_operand_count(mnemonic, tokens, 2)
        d0 = _parse_d(tokens[0])
        csr = _parse_csr(tokens[1])
        return (d0, csr), (("D", d0), ("CSR", csr)), (4, 8)
    if binary_format == "CSR8_D":
        _require_operand_count(mnemonic, tokens, 2)
        csr = _parse_csr(tokens[0])
        d0 = _parse_d(tokens[1])
        return (csr, d0), (("CSR", csr), ("D", d0)), (8, 4)
    if binary_format == "D_CSR8_D":
        _require_operand_count(mnemonic, tokens, 3)
        d0 = _parse_d(tokens[0])
        csr = _parse_csr(tokens[1])
        d1 = _parse_d(tokens[2])
        return (d0, csr, d1), (("D", d0), ("CSR", csr), ("D", d1)), (4, 8, 4)
    if binary_format == "C_CCSR8":
        _require_operand_count(mnemonic, tokens, 2)
        c0 = _parse_c(tokens[0])
        ccsr = _parse_ccsr(tokens[1])
        return (c0, ccsr), (("C", c0), ("CCSR", ccsr)), (4, 8)
    if binary_format == "CCSR8_C":
        _require_operand_count(mnemonic, tokens, 2)
        ccsr = _parse_ccsr(tokens[0])
        c0 = _parse_c(tokens[1])
        return (ccsr, c0), (("CCSR", ccsr), ("C", c0)), (8, 4)
    raise AssertionError(f"unhandled binary format {binary_format!r}")


def _field_widths(binary_format: str) -> tuple[int, ...]:
    widths = {
        "OP12": (),
        "OP24": (),
        "D": (4,),
        "C": (4,),
        "D_D": (4, 4),
        "D_D_WIDTH_WF": (4, 4, 3, 1),
        "D_D_D_WIDTH_WF": (4, 4, 4, 3, 1),
        "D_D_WIDTH": (4, 4, 3),
        "D_CC": (4, 4),
        "D_D_CC": (4, 4, 4),
        "D_C_D": (4, 4, 4),
        "C_D_D": (4, 4, 4),
        "C_C_D": (4, 4, 4),
        "C_D_C": (4, 4, 4),
        "D_C_D_D": (4, 4, 4, 4),
        "C_C": (4, 4),
        "D_C": (4, 4),
        "C_C_C": (4, 4, 4),
        "TARGET24": (16,),
        "CC_TARGET": (4, 12),
        "C_D": (4, 4),
        "D_CSR4": (4, 4),
        "CSR4_D": (4, 4),
        "D_CSR4_D": (4, 4, 4),
        "D_CSR8": (4, 8),
        "CSR8_D": (8, 4),
        "D_CSR8_D": (4, 8, 4),
        "C_CCSR8": (4, 8),
        "CCSR8_C": (8, 4),
    }
    try:
        return widths[binary_format]
    except KeyError as exc:
        raise AssertionError(f"unhandled binary format {binary_format!r}") from exc


def _operands_from_values(
    binary_format: str,
    mnemonic: str,
    values: Sequence[int],
) -> tuple[tuple[object, ...], IntegerWidthCode, int]:
    width = DEFAULT_WIDTH_CODE
    write_code = DEFAULT_WRITE_CODE

    def d(index: int) -> tuple[str, int]:
        return ("D", _decode_d(values[index]))

    def c(index: int) -> tuple[str, int]:
        return ("C", _decode_c(values[index]))

    def condition(index: int) -> tuple[str, str]:
        return ("COND", _decode_condition(values[index]))

    if binary_format in {"OP12", "OP24"}:
        return (), width, write_code
    if binary_format == "D":
        return (d(0),), width, write_code
    if binary_format == "C":
        return (c(0),), width, write_code
    if binary_format == "D_D":
        return (d(0), d(1)), width, write_code
    if binary_format == "D_D_WIDTH_WF":
        width = _decode_width(values[2])
        write_code = _decode_write(values[3])
        return (d(0), d(1)), width, write_code
    if binary_format == "D_D_D_WIDTH_WF":
        width = _decode_width(values[3])
        write_code = _decode_write(values[4])
        return (d(0), d(1), d(2)), width, write_code
    if binary_format == "D_D_WIDTH":
        width = _decode_width(values[2])
        return (d(0), d(1)), width, write_code
    if binary_format == "D_CC":
        return (d(0), condition(1)), width, write_code
    if binary_format == "D_D_CC":
        return (d(0), d(1), condition(2)), width, write_code
    if binary_format == "D_C_D":
        return (d(0), c(1), d(2)), width, write_code
    if binary_format == "C_D_D":
        return (c(0), d(1), d(2)), width, write_code
    if binary_format == "C_C_D":
        return (c(0), c(1), d(2)), width, write_code
    if binary_format == "C_D_C":
        return (c(0), d(1), c(2)), width, write_code
    if binary_format == "D_C_D_D":
        return (d(0), c(1), d(2), d(3)), width, write_code
    if binary_format == "C_C":
        return (c(0), c(1)), width, write_code
    if binary_format == "D_C":
        return (d(0), c(1)), width, write_code
    if binary_format == "C_C_C":
        return (c(0), c(1), c(2)), width, write_code
    if binary_format == "TARGET24":
        return (("TARGET", values[0]),), width, write_code
    if binary_format == "CC_TARGET":
        return (condition(0), ("TARGET", values[1])), width, write_code
    if binary_format == "C_D":
        return (c(0), d(1)), width, write_code
    if binary_format in {"D_CSR4", "D_CSR8"}:
        return (d(0), ("CSR", values[1])), width, write_code
    if binary_format in {"CSR4_D", "CSR8_D"}:
        return (("CSR", values[0]), d(1)), width, write_code
    if binary_format in {"D_CSR4_D", "D_CSR8_D"}:
        return (d(0), ("CSR", values[1]), d(2)), width, write_code
    if binary_format == "C_CCSR8":
        return (c(0), ("CCSR", values[1])), width, write_code
    if binary_format == "CCSR8_C":
        return (("CCSR", values[0]), c(1)), width, write_code
    raise AssertionError(f"unhandled binary format {binary_format!r}")


def _pack_fields(values: Sequence[int], widths: Sequence[int], total_bits: int) -> int:
    if len(values) != len(widths):
        raise AssertionError("values and widths length mismatch")
    if sum(widths) > total_bits:
        raise AssemblyError("operand fields do not fit fixture format")
    shift = total_bits
    result = 0
    for value, width in zip(values, widths):
        value = _require_uint(value, width, "field")
        shift -= width
        result |= value << shift
    return result


def _unpack_fields(value: int, widths: Sequence[int], total_bits: int) -> tuple[tuple[int, ...], int]:
    if sum(widths) > total_bits:
        raise DecodeError("operand fields exceed fixture format")
    shift = total_bits
    values: list[int] = []
    for width in widths:
        shift -= width
        values.append((value >> shift) & ((1 << width) - 1))
    reserved_mask = (1 << shift) - 1 if shift else 0
    return tuple(values), value & reserved_mask


def _require_operand_count(mnemonic: str, operands: Sequence[str], expected: int) -> None:
    if len(operands) != expected:
        raise AssemblyError(f"{mnemonic} expects {expected} operands")


def _parse_d(token: str) -> int:
    normalized = token.strip().upper()
    if not normalized.startswith("D"):
        raise AssemblyError(f"expected integer register, got {token!r}")
    return state.require_integer_register_index(_parse_uint(normalized[1:], 4, "D register"))


def _parse_c(token: str) -> int:
    normalized = token.strip().upper()
    if not normalized.startswith("C"):
        raise AssemblyError(f"expected capability register, got {token!r}")
    return state.require_general_capability_register_index(_parse_uint(normalized[1:], 3, "C register"))


def _parse_condition(token: str) -> int:
    try:
        condition = opcodes.canonical_condition(token)
    except KeyError as exc:
        raise AssemblyError(str(exc)) from exc
    return CONDITION_TO_CODE[condition]


def _parse_csr(token: str) -> int:
    normalized = token.strip().upper()
    try:
        return _parse_uint(normalized, csrs.CSR_NUMBER_BITS, "CSR")
    except AssemblyError:
        try:
            return csrs.csr_number(normalized)
        except KeyError as exc:
            raise AssemblyError(str(exc)) from exc


def _parse_ccsr(token: str) -> int:
    normalized = token.strip().upper()
    try:
        return _parse_uint(normalized, 8, "CCSR")
    except AssemblyError:
        try:
            return state.SPECIAL_NAME_TO_CCSR_INDEX[normalized]
        except KeyError as exc:
            raise AssemblyError(f"unknown CCSR name {token!r}") from exc


def _parse_uint(token: str, bits: int, name: str) -> int:
    token = token.strip().replace("_", "")
    try:
        value = int(token, 0)
    except ValueError as exc:
        raise AssemblyError(f"{name} must be an integer") from exc
    return _require_uint(value, bits, name)


def _require_uint(value: int, bits: int, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if not 0 <= value < (1 << bits):
        raise AssemblyError(f"{name} must be in range [0, 2^{bits})")
    return value


def _decode_d(value: int) -> int:
    try:
        return state.require_integer_register_index(value)
    except (TypeError, IndexError) as exc:
        raise DecodeError(f"malformed integer register field D{value}") from exc


def _decode_c(value: int) -> int:
    try:
        return state.require_general_capability_register_index(value)
    except (TypeError, IndexError) as exc:
        raise DecodeError(f"malformed capability register field C{value}") from exc


def _decode_width(value: int) -> IntegerWidthCode:
    try:
        return IntegerWidthCode(value)
    except ValueError as exc:
        raise DecodeError(f"reserved integer width code {value}") from exc


def _decode_write(value: int) -> int:
    if value not in WRITE_CODE_TO_SUFFIX:
        raise DecodeError(f"reserved write-form code {value}")
    return value


def _decode_condition(value: int) -> str:
    try:
        return CODE_TO_CONDITION[value]
    except KeyError as exc:
        raise DecodeError(f"reserved condition code {value}") from exc


def _format_int(value: int) -> str:
    return f"0x{value:X}"


def _format_csr(value: int) -> str:
    try:
        return csrs.csr_name(value)
    except KeyError:
        return _format_int(value)


def _format_ccsr(value: int) -> str:
    try:
        return state.ccsr_name(value)
    except KeyError:
        return _format_int(value)

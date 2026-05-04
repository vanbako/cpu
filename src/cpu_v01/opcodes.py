"""Final mandatory opcode allocation for CPU v0.1.

Owner stories:
- E04-S01: instruction-size and placement rules.
- E04-S06: mandatory v0.1 opcode coverage contract.
- I07-S01: final mandatory opcode table.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping

from .instructions import InstructionSize


class PrivilegeClass(Enum):
    """Privilege class advertised by the opcode table."""

    USER = "U"
    KERNEL = "K"
    CSR_SPECIFIC = "CSR-specific"


@dataclass(frozen=True)
class OpcodeForm:
    """One canonical binary opcode form.

    The table fixes the opcode selector bits for each instruction-size class.
    Operand field layout is named here and is consumed by the assembler story.
    """

    mnemonic: str
    size: InstructionSize
    opcode_id: int
    fixed_mask: int
    fixed_value: int
    operand_format: str
    binary_format: str
    privilege: PrivilegeClass
    owner: str
    source_mnemonic: str = ""
    aliases: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mnemonic", normalize_mnemonic(self.mnemonic))
        object.__setattr__(self, "size", InstructionSize(self.size))
        object.__setattr__(self, "privilege", PrivilegeClass(self.privilege))
        object.__setattr__(
            self,
            "source_mnemonic",
            self.source_mnemonic or self.mnemonic,
        )
        object.__setattr__(
            self,
            "aliases",
            tuple(normalize_mnemonic(alias) for alias in self.aliases),
        )
        if not self.owner:
            raise ValueError("owner must not be empty")
        if not self.binary_format:
            raise ValueError("binary_format must not be empty")
        if not self.operand_format:
            raise ValueError("operand_format must not be empty")
        if self.fixed_value & ~self.fixed_mask:
            raise ValueError(f"{self.mnemonic} fixed bits outside fixed_mask")
        max_value = (1 << self.size.bits) - 1
        if self.fixed_mask < 0 or self.fixed_mask > max_value:
            raise ValueError(f"{self.mnemonic} fixed_mask does not fit size")
        if self.fixed_value < 0 or self.fixed_value > max_value:
            raise ValueError(f"{self.mnemonic} fixed_value does not fit size")

    @property
    def encoding_pattern(self) -> str:
        width = self.size.bits // 4
        known = f"{self.fixed_value:0{width}X}"
        if self.size is InstructionSize.BITS_12:
            return f"12'h{known}"
        if self.size is InstructionSize.BITS_24:
            return f"24'h{known[:2]}xxxx"
        return f"48'h{known[:2]}xxxxxxxxxx"


CONDITION_CODES: tuple[str, ...] = (
    "AL",
    "EQ",
    "NE",
    "CS",
    "HS",
    "CC",
    "LO",
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

CONDITION_ALIASES: Mapping[str, str] = MappingProxyType({"HS": "CS", "LO": "CC"})

EXCLUDED_MNEMONICS: tuple[str, ...] = (
    "CAS48",
    "CAS96",
    "FENCE.I.U",
)

EXCLUDED_PREFIXES: tuple[str, ...] = (
    "AMO",
    "DMA.TAG",
    "CACHE.IO",
)


def normalize_mnemonic(mnemonic: str) -> str:
    if not isinstance(mnemonic, str):
        raise TypeError("mnemonic must be a str")
    normalized = mnemonic.strip().upper()
    if not normalized:
        raise ValueError("mnemonic must not be empty")
    return normalized


def canonical_condition(condition: str) -> str:
    normalized = normalize_mnemonic(condition)
    if normalized not in CONDITION_CODES:
        raise KeyError(f"unknown condition code {condition!r}")
    return CONDITION_ALIASES.get(normalized, normalized)


def _form12(
    mnemonic: str,
    opcode: int,
    operand_format: str,
    privilege: PrivilegeClass,
    owner: str,
    *,
    source_mnemonic: str = "",
    aliases: tuple[str, ...] = (),
    summary: str = "",
) -> OpcodeForm:
    return OpcodeForm(
        mnemonic=mnemonic,
        size=InstructionSize.BITS_12,
        opcode_id=opcode,
        fixed_mask=0xFFF,
        fixed_value=opcode,
        operand_format=operand_format,
        binary_format="OP12",
        privilege=privilege,
        owner=owner,
        source_mnemonic=source_mnemonic,
        aliases=aliases,
        summary=summary,
    )


def _form24(
    mnemonic: str,
    major: int,
    operand_format: str,
    binary_format: str,
    privilege: PrivilegeClass,
    owner: str,
    *,
    source_mnemonic: str = "",
    aliases: tuple[str, ...] = (),
    summary: str = "",
) -> OpcodeForm:
    return OpcodeForm(
        mnemonic=mnemonic,
        size=InstructionSize.BITS_24,
        opcode_id=major,
        fixed_mask=0xFF0000,
        fixed_value=major << 16,
        operand_format=operand_format,
        binary_format=binary_format,
        privilege=privilege,
        owner=owner,
        source_mnemonic=source_mnemonic,
        aliases=aliases,
        summary=summary,
    )


def _form48(
    mnemonic: str,
    major: int,
    operand_format: str,
    binary_format: str,
    privilege: PrivilegeClass,
    owner: str,
    *,
    source_mnemonic: str = "",
    aliases: tuple[str, ...] = (),
    summary: str = "",
) -> OpcodeForm:
    return OpcodeForm(
        mnemonic=mnemonic,
        size=InstructionSize.BITS_48,
        opcode_id=major,
        fixed_mask=0xFF0000000000,
        fixed_value=major << 40,
        operand_format=operand_format,
        binary_format=binary_format,
        privilege=privilege,
        owner=owner,
        source_mnemonic=source_mnemonic,
        aliases=aliases,
        summary=summary,
    )


_INTEGER_FORMS: tuple[OpcodeForm, ...] = (
    _form24("CPY", 0x10, "Dd, Ds", "D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("NEG", 0x11, "Dd, Ds", "D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("ADD", 0x12, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("ADDU", 0x13, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("SUB", 0x14, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("SUBU", 0x15, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("MUL", 0x16, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("MULU", 0x17, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("DIV", 0x18, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("DIVU", 0x19, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("MOD", 0x1A, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("MODU", 0x1B, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("NOT", 0x1C, "Dd, Ds", "D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("AND", 0x1D, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("OR", 0x1E, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("XOR", 0x1F, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("SHL", 0x20, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("SHRS", 0x21, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("SHRU", 0x22, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("ROL", 0x23, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("ROR", 0x24, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("CMP", 0x25, "Da, Db", "D_D_WIDTH", PrivilegeClass.USER, "E04-S02"),
    _form24("CMPU", 0x26, "Da, Db", "D_D_WIDTH", PrivilegeClass.USER, "E04-S02"),
    _form24("TST", 0x27, "Da, Db", "D_D_WIDTH", PrivilegeClass.USER, "E04-S02"),
    _form24(
        "SETCC",
        0x28,
        "Dd, cc",
        "D_CC",
        PrivilegeClass.USER,
        "E04-S02",
        source_mnemonic="SETcc",
    ),
    _form24(
        "CMOVCC",
        0x29,
        "Dd, Ds, cc",
        "D_D_CC",
        PrivilegeClass.USER,
        "E04-S02",
        source_mnemonic="CMOVcc",
    ),
    _form24("BSET", 0x2A, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
    _form24("BCLR", 0x2B, "Dd, Da, Db", "D_D_D_WIDTH_WF", PrivilegeClass.USER, "E04-S02"),
)

_MEMORY_FORMS: tuple[OpcodeForm, ...] = (
    _form24("LD48", 0x30, "Dd, Ca, Di", "D_C_D", PrivilegeClass.USER, "E04-S03"),
    _form24("ST48", 0x31, "Ca, Di, Ds", "C_D_D", PrivilegeClass.USER, "E04-S03"),
    _form24("CLC", 0x32, "Cd, Ca, Di", "C_C_D", PrivilegeClass.USER, "E04-S03/E04-S05"),
    _form24("CSC", 0x33, "Ca, Di, Cs", "C_D_C", PrivilegeClass.USER, "E04-S03/E04-S05"),
    _form24("LL48", 0x34, "Dd, Ca, Di", "D_C_D", PrivilegeClass.USER, "E08-S01"),
    _form24("SC48", 0x35, "Dr, Ca, Di, Ds", "D_C_D_D", PrivilegeClass.USER, "E08-S01"),
)

_CAPABILITY_FORMS: tuple[OpcodeForm, ...] = (
    _form48("CMOVE", 0x40, "Cd, Cs", "C_C", PrivilegeClass.USER, "E04-S05"),
    _form48("CGETADDR", 0x41, "Dd, Cs", "D_C", PrivilegeClass.USER, "E04-S05"),
    _form48("CSETADDR", 0x42, "Cd, Cs, Da", "C_C_D", PrivilegeClass.USER, "E04-S05"),
    _form48("CINCADDR", 0x43, "Cd, Cs, Di", "C_C_D", PrivilegeClass.USER, "E04-S05"),
    _form48("CSETBOUNDS", 0x44, "Cd, Cs, Dlen", "C_C_D", PrivilegeClass.USER, "E04-S05"),
    _form48("CANDPERM", 0x45, "Cd, Cs, Dmask", "C_C_D", PrivilegeClass.USER, "E04-S05"),
    _form48("CSEAL", 0x46, "Cd, Cs, Cauth", "C_C_C", PrivilegeClass.USER, "E04-S05"),
    _form48("CUNSEAL", 0x47, "Cd, Cs, Cauth", "C_C_C", PrivilegeClass.USER, "E04-S05"),
)

_CONTROL_FORMS: tuple[OpcodeForm, ...] = (
    _form24("BRA", 0x50, "target", "TARGET24", PrivilegeClass.USER, "E04-S04"),
    _form24(
        "BCC",
        0x51,
        "cc, target",
        "CC_TARGET",
        PrivilegeClass.USER,
        "E04-S04",
        source_mnemonic="Bcc",
    ),
    _form24("CALL", 0x52, "target", "TARGET24", PrivilegeClass.USER, "E04-S04/E06-S03"),
    _form12("RET", 0x053, "none", PrivilegeClass.USER, "E04-S04/E06-S03"),
    _form24("JMP", 0x54, "Cs", "C", PrivilegeClass.USER, "E04-S04"),
    _form12("BRK", 0x055, "none", PrivilegeClass.USER, "E04-S04"),
    _form12(
        "SYS",
        0x056,
        "none",
        PrivilegeClass.USER,
        "E04-S04/E04-S06",
        aliases=("SCALL",),
    ),
    _form24("IRET", 0x57, "none", "OP24", PrivilegeClass.KERNEL, "E04-S04/E07-S06"),
    _form24("EPCCRD", 0x58, "Cd, Dd", "C_D", PrivilegeClass.KERNEL, "E04-S04"),
    _form24("EPCCWR", 0x59, "Cs, Ds", "C_D", PrivilegeClass.KERNEL, "E04-S04"),
    _form12("WFI", 0x05A, "none", PrivilegeClass.KERNEL, "E04-S04/E04-S06"),
    _form12("PAUSE", 0x05B, "none", PrivilegeClass.USER, "E04-S04/E04-S06"),
    _form24("CALLC", 0x5C, "Centry", "C", PrivilegeClass.USER, "E06-S02"),
)

_SYSTEM_FORMS: tuple[OpcodeForm, ...] = (
    _form24("FENCE", 0x60, "none", "OP24", PrivilegeClass.USER, "E08-S04"),
    _form24("FENCE.I", 0x61, "none", "OP24", PrivilegeClass.KERNEL, "E08-S04"),
    _form24("SFENCE.VM", 0x62, "none", "OP24", PrivilegeClass.KERNEL, "E08-S04"),
    _form24("SFENCE.VM.ASID", 0x63, "Dasid", "D", PrivilegeClass.KERNEL, "E08-S04"),
    _form24("SFENCE.VM.VA", 0x64, "Dva", "D", PrivilegeClass.KERNEL, "E08-S04"),
    _form24("SFENCE.VM.VA_ASID", 0x65, "Dva, Dasid", "D_D", PrivilegeClass.KERNEL, "E08-S04"),
    _form24("CSRRD", 0x66, "Dd, csr4", "D_CSR4", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form24("CSRWR", 0x67, "csr4, Ds", "CSR4_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form24("CSRSET", 0x68, "Dd, csr4, Ds", "D_CSR4_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form24("CSRCLR", 0x69, "Dd, csr4, Ds", "D_CSR4_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form48("CSRRD", 0x6A, "Dd, csr8", "D_CSR8", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form48("CSRWR", 0x6B, "csr8, Ds", "CSR8_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form48("CSRSET", 0x6C, "Dd, csr8, Ds", "D_CSR8_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form48("CSRCLR", 0x6D, "Dd, csr8, Ds", "D_CSR8_D", PrivilegeClass.CSR_SPECIFIC, "E02-S04"),
    _form48("CCSRRD", 0x70, "Cd, idx", "C_CCSR8", PrivilegeClass.KERNEL, "E02-S05"),
    _form48("CCSRWR", 0x71, "idx, Cs", "CCSR8_C", PrivilegeClass.KERNEL, "E02-S05"),
)

_CACHE_FORMS: tuple[OpcodeForm, ...] = (
    _form24("CACHE.CLEAN", 0x80, "Ca, Di, Dn", "C_D_D", PrivilegeClass.KERNEL, "E10-S05"),
    _form24("CACHE.INVAL", 0x81, "Ca, Di, Dn", "C_D_D", PrivilegeClass.KERNEL, "E10-S05"),
    _form24("CACHE.CLEANINVAL", 0x82, "Ca, Di, Dn", "C_D_D", PrivilegeClass.KERNEL, "E10-S05"),
)

OPCODE_FORMS: tuple[OpcodeForm, ...] = (
    *_INTEGER_FORMS,
    *_MEMORY_FORMS,
    *_CAPABILITY_FORMS,
    *_CONTROL_FORMS,
    *_SYSTEM_FORMS,
    *_CACHE_FORMS,
)

MANDATORY_MNEMONICS: tuple[str, ...] = tuple(
    dict.fromkeys(form.mnemonic for form in OPCODE_FORMS)
)

_FORMS_BY_MNEMONIC: Mapping[str, tuple[OpcodeForm, ...]] = MappingProxyType(
    {
        mnemonic: tuple(form for form in OPCODE_FORMS if form.mnemonic == mnemonic)
        for mnemonic in MANDATORY_MNEMONICS
    }
)

_ALIAS_TO_CANONICAL: Mapping[str, str] = MappingProxyType(
    {
        alias: form.mnemonic
        for form in OPCODE_FORMS
        for alias in form.aliases
    }
)


def all_opcode_forms() -> tuple[OpcodeForm, ...]:
    return OPCODE_FORMS


def mandatory_mnemonics() -> tuple[str, ...]:
    return MANDATORY_MNEMONICS


def canonical_mnemonic(mnemonic: str) -> str:
    normalized = normalize_mnemonic(mnemonic)
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


def opcode_forms_for(mnemonic: str) -> tuple[OpcodeForm, ...]:
    canonical = canonical_mnemonic(mnemonic)
    if is_excluded_mnemonic(canonical):
        raise KeyError(f"{mnemonic!r} is excluded from mandatory CPU v0.1")
    try:
        return _FORMS_BY_MNEMONIC[canonical]
    except KeyError as exc:
        raise KeyError(f"unknown mandatory CPU v0.1 mnemonic {mnemonic!r}") from exc


def opcode_form_for(mnemonic: str) -> OpcodeForm:
    forms = opcode_forms_for(mnemonic)
    if len(forms) != 1:
        raise ValueError(f"{mnemonic!r} has {len(forms)} opcode forms")
    return forms[0]


def is_excluded_mnemonic(mnemonic: str) -> bool:
    normalized = normalize_mnemonic(mnemonic)
    return normalized in EXCLUDED_MNEMONICS or any(
        normalized.startswith(prefix) for prefix in EXCLUDED_PREFIXES
    )


def missing_mandatory_mnemonics(required: Iterable[str]) -> tuple[str, ...]:
    missing: list[str] = []
    for mnemonic in required:
        canonical = canonical_mnemonic(mnemonic)
        if canonical not in _FORMS_BY_MNEMONIC:
            missing.append(normalize_mnemonic(mnemonic))
    return tuple(missing)


def validate_opcode_table() -> tuple[str, ...]:
    issues: list[str] = []
    seen_encodings: dict[tuple[InstructionSize, int], str] = {}
    seen_fixed: dict[tuple[InstructionSize, int, int], str] = {}
    canonical_names = set(_FORMS_BY_MNEMONIC)

    for form in OPCODE_FORMS:
        if form.opcode_id < 0 or form.opcode_id > 0xFF:
            issues.append(f"{form.mnemonic} opcode_id is outside the 8-bit selector space")
        selector_key = (form.size, form.opcode_id)
        if selector_key in seen_encodings:
            issues.append(
                f"{form.mnemonic} collides with {seen_encodings[selector_key]} "
                f"on selector {form.size.bits}:{form.opcode_id:02X}"
            )
        seen_encodings[selector_key] = form.mnemonic

        fixed_key = (form.size, form.fixed_mask, form.fixed_value)
        if fixed_key in seen_fixed:
            issues.append(
                f"{form.mnemonic} fixed encoding collides with {seen_fixed[fixed_key]}"
            )
        seen_fixed[fixed_key] = form.mnemonic

        if form.size is InstructionSize.BITS_48 and not form.size.is_legal_start(0, 0):
            issues.append(f"{form.mnemonic} has no legal 48-bit placement")
        if form.size is InstructionSize.BITS_24 and not form.size.is_legal_start(1, 0):
            issues.append(f"{form.mnemonic} has no legal 24-bit placement")
        if form.size is InstructionSize.BITS_12 and not form.size.is_legal_start(1, 1):
            issues.append(f"{form.mnemonic} has no legal 12-bit placement")

    for alias, target in _ALIAS_TO_CANONICAL.items():
        if target not in canonical_names:
            issues.append(f"alias {alias} targets missing canonical mnemonic {target}")
        if alias in canonical_names:
            issues.append(f"alias {alias} also appears as a canonical mnemonic")

    for mnemonic in EXCLUDED_MNEMONICS:
        if mnemonic in canonical_names or mnemonic in _ALIAS_TO_CANONICAL:
            issues.append(f"excluded mnemonic {mnemonic} is present in opcode table")
    for prefix in EXCLUDED_PREFIXES:
        for form in OPCODE_FORMS:
            if form.mnemonic.startswith(prefix):
                issues.append(f"excluded family {prefix} includes {form.mnemonic}")
            for alias in form.aliases:
                if alias.startswith(prefix):
                    issues.append(f"excluded family {prefix} includes alias {alias}")

    return tuple(issues)

"""Firmware/kernel ABI supplement constants for CPU v0.1.

Owner stories:
- E05-S01/E05-S02: integer and capability calling convention save sets.
- E07-S06: nested trap-frame requirements.
- E15-S06: software-facing ABI contract audit.
- I09-S01: trap-frame and context-switch ABI supplement.
- I09-S02: language ABI argument, return, and spill supplement.
- I09-S03: baseline syscall ABI supplement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping

from .cells import CAPABILITY_OBJECT_CELLS, INTEGER_OBJECT_CELLS
from .state import (
    GENERAL_CAPABILITY_REGISTER_COUNT,
    INTEGER_REGISTER_COUNT,
    SPECIAL_CAPABILITY_NAMES,
)


INTEGER_ARGUMENT_REGS = tuple(range(0, 6))
INTEGER_RETURN_REGS = (0, 1)
INTEGER_CALLER_SAVED_REGS = tuple(range(0, 12))
INTEGER_CALLEE_SAVED_REGS = tuple(range(12, 16))

CAPABILITY_ARGUMENT_REGS = tuple(range(0, 4))
CAPABILITY_RETURN_REGS = (0,)
CAPABILITY_CALLER_SAVED_REGS = tuple(range(0, 6))
CAPABILITY_CALLEE_SAVED_REGS = tuple(range(6, 8))

CONTEXT_SWITCH_INTEGER_REGS = tuple(range(INTEGER_REGISTER_COUNT))
CONTEXT_SWITCH_CAPABILITY_REGS = tuple(range(GENERAL_CAPABILITY_REGISTER_COUNT))
CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS = SPECIAL_CAPABILITY_NAMES

NESTED_TRAP_RESTORE_SEQUENCE = (
    "restore reporting CSRs if required",
    "EPCCWR Cs, Ds",
    "restore SR.PIE/SR.PPRIV",
    "IRET",
)

TRAP_RETURN_TEST_SCENARIOS = (
    "slot0_iret_restore",
    "slot1_iret_restore",
    "nested_frame_restores_epcc_slot",
    "iret_fault_has_no_partial_restore",
)


class AbiFieldKind(Enum):
    INTEGER = "INTEGER"
    CAPABILITY = "CAPABILITY"
    CONTROL = "CONTROL"


class AbiValueKind(Enum):
    INTEGER = "INTEGER"
    CAPABILITY = "CAPABILITY"


class AbiLocationKind(Enum):
    INTEGER_REGISTER = "INTEGER_REGISTER"
    CAPABILITY_REGISTER = "CAPABILITY_REGISTER"
    STACK = "STACK"


INTEGER_ABI_SLOT_CELLS = INTEGER_OBJECT_CELLS
CAPABILITY_ABI_SLOT_CELLS = CAPABILITY_OBJECT_CELLS
PUBLIC_STACK_ALIGNMENT_CELLS = CAPABILITY_OBJECT_CELLS

INTEGER_SPILL_STORE = "ST48"
INTEGER_SPILL_LOAD = "LD48"
CAPABILITY_SPILL_STORE = "CSC"
CAPABILITY_SPILL_LOAD = "CLC"

SYSCALL_CANONICAL_MNEMONIC = "SYS"
SYSCALL_SOURCE_SYNONYMS = ("SCALL",)
SYSCALL_TRAP_CAUSE = "SYSCALL_TRAP"
SYSCALL_SERVICE_REGISTER = 0
SYSCALL_INTEGER_ARGUMENT_REGS = tuple(range(1, 6))
SYSCALL_INTEGER_RETURN_REGS = INTEGER_RETURN_REGS
SYSCALL_CAPABILITY_ARGUMENT_REGS = CAPABILITY_ARGUMENT_REGS
SYSCALL_CAPABILITY_RETURN_REGS = CAPABILITY_RETURN_REGS
SYSCALL_VOLATILE_INTEGER_REGS = INTEGER_CALLER_SAVED_REGS
SYSCALL_VOLATILE_CAPABILITY_REGS = CAPABILITY_CALLER_SAVED_REGS


@dataclass(frozen=True)
class TrapFrameField:
    name: str
    offset_cells: int
    size_cells: int
    alignment_cells: int
    kind: AbiFieldKind
    description: str

    @property
    def end_cells(self) -> int:
        return self.offset_cells + self.size_cells

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("field name must not be empty")
        if self.offset_cells < 0:
            raise ValueError("offset_cells must be nonnegative")
        if self.size_cells <= 0:
            raise ValueError("size_cells must be positive")
        if self.alignment_cells <= 0:
            raise ValueError("alignment_cells must be positive")
        object.__setattr__(self, "kind", AbiFieldKind(self.kind))
        if self.offset_cells % self.alignment_cells != 0:
            raise ValueError(f"{self.name} is not aligned")


@dataclass(frozen=True)
class AbiArgumentLocation:
    argument_index: int
    value_kind: AbiValueKind
    location_kind: AbiLocationKind
    register_index: int | None
    offset_cells: int | None
    size_cells: int
    alignment_cells: int
    tag_required: bool

    @property
    def end_cells(self) -> int | None:
        if self.offset_cells is None:
            return None
        return self.offset_cells + self.size_cells

    @property
    def is_stack(self) -> bool:
        return self.location_kind is AbiLocationKind.STACK

    def __post_init__(self) -> None:
        if self.argument_index < 0:
            raise ValueError("argument_index must be nonnegative")
        object.__setattr__(self, "value_kind", AbiValueKind(self.value_kind))
        object.__setattr__(self, "location_kind", AbiLocationKind(self.location_kind))
        if self.size_cells <= 0:
            raise ValueError("size_cells must be positive")
        if self.alignment_cells <= 0:
            raise ValueError("alignment_cells must be positive")
        if self.location_kind is AbiLocationKind.STACK:
            if self.register_index is not None:
                raise ValueError("stack locations must not name a register")
            if self.offset_cells is None or self.offset_cells < 0:
                raise ValueError("stack locations require a nonnegative offset")
            if self.offset_cells % self.alignment_cells:
                raise ValueError("stack argument offset is not aligned")
        else:
            if self.offset_cells is not None:
                raise ValueError("register locations must not name a stack offset")
            if self.register_index is None:
                raise ValueError("register locations require a register index")
            if self.location_kind is AbiLocationKind.INTEGER_REGISTER:
                if self.value_kind is not AbiValueKind.INTEGER:
                    raise ValueError("integer registers can only hold integer ABI arguments")
                if self.register_index not in INTEGER_ARGUMENT_REGS:
                    raise ValueError("integer argument register is outside D0-D5")
            if self.location_kind is AbiLocationKind.CAPABILITY_REGISTER:
                if self.value_kind is not AbiValueKind.CAPABILITY:
                    raise ValueError("capability registers can only hold capability ABI arguments")
                if self.register_index not in CAPABILITY_ARGUMENT_REGS:
                    raise ValueError("capability argument register is outside C0-C3")


@dataclass(frozen=True)
class AbiCallLayout:
    locations: tuple[AbiArgumentLocation, ...]
    overflow_size_cells: int

    @property
    def stack_locations(self) -> tuple[AbiArgumentLocation, ...]:
        return tuple(location for location in self.locations if location.is_stack)

    def location_for_argument(self, argument_index: int) -> AbiArgumentLocation:
        for location in self.locations:
            if location.argument_index == argument_index:
                return location
        raise KeyError(f"unknown ABI argument index {argument_index}")

    def __post_init__(self) -> None:
        if self.overflow_size_cells < 0:
            raise ValueError("overflow_size_cells must be nonnegative")
        if self.overflow_size_cells % PUBLIC_STACK_ALIGNMENT_CELLS:
            raise ValueError("overflow area must preserve public stack alignment")
        seen: set[int] = set()
        occupied: dict[int, int] = {}
        for location in self.locations:
            if location.argument_index in seen:
                raise ValueError("duplicate ABI argument location")
            seen.add(location.argument_index)
            if location.is_stack:
                assert location.offset_cells is not None
                assert location.end_cells is not None
                for cell in range(location.offset_cells, location.end_cells):
                    if cell in occupied:
                        raise ValueError("overlapping ABI stack argument slots")
                    occupied[cell] = location.argument_index
                if location.end_cells > self.overflow_size_cells:
                    raise ValueError("ABI stack argument exceeds overflow area")


TRAP_FRAME_FIELDS = (
    TrapFrameField(
        "EPCC",
        0,
        CAPABILITY_OBJECT_CELLS,
        CAPABILITY_OBJECT_CELLS,
        AbiFieldKind.CAPABILITY,
        "Captured execution capability payload and tag.",
    ),
    TrapFrameField(
        "EPCC_SLOT",
        4,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Captured hidden EPCC slot saved by EPCCRD and restored by EPCCWR.",
    ),
    TrapFrameField(
        "SR",
        6,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Saved status word, including PIE and PPRIV for IRET policy.",
    ),
    TrapFrameField(
        "CAUSE",
        8,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Trap or interrupt cause.",
    ),
    TrapFrameField(
        "TVAL",
        10,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Trap value.",
    ),
    TrapFrameField(
        "CAPCAUSE",
        12,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Capability-specific fault reason.",
    ),
    TrapFrameField(
        "FAULTCAPIDX",
        14,
        INTEGER_OBJECT_CELLS,
        INTEGER_OBJECT_CELLS,
        AbiFieldKind.CONTROL,
        "Capability operand index associated with a capability fault.",
    ),
)

TRAP_FRAME_FIELD_BY_NAME: Mapping[str, TrapFrameField] = MappingProxyType(
    {field.name: field for field in TRAP_FRAME_FIELDS}
)

TRAP_FRAME_SIZE_CELLS = max(field.end_cells for field in TRAP_FRAME_FIELDS)
TRAP_FRAME_ALIGNMENT_CELLS = CAPABILITY_OBJECT_CELLS


def trap_frame_field(name: str) -> TrapFrameField:
    normalized = name.upper()
    try:
        return TRAP_FRAME_FIELD_BY_NAME[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown trap-frame field {name!r}") from exc


def _align_up(value: int, alignment_cells: int) -> int:
    return value + ((alignment_cells - (value % alignment_cells)) % alignment_cells)


def _value_kind(value: AbiValueKind | str) -> AbiValueKind:
    return AbiValueKind(value)


def _slot_size_cells(kind: AbiValueKind) -> int:
    if kind is AbiValueKind.INTEGER:
        return INTEGER_ABI_SLOT_CELLS
    return CAPABILITY_ABI_SLOT_CELLS


def _slot_alignment_cells(kind: AbiValueKind) -> int:
    if kind is AbiValueKind.INTEGER:
        return INTEGER_ABI_SLOT_CELLS
    return CAPABILITY_ABI_SLOT_CELLS


def _layout_arguments(
    arguments: Iterable[AbiValueKind | str],
    *,
    integer_registers: tuple[int, ...],
    capability_registers: tuple[int, ...],
) -> AbiCallLayout:
    locations: list[AbiArgumentLocation] = []
    integer_count = 0
    capability_count = 0
    overflow_offset = 0

    for argument_index, raw_kind in enumerate(arguments):
        kind = _value_kind(raw_kind)
        size_cells = _slot_size_cells(kind)
        alignment_cells = _slot_alignment_cells(kind)
        if kind is AbiValueKind.INTEGER and integer_count < len(integer_registers):
            locations.append(
                AbiArgumentLocation(
                    argument_index=argument_index,
                    value_kind=kind,
                    location_kind=AbiLocationKind.INTEGER_REGISTER,
                    register_index=integer_registers[integer_count],
                    offset_cells=None,
                    size_cells=size_cells,
                    alignment_cells=alignment_cells,
                    tag_required=False,
                )
            )
            integer_count += 1
            continue
        if kind is AbiValueKind.CAPABILITY and capability_count < len(capability_registers):
            locations.append(
                AbiArgumentLocation(
                    argument_index=argument_index,
                    value_kind=kind,
                    location_kind=AbiLocationKind.CAPABILITY_REGISTER,
                    register_index=capability_registers[capability_count],
                    offset_cells=None,
                    size_cells=size_cells,
                    alignment_cells=alignment_cells,
                    tag_required=True,
                )
            )
            capability_count += 1
            continue

        if kind is AbiValueKind.INTEGER:
            integer_count += 1
        else:
            capability_count += 1
        overflow_offset = _align_up(overflow_offset, alignment_cells)
        locations.append(
            AbiArgumentLocation(
                argument_index=argument_index,
                value_kind=kind,
                location_kind=AbiLocationKind.STACK,
                register_index=None,
                offset_cells=overflow_offset,
                size_cells=size_cells,
                alignment_cells=alignment_cells,
                tag_required=kind is AbiValueKind.CAPABILITY,
            )
        )
        overflow_offset += size_cells

    return AbiCallLayout(
        locations=tuple(locations),
        overflow_size_cells=_align_up(overflow_offset, PUBLIC_STACK_ALIGNMENT_CELLS),
    )


def layout_language_arguments(arguments: Iterable[AbiValueKind | str]) -> AbiCallLayout:
    """Assign mixed language ABI arguments to registers and stack slots."""

    return _layout_arguments(
        arguments,
        integer_registers=INTEGER_ARGUMENT_REGS,
        capability_registers=CAPABILITY_ARGUMENT_REGS,
    )


def layout_syscall_arguments(arguments: Iterable[AbiValueKind | str]) -> AbiCallLayout:
    """Assign mixed syscall arguments after the D0 service-number register."""

    return _layout_arguments(
        arguments,
        integer_registers=SYSCALL_INTEGER_ARGUMENT_REGS,
        capability_registers=SYSCALL_CAPABILITY_ARGUMENT_REGS,
    )


def validate_trap_frame_layout(fields: Iterable[TrapFrameField] = TRAP_FRAME_FIELDS) -> tuple[str, ...]:
    issues: list[str] = []
    field_tuple = tuple(fields)
    occupied: dict[int, str] = {}
    for field in field_tuple:
        if field.offset_cells % field.alignment_cells != 0:
            issues.append(f"{field.name} is not {field.alignment_cells}-cell aligned")
        for cell in range(field.offset_cells, field.end_cells):
            if cell in occupied:
                issues.append(f"{field.name} overlaps {occupied[cell]} at cell {cell}")
            occupied[cell] = field.name
    names = {field.name for field in field_tuple}
    for required in ("EPCC", "EPCC_SLOT", "SR", "CAUSE", "TVAL", "CAPCAUSE", "FAULTCAPIDX"):
        if required not in names:
            issues.append(f"missing required trap-frame field {required}")
    if TRAP_FRAME_SIZE_CELLS % TRAP_FRAME_ALIGNMENT_CELLS != 0:
        issues.append("trap-frame size does not preserve ABI stack alignment")
    return tuple(issues)


def validate_context_switch_save_sets() -> tuple[str, ...]:
    issues: list[str] = []
    if CONTEXT_SWITCH_INTEGER_REGS != tuple(range(INTEGER_REGISTER_COUNT)):
        issues.append("context switch must save D0-D15")
    if CONTEXT_SWITCH_CAPABILITY_REGS != tuple(range(GENERAL_CAPABILITY_REGISTER_COUNT)):
        issues.append("context switch must save C0-C7")
    if CONTEXT_SWITCH_SPECIAL_CAPABILITY_REGS != SPECIAL_CAPABILITY_NAMES:
        issues.append("context switch must save every special capability register")
    if "EPCCWR Cs, Ds" not in NESTED_TRAP_RESTORE_SEQUENCE:
        issues.append("nested trap restore must use EPCCWR to preserve EPCC.slot")
    if "IRET" != NESTED_TRAP_RESTORE_SEQUENCE[-1]:
        issues.append("nested trap restore sequence must end with IRET")
    return tuple(issues)


def validate_language_abi_profile() -> tuple[str, ...]:
    issues: list[str] = []
    if INTEGER_ABI_SLOT_CELLS != INTEGER_OBJECT_CELLS:
        issues.append("integer ABI slots must be 2 cells")
    if CAPABILITY_ABI_SLOT_CELLS != CAPABILITY_OBJECT_CELLS:
        issues.append("capability ABI slots must be 4 cells")
    if PUBLIC_STACK_ALIGNMENT_CELLS != CAPABILITY_OBJECT_CELLS:
        issues.append("public stack alignment must be 4 cells")
    if CAPABILITY_SPILL_STORE != "CSC" or CAPABILITY_SPILL_LOAD != "CLC":
        issues.append("capability spills must use CSC/CLC")
    if INTEGER_SPILL_STORE != "ST48" or INTEGER_SPILL_LOAD != "LD48":
        issues.append("integer spills must use ST48/LD48")

    integer_layout = layout_language_arguments([AbiValueKind.INTEGER] * 7)
    seventh_integer = integer_layout.location_for_argument(6)
    if not seventh_integer.is_stack or seventh_integer.offset_cells != 0:
        issues.append("seventh integer argument must start at overflow slot 0")

    capability_layout = layout_language_arguments([AbiValueKind.CAPABILITY] * 5)
    fifth_capability = capability_layout.location_for_argument(4)
    if not fifth_capability.is_stack or fifth_capability.offset_cells != 0 or not fifth_capability.tag_required:
        issues.append("fifth capability argument must start at a tagged overflow slot")

    if integer_layout.overflow_size_cells % PUBLIC_STACK_ALIGNMENT_CELLS:
        issues.append("integer overflow area must preserve public stack alignment")
    if capability_layout.overflow_size_cells % PUBLIC_STACK_ALIGNMENT_CELLS:
        issues.append("capability overflow area must preserve public stack alignment")
    return tuple(issues)


def validate_syscall_abi_profile() -> tuple[str, ...]:
    issues: list[str] = []
    if SYSCALL_CANONICAL_MNEMONIC != "SYS":
        issues.append("SYS must be the canonical syscall mnemonic")
    if SYSCALL_SOURCE_SYNONYMS != ("SCALL",):
        issues.append("SCALL must remain a syscall source synonym")
    if SYSCALL_TRAP_CAUSE != "SYSCALL_TRAP":
        issues.append("syscall instructions must report SYSCALL_TRAP")
    if SYSCALL_SERVICE_REGISTER != 0:
        issues.append("syscall service number must be passed in D0")
    if SYSCALL_INTEGER_ARGUMENT_REGS != (1, 2, 3, 4, 5):
        issues.append("integer syscall arguments must use D1-D5 before overflow")
    if SYSCALL_INTEGER_RETURN_REGS != INTEGER_RETURN_REGS:
        issues.append("integer syscall returns must use D0-D1")
    if SYSCALL_CAPABILITY_ARGUMENT_REGS != CAPABILITY_ARGUMENT_REGS:
        issues.append("capability syscall arguments must use C0-C3 before overflow")
    if SYSCALL_CAPABILITY_RETURN_REGS != CAPABILITY_RETURN_REGS:
        issues.append("capability syscall returns must use C0")
    if SYSCALL_VOLATILE_INTEGER_REGS != INTEGER_CALLER_SAVED_REGS:
        issues.append("syscalls must treat D0-D11 as volatile")
    if SYSCALL_VOLATILE_CAPABILITY_REGS != CAPABILITY_CALLER_SAVED_REGS:
        issues.append("syscalls must treat C0-C5 as volatile")

    integer_layout = layout_syscall_arguments([AbiValueKind.INTEGER] * 6)
    register_locations = integer_layout.locations[:5]
    if tuple(location.register_index for location in register_locations) != SYSCALL_INTEGER_ARGUMENT_REGS:
        issues.append("first five integer syscall arguments must use D1-D5")
    sixth_integer = integer_layout.location_for_argument(5)
    if not sixth_integer.is_stack or sixth_integer.offset_cells != 0:
        issues.append("sixth integer syscall argument must use overflow slot 0")

    capability_layout = layout_syscall_arguments([AbiValueKind.CAPABILITY] * 5)
    fifth_capability = capability_layout.location_for_argument(4)
    if not fifth_capability.is_stack or fifth_capability.offset_cells != 0 or not fifth_capability.tag_required:
        issues.append("fifth capability syscall argument must use a tagged overflow slot")
    return tuple(issues)

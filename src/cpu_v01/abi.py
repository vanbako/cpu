"""Firmware/kernel ABI supplement constants for CPU v0.1.

Owner stories:
- E05-S01/E05-S02: integer and capability calling convention save sets.
- E07-S06: nested trap-frame requirements.
- E15-S06: software-facing ABI contract audit.
- I09-S01: trap-frame and context-switch ABI supplement.
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

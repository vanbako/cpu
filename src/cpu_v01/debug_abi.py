"""Debugger register view and protected unwind ABI profile for CPU v0.1.

Owner stories:
- E05-S04: protected return-stack storage and debug unwind constraints.
- E12-S01/E12-S03: debug halt, monitor, resume, and single-step state.
- E15-S06: software-facing debug and unwind contract audit.
- I09-S04: debugger register access and unwind supplement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from . import csrs
from .capabilities import OTYPE_RETURN
from .cells import CAPABILITY_OBJECT_CELLS
from .state import (
    GENERAL_CAPABILITY_REGISTER_COUNT,
    INTEGER_REGISTER_COUNT,
    SPECIAL_CAPABILITY_NAMES,
    SPECIAL_NAME_TO_CCSR_INDEX,
    SLOTTED_SPECIAL_CAPABILITY_NAMES,
    CoreLifecycle,
)


class DebugRegisterClass(Enum):
    INTEGER = "INTEGER"
    CAPABILITY = "CAPABILITY"
    SPECIAL_CAPABILITY = "SPECIAL_CAPABILITY"
    CSR = "CSR"


class DebugUnwindOperation(Enum):
    PEEK = "PEEK"
    DROP = "DROP"
    REPLACE = "REPLACE"


DEBUG_DIRECT_REGISTER_ACCESS_LIFECYCLES = (CoreLifecycle.DEBUG_HALTED,)
DEBUG_READONLY_CSR_NAMES = ("COREID", "TIMER")
RETURN_STACK_ENTRY_CELLS = CAPABILITY_OBJECT_CELLS
DEBUG_RETURN_REPLACEMENT_OTYPE = OTYPE_RETURN


@dataclass(frozen=True)
class DebugRegisterView:
    name: str
    register_class: DebugRegisterClass
    index: int
    readable: bool
    writable: bool
    tag_visible: bool
    slot_visible: bool

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("debug register name must not be empty")
        object.__setattr__(self, "register_class", DebugRegisterClass(self.register_class))
        if type(self.index) is not int or self.index < 0:
            raise ValueError("debug register index must be a nonnegative int")
        if self.register_class is DebugRegisterClass.INTEGER:
            if not self.name.startswith("D") or self.tag_visible or self.slot_visible:
                raise ValueError("integer debug registers expose only 48-bit payload state")
        if self.register_class is DebugRegisterClass.CAPABILITY:
            if not self.name.startswith("C") or not self.tag_visible or self.slot_visible:
                raise ValueError("general capability debug registers expose payload and tag")
        if self.register_class is DebugRegisterClass.SPECIAL_CAPABILITY:
            if not self.tag_visible:
                raise ValueError("special capability debug registers must expose tags")
            if self.slot_visible != (self.name in SLOTTED_SPECIAL_CAPABILITY_NAMES):
                raise ValueError("only PCC and EPCC expose hidden slot state")
        if self.register_class is DebugRegisterClass.CSR:
            if self.tag_visible or self.slot_visible:
                raise ValueError("scalar CSR debug registers expose only scalar payload state")


@dataclass(frozen=True)
class DebugUnwindRule:
    operation: DebugUnwindOperation
    updates_rsc_cursor: bool
    writes_return_slot: bool
    requires_valid_return_capability: bool
    atomic_payload_tag: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", DebugUnwindOperation(self.operation))
        if self.operation is DebugUnwindOperation.REPLACE:
            if not self.writes_return_slot or not self.requires_valid_return_capability:
                raise ValueError("return-stack replace must write a valid return capability")
            if not self.atomic_payload_tag:
                raise ValueError("return-stack replace must update payload and tag atomically")
        if self.operation is DebugUnwindOperation.DROP and not self.updates_rsc_cursor:
            raise ValueError("return-stack drop must update RSC.cursor")
        if self.operation is DebugUnwindOperation.PEEK and self.updates_rsc_cursor:
            raise ValueError("return-stack peek must not update RSC.cursor")


def _build_register_views() -> tuple[DebugRegisterView, ...]:
    views: list[DebugRegisterView] = []
    for index in range(INTEGER_REGISTER_COUNT):
        views.append(
            DebugRegisterView(
                name=f"D{index}",
                register_class=DebugRegisterClass.INTEGER,
                index=index,
                readable=True,
                writable=True,
                tag_visible=False,
                slot_visible=False,
            )
        )
    for index in range(GENERAL_CAPABILITY_REGISTER_COUNT):
        views.append(
            DebugRegisterView(
                name=f"C{index}",
                register_class=DebugRegisterClass.CAPABILITY,
                index=index,
                readable=True,
                writable=True,
                tag_visible=True,
                slot_visible=False,
            )
        )
    for name in SPECIAL_CAPABILITY_NAMES:
        views.append(
            DebugRegisterView(
                name=name,
                register_class=DebugRegisterClass.SPECIAL_CAPABILITY,
                index=SPECIAL_NAME_TO_CCSR_INDEX[name],
                readable=True,
                writable=True,
                tag_visible=True,
                slot_visible=name in SLOTTED_SPECIAL_CAPABILITY_NAMES,
            )
        )
    for number, name in sorted(csrs.ASSIGNED_CSR_NUMBER_TO_NAME.items()):
        views.append(
            DebugRegisterView(
                name=name,
                register_class=DebugRegisterClass.CSR,
                index=number,
                readable=True,
                writable=name not in DEBUG_READONLY_CSR_NAMES,
                tag_visible=False,
                slot_visible=False,
            )
        )
    return tuple(views)


DEBUG_REGISTER_VIEWS = _build_register_views()
DEBUG_REGISTER_VIEW_BY_NAME: Mapping[str, DebugRegisterView] = MappingProxyType(
    {view.name: view for view in DEBUG_REGISTER_VIEWS}
)

DEBUG_UNWIND_RULES = (
    DebugUnwindRule(
        operation=DebugUnwindOperation.PEEK,
        updates_rsc_cursor=False,
        writes_return_slot=False,
        requires_valid_return_capability=True,
        atomic_payload_tag=True,
    ),
    DebugUnwindRule(
        operation=DebugUnwindOperation.DROP,
        updates_rsc_cursor=True,
        writes_return_slot=False,
        requires_valid_return_capability=True,
        atomic_payload_tag=True,
    ),
    DebugUnwindRule(
        operation=DebugUnwindOperation.REPLACE,
        updates_rsc_cursor=False,
        writes_return_slot=True,
        requires_valid_return_capability=True,
        atomic_payload_tag=True,
    ),
)
DEBUG_UNWIND_RULE_BY_OPERATION: Mapping[DebugUnwindOperation, DebugUnwindRule] = MappingProxyType(
    {rule.operation: rule for rule in DEBUG_UNWIND_RULES}
)


def debug_register_view(name: str) -> DebugRegisterView:
    if not isinstance(name, str):
        raise TypeError("debug register name must be a str")
    normalized = name.upper()
    try:
        return DEBUG_REGISTER_VIEW_BY_NAME[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown debug register {name!r}") from exc


def debug_register_views(register_class: DebugRegisterClass | str) -> tuple[DebugRegisterView, ...]:
    register_class = DebugRegisterClass(register_class)
    return tuple(view for view in DEBUG_REGISTER_VIEWS if view.register_class is register_class)


def direct_register_access_allowed(lifecycle: CoreLifecycle | str) -> bool:
    lifecycle = CoreLifecycle(lifecycle)
    return lifecycle in DEBUG_DIRECT_REGISTER_ACCESS_LIFECYCLES


def debug_unwind_rule(operation: DebugUnwindOperation | str) -> DebugUnwindRule:
    operation = DebugUnwindOperation(operation)
    return DEBUG_UNWIND_RULE_BY_OPERATION[operation]


def validate_debug_abi_profile() -> tuple[str, ...]:
    issues: list[str] = []
    if len(debug_register_views(DebugRegisterClass.INTEGER)) != INTEGER_REGISTER_COUNT:
        issues.append("debug view must expose D0-D15")
    if len(debug_register_views(DebugRegisterClass.CAPABILITY)) != GENERAL_CAPABILITY_REGISTER_COUNT:
        issues.append("debug view must expose C0-C7")
    special_names = tuple(view.name for view in debug_register_views(DebugRegisterClass.SPECIAL_CAPABILITY))
    if special_names != SPECIAL_CAPABILITY_NAMES:
        issues.append("debug view must expose every special capability register")
    csr_names = {view.name for view in debug_register_views(DebugRegisterClass.CSR)}
    if set(csrs.ASSIGNED_CSR_NUMBER_TO_NAME.values()) - csr_names:
        issues.append("debug view must expose every assigned scalar CSR")
    for name in SLOTTED_SPECIAL_CAPABILITY_NAMES:
        if not debug_register_view(name).slot_visible:
            issues.append(f"{name} debug view must expose hidden slot state")
    if direct_register_access_allowed(CoreLifecycle.RUNNING):
        issues.append("direct debug register access must not be allowed while running")
    if not direct_register_access_allowed(CoreLifecycle.DEBUG_HALTED):
        issues.append("direct debug register access must be allowed while debug-halted")
    if RETURN_STACK_ENTRY_CELLS != CAPABILITY_OBJECT_CELLS:
        issues.append("protected return-stack entries must be one capability slot")
    if DEBUG_RETURN_REPLACEMENT_OTYPE != OTYPE_RETURN:
        issues.append("debug return-stack replacement must install OTYPE_RETURN")
    operations = {rule.operation for rule in DEBUG_UNWIND_RULES}
    if operations != set(DebugUnwindOperation):
        issues.append("debug unwind rules must cover peek, drop, and replace")
    replace = debug_unwind_rule(DebugUnwindOperation.REPLACE)
    if not replace.atomic_payload_tag or not replace.requires_valid_return_capability:
        issues.append("debug return-stack replace must be atomic and validate return capabilities")
    return tuple(issues)

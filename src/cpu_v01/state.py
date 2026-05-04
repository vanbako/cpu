"""Architectural core-state containers for CPU v0.1.

Owner stories:
- E01-S02: 16 writable 48-bit integer registers.
- E01-S03: 8 general capability registers.
- E01-S04: 8 special capability registers and CCSR indices.
- E01-S05: hidden slot state for PCC and EPCC.
- I02-S04: implementation representation of architectural core state.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum

from .capabilities import Capability, CapabilityPayload, require_uint
from .csrs import CSR_COREID, CSR_SR, ScalarCsrFile
from .tlb import LocalTlbs


INTEGER_REGISTER_BITS = 48
INTEGER_REGISTER_MASK = (1 << INTEGER_REGISTER_BITS) - 1
INTEGER_REGISTER_COUNT = 16
GENERAL_CAPABILITY_REGISTER_COUNT = 8

SLOT_0 = 0
SLOT_1 = 1
VALID_SLOTS = (SLOT_0, SLOT_1)

SPECIAL_CAPABILITY_NAMES = (
    "PCC",
    "DSC",
    "RSC",
    "DDC",
    "EPCC",
    "TVC",
    "KSC",
    "KRC",
)
SLOTTED_SPECIAL_CAPABILITY_NAMES = ("PCC", "EPCC")

CCSR_INDEX_TO_SPECIAL_NAME = {
    index: name for index, name in enumerate(SPECIAL_CAPABILITY_NAMES)
}
SPECIAL_NAME_TO_CCSR_INDEX = {
    name: index for index, name in CCSR_INDEX_TO_SPECIAL_NAME.items()
}


class CoreLifecycle(Enum):
    """Architectural lifecycle state used by reset and startup stories."""

    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    WFI_PARKED = "WFI_PARKED"
    STARTED = "STARTED"
    DEBUG_HALTED = "DEBUG_HALTED"
    DEBUG_MONITOR = "DEBUG_MONITOR"


def require_register_index(index: int, count: int, prefix: str) -> int:
    if type(index) is not int:
        raise TypeError(f"{prefix} register index must be an int")
    if not 0 <= index < count:
        raise IndexError(f"{prefix} register index must be in range [0, {count})")
    return index


def require_integer_register_index(index: int) -> int:
    return require_register_index(index, INTEGER_REGISTER_COUNT, "D")


def require_general_capability_register_index(index: int) -> int:
    return require_register_index(index, GENERAL_CAPABILITY_REGISTER_COUNT, "C")


def require_slot(slot: int, name: str = "slot") -> int:
    if type(slot) is not int:
        raise TypeError(f"{name} must be an int")
    if slot not in VALID_SLOTS:
        raise ValueError(f"{name} must be 0 or 1")
    return slot


def require_ccsr_index(index: int) -> int:
    return require_uint(index, 8, "ccsr_index")


def ccsr_name(index: int) -> str:
    index = require_ccsr_index(index)
    try:
        return CCSR_INDEX_TO_SPECIAL_NAME[index]
    except KeyError as exc:
        raise KeyError(f"reserved CCSR index {index}") from exc


def require_special_capability_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("special capability name must be a str")
    normalized = name.upper()
    if normalized not in SPECIAL_NAME_TO_CCSR_INDEX:
        raise KeyError(f"unknown special capability register {name!r}")
    return normalized


def is_slotted_special_capability(name: str) -> bool:
    return require_special_capability_name(name) in SLOTTED_SPECIAL_CAPABILITY_NAMES


def _invalid_capability() -> Capability:
    return Capability.invalid()


@dataclass(frozen=True)
class SlottedCapability:
    """Capability plus the hidden instruction slot bit used by PCC and EPCC."""

    capability: Capability
    slot: int = SLOT_0

    def __post_init__(self) -> None:
        if not isinstance(self.capability, Capability):
            raise TypeError("capability must be a Capability")
        object.__setattr__(self, "slot", require_slot(self.slot))

    @classmethod
    def invalid(
        cls,
        payload: CapabilityPayload | None = None,
        slot: int = SLOT_0,
    ) -> "SlottedCapability":
        return cls(capability=Capability.invalid(payload), slot=slot)

    @classmethod
    def from_capability(
        cls,
        capability: Capability,
        slot: int = SLOT_0,
    ) -> "SlottedCapability":
        return cls(capability=capability.copy(), slot=slot)

    @property
    def payload(self) -> CapabilityPayload:
        return self.capability.payload

    @property
    def tag(self) -> bool:
        return self.capability.tag

    @property
    def is_valid(self) -> bool:
        return self.capability.is_valid

    @property
    def is_invalid(self) -> bool:
        return self.capability.is_invalid

    def without_slot(self) -> Capability:
        return self.capability.copy()

    def with_capability(self, capability: Capability) -> "SlottedCapability":
        return SlottedCapability.from_capability(capability, self.slot)

    def with_slot(self, slot: int) -> "SlottedCapability":
        return SlottedCapability(capability=self.capability, slot=slot)


class IntegerRegisterFile:
    """Mutable `D0-D15` register file with 48-bit values."""

    def __init__(self, values: Iterable[int] | None = None) -> None:
        if values is None:
            self._values = [0] * INTEGER_REGISTER_COUNT
            return

        value_tuple = tuple(values)
        if len(value_tuple) != INTEGER_REGISTER_COUNT:
            raise ValueError(f"integer register file requires {INTEGER_REGISTER_COUNT} values")
        self._values = [
            require_uint(value, INTEGER_REGISTER_BITS, f"D{index}")
            for index, value in enumerate(value_tuple)
        ]

    def __len__(self) -> int:
        return INTEGER_REGISTER_COUNT

    def __iter__(self) -> Iterator[int]:
        return iter(self.as_tuple())

    def read(self, index: int) -> int:
        index = require_integer_register_index(index)
        return self._values[index]

    def write(self, index: int, value: int) -> None:
        index = require_integer_register_index(index)
        self._values[index] = require_uint(value, INTEGER_REGISTER_BITS, f"D{index}")

    def as_tuple(self) -> tuple[int, ...]:
        return tuple(self._values)


class CapabilityRegisterFile:
    """Mutable `C0-C7` register file with payload plus tag."""

    def __init__(self, values: Iterable[Capability] | None = None) -> None:
        if values is None:
            self._values = [_invalid_capability() for _ in range(GENERAL_CAPABILITY_REGISTER_COUNT)]
            return

        value_tuple = tuple(values)
        if len(value_tuple) != GENERAL_CAPABILITY_REGISTER_COUNT:
            raise ValueError(
                f"capability register file requires {GENERAL_CAPABILITY_REGISTER_COUNT} values"
            )
        self._values = [
            self._checked_capability(value, f"C{index}")
            for index, value in enumerate(value_tuple)
        ]

    @staticmethod
    def _checked_capability(value: Capability, name: str) -> Capability:
        if not isinstance(value, Capability):
            raise TypeError(f"{name} must be a Capability")
        return value.copy()

    def __len__(self) -> int:
        return GENERAL_CAPABILITY_REGISTER_COUNT

    def __iter__(self) -> Iterator[Capability]:
        return iter(self.as_tuple())

    def read(self, index: int) -> Capability:
        index = require_general_capability_register_index(index)
        return self._values[index].copy()

    def write(self, index: int, capability: Capability) -> None:
        index = require_general_capability_register_index(index)
        self._values[index] = self._checked_capability(capability, f"C{index}")

    def as_tuple(self) -> tuple[Capability, ...]:
        return tuple(value.copy() for value in self._values)


@dataclass
class SpecialCapabilityRegisters:
    """Per-core special capability registers.

    Plain writes model the v0.1 CCSR payload/tag transfer behavior. For PCC and
    EPCC, those writes reset the hidden slot to 0; hardware paths that must
    preserve or install slot 1 should use `write_slotted`.
    """

    pcc: SlottedCapability = field(default_factory=SlottedCapability.invalid)
    dsc: Capability = field(default_factory=_invalid_capability)
    rsc: Capability = field(default_factory=_invalid_capability)
    ddc: Capability = field(default_factory=_invalid_capability)
    epcc: SlottedCapability = field(default_factory=SlottedCapability.invalid)
    tvc: Capability = field(default_factory=_invalid_capability)
    ksc: Capability = field(default_factory=_invalid_capability)
    krc: Capability = field(default_factory=_invalid_capability)

    def __post_init__(self) -> None:
        self.pcc = self._checked_slotted(self.pcc, "PCC")
        self.dsc = self._checked_capability(self.dsc, "DSC")
        self.rsc = self._checked_capability(self.rsc, "RSC")
        self.ddc = self._checked_capability(self.ddc, "DDC")
        self.epcc = self._checked_slotted(self.epcc, "EPCC")
        self.tvc = self._checked_capability(self.tvc, "TVC")
        self.ksc = self._checked_capability(self.ksc, "KSC")
        self.krc = self._checked_capability(self.krc, "KRC")

    @staticmethod
    def _field_name(name: str) -> str:
        return require_special_capability_name(name).lower()

    @staticmethod
    def _checked_capability(value: Capability, name: str) -> Capability:
        if not isinstance(value, Capability):
            raise TypeError(f"{name} must be a Capability")
        return value.copy()

    @staticmethod
    def _checked_slotted(value: SlottedCapability, name: str) -> SlottedCapability:
        if not isinstance(value, SlottedCapability):
            raise TypeError(f"{name} must be a SlottedCapability")
        return SlottedCapability.from_capability(value.capability, value.slot)

    def read(self, name: str) -> Capability:
        name = require_special_capability_name(name)
        value = getattr(self, self._field_name(name))
        if isinstance(value, SlottedCapability):
            return value.without_slot()
        return value.copy()

    def write(self, name: str, capability: Capability) -> None:
        name = require_special_capability_name(name)
        capability = self._checked_capability(capability, name)
        field_name = self._field_name(name)
        if name in SLOTTED_SPECIAL_CAPABILITY_NAMES:
            setattr(self, field_name, SlottedCapability.from_capability(capability, SLOT_0))
        else:
            setattr(self, field_name, capability)

    def read_slotted(self, name: str) -> SlottedCapability:
        name = require_special_capability_name(name)
        if name not in SLOTTED_SPECIAL_CAPABILITY_NAMES:
            raise TypeError(f"{name} does not carry hidden slot state")
        return self._checked_slotted(getattr(self, self._field_name(name)), name)

    def write_slotted(self, name: str, value: SlottedCapability) -> None:
        name = require_special_capability_name(name)
        if name not in SLOTTED_SPECIAL_CAPABILITY_NAMES:
            raise TypeError(f"{name} does not carry hidden slot state")
        setattr(self, self._field_name(name), self._checked_slotted(value, name))

    def read_ccsr(self, index: int) -> Capability:
        return self.read(ccsr_name(index))

    def write_ccsr(self, index: int, capability: Capability) -> None:
        self.write(ccsr_name(index), capability)


@dataclass
class CoreState:
    """Per-core architectural register state before instruction execution."""

    core_id: int = 0
    lifecycle: CoreLifecycle = CoreLifecycle.RUNNING
    integer_registers: IntegerRegisterFile = field(default_factory=IntegerRegisterFile)
    general_capabilities: CapabilityRegisterFile = field(default_factory=CapabilityRegisterFile)
    special_capabilities: SpecialCapabilityRegisters = field(
        default_factory=SpecialCapabilityRegisters
    )
    scalar_csrs: ScalarCsrFile = field(default_factory=ScalarCsrFile)
    tlbs: LocalTlbs = field(default_factory=LocalTlbs)
    step_active: bool = False

    def __post_init__(self) -> None:
        if type(self.core_id) is not int:
            raise TypeError("core_id must be an int")
        if self.core_id < 0:
            raise ValueError("core_id must be nonnegative")
        if isinstance(self.lifecycle, str):
            self.lifecycle = CoreLifecycle(self.lifecycle)
        if not isinstance(self.lifecycle, CoreLifecycle):
            raise TypeError("lifecycle must be a CoreLifecycle")
        if not isinstance(self.integer_registers, IntegerRegisterFile):
            raise TypeError("integer_registers must be an IntegerRegisterFile")
        if not isinstance(self.general_capabilities, CapabilityRegisterFile):
            raise TypeError("general_capabilities must be a CapabilityRegisterFile")
        if not isinstance(self.special_capabilities, SpecialCapabilityRegisters):
            raise TypeError("special_capabilities must be SpecialCapabilityRegisters")
        if not isinstance(self.scalar_csrs, ScalarCsrFile):
            raise TypeError("scalar_csrs must be a ScalarCsrFile")
        if not isinstance(self.tlbs, LocalTlbs):
            raise TypeError("tlbs must be LocalTlbs")
        if type(self.step_active) is not bool:
            raise TypeError("step_active must be a bool")
        self.scalar_csrs.write_raw(CSR_COREID, self.core_id)
        self._sync_sr_slot_from_pcc()

    def read_d(self, index: int) -> int:
        return self.integer_registers.read(index)

    def write_d(self, index: int, value: int) -> None:
        self.integer_registers.write(index, value)

    def read_c(self, index: int) -> Capability:
        return self.general_capabilities.read(index)

    def write_c(self, index: int, capability: Capability) -> None:
        self.general_capabilities.write(index, capability)

    def read_ccsr(self, index: int) -> Capability:
        return self.special_capabilities.read_ccsr(index)

    def write_ccsr(self, index: int, capability: Capability) -> None:
        self.special_capabilities.write_ccsr(index, capability)
        if index == SPECIAL_NAME_TO_CCSR_INDEX["PCC"]:
            self._sync_sr_slot_from_pcc()

    def read_csr(self, number: int) -> int:
        return self.scalar_csrs.read(number)

    def write_csr_raw(self, number: int, value: int) -> None:
        self.scalar_csrs.write_raw(number, value)
        if number == CSR_SR:
            self._sync_sr_slot_from_pcc()

    def install_pcc(self, value: SlottedCapability) -> None:
        self.special_capabilities.write_slotted("PCC", value)
        self._sync_sr_slot_from_pcc()

    def install_epcc(self, value: SlottedCapability) -> None:
        self.special_capabilities.write_slotted("EPCC", value)

    @property
    def pcc(self) -> SlottedCapability:
        return self.special_capabilities.read_slotted("PCC")

    @property
    def epcc(self) -> SlottedCapability:
        return self.special_capabilities.read_slotted("EPCC")

    def _sync_sr_slot_from_pcc(self) -> None:
        self.scalar_csrs.set_sr_slot(self.pcc.slot)

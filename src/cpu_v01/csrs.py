"""Scalar CSR definitions and storage for CPU v0.1.

Owner stories:
- E01-S06: SR bit layout and reset value.
- E02-S01: 256-entry scalar CSR namespace and fast-window mapping.
- E02-S02: mandatory fast scalar CSR reset values and per-core scope.
- I02-S05: implementation storage for scalar CSR state.
"""

from __future__ import annotations

from collections.abc import Iterator

from .capabilities import require_uint


CSR_BITS = 48
CSR_MASK = (1 << CSR_BITS) - 1
CSR_NUMBER_BITS = 8
CSR_NUMBER_COUNT = 1 << CSR_NUMBER_BITS
FAST_CSR_COUNT = 16

SLOT_0 = 0
SLOT_1 = 1

CSR_SR = 0x00
CSR_COREID = 0x01
CSR_CYCLE = 0x02
CSR_INSTRET = 0x03
CSR_TVEC = 0x04
CSR_CAUSE = 0x05
CSR_TVAL = 0x06
CSR_SCRATCH = 0x07
CSR_IENABLE = 0x08
CSR_IPENDING = 0x09
CSR_TIMER = 0x0A
CSR_TIMECMP = 0x0B
CSR_SATP = 0x0C
CSR_ASID = 0x0D
CSR_DEBUGCTL = 0x0E
CSR_PERFSEL = 0x0F
CSR_FAULTCAPIDX = 0x4A
CSR_CAPCAUSE = 0x4B

MANDATORY_CSR_NAMES = (
    "SR",
    "COREID",
    "CYCLE",
    "INSTRET",
    "TVEC",
    "CAUSE",
    "TVAL",
    "SCRATCH",
    "IENABLE",
    "IPENDING",
    "TIMER",
    "TIMECMP",
    "SATP",
    "ASID",
    "DEBUGCTL",
    "PERFSEL",
)
CSR_NUMBER_TO_NAME = {
    index: name for index, name in enumerate(MANDATORY_CSR_NAMES)
}
EXTENDED_CSR_NUMBER_TO_NAME = {
    CSR_FAULTCAPIDX: "FAULTCAPIDX",
    CSR_CAPCAUSE: "CAPCAUSE",
}
ASSIGNED_CSR_NUMBER_TO_NAME = CSR_NUMBER_TO_NAME | EXTENDED_CSR_NUMBER_TO_NAME
CSR_NAME_TO_NUMBER = {
    name: index for index, name in ASSIGNED_CSR_NUMBER_TO_NAME.items()
}

SR_Z_BIT = 0
SR_N_BIT = 1
SR_C_BIT = 2
SR_V_BIT = 3
SR_IE_BIT = 4
SR_PIE_BIT = 5
SR_PRIV_BIT = 6
SR_PPRIV_BIT = 7
SR_EXL_BIT = 8
SR_SLOT_BIT = 9
SR_ASSIGNED_MASK = (1 << 10) - 1
SR_SLOT_MASK = 1 << SR_SLOT_BIT
SR_RES0_MASK = CSR_MASK ^ SR_ASSIGNED_MASK
SR_RESET_VALUE = (1 << SR_PRIV_BIT) | (1 << SR_PPRIV_BIT)

TIMECMP_RESET_VALUE = CSR_MASK
CAPCAUSE_DEFINED_VALUES = frozenset(range(0x0, 0x6))
FAULTCAPIDX_DEFINED_VALUES = frozenset(
    {
        0x00,
        0x01,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x20,
        0x21,
        0x22,
        0x23,
        0x24,
        0x25,
        0x26,
        0x27,
    }
)


def require_slot(slot: int) -> int:
    if type(slot) is not int:
        raise TypeError("slot must be an int")
    if slot not in (SLOT_0, SLOT_1):
        raise ValueError("slot must be 0 or 1")
    return slot


def require_csr_number(number: int) -> int:
    return require_uint(number, CSR_NUMBER_BITS, "csr_number")


def csr_name(number: int) -> str:
    number = require_csr_number(number)
    try:
        return ASSIGNED_CSR_NUMBER_TO_NAME[number]
    except KeyError as exc:
        raise KeyError(f"reserved CSR number {number}") from exc


def csr_number(name: str) -> int:
    if not isinstance(name, str):
        raise TypeError("csr name must be a str")
    normalized = name.upper()
    try:
        return CSR_NAME_TO_NUMBER[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown CSR name {name!r}") from exc


def sr_with_slot(value: int, slot: int) -> int:
    value = require_uint(value, CSR_BITS, "SR")
    slot = require_slot(slot)
    value &= ~SR_SLOT_MASK
    if slot == SLOT_1:
        value |= SR_SLOT_MASK
    return value


def sr_slot(value: int) -> int:
    value = require_uint(value, CSR_BITS, "SR")
    return SLOT_1 if value & SR_SLOT_MASK else SLOT_0


def mandatory_csr_reset_values(core_id: int) -> tuple[int, ...]:
    core_id = require_uint(core_id, CSR_BITS, "core_id")
    values = [0] * FAST_CSR_COUNT
    values[CSR_SR] = SR_RESET_VALUE
    values[CSR_COREID] = core_id
    values[CSR_TIMECMP] = TIMECMP_RESET_VALUE
    return tuple(values)


def _validate_extended_csr_value(number: int, value: int) -> int:
    value = require_uint(value, CSR_BITS, csr_name(number))
    if number == CSR_CAPCAUSE:
        if value not in CAPCAUSE_DEFINED_VALUES:
            raise ValueError("CAPCAUSE must be a defined 4-bit value")
    elif number == CSR_FAULTCAPIDX:
        if value not in FAULTCAPIDX_DEFINED_VALUES:
            raise ValueError("FAULTCAPIDX must be a defined 8-bit value")
    return value


class ScalarCsrFile:
    """Mutable storage for the mandatory per-core fast scalar CSRs."""

    def __init__(self, core_id: int = 0, values: tuple[int, ...] | None = None) -> None:
        if values is None:
            self._values = list(mandatory_csr_reset_values(core_id))
            self._extended_values = {
                CSR_FAULTCAPIDX: 0,
                CSR_CAPCAUSE: 0,
            }
            return

        if len(values) != FAST_CSR_COUNT:
            raise ValueError(f"scalar CSR file requires {FAST_CSR_COUNT} values")
        self._values = [
            require_uint(value, CSR_BITS, CSR_NUMBER_TO_NAME[index])
            for index, value in enumerate(values)
        ]
        self._extended_values = {
            CSR_FAULTCAPIDX: 0,
            CSR_CAPCAUSE: 0,
        }

    @classmethod
    def reset(cls, core_id: int = 0) -> "ScalarCsrFile":
        return cls(core_id=core_id)

    def __len__(self) -> int:
        return FAST_CSR_COUNT

    def __iter__(self) -> Iterator[int]:
        return iter(self.as_tuple())

    def read(self, number: int) -> int:
        number = require_csr_number(number)
        csr_name(number)
        if number in self._extended_values:
            return self._extended_values[number]
        return self._values[number]

    def write_raw(self, number: int, value: int) -> None:
        number = require_csr_number(number)
        csr_name(number)
        if number in self._extended_values:
            self._extended_values[number] = _validate_extended_csr_value(number, value)
            return
        self._values[number] = require_uint(value, CSR_BITS, csr_name(number))

    def read_name(self, name: str) -> int:
        return self.read(csr_number(name))

    def write_name_raw(self, name: str, value: int) -> None:
        self.write_raw(csr_number(name), value)

    def set_sr_slot(self, slot: int) -> None:
        self._values[CSR_SR] = sr_with_slot(self._values[CSR_SR], slot)

    def as_tuple(self) -> tuple[int, ...]:
        return tuple(self._values)

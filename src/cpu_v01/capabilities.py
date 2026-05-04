"""Capability payload, tag, permission, and object-type helpers.

Owner stories:
- E03-S01: 96-bit capability representation plus out-of-band tag.
- E03-S02: 8-bit capability permission table.
- E03-S05: global/local capability flag semantics.
- I02-S02: implementation data types for capabilities.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import IntFlag

from .cells import (
    ADDRESS_BITS,
    CAPABILITY_OBJECT_CELLS,
    CELL_BITS,
    mask_cell,
    require_cell_address,
    require_cell_value,
)


CAPABILITY_PAYLOAD_BITS = 96
CAPABILITY_CURSOR_BITS = ADDRESS_BITS
CAPABILITY_BOUNDS_METADATA_BITS = 30
CAPABILITY_PERMISSION_BITS = 8
CAPABILITY_OBJECT_TYPE_BITS = 8
CAPABILITY_FLAG_BITS = 2
CAPABILITY_TAG_BITS = 1

BOUNDS_METADATA_MASK = (1 << CAPABILITY_BOUNDS_METADATA_BITS) - 1
PERMISSION_MASK = (1 << CAPABILITY_PERMISSION_BITS) - 1
OBJECT_TYPE_MASK = (1 << CAPABILITY_OBJECT_TYPE_BITS) - 1
FLAG_MASK = (1 << CAPABILITY_FLAG_BITS) - 1

PAYLOAD_FLAG_SHIFT = 0
PAYLOAD_OBJECT_TYPE_SHIFT = PAYLOAD_FLAG_SHIFT + CAPABILITY_FLAG_BITS
PAYLOAD_PERMISSION_SHIFT = PAYLOAD_OBJECT_TYPE_SHIFT + CAPABILITY_OBJECT_TYPE_BITS
PAYLOAD_BOUNDS_METADATA_SHIFT = PAYLOAD_PERMISSION_SHIFT + CAPABILITY_PERMISSION_BITS
PAYLOAD_CURSOR_SHIFT = PAYLOAD_BOUNDS_METADATA_SHIFT + CAPABILITY_BOUNDS_METADATA_BITS

OTYPE_UNSEALED = 0x00
OTYPE_ENTRY = 0xFE
OTYPE_RETURN = 0xFF


class CapabilityPermission(IntFlag):
    """Capability permissions in E03-S02 table order, low bit first."""

    NONE = 0
    LD = 1 << 0
    ST = 1 << 1
    EX = 1 << 2
    LC = 1 << 3
    SC = 1 << 4
    SL = 1 << 5
    SEAL = 1 << 6
    UNSEAL = 1 << 7


ALL_PERMISSIONS = CapabilityPermission(PERMISSION_MASK)


class CapabilityFlag(IntFlag):
    """Capability payload flags.

    E03-S05 defines G=1 as global and G=0 as local. The second flag bit is
    reserved payload state for now and is still width-checked by this module.
    """

    NONE = 0
    G = 1 << 0
    RESERVED = 1 << 1


def _coerce_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return int(value)


def require_uint(value: int, bits: int, name: str) -> int:
    value = _coerce_int(value, name)
    if not 0 <= value < (1 << bits):
        raise ValueError(f"{name} must be in range [0, 2^{bits})")
    return value


def mask_permission_bits(value: int) -> int:
    return _coerce_int(value, "permissions") & PERMISSION_MASK


def require_permission_bits(value: int, name: str = "permissions") -> int:
    return require_uint(value, CAPABILITY_PERMISSION_BITS, name)


def require_bounds_metadata(value: int, name: str = "bounds_metadata") -> int:
    return require_uint(value, CAPABILITY_BOUNDS_METADATA_BITS, name)


def require_object_type(value: int, name: str = "otype") -> int:
    return require_uint(value, CAPABILITY_OBJECT_TYPE_BITS, name)


def require_flags(value: int, name: str = "flags") -> int:
    return require_uint(value, CAPABILITY_FLAG_BITS, name)


def is_unsealed_otype(otype: int) -> bool:
    return require_object_type(otype) == OTYPE_UNSEALED


def is_sealed_otype(otype: int) -> bool:
    return require_object_type(otype) != OTYPE_UNSEALED


def is_cseal_available_otype(otype: int) -> bool:
    otype = require_object_type(otype)
    return otype != OTYPE_UNSEALED and otype != OTYPE_RETURN


def is_cunseal_available_otype(otype: int) -> bool:
    otype = require_object_type(otype)
    return otype not in (OTYPE_UNSEALED, OTYPE_ENTRY, OTYPE_RETURN)


def require_payload_bits(value: int, name: str = "payload") -> int:
    return require_uint(value, CAPABILITY_PAYLOAD_BITS, name)


@dataclass(frozen=True)
class CapabilityPayload:
    """The 96-bit architectural capability payload fields.

    The exact bounds-compression algorithm is still implementation-facing in
    v0.1, so this type owns the 30-bit metadata field but does not decode it.
    """

    cursor: int
    bounds_metadata: int = 0
    permissions: int = 0
    otype: int = OTYPE_UNSEALED
    flags: int = int(CapabilityFlag.G)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cursor", require_cell_address(self.cursor, "cursor"))
        object.__setattr__(
            self,
            "bounds_metadata",
            require_bounds_metadata(self.bounds_metadata),
        )
        object.__setattr__(
            self,
            "permissions",
            require_permission_bits(self.permissions),
        )
        object.__setattr__(self, "otype", require_object_type(self.otype))
        object.__setattr__(self, "flags", require_flags(self.flags))

    @classmethod
    def zero(cls) -> "CapabilityPayload":
        return cls(cursor=0, bounds_metadata=0, permissions=0, otype=0, flags=0)

    @property
    def permission_set(self) -> CapabilityPermission:
        return CapabilityPermission(self.permissions)

    @property
    def flag_set(self) -> CapabilityFlag:
        return CapabilityFlag(self.flags)

    @property
    def is_sealed(self) -> bool:
        return self.otype != OTYPE_UNSEALED

    @property
    def is_unsealed(self) -> bool:
        return self.otype == OTYPE_UNSEALED

    @property
    def is_global(self) -> bool:
        return bool(self.flags & CapabilityFlag.G)

    @property
    def is_local(self) -> bool:
        return not self.is_global

    def has_permissions(self, required: int) -> bool:
        required = require_permission_bits(required, "required")
        return (self.permissions & required) == required

    def with_cursor(self, cursor: int) -> "CapabilityPayload":
        return replace(self, cursor=cursor)

    def with_bounds_metadata(self, bounds_metadata: int) -> "CapabilityPayload":
        return replace(self, bounds_metadata=bounds_metadata)

    def with_permissions(self, permissions: int) -> "CapabilityPayload":
        return replace(self, permissions=permissions)

    def clear_permissions_by_mask(self, mask: int) -> "CapabilityPayload":
        return self.with_permissions(self.permissions & mask_permission_bits(mask))

    def with_otype(self, otype: int) -> "CapabilityPayload":
        return replace(self, otype=otype)

    def with_flags(self, flags: int) -> "CapabilityPayload":
        return replace(self, flags=flags)

    def as_local(self) -> "CapabilityPayload":
        return self.with_flags(self.flags & ~int(CapabilityFlag.G))

    def as_global(self) -> "CapabilityPayload":
        return self.with_flags(self.flags | int(CapabilityFlag.G))


def pack_payload(payload: CapabilityPayload) -> int:
    if not isinstance(payload, CapabilityPayload):
        raise TypeError("payload must be a CapabilityPayload")
    return (
        (payload.cursor << PAYLOAD_CURSOR_SHIFT)
        | (payload.bounds_metadata << PAYLOAD_BOUNDS_METADATA_SHIFT)
        | (payload.permissions << PAYLOAD_PERMISSION_SHIFT)
        | (payload.otype << PAYLOAD_OBJECT_TYPE_SHIFT)
        | (payload.flags << PAYLOAD_FLAG_SHIFT)
    )


def unpack_payload(value: int) -> CapabilityPayload:
    value = require_payload_bits(value)
    return CapabilityPayload(
        cursor=(value >> PAYLOAD_CURSOR_SHIFT) & ((1 << CAPABILITY_CURSOR_BITS) - 1),
        bounds_metadata=(
            (value >> PAYLOAD_BOUNDS_METADATA_SHIFT) & BOUNDS_METADATA_MASK
        ),
        permissions=(value >> PAYLOAD_PERMISSION_SHIFT) & PERMISSION_MASK,
        otype=(value >> PAYLOAD_OBJECT_TYPE_SHIFT) & OBJECT_TYPE_MASK,
        flags=(value >> PAYLOAD_FLAG_SHIFT) & FLAG_MASK,
    )


def payload_to_cells(payload: CapabilityPayload) -> tuple[int, int, int, int]:
    packed = pack_payload(payload)
    return tuple(
        mask_cell(packed >> (CELL_BITS * index))
        for index in range(CAPABILITY_OBJECT_CELLS)
    )


def payload_from_cells(cells: Iterable[int]) -> CapabilityPayload:
    cell_tuple = tuple(cells)
    if len(cell_tuple) != CAPABILITY_OBJECT_CELLS:
        raise ValueError(f"payload requires {CAPABILITY_OBJECT_CELLS} cells")

    packed = 0
    for index, cell in enumerate(cell_tuple):
        packed |= require_cell_value(cell, f"cells[{index}]") << (CELL_BITS * index)
    return unpack_payload(packed)


@dataclass(frozen=True)
class Capability:
    """Capability payload plus its out-of-band architectural validity tag."""

    payload: CapabilityPayload
    tag: bool

    def __post_init__(self) -> None:
        if not isinstance(self.payload, CapabilityPayload):
            raise TypeError("payload must be a CapabilityPayload")
        if type(self.tag) is not bool:
            raise TypeError("tag must be a bool")

    @classmethod
    def invalid(cls, payload: CapabilityPayload | None = None) -> "Capability":
        if payload is None:
            payload = CapabilityPayload.zero()
        return cls(payload=payload, tag=False)

    @classmethod
    def valid(cls, payload: CapabilityPayload) -> "Capability":
        return cls(payload=payload, tag=True)

    @property
    def is_valid(self) -> bool:
        return self.tag

    @property
    def is_invalid(self) -> bool:
        return not self.tag

    @property
    def is_sealed(self) -> bool:
        return self.payload.is_sealed

    @property
    def is_unsealed(self) -> bool:
        return self.payload.is_unsealed

    @property
    def is_global(self) -> bool:
        return self.payload.is_global

    @property
    def is_local(self) -> bool:
        return self.payload.is_local

    def copy(self) -> "Capability":
        return Capability(payload=self.payload, tag=self.tag)

    def with_payload(self, payload: CapabilityPayload) -> "Capability":
        return Capability(payload=payload, tag=self.tag)

    def with_tag(self, tag: bool) -> "Capability":
        return Capability(payload=self.payload, tag=tag)

    def invalidated(self) -> "Capability":
        return self.with_tag(False)

    def with_cursor(self, cursor: int) -> "Capability":
        return self.with_payload(self.payload.with_cursor(cursor))

    def with_permissions(self, permissions: int) -> "Capability":
        return self.with_payload(self.payload.with_permissions(permissions))

    def clear_permissions_by_mask(self, mask: int) -> "Capability":
        return self.with_payload(self.payload.clear_permissions_by_mask(mask))

    def with_otype(self, otype: int) -> "Capability":
        return self.with_payload(self.payload.with_otype(otype))

    def as_local(self) -> "Capability":
        return self.with_payload(self.payload.as_local())

    def as_global(self) -> "Capability":
        return self.with_payload(self.payload.as_global())

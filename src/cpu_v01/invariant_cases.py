"""Deterministic invariant case generators for CPU v0.1.

Owner stories:
- E03-S03: monotonic capability derivation.
- E04-S05: capability instruction semantics.
- I16-S02: reusable deterministic capability property generators.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import capabilities as caps
from .cells import ADDRESS_SPACE_CELLS


SIGNED_48_MASK = (1 << 48) - 1


@dataclass(frozen=True)
class CapabilityDerivationCase:
    name: str
    parent: caps.Capability
    candidate_addresses: tuple[int, ...]
    offsets: tuple[int, ...]
    bounds_lengths: tuple[int, ...]
    permission_masks: tuple[int, ...]
    seal_object_types: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("case name must not be empty")
        if not isinstance(self.parent, caps.Capability):
            raise TypeError("parent must be a Capability")
        if self.parent.is_invalid or self.parent.is_sealed:
            raise ValueError("parent must be valid and unsealed")
        _require_non_empty_tuple(self.candidate_addresses, "candidate_addresses")
        _require_non_empty_tuple(self.offsets, "offsets")
        _require_non_empty_tuple(self.bounds_lengths, "bounds_lengths")
        _require_non_empty_tuple(self.permission_masks, "permission_masks")
        _require_non_empty_tuple(self.seal_object_types, "seal_object_types")
        bounds = self.parent.payload.bounds
        for address in self.candidate_addresses:
            if not bounds.contains_cursor(address):
                raise ValueError(f"{self.name} candidate address escapes parent bounds")
        for offset in self.offsets:
            candidate = self.parent.payload.cursor + offset
            if not 0 <= candidate < ADDRESS_SPACE_CELLS:
                raise ValueError(f"{self.name} offset escapes address space")
            if not bounds.contains_cursor(candidate):
                raise ValueError(f"{self.name} offset escapes parent bounds")
        for length in self.bounds_lengths:
            if length <= 0:
                raise ValueError(f"{self.name} bounds length must be positive")
            child_top = self.parent.payload.cursor + length
            if not bounds.contains_range(self.parent.payload.cursor, child_top):
                raise ValueError(f"{self.name} child bounds escape parent bounds")
            caps.encode_bounds_metadata(self.parent.payload.cursor, child_top)
        for mask in self.permission_masks:
            if type(mask) is not int or mask < 0:
                raise ValueError(f"{self.name} permission masks must be nonnegative ints")
        for otype in self.seal_object_types:
            if not caps.is_cseal_available_otype(otype):
                raise ValueError(f"{self.name} CSEAL object type is unavailable")
            if not caps.is_cunseal_available_otype(otype):
                raise ValueError(f"{self.name} CUNSEAL object type is unavailable")


@dataclass(frozen=True)
class InvalidCapabilityCase:
    name: str
    source: caps.Capability

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("case name must not be empty")
        if not isinstance(self.source, caps.Capability):
            raise TypeError("source must be a Capability")
        if self.source.is_valid:
            raise ValueError("source must be invalid")


def capability(
    cursor: int,
    *,
    base: int,
    top: int,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=permissions,
        otype=otype,
        flags=flags,
    ).with_bounds(base, top)
    return caps.Capability(payload=payload, tag=tag)


def capability_derivation_cases() -> tuple[CapabilityDerivationCase, ...]:
    return (
        CapabilityDerivationCase(
            name="full_permissions_low_cursor",
            parent=capability(0x1000, base=0x1000, top=0x3000),
            candidate_addresses=(0x1000, 0x1800, 0x2FFF),
            offsets=(0, 0x80, 0x1FFF),
            bounds_lengths=(0x80, 0x400, 0x1000),
            permission_masks=(0x00, 0x01, 0x55, 0xFF, 0x1FF),
            seal_object_types=(0x22, 0x44),
        ),
        CapabilityDerivationCase(
            name="limited_permissions_mid_cursor",
            parent=capability(
                0x1800,
                base=0x1000,
                top=0x3000,
                permissions=int(
                    caps.CapabilityPermission.LD
                    | caps.CapabilityPermission.LC
                    | caps.CapabilityPermission.SEAL
                ),
            ),
            candidate_addresses=(0x1000, 0x1800, 0x2FFF),
            offsets=(0, -0x400, 0x700),
            bounds_lengths=(0x100, 0x400, 0x800),
            permission_masks=(0x00, 0x09, 0x49, 0xFF),
            seal_object_types=(0x33, 0x55),
        ),
        CapabilityDerivationCase(
            name="local_store_authority",
            parent=capability(
                0x0400,
                base=0,
                top=0x1000,
                permissions=int(
                    caps.CapabilityPermission.ST
                    | caps.CapabilityPermission.SC
                    | caps.CapabilityPermission.SL
                ),
                flags=0,
            ),
            candidate_addresses=(0, 0x0400, 0x0FFF),
            offsets=(0, -0x200, 0x200),
            bounds_lengths=(1, 0x200, 0x0C00),
            permission_masks=(0x00, 0x12, 0x32, 0xFF),
            seal_object_types=(0x66, 0x77),
        ),
    )


def invalid_capability_cases() -> tuple[InvalidCapabilityCase, ...]:
    return (
        InvalidCapabilityCase(
            "invalid_unsealed_payload",
            capability(0x1000, base=0x1000, top=0x2000, tag=False),
        ),
        InvalidCapabilityCase(
            "invalid_sealed_payload",
            capability(0x1000, base=0x1000, top=0x2000, tag=False, otype=0x22),
        ),
        InvalidCapabilityCase(
            "invalid_local_payload",
            capability(0x0400, base=0, top=0x1000, tag=False, flags=0),
        ),
    )


def signed_48_cell(value: int) -> int:
    if type(value) is not int:
        raise TypeError("value must be an int")
    return value & SIGNED_48_MASK


def validate_capability_derivation_cases() -> tuple[str, ...]:
    issues: list[str] = []
    cases = capability_derivation_cases()
    names = [case.name for case in cases]
    if len(names) != len(set(names)):
        issues.append("capability derivation case names must be unique")
    for case in cases:
        if case.parent.is_invalid or case.parent.is_sealed:
            issues.append(f"{case.name} parent must be valid and unsealed")
        if not case.candidate_addresses:
            issues.append(f"{case.name} has no cursor samples")
        if not case.bounds_lengths:
            issues.append(f"{case.name} has no bounds samples")
        if not case.permission_masks:
            issues.append(f"{case.name} has no permission masks")
        if not case.seal_object_types:
            issues.append(f"{case.name} has no seal object types")
    invalid_names = [case.name for case in invalid_capability_cases()]
    if len(invalid_names) != len(set(invalid_names)):
        issues.append("invalid capability case names must be unique")
    return tuple(issues)


def _require_non_empty_tuple(values: tuple[int, ...], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    if not all(type(value) is int for value in values):
        raise TypeError(f"{name} must contain ints")

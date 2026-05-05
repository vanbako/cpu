"""External 24-bit cell serialization helpers for CPU v0.1.

Owner sources:
- E01-S01: external containers must define 24-bit cell serialization.
- E09-S01: base-page images serialize to 6144 octets.
- E10-S02: cache-line images serialize to 48 octets.
- E14-S02: toolchain spike for cell-addressed binary containers.
- I07-S03: implementation profile for byte-oriented cell containers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from . import cells


CELL_BYTE_ORDER = "little"
SECTION_MAGIC = b"CV01CELLS"


class SerializationError(ValueError):
    """Raised when an external byte container is not a valid cell image."""


def serialized_size_cells(cell_count: int) -> int:
    cell_count = cells.require_cell_count(cell_count, "cell_count")
    return cell_count * cells.CELL_BYTES


def serialize_cell(value: int) -> bytes:
    value = cells.require_cell_value(value)
    return bytes(
        (
            value & 0xFF,
            (value >> 8) & 0xFF,
            (value >> 16) & 0xFF,
        )
    )


def deserialize_cell(data: bytes | bytearray | memoryview) -> int:
    raw = bytes(data)
    if len(raw) != cells.CELL_BYTES:
        raise SerializationError("a serialized cell must contain exactly 3 octets")
    return raw[0] | (raw[1] << 8) | (raw[2] << 16)


def serialize_cells(values: Iterable[int]) -> bytes:
    return b"".join(serialize_cell(value) for value in values)


def deserialize_cells(data: bytes | bytearray | memoryview) -> tuple[int, ...]:
    raw = bytes(data)
    if len(raw) % cells.CELL_BYTES:
        raise SerializationError("serialized cell payload length must be a multiple of 3 octets")
    return tuple(
        deserialize_cell(raw[index : index + cells.CELL_BYTES])
        for index in range(0, len(raw), cells.CELL_BYTES)
    )


def serialize_base_page(values: Sequence[int]) -> bytes:
    if len(values) != cells.BASE_PAGE_CELLS:
        raise SerializationError(f"base page requires {cells.BASE_PAGE_CELLS} cells")
    return serialize_cells(values)


def deserialize_base_page(data: bytes | bytearray | memoryview) -> tuple[int, ...]:
    if len(data) != serialized_size_cells(cells.BASE_PAGE_CELLS):
        raise SerializationError("serialized base page must contain 6144 octets")
    return deserialize_cells(data)


def serialize_cache_line(values: Sequence[int]) -> bytes:
    if len(values) != cells.CACHE_LINE_CELLS:
        raise SerializationError(f"cache line requires {cells.CACHE_LINE_CELLS} cells")
    return serialize_cells(values)


def deserialize_cache_line(data: bytes | bytearray | memoryview) -> tuple[int, ...]:
    if len(data) != serialized_size_cells(cells.CACHE_LINE_CELLS):
        raise SerializationError("serialized cache line must contain 48 octets")
    return deserialize_cells(data)


def cell_address_to_container_offset(address: int) -> int:
    address = cells.require_cell_address(address)
    return address * cells.CELL_BYTES


def container_offset_to_cell_address(offset_octets: int) -> int:
    if type(offset_octets) is not int:
        raise TypeError("offset_octets must be an int")
    if offset_octets < 0:
        raise ValueError("offset_octets must be nonnegative")
    if offset_octets % cells.CELL_BYTES:
        raise SerializationError("container offset does not name a cell boundary")
    return cells.require_cell_address(offset_octets // cells.CELL_BYTES)


@dataclass(frozen=True)
class CellSection:
    """One cell-addressed section inside a byte-oriented host container."""

    name: str
    base_cell: int
    alignment_cells: int
    payload_cells: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("section name must not be empty")
        base_cell = cells.require_cell_address(self.base_cell, "base_cell")
        alignment_cells = cells.require_positive_cell_count(
            self.alignment_cells,
            "alignment_cells",
        )
        if base_cell % alignment_cells:
            raise SerializationError("section base is not aligned to alignment_cells")
        object.__setattr__(self, "base_cell", base_cell)
        object.__setattr__(self, "alignment_cells", alignment_cells)
        object.__setattr__(
            self,
            "payload_cells",
            tuple(cells.require_cell_value(value) for value in self.payload_cells),
        )

    @property
    def size_cells(self) -> int:
        return len(self.payload_cells)

    @property
    def size_octets(self) -> int:
        return serialized_size_cells(self.size_cells)

    @property
    def payload_octets(self) -> bytes:
        return serialize_cells(self.payload_cells)

    def contains_cell(self, address: int) -> bool:
        address = cells.require_cell_address(address)
        return self.base_cell <= address < self.base_cell + self.size_cells


def validate_section(section: CellSection) -> tuple[str, ...]:
    if not isinstance(section, CellSection):
        raise TypeError("section must be a CellSection")
    issues: list[str] = []
    if section.base_cell % section.alignment_cells:
        issues.append("section base is not cell-aligned")
    if len(section.payload_octets) != section.size_octets:
        issues.append("section byte size is not 3 octets per cell")
    if section.size_octets % cells.CELL_BYTES:
        issues.append("section payload size is not a whole number of cells")
    return tuple(issues)

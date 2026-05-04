"""Cell-addressed constants and helpers for CPU v0.1.

Owner stories:
- E01-S01: 24-bit cell address model.
- I02-S01: implementation helpers for cells, addresses, ranges, and alignment.
"""

from __future__ import annotations

from dataclasses import dataclass


CELL_BITS = 24
CELL_BYTES = 3
CELL_MASK = (1 << CELL_BITS) - 1

ADDRESS_BITS = 48
ADDRESS_SPACE_CELLS = 1 << ADDRESS_BITS
MAX_CELL_ADDRESS = ADDRESS_SPACE_CELLS - 1

CELL_OBJECT_CELLS = 1
INTEGER_OBJECT_CELLS = 2
CAPABILITY_OBJECT_CELLS = 4
FETCH_GROUP_CELLS = 2
BASE_PAGE_CELLS = 1 << 11
CACHE_LINE_CELLS = 16


def _require_int(value: int, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    return value


def mask_cell(value: int) -> int:
    """Return the low 24 bits of an integer cell payload."""
    return _require_int(value, "value") & CELL_MASK


def is_cell_value(value: object) -> bool:
    """Return whether value is representable as one 24-bit cell payload."""
    return type(value) is int and 0 <= value <= CELL_MASK


def require_cell_value(value: int, name: str = "cell") -> int:
    """Return value if it is a valid 24-bit cell payload."""
    value = _require_int(value, name)
    if not 0 <= value <= CELL_MASK:
        raise ValueError(f"{name} must be in range [0, 2^{CELL_BITS})")
    return value


def is_cell_address(value: object) -> bool:
    """Return whether value is a valid 48-bit architectural cell address."""
    return type(value) is int and 0 <= value < ADDRESS_SPACE_CELLS


def require_cell_address(value: int, name: str = "address") -> int:
    """Return value if it is a valid 48-bit architectural cell address."""
    value = _require_int(value, name)
    if not 0 <= value < ADDRESS_SPACE_CELLS:
        raise ValueError(f"{name} must be in range [0, 2^{ADDRESS_BITS})")
    return value


def require_cell_endpoint(value: int, name: str = "endpoint") -> int:
    """Return value if it is valid as a half-open range endpoint."""
    value = _require_int(value, name)
    if not 0 <= value <= ADDRESS_SPACE_CELLS:
        raise ValueError(f"{name} must be in range [0, 2^{ADDRESS_BITS}]")
    return value


def require_cell_count(value: int, name: str = "count") -> int:
    """Return value if it is a nonnegative count of cells."""
    value = _require_int(value, name)
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def require_positive_cell_count(value: int, name: str = "count") -> int:
    """Return value if it is a positive count of cells."""
    value = require_cell_count(value, name)
    if value == 0:
        raise ValueError(f"{name} must be positive")
    return value


def is_aligned(address: int, alignment_cells: int) -> bool:
    """Return whether address is aligned to an N-cell boundary."""
    address = require_cell_address(address)
    alignment_cells = require_positive_cell_count(alignment_cells, "alignment_cells")
    return address % alignment_cells == 0


def align_down(address: int, alignment_cells: int) -> int:
    """Return the closest aligned address at or below address."""
    address = require_cell_address(address)
    alignment_cells = require_positive_cell_count(alignment_cells, "alignment_cells")
    return address - (address % alignment_cells)


@dataclass(frozen=True)
class CellRange:
    """Half-open architectural cell range [base, top)."""

    base: int
    top: int

    def __post_init__(self) -> None:
        base = require_cell_endpoint(self.base, "base")
        top = require_cell_endpoint(self.top, "top")
        if top < base:
            raise ValueError("top must be greater than or equal to base")

    @property
    def length(self) -> int:
        return self.top - self.base

    def contains_address(self, address: int) -> bool:
        address = require_cell_address(address)
        return self.base <= address < self.top

    def contains_range(self, other: "CellRange") -> bool:
        if not isinstance(other, CellRange):
            raise TypeError("other must be a CellRange")
        return self.base <= other.base and other.top <= self.top

    def is_base_aligned(self, alignment_cells: int) -> bool:
        if self.base == ADDRESS_SPACE_CELLS:
            return False
        return is_aligned(self.base, alignment_cells)


def cell_range(base: int, length_cells: int) -> CellRange:
    """Build a checked half-open cell range from base and length."""
    base = require_cell_address(base, "base")
    length_cells = require_cell_count(length_cells, "length_cells")
    top = base + length_cells
    if top > ADDRESS_SPACE_CELLS:
        raise ValueError("range exceeds 48-bit cell address space")
    return CellRange(base=base, top=top)


def object_range(base: int, object_cells: int) -> CellRange:
    """Build a checked non-empty object range from base and object size."""
    object_cells = require_positive_cell_count(object_cells, "object_cells")
    return cell_range(base, object_cells)


def integer_object_range(base: int) -> CellRange:
    return object_range(base, INTEGER_OBJECT_CELLS)


def capability_object_range(base: int) -> CellRange:
    return object_range(base, CAPABILITY_OBJECT_CELLS)


def fetch_group_base(address: int) -> int:
    return align_down(address, FETCH_GROUP_CELLS)


def fetch_group_range(address: int) -> CellRange:
    return object_range(fetch_group_base(address), FETCH_GROUP_CELLS)


def base_page_range(base: int) -> CellRange:
    if not is_aligned(base, BASE_PAGE_CELLS):
        raise ValueError("base page must start on a base-page boundary")
    return object_range(base, BASE_PAGE_CELLS)


def cache_line_base(address: int) -> int:
    return align_down(address, CACHE_LINE_CELLS)


def cache_line_range(address: int) -> CellRange:
    return object_range(cache_line_base(address), CACHE_LINE_CELLS)

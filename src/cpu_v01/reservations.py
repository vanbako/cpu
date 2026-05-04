"""LL/SC reservation state for CPU v0.1.

Owner stories:
- E08-S01: `LL48` and `SC48` reservation behavior.
- E08-S02: reservation identity, consumption, and clear events.
- I06-S03: `LL48`/`SC48` reservations.

This simulator tracks the minimum legal v0.1 granule: the aligned 48-bit word
reserved by `LL48`.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import csrs
from .cells import INTEGER_OBJECT_CELLS, is_aligned


@dataclass
class ReservationState:
    valid: bool = False
    word_pa: int = 0
    granule_base: int = 0
    granule_cells: int = INTEGER_OBJECT_CELLS
    memory_type: int = 0

    def clear(self) -> None:
        self.valid = False
        self.word_pa = 0
        self.granule_base = 0
        self.granule_cells = INTEGER_OBJECT_CELLS
        self.memory_type = 0

    def reserve_word(self, word_pa: int, memory_type: int) -> None:
        word_pa = csrs.require_uint(word_pa, csrs.CSR_BITS, "word_pa")
        if not is_aligned(word_pa, INTEGER_OBJECT_CELLS):
            raise ValueError("LL/SC reservation word must be 2-cell aligned")
        self.valid = True
        self.word_pa = word_pa
        self.granule_base = word_pa
        self.granule_cells = INTEGER_OBJECT_CELLS
        self.memory_type = csrs.require_uint(memory_type, 2, "memory_type")

    def matches_word(self, word_pa: int) -> bool:
        word_pa = csrs.require_uint(word_pa, csrs.CSR_BITS, "word_pa")
        return self.valid and self.word_pa == word_pa

    def overlaps(self, address: int, length_cells: int) -> bool:
        address = csrs.require_uint(address, csrs.CSR_BITS, "address")
        length_cells = csrs.require_uint(length_cells, csrs.CSR_BITS, "length_cells")
        if not self.valid or length_cells == 0:
            return False
        access_top = address + length_cells
        granule_top = self.granule_base + self.granule_cells
        return address < granule_top and self.granule_base < access_top

    def clear_if_overlaps(self, address: int, length_cells: int) -> None:
        if self.overlaps(address, length_cells):
            self.clear()


@dataclass(frozen=True)
class ReservationInstallEffect:
    word_pa: int
    memory_type: int

    def apply(self, core: object) -> None:
        reservation = getattr(core, "reservation", None)
        if not isinstance(reservation, ReservationState):
            raise TypeError("core must provide ReservationState")
        reservation.reserve_word(self.word_pa, self.memory_type)


@dataclass(frozen=True)
class ReservationClearEffect:
    def apply(self, core: object) -> None:
        reservation = getattr(core, "reservation", None)
        if not isinstance(reservation, ReservationState):
            raise TypeError("core must provide ReservationState")
        reservation.clear()


def clear_conflicting_reservations(
    cores: object,
    address: int,
    length_cells: int,
) -> None:
    """Clear reservations on every core whose tracked granule overlaps a store."""
    for core in cores:
        reservation = getattr(core, "reservation", None)
        if isinstance(reservation, ReservationState):
            reservation.clear_if_overlaps(address, length_cells)

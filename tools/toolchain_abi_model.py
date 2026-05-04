#!/usr/bin/env python3
"""Prototype 24-bit-cell toolchain and ABI model for CPU v0.1.

This is a spike prototype for E14-S02. It is not a final opcode map.
It validates software-facing consequences of:

- 24-bit cells.
- 48-bit fetch groups made of 2 cells.
- 12/24/48-bit instruction placement.
- Cell-addressed labels and branch displacements.
- 4-cell ABI stack-frame alignment.
"""

from __future__ import annotations

from dataclasses import dataclass


CELL_BITS = 24
CELL_BYTES = 3
CELL_MASK = (1 << CELL_BITS) - 1
HALF_MASK = (1 << 12) - 1
FETCH_GROUP_CELLS = 2
STACK_ALIGN_CELLS = 4
INT_SLOT_CELLS = 2
CAP_SLOT_CELLS = 4
NOP12 = 0
NOP24 = 0


class ModelError(ValueError):
    """Raised when the prototype hits an invalid encoding or layout."""


@dataclass(frozen=True)
class Emission:
    cell: int
    slot: int
    size_bits: int
    text: str


@dataclass(frozen=True)
class Relocation:
    at_cell: int
    label: str
    target_cell: int
    displacement_cells: int
    encoded: int


@dataclass(frozen=True)
class FrameObject:
    name: str
    offset_cells: int
    size_cells: int
    alignment_cells: int


@dataclass(frozen=True)
class StackFrame:
    name: str
    entry_cursor: int
    new_cursor: int
    raw_cells: int
    aligned_cells: int
    objects: tuple[FrameObject, ...]


def align_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def signed_field(value: int, bits: int) -> int:
    low = -(1 << (bits - 1))
    high = (1 << (bits - 1)) - 1
    if not low <= value <= high:
        raise ModelError(f"value {value} does not fit signed {bits}-bit field")
    return value & ((1 << bits) - 1)


def encode_add12(rd: int, rs: int) -> int:
    return (0x1 << 8) | ((rd & 0xF) << 4) | (rs & 0xF)


def encode_bra24(displacement_cells: int) -> int:
    return (0xB << 20) | signed_field(displacement_cells, 20)


def encode_ld48_24(rd: int, ca: int, offset_cells: int) -> int:
    return (0x2 << 20) | ((rd & 0xF) << 16) | ((ca & 0xF) << 12) | signed_field(offset_cells, 12)


def encode_st48_24(rs: int, ca: int, offset_cells: int) -> int:
    return (0x3 << 20) | ((rs & 0xF) << 16) | ((ca & 0xF) << 12) | signed_field(offset_cells, 12)


def encode_clc48(cd: int, ca: int, offset_cells: int) -> int:
    return (0xC1 << 40) | ((cd & 0xF) << 36) | ((ca & 0xF) << 32) | (offset_cells & 0xFFFF_FFFF)


def cells_to_little_endian_bytes(cells: list[int]) -> bytes:
    result = bytearray()
    for cell in cells:
        if not 0 <= cell <= CELL_MASK:
            raise ModelError(f"cell out of range: 0x{cell:X}")
        result.extend(cell.to_bytes(CELL_BYTES, "little"))
    return bytes(result)


class ToyAssembler:
    def __init__(self) -> None:
        self.cells: list[int] = []
        self.slot = 0
        self.labels: dict[str, int] = {}
        self.emissions: list[Emission] = []
        self._branch_fixups: list[tuple[int, str]] = []
        self.relocations: list[Relocation] = []

    def current_cell(self) -> int:
        return len(self.cells) if self.slot == 0 else len(self.cells) - 1

    def label(self, name: str) -> None:
        self.align_slot0()
        self.labels[name] = self.current_cell()

    def align_slot0(self) -> None:
        if self.slot == 1:
            self.emit12("PAD12", NOP12)

    def align_fetch_group(self) -> None:
        self.align_slot0()
        if len(self.cells) % FETCH_GROUP_CELLS:
            cell = len(self.cells)
            self.cells.append(NOP24)
            self.emissions.append(Emission(cell, 0, 24, "PAD24 fetch-group align"))

    def emit12(self, text: str, encoding: int) -> None:
        encoding &= HALF_MASK
        if self.slot == 0:
            cell = len(self.cells)
            self.cells.append(encoding)
            self.emissions.append(Emission(cell, 0, 12, text))
            self.slot = 1
        else:
            cell = len(self.cells) - 1
            self.cells[cell] |= encoding << 12
            self.emissions.append(Emission(cell, 1, 12, text))
            self.slot = 0

    def emit24(self, text: str, encoding: int) -> int:
        self.align_slot0()
        cell = len(self.cells)
        self.cells.append(encoding & CELL_MASK)
        self.emissions.append(Emission(cell, 0, 24, text))
        return cell

    def emit48(self, text: str, encoding: int) -> int:
        self.align_fetch_group()
        cell = len(self.cells)
        self.cells.append(encoding & CELL_MASK)
        self.cells.append((encoding >> CELL_BITS) & CELL_MASK)
        self.emissions.append(Emission(cell, 0, 48, text))
        return cell

    def add12(self, rd: int, rs: int) -> None:
        self.emit12(f"ADD12 D{rd}, D{rs}", encode_add12(rd, rs))

    def bra24(self, label: str) -> None:
        cell = self.emit24(f"BRA24 {label}", 0)
        self._branch_fixups.append((cell, label))

    def ld48(self, rd: int, ca: int, offset_cells: int) -> None:
        self.emit24(f"LD48 D{rd}, C{ca}, {offset_cells}", encode_ld48_24(rd, ca, offset_cells))

    def st48(self, rs: int, ca: int, offset_cells: int) -> None:
        self.emit24(f"ST48 D{rs}, C{ca}, {offset_cells}", encode_st48_24(rs, ca, offset_cells))

    def clc(self, cd: int, ca: int, offset_cells: int) -> None:
        self.emit48(f"CLC C{cd}, C{ca}, {offset_cells}", encode_clc48(cd, ca, offset_cells))

    def finalize(self) -> None:
        self.align_slot0()
        if len(self.cells) % FETCH_GROUP_CELLS:
            cell = len(self.cells)
            self.cells.append(NOP24)
            self.emissions.append(Emission(cell, 0, 24, "PAD24 section fetch-group tail"))
        self.resolve()

    def resolve(self) -> None:
        for cell, label in self._branch_fixups:
            target = self.labels[label]
            displacement = target - (cell + 1)
            encoded = encode_bra24(displacement)
            self.cells[cell] = encoded
            self.relocations.append(Relocation(cell, label, target, displacement, encoded))


def build_sample_program() -> ToyAssembler:
    asm = ToyAssembler()
    asm.label("start")
    asm.add12(1, 0)
    asm.add12(2, 1)
    asm.bra24("done")
    asm.ld48(3, 0, 4)
    asm.st48(3, 0, 6)
    asm.clc(1, 2, 16)
    asm.label("done")
    asm.add12(0, 0)
    asm.finalize()
    return asm


def layout_stack_frame(
    name: str,
    entry_cursor: int,
    cap_spills: int,
    int_spills: int,
    outgoing_cap_args: int,
    outgoing_int_args: int,
) -> StackFrame:
    if entry_cursor % STACK_ALIGN_CELLS:
        raise ModelError("entry stack cursor must be 4-cell aligned")

    objects: list[FrameObject] = []
    offset = 0

    def place(prefix: str, count: int, size: int, alignment: int) -> None:
        nonlocal offset
        for index in range(count):
            offset = align_up(offset, alignment)
            objects.append(FrameObject(f"{prefix}{index}", offset, size, alignment))
            offset += size

    place("cap_spill", cap_spills, CAP_SLOT_CELLS, CAP_SLOT_CELLS)
    place("int_spill", int_spills, INT_SLOT_CELLS, INT_SLOT_CELLS)
    place("out_cap", outgoing_cap_args, CAP_SLOT_CELLS, CAP_SLOT_CELLS)
    place("out_int", outgoing_int_args, INT_SLOT_CELLS, INT_SLOT_CELLS)

    raw_cells = offset
    aligned_cells = align_up(raw_cells, STACK_ALIGN_CELLS)
    new_cursor = entry_cursor - aligned_cells

    for obj in objects:
        absolute = new_cursor + obj.offset_cells
        if absolute % obj.alignment_cells:
            raise AssertionError(f"{obj.name} is misaligned at 0x{absolute:X}")

    return StackFrame(
        name=name,
        entry_cursor=entry_cursor,
        new_cursor=new_cursor,
        raw_cells=raw_cells,
        aligned_cells=aligned_cells,
        objects=tuple(objects),
    )


def run_checks() -> dict[str, object]:
    asm = build_sample_program()
    encoded_bytes = cells_to_little_endian_bytes(asm.cells)
    fetch_groups = [(base, asm.cells[base], asm.cells[base + 1]) for base in range(0, len(asm.cells), 2)]

    assert len(asm.cells) == 8
    assert len(encoded_bytes) == len(asm.cells) * CELL_BYTES
    assert len(fetch_groups) == 4
    assert asm.labels["start"] == 0
    assert asm.labels["done"] == 6
    assert asm.relocations[0].displacement_cells == 4

    for emission in asm.emissions:
        if emission.size_bits == 48:
            assert emission.slot == 0
            assert emission.cell % FETCH_GROUP_CELLS == 0

    frames = [
        layout_stack_frame("e05_example", 0x1800, 2, 2, 1, 0),
        layout_stack_frame("mixed_spills", 0x1800, 1, 3, 0, 2),
    ]
    for frame in frames:
        assert frame.aligned_cells % STACK_ALIGN_CELLS == 0
        assert frame.new_cursor % STACK_ALIGN_CELLS == 0

    return {
        "assembler": asm,
        "encoded_bytes": encoded_bytes,
        "fetch_groups": fetch_groups,
        "frames": frames,
    }


def main() -> None:
    result = run_checks()
    asm: ToyAssembler = result["assembler"]  # type: ignore[assignment]
    encoded_bytes: bytes = result["encoded_bytes"]  # type: ignore[assignment]
    fetch_groups: list[tuple[int, int, int]] = result["fetch_groups"]  # type: ignore[assignment]
    frames: list[StackFrame] = result["frames"]  # type: ignore[assignment]

    print("24-bit cell toolchain/ABI prototype")
    print(f"cells: {len(asm.cells)}")
    print(f"serialized bytes at 3 bytes/cell: {len(encoded_bytes)}")
    print(f"fetch groups: {len(fetch_groups)}")
    print()

    print("| cell | encoded cell | contents |")
    print("| ---: | ---: | --- |")
    by_cell: dict[int, list[str]] = {}
    for emission in asm.emissions:
        by_cell.setdefault(emission.cell, []).append(f"{emission.text} [{emission.size_bits}b slot {emission.slot}]")
    for index, cell in enumerate(asm.cells):
        contents = "; ".join(by_cell.get(index, ["data/padding"]))
        print(f"| 0x{index:X} | 0x{cell:06X} | {contents} |")

    print()
    print("| fetch-group base | cell0 | cell1 |")
    print("| ---: | ---: | ---: |")
    for base, cell0, cell1 in fetch_groups:
        print(f"| 0x{base:X} | 0x{cell0:06X} | 0x{cell1:06X} |")

    print()
    print("| relocation | at cell | target cell | displacement cells | encoded cell |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for reloc in asm.relocations:
        print(
            f"| BRA24 {reloc.label} | 0x{reloc.at_cell:X} | "
            f"0x{reloc.target_cell:X} | {reloc.displacement_cells} | 0x{reloc.encoded:06X} |"
        )

    print()
    print("| stack frame | entry DSC | new DSC | raw cells | aligned cells | objects |")
    print("| --- | ---: | ---: | ---: | ---: | --- |")
    for frame in frames:
        objects = ", ".join(f"{obj.name}@+{obj.offset_cells}/{obj.size_cells}" for obj in frame.objects)
        print(
            f"| {frame.name} | 0x{frame.entry_cursor:X} | 0x{frame.new_cursor:X} | "
            f"{frame.raw_cells} | {frame.aligned_cells} | {objects} |"
        )


if __name__ == "__main__":
    main()

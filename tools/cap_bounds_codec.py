#!/usr/bin/env python3
"""Prototype 30-bit bounds codec for the CPU v0.1 capability format.

This is a spike prototype, not a final architectural definition.

The tested metadata shape is:

    exponent[5:0] | base_mantissa[11:0] | top_mantissa[11:0]

The cursor/address is stored separately in the 48-bit capability cursor field.
Bounds are reconstructed relative to that cursor.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random


ADDRESS_BITS = 48
MAX_ADDR = 1 << ADDRESS_BITS
MANT_BITS = 12
MANT_MOD = 1 << MANT_BITS
EXP_BITS = 6
MAX_EXP = ADDRESS_BITS - MANT_BITS


class CodecError(ValueError):
    """Raised when an interval cannot be represented by this prototype."""


@dataclass(frozen=True)
class DecodedBounds:
    base: int
    top: int
    exponent: int
    base_mantissa: int
    top_mantissa: int
    span_units: int


@dataclass(frozen=True)
class EncodedBounds:
    requested_base: int
    requested_top: int
    cursor: int
    encoded_base: int
    encoded_top: int
    exponent: int
    base_mantissa: int
    top_mantissa: int
    metadata: int

    @property
    def requested_size(self) -> int:
        return self.requested_top - self.requested_base

    @property
    def encoded_size(self) -> int:
        return self.encoded_top - self.encoded_base

    @property
    def exact(self) -> bool:
        return (
            self.requested_base == self.encoded_base
            and self.requested_top == self.encoded_top
        )

    @property
    def low_slop(self) -> int:
        return self.requested_base - self.encoded_base

    @property
    def high_slop(self) -> int:
        return self.encoded_top - self.requested_top


def ceil_div(value: int, divisor: int) -> int:
    return -(-value // divisor)


def pack_metadata(exponent: int, base_mantissa: int, top_mantissa: int) -> int:
    return (exponent << 24) | (base_mantissa << 12) | top_mantissa


def unpack_metadata(metadata: int) -> tuple[int, int, int]:
    exponent = (metadata >> 24) & 0x3F
    base_mantissa = (metadata >> 12) & 0xFFF
    top_mantissa = metadata & 0xFFF
    return exponent, base_mantissa, top_mantissa


def decode_bounds(metadata: int, cursor: int) -> DecodedBounds:
    if not 0 <= cursor < MAX_ADDR:
        raise CodecError(f"cursor out of range: {cursor}")

    exponent, base_mantissa, top_mantissa = unpack_metadata(metadata)
    if exponent > MAX_EXP:
        raise CodecError(f"unsupported exponent: {exponent}")

    unit = 1 << exponent
    cursor_units = cursor >> exponent
    diff_units = (top_mantissa - base_mantissa) % MANT_MOD
    span_units = diff_units if diff_units else MANT_MOD

    # Reconstruct the base whose low mantissa bits match and whose span
    # contains the cursor. This mirrors the CHERI-style idea that high bits are
    # inferred from the cursor, but keeps the correction logic simple.
    q0 = (cursor_units - base_mantissa) // MANT_MOD
    max_units = MAX_ADDR >> exponent
    for q in range(q0 - 2, q0 + 3):
        base_units = q * MANT_MOD + base_mantissa
        top_units = base_units + span_units
        if base_units < 0 or top_units > max_units:
            continue
        if base_units <= cursor_units < top_units:
            return DecodedBounds(
                base=base_units * unit,
                top=top_units * unit,
                exponent=exponent,
                base_mantissa=base_mantissa,
                top_mantissa=top_mantissa,
                span_units=span_units,
            )

    raise CodecError("cursor is outside the decodable bounds window")


def encode_bounds(
    requested_base: int,
    requested_top: int,
    cursor: int | None = None,
    parent: tuple[int, int] | None = None,
) -> EncodedBounds:
    if not 0 <= requested_base < requested_top <= MAX_ADDR:
        raise CodecError(
            f"invalid interval: [{requested_base:#x}, {requested_top:#x})"
        )

    if cursor is None:
        cursor = requested_base

    if not requested_base <= cursor < requested_top:
        raise CodecError("prototype requires cursor to be inside requested bounds")

    if parent is not None:
        parent_base, parent_top = parent
        if requested_base < parent_base or requested_top > parent_top:
            raise CodecError("requested child interval exceeds parent bounds")

    for exponent in range(MAX_EXP + 1):
        unit = 1 << exponent
        encoded_base = (requested_base // unit) * unit
        encoded_top = ceil_div(requested_top, unit) * unit
        if encoded_top > MAX_ADDR:
            continue

        span_units = (encoded_top - encoded_base) // unit
        if not 1 <= span_units <= MANT_MOD:
            continue

        if parent is not None:
            parent_base, parent_top = parent
            if encoded_base < parent_base or encoded_top > parent_top:
                continue

        base_mantissa = (encoded_base >> exponent) & 0xFFF
        top_mantissa = (encoded_top >> exponent) & 0xFFF
        metadata = pack_metadata(exponent, base_mantissa, top_mantissa)
        decoded = decode_bounds(metadata, cursor)

        if decoded.base == encoded_base and decoded.top == encoded_top:
            return EncodedBounds(
                requested_base=requested_base,
                requested_top=requested_top,
                cursor=cursor,
                encoded_base=encoded_base,
                encoded_top=encoded_top,
                exponent=exponent,
                base_mantissa=base_mantissa,
                top_mantissa=top_mantissa,
                metadata=metadata,
            )

    raise CodecError("interval is not representable by this prototype")


def corpus() -> list[tuple[str, int, int, int]]:
    high_base = MAX_ADDR - 0x5000
    return [
        ("one_cell", 0x100, 0x101, 0x100),
        ("int48_two_cells", 0x200, 0x202, 0x200),
        ("cap96_four_cells", 0x300, 0x304, 0x300),
        ("base_page_2^11_cells", 0x0, 1 << 11, 0x0),
        ("max_exact_e0", 0x10000, 0x11000, 0x10000),
        ("rounds_after_4096", 0x20000, 0x21001, 0x20000),
        ("unaligned_10k_cells", 0x12345, 0x14A55, 0x12345),
        ("future_page_2^15_cells", 0x80000, 0x88000, 0x80000),
        ("future_page_2^19_cells", 0x100000, 0x180000, 0x100000),
        ("large_2^30_cells", 0x4000000000, 0x4040000000, 0x4000000000),
        ("near_top_16k_cells", high_base, MAX_ADDR, high_base),
        ("full_48_bit_space", 0x0, MAX_ADDR, 0x123456789ABC),
    ]


def format_int(value: int) -> str:
    if value >= 1 << 20:
        return f"0x{value:X}"
    return str(value)


def run_corpus() -> list[EncodedBounds]:
    encoded = []
    for name, base, top, cursor in corpus():
        cap = encode_bounds(base, top, cursor)
        decoded = decode_bounds(cap.metadata, cursor)
        assert decoded.base == cap.encoded_base
        assert decoded.top == cap.encoded_top
        encoded.append(cap)
    return encoded


def run_monotonicity_tests(iterations: int = 1000) -> tuple[int, int]:
    rng = Random(0xC0DEC0DE)
    accepted = 0
    rejected = 0

    parents = [
        encode_bounds(0, 1 << 11, 0),
        encode_bounds(0x10000, 0x11000, 0x10000),
        encode_bounds(0x20000, 0x21001, 0x20000),
        encode_bounds(0x100000, 0x180000, 0x100000),
        encode_bounds(0x4000000000, 0x4040000000, 0x4000000000),
    ]

    for parent in parents:
        parent_tuple = (parent.encoded_base, parent.encoded_top)
        span = parent.encoded_size
        for _ in range(iterations):
            size = rng.randrange(1, span + 1)
            offset = rng.randrange(0, span - size + 1)
            child_base = parent.encoded_base + offset
            child_top = child_base + size
            cursor = child_base + rng.randrange(0, size)
            try:
                child = encode_bounds(child_base, child_top, cursor, parent_tuple)
            except CodecError:
                rejected += 1
                continue
            assert parent.encoded_base <= child.encoded_base
            assert child.encoded_top <= parent.encoded_top
            accepted += 1

    return accepted, rejected


def run_failure_cases() -> list[tuple[str, str]]:
    cases = [
        ("zero_length", lambda: encode_bounds(0x100, 0x100, 0x100)),
        ("top_past_48_bits", lambda: encode_bounds(MAX_ADDR - 1, MAX_ADDR + 1, MAX_ADDR - 1)),
        ("cursor_before_bounds", lambda: encode_bounds(0x1000, 0x2000, 0xFFF)),
        ("cursor_after_bounds", lambda: encode_bounds(0x1000, 0x2000, 0x2000)),
        (
            "child_exceeds_parent",
            lambda: encode_bounds(0x1000, 0x3000, 0x1000, (0x1800, 0x2800)),
        ),
    ]

    failures = []
    for name, fn in cases:
        try:
            fn()
        except CodecError as exc:
            failures.append((name, str(exc)))
        else:
            raise AssertionError(f"expected failure did not fail: {name}")
    return failures


def main() -> None:
    encoded = run_corpus()
    accepted, rejected = run_monotonicity_tests()
    failures = run_failure_cases()

    print("30-bit capability bounds codec prototype")
    print(f"metadata: {EXP_BITS}-bit exponent, {MANT_BITS}-bit base mantissa, {MANT_BITS}-bit top mantissa")
    print()
    print("| case | exp | requested cells | encoded cells | low slop | high slop | exact | metadata |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for (name, _, _, _), cap in zip(corpus(), encoded):
        print(
            "| "
            + " | ".join(
                [
                    name,
                    str(cap.exponent),
                    format_int(cap.requested_size),
                    format_int(cap.encoded_size),
                    format_int(cap.low_slop),
                    format_int(cap.high_slop),
                    "yes" if cap.exact else "no",
                    f"0x{cap.metadata:08X}",
                ]
            )
            + " |"
        )

    print()
    print(f"monotonicity accepted children: {accepted}")
    print(f"monotonicity rejected children: {rejected}")
    print()
    print("expected failures:")
    for name, reason in failures:
        print(f"- {name}: {reason}")


if __name__ == "__main__":
    main()

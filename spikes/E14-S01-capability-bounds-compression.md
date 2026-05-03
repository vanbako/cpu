# E14-S01: 96-bit Capability Bounds Compression Spike

Story: E14-S01

Status: Spike complete

Prototype: `tools/cap_bounds_codec.py`

## Question

Can the v0.1 capability format plausibly keep a 48-bit cursor/address, 30 bits of bounds metadata, 8 permission bits, 8 object-type bits, 2 flag bits, and a 1-bit out-of-band tag?

## Prototype Scheme

The prototype tests this 30-bit bounds metadata layout:

| Field | Bits | Purpose |
| --- | ---: | --- |
| `exponent` | 6 | Selects the bounds granularity as `2^exponent` cells. |
| `base_mantissa` | 12 | Low 12 bits of the rounded base in exponent-sized units. |
| `top_mantissa` | 12 | Low 12 bits of the rounded exclusive top in exponent-sized units. |

The 48-bit cursor/address is stored outside the bounds metadata. Decode reconstructs the high bits of the base and top relative to the cursor.

This is deliberately a CHERI-style compressed-bounds prototype, not a final CHERI-compatible encoding.

## Encoding Rule Tested

For requested bounds `[base, top)`:

1. Find the smallest exponent `E` where the interval fits in at most 4096 units of size `2^E` cells.
2. Round the base downward to a `2^E` cell boundary.
3. Round the exclusive top upward to a `2^E` cell boundary.
4. Store `E`, the rounded base mantissa, and the rounded top mantissa.
5. Decode using the capability cursor to recover the full rounded base and top.

For derived capabilities, the prototype rejects any rounded child bounds that would exceed the parent bounds.

## Prototype Results

Command:

```text
python .\tools\cap_bounds_codec.py
```

Output:

| case | exp | requested cells | encoded cells | low slop | high slop | exact | metadata |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| one_cell | 0 | 1 | 1 | 0 | 0 | yes | `0x00100101` |
| int48_two_cells | 0 | 2 | 2 | 0 | 0 | yes | `0x00200202` |
| cap96_four_cells | 0 | 4 | 4 | 0 | 0 | yes | `0x00300304` |
| base_page_2^11_cells | 0 | 2048 | 2048 | 0 | 0 | yes | `0x00000800` |
| max_exact_e0 | 0 | 4096 | 4096 | 0 | 0 | yes | `0x00000000` |
| rounds_after_4096 | 1 | 4097 | 4098 | 0 | 1 | no | `0x01000801` |
| unaligned_10k_cells | 2 | 10000 | 10004 | 1 | 3 | no | `0x028D1296` |
| future_page_2^15_cells | 3 | 32768 | 32768 | 0 | 0 | yes | `0x03000000` |
| future_page_2^19_cells | 7 | 524288 | 524288 | 0 | 0 | yes | `0x07000000` |
| large_2^30_cells | 18 | `0x40000000` | `0x40000000` | 0 | 0 | yes | `0x12000000` |
| near_top_16k_cells | 3 | 20480 | 20480 | 0 | 0 | yes | `0x03600000` |
| full_48_bit_space | 36 | `0x1000000000000` | `0x1000000000000` | 0 | 0 | yes | `0x24000000` |

Monotonicity tests:

- Accepted derived child capabilities: 5000
- Rejected derived child capabilities: 0
- All accepted children decoded inside their parent bounds.

Expected failure cases:

| Case | Reason |
| --- | --- |
| `zero_length` | Empty intervals are not represented by this prototype. |
| `top_past_48_bits` | Bounds must fit within the 48-bit cell address space. |
| `cursor_before_bounds` | This prototype requires the cursor to be inside requested bounds. |
| `cursor_after_bounds` | This prototype requires the cursor to be inside requested bounds. |
| `child_exceeds_parent` | Child derivation cannot exceed parent bounds. |

## Findings

The 30-bit metadata budget is plausible for v0.1.

Small architectural objects are exact:

- 1-cell objects
- 2-cell 48-bit integers
- 4-cell 96-bit capability slots
- 2048-cell base pages
- Objects up to 4096 cells when aligned at cell precision

Larger aligned regions remain exact when their size and base align with the selected exponent. This includes the reserved future page sizes in the current architecture notes:

- `2^15` cells uses exponent 3.
- `2^19` cells uses exponent 7.

Unaligned larger objects round outward. The measured examples show bounded slop:

- 4097 cells became 4098 cells.
- 10000 unaligned cells became 10004 cells, with 1 cell of low slop and 3 cells of high slop.

The maximum 48-bit address space is representable with exponent 36.

## Architectural Risk

The prototype decodes bounds relative to the cursor and requires the cursor to be inside the represented interval. That keeps the correction logic small, but it is a real semantic choice.

If v0.1 wants C-like one-past pointers or temporarily out-of-bounds capability cursors, this exact prototype is not enough. In that case, E03-S01 should either:

- define a richer correction algorithm that decodes stable bounds even when the cursor is just outside the interval, or
- define separate architectural behavior for out-of-bounds cursor updates, such as clearing the tag or trapping.

The current `design.md` does not yet decide that point.

## Recommendation

Keep the 96-bit capability target and the 30-bit bounds metadata budget for v0.1.

Do not freeze this exact codec yet. Use it as evidence that the budget is reasonable, then complete E03-S01 with an explicit decision on cursor-out-of-bounds behavior.

Recommended next decision for E03-S01:

- Tagged capabilities should remain decodable and monotonic.
- `CSETBOUNDS` may round outward only when the rounded bounds stay inside the parent authority.
- The architecture needs an explicit rule for `CSETADDR` and `CINCADDR` when the resulting cursor is outside bounds.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Prototype can encode and decode representative bounds. | Met by `tools/cap_bounds_codec.py` corpus. |
| Precision and rounding behavior are measured. | Met by corpus table. |
| Monotonic narrowing behavior is tested. | Met by 5000 accepted child derivation tests. |
| Failure cases are documented. | Met by expected failure table. |
| Recommendation is made to keep, revise, or expand the 96-bit format. | Keep 96-bit format, revise/finalize cursor-out-of-bounds semantics in E03-S01. |


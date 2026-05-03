# E04-S01: Instruction Size and Fetch-group Rules

Story: E04-S01

Status: Complete

Normative sources:

- `design.md`, section 6
- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S05-pc-subslot-behavior.md`

## Decision

CPU v0.1 fetches instructions in 48-bit fetch groups. A fetch group is exactly 2 cells. Instruction encodings are 12, 24, or 48 bits, and no instruction may cross a fetch-group boundary.

## Fetch-group Definition

| Term | Definition |
| --- | --- |
| Fetch group size | 2 cells = 48 bits |
| Fetch group base | `PCC.address & ~1` |
| First group cell | Even cell address |
| Second group cell | Odd cell address |
| Address unit | Cell address, not byte address |

If `PCC.address` is odd, the fetch group still begins at the previous even cell. The front end selects the current cell and slot from `PCC.address` plus the hidden slot bit.

## Legal Instruction Placements

| Instruction size | Legal placement | Illegal placement |
| ---: | --- | --- |
| 12-bit | Slot 0 or slot 1 of either cell | None, if the instruction itself is a valid 12-bit encoding |
| 24-bit | Slot 0 of either cell | Slot 1 |
| 48-bit | Slot 0 of the first fetch-group cell | Slot 1, or slot 0 of the second fetch-group cell |

No instruction may consume bits from the next fetch group.

## Fetch-group Layout Examples

For a fetch group starting at cell `0x1000`:

| Start location | Legal sizes | Notes |
| --- | --- | --- |
| Cell `0x1000`, slot 0 | 12, 24, 48 | First cell of group. |
| Cell `0x1000`, slot 1 | 12 | Slot 1 is only for packed 12-bit instructions. |
| Cell `0x1001`, slot 0 | 12, 24 | Second cell of group. A 48-bit instruction here would cross the group boundary. |
| Cell `0x1001`, slot 1 | 12 | Falls through to cell `0x1002`, slot 0. |

## Control-transfer Target Rules

Direct control transfers encode cell addresses only:

- Direct branch targets are cell addresses.
- Direct call targets are cell addresses.
- Trap vector targets are cell addresses.

Explicit control transfers enter at slot 0. Slot 1 has no direct architectural address.

Indirect control transfers must resolve to slot 0. If an indirect jump or return capability carries or implies slot 1, the transfer raises `ALIGN_FAULT`.

## Fault Rules

| Fault case | Exception |
| --- | --- |
| 24-bit instruction start at slot 1 | `ALIGN_FAULT` |
| 48-bit instruction start at slot 1 | `ALIGN_FAULT` |
| 48-bit instruction start at second fetch-group cell | `ALIGN_FAULT` |
| Explicit branch/call/trap/return target enters slot 1 | `ALIGN_FAULT` |

Invalid opcode contents still raise the ordinary illegal-instruction exception. `ALIGN_FAULT` is for legal or recognizable instruction-size placement attempted at an invalid cell or slot boundary.

## Encoding Philosophy

| Size | Intended use |
| ---: | --- |
| 12-bit | Short, common, simple operations |
| 24-bit | Normal instruction size |
| 48-bit | Long immediates, far branches/calls, CSR long form, capability operations |

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- Encode and decode packed 12-bit instructions in both cells of a fetch group.
- Decode a 24-bit instruction at slot 0 of the first cell.
- Decode a 24-bit instruction at slot 0 of the second cell.
- Decode a 48-bit instruction at slot 0 of the first cell.
- Reject a 24-bit instruction placed at slot 1.
- Reject a 48-bit instruction placed at slot 1.
- Reject a 48-bit instruction placed at slot 0 of the second cell.
- Confirm direct branch, call, and trap targets name only cell addresses.
- Confirm explicit slot-1 targets raise `ALIGN_FAULT`.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Instructions may be 12, 24, or 48 bits. | Met. |
| Fetch always operates on a 48-bit fetch group. | Met. |
| No instruction may cross a 48-bit fetch-group boundary. | Met. |
| 24-bit cell boundaries are the only legal direct branch, call, and trap targets. | Met: direct targets encode cell addresses and enter slot 0. |
| 48-bit instructions must begin at slot 0 of the first cell in a fetch group. | Met. |


# Language ABI Supplement

Story: I09-S02

Status: Draft implementation profile

Owner sources:

- E05-S01 and E05-S02 define the public integer and capability calling convention.
- E15-S06 records the software contract matrix.
- I09-S01 defines the trap-frame and context-switch ABI supplement.

## Public Call Boundary

The CPU v0.1 language ABI uses cell-addressed stack objects. A public call boundary enters with `DSC.cursor` aligned to 4 cells.

| Value kind | Register arguments | Return registers | Overflow slot |
| --- | --- | --- | --- |
| Integer | `D0-D5` | `D0-D1` | 2 cells, 2-cell aligned |
| Capability | `C0-C3` | `C0` | 4 cells plus tag, 4-cell aligned |

`D0-D11` and `C0-C5` are caller-saved. `D12-D15` and `C6-C7` are callee-saved.

## Mixed Overflow Layout

Overflow arguments are assigned in source order after the register windows for their value kind are exhausted.

The overflow area starts at offset 0 relative to the entry `DSC.cursor` chosen by the caller. Each stack argument is aligned to its slot alignment before placement:

- integer overflow arguments use 2-cell slots;
- capability overflow arguments use 4-cell slots and require tag-preserving stores;
- the total overflow area is padded to preserve 4-cell public stack alignment.

For example, after six integer and four capability register arguments are consumed, the next integer argument uses cells `[0, 2)`, the next capability argument is aligned to cells `[4, 8)`, and the next integer argument uses cells `[8, 10)`. The total overflow area is padded to 12 cells.

## Spill Rules

Integer spills and integer overflow arguments use `ST48`/`LD48`.

Capability spills and capability overflow arguments use `CSC`/`CLC` so payload and tag move together. Integer stores are not a valid capability spill mechanism and cannot preserve capability tags.

This ABI is a software convention. Hardware does not preserve caller-saved or callee-saved registers automatically.

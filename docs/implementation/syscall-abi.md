# Syscall ABI Supplement

Story: I09-S03

Status: Draft implementation profile

Owner sources:

- E04-S04 defines `SYS` and `SCALL` as the same precise synchronous software trap.
- E05-S01 defines the integer syscall convention.
- E05-S02 defines the capability syscall convention.
- E15-S06 records the software contract matrix.

## Trap Instruction

`SYS` is the canonical syscall instruction mnemonic. `SCALL` is a source-level synonym and assembles to the same canonical operation.

Both spellings raise `SYSCALL_TRAP`, do not advance `PCC` before trap entry, and leave register preservation policy to the operating-system ABI.

## Register Convention

| Role | Location |
| --- | --- |
| Syscall service number | `D0` |
| Integer arguments | `D1-D5`, then mixed overflow stack layout |
| Integer returns | `D0-D1` |
| Capability arguments | `C0-C3`, then mixed overflow stack layout |
| Capability return | `C0` |

The overflow layout is the same cell-addressed layout defined by `docs/implementation/language-abi.md`: integer slots are 2 cells, capability slots are 4 cells plus tag, and the total overflow area preserves 4-cell public stack alignment.

## Volatility

User code must treat `D0-D11` and `C0-C5` as volatile across a syscall unless a narrower OS ABI explicitly preserves more state.

Capability authority can cross the syscall boundary only through capability registers or tagged capability overflow slots. Integer payload copies of capability bits do not carry authority.

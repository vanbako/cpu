# E04-S04: Control Transfer Instructions

Story: E04-S04

Status: Complete

Normative source: `design.md`, sections 3.4, 7.3, 9, 10.1, 10.2, 10.3, and 10.5

Prerequisites:

- `spec/E04-S01-instruction-fetch-groups.md`
- `spec/E06-S03-sealed-return-capabilities.md`
- `spec/E07-S04-trap-entry.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S01-pcc-execute-authority.md`
- `spec/E06-S04-protected-return-stack-access.md`
- `spec/E07-S01-privilege-levels.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E07-S06-nested-interrupt-rules.md`

## Decision

CPU v0.1 defines these control-transfer and control-flow-adjacent instructions:

| Instruction | Required privilege | Summary |
| --- | --- | --- |
| `BRA target` | `U` | Unconditional direct branch. |
| `Bcc target` | `U` | Conditional direct branch using `SR.Z`, `SR.N`, `SR.C`, and `SR.V`. |
| `CALL target` | `U` | Direct call with sealed return-capability push through `RSC`. |
| `RET` | `U` | Return by popping and validating a sealed return capability through `RSC`. |
| `JMP Cs` | `U` | Indirect jump through an executable general capability. |
| `BRK` | `U` | Precise breakpoint synchronous trap. |
| `SYS` / `SCALL` | `U` | Precise syscall/software synchronous trap. |
| `IRET` | `K` | Trap return through `EPCC`, `SR.PIE`, and `SR.PPRIV`. |
| `EPCCRD Cd, Dd` | `K` | Slot-aware read of `EPCC` for software trap frames. |
| `EPCCWR Cs, Ds` | `K` | Slot-aware write of `EPCC` for software trap frames. |
| `WFI` | `K` | Wait-for-interrupt or implementation-defined low-power wait hint. |
| `PAUSE` | `U` | Spin-wait hint with no architectural side effects beyond normal retirement. |

Exact opcode bit assignments, immediate layouts, and compact aliases are assigned by E04-S06 and the final opcode story. This story defines architectural behavior.

`SYS` is the canonical mnemonic for the software-trap instruction. `SCALL` is an accepted assembler synonym unless the final opcode story deliberately reserves a distinct spelling.

## Common Control-transfer Rules

All control-transfer instructions execute at a precise architectural retire point.

On success, a control-transfer instruction commits all of its architectural effects together. On fault, none of its normal effects commit, and the faulting instruction is reported through E07-S03 and E07-S04.

Successful ordinary control transfers increment `INSTRET` once. `BRK`, `SYS`, and `SCALL` are synchronous traps and do not increment `INSTRET`. Faulting instructions do not increment `INSTRET`.

Control-transfer instructions do not modify `SR.Z`, `SR.N`, `SR.C`, or `SR.V`.

Except for `IRET`, explicit control transfers enter slot 0 and set `SR.SLOT=0` because `SR.SLOT` mirrors `PCC.slot`.

`IRET` is the only v0.1 instruction that may install `PCC.slot=1`. It restores the slot captured in `EPCC`.

## Direct Target Rules

Direct branch and direct call operands denote cell addresses. They do not denote byte addresses and they do not encode a slot.

For direct control transfers, hardware forms:

```text
target_cell = decoded direct target cell address
target_slot = 0
```

The final encoding story may choose absolute, PC-relative, short, or long immediate forms. After decoding, the architectural target is still a cell address.

A taken direct branch or direct call uses the current `PCC` as the execution authority for the target:

```text
next_pcc.payload = current PCC.payload with cursor = target_cell
next_pcc.tag     = current PCC.tag
next_pcc.slot    = 0
```

Required checks:

| Check | Failure |
| --- | --- |
| `current PCC.tag` is valid | Capability tag fault with `FAULTCAPIDX=PCC`. |
| `current PCC` is unsealed | Capability seal/type fault with `FAULTCAPIDX=PCC`. |
| `current PCC` has `EX` | Capability permission fault with `FAULTCAPIDX=PCC`. |
| `target_cell` is representable as a 48-bit cell address | Capability bounds fault with `FAULTCAPIDX=PCC`. |
| `target_cell` is inside `current PCC.bounds` | Capability bounds fault with `FAULTCAPIDX=PCC`. |
| `target_slot = 0` | Always met for direct v0.1 targets. |

`TVAL` reports `target_cell` for direct-target bounds or representability failures when representable, otherwise `0`.

A direct conditional branch that is not taken does not validate the target address for bounds or execute permission. It follows the normal sequential fall-through rules from E06-S01.

## Conditional Branch Conditions

`Bcc` reads the current condition flags in `SR`.

The mandatory condition namespace is:

| Condition | Meaning | Predicate |
| --- | --- | --- |
| `AL` | Always | `true` |
| `EQ` | Equal / zero | `Z = 1` |
| `NE` | Not equal / nonzero | `Z = 0` |
| `CS` | Carry set / unsigned higher-or-same | `C = 1` |
| `HS` | Alias of `CS` | `C = 1` |
| `CC` | Carry clear / unsigned lower | `C = 0` |
| `LO` | Alias of `CC` | `C = 0` |
| `MI` | Minus / negative | `N = 1` |
| `PL` | Plus / nonnegative | `N = 0` |
| `VS` | Overflow set | `V = 1` |
| `VC` | Overflow clear | `V = 0` |
| `HI` | Unsigned higher | `C = 1 and Z = 0` |
| `LS` | Unsigned lower-or-same | `C = 0 or Z = 1` |
| `GE` | Signed greater-or-equal | `N = V` |
| `LT` | Signed less-than | `N != V` |
| `GT` | Signed greater-than | `Z = 0 and N = V` |
| `LE` | Signed less-or-equal | `Z = 1 or N != V` |

The flag meanings follow E01-S06. `CMP` and `CMPU` use the same flag calculations; signed and unsigned branch conditions interpret those flags differently.

An encoding that names an unassigned condition code raises `ILLEGAL_INSTRUCTION`.

## `BRA`

`BRA target` is an unconditional direct branch.

Architectural effect:

```text
PCC = direct_target(current PCC, target)
PCC.slot = 0
SR.SLOT = 0
```

`BRA` performs the direct target checks above. On success, it commits only the `PCC` and `SR.SLOT` control-transfer update.

## `Bcc`

`Bcc target` is a conditional direct branch.

Architectural effect:

```text
if condition_true(cc, SR):
    PCC = direct_target(current PCC, target)
    PCC.slot = 0
    SR.SLOT = 0
else:
    PCC = sequential_next_pcc
    SR.SLOT = sequential_next_slot
```

When the condition is false, `Bcc` is a normal fall-through instruction. It does not check direct-target bounds and does not fault because of an unreachable branch target.

When the condition is true, `Bcc` performs the same direct target checks as `BRA`.

## `JMP`

`JMP Cs` is an indirect jump through a general capability register.

General capability registers do not carry a hidden slot bit, so `JMP` always enters slot 0.

Required checks:

| Check | Failure |
| --- | --- |
| `Cs.tag` is valid | Capability tag fault with `FAULTCAPIDX=Cs`. |
| `Cs` is unsealed | Capability seal/type fault with `FAULTCAPIDX=Cs`. |
| `Cs` has `EX` | Capability permission fault with `FAULTCAPIDX=Cs`. |
| `Cs.cursor` is inside `Cs.bounds` | Capability bounds fault with `FAULTCAPIDX=Cs`. |

On success:

```text
PCC.payload = Cs.payload
PCC.tag     = Cs.tag
PCC.slot    = 0
SR.SLOT     = 0
```

`JMP` does not alter `Cs`, `RSC`, memory, or condition flags.

## `CALL`

`CALL target` is a direct call using the protected return stack.

`CALL` computes the continuation according to E06-S03:

| Call instruction location | Return continuation |
| --- | --- |
| 12-bit `CALL` at slot 0 | Next cell, slot 0 |
| 12-bit `CALL` at slot 1 | Next cell, slot 0 |
| 24-bit `CALL` at slot 0 | Next cell, slot 0 |
| 48-bit `CALL` at fetch-group slot 0 | Next fetch group, slot 0 |

`CALL` then prepares:

```text
continuation = slot-0 call continuation
return_cap   = derive current PCC with cursor = continuation
return_cap.otype = OTYPE_RETURN
return_cap.G     = 0
next_pcc     = direct_target(current PCC, target)
```

It uses the protected push transaction from E05-S04 and E06-S04:

```text
target_slot = RSC.cursor - 4
next_rsc_cursor = target_slot
```

Required checks:

- Current `PCC` passes execute-authority checks.
- The slot-0 continuation is representable and inside current `PCC.bounds`.
- The direct call target passes the direct target checks above.
- `RSC` authorizes the protected return-stack push according to E05-S04 and E06-S04.
- The return capability is a valid sealed local `OTYPE_RETURN` capability as defined by E06-S03.

At retire, successful `CALL` commits as one architectural action:

- Store the 96-bit return-capability payload to the protected return-stack slot.
- Set the memory tag for that slot.
- Set `RSC.cursor = next_rsc_cursor`.
- Install `next_pcc` into `PCC`.
- Set `PCC.slot = 0`.
- Set `SR.SLOT = 0`.

If any check fails, `CALL` commits none of those effects. In particular, a faulting `CALL` does not push a return capability and does not change `RSC.cursor` or `PCC`.

Target or continuation failures through current `PCC` report capability faults with `FAULTCAPIDX=PCC`. Protected return-stack failures report the named return-stack causes from E05-S04, E06-S04, and E07-S02.

## `RET`

`RET` returns through the protected return stack.

It uses the protected pop transaction from E05-S04 and E06-S04:

```text
target_slot = RSC.cursor
next_rsc_cursor = RSC.cursor + 4
return_cap = memory capability at target_slot
next_pcc = unsealed return_cap, slot 0
```

Required checks:

- `RSC` authorizes the protected pop.
- `target_slot` names a valid active protected return-stack entry.
- The loaded memory tag is valid.
- The loaded capability is sealed with `OTYPE_RETURN`.
- The loaded capability has `G=0`.
- The loaded capability has `EX`.
- The loaded capability cursor is inside its bounds.
- The return target is slot 0.

At retire, successful `RET` commits as one architectural action:

```text
RSC.cursor = next_rsc_cursor
PCC.payload = next_pcc.payload
PCC.tag = next_pcc.tag
PCC.slot = 0
SR.SLOT = 0
```

`RET` does not expose the unsealed return capability in a general capability register.

If any check fails, `RET` leaves `RSC`, `PCC`, return-stack memory, and return-stack memory tags unchanged.

## `BRK`

`BRK` is a precise synchronous breakpoint trap.

It raises:

```text
CAUSE = BREAKPOINT
TVAL = faulting PCC.cursor
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

Trap entry follows E07-S04. `EPCC` captures the faulting `PCC` payload, tag, and hidden slot. `BRK` does not advance `PCC` before trap entry and does not retire as a normal instruction.

If a kernel or debugger policy wants to resume after the breakpoint instruction, privileged software must advance the saved return PC according to the decoded instruction size before executing `IRET`.

Detailed debug halt behavior for breakpoints is deferred to E12. Until then, `BRK` uses the normal synchronous trap path.

## `SYS` / `SCALL`

`SYS` and `SCALL` raise the same precise synchronous software trap.

They raise:

```text
CAUSE = SYSCALL_TRAP
TVAL = faulting PCC.cursor
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

Trap entry follows E07-S04. `EPCC` captures the faulting `PCC` payload, tag, and hidden slot. `SYS` and `SCALL` do not advance `PCC` before trap entry and do not retire as normal instructions.

User mode may execute `SYS` or `SCALL`; it is the normal user-to-kernel service request path. Kernel mode may also execute the instruction if its software policy wants to enter the same trap path.

The baseline v0.1 syscall ABI passes service numbers and arguments in registers. If the final opcode story assigns a syscall immediate field, that story must define whether the immediate is visible to software; it must not change the baseline `CAUSE` or `EPCC` behavior defined here.

## Slot-aware `EPCC` Transfer Helpers

E02-S05 deliberately keeps ordinary `CCSRRD` and `CCSRWR` payload-only with respect to `PCC.slot` and `EPCC.slot`.

E07-S06 requires fully general software trap frames to preserve and restore `EPCC.slot`. E04-S04 therefore defines two privileged trap-state helper operations. They are not scalar CSR instructions and they are not ordinary CCSR accesses.

`EPCCRD Cd, Dd` reads the current exception PC capability and its hidden slot:

```text
Cd.payload = EPCC.payload
Cd.tag     = EPCC.tag
Dd         = zero_extend(EPCC.slot)
```

`EPCCWR Cs, Ds` writes the current exception PC capability and hidden slot:

```text
EPCC.payload = Cs.payload
EPCC.tag     = Cs.tag
EPCC.slot    = Ds[0]
```

Rules:

- Both operations require `SR.PRIV = K`.
- User-mode execution raises `PRIVILEGE_FAULT`.
- `EPCCRD` copies an invalid `EPCC` tag as an invalid general capability tag.
- `EPCCWR` copies the source tag exactly and cannot create a valid tag from integer data.
- `EPCCWR` consumes only `Ds[0]` as the slot value; `Ds[47:1]` are ignored.
- `EPCCWR` does not validate that the resulting `EPCC` can be used by `IRET`; `IRET` performs the return-target checks.
- `EPCCWR` does not change `PCC` or `SR.SLOT`.

These helpers are the v0.1 slot-aware trap-state restore path referenced by E07-S06.

## `IRET`

`IRET` returns from trap or interrupt state by consuming the current `EPCC`, `SR.PIE`, and `SR.PPRIV`.

`IRET` is privileged. If executed when `SR.PRIV != K`, it raises `PRIVILEGE_FAULT` and commits no normal effects.

Before committing, `IRET` checks:

| Check | Failure |
| --- | --- |
| `EPCC.tag` is valid | Capability tag fault with `FAULTCAPIDX=EPCC`. |
| `EPCC` is unsealed | Capability seal/type fault with `FAULTCAPIDX=EPCC`. |
| `EPCC` has `EX` | Capability permission fault with `FAULTCAPIDX=EPCC`. |
| `EPCC.cursor` is inside `EPCC.bounds` | Capability bounds fault with `FAULTCAPIDX=EPCC`. |
| `EPCC.slot` is 0 or 1 | `ALIGN_FAULT`. |

On success, `IRET` commits atomically:

```text
PCC.payload = EPCC.payload
PCC.tag     = EPCC.tag
PCC.slot    = EPCC.slot
SR.SLOT     = EPCC.slot

SR.IE       = SR.PIE
SR.PRIV     = SR.PPRIV
SR.EXL      = 0
```

`IRET` leaves `SR.PIE`, `SR.PPRIV`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX` unchanged.

`IRET` does not clear interrupt pending bits. If it restores `SR.IE=1` and a maskable interrupt is pending and enabled, interrupt delivery may occur at the next precise boundary before the restored context executes its first instruction.

`IRET` may install `PCC.slot=1` only from `EPCC.slot`. The following fetch still obeys E01-S05 and E04-S01. If the restored slot-1 location does not contain a legal 12-bit instruction start, the next fetch raises `ALIGN_FAULT` as a new precise exception.

If any `IRET` check fails, none of the restore effects commit. The resulting synchronous exception follows E07-S04 and may overwrite the current one-level trap state as described by E07-S06.

## `WFI`

`WFI` is a privileged wait-for-interrupt instruction.

If executed when `SR.PRIV != K`, it raises `PRIVILEGE_FAULT` and commits no normal effects.

Interrupt delivery is checked at the precise boundary before `WFI` can start, just as for any other instruction. If an ordinary maskable interrupt is already deliverable at that boundary, interrupt entry occurs and `WFI` does not retire.

If `WFI` retires, it advances `PCC` to the normal fall-through location and may place the core into an implementation-defined wait or low-power state. Entering or leaving that wait state has no architectural register or memory side effect.

A waiting core must resume for reset, fatal platform events, debug events once E12 defines them, or an interrupt/event condition recognized by the implementation. After wakeup:

- If a maskable interrupt is deliverable, E07-S05 interrupt entry occurs at the current precise boundary.
- If no maskable interrupt is deliverable, execution continues at the fall-through `PCC`.

`WFI` does not set or clear `IPENDING`, `IENABLE`, `SR.IE`, or `SR.EXL`.

## `PAUSE`

`PAUSE` is a user-mode execution hint for spin loops and short waits.

Architectural effect:

```text
PCC = sequential_next_pcc
SR.SLOT = sequential_next_slot
```

`PAUSE` does not read or write memory, CSRs, capability registers, integer registers, condition flags, interrupt pending bits, or privilege state.

An implementation may use `PAUSE` to reduce contention, release pipeline resources, or bias scheduling. It may also execute `PAUSE` as a normal no-op with fall-through. Software must not rely on any timing guarantee.

## Fault Priority Notes

Fetch, instruction-placement, and malformed-encoding checks occur before the instruction-specific behavior in this story.

For decoded control-transfer instructions, the baseline instruction-specific order is:

1. Check instruction privilege for `IRET`, `EPCCRD`, `EPCCWR`, and `WFI`.
2. Decode condition-code fields for `Bcc`.
3. Evaluate direct branch condition.
4. Check source capability operands for `JMP`, `CALL`, `RET`, and `IRET`.
5. Check direct or indirect target bounds and slot rules.
6. Check protected return-stack transaction requirements for `CALL` and `RET`.
7. Commit normal effects or raise the selected synchronous exception.

`BRK`, `SYS`, and `SCALL` are explicit synchronous traps. They take priority over ordinary maskable interrupts at the same boundary according to E07-S03.

## Out of Scope for This Story

- Exact opcode bit assignments, immediate field widths, branch ranges, and compact aliases: E04-S06 and the final opcode story.
- Sealed entry capabilities and `CALLC`: E06-S02.
- Integer instruction flag producers beyond the E01-S06 baseline.
- Full debug halt, debug breakpoint, single-step, and debug resume behavior: E12 stories.
- Branch prediction, return-address prediction, and mispredict recovery: E13-S04.
- Counter behavior while halted or waiting beyond the `INSTRET` baseline above: E12-S04 and E12-S05.
- Instruction-cache synchronization and self-modifying-code ordering: E08-S04.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- `BRA` installs a slot-0 direct target.
- `BRA` outside current `PCC.bounds` raises capability bounds fault with `FAULTCAPIDX=PCC`.
- A false `Bcc` falls through and does not validate an out-of-bounds direct target.
- A true `Bcc` validates and installs a slot-0 direct target.
- Every mandatory condition code maps to the specified `SR` flag predicate.
- Unassigned condition-code encodings raise `ILLEGAL_INSTRUCTION`.
- `JMP Cs` rejects invalid, sealed, non-executable, or out-of-bounds source capabilities.
- `JMP Cs` installs a slot-0 `PCC` on success.
- `CALL` derives a sealed local return capability with a slot-0 continuation.
- `CALL` commits return-slot payload, return-slot tag, `RSC.cursor`, and `PCC` together.
- Faulting `CALL` leaves return-stack memory, tags, `RSC`, and `PCC` unchanged.
- `RET` pops only through `RSC`.
- `RET` rejects invalid, unsealed, wrong-type, global, non-executable, or out-of-bounds return capabilities.
- `RET` commits `RSC.cursor` and `PCC` together.
- Faulting `RET` leaves `RSC`, `PCC`, return-stack memory, and return-stack tags unchanged.
- `BRK` raises `BREAKPOINT` with `TVAL` equal to the faulting instruction cell.
- `SYS` and `SCALL` raise `SYSCALL_TRAP` with `TVAL` equal to the faulting instruction cell.
- `BRK`, `SYS`, and `SCALL` capture the faulting slot in `EPCC`.
- User-mode `IRET`, `EPCCRD`, `EPCCWR`, and `WFI` raise `PRIVILEGE_FAULT`.
- `EPCCRD` exposes `EPCC.slot` in an integer register.
- `EPCCWR` restores `EPCC.payload`, `EPCC.tag`, and `EPCC.slot`.
- `IRET` restores `PCC` payload, tag, and slot from `EPCC`.
- `IRET` restores `SR.IE` from `SR.PIE`, `SR.PRIV` from `SR.PPRIV`, and clears `SR.EXL`.
- Faulting `IRET` commits none of the restore effects.
- `WFI` has no register or memory side effects beyond normal fall-through before wait.
- User-mode `PAUSE` retires as a fall-through hint and does not alter flags or interrupt state.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `BRA`, `Bcc`, `CALL`, `RET`, `JMP`, `BRK`, `SYS` or `SCALL`, `IRET`, `WFI`, and `PAUSE` are defined. | Met. |
| Direct target slot rules are enforced. | Met: direct targets are cell addresses and enter slot 0. |
| Conditional branch conditions map to status flags. | Met: the mandatory condition namespace maps to `SR.Z`, `SR.N`, `SR.C`, and `SR.V`. |
| `CALL` and `RET` semantics are compatible with the protected return stack. | Met: `CALL` and `RET` use the E05-S04/E06-S04 protected transactions. |
| `IRET`, `WFI`, and privileged forms enforce privilege rules. | Met: `IRET`, `EPCCRD`, `EPCCWR`, and `WFI` require `K` privilege. |

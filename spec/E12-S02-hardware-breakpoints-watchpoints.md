# E12-S02: Hardware Breakpoints and Watchpoints

Story: E12-S02

Status: Complete

Normative source: `design.md`, section 15

Prerequisite:

- `spec/E12-S01-debug-halt-behavior.md`

Related sources:

- `spec/E02-S03-extended-csr-space.md`
- `spec/E07-S02-exception-classes.md`
- `spec/E07-S03-precise-exception-model.md`
- `spec/E09-S07-effective-access-rule.md`
- `spec/E13-S03-hazard-handling.md`

## Decision

CPU v0.1 defines a small mandatory hardware breakpoint/watchpoint facility:

- Two instruction breakpoint comparators.
- Two data watchpoint comparators.
- Cell-addressed match granularity.
- Optional ASID matching.
- User/kernel privilege masks.
- Debug event delivery through the E12-S01 `DEBUG_HALT` path.

The comparators are per-core architectural debug state. They are controlled by kernel-only scalar CSRs in the extended debug CSR range reserved by E02-S03.

## Debug Comparator CSRs

E12-S02 assigns CSR numbers `0x4C-0x53`:

| CSR number | Name | Access | Reset | Purpose |
| ---: | --- | --- | ---: | --- |
| `0x4C` | `IBP0ADDR` | K `RW` | `0` | Instruction breakpoint 0 virtual cell address. |
| `0x4D` | `IBP0CTL` | K `WARL` | `0` | Instruction breakpoint 0 control. |
| `0x4E` | `IBP1ADDR` | K `RW` | `0` | Instruction breakpoint 1 virtual cell address. |
| `0x4F` | `IBP1CTL` | K `WARL` | `0` | Instruction breakpoint 1 control. |
| `0x50` | `DWP0ADDR` | K `RW` | `0` | Data watchpoint 0 virtual cell address. |
| `0x51` | `DWP0CTL` | K `WARL` | `0` | Data watchpoint 0 control. |
| `0x52` | `DWP1ADDR` | K `RW` | `0` | Data watchpoint 1 virtual cell address. |
| `0x53` | `DWP1CTL` | K `WARL` | `0` | Data watchpoint 1 control. |

User-mode access to these CSRs raises `CSR_PRIVILEGE_FAULT`.

Unsupported or unimplemented comparator state must read as zero after reset. A conforming v0.1 implementation must implement all eight CSRs above.

## Instruction Breakpoint Control

`IBP0CTL` and `IBP1CTL` share this layout:

| Bits | Name | Meaning |
| ---: | --- | --- |
| `0` | `EN` | Enable this comparator. |
| `1` | `SLOTEN` | Match the hidden slot bit when set. |
| `2` | `SLOT` | Slot value to match when `SLOTEN=1`. |
| `3` | `MATCH_U` | Match user-mode fetches. |
| `4` | `MATCH_K` | Match kernel-mode fetches. |
| `5` | `ASIDEN` | Compare active ASID against `ASID`. |
| `7:6` | `RES0` | Reserved-zero. |
| `15:8` | `ASID` | ASID value to match when `ASIDEN=1`. |
| `47:16` | `RES0` | Reserved-zero. |

Reserved-zero writes raise `ILLEGAL_CSR_WRITE` and leave the CSR unchanged.

If `EN=1` but both `MATCH_U=0` and `MATCH_K=0`, the comparator is enabled but cannot match any current privilege mode.

`IBPADDR` values are 48-bit virtual cell addresses. They do not encode a byte offset.

## Data Watchpoint Control

`DWP0CTL` and `DWP1CTL` share this layout:

| Bits | Name | Meaning |
| ---: | --- | --- |
| `0` | `EN` | Enable this comparator. |
| `1` | `MATCH_LOAD` | Match load-like accesses. |
| `2` | `MATCH_STORE` | Match store-like accesses. |
| `3` | `MATCH_ATOMIC` | Match `LL48` and `SC48` accesses. |
| `4` | `MATCH_CAP` | Match capability load/store accesses. |
| `5` | `ASIDEN` | Compare active ASID against `ASID`. |
| `7:6` | `LEN` | Watched range length. |
| `15:8` | `ASID` | ASID value to match when `ASIDEN=1`. |
| `16` | `MATCH_U` | Match user-mode data accesses. |
| `17` | `MATCH_K` | Match kernel-mode data accesses. |
| `47:18` | `RES0` | Reserved-zero. |

`LEN` encodings:

| `LEN` | Watched range |
| ---: | ---: |
| `0b00` | 1 cell |
| `0b01` | 2 cells |
| `0b10` | 4 cells |
| `0b11` | 16 cells |

Reserved-zero writes raise `ILLEGAL_CSR_WRITE` and leave the CSR unchanged.

If `EN=1` but no access-class bit or no privilege bit can match, the comparator is enabled but cannot trigger.

`DWPADDR` values are 48-bit virtual cell addresses. They name the base of the watched range. The base need not be aligned to the watched length, but portable software should align watch ranges to their natural size to avoid surprising overlap matches.

## Match Address Space

Hardware breakpoint and watchpoint comparators match virtual cell addresses.

Instruction breakpoints compare:

```text
candidate_cell = current instruction virtual cell address
candidate_slot = current instruction hidden slot
```

Data watchpoints compare:

```text
access_range = [effective_virtual_cell, effective_virtual_cell + object_cells)
watch_range  = [DWPADDR, DWPADDR + watched_cells)
```

A data watchpoint matches if the two ranges overlap.

If `ASIDEN=1`, the active ASID from the current translation context must equal the comparator `ASID` field. In `SATP.MODE=BARE`, ASID matching is not meaningful; comparators with `ASIDEN=1` do not match. Comparators with `ASIDEN=0` may match in either bare or translated mode.

## Instruction Breakpoint Match

Instruction breakpoint matching occurs after instruction fetch authority and placement are known, but before the instruction commits any normal effect.

Fault priority:

1. Fetch capability, bounds, alignment, translation, page, memory-type, and physical access faults are reported normally.
2. If fetch succeeds and an enabled instruction breakpoint matches the instruction cell, slot, privilege, and ASID, a debug event is accepted with `DCAUSE=HW_BREAKPOINT`.
3. Malformed or unsupported instruction decoding is checked only if no instruction breakpoint debug event is accepted.

This allows a debugger to stop before executing or decoding an instruction at a watched address, but it does not let a breakpoint bypass invalid fetch authority.

If both instruction breakpoint comparators match, comparator 0 wins for diagnostic ordering. The same `DCAUSE=HW_BREAKPOINT` is reported; implementations may expose the matching comparator number only through platform debug transport or optional future CSRs.

## Data Watchpoint Match

Data watchpoint matching applies to these access classes:

| Access class | Required control bits |
| --- | --- |
| `LD48` and ordinary integer load | `MATCH_LOAD` |
| `ST48` and ordinary integer store | `MATCH_STORE` |
| `CLC` | `MATCH_LOAD` and `MATCH_CAP` |
| `CSC` | `MATCH_STORE` and `MATCH_CAP` |
| `LL48` | `MATCH_LOAD` and `MATCH_ATOMIC` |
| `SC48` | `MATCH_STORE` and `MATCH_ATOMIC` |

The watchpoint range match is checked after effective address calculation, alignment, capability authority, translation, page privilege, page permission, memory type, and physical access checks have succeeded.

If any effective-access check fails, the ordinary architectural fault is reported and the watchpoint does not fire.

If a watchpoint matches, a debug event is accepted before the access commits any normal architectural result:

- A matching load does not write its destination.
- A matching `CLC` does not write its destination capability payload or tag.
- A matching store does not allocate a store-buffer entry.
- A matching `CSC` does not write memory payload or tag.
- A matching `LL48` does not create a reservation.
- A matching `SC48` does not test or consume the reservation and does not write a result code.

Debug entry itself clears active LL/SC reservation state according to E08-S02.

If both data watchpoint comparators match, comparator 0 wins for diagnostic ordering. The same `DCAUSE=WATCHPOINT` is reported.

## Debug Event Delivery

Hardware breakpoint and watchpoint matches use the E12-S01 debug event path.

Instruction breakpoint event:

```text
CAUSE = DEBUG_HALT
DCAUSE = HW_BREAKPOINT
TVAL = matching instruction virtual cell address
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

Data watchpoint event:

```text
CAUSE = DEBUG_HALT
DCAUSE = WATCHPOINT
TVAL = effective virtual cell address of the attempted access
CAPCAUSE = NONE
FAULTCAPIDX = NONE
```

`DEBUGCTL.MONITOR` selects whether the event enters `DEBUG_HALTED` or the debug-monitor vector. `DEBUGCTL.HALTED`, `DEBUGCTL.HALTREQ`, and resume behavior follow E12-S01.

In non-monitor `DEBUG_HALTED` entry, `PCC` remains at the instruction that matched the breakpoint or attempted the watched access. Resuming without changing state re-executes the same instruction and can trigger the same comparator again.

## Privilege Behavior

Comparator CSRs are kernel-only architectural state.

Match privilege is controlled by `MATCH_U` and `MATCH_K` fields:

| Current `SR.PRIV` | Required bit |
| --- | --- |
| `U` | `MATCH_U=1` |
| `K` | `MATCH_K=1` |

Kernel mode does not bypass comparator matching. If `MATCH_K=1`, kernel instruction fetches and data accesses can trigger debug events.

Instruction breakpoints and watchpoints do not match while the core is in `DEBUG_HALTED`.

To avoid mandatory nested debug semantics in v0.1, hardware breakpoint and watchpoint comparators are suppressed during debug-monitor execution entered by E12-S01. Future debug-nesting extensions may relax this rule.

## Atomicity and Precise State

Hardware breakpoint and watchpoint events are precise.

Rules:

- Older instructions have retired and their architectural effects are visible according to the normal memory model.
- The matching instruction has committed no normal effects.
- Younger instructions have committed no architectural effects.
- `INSTRET` does not increment for the matching instruction.
- Any younger in-flight work is killed or replayed according to E13-S03.
- Reporting state is updated through the E12-S01 debug event path.

For a watchpoint on a store-like instruction, no memory payload, memory tag, store-buffer entry, cache-maintenance effect, or return-stack update from that instruction is visible.

For a watchpoint on a load-like instruction, no destination register or capability destination is written.

## Out of Scope for This Story

- Single-step behavior: E12-S03.
- Extended counters for breakpoint/watchpoint events: E12-S05.
- External debugger transport, authentication, and host protocol.
- Comparator chaining, address masks, physical-address comparators, and more than two slots of each type.
- Data-value watchpoints.
- Instruction breakpoints that patch memory with `BRK`; this story defines hardware comparators only.

## Verification Notes

Minimum conformance checks for later simulator, debugger, and RTL work:

- `IBP0ADDR/CTL`, `IBP1ADDR/CTL`, `DWP0ADDR/CTL`, and `DWP1ADDR/CTL` reset to zero.
- User-mode access to comparator CSRs raises `CSR_PRIVILEGE_FAULT`.
- Reserved-zero control-bit writes raise `ILLEGAL_CSR_WRITE`.
- An enabled instruction breakpoint matching user fetch enters debug with `DCAUSE=HW_BREAKPOINT`.
- Instruction fetch capability or page faults take priority over instruction breakpoint match.
- Instruction breakpoint match can occur before illegal-instruction decode when fetch succeeds.
- Slot-specific instruction breakpoint matching distinguishes slot 0 and slot 1 12-bit instructions.
- ASID-enabled comparators match only the selected ASID in translated mode.
- Data watchpoint range overlap detects `LD48`, `ST48`, `CLC`, `CSC`, `LL48`, and `SC48` according to control bits.
- Data access faults take priority over watchpoint match.
- A matching store watchpoint creates no store-buffer entry.
- A matching `CLC` watchpoint writes no destination capability.
- A matching `LL48` watchpoint creates no reservation.
- A matching `SC48` watchpoint does not store and does not write a result code.
- Comparator 0 wins diagnostic ordering when both comparators of a class match.
- Comparators are suppressed during `DEBUG_HALTED` and debug-monitor execution.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Hardware instruction breakpoint capability is defined. | Met: two instruction breakpoint comparators are defined. |
| Hardware data watchpoint capability is defined. | Met: two data watchpoint comparators are defined. |
| Match granularity and privilege behavior are specified. | Met: cell/slot/range granularity, ASID matching, and user/kernel masks are specified. |
| Watchpoint interaction with capability and page faults is specified. | Met: effective-access faults take priority over watchpoint events. |

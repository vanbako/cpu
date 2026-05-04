# Software Contract Matrix

Story: E15-S06

Status: Complete

This matrix is a review aid for the v0.1 software-facing contract. It is not a replacement for the owning specification stories.

## Mandatory Instruction Coverage

| Class | Mandatory instruction or family | Owner | Software-facing requirement |
| --- | --- | --- | --- |
| Integer | `CPY`, `NEG`, `ADD`, `ADDU`, `SUB`, `SUBU`, `MUL`, `MULU`, `DIV`, `DIVU`, `MOD`, `MODU`, `NOT`, `AND`, `OR`, `XOR`, `SHL`, `SHRS`, `SHRU`, `ROL`, `ROR`, `CMP`, `CMPU`, `TST`, `SETcc`, `CMOVcc`, `BSET`, `BCLR` | E04-S02 | Assembler accepts canonical register forms; unsupported widths or malformed encodings fault as illegal instructions. |
| Memory | `LD48`, `ST48`, `CLC`, `CSC` | E04-S03/E04-S05 | Assembler exposes capability-authorized cell-addressed load/store forms; capability tags are preserved only by capability operations. |
| Capability derivation | `CMOVE`, `CGETADDR`, `CSETADDR`, `CINCADDR`, `CSETBOUNDS`, `CANDPERM`, `CSEAL`, `CUNSEAL` | E04-S05 | Capability payload/tag movement and monotonic derivation are available without integer tag forging. |
| Control transfer | `BRA`, `Bcc`, `CALL`, `RET`, `JMP`, `BRK`, `SYS`, `SCALL`, `IRET`, `EPCCRD`, `EPCCWR`, `WFI`, `PAUSE` | E04-S04 | Direct targets are cell addresses and enter slot 0; `SCALL` is a source synonym for `SYS`; `EPCCRD`/`EPCCWR` preserve trap-frame slots. |
| Sealed entry call | `CALLC` | E06-S02 | Sealed entry capabilities are consumed atomically and the source capability remains sealed. |
| Atomic | `LL48`, `SC48` | E08-S01/E08-S02 | `LL48`/`SC48` are the mandatory v0.1 atomic primitive; `CAS*` and generic `AMO*` are not baseline requirements. |
| Ordering | `FENCE`, `FENCE.I`, `SFENCE.VM`, `SFENCE.VM.ASID`, `SFENCE.VM.VA`, `SFENCE.VM.VA_ASID` | E08-S04 | User code may execute `FENCE`; instruction-cache and translation maintenance forms are kernel-only. |
| CSR | `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR` | E02-S04 | Scalar CSR transfers use `D0-D15`; fast selectors reach `0x00-0x0F`; long selectors reach `0x00-0xFF`. |
| CCSR | `CCSRRD`, `CCSRWR` | E02-S05 | Special capability transfers use `C0-C7` and CCSR indices; tags are copied exactly; user mode faults. |
| Cache maintenance | `CACHE.CLEAN`, `CACHE.INVAL`, `CACHE.CLEANINVAL` | E10-S05 | Privileged line-range maintenance has explicit range, translation, memory-type, and fence interactions. |

## ABI Preservation Checks

| Check | Expected result |
| --- | --- |
| Six integer arguments | Arrive in `D0-D5`. |
| Seventh integer argument | Arrives at the first 2-cell overflow slot relative to entry `DSC.cursor`. |
| Four capability arguments | Arrive in `C0-C3` with payload and tag preserved. |
| Fifth capability argument | Arrives in a 4-cell aligned capability overflow slot stored by `CSC`. |
| Normal integer return | Uses `D0`, or `D0-D1` for two integer results. |
| Normal capability return | Uses `C0` with payload and tag preserved. |
| Caller-saved integer state | `D0-D11` may be clobbered by a callee or syscall unless a narrower OS ABI says otherwise. |
| Callee-saved integer state | `D12-D15` are restored exactly before normal `RET`. |
| Caller-saved capability state | `C0-C5` may be clobbered, including tags. |
| Callee-saved capability state | `C6-C7` payload and tag are restored exactly before normal `RET`. |
| Public stack alignment | `DSC.cursor` is 4-cell aligned at call and startup handoff boundaries. |
| Capability spill | Uses `CSC`/`CLC`; local spills require `DSC` with `SL`. |
| Return state | Uses protected `RSC`; ordinary data-stack stores cannot update return-stack storage. |

## Boot-sequence Checklist

| Step | Required software-visible state |
| --- | --- |
| Boot core reset fetch | `COREID=0`, `SR.PRIV=K`, `SR.IE=0`, `SR.EXL=0`, `PCC.cursor=RESET_VECTOR`, `PCC.slot=0`. |
| Reset scalar state | Mandatory fast CSRs observe E02-S02 reset values, including `SATP=0`, `ASID=0`, `IENABLE=0`, and `DEBUGCTL=0`. |
| Reset capability authority | Boot `PCC` is valid ROM execute authority; non-handoff capability tags are invalid unless a reset profile documents valid tagged authority. |
| Early firmware setup | Firmware installs `KRC`, `KSC`, `DSC`, `RSC`, and `TVC` through trusted tagged authority before relying on them. |
| Trap enable | Firmware installs valid `TVC`, configures `TVEC`, and enables `IENABLE` plus `SR.IE` only after stack and handler authority are ready. |
| Secondary mailbox publish | Producer writes all mailbox fields, sets `READY`, executes the required ordering operation, then sends the target start signal. |
| Secondary first instruction | Target enters with `SR.PRIV=K`, `SR.IE=0`, `SR.EXL=0`, `SATP=0` unless profiled otherwise, `PCC.slot=0`, valid stack capabilities, and startup arguments in `D0` and `C0`. |

## Debug and Counter Checklist

| Scenario | Expected result |
| --- | --- |
| `BRK` with `DEBUGCTL.BRKHALT=0` | Ordinary `BREAKPOINT` synchronous trap; `EPCC` captures the faulting slot. |
| `BRK` with `DEBUGCTL.BRKHALT=1` | Debug event with `CAUSE=DEBUG_HALT` and `DCAUSE=BRK`. |
| Non-monitor halt | `PCC`, slot, `SR`, `EPCC`, registers, memory payload, and tags are preserved for inspection. |
| Debug-monitor entry | Uses vector index 4, writes the one hardware saved level, and exits with `IRET`. |
| Instruction breakpoint | Fires after fetch authority succeeds and before decode/normal effects commit. |
| Data watchpoint | Fires after effective-access checks and before load/store/atomic/capability effects commit. |
| Single-step | One eligible instruction retires, increments `INSTRET`, and then reports `DCAUSE=SINGLE_STEP`. |
| `DEBUG_HALTED` counters | `CYCLE`, `INSTRET`, and PMCs do not increment for the halted core. |
| Mandatory counters | `CYCLE` and `INSTRET` are user-readable, kernel-writable, and wrap modulo `2^48`. |
| Extended performance events | `PMC0-PMC7` are kernel-only; unsupported selectors read back as `EVENT=NONE`, `EN=0`. |

## Toolchain Assumptions

| Topic | Required custom behavior |
| --- | --- |
| Address unit | All architectural labels, relocation addends, PC values, trap values, pages, and cache lines are cell-addressed. |
| Cell serialization | Any byte-oriented object file or debug container must define how 24-bit cells are serialized. |
| Instruction placement | 12-bit instructions may use slot 0 or slot 1; 24-bit instructions use slot 0; 48-bit instructions use slot 0 of the first fetch-group cell. |
| Direct targets | Branch, call, trap, interrupt, and debug-monitor targets are cell addresses and enter slot 0. |
| Slot diagnostics | Debuggers and trap frames must preserve hidden slot state for slot-1 faults and stepped slot-0 fall-through. |
| Stack objects | Integer ABI slots are 2 cells; capability ABI slots are 4 cells plus tag; public frames preserve 4-cell alignment. |
| Capability spills | The compiler must use capability moves, `CLC`, and `CSC`; integer loads/stores do not preserve tags. |
| Unsupported baseline assumptions | A byte-addressed host ABI, hardwired zero register, byte-sized memory objects, or untagged capability serialization is not portable v0.1 behavior. |

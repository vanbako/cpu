First, make the 24-bit memory unit explicit. Your machine is **not byte-addressed**. The smallest addressable unit should have its own name in the spec, such as **cell** = 24 bits. Then everything becomes precise: a 48-bit integer load/store touches 2 cells, a 96-bit capability touches 4 cells, page sizes are counted in cells, and cache lines are counted in cells. If you do **not** name this early, the MMU, ABI, cache, and toolchain will all get muddy.

Second, do **not** freeze the architecture to exactly 16 scalar CSRs. Keep 16 as the **short-encoding fast set**, but define a larger architectural CSR namespace now. Modern designs normally use a dedicated CSR address space with dedicated instructions, and that scales much better than memory-mapped control registers. ([docs.riscv.org][1])

Third, do **not** use a CSR to return long-latency multiply/divide results. That is the wrong abstraction. Use an independent execution unit plus scoreboard/busy bits and normal register writeback. CSR is for control/state, not for “future result delivery.”

The biggest architectural consequence of going pure-capability is that **all** loads, stores, and instruction fetches are capability-governed, and pure-capability code is not binary-compatible with ordinary integer-pointer code. CHERI also relies on compressed bounds metadata plus a 1-bit out-of-band validity tag; valid capabilities in memory must be naturally aligned, partial or non-capability overwrites clear the tag, and tag/data must be stored atomically so capabilities cannot be forged. ([cl.cam.ac.uk][2])

For the open design choices, my recommendations are: **LL/SC for MVP atomics**, not CAS; **direct exceptions plus vectored interrupts**; a **TSO-like coherent memory model** from day one; **private L1s plus shared inclusive L2**; **per-core TLBs with ASIDs**; **pure-capability addressing with sealed entry capabilities and a protected return stack**; and a **small per-core 2-bit branch predictor only for direct conditional branches, plus a return stack, flushed or partitioned on context switch**. RISC-V’s rationale for LR/SC is especially relevant here: CAS needs more operands and a different memory-system message format and has ABA issues, while LR/SC is cleaner for a simple in-order design; later CAS can still be added as an optional extension if you want more highly parallel lock-free algorithms. RISC-V’s privileged architecture is also a good model for direct/vectored trap modes and the simple `xIE/xPIE/xPP` trap-state stack, while AIA shows the modern shape of per-hart interrupt files and external interrupt delivery. Stronger memory models are easier to program than weak ones, and TSO is a cleaner long-term contract than starting weak and regretting it later. Spectre-class attacks do exploit branch prediction/speculation, and context-tagged or flushed predictor state is a standard mitigation direction. ([docs.riscv.org][3])

## Final architecture document, draft 0.1

### 1. Design goals

This CPU is a **4-core, in-order, server-style, pure-capability processor** with a 48-bit architectural address space, user/kernel privilege, coherent caches, virtual memory, and strong control-flow protection.

The design priorities are:

1. simplicity of implementation,
2. security and predictability,
3. performance.

The ISA should look coherent and intentional, even if early prototypes refactor internally.

### 2. Architectural naming and address model

The smallest addressable memory unit is a **cell**.

Normative unit rules:

* 1 cell = 24 bits
* all architectural addresses are **cell addresses**
* the architecture has no architectural byte addresses
* a 48-bit architectural address names one of `2^48` cells
* address arithmetic, bounds, page sizes, cache lines, and memory ranges are counted in cells
* a memory range `[base, top)` contains `top - base` cells
* a cell address `A` identifies the 24 architectural memory bits belonging to cell `A`

Object-size rules:

* 48-bit integer values occupy **2 cells**
* 96-bit capabilities occupy **4 cells** plus one out-of-band tag bit
* a fetch group is **2 cells = 48 bits**
* the MVP base page is `2^11` cells
* the initial cache-line recommendation is 16 cells

Alignment is also defined in cells:

* an address is `N`-cell aligned when `address mod N = 0`
* `LD48` and `ST48` require 2-cell alignment
* `CLC` and `CSC` require 4-cell alignment
* instruction fetch groups require 2-cell alignment
* capability slots in memory require 4-cell alignment

Sub-cell quantities such as 8-bit, 12-bit, 16-bit, and 24-bit instruction or register fields may exist, but they are not independently addressable memory locations in v0.1. Any future byte or sub-cell load/store extension would need an explicit architectural rule for packing, sign extension, capability tag clearing, alignment, and MMU interaction.

This means the architecture is **cell-addressed**, not byte-addressed. That is internally consistent, but it also means the toolchain, ABI, object format conventions, debugger, loader, and OS memory-management code are necessarily custom. For a Unix-like server OS, this is the single biggest nonstandard choice in the whole design.

### 3. Architectural state

#### 3.1 Integer register file

* 16 general data registers: `D0-D15`
* Each register is physically 48 bits
* Operations may interpret/write them as 8/12/16/24/32/48-bit values
* Narrow write behavior is controlled by the instruction form:

  * zero-extending form
  * sign-extending form
  * full-width form

I would make this explicit in the ISA encoding, not implicit in opcode semantics.

#### 3.2 Capability register file

There are 8 general capability registers: `C0-C7`.

Each general capability register contains:

* a 96-bit architectural capability payload
* one out-of-band validity tag

The tag is architectural state but is not part of the 96-bit payload. A tagged capability is valid. An untagged capability is invalid and cannot authorize fetch, load, store, seal, unseal, or derivation operations.

General capability registers hold data capabilities, object capabilities, sealed entry capabilities, and temporary delegated authority. They do not replace the special capability registers used for `PCC`, stacks, traps, and kernel roots.

Pure-capability addressing rules:

* integer registers never directly authorize memory access
* integer addresses are never directly dereferenced in pure-capability mode
* instruction fetch is authorized by `PCC`
* explicit data loads and stores are authorized by a capability source register or by `DDC` when an instruction form explicitly uses the default data capability
* capability loads and stores require both data access permission and capability load/store permission
* invalid, sealed, out-of-bounds, or under-permissioned capabilities raise capability faults before the access commits

Tag movement rules:

* `CMOVE` copies the payload and tag
* `CLC` loads the payload and tag from a naturally aligned capability slot
* `CSC` stores the payload and tag to a naturally aligned capability slot
* ordinary integer moves, integer ALU operations, and `LD48` do not create valid capability tags
* ordinary `ST48` into a capability slot clears the memory tag for that slot

This makes `C0-C7` the only general-purpose registers that can carry dereferenceable authority. Data registers may hold integer addresses for arithmetic, offsets, indexes, syscall arguments, or diagnostics, but those integers are not pointers unless converted through explicit capability instructions that preserve monotonic authority.

#### 3.3 Special capability registers

Use the 8 special capability registers as:

* `PCC` — current program-counter capability
* `DSC` — data-stack capability
* `RSC` — return-stack capability
* `DDC` — default data capability
* `EPCC` — exception program-counter capability
* `TVC` — trap-vector capability
* `KSC` — kernel trap-stack capability
* `KRC` — kernel root capability

That gives you a clean privileged/control-flow story without inventing more state later.

#### 3.4 Program-counter subslot state

Because instructions can be 12/24/48 bits while addresses are cell-based, `PCC` and `EPCC` each carry an associated hidden **slot bit**:

* slot 0 = first instruction in the 24-bit cell
* slot 1 = second 12-bit half-instruction in the cell

Instruction start rules:

* a 12-bit instruction may start at slot 0 or slot 1
* a 24-bit instruction may start only at slot 0
* a 48-bit instruction may start only at slot 0 of the first cell in a fetch group
* no instruction may cross a 48-bit fetch-group boundary

Sequential fall-through rules:

* after a 12-bit instruction in slot 0, execution advances to slot 1 in the same cell
* after a 12-bit instruction in slot 1, execution advances to slot 0 of the next cell
* after a 24-bit instruction, execution advances to slot 0 of the next cell
* after a 48-bit instruction, execution advances to slot 0 of the next fetch group

Explicit control-transfer rules:

* direct branches enter at slot 0
* indirect jumps enter at slot 0
* calls enter at slot 0
* returns enter at slot 0
* trap and interrupt entry enter at slot 0
* `IRET` restores the slot captured in `EPCC`, but normal trap entry must have captured a valid architectural slot

Slot 1 is reachable only by sequential fall-through after a 12-bit instruction in slot 0. Any attempt to start a 24-bit or 48-bit instruction at slot 1 raises `ALIGN_FAULT`. Any explicit control transfer that would enter slot 1 also raises `ALIGN_FAULT`.

This rule makes variable-length decode much simpler and lets cell boundaries remain the only externally visible branch, call, return, and trap targets.

#### 3.5 Status register

Use one 48-bit status register `SR`, with at least these bits:

* `Z` zero
* `N` negative
* `C` carry
* `V` overflow
* `IE` interrupt enable
* `PIE` previous interrupt enable
* `PRIV` current privilege (0=user, 1=kernel)
* `EXL` exception level / in-trap
* `SLOT` current instruction slot
* remaining bits reserved

Arithmetic should **not** update flags by default. Use either dedicated `CMP/TST` or flag-setting forms of ALU instructions. That reduces false flag dependencies.

### 4. CSR architecture

Architectural CSR space should be **larger than 16 entries**. I recommend:

* **256 architectural scalar CSR numbers**
* **16 fast CSRs** accessible from short encodings
* extended CSR access through long-form CSR instructions

Mandatory scalar CSR set:

* `SR`
* `COREID`
* `CYCLE`
* `INSTRET`
* `TVEC`
* `CAUSE`
* `TVAL`
* `SCRATCH`
* `IENABLE`
* `IPENDING`
* `TIMER`
* `TIMECMP`
* `SATP`
* `ASID`
* `DEBUGCTL`
* `PERFSEL`

Extended CSR space should hold:

* `PMC0-PMC7`
* `CACHECTL`
* `TLBCTL`
* `FAULTCAPIDX`
* `CAPCAUSE`
* platform-specific interrupt controller interface

CSR access instructions:

* `CSRRD`
* `CSRWR`
* `CSRSET`
* `CSRCLR`

For special capability registers, define a parallel mechanism such as:

* `CCSRRD Cd, idx`
* `CCSRWR idx, Cs`

### 5. Capability model

#### 5.1 Capability format

For MVP, use a **96-bit capability + 1 out-of-band tag**.

* `cursor/address`: 48 bits
* `bounds metadata`: 30 bits
* `permissions`: 8 bits
* `object type`: 8 bits
* `flags`: 2 bits

The tag is not stored in addressable memory. It is carried in registers, cache, and memory tag state as separate architectural metadata.

The capability cursor is a 48-bit cell address. Bounds metadata describes a cell-addressed half-open range `[base, top)`. The cursor of a tagged v0.1 capability must be inside its decoded bounds:

* `base <= cursor < top`

This is an intentional v0.1 simplification. C-like one-past pointers and temporarily out-of-bounds tagged capability cursors are not supported in v0.1. Software should keep tentative offsets in integer registers and update the capability cursor only after checking that the resulting address remains in bounds.

`CSETADDR` and `CINCADDR` behavior:

* if the resulting cursor is inside bounds, the result keeps the input tag
* if the resulting cursor is outside bounds, the instruction raises a capability bounds fault and leaves the destination register unchanged

`CSETBOUNDS` behavior:

* requested bounds must be within the parent capability bounds
* the implementation may round representable bounds outward
* rounded bounds must still remain within the parent capability bounds
* if exact or rounded-in-parent bounds cannot be represented, the instruction raises a capability bounds fault and leaves the destination register unchanged

The E14-S01 prototype tested a 30-bit layout with a 6-bit exponent, 12-bit base mantissa, and 12-bit top mantissa. It represented small objects, base pages, reserved future page sizes, large aligned regions, near-top regions, and the full 48-bit cell address space. Keep the 30-bit bounds metadata budget for v0.1, but treat the exact compression algorithm as an implementation-facing detail until the formal capability model is written.

Permission bits:

* `LD`: permits integer/data loads through the capability
* `ST`: permits integer/data stores through the capability
* `EX`: permits instruction fetch through the capability
* `LC`: permits capability loads through the capability
* `SC`: permits capability stores through the capability
* `SL`: permits storing local capabilities through the capability
* `SEAL`: permits sealing with an authorized object type
* `UNSEAL`: permits unsealing with an authorized object type

Permission check rules:

* instruction fetch requires `EX`
* `LD48` requires `LD`
* `ST48` requires `ST`
* `CLC` requires `LD` and `LC`
* `CSC` requires `ST` and `SC`
* storing a local capability additionally requires `SL`
* `CSEAL` requires `SEAL`
* `CUNSEAL` requires `UNSEAL`
* missing `SL` for a local capability store raises a capability local-store fault and leaves destination state unchanged
* other missing required permissions raise a capability permission fault and leave destination state unchanged
* derived capabilities may clear permission bits but may not set permission bits that were clear in the source capability

Suggested flag bits:

* `G` global/local
* `R` reserved

Suggested object-type rule:

* `otype = 0` means unsealed
* `otype != 0` means sealed

E14-S01 validated that the 30-bit bounds metadata budget is plausible for v0.1. The exact codec still needs a formal model before hardware freeze. CHERI's public designs remain the right reference point for compressed bounds metadata. ([cl.cam.ac.uk][2])

#### 5.2 Capability semantics

Architectural rules:

* capabilities are **unforgeable**
* derivation is **monotonic**
* bounds may be narrowed, not widened
* permissions may be reduced, not increased
* sealed capabilities cannot be dereferenced
* sealed capabilities cannot be modified except by defined unseal or call-entry operations
* invalid-tag capabilities cannot be dereferenced or used as derivation sources
* faulting capability instructions leave destination architectural state unchanged

Tag propagation rules:

* `CMOVE` copies the source payload and tag unchanged
* `CGETADDR` copies only the cursor into an integer register
* successful derivation instructions preserve the source tag
* failed derivation instructions do not create a valid destination tag

Monotonic derivation rules:

* `CSETADDR` may change only the cursor
* `CINCADDR` may change only the cursor
* `CSETBOUNDS` may narrow bounds but may not widen bounds
* `CANDPERM` may clear permissions but may not set permissions
* `CSEAL` may convert an unsealed capability into a sealed capability with an authorized object type
* `CUNSEAL` may convert a sealed capability back to an unsealed capability only when authorized by a matching unseal capability
* no instruction may create authority not already present in one of its valid capability operands

Integer arithmetic on capability registers is forbidden except via explicit capability-address instructions:

* `CMOVE`
* `CGETADDR`
* `CSETADDR`
* `CINCADDR`
* `CANDPERM`
* `CSETBOUNDS`
* `CSEAL`
* `CUNSEAL`

#### 5.3 Memory tag rules

Normative memory tag granularity:

* memory has one tag bit per naturally aligned 4-cell capability slot
* a capability slot starts at an address where `address mod 4 = 0`
* a 16-cell cache line contains four capability tag bits
* tags are architectural metadata, not addressable memory bits

Capability load/store rules:

* `CLC` requires 4-cell alignment
* `CLC` loads all 96 payload bits and the slot tag as one architectural operation
* `CSC` requires 4-cell alignment
* `CSC` stores all 96 payload bits and the slot tag as one architectural operation
* misaligned `CLC` or `CSC` raises `ALIGN_FAULT`

Ordinary store tag-clear rules:

* `ST48` writes two cells
* if either written cell overlaps a capability slot, that slot's tag is cleared
* `ST48` may clear at most one capability-slot tag because it is 2-cell aligned
* ordinary integer stores never create valid capability tags
* `LD48` may read capability payload bits as integer data but never returns the tag

Cache and coherence rules:

* L1 data cache, L2, and memory carry tag state with cache-line data
* CPU coherence treats tag bits as part of coherent line state
* another core must not observe new capability payload with an old tag or old payload with a new tag
* E14-S04 validated the one-tag-per-4-cell-slot model through L1, L2, and memory

External overwrite rules:

* non-tag-aware DMA or external agents clear tags for every overlapped capability slot in memory
* DMA is noncoherent in v0.1, so CPU caches may hold stale data and stale tags until software performs cache maintenance
* drivers must invalidate or clean/invalidate relevant CPU cache lines before CPU reuse of DMA-written buffers

* `CSC` stores a full 96-bit capability and its tag atomically
* `CLC` loads a full 96-bit capability and its tag atomically
* any `ST48` into any of the four cells of a capability slot clears that slot’s tag
* capabilities in memory must be aligned to 4-cell boundaries
* non-tag-aware DMA or external agents clear tags on overwrite

These rules are essential if you want CHERI-like integrity rather than “fat pointers with permissions.” ([CHERI][4])

#### 5.4 Local capabilities

Local capability flag rules:

* `G=1` means global capability
* `G=0` means local capability
* local capabilities carry authority that must not be stored into ordinary global or heap memory
* global capabilities may be stored through any capability that has `ST` and `SC`
* local capabilities may be stored only through a destination capability that has `ST`, `SC`, and `SL`
* violating the local-store rule raises a capability local-store fault and leaves memory unchanged

Recommended usage:

* data stack capabilities should normally be local
* protected return stack capabilities should normally be local
* temporary delegated authority should normally be local
* heap, global, and persistent object capabilities should normally reject local capability stores unless explicitly intended

This rule prevents stack-derived and temporary authority from leaking into longer-lived memory.

Borrow one very good CHERIoT idea:

* `G=1` means global capability
* `G=0` means local capability
* local capabilities may be stored only via a capability with `SL=1`

Use that for stacks, return capabilities, and temporary delegated authority. It gives you a clean way to stop stack-derived pointers from leaking into heap/global memory. ([CHERIoT Platform][5])

### 6. Instruction encoding and fetch

Fetch always operates on one **48-bit fetch group**.

Fetch-group rules:

* a fetch group is 2 consecutive cells
* fetch-group base address is `PCC.address & ~1`
* the first cell in a fetch group has an even cell address
* the second cell in a fetch group has an odd cell address
* instruction bytes do not exist architecturally; predecode consumes instruction bits from fetched cells

Instruction sizes:

* instructions are 12, 24, or 48 bits
* no instruction may cross a 48-bit fetch-group boundary
* 12-bit instructions may start at slot 0 or slot 1
* 24-bit instructions may start only at slot 0 of either cell in a fetch group
* 48-bit instructions must start at slot 0 of the first cell in a fetch group

Target rules:

* direct branch, call, and trap targets encode cell addresses only
* direct branch, call, and trap targets always enter slot 0
* indirect jump and return targets must resolve to slot 0
* explicit slot-1 targets raise `ALIGN_FAULT`

Boundary fault rules:

* a 24-bit instruction decoded at slot 1 raises `ALIGN_FAULT`
* a 48-bit instruction decoded at slot 1 raises `ALIGN_FAULT`
* a 48-bit instruction decoded at slot 0 of the second cell in a fetch group raises `ALIGN_FAULT`

Use the following encoding philosophy:

* **12-bit**: short, common, simple operations
* **24-bit**: normal instruction size
* **48-bit**: long immediates, far branches/calls, CSR long form, capability ops

### 7. Base ISA

#### 7.1 Integer operations

Mandatory integer ops:

* `CPY`
* `NEG`
* `ADD`, `ADDU`
* `SUB`, `SUBU`
* `MUL`, `MULU`
* `DIV`, `DIVU`
* `MOD`, `MODU`
* `NOT`
* `AND`, `OR`, `XOR`
* `SHL`
* `SHRS`
* `SHRU`
* `ROL`, `ROR`
* `CMP`, `CMPU`
* `TST`
* `SETcc`
* `CMOVcc`
* `BSET`, `BCLR`

I would keep `SETcc` and `CMOVcc`. They are useful, and they do not complicate the machine much.

#### 7.2 Memory operations

Data memory:

* `LD48`
* `ST48`

Capability memory:

* `CLC`
* `CSC`

Rules:

* `LD48/ST48` require even-cell alignment
* `CLC/CSC` require 4-cell alignment
* no unaligned access of any kind
* misalignment raises `ALIGN_FAULT`

#### 7.3 Control transfer

* `BRA`
* `Bcc`
* `CALL`
* `RET`
* `JMP`
* `BRK`
* `SYS` or `SCALL`
* `IRET`
* `WFI`
* `PAUSE`

I would keep `CALL` and `RET` as ISA-level macro-ops, lowered internally to micro-ops.

#### 7.4 Capability instructions

Mandatory capability instructions:

* `CMOVE`
* `CGETADDR`
* `CSETADDR`
* `CINCADDR`
* `CSETBOUNDS`
* `CANDPERM`
* `CSEAL`
* `CUNSEAL`
* `CLC`
* `CSC`

### 8. Calling convention and stack model

This is ABI, not ISA, but you should pick a recommended ABI now so the toolchain doesn’t thrash later.

Recommended ABI:

* integer args: `D0-D5`
* integer returns: `D0-D1`
* capability args: `C0-C3`
* capability return: `C0`
* caller-saved integers: `D0-D11`
* callee-saved integers: `D12-D15`
* caller-saved capabilities: `C0-C5`
* callee-saved capabilities: `C6-C7`

Stacks:

* `DSC` is the data stack for locals/args
* `RSC` is the protected return stack
* both stacks grow downward in cells

`PUSH/POP` operate on `DSC`. `CALL/RET` operate on `RSC`.

### 9. Control-flow protection

This should be the most secure model, not the most x86-like one.

Use:

* `PCC` as an execute-authorized capability
* sealed entry capabilities for callable protected entry points
* sealed return capabilities for backward edges
* protected return stack memory reachable only by `CALL/RET` and privileged unwind/debug operations

Recommended call semantics:

* `CALL target`

  * derive return capability from current `PCC`
  * seal it as a return capability
  * push to `RSC`
  * transfer to target
* `CALLC Cs`

  * if `Cs` is a sealed entry capability, unseal-and-enter atomically
* `RET`

  * pop a sealed return capability from `RSC`
  * validate it
  * install into `PCC`

This gives you strong backward-edge and forward-edge CFI. CHERI’s sealed entry capability model is the right inspiration here. ([CHERIoT Platform][6])

### 10. Privilege, exceptions, and interrupts

#### 10.1 Privilege levels

* `U` user
* `K` kernel

No virtualization level in MVP.

#### 10.2 Exception model

All exceptions are **precise**.

Mandatory exception classes:

* illegal instruction
* breakpoint
* privilege violation
* divide by zero
* alignment fault
* access fault
* page fault
* syscall/software trap
* capability tag fault
* capability bounds fault
* capability permission fault
* capability seal/type fault
* capability local-store fault
* debug halt

#### 10.3 Trap entry

Chosen model:

* **direct exceptions**
* **vectored interrupts**

That is the best balance here: exceptions usually want a common decoder path, while interrupts benefit from low-latency vectoring. This is also the same split used by RISC-V’s `tvec/stvec` direct vs vectored trap modes. ([docs.riscv.org][7])

On trap entry, hardware saves:

* `EPCC`
* `SR.IE -> SR.PIE`
* `SR.PRIV -> previous privilege field`
* `CAUSE`
* `TVAL`
* `CAPCAUSE` on capability-related traps

That is enough for an MVP. Do **not** auto-save all GPRs. Let software decide the full trap frame.

#### 10.4 Interrupt architecture

Use this model:

* per-core local interrupt state
* timer interrupt per core
* software IPI per core
* external interrupt delivery through a platform interrupt controller
* per-core trap vector base
* interrupt enable, pending, and priority threshold CSRs

Future-proof it for an AIA-like direction:

* optional per-hart interrupt file for MSIs
* optional external controller that can deliver either direct wired interrupts or MSIs

That is the most modern path if you may want clean scaling later, and it matches the general direction of RISC-V AIA with per-hart IMSIC plus APLIC. ([docs.riscv.org][8])

#### 10.5 Nested interrupts

Use **one hardware level** of saved trap state only:

* `IE`
* `PIE`
* previous privilege

Then allow deeper nesting only after software has saved a trap frame and explicitly re-enabled interrupts.

That is the simplest correct solution, and it mirrors the logic behind RISC-V’s `xIE/xPIE/xPP` model. ([docs.riscv.org][7])

### 11. Atomics and memory ordering

#### 11.1 Chosen atomic primitive

For MVP, choose **LL/SC on aligned 48-bit words**:

* `LL48`
* `SC48`

Rules:

* alignment required to 2-cell boundary
* reservation granule is at least the accessed word and may be the cache line
* `SC48` may fail spuriously
* progress guarantee: absent conflicting stores and repeated interruptions, bounded retry loops eventually succeed

This is the right choice for your design. RISC-V explicitly documents that LR/SC was chosen over CAS partly because CAS needs a new 3-source format and a different memory-system message format, and because LR/SC avoids the ABA problem; RISC-V later added CAS because it can scale better in highly parallel systems. For a simple 4-core in-order design, LL/SC is the right MVP and CAS is the right optional future extension. ([docs.riscv.org][3])

Optional future extension:

* `CAS48`
* `CAS96` for paired data if you later need richer lock-free algorithms

#### 11.2 Memory model

Use a **TSO-like coherent, multi-copy-atomic memory model** from the start.

Why:

* much simpler software contract than a weak model
* still realistic for an in-order core with store buffering
* far easier to live with long-term than starting weak and regretting it

Mandatory ordering instructions:

* `FENCE`
* `FENCE.I`
* `SFENCE.VM` / TLB invalidate instruction

RISC-V’s official documentation makes the tradeoff clear: weaker models buy more implementation freedom but a harder programming model, while TSO is a stronger model intended to ease porting and reasoning. ([docs.riscv.org][9])

### 12. MMU and virtual memory

#### 12.1 Address sizes

* virtual addresses: 48 bits in cells
* physical addresses: 48 bits in cells

#### 12.2 Page size

MVP mandatory page size:

* `2^11` cells = 2048 cells

Future-reserved page sizes:

* `2^15` cells
* `2^19` cells

#### 12.3 SATP

Define `SATP` as:

* `MODE`
* `ASID`
* `ROOT_PPN`

Recommended packing in 48 bits:

* `MODE[2:0]`
* `ASID[7:0]`
* `ROOT_PPN[36:0]`

#### 12.4 TLBs

* private ITLB per core
* private DTLB per core
* ASID mandatory
* local TLB invalidate instructions mandatory
* remote TLB shootdown done by IPI

#### 12.5 Page-table format

For MVP, use a **4-level radix page table** with 48-bit PTEs and base pages only.

Because:

* page size is 2048 cells
* a 48-bit PTE occupies 2 cells
* one page-table page therefore holds 1024 PTEs
* VPN bits are 37, so the natural split is `7 + 10 + 10 + 10`

This gives you a coherent hardware walker story.

A practical 48-bit PTE can fit:

* `PPN[36:0]`
* `V`
* `U`
* `R`
* `W`
* `X`
* `G`
* `A`
* `MT[1:0]`
* one reserved bit

Use page memory types:

* normal coherent cacheable
* normal uncacheable
* device ordered
* reserved

One important note: your desired future page sizes `2^15` and `2^19` cells do **not** line up naturally with this radix geometry. So for MVP I would implement only base pages, reserve the encoding space for larger pages, and revisit the exact large-page walker behavior once the base core is up.

#### 12.6 Effective access rule

A memory access succeeds only if:

1. the base capability is valid, unsealed, in bounds, and has the needed capability permission,
2. the translated page is valid and has the needed page permission,
3. the privilege mode allows the access,
4. alignment rules are satisfied.

### 13. Cache hierarchy and coherence

Chosen cache hierarchy:

* each core has a private L1 instruction cache
* each core has a private L1 data cache
* all cores share one inclusive L2 cache
* the L1 data cache is write-back and write-allocate
* the L2 cache is the CPU coherence point
* CPU coherence is MESI-like

Hierarchy rules:

* L1 instruction caches are read-only from the data side and are synchronized with data writes by `FENCE.I`
* L1 data caches hold ordinary data, capability payload bits, and associated capability tag state
* inclusive L2 means every valid L1 line has a corresponding L2 line or L2 directory entry
* L2 is responsible for cross-core ownership, invalidation, and visibility ordering
* memory below L2 is not the CPU coherence point
* device/DMA agents do not participate in CPU cache coherence in v0.1

Policy rules:

* L1 data cache write hits update L1 and mark the line dirty
* L1 data cache write misses allocate the line before writing it
* dirty L1 data lines write back through L2
* instruction fetch does not allocate into the L1 data cache
* data load/store does not allocate into the L1 instruction cache
* L1 instruction cache fill, L1 data cache fill, and L1 writeback all go through L2

Deferred to later stories:

* E10-S02 defines line size and index details
* E10-S03 defines the coherence protocol state machine
* E10-S04 defines noncoherent DMA policy
* E10-S05 defines cache maintenance operations

Because the architecture is cell-addressed, define cache lines in **cells**, not bytes. I would start with:

* 16-cell line size
* 16 cells = 384 bits = 48 octets of storage when serialized externally

Cache-line address rules:

* cache-line size is counted in cells
* line offset is the low 4 bits of the cell address
* line base address is `address & ~0xF`
* a 16-cell line may contain four naturally aligned 96-bit capability slots
* a 16-cell line may contain eight naturally aligned 48-bit integer slots
* no byte address is implied by the 48-octet storage equivalence

This keeps line size power-of-two in the architectural address unit.

For MVP, keep I/O **outside coherence**:

* CPU caches are coherent with each other
* DMA/device accesses are noncoherent
* drivers use cache maintenance + fences around DMA

That is much simpler than coherent I/O and is a perfectly reasonable first server-style platform.

Mandatory maintenance operations:

* `FENCE`
* `FENCE.I`
* privileged `CACHE.CLEAN`
* privileged `CACHE.INVAL`
* privileged `CACHE.CLEANINVAL`

### 14. Boot and reset

Reset model:

* fixed ROM reset vector
* only core 0 starts executing after cold reset
* other cores enter `STOPPED` or `WFI`-parked state
* MMU off
* interrupts masked
* caches off or in known invalid state
* `PCC` initialized to ROM code capability
* `KRC`, `KSC`, `DSC`, and `RSC` initialized by ROM/firmware

Secondary-core bring-up:

* kernel/firmware writes per-core start mailbox
* sends IPI / start event
* target core enters `STARTED`

That is the cleanest modern model for a non-virtualized multicore system, and it is very much in line with the hart lifecycle ideas standardized in the RISC-V SBI HSM extension. ([docs.riscv.org][10])

### 15. Debug and observability

Mandatory debug features:

* `BRK`
* hardware instruction breakpoints
* hardware data watchpoints
* single-step
* debug mode
* separate debug vector
* halt/resume control
* register and memory inspection

Mandatory counters:

* `CYCLE`
* `INSTRET`

Extended counters:

* icache misses
* dcache misses
* L2 misses
* ITLB misses
* DTLB misses
* branch mispredicts
* traps taken
* LL/SC failures
* capability faults

### 16. Microarchitecture

#### 16.1 Pipeline shape

Keep it **single-issue, in-order**, but name the stages like a modern front-end/back-end:

* `FE0` next-PC generation / predictor
* `FE1` I-TLB + I-cache fetch
* `PD` predecode / pack splitter
* `XLT` ISA-to-micro-op translation
* `ISS` issue / scoreboard
* `EX` integer execute / branch / AGU
* `MEM` D-TLB + D-cache / capability access check
* `WB` writeback
* `RT` retire / precise-exception point

This is still a pipeline, but it is a clean front-end/back-end description rather than the older “classic 5-stage” view.

#### 16.2 Long-latency units

Use an independent `MDU`:

* `MUL` may be pipelined, 2-3 cycles
* `DIV/MOD` may be iterative
* destination register is marked busy in the scoreboard
* independent instructions continue
* dependent instructions wait
* result returns on the normal writeback path
* precise exceptions are taken at retire

Do **not** expose MDU completion through CSR.

#### 16.3 Hazard handling

Mandatory from the start:

* full bypass/forwarding from EX/MEM/WB where possible
* scoreboard/busy-bit tracking
* load-use interlock
* branch mispredict flush
* precise exception replay/kill

#### 16.4 Branch prediction

For MVP, use the safest simple predictor:

* small per-core 2-bit BHT for **direct conditional branches only**
* no generic indirect BTB in MVP
* small return-address stack for `CALL/RET`
* predictor state flushed or partitioned on privilege change and ASID switch

That gives you some speedup without opening the full branch-target-injection surface of a richer predictor. Spectre-class attacks do exploit branch prediction and speculative execution, and filtering predictions by context or flushing predictor state on context switch is a known mitigation direction. ([Linux Kernel Documentation][11])

### 17. MVP-required additions to your current instruction list

These are the ones I would add immediately because they complete the architecture:

* `CLC`, `CSC`
* `CSETBOUNDS`, `CANDPERM`, `CSEAL`, `CUNSEAL`, `CINCADDR`
* `SETcc`, `CMOVcc`
* `LL48`, `SC48`
* `FENCE`, `FENCE.I`, `SFENCE.VM`
* `CSRRD`, `CSRWR`, `CSRSET`, `CSRCLR`
* `CCSRRD`, `CCSRWR`
* `BRK`
* `SYS` / `SCALL`
* `WFI`
* `PAUSE`

### 18. Three places I would prototype first

1. **96-bit capability compression**

   I think your 96-bit target is workable, but this is the part I’m least confident about without actually prototyping the bounds codec.

2. **24-bit cell-addressed toolchain and ABI**

   This is the biggest software risk, not the biggest hardware risk.

3. **Page-table geometry vs future page sizes**

   Your base-page choice is fine, but your desired later page sizes do not fall out naturally from the simplest radix-tree walker.

Overall, I think this is now a coherent CPU architecture: unusual, but coherent. The biggest defining choices are the **24-bit cell-addressed memory model**, **pure-capability pointers from day one**, **protected return stack**, **LL/SC atomics**, and a **TSO-like multicore memory model**.

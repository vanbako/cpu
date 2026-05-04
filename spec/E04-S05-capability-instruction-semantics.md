# E04-S05: Capability Instruction Semantics

Story: E04-S05

Status: Complete

Normative source: `design.md`, sections 5.1, 5.2, 5.3, 5.4, 5.5, and 7.4

Prerequisites:

- `spec/E03-S03-capability-derivation.md`
- `spec/E04-S01-instruction-fetch-groups.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S03-general-capability-registers.md`
- `spec/E03-S01-capability-representation.md`
- `spec/E03-S02-capability-permissions.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E03-S05-local-capabilities.md`
- `spec/E03-S06-capability-fault-reporting.md`

## Decision

CPU v0.1 includes these mandatory capability instructions:

- `CMOVE`
- `CGETADDR`
- `CSETADDR`
- `CINCADDR`
- `CSETBOUNDS`
- `CANDPERM`
- `CSEAL`
- `CUNSEAL`
- `CLC`
- `CSC`

Capability instructions are the only ordinary instructions that can copy, inspect, derive, seal, unseal, load, or store architectural capability state.

Integer instructions cannot read or write capability registers. Integer values may be used as scalar operands to capability instructions, but integer values never carry capability tags and never authorize memory access by themselves.

## Register and Operand Conventions

Capability operands name general capability registers `C0-C7`.

Integer operands name general integer registers `D0-D15`.

Architectural assembly forms:

| Instruction | Form | Sources | Destinations | Summary |
| --- | --- | --- | --- | --- |
| `CMOVE` | `CMOVE Cd, Cs` | `Cs` | `Cd` | Copy capability payload and tag. |
| `CGETADDR` | `CGETADDR Dd, Cs` | `Cs` | `Dd` | Copy capability cursor/address bits to an integer register. |
| `CSETADDR` | `CSETADDR Cd, Cs, Da` | `Cs`, `Da` | `Cd` | Set cursor to an absolute cell address. |
| `CINCADDR` | `CINCADDR Cd, Cs, Di` | `Cs`, `Di` | `Cd` | Add a signed cell offset to the cursor. |
| `CSETBOUNDS` | `CSETBOUNDS Cd, Cs, Dlen` | `Cs`, `Dlen` | `Cd` | Narrow bounds to `[Cs.cursor, Cs.cursor + length)`. |
| `CANDPERM` | `CANDPERM Cd, Cs, Dmask` | `Cs`, `Dmask` | `Cd` | Clear permission bits by mask. |
| `CSEAL` | `CSEAL Cd, Cs, Cauth` | `Cs`, `Cauth` | `Cd` | Seal an unsealed capability with authorized object type. |
| `CUNSEAL` | `CUNSEAL Cd, Cs, Cauth` | `Cs`, `Cauth` | `Cd` | Unseal a sealed capability with matching authority. |
| `CLC` | `CLC Cd, Ca, Di` | `Ca`, `Di` | `Cd` | Load a capability from memory. |
| `CSC` | `CSC Ca, Di, Cs` | `Ca`, `Di`, `Cs` | memory | Store a capability to memory. |

`Ca` is a memory-authorizing capability register. `Di` is a signed 48-bit cell offset. `Da` and `Dlen` are unsigned 48-bit cell values.

Capability instruction encodings are in the 48-bit instruction-size class unless a later opcode story defines a compact alias. 48-bit capability instructions must obey E04-S01 placement rules.

## Common Capability Checks

Capability derivation instructions that produce a valid capability require valid, unsealed source capabilities unless their instruction-specific rule says otherwise.

Common source checks:

| Check | Failure |
| --- | --- |
| Required source tag is invalid | Capability tag fault. |
| Required unsealed source is sealed | Capability seal/type fault. |
| Required permission is missing | Capability permission fault, except missing `SL` for local store. |
| Resulting cursor or memory access is outside bounds | Capability bounds fault. |
| Sealing object type is invalid, unavailable, or mismatched | Capability seal/type fault. |

Faulting capability instructions are precise:

- Capability destination registers are unchanged.
- Integer destination registers are unchanged.
- Memory payload is unchanged.
- Memory tags are unchanged.
- No partial payload/tag update is visible.

Capability faults populate `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL` according to E03-S06 and E02-S03.

When an instruction has multiple capability operands, `FAULTCAPIDX` reports the first operand that fails the architecturally ordered checks below. If a later story defines a narrower fault-priority matrix, it must preserve fault atomicity.

## Tag Propagation Summary

| Instruction | Tag result |
| --- | --- |
| `CMOVE` | Destination tag equals source tag. |
| `CGETADDR` | No capability tag is produced. |
| `CSETADDR` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CINCADDR` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CSETBOUNDS` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CANDPERM` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CSEAL` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CUNSEAL` | Successful result tag equals source tag. Faulting result writes nothing. |
| `CLC` | Destination tag equals the memory slot tag. |
| `CSC` | Memory slot tag equals stored source tag. |

No instruction in this story can synthesize a valid tag from integer data.

## `CMOVE`

`CMOVE` copies a general capability register:

```text
Cd.payload = Cs.payload
Cd.tag     = Cs.tag
```

Rules:

- Payload and tag are copied exactly.
- Invalid-tag capabilities can be copied.
- Sealed capabilities can be copied.
- `CMOVE` does not inspect bounds, permissions, object type, or flags.
- If `Cd == Cs`, the instruction is an architectural no-op.

## `CGETADDR`

`CGETADDR` copies the cursor/address payload field into an integer register:

```text
Dd = Cs.cursor
```

Rules:

- No capability tag is copied to `Dd`.
- `Dd` receives a 48-bit integer cell address value.
- `CGETADDR` may inspect invalid-tag or sealed capability payloads because it does not produce authority.
- `CGETADDR` does not authorize memory access and does not prove that the returned integer is dereferenceable.

## `CSETADDR`

`CSETADDR` changes only the cursor field:

```text
candidate = unsigned(Da[47:0])
Cd = Cs with cursor = candidate
```

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be unsealed.
3. `candidate` must satisfy `Cs.base <= candidate < Cs.top`.

On success:

- `Cd` receives `Cs` with only the cursor changed.
- The destination tag remains valid.
- Bounds, permissions, object type, and flags are unchanged.

On failure:

- Invalid `Cs.tag` raises capability tag fault.
- Sealed `Cs` raises capability seal/type fault.
- Out-of-bounds `candidate` raises capability bounds fault and reports `TVAL = candidate`.

## `CINCADDR`

`CINCADDR` adds a signed cell offset to the cursor:

```text
candidate = Cs.cursor + signed(Di[47:0])
Cd = Cs with cursor = candidate
```

The addition is computed in mathematical integers, not modulo `2^48`.

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be unsealed.
3. `0 <= candidate < 2^48`.
4. `candidate` must satisfy `Cs.base <= candidate < Cs.top`.

On success:

- `Cd` receives `Cs` with only the cursor changed.
- The destination tag remains valid.

On failure:

- Invalid `Cs.tag` raises capability tag fault.
- Sealed `Cs` raises capability seal/type fault.
- Address overflow, address underflow, or out-of-bounds `candidate` raises capability bounds fault and reports `TVAL = candidate` when representable, otherwise `TVAL = 0`.

## `CSETBOUNDS`

`CSETBOUNDS` narrows a capability to a child range beginning at the source cursor:

```text
requested_base = Cs.cursor
requested_top  = Cs.cursor + unsigned(Dlen[47:0])
requested_len  = unsigned(Dlen[47:0])
Cd = Cs with bounds = representable_bounds(requested_base, requested_top)
```

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be unsealed.
3. `requested_len` must be nonzero.
4. `requested_top` must not overflow 48-bit cell address space.
5. `requested_base` and `requested_top` must define a range within `Cs` bounds.
6. The exact requested bounds or an outward-rounded representable result must fit within `Cs` bounds.

On success:

- `Cd` receives a capability with narrowed bounds.
- `Cd.cursor = requested_base`.
- Permissions, object type, and flags are unchanged.
- The destination tag remains valid.
- The resulting decoded bounds must include `[requested_base, requested_top)` and remain within the parent bounds.

On failure:

- Invalid `Cs.tag` raises capability tag fault.
- Sealed `Cs` raises capability seal/type fault.
- Zero length, top overflow, requested range outside parent bounds, or unrepresentable rounded-in-parent bounds raises capability bounds fault.
- `TVAL` reports the requested base if the base is outside the parent bounds, otherwise the requested top when representable, otherwise `0`.

`CSETBOUNDS` cannot widen bounds. It cannot move the cursor away from the child base.

## `CANDPERM`

`CANDPERM` clears permissions by mask:

```text
Cd.permissions = Cs.permissions & Dmask[7:0]
```

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be unsealed.

On success:

- `Cd` receives `Cs` with only permission bits changed.
- Permission bits may be cleared but never set.
- Bounds, cursor, object type, flags, and tag are unchanged.
- Bits above `Dmask[7:0]` are ignored.

On failure:

- Invalid `Cs.tag` raises capability tag fault.
- Sealed `Cs` raises capability seal/type fault.

## `CSEAL`

`CSEAL` seals an unsealed capability:

```text
otype = Cauth.cursor[7:0]
Cd = Cs with otype = otype
```

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be unsealed.
3. `Cauth.tag` must be valid.
4. `Cauth` must be unsealed.
5. `Cauth` must have `SEAL`.
6. `otype` must be nonzero.
7. `otype` must not be an architecture-reserved object type unavailable to ordinary `CSEAL`.

On success:

- `Cd` receives `Cs` with `otype` set to the authorized nonzero object type.
- Cursor, bounds, permissions, flags, and tag are otherwise unchanged.

On failure:

- Invalid source or authorizer tag raises capability tag fault and reports the failing source.
- Sealed source, sealed authorizer, zero `otype`, or unavailable reserved `otype` raises capability seal/type fault.
- Missing `SEAL` raises capability permission fault.

`OTYPE_ENTRY` from E06-S02 is reserved for architectural entry capabilities but is available to ordinary `CSEAL` when the sealing authority selects that type.

`OTYPE_RETURN` from E06-S03 is reserved for architectural return capabilities. Ordinary `CSEAL` cannot create it.

## `CUNSEAL`

`CUNSEAL` unseals a sealed capability when authorized:

```text
otype = Cauth.cursor[7:0]
Cd = Cs with otype = 0
```

Checks, in order:

1. `Cs.tag` must be valid.
2. `Cs` must be sealed.
3. `Cauth.tag` must be valid.
4. `Cauth` must be unsealed.
5. `Cauth` must have `UNSEAL`.
6. `otype` must equal `Cs.otype`.
7. `otype` must not be an architecture-reserved object type unavailable to ordinary `CUNSEAL`.

On success:

- `Cd` receives `Cs` with `otype = 0`.
- Cursor, bounds, permissions, flags, and tag are otherwise unchanged.

On failure:

- Invalid source or authorizer tag raises capability tag fault and reports the failing source.
- Unsealed source, sealed authorizer, object-type mismatch, or unavailable reserved `otype` raises capability seal/type fault.
- Missing `UNSEAL` raises capability permission fault.

`CUNSEAL` cannot unseal `OTYPE_ENTRY`; only `CALLC` consumes that architectural object type in v0.1.

`CUNSEAL` cannot unseal `OTYPE_RETURN`; only `RET` consumes that architectural object type in v0.1.

## `CLC`

`CLC` loads one capability slot from memory:

```text
effective = Ca.cursor + signed(Di[47:0])
Cd.payload = memory_payload[effective, effective + 4)
Cd.tag     = memory_tag[effective]
```

The effective address calculation is performed in mathematical integers, not modulo `2^48`. The effective address is a cell address. The accessed memory object is the 4-cell slot `[effective, effective + 4)`.

Checks, in order:

1. `Ca.tag` must be valid.
2. `Ca` must be unsealed.
3. `effective` must satisfy `0 <= effective <= 2^48 - 4`.
4. `effective` must be 4-cell aligned.
5. The entire 4-cell slot must be within `Ca` bounds.
6. `Ca` must have `LD` and `LC`.

On success:

- `Cd` receives the 96-bit memory payload and the slot tag as one architectural operation.
- A memory slot with tag clear loads into `Cd` with tag clear.
- Loading an invalid capability payload is not a fault by itself.

On failure:

- Invalid `Ca.tag` raises capability tag fault.
- Sealed `Ca` raises capability seal/type fault.
- Address overflow or underflow raises capability bounds fault and reports `TVAL = 0`.
- Misaligned `effective` raises `ALIGN_FAULT`.
- Out-of-bounds slot raises capability bounds fault and reports `TVAL = effective`.
- Missing `LD` or `LC` raises capability permission fault.

Address translation, page permission checks, and complete fault priority with MMU faults are defined by E04-S03, E09-S07, and related MMU stories.

## `CSC`

`CSC` stores one capability slot to memory:

```text
effective = Ca.cursor + signed(Di[47:0])
memory_payload[effective, effective + 4) = Cs.payload
memory_tag[effective] = Cs.tag
```

The effective address calculation is performed in mathematical integers, not modulo `2^48`. The effective address is a cell address. The written memory object is the 4-cell slot `[effective, effective + 4)`.

Checks, in order:

1. `Ca.tag` must be valid.
2. `Ca` must be unsealed.
3. `effective` must satisfy `0 <= effective <= 2^48 - 4`.
4. `effective` must be 4-cell aligned.
5. The entire 4-cell slot must be within `Ca` bounds.
6. `Ca` must have `ST` and `SC`.
7. If `Cs.tag = 1` and `Cs.G = 0`, `Ca` must have `SL`.

On success:

- Memory receives `Cs.payload` and `Cs.tag` as one architectural operation.
- Storing an invalid-tag source writes the payload and clears the memory slot tag.
- Storing a sealed capability is allowed when the destination authority permits capability store.
- Storing a local valid capability requires `SL` in the destination authority.

On failure:

- Invalid `Ca.tag` raises capability tag fault.
- Sealed `Ca` raises capability seal/type fault.
- Address overflow or underflow raises capability bounds fault and reports `TVAL = 0`.
- Misaligned `effective` raises `ALIGN_FAULT`.
- Out-of-bounds slot raises capability bounds fault and reports `TVAL = effective`.
- Missing `ST` or `SC` raises capability permission fault.
- Missing `SL` for a valid local source capability raises capability local-store fault.

`CSC` does not require the stored source capability `Cs` to be valid, unsealed, in bounds, or permission-bearing. The source is data being stored, not the authority for the store.

Address translation, page permission checks, and complete fault priority with MMU faults are defined by E04-S03, E09-S07, and related MMU stories.

## Fault Reporting

Capability instruction fault reporting follows E03-S06.

Baseline reporting:

| Instruction family | `CAPCAUSE` | `FAULTCAPIDX` | `TVAL` |
| --- | --- | --- | --- |
| Invalid required source tag | `TAG` | Failing capability source | `0` |
| Bounds failure in `CSETADDR` or `CINCADDR` | `BOUNDS` | `Cs` | Attempted cursor when representable |
| Bounds failure in `CSETBOUNDS` | `BOUNDS` | `Cs` | Requested base or top as defined above |
| Bounds failure in `CLC` or `CSC` | `BOUNDS` | `Ca` | Effective slot base |
| Missing permission except `SL` | `PERMISSION` | Capability missing permission | `0` |
| Missing `SL` for local store | `LOCAL_STORE` | Destination authority `Ca` | Effective slot base |
| Sealed source used where unsealed required | `SEAL_TYPE` | Failing capability source | `0` |
| Seal/unseal object-type mismatch | `SEAL_TYPE` | Source or authorizer according to failing check | `0` |

`ALIGN_FAULT` is not a capability fault. E07-S04 clears capability reporting for non-capability faults by writing `CAPCAUSE=NONE` and `FAULTCAPIDX=NONE`.

## Out of Scope for This Story

- Exact opcode bit assignments and compact aliases: E04-S06.
- Integer `LD48` and `ST48` instruction semantics: E04-S03.
- Address translation, page permissions, and combined capability/page fault priority: E09-S07.
- Full control-transfer capability semantics, `CALLC`, `CALL`, `RET`, `IRET`, `SYS`, `BRK`, `WFI`, and `PAUSE`: E04-S04, E06-S02, and E06-S03.
- Exact bounds-compression algorithm beyond the E03-S01 architectural contract.
- ABI register roles and stack conventions: E05 stories.

## Verification Notes

Minimum conformance checks for later assembler, simulator, and RTL work:

- `CMOVE` copies payload and tag exactly.
- `CGETADDR` writes cursor bits to an integer register and produces no tag.
- `CSETADDR` changes only the cursor.
- `CSETADDR` faults when the requested cursor is outside source bounds.
- `CINCADDR` treats the integer operand as a signed cell offset.
- `CINCADDR` faults on 48-bit address overflow or underflow.
- `CSETBOUNDS` narrows bounds and never widens source bounds.
- `CSETBOUNDS` rejects zero length.
- `CANDPERM` clears permissions and never sets a previously clear permission bit.
- `CSEAL` requires valid unsealed source, valid unsealed `SEAL` authority, and a nonzero available object type.
- `CUNSEAL` requires valid sealed source, valid unsealed `UNSEAL` authority, and matching object type.
- `CSEAL` can create `OTYPE_ENTRY` when authorized.
- `CSEAL` cannot create `OTYPE_RETURN`.
- `CUNSEAL` cannot unseal `OTYPE_ENTRY`.
- `CUNSEAL` cannot unseal `OTYPE_RETURN`.
- `CLC` requires valid unsealed load authority with `LD` and `LC`.
- `CLC` requires 4-cell alignment.
- `CLC` loads payload and tag atomically.
- `CSC` requires valid unsealed store authority with `ST` and `SC`.
- `CSC` storing a valid local capability additionally requires `SL`.
- `CSC` requires 4-cell alignment.
- `CSC` stores payload and tag atomically.
- Faulting capability derivation instructions leave capability destinations unchanged.
- Faulting `CLC` leaves the destination capability register unchanged.
- Faulting `CSC` leaves memory payload and tag unchanged.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `CMOVE`, `CGETADDR`, `CSETADDR`, `CINCADDR`, `CSETBOUNDS`, `CANDPERM`, `CSEAL`, `CUNSEAL`, `CLC`, and `CSC` are defined. | Met. |
| Tag propagation behavior is specified. | Met. |
| Bounds, permission, and sealing checks are specified. | Met. |
| Invalid operations produce named capability faults. | Met. |

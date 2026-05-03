# E03-S02: Capability Permission Bits

Story: E03-S02

Status: Complete

Normative source: `design.md`, section 5.1

## Decision

CPU v0.1 capabilities have 8 permission bits. Permissions are monotonic: derivation may remove permissions but may not add permissions that were absent in the source capability.

## Permission Table

| Bit | Name | Architectural effect |
| --- | --- | --- |
| `LD` | Load data | Permits integer/data loads through the capability. |
| `ST` | Store data | Permits integer/data stores through the capability. |
| `EX` | Execute | Permits instruction fetch through the capability. |
| `LC` | Load capability | Permits loading capability payload and tag through the capability. |
| `SC` | Store capability | Permits storing capability payload and tag through the capability. |
| `SL` | Store local capability | Permits storing local capabilities through the capability. |
| `SEAL` | Seal | Permits sealing with an authorized object type. |
| `UNSEAL` | Unseal | Permits unsealing with an authorized object type. |

## Required Permissions by Operation

| Operation | Required permissions |
| --- | --- |
| Instruction fetch | `EX` |
| `LD48` | `LD` |
| `ST48` | `ST` |
| `CLC` | `LD` and `LC` |
| `CSC` storing global capability | `ST` and `SC` |
| `CSC` storing local capability | `ST`, `SC`, and `SL` |
| `CSEAL` | `SEAL` |
| `CUNSEAL` | `UNSEAL` |

Missing any required permission except `SL` raises a capability permission fault. Missing `SL` for a local capability store raises a capability local-store fault. The faulting instruction leaves destination architectural state unchanged.

## Monotonicity Rule

Permission derivation is one-way.

Allowed:

```text
source permissions: LD ST LC SC
derived permissions: LD LC
```

Not allowed:

```text
source permissions: LD
derived permissions: LD ST
```

`CANDPERM` may clear bits. No ordinary capability instruction may set a permission bit that is clear in the source capability. Authority can be expanded only by receiving another valid capability that already carries that authority.

## Permission Fault Examples

| Case | Fault |
| --- | --- |
| Fetch through capability without `EX` | Capability permission fault |
| `LD48` through capability without `LD` | Capability permission fault |
| `ST48` through capability without `ST` | Capability permission fault |
| `CLC` through capability with `LD` but not `LC` | Capability permission fault |
| `CSC` through capability with `ST` but not `SC` | Capability permission fault |
| Store local capability through capability without `SL` | Capability local-store fault |
| `CSEAL` without `SEAL` | Capability permission fault |
| `CUNSEAL` without `UNSEAL` | Capability permission fault |

The local-store case has its own named fault in the broader exception list. E03-S06 will assign the exact `CAPCAUSE` encoding.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Fetch succeeds with `EX` and fails without `EX`.
- `LD48` succeeds with `LD` and fails without `LD`.
- `ST48` succeeds with `ST` and fails without `ST`.
- `CLC` requires both `LD` and `LC`.
- `CSC` requires both `ST` and `SC`.
- Local capability store additionally requires `SL`.
- `CSEAL` requires `SEAL`.
- `CUNSEAL` requires `UNSEAL`.
- `CANDPERM` can clear bits.
- No derivation path can set a previously clear permission bit.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `LD`, `ST`, `EX`, `LC`, `SC`, `SL`, `SEAL`, and `UNSEAL` are defined. | Met. |
| Each permission has an architectural effect. | Met. |
| Missing permissions raise named capability permission faults. | Met. Missing `SL` for local capability store raises the more specific capability local-store fault. |
| Permission reduction is monotonic. | Met. |

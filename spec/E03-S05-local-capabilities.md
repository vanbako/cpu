# E03-S05: Local Capability Semantics

Story: E03-S05

Status: Complete

Normative source: `design.md`, section 5.4

Related story: `spec/E03-S02-capability-permissions.md`

## Decision

CPU v0.1 uses the `G` flag to distinguish global and local capabilities.

| Flag | Meaning |
| --- | --- |
| `G=1` | Global capability |
| `G=0` | Local capability |

Local capabilities are valid capabilities, but they carry authority that must not be stored into ordinary long-lived memory unless the destination capability explicitly permits local stores.

## Store Rule

Capability stores use the permission bits of the destination memory-authorizing capability.

| Stored capability | Destination requirements |
| --- | --- |
| Global capability | `ST` and `SC` |
| Local capability | `ST`, `SC`, and `SL` |

If software tries to store a local capability through a destination capability that lacks `SL`, the instruction raises a capability local-store fault and leaves memory unchanged.

## Intended Use

Local capabilities are appropriate for:

- Data stack authority
- Protected return stack authority
- Temporarily delegated authority
- Short-lived frame-local references
- Runtime-internal authority that must not leak into heap or global storage

Global capabilities are appropriate for:

- Persistent heap objects
- Global objects
- Kernel-owned root objects
- Capabilities intentionally safe to store in longer-lived memory

## Examples

Stack-local pointer:

```text
source capability: local stack-derived capability, G=0
destination heap capability: ST SC, no SL
CSC raises capability local-store fault
```

Explicit local-capability spill area:

```text
source capability: local temporary capability, G=0
destination stack capability: ST SC SL
CSC succeeds
```

Ordinary global object store:

```text
source capability: global object capability, G=1
destination heap capability: ST SC
CSC succeeds
```

## Security Rationale

The `SL` bit creates an explicit boundary between short-lived authority and long-lived storage.

Without this rule, a program could accidentally store stack-derived or temporary delegated capabilities into heap/global memory, extending their lifetime beyond the stack frame or delegation scope that created them.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CSC` storing a global capability succeeds with `ST` and `SC`.
- `CSC` storing a local capability succeeds with `ST`, `SC`, and `SL`.
- `CSC` storing a local capability without `SL` raises capability local-store fault.
- Local-store fault leaves memory payload and tag unchanged.
- `ST48` ordinary integer store behavior is unaffected by source capability locality.
- Capability load preserves the loaded capability's `G` flag.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `G=1` means global capability. | Met. |
| `G=0` means local capability. | Met. |
| Local capabilities may be stored only through a capability with `SL=1`. | Met, with `ST` and `SC` also required for `CSC`. |
| Violations raise capability local-store fault. | Met. |
| Stack and temporary delegation examples are documented. | Met. |


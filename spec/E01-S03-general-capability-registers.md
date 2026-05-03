# E01-S03: General Capability Registers

Story: E01-S03

Status: Complete

Normative source: `design.md`, section 3.2

## Decision

CPU v0.1 has 8 general capability registers: `C0-C7`.

Each register contains:

- 96-bit capability payload
- 1 out-of-band architectural validity tag

The tag is architectural state. It is not stored in the 96-bit payload and is not directly addressable as data.

## Register Purpose

General capability registers carry ordinary program authority:

- Data capabilities
- Object capabilities
- Sealed entry capabilities
- Temporary delegated authority
- Capability arguments and return values under the ABI

They do not replace the special capability registers:

- `PCC` for instruction fetch
- `DSC` for data stack
- `RSC` for protected return stack
- `DDC` for explicit default data capability forms
- `EPCC`, `TVC`, `KSC`, and `KRC` for trap and kernel authority

## Pure-capability Authorization Rule

Integer registers do not authorize memory access.

All fetch, load, and store operations are capability-governed:

| Operation | Authorizing capability |
| --- | --- |
| Instruction fetch | `PCC` |
| Explicit data load/store | Capability source register named by the instruction |
| Default data load/store form | `DDC`, only when the instruction form explicitly says so |
| Capability load | Data capability with `LD` and `LC` permissions |
| Capability store | Data capability with `ST` and `SC` permissions |

An integer register may contain a cell address, offset, index, diagnostic value, or syscall argument. It is not a pointer by itself. It cannot be dereferenced unless an explicit capability instruction uses it to derive or adjust a capability while preserving monotonic authority.

## Tag Behavior

| Operation | Tag behavior |
| --- | --- |
| `CMOVE` | Copies payload and tag. |
| `CLC` | Loads payload and tag from an aligned capability slot. |
| `CSC` | Stores payload and tag to an aligned capability slot. |
| Integer ALU operation | Does not create a valid capability tag. |
| `LD48` | Loads integer data only; does not create a valid capability tag. |
| `ST48` into capability slot | Clears the memory tag for that capability slot. |

Invalid-tag capabilities cannot authorize:

- Instruction fetch
- Data load/store
- Capability load/store
- Seal/unseal
- Capability derivation

## Fault Rules

Capability-governed access fails before commit when the authorizing capability is:

- Invalid-tagged
- Sealed when an unsealed capability is required
- Out of bounds
- Missing the required permission
- Local-store restricted

The specific cause is assigned by the capability fault model in later stories.

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- `CMOVE` preserves payload and tag.
- Integer register copy cannot create a valid capability.
- Integer ALU operation on capability payload bits cannot create a valid capability.
- `LD48` from memory containing capability payload bits returns integer data but no tag.
- `CLC` from a tagged capability slot loads a tagged capability.
- `CSC` stores payload and tag atomically to a capability slot.
- Fetch through invalid `PCC` fails.
- Data load through invalid `C0-C7` fails.
- Integer-only address cannot be dereferenced without a capability.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Registers `C0-C7` are defined. | Met. |
| Each architectural capability is defined as 96 bits plus an out-of-band tag. | Met. |
| Integer addresses are not directly dereferenceable in pure-capability mode. | Met. |
| All instruction fetch, load, and store operations are capability-authorized. | Met. |


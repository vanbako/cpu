# E03-S06: Capability Fault Reporting

Story: E03-S06

Status: Complete

Normative source: `design.md`, section 5.5

Related sources:

- `spec/E03-S01-capability-representation.md`
- `spec/E03-S02-capability-permissions.md`
- `spec/E03-S03-capability-derivation.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E03-S05-local-capabilities.md`

## Decision

Capability faults use the normal precise exception path and populate capability-specific reporting CSRs:

- `CAPCAUSE`
- `FAULTCAPIDX`
- `TVAL`

`CAUSE` still records the architectural trap class. `CAPCAUSE` gives the capability-specific reason.

## Capability Fault Classes

| Fault class | Meaning |
| --- | --- |
| Capability tag fault | A required authorizing or derivation-source capability has an invalid tag. |
| Capability bounds fault | A cursor, fetch, load/store, or bounds derivation exceeds capability bounds. |
| Capability permission fault | A capability is missing a required permission other than `SL` local-store permission. |
| Capability seal/type fault | A sealed capability is used incorrectly, or seal/unseal object type authority does not match. |
| Capability local-store fault | A local capability is stored through a destination capability without `SL`. |

## `CAPCAUSE`

Required architectural `CAPCAUSE` names:

| Name | Use |
| --- | --- |
| `NONE` | No capability-specific cause. |
| `TAG` | Capability tag fault. |
| `BOUNDS` | Capability bounds fault. |
| `PERMISSION` | Capability permission fault. |
| `SEAL_TYPE` | Capability seal/type fault. |
| `LOCAL_STORE` | Capability local-store fault. |

Numeric encodings are reserved for the CSR allocation story. Software should use the architectural names until encodings are assigned.

## `FAULTCAPIDX`

`FAULTCAPIDX` identifies the most relevant capability operand when possible.

Required names:

| Name | Meaning |
| --- | --- |
| `C0-C7` | General capability register source. |
| `PCC` | Program-counter capability, normally for fetch faults. |
| `DDC` | Default data capability source. |
| `DSC` | Data stack capability source. |
| `RSC` | Return stack capability source. |
| `KSC` | Kernel stack capability source. |
| `KRC` | Kernel root capability source. |
| `EPCC` | Exception PC capability source. |
| `TVC` | Trap vector capability source. |
| `NONE` | No single capability operand is responsible. |
| `UNKNOWN` | Implementation cannot report a precise operand. |

For an instruction with multiple capability operands, `FAULTCAPIDX` reports the operand that failed the first architecturally prioritized capability check.

## `TVAL`

`TVAL` records the relevant cell address when there is one.

| Fault source | `TVAL` value |
| --- | --- |
| Instruction fetch | Attempted fetch cell address |
| Data load/store | Effective cell address |
| `CLC` or `CSC` | Effective slot base cell address |
| `CSETADDR` or `CINCADDR` bounds fault | Attempted resulting cursor |
| `CSETBOUNDS` bounds fault | Requested base if base failed; otherwise requested top |
| Seal/type fault with no relevant address | `0` |
| Tag or permission fault with no relevant address | `0` |

## Commit Behavior

Capability faults are precise.

On a capability fault:

- Destination registers are unchanged.
- Memory payload is unchanged.
- Memory tags are unchanged.
- `EPCC` identifies the faulting instruction and slot.
- `CAUSE` identifies the trap class.
- `CAPCAUSE`, `FAULTCAPIDX`, and `TVAL` are populated before trap entry.

## Examples

Invalid `PCC` tag during fetch:

```text
CAUSE = capability tag fault
CAPCAUSE = TAG
FAULTCAPIDX = PCC
TVAL = attempted fetch cell address
```

`LD48` through `C2` outside bounds:

```text
CAUSE = capability bounds fault
CAPCAUSE = BOUNDS
FAULTCAPIDX = C2
TVAL = effective load cell address
```

`CSC` storing local capability through destination without `SL`:

```text
CAUSE = capability local-store fault
CAPCAUSE = LOCAL_STORE
FAULTCAPIDX = destination capability register
TVAL = effective capability slot base cell address
```

`CUNSEAL` with mismatched object type:

```text
CAUSE = capability seal/type fault
CAPCAUSE = SEAL_TYPE
FAULTCAPIDX = source or unseal-authority register, according to failing check
TVAL = 0
```

## Verification Notes

Minimum conformance checks for later simulator and RTL work:

- Invalid authorizing capability tag reports `CAPCAUSE = TAG`.
- Out-of-bounds fetch reports `FAULTCAPIDX = PCC`.
- Out-of-bounds load/store reports the source capability index.
- Missing `LD`, `ST`, `EX`, `LC`, `SC`, `SEAL`, or `UNSEAL` reports `CAPCAUSE = PERMISSION`.
- Missing `SL` for local capability store reports `CAPCAUSE = LOCAL_STORE`.
- Seal/type mismatch reports `CAPCAUSE = SEAL_TYPE`.
- `TVAL` reports cell addresses, not byte addresses.
- Destination state remains unchanged on capability faults.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Capability tag, bounds, permission, seal/type, and local-store faults are named. | Met. |
| `CAPCAUSE` is populated for capability-related traps. | Met. |
| `FAULTCAPIDX` identifies the relevant source capability where possible. | Met. |
| Faulting virtual address or cell address behavior is defined through `TVAL`. | Met. |


# E11-S02: Reset Capability State

Story: E11-S02

Status: Complete

Normative source: `design.md`, section 14

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E03-S01-capability-representation.md`

Related sources:

- `spec/E01-S01-cell-address-model.md`
- `spec/E01-S05-pc-subslot-behavior.md`
- `spec/E01-S06-status-register-behavior.md`
- `spec/E02-S05-capability-csr-access.md`
- `spec/E03-S02-capability-permissions.md`
- `spec/E03-S03-capability-derivation.md`
- `spec/E03-S05-local-capabilities.md`
- `spec/E05-S03-data-stack-model.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E06-S01-pcc-execute-authority.md`

## Decision

Cold reset must start from a defined capability state that gives firmware only deliberate authority.

CPU v0.1 uses two reset phases for capability state:

1. Hardware reset entry installs the minimum execution authority needed for core 0 to fetch the fixed ROM reset vector.
2. ROM or firmware initializes the broader privileged capability context, including `KRC`, `KSC`, `DSC`, and `RSC`.

All capability state not explicitly initialized as valid must have an invalid tag. Undefined reset payload bits are never authority without a valid out-of-band tag.

## Hardware Reset Entry

At cold reset entry, core 0 starts in kernel mode with interrupts masked according to E01-S06 and E11-S01.

Hardware must initialize core 0 `PCC` as a valid ROM code capability:

| Field | Required reset value |
| --- | --- |
| Tag | Valid |
| Seal state | Unsealed (`otype = 0`) |
| Cursor | Fixed ROM reset vector cell address |
| Hidden slot | `0` |
| Bounds | Platform ROM executable reset region |
| Required permission | `EX` |
| Disallowed by default | `ST`, `SC`, `SL`, `SEAL`, `UNSEAL` |
| Local/global flag | Global (`G=1`) unless a platform profile explicitly narrows it |

The reset `PCC.cursor` must be inside `PCC.bounds`. Instruction fetch through this `PCC` must satisfy E06-S01.

The reset `PCC` should be execute-only. A platform may also grant `LD` or `LC` to the ROM `PCC` only if its ROM code model explicitly fetches literal data through `PCC`; such extra permissions must not grant write, seal, or unseal authority.

## Hardware Invalid-tag Baseline

Unless a platform reset profile explicitly defines a stronger valid value, hardware reset sets these architectural capability tags to invalid:

- General capability registers `C0-C7`.
- `DSC`.
- `RSC`.
- `DDC`.
- `EPCC`.
- `TVC`.
- `KSC`.
- `KRC`.

For invalid-tag reset state:

- Payload bits are architecturally unspecified.
- The tag is architecturally `0`.
- The value cannot authorize fetch, load, store, seal, unseal, derivation, or CCSR-mediated authority creation.
- Copying the value with `CMOVE`, `CCSRRD`, or `CCSRWR` preserves the invalid tag.

Software and tests must not infer authority from invalid reset payload bits.

## ROM/Firmware Capability Initialization

ROM or firmware is responsible for installing usable privileged capability state before using facilities that depend on it.

The source of valid reset capabilities is trusted reset logic, mask ROM, or a platform-defined reset manifest. This source is outside ordinary integer dataflow: it may install or provide valid tags only as part of the trusted reset process. After reset capability initialization, ordinary architectural instructions still cannot create a valid tag from integer payload bits.

Required ROM/firmware initialized capabilities:

| Register | Required initialized role | Required properties |
| --- | --- | --- |
| `KRC` | Kernel or firmware root capability | Valid, unsealed, global, broad enough for firmware to derive platform code, data, stack, trap, and device authority. |
| `KSC` | Early kernel/trap stack authority | Valid, unsealed, local, in-bounds cursor, stack-aligned, no `EX`. |
| `DSC` | Initial data-stack authority | Valid, unsealed, local, in-bounds cursor, 4-cell aligned at public handoff boundaries, no `EX`. |
| `RSC` | Initial protected return-stack authority | Valid, unsealed, local, 4-cell aligned in-bounds cursor naming the empty return-stack anchor, no `EX`. |

Firmware must initialize `TVC` before enabling traps or interrupts. Firmware may leave `DDC` invalid unless it will execute instruction forms that explicitly use `DDC`.

`EPCC` remains invalid until the first trap captures a faulting or interrupted `PCC`, or until privileged firmware intentionally initializes it for a controlled `IRET` path.

## Required Initialized Permissions

The minimum useful permissions for reset-installed capabilities are:

| Register | Minimum permissions | Notes |
| --- | --- | --- |
| `PCC` | `EX` | ROM fetch authority only. |
| `KRC` | Platform-defined root permissions | May include all v0.1 permissions when needed to derive narrower boot authority. |
| `KSC` | `LD`, `ST`, `LC`, `SC`, `SL` | Supports trap-frame and local capability storage. |
| `DSC` | `LD`, `ST`, `LC`, `SC`, `SL` | Supports ordinary data-stack use defined by E05-S03. |
| `RSC` | `LD`, `ST`, `LC`, `SC`, `SL` | Supports protected return-stack push and pop defined by E05-S04. |
| `TVC` | `EX` | Needed only before trap or interrupt entry can be delivered. |
| `DDC` | As required by explicit DDC-form instructions | Must be invalid if not intentionally configured. |

Reset-installed stack capabilities must have `G=0` unless a later ABI story explicitly permits a global stack capability for a constrained environment. `KRC` and ROM code capabilities should normally have `G=1`.

## Capability Construction and Tag Integrity

Reset cannot expose forgeable capability state.

Rules:

- Raw ROM, RAM, or mailbox payload bits do not imply valid tags.
- Integer registers cannot hold or transfer capability tags.
- Scalar CSR writes cannot create or modify capability tags.
- `CCSRWR` copies an existing general capability tag exactly; it cannot manufacture a valid special capability tag.
- Any reset-time valid tag must originate from trusted reset capability state, from a valid capability loaded by a tag-aware path, or from ordinary monotonic derivation from an already valid capability.
- Firmware must invalidate temporary general capability registers that carry root or setup authority before entering less-privileged or untrusted code.

If firmware serializes a capability payload into ordinary ROM or RAM without a tag-aware capability slot, later loads of that payload are invalid capabilities. A valid reset capability table, if implemented, must preserve out-of-band tags through a trusted platform mechanism.

## Boot-core Handoff State

Before ROM or firmware hands control to the kernel or to a more general privileged runtime, it must establish a coherent capability handoff state:

- `PCC` names the handoff code entry, is valid, unsealed, in bounds, slot 0, and has `EX`.
- `KRC` is valid if the next stage is expected to derive authority.
- `KSC` is valid before traps, interrupts, or debug paths can use a kernel stack.
- `DSC` is valid before ordinary stack use.
- `RSC` is valid before executing `CALL` instructions that use protected return state.
- `TVC` is valid before traps or interrupts are enabled.
- `DDC` is invalid unless the next stage explicitly uses DDC-form memory operations.
- General capability registers not part of the documented handoff ABI have invalid tags.

The handoff ABI may pass selected valid capabilities in `C0-C7`, but every such register must be documented as an intentional authority transfer.

## Secondary-core Capability State

Non-boot cores do not begin normal instruction execution after cold reset.

Until E11-S03 starts a secondary core, its architectural capability state must not be observable as usable authority by ordinary software. A conforming implementation may either keep secondary-core capability tags invalid or park the core in implementation-controlled firmware state.

When a secondary core is started, firmware or kernel startup code must install a valid `PCC` and the stack/root capability state required by the startup ABI before the core enters ordinary instruction execution.

## Invalid-tag and Delivery-failure Behavior

Using an invalid reset capability follows the normal capability fault rules when the capability is consumed by an ordinary instruction or data access.

Invalid `TVC` during trap or interrupt delivery follows the entry-failure rules in E07-S04 and E07-S05. It is not delivered as a recursive normal trap through the same invalid vector state.

| Use of invalid reset capability | Fault behavior |
| --- | --- |
| Fetch through invalid `PCC` | Capability tag fault, `FAULTCAPIDX = PCC` |
| Load/store through invalid `DSC` or `DDC` | Capability tag fault for the authorizing capability |
| `CALL` or `RET` through invalid `RSC` | Return-stack permission/tag fault according to E05-S04 |
| Trap or interrupt entry through invalid `TVC` | Fatal trap-entry or interrupt-entry failure; diagnostic reporting, if exposed, uses `FAULTCAPIDX=TVC` and `CAPCAUSE=TAG` |
| `IRET` through invalid `EPCC` | Capability tag fault for `EPCC` |
| Derivation from invalid `C0-C7` | Capability tag fault |

Payload values are irrelevant when tag is invalid. Tests should check tag behavior rather than expecting a specific reset payload pattern.

## Out of Scope for This Story

- Full scalar cold reset table, MMU reset state, cache reset state, and core lifecycle state: E11-S01.
- Secondary-core mailbox and start-event protocol: E11-S03.
- Trap entry and `TVC` vector sequencing: E07-S04 and E07-S05.
- Debug reset and halt behavior: E12 stories.
- Final exception encoding and priority: E07-S02 and E07-S03.

## Verification Notes

Minimum conformance checks for later simulator, ROM, and RTL work:

- Core 0 reset `PCC` has a valid tag, unsealed state, `EX`, slot 0, and a cursor at the fixed ROM reset vector.
- Core 0 reset `PCC.cursor` is inside the ROM code capability bounds.
- Reset `PCC` lacks store, seal, and unseal permissions unless a platform profile explicitly authorizes otherwise.
- Reset general capability registers `C0-C7` have invalid tags unless documented as part of a reset handoff ABI.
- Reset `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, and `KRC` invalid tags are treated as invalid authority.
- `CMOVE`, `CCSRRD`, and `CCSRWR` preserve invalid reset tags.
- ROM/firmware initializes `KRC`, `KSC`, `DSC`, and `RSC` before using the corresponding authority.
- `DSC.cursor` and `RSC.cursor` are in bounds after initialization.
- `DSC.cursor` and `RSC.cursor` are 4-cell aligned at boot handoff.
- Raw payload bits in ROM, RAM, or scalar CSRs cannot become valid capabilities without a trusted tag-preserving reset mechanism or derivation from an existing valid capability.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| `PCC` is initialized to a ROM code capability. | Met. |
| `KRC`, `KSC`, `DSC`, and `RSC` are initialized by ROM or firmware. | Met. |
| Undefined capability registers have defined invalid-tag behavior. | Met. |
| Reset cannot expose forgeable capability state. | Met. |

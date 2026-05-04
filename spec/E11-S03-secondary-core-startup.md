# E11-S03: Secondary-core Startup

Story: E11-S03

Status: Complete

Normative source: `design.md`, section 14

Prerequisites:

- `spec/E07-S05-vectored-interrupts.md`
- `spec/E11-S01-cold-reset-state.md`

Related sources:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E02-S03-extended-csr-space.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E05-S03-data-stack-model.md`
- `spec/E05-S04-return-stack-model.md`
- `spec/E07-S06-nested-interrupt-rules.md`
- `spec/E08-S03-tso-memory-model.md`
- `spec/E11-S02-reset-capability-state.md`

## Decision

CPU v0.1 starts secondary cores through a per-core start mailbox plus an explicit start signal.

After cold reset, only `COREID=0` is running. Secondary cores remain in the E11-S01 `STOPPED` or `WFI_PARKED` lifecycle state until privileged firmware or kernel software prepares a valid mailbox and sends a platform start signal to the target core.

The startup protocol has three architectural responsibilities:

- Publish the target core's entry state through a per-core start mailbox.
- Signal exactly one target secondary core with an IPI-backed wakeup or a platform start event.
- Transition the target core to `STARTED` only after the mailbox has been validated and the startup capability state has been installed.

## Lifecycle States

E11-S03 extends the E11-S01 core lifecycle model with startup states:

| State | Meaning |
| --- | --- |
| `STOPPED` | The secondary core is not fetching or retiring ordinary instructions. |
| `WFI_PARKED` | The secondary core is parked in a reset-time wait state and is not retiring ordinary startup code. |
| `START_PENDING` | A start signal has been accepted and mailbox validation or startup-state installation is in progress. |
| `STARTED` | The core has accepted a valid mailbox and may fetch, execute, and retire ordinary architectural instructions from the requested entry state. |
| `START_FAILED` | Startup failed before the requested entry state became executable. |

Only secondary cores use `START_PENDING`, `STARTED`, and `START_FAILED` during this story. The boot core is already running after cold reset.

A `STARTED` core may later execute `WFI`, take interrupts, or enter debug state according to the relevant instruction and debug stories. That does not return it to reset-time `WFI_PARKED`.

## Start Mailbox

Each secondary core has one platform-defined start mailbox.

The mailbox may be implemented as normal coherent memory, a tag-aware platform memory region, platform CSRs in the reserved `0x90-0x9F` software IPI and start-event range, or another documented platform mechanism. The exact address, CSR numbers, reset contents, and ownership rules are platform profile details.

The architectural mailbox has these logical fields:

| Field | Required role |
| --- | --- |
| `target_coreid` | Identifies the secondary core that may consume this mailbox. |
| `generation` | Distinguishes a new start request from stale mailbox contents or stale start events. |
| `state` | Reports `EMPTY`, `READY`, `CONSUMED`, or `FAILED`. |
| `entry_pcc` | Valid executable capability or trusted descriptor used to install target `PCC`. |
| `dsc` | Valid data-stack capability or trusted descriptor used to install `DSC`. |
| `rsc` | Valid protected return-stack capability or trusted descriptor used to install `RSC`. |
| `ksc` | Optional valid kernel stack capability or trusted descriptor used to install `KSC`. |
| `krc` | Optional valid root capability or trusted descriptor used to install `KRC`. |
| `tvc` | Optional trap-vector capability or trusted descriptor used to install `TVC`. |
| `ddc` | Optional default data capability or trusted descriptor used to install `DDC`. |
| `arg0` | Optional scalar startup argument placed in `D0` at entry. |
| `arg_cap0` | Optional capability startup argument placed in `C0` at entry. |
| `failure_code` | Reports why startup did not reach `STARTED`, if applicable. |

`entry_pcc`, `dsc`, `rsc`, `ksc`, `krc`, `tvc`, `ddc`, and `arg_cap0` cannot be ordinary untagged payload bits pretending to be capabilities. A mailbox implementation must use one of these valid authority paths:

- Tagged capability slots in coherent memory, written by `CSC` and read by a tag-preserving startup path.
- Existing valid capabilities copied through a platform-defined trusted startup mechanism.
- Trusted reset firmware or reset hardware deriving capabilities from an existing valid reset authority.
- A platform reset manifest that preserves capability tags outside ordinary integer dataflow.

Raw scalar mailbox values may describe addresses, sizes, or selectors, but raw values do not create valid tags. If a platform uses scalar descriptors, trusted startup firmware or hardware must derive the actual capabilities from valid authority before the core can reach `STARTED`.

## Mailbox Publication

Firmware or kernel software starts a secondary core by publishing the mailbox in this order:

1. Ensure the target core is in `STOPPED`, `WFI_PARKED`, or `START_FAILED`.
2. Write all mailbox fields for the new request.
3. Set `target_coreid` to the intended target core.
4. Set a new `generation` value different from the previously consumed generation for that target.
5. Set `state=READY`.
6. Execute the ordering operation required by the mailbox's storage class.
7. Send an IPI-backed wakeup or platform start event to the target core.

For a mailbox stored in normal coherent cacheable memory, the required ordering operation is `FENCE`. The `FENCE` must make all older mailbox stores globally visible before the start event can be observed by the target.

For a mailbox implemented through platform CSRs or device memory, the platform profile must specify the required ordering sequence. Until E08-S04 and E10-S05 finalize fence and cache-maintenance details, portable v0.1 firmware should use normal coherent cacheable memory for the start mailbox.

The boot core must not update a `READY` mailbox in place after sending the start event. To change a pending request, software must wait for `CONSUMED`, `FAILED`, or a platform-defined cancellation path.

## Start Signal

The start signal targets exactly one secondary core.

A conforming platform may implement the signal as:

- A platform start event that releases a `STOPPED` or `WFI_PARKED` core into startup validation.
- A software-IPI-backed wakeup that sets the target's `IPENDING.SOFTWARE_IPI` latch and also releases reset-time parking.
- A combined platform mechanism that performs both actions.

For a core that is still in `STOPPED` or reset-time `WFI_PARKED`, the start signal is a lifecycle event. It does not require `SR.IE=1`, `IENABLE.SOFTWARE_IPI=1`, or a valid `TVC`, and it does not perform ordinary E07-S05 interrupt entry.

For a core that is already `STARTED`, software IPI delivery follows E07-S05. A start signal sent to an already `STARTED` core must not replace that core's `PCC`, stack, root authority, scalar state, or capability state.

## Startup Validation

When the target observes a start signal, it enters `START_PENDING` and validates the mailbox before reaching `STARTED`.

Required validation:

| Check | Failure code |
| --- | --- |
| Mailbox `state=READY` | `NOT_READY` |
| `target_coreid` equals the target core's `COREID` | `WRONG_CORE` |
| `generation` is newer than the last consumed generation for this core | `STALE_GENERATION` |
| Startup authority path can install a valid `PCC` | `INVALID_PCC` |
| `PCC` is unsealed, has `EX`, has slot `0`, and `PCC.cursor` is in bounds | `INVALID_PCC` |
| Startup authority path can install valid `DSC` and `RSC` before stack or call use | `INVALID_STACK` |
| `DSC.cursor` and `RSC.cursor` are 4-cell aligned at public startup handoff | `INVALID_STACK` |
| Any provided `KSC`, `KRC`, `TVC`, `DDC`, or `arg_cap0` capability has a valid tag and legal permissions for its role | `INVALID_CAPABILITY` |
| Raw scalar descriptors, if used, can be derived only through valid trusted authority | `INVALID_DESCRIPTOR` |

If validation fails:

- The target core must not fetch through the requested `entry_pcc`.
- The target core must not expose partial startup capability state to ordinary software.
- The target lifecycle becomes `START_FAILED` or returns to the documented parked state with mailbox `state=FAILED`.
- `failure_code` records the reason where the platform mailbox exposes it.
- The failed start signal is consumed for that generation.

Startup validation failure is not an ordinary trap through `TVC`. The target may not yet have valid trap-vector authority.

## Successful Startup State

On a successful start, the target transitions to `STARTED` and enters the requested startup state.

Required target architectural state at the first instruction of the requested entry:

| State | Required value |
| --- | --- |
| Lifecycle | `STARTED` |
| `COREID` | Target core number, `1-3` |
| `PCC` | Valid `entry_pcc`, unsealed, `EX`, slot `0`, cursor in bounds |
| `SR.PRIV` | `1` (`K`) |
| `SR.IE` | `0` |
| `SR.EXL` | `0` |
| `SR.SLOT` | `0` |
| `SATP` | `0` unless a later platform profile explicitly defines a virtualized startup handoff after E09-S02/E09-S03 |
| `ASID` | `0` unless paired with a documented nonzero `SATP` startup handoff |
| `DSC` | Valid before ordinary stack use |
| `RSC` | Valid before `CALL` or `RET` use |
| `KSC` | Valid before trap, interrupt, or debug stack use if those paths can run |
| `KRC` | Valid if the target startup code is expected to derive authority |
| `TVC` | Valid before the target enables traps or interrupts |
| `DDC` | Invalid unless intentionally provided |
| `D0` | `arg0`, or `0` if no scalar argument is provided |
| `C0` | `arg_cap0`, or invalid tag if no capability argument is provided |

General integer registers other than `D0` start as `0` unless the platform startup ABI documents another intentional argument. General capability registers other than `C0` have invalid tags unless the platform startup ABI documents another intentional capability argument.

The target's `IENABLE` starts at `0`. If the start signal set `IPENDING.SOFTWARE_IPI`, startup code must clear or mask it before enabling interrupts unless it intentionally wants immediate software IPI delivery.

The mailbox producer may set `state=CONSUMED` before or as part of the transition to `STARTED`. A platform may instead require target startup code to acknowledge `CONSUMED` after its first instructions, but it must document the ordering so the boot core can distinguish accepted startup from failure.

## Capability and Stack Requirements

Startup capability state must preserve the capability integrity rules from E11-S02.

Minimum requirements:

- `entry_pcc` must not grant store, seal, or unseal authority unless the target startup ABI explicitly requires it.
- `DSC` must be valid, unsealed, local, in bounds, and have the load/store/capability permissions needed by E05-S03 before ordinary stack use.
- `RSC` must be valid, unsealed, local, in bounds, 4-cell aligned, and have the permissions needed by E05-S04 before protected return-stack use.
- `KSC` must be valid before any trap, interrupt, or debug handler expects to use a kernel stack.
- `TVC` must be valid, unsealed, executable, and in bounds before the target enables `SR.IE` or any `IENABLE` source.
- `KRC` must be valid only if broad derivation authority is intentionally delegated to the target.
- Any startup capabilities not intentionally delegated must have invalid tags.

If the mailbox passes stack bounds as scalar descriptors rather than capabilities, trusted startup logic must derive `DSC`, `RSC`, and `KSC` from valid authority. Ordinary scalar writes to mailbox memory or CSRs cannot create these tags.

## Ordering and Visibility

For normal coherent cacheable mailboxes, the publication `FENCE` and the target's mailbox reads use the E08-S03 memory model.

Required visibility properties:

- The target must not observe `state=READY` for a new generation without also being able to observe the associated mailbox fields from that generation.
- The start signal must not be observed before the producer's mailbox stores that are ordered before the publication `FENCE`.
- Tagged mailbox capability slots must preserve payload and tag together according to E03-S04.
- A target `CLC` from a mailbox capability slot must not observe a valid tag with stale payload.
- A boot core polling `state=CONSUMED` or `state=FAILED` must eventually observe the target's mailbox update once that update is globally visible, subject to ordinary progress and cache-maintenance rules.

For noncoherent or device-backed mailboxes, the platform profile must define equivalent visibility rules and any required cache maintenance.

## Invalid Requests and Races

Invalid requests do not partially start a core.

Required behavior:

| Request | Required result |
| --- | --- |
| Start event for `COREID=0` | Rejected or ignored; boot-core state is not replaced. |
| Start event for a nonexistent core ID | Rejected or ignored; no existing core state is changed. |
| Start event for an already `STARTED` core | Rejected or treated as an ordinary software IPI if the platform defines that signal as IPI-backed; startup state is not replaced. |
| Start event with mailbox not `READY` | Target remains parked or enters `START_FAILED` with `NOT_READY`. |
| Start event with stale `generation` | Target remains parked or enters `START_FAILED` with `STALE_GENERATION`. |
| Mailbox capability has invalid tag | Startup fails with `INVALID_PCC`, `INVALID_STACK`, or `INVALID_CAPABILITY`. |
| Mailbox entry target is out of bounds or lacks `EX` | Startup fails with `INVALID_PCC`. |
| Mailbox is modified after start event but before target consumption | Platform behavior is undefined unless the platform profile defines cancellation; portable software must not do this. |

Failure must be visible through the mailbox `state=FAILED`, a documented platform lifecycle status, or both. Failure must not silently execute an unintended target or silently report `STARTED`.

## Out of Scope for This Story

- Exact platform CSR numbers, MMIO addresses, and interrupt-controller register layouts for start events.
- CPU hotplug shutdown or returning a `STARTED` core to `STOPPED`.
- Virtualized secondary startup with a nonzero `SATP` handoff.
- Rich scheduler policy, CPU affinity, and operating-system CPU online state.
- Debug halt priority during secondary startup: E12 stories.
- Cache-maintenance instruction details for noncoherent mailbox storage: E10-S05.
- Remote TLB shootdown after startup: E09-S03 and E08-S04.

## Verification Notes

Minimum conformance checks for later simulator, firmware, and RTL work:

- A secondary core in `STOPPED` or `WFI_PARKED` does not execute the entry point before a start signal.
- Publishing a valid mailbox, executing `FENCE`, and sending a start event transitions the target to `STARTED`.
- The target first enters at `entry_pcc.cursor` with slot `0`, `SR.PRIV=K`, `SR.IE=0`, and `SR.EXL=0`.
- The target receives the intended `DSC` and `RSC` capability tags before stack and return-stack use.
- A tagged `arg_cap0` mailbox slot arrives in `C0` with payload and tag preserved.
- Raw scalar mailbox payload bits do not create valid capabilities.
- An invalid `entry_pcc` tag fails startup before target fetch.
- A wrong `target_coreid` fails startup without modifying the wrong core.
- A stale generation fails or is ignored.
- A start event sent to an already `STARTED` core does not replace its execution state.
- If the start signal sets `IPENDING.SOFTWARE_IPI`, startup code can observe and clear that latch before enabling interrupts.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Kernel or firmware writes a per-core start mailbox. | Met. |
| Kernel or firmware sends an IPI or start event. | Met. |
| Target core transitions to `STARTED`. | Met: valid mailbox plus accepted start signal transitions the target to `STARTED`. |
| Startup capability and stack state requirements are documented. | Met. |
| Failed startup or invalid mailbox behavior is specified. | Met. |

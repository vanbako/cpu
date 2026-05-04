# E11-S01: Cold Reset State

Story: E11-S01

Status: Complete

Normative source: `design.md`, section 14

Prerequisites:

- `spec/E01-S04-special-capability-registers.md`
- `spec/E02-S02-mandatory-scalar-csrs.md`

Related sources:

- `spec/E01-S06-status-register-behavior.md`
- `spec/E03-S04-memory-tag-rules.md`
- `spec/E04-S04-control-transfer-instructions.md`
- `spec/E07-S05-vectored-interrupts.md`
- `spec/E09-S01-address-and-page-size.md`
- `spec/E10-S01-cache-hierarchy.md`
- `spec/E10-S03-cpu-coherence-protocol.md`
- `spec/E11-S02-reset-capability-state.md`

## Decision

Cold reset establishes a deterministic architectural starting point for firmware.

CPU v0.1 has one boot core and three secondary cores. The boot core is the core whose `COREID` CSR reads `0`. After cold reset, only the boot core begins normal instruction execution. Secondary cores remain parked until the secondary-core startup protocol defined by E11-S03 releases them.

The reset entry point is a fixed ROM cell address named `RESET_VECTOR`. A conforming platform must define exactly one `RESET_VECTOR` value for its reset profile. That value must be stable across cold resets for that platform and must be inside the executable ROM region authorized by the reset `PCC` defined in E11-S02.

## Core Lifecycle at Cold Reset

Cold reset applies to all four v0.1 cores.

| Core | Required lifecycle state after cold reset | Required `COREID` |
| --- | --- | ---: |
| Boot core | `RUNNING` | `0` |
| Secondary core 1 | `STOPPED` or `WFI_PARKED` | `1` |
| Secondary core 2 | `STOPPED` or `WFI_PARKED` | `2` |
| Secondary core 3 | `STOPPED` or `WFI_PARKED` | `3` |

Lifecycle state meanings:

| State | Meaning |
| --- | --- |
| `RUNNING` | The core may fetch, execute, and retire ordinary architectural instructions. |
| `STOPPED` | The core does not fetch, execute, or retire ordinary architectural instructions until a later start event releases it. |
| `WFI_PARKED` | The core is parked in an implementation-defined wait state equivalent to a reset-time `WFI` park. It does not retire ordinary reset ROM code before E11-S03 releases it. |

An implementation must document whether secondary cores reset into `STOPPED` or `WFI_PARKED`. In either state, a secondary core must not modify architectural memory, cache-visible data, scalar CSRs, capability state, interrupt state, or performance counters by executing ordinary instructions before the E11-S03 startup path begins.

## Boot-core Reset Entry

The first ordinary architectural instruction retired by the boot core after cold reset must be fetched through the reset `PCC` at:

```text
PCC.cursor = RESET_VECTOR
PCC.slot   = 0
```

The boot core starts in kernel mode with the `SR` reset value defined by E01-S06:

| Field | Reset value |
| --- | --- |
| `Z`, `N`, `C`, `V` | `0` |
| `IE` | `0` |
| `PIE` | `0` |
| `PRIV` | `1` (`K`) |
| `PPRIV` | `1` (`K`) |
| `EXL` | `0` |
| `SLOT` | `0` |
| `RES0` | `0` |

Hardware reset must not enter through the trap-vector path. Reset does not write `EPCC`, `CAUSE`, `TVAL`, or `CAPCAUSE` as a trap entry. Reset reporting, if a platform exposes it, is outside the mandatory scalar CSR set.

## Scalar Architectural State

When a core begins normal instruction execution after cold reset, it observes the mandatory scalar CSR reset values from E02-S02 unless ROM or firmware has intentionally written a later value before handing control to that code.

| State | Cold reset value |
| --- | --- |
| `D0-D15` | `0` |
| `SR` | E01-S06 reset value |
| `COREID` | Stable core number, `0-3` in the v0.1 four-core profile |
| `CYCLE` | `0` |
| `INSTRET` | `0` |
| `TVEC` | `0` |
| `CAUSE` | `0` |
| `TVAL` | `0` |
| `SCRATCH` | `0` |
| `IENABLE` | `0` |
| `IPENDING` | `0` for reset-latched mandatory pending state |
| `TIMER` | `0` |
| `TIMECMP` | `0xFFFF_FFFF_FFFF` |
| `SATP` | `0` |
| `ASID` | `0` |
| `DEBUGCTL` | `0` |
| `PERFSEL` | `0` |

`IPENDING` may reflect an external level condition after reset if a platform interrupt controller asserts the external input. Such a condition still cannot be delivered while `SR.IE=0` and `IENABLE=0`.

`INSTRET=0` means no ordinary instruction has retired before boot-core ROM entry. If an implementation performs internal reset sequencing, that sequencing is not counted as retired architectural instructions.

## Capability Reset State

Capability reset state is owned by E11-S02.

Cold reset must be consistent with these E11-S02 rules:

- The boot core has a valid, unsealed `PCC` whose cursor is `RESET_VECTOR`, slot is `0`, and permissions authorize ROM instruction fetch.
- `KRC`, `KSC`, `DSC`, and `RSC` are initialized by ROM, firmware, trusted reset logic, or a platform reset manifest before code relies on them.
- Capability state not explicitly initialized as valid has an invalid tag.
- Reset cannot expose forgeable capability tags through integer registers, scalar CSRs, raw ROM payload bits, or raw RAM payload bits.

Non-boot cores do not expose usable capability authority to ordinary software before E11-S03 starts them.

## MMU and Address Translation Reset State

The MMU is off after cold reset.

`SATP=0` disables address translation. While translation is disabled:

- Instruction fetch uses the effective cell address authorized by `PCC` as the physical cell address.
- Data and capability memory accesses use the effective cell address authorized by the relevant capability as the physical cell address.
- No page-table walk is performed.
- No page fault is generated solely because page tables are absent or uninitialized.
- `ASID=0` is the initial address-space identifier, but it has no translation effect while `SATP=0`.

Any implementation TLB state must be invalid or architecturally ignored after cold reset. Stale pre-reset TLB entries must not affect instruction fetch, data access, capability access, or fault reporting.

## Interrupt Reset State

Interrupts are masked after cold reset.

The required masked state is:

| State | Reset value | Effect |
| --- | --- | --- |
| `SR.IE` | `0` | Global maskable interrupt delivery disabled. |
| `SR.EXL` | `0` | Reset is not trap entry and does not begin in exception level. |
| `IENABLE` | `0` | No mandatory maskable interrupt source is enabled. |
| `IPENDING` | `0` for reset-latched mandatory pending state | No latched software IPI or timer pending state from reset. |
| `TIMECMP` | `0xFFFF_FFFF_FFFF` | Prevents an immediate timer interrupt while `TIMER=0`. |
| `TVEC` | `0` | Base interrupt-vector scalar control state. |

No ordinary maskable interrupt may be delivered before firmware explicitly enables both the relevant `IENABLE` bit and `SR.IE`, and before firmware installs a valid `TVC` according to E11-S02 and the trap-entry stories.

Reset does not clear platform device conditions unless the platform reset profile says so. A platform external interrupt may become pending after reset if the external controller asserts it, but delivery remains masked by `SR.IE=0` and `IENABLE=0`.

## Cache and Coherence Reset State

Caches are off or invalid after cold reset.

CPU v0.1 has no mandatory architectural cache-enable CSR in the fast CSR set. Therefore, a conforming implementation may choose either reset cache policy:

| Policy | Required behavior |
| --- | --- |
| Caches disabled at reset | Instruction fetch and data access behave as if they miss or bypass cache until platform-specific cache controls enable caching. |
| Caches enabled but invalid at reset | All L1 instruction, L1 data, and L2 directory entries start in an invalid or empty state before ordinary boot-core fetch. |

For either policy:

- No dirty L1 or L2 data from before cold reset may be visible after reset.
- No stale capability tag state from before cold reset may be visible after reset.
- No L2 directory owner or sharer state from before cold reset may be visible after reset.
- The first boot-core instruction fetch observes ROM contents and tag state consistent with the reset `PCC` and memory-tag rules.
- If an implementation preloads clean ROM lines, those lines must be indistinguishable from fetching the same ROM contents after reset and must not carry stale dirty, owner, or sharer metadata.

Cache-line contents, coherence state, and tag movement after the first fill follow E03-S04, E10-S01, and E10-S03.

## Other Reset Effects

Cold reset clears transient architectural execution state:

- No instruction is partially retired.
- No store-buffer entry is pending.
- No `LL48` reservation is valid.
- No exception or interrupt is pending as an already-accepted architectural event.

Microarchitectural predictor, predecode, pipeline, replacement, and timing state may take any implementation value after reset if it cannot change the architectural state specified by this story.

RAM contents after cold reset are platform-defined unless a platform reset profile guarantees clearing or initialization. Firmware must initialize RAM and memory capability tags before relying on their contents or authority. ROM contents at `RESET_VECTOR` must be stable and executable through the reset `PCC`.

## Out of Scope for This Story

- Reset capability construction and handoff details: E11-S02.
- Secondary-core mailbox, IPI/start event, and `STARTED` transition: E11-S03.
- Debug halt-on-reset, debug vectors, and debug resume behavior: E12 stories.
- Platform interrupt-controller reset state beyond the mandatory core-visible mask and pending CSRs.
- Platform memory map beyond the requirement for a fixed executable ROM `RESET_VECTOR`.
- Warm reset, power-domain reset, and partial-core reset behavior.
- Cache maintenance instruction semantics and cache-control CSRs: E10-S05.

## Verification Notes

Minimum conformance checks for later simulator, ROM, and RTL work:

- Bind a concrete platform `RESET_VECTOR` and verify boot-core first fetch uses `PCC.cursor=RESET_VECTOR` with slot `0`.
- Verify only `COREID=0` retires ordinary ROM instructions immediately after cold reset.
- Verify secondary cores remain in documented `STOPPED` or `WFI_PARKED` state until E11-S03 releases them.
- Verify `D0-D15` and mandatory scalar CSRs observe the reset values in this story.
- Verify `SATP=0` disables translation for boot ROM fetch and early data access.
- Verify stale TLB state is invalid or ignored after reset.
- Verify no maskable interrupt is delivered while `SR.IE=0` and `IENABLE=0`, even if a pending source is asserted.
- Verify L1 and L2 caches have no valid stale dirty line, owner, sharer, or capability-tag state after reset.
- Verify the first ROM fetch observes ROM contents rather than stale pre-reset cache data.
- Verify no `LL48` reservation survives cold reset.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Reset starts at a fixed ROM reset vector. | Met: `RESET_VECTOR` is a fixed platform reset-profile cell address and boot-core `PCC.cursor`. |
| Only core 0 starts executing after cold reset. | Met. |
| Other cores enter `STOPPED` or `WFI` parked state. | Met: secondary cores reset to `STOPPED` or `WFI_PARKED`. |
| MMU is off. | Met: `SATP=0` disables translation and stale TLB state is invalid or ignored. |
| Interrupts are masked. | Met: `SR.IE=0`, `IENABLE=0`, and timer compare reset prevents immediate timer delivery. |
| Caches are off or invalid. | Met: reset cache policy must be disabled or invalid, with no stale dirty/tag/coherence state visible. |

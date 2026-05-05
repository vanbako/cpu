# Program Image Manifest

Story: I11-S01

Status: Draft implementation profile

Owner sources:

- I07-S03 defines byte-oriented serialization for ordinary 24-bit cell payloads.
- I08-S01 defines the minimal test-platform memory map and reset-vector policy.
- E11-S01 and E11-S02 define cold reset and reset capability state.

## Scope

This profile defines the simulator program-image manifest and the boundary
between image validation and image loading. It does not load bytes into memory;
that belongs to I11-S02. It does not execute a reset-to-program fixture; that
belongs to I11-S03.

## Manifest Fields

A manifest names:

- `name`: non-empty image name.
- `entry_cell`: architectural cell address for slot-0 entry.
- `entry_slot`: always slot 0 for v0.1 image entry.
- `entry_source`: either `RESET_PCC` or `MANIFEST_ENTRY`.
- `sections`: one or more cell-addressed sections.

`RESET_PCC` means the test platform reset path supplies `PCC`, so `entry_cell`
must equal the platform reset vector. `MANIFEST_ENTRY` is reserved for trusted
test harnesses that construct an entry `PCC` from the manifest instead of using
platform reset state.

## Sections

Each section wraps an I07-S03 `CellSection` and adds:

- target platform region name;
- section kind: `TEXT`, `RODATA`, `DATA`, or `CAPDATA`;
- tag policy: `UNTYPED_CELLS` or `TRUSTED_CAPABILITY_SIDECAR`.

Sections are loadable only into ROM or RAM regions from the test-platform
profile. `TEXT` requires an executable region. `DATA` and `CAPDATA` require
writable RAM. Device and mailbox regions are not image-load targets in this
profile.

Section ranges are half-open cell ranges. Empty sections, overlapping sections,
duplicate names, out-of-region placement, and unknown target regions are invalid
image failures.

## Capability Tags

Ordinary section payload cells never create valid capability tags. Loading an
ordinary `UNTYPED_CELLS` section must clear or leave clear the memory tags for
overlapped capability slots.

`CAPDATA` is the only section kind that may request
`TRUSTED_CAPABILITY_SIDECAR`. The sidecar path is a future trusted-loader
boundary: it may install payload and tag atomically, but it must target RAM,
start on a 4-cell capability slot, and cover a whole number of capability
slots. The sidecar format itself is intentionally left to I11-S02 or a later
loader story.

## Entry Acceptance

Every valid manifest must place `entry_cell` inside a `TEXT` section that
targets an executable region. Entry always enters slot 0. A manifest that asks
for slot 1 entry is invalid even if a decoded 12-bit instruction could
eventually reach slot 1 by fall-through.

## Loader Boundary

I11-S01 validation is side-effect free. A valid manifest only says that a future
loader may attempt to load the image. Actual writes into `TaggedMemory`, tag
clearing, sidecar tag installation, reset-state construction, and executable
program stepping remain separate implementation stories.

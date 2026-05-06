# User Process Entry Fixture

Story: I18-S01

Status: Draft executable fixture

## Scope

This story defines the first simulator fixture for entering a user process from
kernel-owned setup code. It builds on the program-image loader, minimal kernel
handler fixtures, ABI register windows, and SATP/ASID state. It does not define
VM page allocation, syscall round trips, or scheduling; those remain I18-S02
through I18-S04.

## Image

The fixture image is a `MANIFEST_ENTRY` program image named
`user_process_demo`. Its text section lives in executable boot ROM at the user
entry cell and contains a tiny `SYS`/`PAUSE` sequence. Its data section lives in
main RAM and seeds the scalar argument value used by the entry-context tests.

The user entry image is rejected when:

- the manifest does not use `MANIFEST_ENTRY`;
- the entry slot is not slot 0;
- the entry cell is not covered by a text section in an executable region;
- the ordinary program-image manifest validator reports section, region, or
  overlap errors.

Loading validates the complete user entry context before writing image cells.
Invalid setup therefore fails without partial state in simulator memory.

## Entry Context

`UserEntryContext` packages the architectural state a minimal kernel fixture
must install before entering user mode:

- a slot-0 executable `PCC` bounded to the manifest text section;
- local `DSC` and `RSC` stack capabilities in main RAM;
- a `SATP` value with a nonzero ASID;
- integer arguments in `D0-D5` and capability arguments in `C0-C3`;
- user interrupt-enable policy and protected return-stack policy.

Entering a context first validates every image and context field. Only after
validation succeeds does it clear volatile simulator register windows, install
the user `PCC`, `DSC`, `RSC`, `SATP`, and `ASID`, invalidate local TLB state,
clear the LL/SC reservation, set user privilege state, and optionally protect
the return-stack range in `TaggedMemory`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Kernel fixture installs user `PCC`, `DSC`, `RSC`, `SATP`, ABI arguments, and privilege state. | Met. |
| User entry reaches user mode with interrupts following the context policy. | Met. |
| Entry invalidates stale local TLB state and clears reservations. | Met. |
| Invalid image setup rejects before memory writes. | Met. |
| Invalid context setup rejects before core-state mutation. | Met. |

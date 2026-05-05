# Secondary-Core Boot Demo

Story: I14-S03

Status: Draft executable fixture

Owner sources:

- I08-S02 defines the start mailbox and platform start-event binding.
- I14-S01 installs trusted boot capability authority.
- I14-S02 establishes the first firmware/kernel handler fixture layer.
- E11-S03 defines secondary-core startup state transitions.

## Scope

The I14-S03 fixture demonstrates the first firmware-controlled secondary-core
bring-up path in simulation. It reuses the `SecondaryStartupController` from the
platform binding instead of defining a new startup protocol.

The boot core:

- runs the tiny ROM handoff initialization;
- derives trusted tagged startup capabilities;
- publishes a mailbox for one secondary core;
- sends the platform start signal;
- observes the target transition to `STARTED`;
- attempts a repeated start and verifies live secondary state is not replaced;
- publishes an invalid mailbox for another secondary core and observes a
  rejected startup with no partial execution state.

## Handoff

The valid mailbox installs:

- a slot-0 executable `PCC` for the secondary entry stub;
- local `DSC`, `RSC`, and `KSC` stack capabilities;
- inherited `KRC` and `TVC` authority from trusted ROM setup;
- `D0` as a boot argument;
- `C0` as an optional tagged startup capability.

The demo keeps `SATP=0`, `ASID=0`, `IENABLE=0`, and `IPENDING=0` for the
started secondary core, matching the current platform startup profile.

Repeated start signals report `ALREADY_STARTED` and do not replace `PCC`,
stack authority, argument registers, or capability state. Invalid mailboxes
transition the target to `START_FAILED` and leave the invalid target unable to
fetch the requested entry.

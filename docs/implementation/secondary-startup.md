# Secondary-Core Startup Binding

Story: I08-S02

The test platform uses one logical start mailbox per secondary core, backed by the `secondary_mailbox` platform MMIO region. The simulator binding models the mailbox as trusted platform state so capability tags are copied as tags, not reconstructed from raw scalar payload bits.

## Publication

Firmware publishes all fields, sets `state=READY`, executes the ordering sequence for the mailbox storage class, then sends a platform start event to exactly one secondary core.

For the test platform, the start event is a lifecycle event rather than ordinary interrupt entry. It does not require `SR.IE`, `IENABLE`, or a valid `TVC` while the target is still `STOPPED` or reset-time `WFI_PARKED`.

## Required Mailbox Fields

- `target_coreid`
- `generation`
- `entry_pcc`
- `dsc`
- `rsc`
- optional `ksc`, `krc`, `tvc`, `ddc`, `arg0`, and `arg_cap0`

`entry_pcc`, stack capabilities, optional capabilities, and `arg_cap0` must already carry valid tags through a trusted startup path. Raw scalar descriptors are not accepted by this binding.

## Result States

- A valid mailbox transitions the target to `STARTED`, installs `PCC`, `DSC`, `RSC`, optional capabilities, `D0`, and optional `C0`, and marks the mailbox `CONSUMED`.
- Invalid requests set mailbox `state=FAILED`, record a failure code, and leave the target unable to fetch the requested entry.
- A start event for an already `STARTED` core does not replace live execution state.

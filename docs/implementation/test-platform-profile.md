# CPU v0.1 Test Platform Profile

Story: I08-S01

This profile binds the frozen CPU v0.1 reset requirements to a concrete simulator/test platform. All addresses are cell addresses.

## Reset

- `RESET_VECTOR = 0x0000_1000`.
- Core count is four.
- Core 0 resets to `RUNNING` and fetches through a valid slot-0 ROM `PCC`.
- Secondary cores reset to `STOPPED` until the E11-S03 startup binding releases them.
- `SATP=0`, `ASID=0`, interrupts are masked, `DEBUGCTL=0`, and no LL/SC reservation is valid after reset.

The reset `PCC` is bounded to the `boot_rom` region, is global, unsealed, and grants only `EX`.

## Memory Map

| Region | Cell range | Type | Authority |
| --- | ---: | --- | --- |
| `boot_rom` | `[0x0000_1000, 0x0000_2000)` | Normal coherent ROM | `EX` |
| `main_ram` | `[0x0001_0000, 0x0002_0000)` | Normal coherent RAM | `LD`, `ST`, `LC`, `SC`, `SL` |
| `platform_devices` | `[0x00F0_0000, 0x00F0_1000)` | Device ordered MMIO | `LD`, `ST` |
| `secondary_mailbox` | `[0x00F0_1000, 0x00F0_1100)` | Device ordered MMIO | `LD`, `ST` |

RAM contents and memory tags are uninitialized after cold reset. Firmware must initialize RAM payloads and tags before relying on them.

## Fatal Entry

Trap-entry or interrupt-entry delivery failure uses the test profile's `DEBUG_HALT` fatal policy. It is visible to platform debug/fatal machinery and is not recursively delivered as an ordinary trap through the same invalid vector state.

## Debug Policy

The test platform exposes a simulated MMIO debug transport. Cold reset does not halt the core by default. External debug may halt or resume cores through the documented debug transport and architectural `DEBUGCTL` behavior.

## Cache Policy

Caches are disabled at reset for the test profile. Instruction fetch and data access behave as misses or bypasses until later platform cache controls are introduced.

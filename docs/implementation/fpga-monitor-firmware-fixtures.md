# FPGA Monitor Firmware Fixtures

Story: I32-S02

Status: ROM monitor and trap-shell firmware fixtures defined

Structured gate:

```text
python tools\fpga_monitor_firmware.py --check
```

List fixtures:

```text
python tools\fpga_monitor_firmware.py --list
```

Run fixture model:

```text
python tools\fpga_monitor_firmware.py --fixtures
```

## Purpose

I32-S02 adds the executable firmware-side fixture layer for the I32-S01
interactive monitor command profile. The model represents the ROM monitor and
trap-shell state machine that receives a bounded command stream, validates
program-image metadata, reports failures through UART/debug status, and returns
to either `safe_idle` or `trap_shell_idle` without corrupting architectural
state.

Required upstream gates:

```text
python tools\fpga_monitor_profile.py --check
python tools\fpga_program_loader.py --check
python tools\fpga_uart_status_streamer.py --check
python tools\fpga_debug_status_packet.py --check
python -m unittest tests.conformance.test_i14_s02_kernel_handlers
```

This story does not replace the FPGA top-level loader handoff, create a ROM
assembly image, or claim an interactive board session. I32-S03 consumes these
fixtures for multi-program monitor sessions. I32-S04 consumes the status and
memory-read paths for replayable debug snapshots.

## Firmware States

| State | Meaning |
| --- | --- |
| `rom_monitor_idle` | Reset ROM monitor is halted and ready for host commands. |
| `safe_idle` | A non-trap failure was reported before stateful corruption; monitor remains halted. |
| `trap_shell_idle` | Trap shell is active after a trap/debug halt and remains available for inspection. |
| `program_running` | A valid `RESUME` left the monitor and selected an allowed ROM entry cell. |

The command stream bound is `8` monitor requests. Longer streams fail with
`BAD_LENGTH` before any command payload mutates memory.

## Fixture Matrix

| Fixture | Command stream | Expected result |
| --- | --- | --- |
| `rom_monitor.load_resume_ok` | `HELLO`, `HALT`, `LOAD_IMAGE`, `READ_STATUS`, `RESUME` | Installs `relocation.branch_call_data_fpga`, clears `tag_ram`, reports `OK`, and enters `program_running`. |
| `rom_monitor.reject_bad_hash` | `HELLO`, `HALT`, `LOAD_IMAGE` with a stale manifest hash | Reports outer `LOADER_ERROR`, preserves the loader `BAD_HASH` payload status, leaves `data_ram` and `tag_ram` unchanged, and enters `safe_idle`. |
| `trap_shell.bad_command_idle` | trap `HALT`, unsupported command, `READ_STATUS` | Reports `BAD_COMMAND`, leaves memory unchanged, and remains in `trap_shell_idle`. |

`LOAD_IMAGE` delegates accepted writes to I26-S04. The monitor fixture uses
bounded chunks of at most `16` cells while the loader validates the full
manifest image hash, `data_ram` hash, payload hash, target range, and
`tag_bits_all_zero` policy.

## Failure Reporting

Every command result emits an ASCII status line such as:

```text
I32-S02 MONITOR ERR command=LOAD_IMAGE status=LOADER_ERROR loader=BAD_HASH state=safe_idle
```

The same result carries an I25-S01 debug/status packet. Successful idle commands
use `idle_or_reset`, a successful `RESUME` uses `running`, and failures use
`blocked` with `fault_valid` set and the outer monitor status code in
`fault_code`. The detailed loader status such as `BAD_HASH` remains part of the
command payload.

## Trap Shell

The trap-shell restore fixture reuses the I14-S02 software trap-frame helpers.
It restores `EPCC`, `SR`, `CAUSE`, `TVAL`, `CAPCAUSE`, and `FAULTCAPIDX`, then
returns through the architectural `IRET` helper. The fixture proves the final
`PCC` cell and slot match the restored `EPCC` and that the monitor can leave the
trap shell without inventing a separate return path.

## Non-Corruption Rules

- Frame parse, unsupported command, bad metadata, and tag-policy failures report
  status before memory writes.
- Accepted `LOAD_IMAGE` traffic delegates all `data_ram` writes and `tag_ram`
  clearing to I26-S04.
- Trap-shell resume restores the I14-S02 software trap frame and returns through
  `IRET`.
- `safe_idle` and `trap_shell_idle` keep the monitor halted until an explicit
  valid `RESUME`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Monitor firmware can receive a bounded command stream. | Met by the `8` command limit and the `rom_monitor.load_resume_ok` stream. |
| Image metadata is validated. | Met by the `rom_monitor.reject_bad_hash` fixture and I26-S04 hash checks. |
| Failures are reported. | Met by UART status text plus I25-S01 debug/status packets carrying `LOADER_ERROR`, `BAD_HASH`, and `BAD_COMMAND` outcomes. |
| Monitor returns to safe idle or trap shell without corrupting state. | Met by no-mutation checks for `data_ram`, `tag_ram`, and loaded-program state in failure fixtures. |
| Trap-shell return uses existing kernel/trap semantics. | Met by the I14-S02 trap-frame restore and `IRET` fixture. |

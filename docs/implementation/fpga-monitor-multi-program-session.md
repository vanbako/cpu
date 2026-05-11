# FPGA Monitor Multi-Program Session

Story: I32-S03

Status: Multi-program monitor session fixture defined

Structured gate:

```text
python tools\fpga_monitor_session.py --check
```

Run the modeled session:

```text
python tools\fpga_monitor_session.py --run
```

## Purpose

I32-S03 models one interactive monitor session that loads and starts multiple
board-safe programs. The session uses the I32-S02 ROM monitor fixture for
`HALT`, `LOAD_IMAGE`, `READ_STATUS`, and `RESUME`, the I26-S02 BRAM image
bundle hashes for metadata validation, and the I26-S05 smoke corpus for
distinct expected LED, expected UART, and expected probe signatures.

Required gates:

```text
python tools\fpga_monitor_firmware.py --check
python tools\fpga_bram_images.py --check
python tools\fpga_smoke_corpus.py --check
```

This is still a deterministic fixture, not a physical board pass. I32-S06 owns
the captured board session or blocker record. I32-S04 adds replayable debug
snapshots, and I32-S05 expands the interactive board program corpus.

## Selected Programs

The default session selects two image-ready I26-S05 cases:

| Order | Case | Program | Expected result |
| --- | --- | --- | --- |
| 1 | `scalar_control.call_return` | `call_return.direct_call_ret_fpga` | `pass_after_harness` |
| 2 | `trap_syscall.sys_pause_iret` | `syscall_trap.sys_pause_iret_fpga` | `trap_or_pass_after_harness` |

For each program, the session records:

- `manifest_image_sha256`
- `ram_image_sha256`
- loader status and installed cell count
- `RESUME` start PC
- I25-S01 status packet sequence and state
- expected LED, expected UART, and expected probe signatures
- `signature_digest`
- nearest replay case from the smoke corpus

## Command Flow

The session starts with `HELLO`, then runs a bounded transaction for each
program:

```text
HALT
LOAD_IMAGE manifest_image_sha256 ram_image_sha256
READ_STATUS
RESUME
```

Each per-program transaction is below the I32-S02 `8` command bound. `LOAD_IMAGE`
delegates all memory writes to the I26-S04 loader; accepted images install only
the bounded `data_ram` image and clear matching `tag_ram` sidecar bits.

## Observations

The first program preserves the scalar/control smoke signature:

- expected LED: pass only after a bounded control-flow harness completes
- expected UART: retire progress and no sampled fault
- expected probe: PC leaves the reset vector through the CALL/RET fixture

The second program preserves the trap/syscall smoke signature:

- expected LED: fail may assert until a trap-aware harness completes
- expected UART: trap cause or fault code identifies the syscall trap
- expected probe: EPCC/TVC path matches replay progression

The two observations must have different `signature_digest` values, proving the
session did not collapse both starts into one generic status report.

## Handoffs

- I32-S04 adds register, CSR/CCSR, memory-window, and replay snapshot capture
  for failed sessions.
- I32-S05 expands the interactive board corpus beyond this two-program
  executable fixture.
- I32-S06 captures a physical board session or blocker using the same command
  and signature fields.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A session installs at least two bounded images. | Met by the two selected image-ready I26-S05 programs and I26-S04 loader status checks. |
| Image hashes and statuses are verified. | Met by `manifest_image_sha256`, `ram_image_sha256`, loader `OK`, and installed-cell checks. |
| Each program is started. | Met by `RESUME` returning `OK` and start PC `0x00001000` for each run. |
| Distinct pass/fail/debug signatures are observed. | Met by preserving expected LED/UART/probe signatures and distinct `signature_digest` values for scalar/control and trap/syscall cases. |

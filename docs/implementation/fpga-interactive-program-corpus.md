# FPGA Interactive Program Corpus

Story: I32-S05

Status: `published_interactive_board_program_corpus`

Validator:

```text
python tools\fpga_interactive_corpus.py --check
```

Required upstream gates:

```text
python tools\fpga_monitor_session.py --check
python tools\toolchain_corpus.py --check
python tools\fpga_smoke_corpus.py --check
python tools\fpga_program_loader.py --check
```

## Corpus Scope

The interactive corpus is the publishable board-session selection consumed by
I32-S06. It covers scalar/control, capability memory, trap/syscall, loader
rejection, and failure-path cases. Each row carries manifest_image_sha256,
ram_image_sha256, expected LED, expected UART, expected probe, and a replay or
fixture reproduction command.

| Case | Category | Program | Load Mode | Expected Status |
| --- | --- | --- | --- | --- |
| `scalar_control.call_return` | scalar/control | `call_return.direct_call_ret_fpga` | `monitor_load_image` | `OK` / `OK` |
| `capability_memory.csc_clc_st48_ld48` | capability memory | `capability_memory.csc_clc_st48_ld48_fpga` | `monitor_load_image` | `OK` / `OK` |
| `trap_syscall.sys_pause_iret` | trap/syscall | `syscall_trap.sys_pause_iret_fpga` | `monitor_load_image` | `OK` / `OK` |
| `loader_rejection.bad_hash` | loader rejection | `relocation.branch_call_data_fpga` | `monitor_loader_rejection` | `LOADER_ERROR` / `BAD_HASH` |
| `failure_path.divide_by_zero` | failure-path | `planned.divide_by_zero_fault` | `replay_only_until_fault_harness` | `REPLAY_ONLY` |

## Hash Policy

Image-ready rows copy their generated I26-S02/I26-S04 manifest_image_sha256 and
ram_image_sha256 values from the loader request. The loader rejection row keeps
the selected program hash and also publishes rejected_manifest_image_sha256 as
the stale all-zero hash that must fail before RAM or tag sidecar mutation.

The failure-path divide-by-zero row is intentionally replay-only until the fault
harness can emit a generated board image. Its manifest_image_sha256 and
ram_image_sha256 fields are deterministic planned identity hashes, not evidence
of a programmed BRAM image.

## Expected Observations

The successful monitor-load rows inherit expected UART and expected probe
signatures from I26-S05 so board evidence can distinguish scalar/control
retire progress, capability tag behavior, and trap/syscall cause reporting.

The loader rejection row expects the ROM monitor UART message to include
`LOADER_ERROR` and `BAD_HASH`. The expected probe observation is that data RAM
checksum and tag RAM bits remain unchanged while loaded_program_id remains
empty.

The failure-path row expects fail LED assertion, UART fault_code reporting, and
probe evidence that no destination register write occurs after the precise
divide-by-zero fault. Its replay command is:

```text
python tools\verilator_diff_harness.py --case-id fault_cases.divide_by_zero
```

## Acceptance Review

- The corpus covers scalar/control, capability memory, trap/syscall, loader
  rejection, and failure-path categories.
- Generated manifest hashes are used for every image-ready board program, while
  replay-only planned hashes are explicitly labeled.
- Expected LED, expected UART, and expected probe signatures are preserved for
  every row.
- Loader rejection is reproducible through
  `python tools\fpga_monitor_firmware.py --run-fixture rom_monitor.reject_bad_hash`
  and must report `LOADER_ERROR` / `BAD_HASH` without memory mutation.
- I32-S06 must use this corpus as the board-session input and replace any
  replay-only blocker with captured board evidence when available.

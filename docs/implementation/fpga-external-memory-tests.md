# FPGA External Memory Tests

Story: I29-S03

Status: Firmware profile and executable model; board DDR IP blocked

## Command

Validate the firmware profile and modeled run:

```text
python tools\fpga_external_memory_tests.py --check
```

Inspect the profile, modeled run, case list, or progress codes:

```text
python tools\fpga_external_memory_tests.py --json
python tools\fpga_external_memory_tests.py --run
python tools\fpga_external_memory_tests.py --cases
python tools\fpga_external_memory_tests.py --progress
```

Required gates:

```text
python tools\fpga_ddr_wrapper.py --check
python tools\fpga_smoke_corpus.py --check
python tools\fpga_debug_status_packet.py --check
```

## Scope

I29-S03 defines the BRAM-resident external-memory test firmware for the first
DDR bring-up path. The firmware waits for `controller_ready`, runs from BRAM,
uses `external_ddr_payload` only as data memory, and reports progress through
debug/status observations, UART/status packets, pass/fail LEDs, and probe
captures.

The profile is not a board DDR pass claim. Physical closure still needs the
board-specific DDR controller IP, external-memory decoder in `cpu_v01_fpga_top`,
constraints, timing reports, bitstream handoff, and captured board evidence.

## Test Cases

| Case | Category | External DDR use | Expected UART/status | Expected probe |
| --- | --- | --- | --- | --- |
| `walking_pattern.low_window` | `walking_pattern` | Writes and reads eight 24-bit walking-pattern cells. | Complete progress with no `fault_code`. | `controller_ready` and matching readback. |
| `address_line.power_of_two_offsets` | `address_line` | Writes unique sentinels at power-of-two offsets. | Complete progress with no alias fault. | Distinct `ext_mem_req_addr` offsets. |
| `burst.contiguous_cells` | `burst` | Writes and reads a contiguous 16-cell burst. | Retire/progress advances through burst completion. | Monotonic external-memory request addresses. |
| `alignment.integer_object` | `alignment` | Confirms aligned integer-object access and an expected misaligned access fault. | Expected `ACCESS_FAULT` sample then recovery. | No controller transaction for the misaligned request. |
| `fault_injection.controller_error` | `fault_injection` | Forces one controller-side error sample. | Expected `ACCESS_FAULT` sample with visible failure then recovery. | `fail_visible_o` and `status_error_code_o` captured. |

## Progress Contract

The firmware emits one 24-bit progress code per case and finishes with
`0x2903F0` on pass or `0x2903FF` on fail. The progress codes are intended to be
visible through the GPIO/status software vector, UART/status packet fields, or
optional probes. A failure path preserves the first `ACCESS_FAULT` sample so
I25-S04 replay mapping and I25-S05 debug-evidence classification can consume it.

## Handoff

- I29-S04 owns cacheability, ordering, and capability-tag policy before
  off-BRAM execution or trusted tag sidecars are claimed.
- I29-S05 archives board DDR calibration, memory-test pass/fail, UART/status,
  timing, and residual blocker evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Walking pattern, address-line, burst, alignment, and fault-injection cases are all named. | Met by the profile cases. |
| Tests run from BRAM and use DDR only as data memory. | Met by `bram_resident` execution and `external_ddr_payload` addressing. |
| Progress is visible through debug/status output. | Met by progress codes, UART/status signatures, and probe signatures. |
| Fault-injection and alignment failures become CPU-owned `ACCESS_FAULT` samples. | Met by the modeled run and validation. |
| Physical board pass remains blocked until DDR IP and top-level integration exist. | Met by `blocked_until_board_ddr_ip` status and blocker list. |

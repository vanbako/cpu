# FPGA External Memory Boundary

Story: I29-S01

Status: Boundary profile

## Command

Validate the profile:

```text
python tools\fpga_external_memory.py --check
```

Print the structured profile:

```text
python tools\fpga_external_memory.py --json
```

Required prerequisite gates:

```text
python tools\fpga_soc_platform.py --check
python tools\fpga_reproducible_build.py --check
python -m unittest tests.conformance.test_i19_s03_external_transfers
python -m unittest tests.litmus.test_i06_s04_memory_litmus
```

## Scope

I29-S01 defines the CPU-owned external-memory boundary for the first DDR
bring-up path. It separates the CPU request/response interface, DDR controller
calibration status, visible memory window, cacheability, tag policy, and
CPU-owned fault behavior from board-specific IP details.

This story does not instantiate a vendor DDR controller, name physical DDR
pins, claim timing closure, or prove board calibration. I29-S02 owns the
board-specific IP wrapper and calibration visibility. I29-S04 owns the later
cache, ordering, and capability-tag policy evidence for external memory.

## Memory Window

The first bring-up reserves a CPU-visible payload window above the existing
BRAM/MMIO map:

| Field | Value |
| --- | --- |
| Name | `external_ddr_payload` |
| Base | `0x01000000` |
| End | `0x02000000` |
| Size | `0x01000000` cells |
| Memory type | normal uncacheable |
| Access | Payload LD/ST after `controller_ready`; no fetch requirement for I29-S01. |
| Cacheability | Normal uncacheable until I29-S04 provides coherent/cacheable evidence. |

The window does not overlap boot ROM, main RAM, `platform_devices`, or the
secondary mailbox. Address decode outside this window remains with the existing
platform map.

## DDR Controller Boundary

The CPU shell observes an abstract DDR controller adapter, not board-specific
DDR pins or vendor PHY internals:

| Signal | Direction | Width | Owner |
| --- | --- | --- | --- |
| `ext_mem_req_valid` | out | 1 | CPU shell |
| `ext_mem_req_ready` | in | 1 | DDR controller adapter |
| `ext_mem_req_write` | out | 1 | CPU shell |
| `ext_mem_req_addr` | out | 48 | CPU shell |
| `ext_mem_req_wdata` | out | 48 | CPU shell |
| `ext_mem_req_wstrb` | out | 2 | CPU shell |
| `ext_mem_rsp_valid` | in | 1 | DDR controller adapter |
| `ext_mem_rsp_ready` | out | 1 | CPU shell |
| `ext_mem_rsp_rdata` | in | 48 | DDR controller adapter |
| `ext_mem_rsp_error` | in | 1 | DDR controller adapter |
| `ddr_ui_clk` | in | 1 | board-specific IP wrapper |
| `ddr_ui_reset` | in | 1 | board-specific IP wrapper |

The board-specific IP wrapper owns physical DDR pinout, byte-lane width,
training parameters, PHY reset sequencing, PLL outputs, generated-clock
constraints, and vendor burst adaptation. The CPU side owns only the
cell-addressed request/response contract and the architectural result of a
transaction.

## Calibration Status

The status contract records enough DDR controller visibility for firmware,
UART/status output, and later board evidence:

| Field | Access | Reset | Meaning |
| --- | --- | --- | --- |
| `calibration_done` | ro | 0 | DDR training completed and traffic may be considered. |
| `calibration_error` | ro | 0 | Calibration failed or timed out. |
| `init_in_progress` | ro | 1 | Controller initialization or training is active. |
| `controller_ready` | ro | 0 | Derived traffic gate: `calibration_done` and no `calibration_error`. |
| `access_gate_closed` | ro | 1 | CPU external-memory requests are blocked. |
| `error_code` | ro | 0 | Board-wrapper normalized controller or timeout error. |
| `reset_request` | wo | 0 | Firmware/debug request to reinitialize the wrapper. |

I29-S02 chooses the exact MMIO or debug/status packet placement for these
fields. I29-S01 only fixes their names and CPU-visible meaning.

## Cache And Tag Policy

The first external memory window is normal uncacheable. Payload reads and writes
are visible after the controller response without CPU cache maintenance. This
keeps the first DDR bring-up aligned with the existing E10 cache-maintenance
fixtures and avoids claiming coherent behavior before I29-S04.

The tag policy is intentionally conservative: the external DDR window has no
trusted capability-tag sidecar in I29-S01. `CLC` and `CSC` to
`external_ddr_payload` are CPU-owned access faults until I29-S04 defines a tag
sidecar or a stricter no-capability rule. Integer and payload memory tests can
still use ordinary LD/ST traffic.

## CPU-Owned Fault Rules

| Rule | Condition | Result |
| --- | --- | --- |
| `calibration_not_ready` | External-memory load, store, or fetch before `controller_ready`. | CPU-owned fault: precise `ACCESS_FAULT`, no controller request, `tval` is the effective cell address. |
| `controller_error` | Adapter returns `ext_mem_rsp_error`. | CPU-owned fault: precise `ACCESS_FAULT` with sticky status available through I29-S02 visibility. |
| `external_window_decode` | Address falls outside `external_ddr_payload`. | Existing CPU memory-map fault behavior applies before any DDR controller request. |
| `tag_sidecar_unavailable` | `CLC` or `CSC` targets external DDR before a tag sidecar exists. | CPU-owned fault: precise `ACCESS_FAULT`; payload LD/ST remains available. |
| `cache_policy_mismatch` | Cache maintenance or coherent ownership handoff is requested for the first normal uncacheable DDR window. | Existing E10/I06 memory-type policy decides the fault or no-op before the controller boundary. |

The DDR controller reports readiness, completion, and adapter errors; it does
not create architectural exception packets.

## Handoffs

- I29-S02 instantiates the board DDR controller wrapper, synchronizes
  calibration status, and exposes pass/fail visibility.
- I29-S03 adds BRAM-resident walking-pattern, address-line, burst, alignment,
  and fault-injection firmware tests.
- I29-S04 decides whether external memory can become coherent/cacheable and how
  capability tags are represented or forbidden.
- I29-S05 captures first board evidence for calibration, timing, memory-test
  results, UART/status output, and any remaining blockers.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| DDR controller signals are separated from physical board IP. | Met by the abstract request/response and UI clock/reset boundary. |
| Calibration status is explicit. | Met by `calibration_done`, `calibration_error`, `controller_ready`, and related fields. |
| Memory window is reserved without overlapping existing regions. | Met by `0x01000000` through `0x02000000`. |
| Cacheability is defined. | Met by the normal uncacheable first-bring-up policy. |
| Tag policy is explicit. | Met by the deferred tag-sidecar rule and I29-S04 handoff. |
| CPU-owned fault behavior is separated from DDR IP errors. | Met by the fault table. |

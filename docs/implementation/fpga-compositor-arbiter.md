# FPGA Compositor Memory Arbiter

Story: I36-S08

Status: CPU/compositor arbitration fixture implemented

## Command

Validate the arbiter profile:

```text
python tools\fpga_compositor_arbiter.py --check
```

Print structured data, the arbitration demo, visible counters, or the Verilator
plan:

```text
python tools\fpga_compositor_arbiter.py --json
python tools\fpga_compositor_arbiter.py --demo
python tools\fpga_compositor_arbiter.py --counters
python tools\fpga_compositor_arbiter.py --plan
```

Required prerequisite gates:

```text
python tools\fpga_compositor_fetch.py --check
python tools\fpga_soc_top_decoder.py --check
python tools\fpga_ddr_wrapper.py --check
python tools\fpga_video_mmio.py --check
```

## Scope

I36-S08 defines the board-neutral arbitration point between I30-S02 CPU
data/MMIO decoder traffic, the I29-S02 DDR adapter, the I35-S04 video status
surface, and the I36-S02 compositor scanout read master. The fixture keeps the
first integration deterministic: one outstanding memory transaction is accepted
at a time, CPU data/MMIO traffic preserves ordering, and scanout traffic sees
explicit backpressure instead of implicit drops.

The standalone RTL module is `cpu_v01_fpga_compositor_mem_arbiter`. It is a
focused integration fixture rather than a claim that the full FPGA top has
closed physical memory bandwidth.

Implemented artifacts:

| Artifact | Role |
| --- | --- |
| `src/cpu_v01/fpga_compositor_arbiter.py` | Executable arbitration profile, demo, command inventory, and validator. |
| `tools/fpga_compositor_arbiter.py` | CLI for `--check`, `--json`, `--demo`, `--counters`, and `--plan`. |
| `rtl/cpu_v01_fpga_compositor_mem_arbiter.sv` | CPU-first single-outstanding memory arbiter RTL. |
| `rtl/cpu_v01_fpga_compositor_mem_arbiter_tb.sv` | Self-checking fixture for CPU writes, descriptor updates, scanout fetches, CPU faults, and stalls. |
| `tests/conformance/test_i36_s08_fpga_compositor_arbiter.py` | Story conformance tests for model, docs, CLI, RTL tokens, and Verilator lint. |

## Policy

The first policy is CPU-first and single-outstanding. When CPU and compositor
requests arrive in the same cycle, CPU data/MMIO wins and the compositor read
remains backpressured. CPU fault responses stay on the CPU response path and
memory errors on the compositor path are counted as video underflow events.

The compositor has deterministic visibility into pressure:

| Counter | Meaning |
| --- | --- |
| `cpu_grant_count` | CPU data/MMIO requests accepted by the arbiter. |
| `video_grant_count` | Compositor scanout reads accepted by the arbiter. |
| `video_starvation_count` | Cycles where scanout requested memory but could not be granted. |
| `video_underflow_count` | Bounded scanout stalls or memory errors visible as underflow evidence. |
| `descriptor_update_count` | Vblank descriptor update pulses observed while arbitration continues. |

Descriptor updates do not change the arbitration owner directly, but they are
counted so I36-S04 descriptor activity can be correlated with simultaneous CPU
writes, descriptor updates, and scanout fetches in simulation and board logs.

## RTL

`cpu_v01_fpga_compositor_mem_arbiter` accepts:

| Boundary | Signals |
| --- | --- |
| CPU request | `cpu_req_valid_i`, `cpu_req_ready_o`, `cpu_req_write_i`, `cpu_req_mmio_i`, `cpu_req_addr_i`, `cpu_req_wdata_i` |
| CPU response | `cpu_rsp_valid_o`, `cpu_rsp_data_o`, `cpu_rsp_fault_o` |
| Video request | `video_req_valid_i`, `video_req_ready_o`, `video_req_addr_i`, `video_req_len_cells_i` |
| Video response | `video_rsp_valid_o`, `video_rsp_data_o`, `video_rsp_error_o` |
| Shared memory | `mem_req_valid_o`, `mem_req_ready_i`, `mem_req_write_o`, `mem_req_addr_o`, `mem_req_wdata_o`, `mem_req_owner_o`, `mem_rsp_valid_i`, `mem_rsp_data_i`, `mem_rsp_error_i` |

The focused lint command is:

```text
verilator --lint-only --timing --top-module cpu_v01_fpga_compositor_mem_arbiter_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_fpga_compositor_mem_arbiter.sv rtl/cpu_v01_fpga_compositor_mem_arbiter_tb.sv
```

## Handoffs

- I36-S06 and I36-S07 consume `video_starvation_count` and
  `video_underflow_count` as evidence when classifying compositor board
  failures.
- Future top-level integration can insert the arbiter between I30-S02 decoder
  traffic and the I29-S02 DDR adapter without changing the I35-S04 visible
  register map.
- Later cache or DDR scheduler work may replace the CPU-first policy only with
  new ordering, fault, and underflow evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| A top-level arbitration contract schedules CPU data/MMIO and compositor scanout reads. | Met by the `cpu_v01_fpga_compositor_mem_arbiter` request owner policy and fixture boundary. |
| Deterministic priority or credit policy is documented. | Met by the CPU-first, single-outstanding policy. |
| CPU ordering and CPU fault responses are preserved. | Met by the CPU response owner path and focused fault test. |
| Starvation and underflow counters are exposed. | Met by `video_starvation_count` and `video_underflow_count`. |
| Focused simulation covers contention and descriptor activity. | Met by simultaneous CPU writes, descriptor updates, scanout fetches, CPU fault responses, and bounded video stall checks. |

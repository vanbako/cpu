# FPGA SoC Top Archive

Story: I30-S06

Status: Closure archive gate implemented; captured archive blocked

## Command

Validate the archive profile:

```text
python tools\fpga_soc_top_archive.py --check
```

Print a closure archive template:

```text
python tools\fpga_soc_top_archive.py --template
```

Audit a captured archive record:

```text
python tools\fpga_soc_top_archive.py --audit docs\implementation\evidence\i30_s06_soc_top_closure_archive.txt
```

Required upstream gates:

```text
python tools\fpga_soc_top_smoke.py --check
python tools\fpga_replay_mapper.py --check
python tools\fpga_debug_evidence.py --check
```

## Scope

I30-S06 archives the pre-board integration evidence for `cpu_v01_fpga_top`
after the I30-S05 Verilator smoke. It does not claim a Gowin build or physical
board pass. The archive is the handoff from the I30 closure sequence to I31-S01
first-pass board build preparation.

The expected evidence record is:

```text
docs/implementation/evidence/i30_s06_soc_top_closure_archive.txt
```

The default audit is `blocked` until that record exists. Once captured, the
record must link RTL sources, Verilator logs, decoded UART/status evidence or a
probe trace, replay mapping, debug evidence, remaining blocker disposition, and
retest commands.

## Required Record Fields

| Field | Requirement |
| --- | --- |
| `story` | Must be `I30-S06`. |
| `archived_at` | Local archive timestamp. |
| `repository_commit` | Repository commit used for the archive. |
| `top_module` | Must be `cpu_v01_fpga_top`. |
| `rtl_sources` | Must include `rtl/cpu_v01_core.sv`, `rtl/cpu_v01_fpga_top.sv`, and `rtl/cpu_v01_fpga_top_soc_smoke_tb.sv`. |
| `verilator_command` | Exact I30-S05 build command. |
| `verilator_build_log` | Captured Verilator build log path. |
| `smoke_run_command` | Exact I30-S05 executable command. |
| `smoke_run_log` | Captured smoke run log path. |
| `decoded_uart_trace` | Decoded UART output from the I30-S05 run. |
| `decoded_status_trace` | Decoded status/fault trace from the I30-S05 run. |
| `probe_trace` | Optional GAO/ILA/LED probe capture; `none` is allowed when UART/status traces are present. |
| `replay_mapping` | I25-S04 nearest replay mapping, pass/no-mismatch disposition, or command output. |
| `debug_evidence` | I25-S05 debug-evidence triage record. |
| `closure_result` | Must be `soc_top_closure_pass` for a passing archive. |
| `remaining_blockers` | `none`, or named blockers. |
| `filed_issues` | `none`, or issue IDs for remaining blockers. |
| `retest_commands` | Commands to rerun the validators, Verilator build, and smoke executable. |

## Evidence Links

The closure archive binds the following source and evidence surfaces:

- RTL sources from the I30-S05 smoke, including
  `rtl/cpu_v01_fpga_top.sv` and `rtl/cpu_v01_fpga_top_soc_smoke_tb.sv`.
- Verilator logs for the I30-S05 build and smoke executable.
- Decoded UART/status traces from the firmware-visible smoke path, with
  `probe_trace` available for optional GAO/ILA or LED evidence.
- `replay_mapping` output from `python tools\fpga_replay_mapper.py --check` or
  an I25-S04 replay command record.
- `debug_evidence` from `python tools\fpga_debug_evidence.py --check` or an
  I25-S05 triage record.

## Retest Commands

The archive must preserve commands sufficient to rerun the handoff:

```text
python tools\fpga_soc_top_smoke.py --check
verilator --binary --timing --Mdir obj_dir\soc_top_smoke --top-module cpu_v01_fpga_top_soc_smoke_tb rtl/cpu_v01_pkg.sv rtl/cpu_v01_core.sv rtl/cpu_v01_fpga_memories.sv rtl/cpu_v01_fpga_uart_mmio.sv rtl/cpu_v01_fpga_timer_mmio.sv rtl/cpu_v01_fpga_gpio_status.sv rtl/cpu_v01_fpga_top.sv rtl/cpu_v01_fpga_top_soc_smoke_tb.sv
obj_dir\soc_top_smoke\Vcpu_v01_fpga_top_soc_smoke_tb.exe
python tools\fpga_replay_mapper.py --check
python tools\fpga_debug_evidence.py --check
```

## Status Results

| Status | Meaning | Next action |
| --- | --- | --- |
| `archived` | A complete archive exists with `closure_result=soc_top_closure_pass`, concrete evidence links, no unresolved blockers, and retest commands. | I31-S01 may consume this as pre-board integration evidence. |
| `blocked` | No archive record exists yet. | Capture the I30-S05 logs and decoded traces before preparing the board build bundle. |
| `invalid` | Required fields or evidence links are missing or malformed. | Fix the key=value record and rerun the audit. |
| `needs_followup` | The archive exists, but closure result or blocker disposition is incomplete. | File or close blockers and preserve retest commands. |

## Handoff

I31-S01 consumes only an `archived` I30-S06 record. Physical board evidence
remains deferred to I31-S02 through I31-S05, where Gowin reports, bitstream
hashes, SRAM programming logs, LED/UART/probe observations, and replay
classification are captured.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Closure record links RTL sources. | Met by the required `rtl_sources` field and validator checks for the core, top, and smoke testbench. |
| Verilator build and run logs are required. | Met by `verilator_build_log`, `smoke_run_command`, and `smoke_run_log`. |
| Decoded UART/status or probe evidence is required. | Met by `decoded_uart_trace`, `decoded_status_trace`, and optional `probe_trace`. |
| Replay mapping is linked. | Met by the required `replay_mapping` field and I25-S04 gate dependency. |
| Debug evidence is linked. | Met by the required `debug_evidence` field and I25-S05 gate dependency. |
| Remaining blockers and retest commands are explicit. | Met by `remaining_blockers`, `filed_issues`, and `retest_commands`. |
| Downstream board-build handoff is explicit. | Met by the I31-S01 handoff rule. |

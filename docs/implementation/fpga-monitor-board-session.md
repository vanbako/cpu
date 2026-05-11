# FPGA Monitor Board Session

Story: I32-S06

Status: Evidence gate implemented; physical interactive board session blocked
until the FPGA run is captured.

Structured gate:

```text
python tools\fpga_monitor_board_session.py --check
```

Evidence template:

```text
python tools\fpga_monitor_board_session.py --template
```

Audit captured evidence:

```text
python tools\fpga_monitor_board_session.py --audit-evidence docs\implementation\evidence\i32_s06_monitor_board_session.txt
```

Required upstream gates:

```text
python tools\fpga_first_pass_archive.py --check
python tools\fpga_monitor_session.py --check
python tools\fpga_interactive_corpus.py --check
python tools\fpga_monitor_snapshot.py --check
```

## Purpose

I32-S06 is the physical evidence gate for an interactive multi-program board
session. It consumes the I32-S05 interactive corpus, the I32-S03 modeled
session shape, and the I32-S04 snapshot/replay handoff. It does not claim a
board run by default: the audit is `blocked` until a real session record is
captured after programming the Tang Mega Dock with 138K SOM.

## Evidence Path

```text
docs/implementation/evidence/i32_s06_monitor_board_session.txt
```

## Evidence Format

The record is a key/value file:

```text
story=I32-S06
captured_at=
repository_commit=
board=Sipeed Tang Mega Dock with 138K SOM
first_pass_archive=docs/implementation/evidence/i31_s05_first_cpu_pass_archive.txt
first_pass_archive_status=archived
monitor_transport=UART COMx 8N1 or JTAG monitor transport
bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
interactive_corpus=python tools\fpga_interactive_corpus.py --check
loaded_case_ids=scalar_control.call_return,trap_syscall.sys_pause_iret
program_run_count=2
loader_connect_log=docs/implementation/evidence/i32_s06_loader_connect.log
command_transcript=docs/implementation/evidence/i32_s06_monitor_commands.log
status_packet_hex=
uart_capture=docs/implementation/evidence/i32_s06_uart.log
snapshot_evidence=docs/implementation/evidence/i32_s06_snapshot.json
replay_command=python tools\fpga_monitor_snapshot.py --snapshot-json
pass_fail_result=multi_program_session_passed
residual_blockers=none
evidence_archive=docs/implementation/evidence/i32_s06_board_session
retest_steps=python tools\fpga_monitor_profile.py --check ; python tools\fpga_interactive_corpus.py --check
```

Required fields:

| Field | Required | Expected content |
| --- | --- | --- |
| `story` | Yes | `I32-S06`. |
| `captured_at` | Yes | Local capture timestamp. |
| `repository_commit` | Yes | Commit used for the board run. |
| `board` | Yes | `Sipeed Tang Mega Dock with 138K SOM`. |
| `first_pass_archive` | Yes | I31-S05 pass/blocker archive path. |
| `first_pass_archive_status` | Yes | `archived` or `needs_followup`. |
| `monitor_transport` | Yes | UART/JTAG transport, cable, and endpoint. |
| `bitstream_sha256` | Yes | 64-character SHA-256 digest. |
| `interactive_corpus` | Yes | I32-S05 corpus command or artifact. |
| `loaded_case_ids` | Yes | At least two I32-S05 case IDs loaded in order. |
| `program_run_count` | Yes | Count matching `loaded_case_ids`. |
| `loader_connect_log` | Yes | Monitor connect/HELLO transcript. |
| `command_transcript` | Yes | Full load/status/resume transcript. |
| `status_packet_hex` | Yes | Final or failure I25-S01 32-byte packet hex. |
| `uart_capture` | Yes | UART/status capture path. |
| `snapshot_evidence` | Yes | I32-S04-shaped debug snapshot captured for this session. |
| `replay_command` | Yes | Snapshot reproduction command or Verilator replay command. |
| `pass_fail_result` | Yes | `multi_program_session_passed` or `classified_board_session_blocker`. |
| `residual_blockers` | Yes | `none` for pass; named blockers for classified blocker. |
| `evidence_archive` | Yes | Directory or bundle with raw captures. |
| `retest_steps` | Yes | Concrete commands or physical steps to reproduce. |

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `accepted` | Evidence is complete, packet hex decodes, at least two I32-S05 cases were loaded, and pass/blocker disposition is consistent. | Use the evidence for I33-S01 release-candidate checklist input. |
| `needs_followup` | A classified blocker is missing residual blockers or replay/retest disposition. | File or close blockers before release-candidate use. |
| `invalid` | Evidence is malformed, incomplete, has bad hashes, unknown case IDs, or bad status-packet data. | Fix the record and rerun the audit. |
| `blocked` | No physical evidence file exists. | Keep I33-S01 blocked on board-session evidence. |

## Capture Checklist

1. Confirm I31-S05 has archived a first-pass result or classified blocker.
2. Start the monitor transport and save the connect/HELLO log.
3. Load and run at least two I32-S05 cases in one bounded session.
4. Save the full command transcript, UART/status capture, final packet hex,
   and I32-S04-shaped snapshot.
5. If the session blocks, record `classified_board_session_blocker`,
   `residual_blockers`, and a Verilator `replay_command`.
6. Record `evidence_archive` and concrete `retest_steps`.

## Handoff

I33-S01 consumes this accepted evidence as release-candidate input. I33-S02
uses `evidence_archive` and `retest_steps` when running the full regression and
artifact-capture gate. If the board session is classified as blocked, the
`replay_command` and `residual_blockers` become the next debug work queue.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Loader connect evidence is captured. | Met by required `loader_connect_log` and `monitor_transport`. |
| At least two bounded images are loaded and run. | Met by `loaded_case_ids` and `program_run_count` audit rules. |
| Pass/fail/status capture is preserved. | Met by required `status_packet_hex`, `uart_capture`, and decoded I25-S01 packet validation. |
| Snapshot or replay handoff exists. | Met by `snapshot_evidence` and `replay_command`. |
| Residual blockers and retest steps are explicit. | Met by `residual_blockers`, `evidence_archive`, and `retest_steps`. |

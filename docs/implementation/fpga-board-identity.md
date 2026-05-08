# FPGA Board Identity

Story: I24-S01

Status: Evidence gate implemented; physical identity capture blocked

Structured gate:

```text
python tools\fpga_board_identity.py --check
```

Evidence template:

```text
python tools\fpga_board_identity.py --template
```

Audit captured evidence:

```text
python tools\fpga_board_identity.py --audit-evidence docs\implementation\evidence\i24_s01_device_identity.txt
```

## Purpose

I24-S01 removes the first hard blocker from the Tang Mega 138K FPGA path:
before creating the CST overlay or running Gowin against a real board, the
physical SOM must confirm the device, package, and Gowin Device Version.

The current first-test target remains `Sipeed Tang Mega 138K Dock` with assumed
device `GW5AST-LV138PG484A`, package `PBG484A`, and Device Version `B/C,
verify on board or JTAG scan`. Public Tang Mega 138K sources also mention
`GW5AST-LV138FPG676A` and `FPG676A`, so the build must stay blocked until board
marking or programmer scan evidence resolves that ambiguity.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| `src/cpu_v01/fpga_board_identity.py` | Structured I24-S01 expected identity, evidence parser, audit rules, blocker state, and validator. |
| `tools/fpga_board_identity.py` | CLI wrapper for checking the profile, printing JSON, printing the evidence template, and auditing captured evidence. |
| `tests/conformance/test_i24_s01_fpga_board_identity.py` | Conformance tests for target assumptions, evidence fields, parser/audit behavior, CLI output, and documentation. |
| `docs/implementation/fpga-board-identity.md` | This implementation note. |

## Expected Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega 138K Dock` |
| Assumed device | `GW5AST-LV138PG484A` |
| Assumed package | `PBG484A` |
| Assumed Device Version | `B/C, verify on board or JTAG scan` |
| Evidence path | `docs/implementation/evidence/i24_s01_device_identity.txt` |

## Evidence Format

The captured evidence record is a small key/value file:

```text
story=I24-S01
board=Sipeed Tang Mega 138K Dock
source=
observed_device=
observed_package=
observed_device_version=
observed_tool=
observed_at=
evidence_notes=
```

Required fields:

| Field | Required | Expected content |
| --- | --- | --- |
| `story` | Yes | `I24-S01`. |
| `board` | Yes | `Sipeed Tang Mega 138K Dock`. |
| `source` | Yes | `board_marking`, `programmer_jtag_scan`, or both. |
| `observed_device` | Yes | The FPGA device from the marking or scan, such as `GW5AST-LV138PG484A`. |
| `observed_package` | Yes | The package from the marking or scan, such as `PBG484A`. |
| `observed_device_version` | Yes | Gowin Device Version selected for the build, normally `B` or `C`. |
| `observed_tool` | Yes | Tool or method used, such as `Gowin Programmer` or board marking inspection. |
| `observed_at` | Yes | Local date/time of capture. |
| `evidence_notes` | No | Serial number, screenshot path, photo path, or raw command output path. |

## Capture Procedure

1. Inspect the SOM marking and record the exact printed device/package. Use
   `source=board_marking` if this is the only evidence source.
2. Run a Gowin Programmer device scan and record the displayed device, package,
   and Device Version. Use `source=programmer_jtag_scan`.
3. Optionally run `openFPGALoader --detect` as an independent visibility check
   when the tool and cable support it.
4. Save the record at
   `docs/implementation/evidence/i24_s01_device_identity.txt`.
5. Run `python tools\fpga_board_identity.py --audit-evidence`.

## Audit Rules

| Audit result | Meaning | Next action |
| --- | --- | --- |
| `confirmed` | Evidence matches `GW5AST-LV138PG484A` and `PBG484A`. | Use the record as the I24-S02 CST/SDC target basis and carry it into the Gowin report bundle. |
| `target_mismatch` | Evidence reports a different device or package, especially `GW5AST-LV138FPG676A` or `FPG676A`. | Update `src/cpu_v01/fpga_first_test.py`, the FPGA docs, and the synthesis gate before CST work. |
| `invalid` | Evidence is malformed or missing required fields. | Recapture or fix the key/value record and rerun the audit. |
| `blocked` | No evidence file exists yet. | Keep I24-S02 blocked and do not lock board constraints. |

## Current Blocker

- No physical Tang Mega 138K board marking has been captured in this repository.
- No Gowin Programmer or JTAG scan evidence has been captured in this
  repository.
- I24-S02 CST work must remain blocked until `confirmed` identity evidence
  exists, or until the target profile is deliberately updated for an observed
  `FPG676A` board.

I24-S02 is tracked in `docs/implementation/fpga-constraints-overlay.md` and
checked with `python tools\fpga_constraints_overlay.py --check`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Board identity fields are explicit. | Met by the evidence format and required-field audit. |
| Package ambiguity is handled. | Met by the `target_mismatch` path for `GW5AST-LV138FPG676A`/`FPG676A`. |
| Build settings are protected from stale assumptions. | Met by the blocker on I24-S02 until the audit is `confirmed` or the target profile is updated. |
| Physical execution is not claimed without evidence. | Met by the default `blocked` audit when the evidence file is absent. |

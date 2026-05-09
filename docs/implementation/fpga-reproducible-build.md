# FPGA Reproducible Build

Story: I28-S05

Structured gate:

```text
python tools\fpga_reproducible_build.py --check
```

Related gates:

```text
python tools\fpga_reset_cdc.py --check
python tools\fpga_gowin_reports.py --check
python tools\fpga_frequency_margin.py --check
```

Manifest template:

```text
python tools\fpga_reproducible_build.py --template
```

## Scope

I28-S05 publishes the reproducible FPGA build profile. It does not claim a
physical board pass. The profile lists the exact tool version fields,
device/package evidence, constraints, Gowin Tcl, reports, bitstream_sha256,
clock/reset/timing gates, and board evidence links that must be captured before
another machine can reproduce the build.

The current profile status is `documented_blocker` because identity, final
constraints, Gowin reports, bitstream identity, programming logs, and I24-S05
board evidence are not present.

## Target

| Field | Value |
| --- | --- |
| Board | `Sipeed Tang Mega 138K Dock` |
| Device | `GW5AST-LV138PG484A` |
| Package | `PBG484A` |
| Top module | `cpu_v01_fpga_top` |
| Build root | `build/fpga/tang_mega_138k/first_test` |
| Selected clock profile | `debug_direct_25mhz` |
| Debug default | 25 MHz |
| Release default | 25 MHz |

## Required Artifacts

| Artifact | Path | Gate |
| --- | --- | --- |
| `device_package_evidence` | `docs/implementation/evidence/i24_s01_device_identity.txt` | `python tools\fpga_board_identity.py --check` |
| `constraints_cst_sdc` | `constraints/tang_mega_138k_first_test.cst` and `constraints/tang_mega_138k_first_test.sdc` | `python tools\fpga_constraints_overlay.py --check` |
| `gowin_tcl` | `build/fpga/tang_mega_138k/first_test/run_gowin.tcl` | `python tools\fpga_synthesis_gate.py --check` |
| `gowin_reports` | `build/fpga/tang_mega_138k/first_test/impl` | `python tools\fpga_gowin_reports.py --check` |
| `bitstream_identity` | `build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs` | `python tools\fpga_gowin_reports.py --check` |
| `clock_profile` | `docs/implementation/fpga-clock-profiles.md` | `python tools\fpga_clock_profiles.py --check` |
| `reset_cdc_audit` | `docs/implementation/fpga-reset-cdc-audit.md` | `python tools\fpga_reset_cdc.py --check` |
| `frequency_margin` | `docs/implementation/evidence/i28_s04_frequency_sweep.json` | `python tools\fpga_frequency_margin.py --check` |
| `board_evidence` | `docs/implementation/evidence/i24_s05_first_board_archive.txt` | `python tools\fpga_first_board_archive.py --check` |

## Tool Version Fields

The manifest requires tool version evidence for:

- Gowin EDA command shell (`gw_sh`);
- Gowin Programmer;
- Verilator;
- Python and the repository commit.

The manifest also records `bitstream_sha256`, selected clock profile, report
bundle path, reset/CDC audit, frequency-margin summary, and board evidence
path.

## Reproduction Steps

1. Confirm I24-S01 device/package evidence.
2. Confirm I24-S02 constraints evidence and generate the final CST from
   verified pins.
3. Run `python tools\fpga_synthesis_gate.py --gowin-tcl` and archive the
   generated Tcl.
4. Run `gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl`.
5. Run
   `python tools\fpga_gowin_reports.py --audit-reports build\fpga\tang_mega_138k\first_test`.
6. Record bitstream SHA-256, selected clock profile, reset/CDC audit, and
   frequency margin summary.
7. Link board programming and first-board evidence before claiming
   reproducibility.

## Current Blockers

- I24-S01 identity evidence is not captured.
- I24-S02 final CST from verified pins is not captured.
- Gowin reports and bitstream are not present under the build root.
- I24-S04/I24-S05 board programming and evidence archive are not complete.

I29 external-memory stories must not treat FPGA timing as stable until this
profile has real reports, bitstream identity, and board evidence.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Tool version fields are listed. | Met by the manifest template and tool table. |
| Device/package evidence is required. | Met by `device_package_evidence`. |
| Constraints and Tcl are required. | Met by `constraints_cst_sdc` and `gowin_tcl`. |
| Reports and bitstream hash are required. | Met by `gowin_reports` and `bitstream_identity`. |
| Board evidence is required. | Met by `board_evidence` and I24-S05 handoff. |
| Reproducibility remains blocked until evidence exists. | Met by `documented_blocker` status. |

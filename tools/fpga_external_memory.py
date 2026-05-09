#!/usr/bin/env python3
"""Validate and print the I29-S01 FPGA external-memory boundary profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the external-memory profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--windows", action="store_true", help="list external memory windows")
    parser.add_argument("--signals", action="store_true", help="list controller boundary signals")
    parser.add_argument("--status", action="store_true", help="list calibration status fields")
    parser.add_argument("--faults", action="store_true", help="list CPU-owned fault rules")
    args = parser.parse_args(argv)

    profile = fpga_external_memory.fpga_external_memory_profile()

    if args.json:
        print(fpga_external_memory.fpga_external_memory_json())
        return 0

    if args.windows:
        for window in profile.memory_windows:
            print(
                f"{window.name}\t0x{window.base_cell:08X}\t"
                f"0x{window.end_cell:08X}\t{window.memory_type_name}"
            )
        return 0

    if args.signals:
        for signal in profile.controller_signals:
            print(f"{signal.name}\t{signal.direction}\t{signal.width}\t{signal.owner}")
        return 0

    if args.status:
        for field in profile.calibration_status:
            print(f"{field.name}\t{field.access}\t{field.width_bits}\t{field.reset_value}")
        return 0

    if args.faults:
        for rule in profile.fault_rules:
            print(f"{rule.name}\t{rule.owner}\t{rule.architectural_result}")
        return 0

    issues = fpga_external_memory.validate_fpga_external_memory(ROOT)
    if issues:
        print("FPGA external memory issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA external memory issues: 0")
        return 0

    print(fpga_external_memory.render_fpga_external_memory())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

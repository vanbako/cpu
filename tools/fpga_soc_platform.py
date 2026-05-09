#!/usr/bin/env python3
"""Validate and print the I27-S01 FPGA SoC platform profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_platform


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA SoC profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--list", action="store_true", help="list peripherals and base addresses")
    parser.add_argument("--registers", metavar="PERIPHERAL", help="list registers for one peripheral")
    args = parser.parse_args(argv)

    profile = fpga_soc_platform.fpga_soc_platform_profile()

    if args.list:
        for peripheral in profile.peripherals:
            print(f"{peripheral.name}\t0x{peripheral.base_cell:08X}\t0x{peripheral.size_cells:X}\t{peripheral.owner_story}")
        return 0

    if args.registers:
        try:
            peripheral = profile.peripheral_by_name(args.registers)
        except KeyError:
            print(f"unknown FPGA SoC peripheral: {args.registers}")
            return 1
        for register in peripheral.registers:
            print(f"{register.name}\t0x{peripheral.base_cell + register.offset_cell:08X}\t{register.access}\t{register.width_bits}")
        return 0

    if args.json:
        print(fpga_soc_platform.fpga_soc_platform_json())
        return 0

    issues = fpga_soc_platform.validate_fpga_soc_platform(ROOT)
    if issues:
        print("FPGA SoC platform issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC platform issues: 0")
        return 0

    print(fpga_soc_platform.render_fpga_soc_platform())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and print the I23-S02 FPGA top wrapper projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_top


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate FPGA top wrapper RTL and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA top wrapper port projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_top.fpga_top_ports_json())
        return 0

    issues = fpga_top.validate_fpga_top_wrapper(ROOT)
    if issues:
        print("FPGA top wrapper issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA top wrapper issues: 0")
        return 0

    print("FPGA top wrapper ports:")
    for port in fpga_top.fpga_top_ports():
        print(f"- {port.name}: {port.direction} {port.width} ({port.group})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and print the I23-S04 FPGA smoke firmware observation profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate FPGA smoke firmware RTL and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA smoke observation profile as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_smoke.fpga_smoke_observations_json())
        return 0

    issues = fpga_smoke.validate_fpga_smoke_firmware(ROOT)
    if issues:
        print("FPGA smoke firmware issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA smoke firmware issues: 0")
        return 0

    print("FPGA smoke observations:")
    for observation in fpga_smoke.fpga_smoke_observations():
        print(f"- {observation.name}: {observation.pass_role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

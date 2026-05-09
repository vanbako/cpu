#!/usr/bin/env python3
"""Validate and print the I28-S02 FPGA reset/CDC audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_reset_cdc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the reset/CDC audit")
    parser.add_argument("--json", action="store_true", help="print the reset/CDC audit as JSON")
    parser.add_argument("--plan", action="store_true", help="print the reset/CDC command plan")
    parser.add_argument("--items", action="store_true", help="list audited reset/CDC items")
    parser.add_argument("--open-issues", action="store_true", help="list reset/CDC open issues")
    args = parser.parse_args(argv)

    profile = fpga_reset_cdc.fpga_reset_cdc_profile()

    if args.json:
        print(fpga_reset_cdc.fpga_reset_cdc_json())
        return 0

    if args.plan:
        for command in fpga_reset_cdc.fpga_reset_cdc_command_plan():
            print(command)
        return 0

    if args.items:
        for item in profile.items:
            print(f"{item.name}\t{item.kind}\t{item.clock_domain}\t{item.status}")
        return 0

    if args.open_issues:
        for issue in profile.open_issues:
            print(issue)
        return 0

    issues = fpga_reset_cdc.validate_fpga_reset_cdc(ROOT)
    if issues:
        print("FPGA reset/CDC issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA reset/CDC issues: 0")
        return 0

    print(fpga_reset_cdc.render_fpga_reset_cdc())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

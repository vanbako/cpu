#!/usr/bin/env python3
"""Validate and print the I23-S06 FPGA board bring-up runbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_bringup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the FPGA board bring-up runbook and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA board bring-up runbook as JSON",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="print the board bring-up command plan",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_bringup.fpga_board_bringup_runbook_json())
        return 0

    if args.plan:
        for command in fpga_bringup.fpga_bringup_command_plan():
            print(command)
        return 0

    issues = fpga_bringup.validate_fpga_board_bringup(ROOT)
    if issues:
        print("FPGA board bring-up issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA board bring-up issues: 0")
        return 0

    print(fpga_bringup.render_fpga_bringup_runbook())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

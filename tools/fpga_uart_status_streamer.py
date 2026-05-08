#!/usr/bin/env python3
"""Validate and print the I25-S02 FPGA UART status streamer profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_uart_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the UART status streamer")
    parser.add_argument("--json", action="store_true", help="print the UART status profile as JSON")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command plan")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_uart_status.fpga_uart_status_json())
        return 0

    if args.plan:
        for command in fpga_uart_status.fpga_uart_status_command_plan():
            print(command)
        return 0

    issues = fpga_uart_status.validate_fpga_uart_status(ROOT)
    if issues:
        print("FPGA UART status streamer issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA UART status streamer issues: 0")
        return 0

    print(fpga_uart_status.render_fpga_uart_status_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

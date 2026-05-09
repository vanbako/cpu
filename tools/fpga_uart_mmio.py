#!/usr/bin/env python3
"""Validate and print the I27-S02 FPGA UART MMIO profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_uart_mmio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA UART MMIO profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--registers", action="store_true", help="list UART MMIO registers")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    parser.add_argument("--demo", action="store_true", help="print a small state-machine demo as JSON")
    args = parser.parse_args(argv)

    profile = fpga_uart_mmio.fpga_uart_mmio_profile()

    if args.registers:
        for register in profile.registers:
            print(
                f"{register.name}\t0x{register.absolute_cell:08X}\t"
                f"{register.access}\t{register.width_bits}"
            )
        return 0

    if args.plan:
        for command in fpga_uart_mmio.fpga_uart_mmio_verilator_commands():
            print(command)
        return 0

    if args.demo:
        state = fpga_uart_mmio.fpga_uart_mmio_state()
        state.write_register(fpga_uart_mmio.UART_TXDATA, 0x41)
        state.receive_byte(0x52)
        print(json.dumps(state.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_uart_mmio.fpga_uart_mmio_json())
        return 0

    issues = fpga_uart_mmio.validate_fpga_uart_mmio(ROOT)
    if issues:
        print("FPGA UART MMIO issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA UART MMIO issues: 0")
        return 0

    print(fpga_uart_mmio.render_fpga_uart_mmio())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

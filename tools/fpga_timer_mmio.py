#!/usr/bin/env python3
"""Validate and print the I27-S03 FPGA timer MMIO profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_timer_mmio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA timer MMIO profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--registers", action="store_true", help="list timer MMIO registers")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    parser.add_argument("--demo", action="store_true", help="print a timer compare demo as JSON")
    args = parser.parse_args(argv)

    profile = fpga_timer_mmio.fpga_timer_mmio_profile()

    if args.registers:
        for register in profile.registers:
            print(
                f"{register.name}\t0x{register.absolute_cell:08X}\t"
                f"{register.access}\t{register.width_bits}\t{register.cells}"
            )
        return 0

    if args.plan:
        for command in fpga_timer_mmio.fpga_timer_mmio_verilator_commands():
            print(command)
        return 0

    if args.demo:
        state = fpga_timer_mmio.fpga_timer_mmio_state()
        state.write_register(fpga_timer_mmio.TIMER_COMPARE, 3)
        state.write_register(
            fpga_timer_mmio.TIMER_CONTROL,
            fpga_timer_mmio.CONTROL_ENABLE | fpga_timer_mmio.CONTROL_IRQ_ENABLE,
        )
        state.tick(3)
        print(json.dumps(state.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_timer_mmio.fpga_timer_mmio_json())
        return 0

    issues = fpga_timer_mmio.validate_fpga_timer_mmio(ROOT)
    if issues:
        print("FPGA timer MMIO issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA timer MMIO issues: 0")
        return 0

    print(fpga_timer_mmio.render_fpga_timer_mmio())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

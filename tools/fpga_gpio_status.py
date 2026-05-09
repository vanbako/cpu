#!/usr/bin/env python3
"""Validate and print the I27-S04 FPGA GPIO/status MMIO profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gpio_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA GPIO/status profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--registers", action="store_true", help="list GPIO/status registers")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    parser.add_argument("--demo", action="store_true", help="print a GPIO/status demo as JSON")
    args = parser.parse_args(argv)

    profile = fpga_gpio_status.fpga_gpio_status_profile()

    if args.registers:
        for register in profile.registers:
            print(
                f"{register.name}\t0x{register.absolute_cell:08X}\t"
                f"{register.access}\t{register.width_bits}"
            )
        return 0

    if args.plan:
        for command in fpga_gpio_status.fpga_gpio_status_verilator_commands():
            print(command)
        return 0

    if args.demo:
        state = fpga_gpio_status.fpga_gpio_status_state()
        state.write_register(fpga_gpio_status.GPIO_DIR, 0x00FF)
        state.write_register(fpga_gpio_status.GPIO_OUT, 0xA5A5)
        state.write_register(
            fpga_gpio_status.STATUS_LEDS,
            fpga_gpio_status.STATUS_LED_PASS | fpga_gpio_status.STATUS_LED_HEARTBEAT,
        )
        state.set_gpio_inputs(0x1234)
        print(json.dumps(state.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_gpio_status.fpga_gpio_status_json())
        return 0

    issues = fpga_gpio_status.validate_fpga_gpio_status(ROOT)
    if issues:
        print("FPGA GPIO/status issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA GPIO/status issues: 0")
        return 0

    print(fpga_gpio_status.render_fpga_gpio_status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

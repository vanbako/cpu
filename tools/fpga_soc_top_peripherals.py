#!/usr/bin/env python3
"""Validate and print the I30-S03 FPGA SoC top peripheral handoff contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_peripherals


def _parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the peripheral handoffs")
    parser.add_argument("--json", action="store_true", help="print the handoff profile as JSON")
    parser.add_argument("--handoffs", action="store_true", help="list top-level handoffs")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command")
    parser.add_argument("--demo", action="store_true", help="evaluate the executable handoff demo")
    parser.add_argument("--irq-pending-enabled", type=_parse_int, default=0x0009)
    args = parser.parse_args(argv)

    profile = fpga_soc_top_peripherals.fpga_soc_top_peripherals_profile()

    if args.handoffs:
        for handoff in profile.handoffs:
            print(f"{handoff.name}\t{handoff.source}\t{handoff.destination}")
        return 0

    if args.plan:
        print(profile.verilator_command)
        return 0

    if args.demo:
        result = fpga_soc_top_peripherals.evaluate_soc_top_peripherals(
            uart_mmio_tx=False,
            status_uart_tx=True,
            timer_compare_irq=True,
            irq_pending_enabled=args.irq_pending_enabled,
            gpio_pass_led=True,
            gpio_heartbeat_led=True,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_soc_top_peripherals.fpga_soc_top_peripherals_json())
        return 0

    issues = fpga_soc_top_peripherals.validate_fpga_soc_top_peripherals(ROOT)
    if issues:
        print("FPGA SoC top peripheral handoff issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC top peripheral handoff issues: 0")
        return 0

    print(fpga_soc_top_peripherals.render_fpga_soc_top_peripherals())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

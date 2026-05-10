#!/usr/bin/env python3
"""Validate and print the I30-S04 FPGA SoC loader handoff contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_loader_handoff


def _parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the loader handoff")
    parser.add_argument("--json", action="store_true", help="print the loader handoff profile")
    parser.add_argument("--rules", action="store_true", help="list handoff rules")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command")
    parser.add_argument("--decode", type=_parse_int, metavar="CELL_ADDR", help="evaluate one loader address")
    parser.add_argument("--tag", action="store_true", help="treat --decode as tag-bearing traffic")
    parser.add_argument("--non-write", action="store_true", help="treat --decode as malformed non-write traffic")
    parser.add_argument("--loader-uart-low", action="store_true", help="drive the loader UART leg low")
    args = parser.parse_args(argv)

    profile = fpga_soc_loader_handoff.fpga_soc_loader_handoff_profile()

    if args.rules:
        for rule in profile.rules:
            print(f"{rule.name}\t{rule.policy}")
        return 0

    if args.plan:
        print(profile.verilator_command)
        return 0

    if args.decode is not None:
        result = fpga_soc_loader_handoff.evaluate_soc_loader_handoff(
            args.decode,
            write=not args.non_write,
            tag=args.tag,
            loader_uart_tx=not args.loader_uart_low,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_soc_loader_handoff.fpga_soc_loader_handoff_json())
        return 0

    issues = fpga_soc_loader_handoff.validate_fpga_soc_loader_handoff(ROOT)
    if issues:
        print("FPGA SoC loader handoff issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC loader handoff issues: 0")
        return 0

    print(fpga_soc_loader_handoff.render_fpga_soc_loader_handoff())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

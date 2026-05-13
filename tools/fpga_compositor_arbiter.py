#!/usr/bin/env python3
"""Validate and print the I36-S08 FPGA compositor memory arbiter profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_arbiter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor arbiter profile")
    parser.add_argument("--json", action="store_true", help="print the arbiter profile as JSON")
    parser.add_argument("--demo", action="store_true", help="print the arbitration demo as JSON")
    parser.add_argument("--counters", action="store_true", help="list visible counters")
    parser.add_argument("--plan", action="store_true", help="print Verilator command inventory")
    args = parser.parse_args(argv)

    profile = fpga_compositor_arbiter.fpga_compositor_arbiter_profile()

    if args.json:
        print(fpga_compositor_arbiter.fpga_compositor_arbiter_json())
        return 0

    if args.demo:
        print(fpga_compositor_arbiter.fpga_compositor_arbiter_demo_json())
        return 0

    if args.counters:
        for counter in profile.counters:
            print(counter)
        return 0

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    issues = fpga_compositor_arbiter.validate_fpga_compositor_arbiter(ROOT)
    if issues:
        print("FPGA compositor arbiter issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor arbiter issues: 0")
        return 0

    print(fpga_compositor_arbiter.render_fpga_compositor_arbiter(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

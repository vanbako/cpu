#!/usr/bin/env python3
"""Validate and print the I29-S02 FPGA DDR wrapper profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_ddr_wrapper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the DDR wrapper profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--signals", action="store_true", help="list visibility signals")
    parser.add_argument("--rules", action="store_true", help="list calibration gate rules")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    parser.add_argument("--blockers", action="store_true", help="print remaining integration blockers")
    args = parser.parse_args(argv)

    profile = fpga_ddr_wrapper.fpga_ddr_wrapper_profile()

    if args.json:
        print(fpga_ddr_wrapper.fpga_ddr_wrapper_json())
        return 0

    if args.signals:
        for signal in profile.visibility_signals:
            print(f"{signal.name}\t{signal.width}\t{signal.source}")
        return 0

    if args.rules:
        for rule in profile.gate_rules:
            print(f"{rule.name}\t{rule.condition}\t{rule.behavior}")
        return 0

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    if args.blockers:
        for blocker in profile.integration_blockers:
            print(blocker)
        return 0

    issues = fpga_ddr_wrapper.validate_fpga_ddr_wrapper(ROOT)
    if issues:
        print("FPGA DDR wrapper issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA DDR wrapper issues: 0")
        return 0

    print(fpga_ddr_wrapper.render_fpga_ddr_wrapper())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

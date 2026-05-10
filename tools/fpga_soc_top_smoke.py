#!/usr/bin/env python3
"""Validate and print the I30-S05 FPGA SoC top-level smoke contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the top-level smoke contract")
    parser.add_argument("--json", action="store_true", help="print the smoke profile as JSON")
    parser.add_argument("--run", action="store_true", help="print the expected smoke run as JSON")
    parser.add_argument("--steps", action="store_true", help="list smoke steps")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command")
    args = parser.parse_args(argv)

    profile = fpga_soc_top_smoke.fpga_soc_top_smoke_profile()

    if args.steps:
        for step in profile.steps:
            print(f"{step.name}\t{step.fixture}\t{step.acceptance}")
        return 0

    if args.plan:
        print(profile.verilator_command)
        return 0

    if args.run:
        print(fpga_soc_top_smoke.fpga_soc_top_smoke_run_json())
        return 0

    if args.json:
        print(fpga_soc_top_smoke.fpga_soc_top_smoke_json())
        return 0

    issues = fpga_soc_top_smoke.validate_fpga_soc_top_smoke(ROOT)
    if issues:
        print("FPGA SoC top smoke issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC top smoke issues: 0")
        return 0

    print(fpga_soc_top_smoke.render_fpga_soc_top_smoke())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

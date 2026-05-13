#!/usr/bin/env python3
"""Validate and print the I36-S05 FPGA compositor demo fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor demo profile")
    parser.add_argument("--json", action="store_true", help="print the compositor demo profile as JSON")
    parser.add_argument("--run", action="store_true", help="run the default compositor demos as JSON")
    parser.add_argument("--cases", action="store_true", help="list compositor demo cases")
    parser.add_argument("--plan", action="store_true", help="print the command vocabulary")
    args = parser.parse_args(argv)

    profile = fpga_compositor_demo.fpga_compositor_demo_profile()

    if args.json:
        print(fpga_compositor_demo.fpga_compositor_demo_json())
        return 0

    if args.run:
        print(fpga_compositor_demo.fpga_compositor_demo_run_json())
        return 0

    if args.cases:
        for case in profile.cases:
            print(f"{case.case_id}\t{case.actor}\t{case.program_id}\t{len(case.phases)}")
        return 0

    if args.plan:
        for command in profile.command_vocabulary:
            print(command)
        return 0

    issues = fpga_compositor_demo.validate_fpga_compositor_demo(ROOT)
    if issues:
        print("FPGA compositor demo issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor demo issues: 0")
        return 0

    print(fpga_compositor_demo.render_fpga_compositor_demo(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

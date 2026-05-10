#!/usr/bin/env python3
"""Validate and print the I30-S01 FPGA SoC top-level closure plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_closure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the closure plan")
    parser.add_argument("--json", action="store_true", help="print the closure profile as JSON")
    parser.add_argument("--matrix", action="store_true", help="list shortcut closure rows")
    parser.add_argument("--sequence", action="store_true", help="list ordered I30 closure steps")
    parser.add_argument("--shortcut", metavar="SHORTCUT_ID", help="print one shortcut row as JSON")
    args = parser.parse_args(argv)

    profile = fpga_soc_top_closure.fpga_soc_top_closure_profile()

    if args.matrix:
        for shortcut in profile.shortcuts:
            print(
                f"{shortcut.shortcut_id}\t{shortcut.owner_story}\t"
                f"{shortcut.testbench}\t{shortcut.validator}"
            )
        return 0

    if args.sequence:
        for step in profile.sequence:
            print(step)
        return 0

    if args.shortcut:
        try:
            shortcut = profile.shortcut_by_id(args.shortcut)
        except KeyError:
            print(f"unknown FPGA SoC top closure shortcut: {args.shortcut}")
            return 1
        print(json.dumps(shortcut.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_soc_top_closure.fpga_soc_top_closure_json())
        return 0

    issues = fpga_soc_top_closure.validate_fpga_soc_top_closure(ROOT)
    if issues:
        print("FPGA SoC top closure issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC top closure issues: 0")
        return 0

    print(fpga_soc_top_closure.render_fpga_soc_top_closure())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

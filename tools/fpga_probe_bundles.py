#!/usr/bin/env python3
"""Validate and print the I25-S03 FPGA probe bundle profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_probe_bundles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the probe bundle profile")
    parser.add_argument("--json", action="store_true", help="print the probe bundle profile as JSON")
    parser.add_argument("--list", action="store_true", help="print a CSV probe list for GAO/ILA setup")
    parser.add_argument("--plan", action="store_true", help="print the dependent check command plan")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_probe_bundles.fpga_probe_bundle_json())
        return 0

    if args.list:
        print(fpga_probe_bundles.render_probe_list())
        return 0

    if args.plan:
        for command in fpga_probe_bundles.fpga_probe_bundle_command_plan():
            print(command)
        return 0

    issues = fpga_probe_bundles.validate_fpga_probe_bundles(ROOT)
    if issues:
        print("FPGA probe bundle issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA probe bundle issues: 0")
        return 0

    print(fpga_probe_bundles.render_fpga_probe_bundle_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

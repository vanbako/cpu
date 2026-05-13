#!/usr/bin/env python3
"""Validate and print the I36-S02 FPGA compositor single-plane fetch profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor fetch profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--demo", action="store_true", help="print a complete RGB565 demo fetch")
    parser.add_argument("--underflow-demo", action="store_true", help="print an underflow demo fetch")
    parser.add_argument("--signals", action="store_true", help="list read-master signals")
    parser.add_argument("--plan", action="store_true", help="print Verilator command inventory")
    args = parser.parse_args(argv)

    profile = fpga_compositor_fetch.fpga_compositor_fetch_profile()

    if args.demo:
        print(json.dumps(fpga_compositor_fetch.demo_fetch_line().as_dict(), indent=2, sort_keys=True))
        return 0

    if args.underflow_demo:
        print(json.dumps(fpga_compositor_fetch.demo_underflow_line().as_dict(), indent=2, sort_keys=True))
        return 0

    if args.signals:
        for signal in profile.read_master_signals:
            print(signal)
        return 0

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    if args.json:
        print(fpga_compositor_fetch.fpga_compositor_fetch_json())
        return 0

    issues = fpga_compositor_fetch.validate_fpga_compositor_fetch(ROOT)
    if issues:
        print("FPGA compositor fetch issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor fetch issues: 0")
        return 0

    print(fpga_compositor_fetch.render_fpga_compositor_fetch())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

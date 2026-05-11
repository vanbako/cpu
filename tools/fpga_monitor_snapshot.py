#!/usr/bin/env python3
"""Validate and print the I32-S04 FPGA monitor debug snapshot profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the monitor snapshot profile")
    parser.add_argument("--json", action="store_true", help="print the monitor snapshot profile as JSON")
    parser.add_argument("--snapshot", action="store_true", help="capture the modeled snapshot as JSON")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_monitor_snapshot.fpga_monitor_snapshot_json())
        return 0

    if args.snapshot:
        print(fpga_monitor_snapshot.fpga_monitor_debug_snapshot_json())
        return 0

    issues = fpga_monitor_snapshot.validate_fpga_monitor_snapshot(ROOT)
    if issues:
        print("FPGA monitor snapshot issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA monitor snapshot issues: 0")
        return 0

    print(fpga_monitor_snapshot.render_fpga_monitor_snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

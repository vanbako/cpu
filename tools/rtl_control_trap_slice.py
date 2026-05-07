#!/usr/bin/env python3
"""Validate and print the I21-S04 RTL control/trap coverage projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_control_trap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL control/trap sources and coverage projection",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the control/trap coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_control_trap.control_trap_projection_json())
        return 0

    issues = rtl_control_trap.validate_rtl_control_trap_slice(ROOT)
    if issues:
        print("RTL control/trap slice issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL control/trap slice issues: 0")
        return 0

    print("RTL control/trap slice cases:")
    for row in rtl_control_trap.control_trap_coverage_rows():
        print(f"- {row.case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

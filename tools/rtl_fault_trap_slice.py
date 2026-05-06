#!/usr/bin/env python3
"""Validate and print the I20-S07 RTL fault/trap golden projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_fault_trap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL fault/trap sources and golden projections",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the projected fault/trap retire packets as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_fault_trap.fault_trap_projection_json())
        return 0

    issues = rtl_fault_trap.validate_rtl_fault_trap_slice(ROOT)
    if issues:
        print("RTL fault/trap slice issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL fault/trap slice issues: 0")
        return 0

    print("RTL fault/trap slice cases:")
    for case_id in rtl_fault_trap.fault_trap_slice_case_ids():
        print(f"- {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

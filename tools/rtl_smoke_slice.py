#!/usr/bin/env python3
"""Validate and print the I20-S05 RTL smoke-slice golden projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL smoke sources and golden projections",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the projected first-slice retire packets as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_smoke.smoke_slice_projection_json())
        return 0

    issues = rtl_smoke.validate_rtl_smoke_slice(ROOT)
    if issues:
        print("RTL smoke slice issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL smoke slice issues: 0")
        return 0

    print("RTL smoke slice cases:")
    for case_id in rtl_smoke.smoke_slice_case_ids():
        print(f"- {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and print the I21-S01 RTL scalar/control coverage projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_scalar_control


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL scalar/control sources and coverage projection",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the scalar/control coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_scalar_control.scalar_control_projection_json())
        return 0

    issues = rtl_scalar_control.validate_rtl_scalar_control_slice(ROOT)
    if issues:
        print("RTL scalar/control slice issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL scalar/control slice issues: 0")
        return 0

    print("RTL scalar/control slice mnemonics:")
    for mnemonic in rtl_scalar_control.scalar_control_mnemonics():
        print(f"- {mnemonic}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and print the I22-S03 integrated core scalar/control projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_scalar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate integrated core scalar/control RTL sources and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the integrated core scalar/control coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_core_scalar.integrated_scalar_control_json())
        return 0

    issues = rtl_core_scalar.validate_rtl_core_scalar_control(ROOT)
    if issues:
        print("RTL integrated core scalar/control issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL integrated core scalar/control issues: 0")
        return 0

    print("RTL integrated core scalar/control coverage:")
    for row in rtl_core_scalar.integrated_scalar_control_coverage_rows():
        effects = ", ".join(row.retire_effects)
        sizes = "/".join(str(size) for size in row.size_bits)
        print(f"- {row.mnemonic} ({row.family}, {sizes}-bit): {effects}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

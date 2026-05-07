#!/usr/bin/env python3
"""Validate and print the I22-S02 integrated core fetch/decode projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate integrated core fetch/decode RTL sources and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the integrated core fetch/decode coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_core_fetch.fetch_decode_coverage_json())
        return 0

    issues = rtl_core_fetch.validate_rtl_core_fetch_decode(ROOT)
    if issues:
        print("RTL integrated core fetch/decode issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL integrated core fetch/decode issues: 0")
        return 0

    print("RTL integrated core fetch/decode coverage:")
    for row in rtl_core_fetch.fetch_decode_coverage_rows():
        print(f"- {row.size_bits}-bit: {', '.join(row.mnemonics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

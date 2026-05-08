#!/usr/bin/env python3
"""Validate and print the I22-S07 integrated core atomic/cache projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_atomic_cache


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate integrated core atomic/cache RTL sources and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the integrated core atomic/cache coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_core_atomic_cache.integrated_atomic_cache_json())
        return 0

    issues = rtl_core_atomic_cache.validate_rtl_core_atomic_cache(ROOT)
    if issues:
        print("RTL integrated core atomic/cache issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL integrated core atomic/cache issues: 0")
        return 0

    print("RTL integrated core atomic/cache coverage:")
    for row in rtl_core_atomic_cache.integrated_atomic_cache_coverage_rows():
        effects = ", ".join(row.retire_effects)
        print(f"- {row.case_id}: {row.mnemonic}: {effects}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

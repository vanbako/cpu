#!/usr/bin/env python3
"""Validate and print the I21-S02 RTL MMU/TLB coverage projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_mmu_tlb


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL MMU/TLB sources and coverage projection",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the MMU/TLB coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_mmu_tlb.mmu_tlb_projection_json())
        return 0

    issues = rtl_mmu_tlb.validate_rtl_mmu_tlb_slice(ROOT)
    if issues:
        print("RTL MMU/TLB slice issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL MMU/TLB slice issues: 0")
        return 0

    print("RTL MMU/TLB slice cases:")
    for row in rtl_mmu_tlb.mmu_tlb_coverage_rows():
        print(f"- {row.case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

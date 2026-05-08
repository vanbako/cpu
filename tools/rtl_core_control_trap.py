#!/usr/bin/env python3
"""Validate and print the I22-S05 integrated core control/trap projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_control_trap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate integrated core control/trap RTL sources and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the integrated core control/trap coverage projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_core_control_trap.integrated_control_trap_json())
        return 0

    issues = rtl_core_control_trap.validate_rtl_core_control_trap(ROOT)
    if issues:
        print("RTL integrated core control/trap issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL integrated core control/trap issues: 0")
        return 0

    print("RTL integrated core control/trap coverage:")
    for row in rtl_core_control_trap.integrated_control_trap_coverage_rows():
        effects = ", ".join(row.retire_effects)
        print(f"- {row.case_id}: {row.mnemonic}: {effects}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

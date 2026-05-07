#!/usr/bin/env python3
"""Validate and print the I22-S01 integrated RTL core shell projection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate RTL integrated-core shell sources and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the integrated-core shell port projection as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(rtl_core.core_shell_ports_json())
        return 0

    issues = rtl_core.validate_rtl_core_shell(ROOT)
    if issues:
        print("RTL integrated core shell issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("RTL integrated core shell issues: 0")
        return 0

    print("RTL integrated core shell ports:")
    for port in rtl_core.core_shell_ports():
        print(f"- {port.name}: {port.direction} {port.type_name} ({port.group})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

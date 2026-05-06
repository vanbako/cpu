#!/usr/bin/env python3
"""Render and validate the I20-S08 RTL readiness gap report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the RTL readiness report inventory and doc",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="output format",
    )
    args = parser.parse_args(argv)

    if args.check:
        issues = rtl_readiness.validate_rtl_readiness_report(ROOT)
        if issues:
            print("RTL readiness gap report issues:")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print("RTL readiness gap report issues: 0")
        return 0

    if args.format == "json":
        print(rtl_readiness.rtl_readiness_report_json())
    else:
        print(rtl_readiness.render_rtl_readiness_markdown(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

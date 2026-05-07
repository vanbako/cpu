#!/usr/bin/env python3
"""Render and validate the I21-S06 RTL semantic closure report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_semantic_closure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the RTL semantic closure report and artifacts",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="output format",
    )
    args = parser.parse_args(argv)

    if args.check:
        issues = rtl_semantic_closure.validate_rtl_semantic_closure(ROOT)
        if issues:
            print("RTL semantic closure issues:")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print("RTL semantic closure issues: 0")
        return 0

    if args.format == "json":
        print(rtl_semantic_closure.rtl_semantic_closure_json())
    else:
        print(rtl_semantic_closure.render_rtl_semantic_closure_markdown(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
